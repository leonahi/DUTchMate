from __future__ import annotations

import json
from collections.abc import Callable, Coroutine
from unittest.mock import AsyncMock, Mock

import httpx
import pytest
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
    "get_status",
    "monitor",
    "interact",
    "send_uart",
    "reset_dut",
    "set_dut_boot_mode",
    "get_evidence",
    "get_recent_logs",
    "list_sessions",
    "get_session",
    "release_connection",
    "reacquire_connection",
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
        ("get_status", {}),
        ("monitor", {"duration_s": 1.5}),
        ("interact", {"data_b64": "AP8=", "duration_s": 1}),
        ("send_uart", {"text": "version", "line_ending": "none"}),
        ("reset_dut", {}),
        ("set_dut_boot_mode", {"mode": "bootloader"}),
        ("get_evidence", {"cursor": "opaque+/=", "wait_s": 0}),
        ("get_recent_logs", {}),
        ("list_sessions", {}),
        ("get_session", {"session_id": "session-1"}),
        ("release_connection", {}),
        ("reacquire_connection", {}),
    ]

    results = [await server.call_tool(name, arguments) for name, arguments in calls]

    assert [(request.method, request.url.path) for request in requests] == [
        ("GET", "/status"),
        ("POST", "/dut/monitor"),
        ("POST", "/dut/interact"),
        ("POST", "/dut/uart/send"),
        ("POST", "/dut/reset"),
        ("POST", "/dut/boot-mode"),
        ("GET", "/dut/evidence"),
        ("GET", "/dut/logs"),
        ("GET", "/sessions"),
        ("GET", "/sessions/session-1"),
        ("POST", "/connection/release"),
        ("POST", "/connection/reacquire"),
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

    result = await server.call_tool("send_uart", {"text": "x" * 1025, "line_ending": "none"})

    assert isinstance(result, CallToolResult)
    assert result.result_type == "complete"
    assert result.is_error is True
    assert result.structured_content == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "UART send payload must contain 1..1024 bytes",
        "detail_truncated": False,
        "context": {"actual_bytes": 1025, "max_bytes": 1024},
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
    create_calls: list[tuple[str, str]] = []

    def fake_create_server(service_url: str, *, log_level: str) -> Mock:
        create_calls.append((service_url, log_level))
        return server

    monkeypatch.setattr(server_module, "create_server", fake_create_server)

    run_stdio(service_url="http://127.0.0.1:3040", log_level="DEBUG")

    assert create_calls == [("http://127.0.0.1:3040", "DEBUG")]
    server.run.assert_called_once_with("stdio")


def _client_factory(
    handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
) -> Callable[[], DeviceCoreClient]:
    return lambda: DeviceCoreClient(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    ("name", "arguments", "expected_kwargs"),
    [
        ("get_status", {}, {}),
        ("monitor", {"duration_s": 1}, {"duration_s": 1, "conditions": None, "timeout_s": None}),
        (
            "interact",
            {"data_b64": "AP8=", "duration_s": 1},
            {
                "data_b64": "AP8=",
                "text": None,
                "line_ending": None,
                "duration_s": 1,
                "conditions": None,
                "timeout_s": None,
            },
        ),
        (
            "send_uart",
            {"text": "INFO", "line_ending": "lf"},
            {"data_b64": None, "text": "INFO", "line_ending": "lf"},
        ),
        ("reset_dut", {}, {"pulse_ms": 100}),
        ("set_dut_boot_mode", {"mode": "bootloader"}, {"mode": "bootloader"}),
        (
            "get_evidence",
            {"cursor": "opaque+/=", "wait_s": 0},
            {"cursor": "opaque+/=", "limit": 100, "wait_s": 0},
        ),
        ("get_recent_logs", {"session_id": "s1"}, {"session_id": "s1", "lines": 300}),
        ("list_sessions", {"cursor": "opaque+/="}, {"cursor": "opaque+/=", "limit": 50}),
        ("get_session", {"session_id": "s1"}, {"session_id": "s1"}),
        ("release_connection", {}, {}),
        ("reacquire_connection", {}, {}),
    ],
)
async def test_each_tool_calls_its_corresponding_client_operation_once(
    name,
    arguments,
    expected_kwargs,
    monkeypatch,
):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    client = DeviceCoreClient(transport=httpx.MockTransport(handler))
    operation = AsyncMock(wraps=getattr(client, name))
    monkeypatch.setattr(client, name, operation)
    server = create_server(client_factory=lambda: client)
    result = await server.call_tool(name, arguments)

    operation.assert_awaited_once_with(**expected_kwargs)
    assert len(requests) == 1
    assert result.structured_content == {"ok": True}


@pytest.mark.parametrize("name", ["monitor", "interact"])
@pytest.mark.parametrize(
    "completion",
    [
        {"duration_s": 0.25},
        {
            "conditions": [{"pattern": "READY", "name": "ready"}, {"pattern": "FAIL"}],
            "timeout_s": 2.5,
        },
    ],
)
async def test_bounded_tools_forward_completion_requests_and_outcomes(name, completion):
    requests = []
    payload = {
        "ok": True,
        "operation_id": "op-1",
        "outcome": "timeout",
        "evidence_ranges": [
            {"session_id": "s1", "start_evidence_seq": 4, "end_evidence_seq_exclusive": 8}
        ],
        "start_cursor": {"session_id": "s1", "next_evidence_seq": 5},
        "end_cursor": {"session_id": "s1", "next_evidence_seq": 8},
    }

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    arguments = dict(completion)
    if name == "interact":
        arguments["data_b64"] = "AP8="
    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, arguments)
    assert json.loads(requests[0].content) == arguments
    assert result.is_error is False
    assert result.structured_content == payload


@pytest.mark.parametrize("name", ["send_uart", "interact"])
@pytest.mark.parametrize("line_ending", ["none", "lf", "cr", "crlf", "profile_default"])
@pytest.mark.parametrize("text", ["INFO", "null", "true", "[]", "{}", '"quoted"', "  λ\n"])
async def test_uart_text_and_explicit_endings_are_not_reinterpreted(name, line_ending, text):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "data_b64": "eA=="})

    arguments = {"text": text, "line_ending": line_ending}
    if name == "interact":
        arguments["duration_s"] = 1
    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, arguments)
    assert result.is_error is False
    assert len(requests) == 1
    assert json.loads(requests[0].content) == arguments


@pytest.mark.parametrize("name", ["send_uart", "interact"])
@pytest.mark.parametrize("retired", ["force", "cmd", "append_newline"])
async def test_retired_uart_arguments_are_rejected_without_dispatch(name, retired):
    async def handler(request):
        pytest.fail("retired argument reached Device Core")

    arguments = {"data_b64": "eA==", retired: True}
    if name == "interact":
        arguments["duration_s"] = 1
    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, arguments)
    assert result.is_error is True
    assert result.structured_content["error"] == "invalid_argument"


@pytest.mark.parametrize(
    "name",
    [
        "set_boot_mode",
        "capture_uart",
        "wait_for_uart_pattern",
        "run_boot_test",
        "send_uart_command",
        "get_recent_uart_log",
        "get_debug_session",
        "list_debug_sessions",
    ],
)
async def test_retired_tool_names_cannot_dispatch(name):
    from mcp.server.mcpserver.exceptions import ToolError

    async def handler(request):
        pytest.fail("retired tool reached Device Core")

    with pytest.raises(ToolError, match="Unknown tool"):
        await create_server(client_factory=_client_factory(handler)).call_tool(name, {})


@pytest.mark.parametrize("name", ["get_evidence", "list_sessions"])
@pytest.mark.parametrize("cursor", ["opaque+/=雪", "null", "true", "{}", "[]"])
async def test_cursor_strings_and_returned_pages_remain_opaque(name, cursor):
    requests = []
    payload = {"ok": True, "next_cursor": "opaque-next+/=", "records": [], "omitted_records": 1}
    if name == "list_sessions":
        payload = {
            "items": [{"session_id": "s1", "schema_version": 2}],
            "next_cursor": "opaque-next+/=",
        }

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    arguments = {"cursor": cursor}
    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, arguments)
    assert result.is_error is False
    assert dict(requests[0].url.params)["cursor"] == cursor
    assert result.structured_content == payload


@pytest.mark.parametrize(
    "name, state", [("release_connection", "released"), ("reacquire_connection", "connected")]
)
async def test_connection_tools_preserve_service_boundaries(name, state):
    requests = []
    payload = {"ok": True, "connection_state": state, "session_id": "s1", "segment_id": 2}

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=payload)

    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, {})
    assert len(requests) == 1 and requests[0].content == b""
    assert result.structured_content == payload


@pytest.mark.parametrize(
    "name, arguments",
    [
        ("monitor", {"duration_s": True}),
        ("monitor", {"conditions": [{"pattern": "OK"}]}),
        ("interact", {"text": "INFO", "duration_s": 1}),
        ("send_uart", {"text": "INFO"}),
        ("reset_dut", {"pulse_ms": True}),
        ("set_dut_boot_mode", {"mode": "helper"}),
        ("get_evidence", {"wait_s": 31}),
        ("list_sessions", {"limit": True}),
        ("get_session", {}),
        ("set_dut_boot_mode", {}),
    ],
)
async def test_invalid_tool_arguments_return_bounded_structured_errors(name, arguments):
    async def handler(request):
        pytest.fail("invalid arguments reached HTTP")

    result = await create_server(client_factory=_client_factory(handler)).call_tool(name, arguments)
    assert result.is_error is True
    assert result.structured_content["error"] == "invalid_argument"
    assert len(result.structured_content["detail"].encode()) <= 1024


async def test_public_schemas_expose_only_v2_parameters():
    listing = await create_server().list_tools()
    by_name = {tool.name: tool.input_schema for tool in listing}
    assert set(by_name["send_uart"]["properties"]) == {"data_b64", "text", "line_ending"}
    assert set(by_name["monitor"]["properties"]) == {"duration_s", "conditions", "timeout_s"}
    assert set(by_name["interact"]["properties"]) == {
        "data_b64",
        "text",
        "line_ending",
        "duration_s",
        "conditions",
        "timeout_s",
    }
    for schema in by_name.values():
        assert schema["additionalProperties"] is False
