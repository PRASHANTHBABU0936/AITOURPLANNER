"""
MCP client for the AI Tour Planner.

Connects the travel-planner agents to the project's MCP servers over the
official stdio transport, providing tool discovery (``list_tools``) and tool
execution (``call_tool``).

The agents run synchronously while the MCP SDK is asynchronous, so the manager
keeps a persistent anyio blocking portal that owns a background event loop.
Each server connection is opened lazily and reused across calls.

Usage:

    from mcp_client import get_mcp_manager

    manager = get_mcp_manager()
    manager.list_tools("research")
    manager.call_tool("research", "destination_info", {"destination": "Goa"})
"""

from __future__ import annotations

import contextlib
import json
import logging
import sys
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from anyio.from_thread import BlockingPortal, start_blocking_portal
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent

DEFAULT_CALL_TIMEOUT = 60.0


class MCPError(RuntimeError):
    """Raised when an MCP server is unavailable or a tool call fails."""


def _server_parameters(module: str) -> StdioServerParameters:
    """Build stdio parameters that launch a project MCP server module."""
    return StdioServerParameters(
        command=sys.executable,
        args=["-m", module],
        cwd=str(PROJECT_ROOT),
    )


# Registry of the MCP servers shipped with the project.
SERVER_REGISTRY: Dict[str, StdioServerParameters] = {
    "research": _server_parameters("mcp_servers.research_server"),
    "images": _server_parameters("mcp_servers.image_server"),
}


def _tool_to_dict(tool: Any) -> Dict[str, Any]:
    """Normalise an MCP ``Tool`` object into a plain dictionary."""
    schema = getattr(tool, "input_schema", None)
    if schema is None:
        schema = getattr(tool, "inputSchema", None)

    return {
        "name": getattr(tool, "name", ""),
        "description": getattr(tool, "description", "") or "",
        "input_schema": schema or {},
    }


def _result_text(result: Any) -> str:
    """Concatenate the text blocks of an MCP ``CallToolResult``."""
    parts: List[str] = []
    for block in getattr(result, "content", None) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(str(text))
    return "\n".join(parts)


def _extract_result(result: Any) -> Any:
    """
    Convert an MCP tool result into a plain Python value.

    Structured content is returned as-is; otherwise the text payload is
    JSON-decoded when possible and returned as a string when it is not.
    """
    if getattr(result, "is_error", False):
        raise MCPError(_result_text(result) or "MCP tool returned an error")

    structured = getattr(result, "structured_content", None)
    if isinstance(structured, dict):
        # Unwrap the single ``result`` key produced by output schemas.
        if set(structured) == {"result"}:
            return structured["result"]
        return structured
    if structured is not None:
        return structured

    text = _result_text(result)
    if not text:
        return None

    try:
        return json.loads(text)
    except (ValueError, TypeError):
        return text


class MCPClientManager:
    """Discover and execute MCP tools across the project's servers."""

    def __init__(
        self,
        servers: Optional[Dict[str, StdioServerParameters]] = None,
        call_timeout: float = DEFAULT_CALL_TIMEOUT,
    ) -> None:
        self._servers = dict(servers or SERVER_REGISTRY)
        self._call_timeout = call_timeout

        self._portal: Optional[BlockingPortal] = None
        self._portal_cm = None
        self._sessions: Dict[str, ClientSession] = {}
        self._tools: Dict[str, List[Dict[str, Any]]] = {}
        self._stack = contextlib.ExitStack()
        # Re-entrant lock: guards portal/session setup so concurrent callers
        # (for example multiple Streamlit sessions) share one session each.
        self._lock = threading.RLock()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def start(self) -> None:
        """Start the background event loop that hosts the sessions."""
        if self._portal is not None:
            return

        with self._lock:
            if self._portal is None:
                self._portal_cm = start_blocking_portal(backend="asyncio")
                self._portal = self._portal_cm.__enter__()
                logger.debug("MCP client portal started")

    def close(self) -> None:
        """Close every server session and stop the background loop."""
        with self._lock:
            if self._portal is None:
                return

            try:
                self._stack.close()
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Error while closing MCP sessions: %s", exc)

            self._sessions.clear()
            self._tools.clear()

            try:
                self._portal_cm.__exit__(None, None, None)
            except Exception as exc:  # pragma: no cover - defensive
                logger.warning("Error while stopping MCP portal: %s", exc)

            self._portal = None
            self._portal_cm = None

    # ------------------------------------------------------------------
    # Connections
    # ------------------------------------------------------------------
    @contextlib.asynccontextmanager
    async def _session(self, server: str):
        """Open one server session and yield it for the connection lifetime."""
        params = self._servers[server]

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                self._tools[server] = [
                    _tool_to_dict(tool) for tool in result.tools
                ]
                yield session

    def _ensure_connected(self, server: str) -> ClientSession:
        """Connect to a server on first use and cache the session."""
        session = self._sessions.get(server)
        if session is not None:
            return session

        if server not in self._servers:
            raise MCPError(f"Unknown MCP server: {server!r}")

        # Serialise connection setup so concurrent callers share one session.
        with self._lock:
            session = self._sessions.get(server)
            if session is not None:
                return session

            self.start()

            try:
                cm = self._portal.wrap_async_context_manager(
                    self._session(server)
                )
                session = self._stack.enter_context(cm)
            except Exception as exc:
                raise MCPError(
                    f"Could not connect to MCP server {server!r}: {exc}"
                ) from exc

            self._sessions[server] = session

        logger.info("Connected to MCP server %r", server)
        return session

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def servers(self) -> List[str]:
        """Return the configured MCP server names."""
        return list(self._servers)

    def list_tools(self, server: str) -> List[Dict[str, Any]]:
        """Discover the tools exposed by a server."""
        self._ensure_connected(server)
        return self._tools.get(server, [])

    def call_tool(
        self,
        server: str,
        tool: str,
        arguments: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a tool on a server and return its plain Python result."""
        session = self._ensure_connected(server)

        async def _invoke() -> Any:
            return await session.call_tool(
                tool,
                arguments or {},
                read_timeout_seconds=self._call_timeout,
            )

        try:
            result = self._portal.call(_invoke)
        except Exception as exc:
            raise MCPError(
                f"MCP tool {server}.{tool} failed: {exc}"
            ) from exc

        return _extract_result(result)


# ----------------------------------------------------------------------
# Module-level singleton access
# ----------------------------------------------------------------------

_manager: Optional[MCPClientManager] = None
_manager_lock = threading.Lock()


def get_mcp_manager() -> MCPClientManager:
    """Return the process-wide MCP client manager, starting it on first use."""
    global _manager

    if _manager is None:
        with _manager_lock:
            if _manager is None:
                manager = MCPClientManager()
                manager.start()
                _manager = manager

    return _manager


def list_tools(server: str) -> List[Dict[str, Any]]:
    """Convenience wrapper around :meth:`MCPClientManager.list_tools`."""
    return get_mcp_manager().list_tools(server)


def call_tool(
    server: str,
    tool: str,
    arguments: Optional[Dict[str, Any]] = None,
) -> Any:
    """Convenience wrapper around :meth:`MCPClientManager.call_tool`."""
    return get_mcp_manager().call_tool(server, tool, arguments)


__all__ = [
    "MCPClientManager",
    "MCPError",
    "SERVER_REGISTRY",
    "get_mcp_manager",
    "list_tools",
    "call_tool",
]
