"""
Wikimedia Commons API helper for AI Tour Planner.
No API key is required for public image searches.
Follow each image's license and attribution requirements.
"""
from pathlib import Path
import re
import requests

API_URL = "https://commons.wikimedia.org/w/api.php"
HEADERS = {
    "User-Agent": "AITourPlanner/1.0 (real travel photo search; educational project)"
}
TIMEOUT = 25


def search_images(query: str, limit: int = 8) -> list[dict]:
    """Return real Wikimedia Commons images matching a search query."""
    if not query or not query.strip():
        return []

    params = {
        "action": "query",
        "format": "json",
        "generator": "search",
        "gsrsearch": query.strip(),
        "gsrnamespace": 6,
        "gsrlimit": max(1, min(int(limit), 20)),
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": 1200,
    }
    response = requests.get(API_URL, params=params, headers=HEADERS, timeout=TIMEOUT)
    response.raise_for_status()
    payload = response.json()

    images = []
    for page in payload.get("query", {}).get("pages", {}).values():
        info_list = page.get("imageinfo", [])
        if not info_list:
            continue
        info = info_list[0]
        metadata = info.get("extmetadata", {})

        def value(key, default=""):
            raw = metadata.get(key, {}).get("value", default)
            return re.sub(r"<[^>]*>", "", str(raw)).strip()

        image_url = info.get("thumburl") or info.get("url")
        if image_url:
            images.append({
                "title": page.get("title", "Wikimedia Commons image"),
                "url": image_url,
                "source_url": info.get("descriptionurl", ""),
                "artist": value("Artist", "Unknown"),
                "license": value("LicenseShortName", "Check source page"),
                "credit": value("Credit", ""),
            })
    return images


def download_image(image: dict, output_dir: str | Path = "images") -> str:
    """Download an image result and return its local file path."""
    image_url = image.get("url")
    if not image_url:
        raise ValueError("The image result has no URL.")

    folder = Path(output_dir)
    folder.mkdir(parents=True, exist_ok=True)
    title = image.get("title", "travel_photo")
    filename = Path(title.replace("File:", "")).name
    filename = re.sub(r"[^A-Za-z0-9._-]+", "_", filename).strip("._") or "travel_photo.jpg"
    destination = folder / filename

    if destination.exists() and destination.stat().st_size > 0:
        return str(destination)

    response = requests.get(image_url, headers=HEADERS, timeout=TIMEOUT, stream=True)
    response.raise_for_status()
    content_type = response.headers.get("Content-Type", "").lower()
    if not content_type.startswith("image/"):
        raise ValueError(f"URL did not return an image (Content-Type: {content_type}).")

    try:
        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    file.write(chunk)
        if destination.stat().st_size == 0:
            raise ValueError("Downloaded image was empty.")
    except Exception:
        destination.unlink(missing_ok=True)
        raise
    return str(destination)
