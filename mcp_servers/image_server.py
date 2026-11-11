"""
Travel images MCP server.

Exposes the Wikimedia Commons REST integration as MCP tools by wrapping the
helpers in ``mcp_servers.image_tools``.

Run as a stdio MCP server:

    python -m mcp_servers.image_server
"""

from typing import Any, Dict, List

from mcp.server.mcpserver import MCPServer

from mcp_servers.image_tools import (
    download_image_b64,
    search_images,
)
from mcp_servers.image_tools import search_place_images as _search_place_images


server = MCPServer(
    name="travel-images",
    instructions=(
        "Wikimedia Commons photo search and download tools for travel "
        "destinations. No API key is required."
    ),
)


@server.tool()
def search_commons_images(query: str, limit: int = 8) -> List[Dict[str, Any]]:
    """Search Wikimedia Commons for images matching a free-text query."""
    return search_images(query, limit)


@server.tool()
def search_place_images(place: str, destination: str = "", limit: int = 10) -> List[Dict[str, Any]]:
    """
    Return Wikimedia Commons photographs for a named place.

    Prefers a place + destination match before falling back to a place-only
    search. Each result contains ``url``, ``source_url``, ``artist`` and
    ``license`` fields.
    """
    return _search_place_images(place, destination, limit)


@server.tool()
def download_image(url: str) -> Dict[str, str]:
    """
    Download an image URL and return its bytes as base64.

    The response contains ``content_type`` and ``data_base64``.
    """
    return download_image_b64(url)


def main() -> None:
    """Run the MCP server over stdio."""
    server.run("stdio")


if __name__ == "__main__":
    main()
