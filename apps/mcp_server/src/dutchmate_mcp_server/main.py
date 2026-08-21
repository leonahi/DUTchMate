"""MCP server entrypoint for DUTchMate."""

from dutchmate_mcp_server.server import run_stdio


def main() -> None:
    """Start the DUTchMate MCP server."""
    run_stdio()
