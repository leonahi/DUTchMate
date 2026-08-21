from importlib.metadata import version

from mcp.server import MCPServer
from mcp.types import LATEST_PROTOCOL_VERSION


def test_mcp_sdk_matches_the_normative_protocol_baseline() -> None:
    assert version("mcp").split(".", maxsplit=1)[0] == "2"
    assert LATEST_PROTOCOL_VERSION == "2026-07-28"
    assert MCPServer.__name__ == "MCPServer"
