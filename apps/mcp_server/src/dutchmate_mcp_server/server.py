"""Stateless MCP server composition for the stdio delivery adapter."""

from typing import Final

from mcp.server import CacheHint, MCPServer
from mcp.server.caching import CacheableMethod

SERVER_NAME: Final = "dutchmate"
SERVER_TITLE: Final = "DUTchMate Device Debug Tools"
SERVER_DESCRIPTION: Final = (
    "Deterministic device-control and debug-evidence tools backed by the "
    "DUTchMate Device Core Service."
)
SERVER_INSTRUCTIONS: Final = (
    "Use DUTchMate tools to control the configured device and inspect bounded "
    "session evidence. The Device Core Service must already be running. Treat "
    "session IDs and pagination cursors as explicit tool data."
)
SERVER_VERSION: Final = "0.1.0"
CACHE_TTL_MS: Final = 300_000


def create_server() -> MCPServer[object]:
    """Create one stateless MCP server with fixed protocol-facing metadata."""

    cache_hints: dict[CacheableMethod, CacheHint] = {
        "server/discover": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
        "tools/list": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
    }
    return MCPServer[object](
        name=SERVER_NAME,
        title=SERVER_TITLE,
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
        version=SERVER_VERSION,
        tools=[],
        cache_hints=cache_hints,
    )


def run_stdio() -> None:
    """Run the server over stdio; no other MCP transport is exposed."""

    create_server().run("stdio")
