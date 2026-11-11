"""
Wikimedia Commons REST helpers backing the travel-images MCP server.

The raw HTTP integration lives here (not in the agents) so the MCP server and
the client's offline fallback share a single source of truth. This module never
imports the MCP SDK.
"""

from __future__ import annotations

import base64
import logging
import re
from typing import Any, Dict, List

import requests

logger = logging.getLogger(__name__)

API_URL = "https://commons.wikimedia.org/w/api.php"

HEADERS = {
    "User-Agent": (
        "AITourPlanner/1.0 "
        "(real travel photo retrieval for an educational project)"
    )
}

REQUEST_TIMEOUT = 25

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _plain_text(value: Any) -> str:
    """Remove HTML tags from Wikimedia metadata values."""
    return re.sub(r"<[^>]*>", "", str(value or "")).strip()


def _search_commons(query: str, limit: int) -> List[Dict[str, str]]:
    """Execute a single Wikimedia Commons image search query."""
    params = {
        "action": "query",
        "format": "json",
        "formatversion": "2",
        "generator": "search",
        "gsrsearch": f"filetype:bitmap {query}",
        "gsrnamespace": "6",
        "gsrlimit": min(max(int(limit), 1), 20),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "iiurlwidth": "1200",
    }

    response = SESSION.get(API_URL, params=params, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()
    data = response.json()

    if "error" in data:
        raise RuntimeError(f"Wikimedia API error: {data['error']}")

    pages = data.get("query", {}).get("pages", [])
    if isinstance(pages, dict):
        pages = list(pages.values())

    photos: List[Dict[str, str]] = []
    seen_urls = set()

    for page in pages:
        info_list = page.get("imageinfo") or []
        if not info_list:
            continue

        info = info_list[0]
        image_url = info.get("thumburl") or info.get("url")
        if not image_url or image_url in seen_urls:
            continue

        mime = info.get("mime", "")
        if mime and not mime.startswith("image/"):
            continue

        metadata = info.get("extmetadata") or {}

        def meta(name: str, default: str = "") -> str:
            return _plain_text((metadata.get(name) or {}).get("value", default))

        title = page.get("title", "Wikimedia Commons image")

        photos.append({
            "title": title.removeprefix("File:"),
            "url": image_url,
            "source_url": (
                info.get("descriptionurl")
                or (
                    "https://commons.wikimedia.org/wiki/"
                    + title.replace(" ", "_")
                )
            ),
            "artist": meta("Artist", "Unknown") or "Unknown",
            "license": (
                meta("LicenseShortName", "Check source page")
                or "Check source page"
            ),
        })

        seen_urls.add(image_url)

    return photos


def search_images(query: str, limit: int = 8) -> List[Dict[str, str]]:
    """Search Wikimedia Commons for images matching a free-text query."""
    if not query or not query.strip():
        return []

    return _search_commons(query.strip(), limit)


def search_place_images(
    place: str,
    destination: str = "",
    limit: int = 10,
) -> List[Dict[str, str]]:
    """
    Search Wikimedia Commons for photographs of one named place.

    Tries a place + destination query first, then a broader place-only query.
    Returns an empty list when no usable results are found.
    """
    if not place or not place.strip():
        return []

    if destination and destination.strip():
        queries = [
            f'"{place}" "{destination}"',
            f'"{place}"',
        ]
    else:
        queries = [f'"{place}"']

    for query in queries:
        try:
            photos = _search_commons(query, limit)
        except Exception as exc:
            logger.warning("Wikimedia search failed for %r: %s", query, exc)
            continue

        if photos:
            for photo in photos:
                photo["caption"] = place
            return photos

    return []


def download_image_b64(url: str) -> Dict[str, str]:
    """
    Download an image URL and return its bytes as base64.

    Returns a mapping with ``content_type`` and ``data_base64`` so the result
    can be transported through an MCP tool response.
    """
    response = SESSION.get(url, timeout=REQUEST_TIMEOUT)
    response.raise_for_status()

    content_type = response.headers.get("Content-Type", "").lower()
    if content_type and not content_type.startswith("image/"):
        raise RuntimeError(f"URL did not return an image: {content_type}")

    if not response.content:
        raise RuntimeError("Downloaded image is empty.")

    return {
        "content_type": content_type,
        "data_base64": base64.b64encode(response.content).decode("ascii"),
    }


__all__ = [
    "search_images",
    "search_place_images",
    "download_image_b64",
]
