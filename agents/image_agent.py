"""
Image Agent: Fetches real photographs for places in the actual travel plan.

- Uses itinerary/research attractions instead of a hardcoded city list.
- Retrieves and downloads photographs via the MCP image server (Wikimedia
  Commons), falling back to the direct REST helper when MCP is unavailable.
- Avoids duplicate image URLs.
- Saves validated JPEG files in the project's images directory.
- Preserves the existing TravelPlanState structure.
- Stores source URLs, artist information, and license details.
"""

from pathlib import Path
from typing import Dict, List
from io import BytesIO
import base64
import logging
import re

from PIL import Image, UnidentifiedImageError

from models.schemas import TravelPlanState
from mcp_servers.image_tools import (
    download_image_b64 as _rest_download_image,
)
from mcp_servers.image_tools import (
    search_place_images as _rest_search_place_images,
)


logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
IMAGES_DIR = BASE_DIR / "images"

MAX_IMAGES = 6


def _get(obj, key, default=None):
    """Read a field from a dictionary or an object."""
    if isinstance(obj, dict):
        return obj.get(key, default)

    return getattr(obj, key, default)


def _make_slug(text: str) -> str:
    """Create a filesystem-safe name."""
    slug = re.sub(
        r"[^a-zA-Z0-9_-]+",
        "_",
        str(text or "travel_photo").strip().lower(),
    ).strip("_")

    return slug or "travel_photo"


def _place_name(value) -> str:
    """
    Get a named place from an attraction/activity.

    Supports strings and common dictionary/Pydantic object fields.
    """
    if isinstance(value, str):
        name = value.strip()
    else:
        name = ""

        for field in (
            "name",
            "title",
            "place",
            "attraction",
            "location",
            "site",
            "landmark",
        ):
            candidate = _get(value, field)

            if isinstance(candidate, str) and candidate.strip():
                name = candidate.strip()
                break

    name = re.sub(r"\s+", " ", name).strip(" .,:;-")

    # Remove common activity prefixes without inventing new locations.
    name = re.sub(
        r"^(visit|explore|see|tour|head to|travel to)\s+",
        "",
        name,
        flags=re.IGNORECASE,
    ).strip(" .,:;-")

    # Don't search generic activities as if they were landmarks.
    generic = {
        "breakfast",
        "lunch",
        "dinner",
        "free time",
        "shopping",
        "check in",
        "check-in",
        "check out",
        "check-out",
        "arrival",
        "departure",
        "relax",
        "hotel",
        "travel",
        "sightseeing",
    }

    if len(name) < 3 or name.casefold() in generic:
        return ""

    return name


def _extract_places(state, final_plan) -> List[str]:
    """
    Extract places from the plan and research fields.

    No city-specific attraction list is used. Only named places actually
    present in the available plan/research data are searched.
    """
    places = []
    seen = set()

    def add(value):
        name = _place_name(value)

        if not name:
            return

        key = name.casefold()

        if key not in seen:
            seen.add(key)
            places.append(name)

    # Attractions explicitly included in the final plan.
    destination_info = _get(final_plan, "destination_info")
    attractions = _get(destination_info, "attractions", []) or []

    if isinstance(attractions, (list, tuple)):
        for attraction in attractions:
            add(attraction)

    # Activities explicitly included in each itinerary day.
    itinerary = _get(final_plan, "itinerary")
    days = _get(itinerary, "days", []) or []

    if isinstance(days, (list, tuple)):
        for day in days:
            activities = _get(day, "activities", []) or []

            if isinstance(activities, (list, tuple)):
                for activity in activities:
                    add(activity)

    # Some project versions may store research separately on state.
    for field in (
        "research",
        "research_results",
        "research_data",
        "destination_research",
    ):
        research = _get(state, field)

        if not research:
            continue

        research_attractions = _get(research, "attractions", []) or []

        if isinstance(research_attractions, (list, tuple)):
            for attraction in research_attractions:
                add(attraction)

        research_places = _get(research, "places", []) or []

        if isinstance(research_places, (list, tuple)):
            for place in research_places:
                add(place)

    return places


def _search_commons(
    place: str,
    destination: str,
    limit: int = 10,
) -> List[Dict[str, str]]:
    """
    Search Wikimedia Commons for photographs of one named place.

    Uses the MCP image server first, then falls back to the direct REST
    helper when MCP is unavailable.
    """
    try:
        from mcp_client import call_tool

        photos = call_tool(
            "images",
            "search_place_images",
            {
                "place": place,
                "destination": destination,
                "limit": limit,
            },
        )

        if isinstance(photos, list):
            return photos

        raise ValueError("unexpected MCP search response")

    except Exception as exc:
        logger.warning(
            "MCP image search failed for %r (%s); using direct REST fallback",
            place,
            exc,
        )
        return _rest_search_place_images(place, destination, limit)


def _write_image_bytes(
    content: bytes,
    output_path: Path,
) -> None:
    """Validate raw image bytes and save them as a JPEG."""
    if not content:
        raise RuntimeError("Downloaded image is empty.")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    temp_path = output_path.with_name(
        f"{output_path.stem}.tmp.jpg"
    )

    try:
        with Image.open(BytesIO(content)) as image:
            image.load()

            if image.width < 200 or image.height < 150:
                raise RuntimeError(
                    f"Image resolution too small: "
                    f"{image.width}x{image.height}"
                )

            # Convert formats such as WebP to a real JPEG.
            image.convert("RGB").save(
                temp_path,
                format="JPEG",
                quality=90,
                optimize=True,
            )

        # Validate the generated JPEG.
        with Image.open(temp_path) as image:
            image.verify()

        temp_path.replace(output_path)

    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise RuntimeError(
            f"Downloaded content is not a usable image: {exc}"
        ) from exc

    finally:
        if temp_path.exists():
            temp_path.unlink(missing_ok=True)


def _download_photo_bytes(url: str) -> bytes:
    """
    Fetch raw photograph bytes through the MCP image server.

    Falls back to the direct REST helper when MCP is unavailable.
    """
    try:
        from mcp_client import call_tool

        result = call_tool("images", "download_image", {"url": url})

        if isinstance(result, dict) and result.get("data_base64"):
            return base64.b64decode(result["data_base64"])

        raise ValueError("unexpected MCP download response")

    except Exception as exc:
        logger.warning(
            "MCP image download failed (%s); using direct REST fallback",
            exc,
        )

    data = _rest_download_image(url)
    return base64.b64decode(data["data_base64"])


def _download_photo(
    photo: Dict[str, str],
    output_path: Path,
) -> None:
    """Download an image, validate it, and save it as a JPEG."""
    _write_image_bytes(
        _download_photo_bytes(photo["url"]),
        output_path,
    )


def _is_valid_image(path: Path) -> bool:
    """Return True if a cached image exists and is readable."""
    try:
        if not path.is_file() or path.stat().st_size == 0:
            return False

        with Image.open(path) as image:
            image.verify()

        return True

    except (OSError, ValueError, UnidentifiedImageError):
        return False


def image_agent_node(state: TravelPlanState) -> TravelPlanState:
    """Fetch real photos for named places in the generated travel plan."""

    if getattr(state, "errors", None) is None:
        state.errors = []

    if getattr(state, "conversation_history", None) is None:
        state.conversation_history = []

    final_plan = getattr(state, "final_plan", None)

    if final_plan is None:
        message = "Image Agent: final_plan is missing."
        state.generated_images = []
        state.errors.append(message)
        logger.error(message)
        return state

    destination = str(
        _get(final_plan, "destination", "") or ""
    ).strip()

    if not destination:
        destination = "travel destination"

    places = _extract_places(state, final_plan)

    if not places:
        message = (
            "Image Agent: no named attractions were found in the final "
            "plan or available research fields. Check the field names "
            "used by your research agent and itinerary schema."
        )
        state.generated_images = []
        state.errors.append(message)
        logger.warning(message)
        return state

    IMAGES_DIR.mkdir(parents=True, exist_ok=True)

    generated_images: List[Dict[str, str]] = []
    used_urls = set()
    download_errors = []

    for place in places:
        if len(generated_images) >= MAX_IMAGES:
            break

        photos = _search_commons(place, destination)

        if not photos:
            logger.warning(
                "Wikimedia returned no photos for itinerary place %r",
                place,
            )
            continue

        for photo in photos:
            if len(generated_images) >= MAX_IMAGES:
                break

            if photo["url"] in used_urls:
                continue

            filename = (
                f"real_{_make_slug(destination)}_"
                f"{_make_slug(place)}.jpg"
            )
            output_path = IMAGES_DIR / filename

            try:
                # Reuse a valid cached photo.
                if not _is_valid_image(output_path):
                    output_path.unlink(missing_ok=True)
                    _download_photo(photo, output_path)

                used_urls.add(photo["url"])

                generated_images.append({
                    "path": str(output_path.resolve()),
                    "filename": filename,
                    "caption": place,
                    "alt": f"Real photograph of {place}, {destination}",
                    "prompt": place,
                    "source_url": photo["source_url"],
                    "image_url": photo["url"],
                    "artist": photo["artist"],
                    "license": photo["license"],
                })

                logger.info(
                    "Saved photograph for itinerary place %r: %s",
                    place,
                    output_path,
                )

                # One photo per named place.
                break

            except Exception as exc:
                error = (
                    f"Could not download photo for '{place}': "
                    f"{type(exc).__name__}: {exc}"
                )
                download_errors.append(error)
                logger.exception(error)

    state.generated_images = generated_images

    if generated_images:
        message = (
            f"Fetched {len(generated_images)} real photograph(s) "
            f"for {destination}. Places shown: "
            + ", ".join(
                image["caption"] for image in generated_images
            )
        )

        logger.info(message)

    else:
        message = (
            f"Fetched 0 real photographs for {destination}. "
            f"Found {len(places)} named itinerary/research places, "
            "but no usable photographs were downloaded. "
            "Check the terminal logs for details."
        )

        logger.warning(message)

        if download_errors:
            state.errors.extend(download_errors[:5])

        state.errors.append(message)

    state.conversation_history.append({
        "role": "image_agent",
        "content": message,
    })

    return state