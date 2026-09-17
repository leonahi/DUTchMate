from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from unittest.mock import Mock

import httpx
from mcp.server import CacheHint
from mcp.types import CallToolResult, TextContent

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
from dutchmate_mcp_server.service_client import DeviceCoreClient

EXPECTED_TOOL_NAMES = [
    "reset_dut",
    "set_boot_mode",
    "capture_uart",
    "get_recent_uart_log",
    "wait_for_uart_pattern",
    "run_boot_test",
    "send_uart_command",
    "get_debug_session",
    "list_debug_sessions",
]


async def test_create_server_has_fixed_identity_and_deterministic_tool_catalog() -> None:
    server = create_server()

    assert server.name == SERVER_NAME
    assert server.title == SERVER_TITLE
    assert server.description == SERVER_DESCRIPTION
    assert server.instructions == SERVER_INSTRUCTIONS
    assert server.version == SERVER_VERSION
    first_listing = await server.list_tools()
    second_listing = await server.list_tools()

    assert [tool.name for tool in first_listing] == EXPECTED_TOOL_NAMES
    assert [tool.name for tool in second_listing] == EXPECTED_TOOL_NAMES


async def test_registered_tools_return_complete_structured_service_results() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            200,
            json={"ok": True, "method": request.method, "path": request.url.path},
        )

    server = create_server(client_factory=_client_factory(handler))
    calls: list[tuple[str, dict[str, object]]] = [
        ("reset_dut", {}),
        ("set_boot_mode", {"mode": "bootloader"}),
        ("capture_uart", {"duration_s": 1.5}),
        ("get_recent_uart_log", {}),
        ("wait_for_uart_pattern", {"pattern": "READY", "timeout_s": 2}),
        ("run_boot_test", {"duration_s": 3}),
        ("send_uart_command", {"cmd": "version"}),
        ("get_debug_session", {"session_id": "session-1"}),
        ("list_debug_sessions", {}),
    ]

    results = [await server.call_tool(name, arguments) for name, arguments in calls]

    assert [request.url.path for request in requests] == [
        "/dut/reset",
        "/dut/boot-mode",
        "/dut/capture",
        "/dut/logs",
        "/dut/wait-pattern",
        "/dut/boot-test",
        "/dut/uart/send",
        "/sessions/session-1",
        "/sessions",
    ]
    for result, request in zip(results, requests, strict=True):
        assert isinstance(result, CallToolResult)
        assert result.result_type == "complete"
        assert result.is_error is False
        expected = {"ok": True, "method": request.method, "path": request.url.path}
        assert result.structured_content == expected
        assert len(result.content) == 1
        assert isinstance(result.content[0], TextContent)
        assert json.loads(result.content[0].text) == expected


async def test_registered_tool_preserves_device_core_error_as_structured_tool_error() -> None:
    error_payload: dict[str, object] = {
        "ok": False,
        "error": "not_configured",
        "detail": "reset role is not configured",
        "detail_truncated": False,
        "context": {
            "operation": "reset",
            "required_role": "reset",
            "role_state": "unconfigured",
        },
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(409, json=error_payload)

    server = create_server(client_factory=_client_factory(handler))

    result = await server.call_tool("reset_dut", {})

    assert isinstance(result, CallToolResult)
    assert result.result_type == "complete"
    assert result.is_error is True
    assert result.structured_content == error_payload
    assert len(result.content) == 1
    assert isinstance(result.content[0], TextContent)
    assert json.loads(result.content[0].text) == error_payload


async def test_registered_tool_projects_validation_failure_without_http_dispatch() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={"ok": True})

    server = create_server(client_factory=_client_factory(handler))

    result = await server.call_tool("send_uart_command", {"cmd": "x" * 1025})

    assert isinstance(result, CallToolResult)
    assert result.result_type == "complete"
    assert result.is_error is True
    assert result.structured_content == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "UART send payload must contain 1..1024 bytes",
        "detail_truncated": False,
        "context": {"actual_bytes": 1026, "max_bytes": 1024},
    }
    assert request_count == 0


async def test_registered_tool_projects_unavailable_service_as_structured_tool_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    server = create_server(client_factory=_client_factory(handler))

    result = await server.call_tool("reset_dut", {})

    assert isinstance(result, CallToolResult)
    assert result.is_error is True
    assert result.structured_content is not None
    assert result.structured_content["error"] == "service_unavailable"
    assert "explicit Basic or Enhanced backend" in result.structured_content["detail"]


async def test_registered_tool_projects_invalid_service_response_as_tool_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"not-json")

    server = create_server(client_factory=_client_factory(handler))

    result = await server.call_tool("reset_dut", {})

    assert isinstance(result, CallToolResult)
    assert result.is_error is True
    assert result.structured_content == {
        "ok": False,
        "error": "service_protocol_error",
        "detail": "Device Core Service returned invalid JSON with HTTP 200",
        "detail_truncated": False,
    }


def test_create_server_configures_finite_private_cache_hints() -> None:
    server = create_server()

    assert server._lowlevel_server.cache_hints == {  # type: ignore[attr-defined]
        "server/discover": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
        "tools/list": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
    }


def test_run_stdio_exposes_only_the_stdio_transport(monkeypatch: object) -> None:
    server = Mock()
    monkeypatch.setattr(server_module, "create_server", lambda: server)

    run_stdio()

    server.run.assert_called_once_with("stdio")


def _client_factory(
    handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
) -> Callable[[], DeviceCoreClient]:
    return lambda: DeviceCoreClient(transport=httpx.MockTransport(handler))
