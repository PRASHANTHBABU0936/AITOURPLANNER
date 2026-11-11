"""
Travel research MCP server.

Exposes the project's destination research REST integrations as MCP tools by
wrapping the existing helpers in ``tools``:

- Open-Meteo geocoding + weather
- CountriesNow country / currency lookup

Run as a stdio MCP server:

    python -m mcp_servers.research_server
"""

from typing import Any, Dict

from mcp.server.mcpserver import MCPServer

from tools import (
    get_country_currency,
    get_destination_info,
    get_location_and_weather,
)


server = MCPServer(
    name="travel-research",
    instructions=(
        "Live destination research tools: geocoding, current weather and "
        "country/currency metadata. No API keys are required."
    ),
)


@server.tool()
def destination_info(destination: str) -> str:
    """
    Return a complete research summary for a destination.

    Includes matched location, coordinates, live weather (Open-Meteo) and
    country/currency details (CountriesNow) formatted for LLM consumption.
    """
    return get_destination_info(destination)


@server.tool()
def location_and_weather(destination: str) -> Dict[str, Any]:
    """
    Return coordinates and current weather for a destination.

    Uses Open-Meteo geocoding and forecast endpoints.
    """
    return get_location_and_weather(destination)


@server.tool()
def country_currency(
    country_name: str = "",
    country_code: str = "",
) -> Dict[str, Any]:
    """
    Return country and currency details using CountriesNow.

    Match by ``country_name`` or ISO2 ``country_code``.
    """
    return get_country_currency(country_name, country_code)


def main() -> None:
    """Run the MCP server over stdio."""
    server.run("stdio")


if __name__ == "__main__":
    main()
