from __future__ import annotations

from unittest.mock import Mock

from mcp.server import CacheHint

import dutchmate_mcp_server.server as server_module
from dutchmate_mcp_server.server import (
    CACHE_TTL_MS,
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    SERVER_NAME,
    SERVER_TITLE,
    SERVER_VERSION,
    create_server,
    run_stdio,
)


async def test_create_server_has_fixed_identity_and_deterministic_empty_catalog() -> None:
    server = create_server()

    assert server.name == SERVER_NAME
    assert server.title == SERVER_TITLE
    assert server.description == SERVER_DESCRIPTION
    assert server.instructions == SERVER_INSTRUCTIONS
    assert server.version == SERVER_VERSION
    assert await server.list_tools() == []
    assert await server.list_tools() == []


def test_create_server_configures_finite_private_cache_hints() -> None:
    server = create_server()

    assert server._lowlevel_server.cache_hints == {  # type: ignore[attr-defined]
        "server/discover": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
        "tools/list": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
    }


def test_run_stdio_exposes_only_the_stdio_transport(monkeypatch: object) -> None:
    server = Mock()
    monkeypatch.setattr(server_module, "create_server", lambda: server)  # type: ignore[attr-defined]

    run_stdio()

    server.run.assert_called_once_with("stdio")
