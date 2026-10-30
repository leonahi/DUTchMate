from __future__ import annotations

import asyncio
import json
import sys
from collections.abc import Callable, Coroutine
from pathlib import Path
from threading import Event

import anyio
import httpx
import pytest
from mcp.client import Client, ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.client.stdio import StdioServerParameters, stdio_client
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp.types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    METHOD_NOT_FOUND,
    PROTOCOL_VERSION_META_KEY,
    UNSUPPORTED_PROTOCOL_VERSION,
    CallToolResult,
    Implementation,
)
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION
from mcp_service_fixture import ServiceFixture

from dutchmate_mcp_server.server import (
    CACHE_TTL_MS,
    SERVER_DESCRIPTION,
    SERVER_INSTRUCTIONS,
    SERVER_NAME,
    SERVER_TITLE,
    SERVER_VERSION,
    create_server,
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


async def test_modern_stream_client_discovers_lists_and_calls_tools() -> None:
    requests: list[httpx.Request] = []
    observations: list[tuple[str, str, dict[str, object] | None, object]] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "pulse_ms": 100})

    async def record_request(
        ctx: ServerRequestContext[object, object],
        call_next: CallNext,
    ) -> HandlerResult:
        observations.append(
            (
                ctx.method,
                ctx.protocol_version,
                dict(ctx.meta) if ctx.meta is not None else None,
                ctx.request,
            )
        )
        return await call_next(ctx)

    server = create_server(client_factory=_client_factory(handler))
    server.middleware.append(record_request)
    client_info = Implementation(name="dutchmate-integration-test", version="1.0.0")

    async with Client(
        InMemoryTransport(server),
        mode="auto",
        client_info=client_info,
        cache=None,
    ) as client:
        discover = client.session.discover_result
        assert discover is not None
        assert client.session.initialize_result is None
        assert client.protocol_version == LATEST_MODERN_VERSION
        assert discover.supported_versions == [LATEST_MODERN_VERSION]
        assert discover.result_type == "complete"
        assert discover.ttl_ms == CACHE_TTL_MS
        assert discover.cache_scope == "private"
        assert discover.instructions == SERVER_INSTRUCTIONS
        assert discover.capabilities.tools is not None
        assert discover.capabilities.tools.list_changed is False
        assert discover.capabilities.prompts is None
        assert discover.capabilities.resources is None
        assert client.server_info == Implementation(
            name=SERVER_NAME,
            title=SERVER_TITLE,
            description=SERVER_DESCRIPTION,
            version=SERVER_VERSION,
        )

        first_listing = await client.list_tools()
        second_listing = await client.list_tools()
        result = await client.call_tool("reset_dut", {})

    assert [tool.name for tool in first_listing.tools] == EXPECTED_TOOL_NAMES
    assert [tool.name for tool in second_listing.tools] == EXPECTED_TOOL_NAMES
    assert first_listing.result_type == "complete"
    assert first_listing.ttl_ms == CACHE_TTL_MS
    assert first_listing.cache_scope == "private"
    assert isinstance(result, CallToolResult)
    assert result.result_type == "complete"
    assert result.is_error is False
    assert result.structured_content == {"ok": True, "pulse_ms": 100}
    assert [(request.method, request.url.path) for request in requests] == [("POST", "/dut/reset")]

    request_observations = [item for item in observations if item[0] != "notifications/cancelled"]
    assert [item[0] for item in request_observations] == [
        "server/discover",
        "tools/list",
        "tools/list",
        "tools/call",
    ]
    for _, protocol_version, meta, transport_request in request_observations:
        assert protocol_version == LATEST_MODERN_VERSION
        assert transport_request is None
        assert meta is not None
        assert meta[PROTOCOL_VERSION_META_KEY] == LATEST_MODERN_VERSION
        assert meta[CLIENT_INFO_META_KEY] == {
            "name": "dutchmate-integration-test",
            "version": "1.0.0",
        }
        assert meta[CLIENT_CAPABILITIES_META_KEY] == {}


async def test_modern_stream_client_rejects_unsupported_protocol_version() -> None:
    server = create_server()

    async with (
        InMemoryTransport(server) as (read_stream, write_stream),
        ClientSession(read_stream, write_stream) as session,
    ):
        with pytest.raises(MCPError) as raised:
            await session.send_discover("2099-01-01")

    assert raised.value.code == UNSUPPORTED_PROTOCOL_VERSION
    assert raised.value.error.data == {
        "supported": [LATEST_MODERN_VERSION],
        "requested": "2099-01-01",
    }


@pytest.mark.parametrize("method", ["prompts/list", "resources/list"])
async def test_modern_stream_rejects_unadvertised_capabilities(method: str) -> None:
    server = create_server()

    async with Client(InMemoryTransport(server), mode="auto", cache=None) as client:
        with pytest.raises(MCPError) as raised:
            if method == "prompts/list":
                await client.session.list_prompts()
            else:
                await client.session.list_resources()

    assert raised.value.code == METHOD_NOT_FOUND


async def test_modern_stream_client_cancellation_stops_the_tool_call() -> None:
    request_started = anyio.Event()
    request_stopped = anyio.Event()
    cancel_scope_ready = anyio.Event()
    cancelled_methods: list[str] = []
    call_scope: anyio.CancelScope | None = None

    async def handler(request: httpx.Request) -> httpx.Response:
        request_started.set()
        try:
            await anyio.sleep_forever()
        finally:
            request_stopped.set()

    async def record_request(
        ctx: ServerRequestContext[object, object],
        call_next: CallNext,
    ) -> HandlerResult:
        if ctx.method == "notifications/cancelled":
            cancelled_methods.append(ctx.method)
        return await call_next(ctx)

    async def call_tool(client: Client) -> None:
        nonlocal call_scope
        with anyio.CancelScope() as scope:
            call_scope = scope
            cancel_scope_ready.set()
            await client.call_tool("monitor", {"duration_s": 10})

    server = create_server(client_factory=_client_factory(handler))
    server.middleware.append(record_request)

    async with (
        Client(InMemoryTransport(server), mode="auto", cache=None) as client,
        anyio.create_task_group() as task_group,
    ):
        task_group.start_soon(call_tool, client)
        await cancel_scope_ready.wait()
        await request_started.wait()
        assert call_scope is not None
        call_scope.cancel()
        with anyio.fail_after(1):
            await request_stopped.wait()

    assert cancelled_methods == ["notifications/cancelled"]


async def test_stream_transport_shuts_down_cleanly_on_client_eof() -> None:
    server = create_server()

    with anyio.fail_after(1):
        async with Client(InMemoryTransport(server), mode="auto", cache=None) as client:
            assert client.protocol_version == LATEST_MODERN_VERSION


async def test_installed_cli_serves_modern_stdio_without_service_or_venv_path() -> None:
    executable = Path(sys.executable).with_name("dutchmate")
    parameters = StdioServerParameters(
        command=str(executable),
        args=["mcp", "--service-url", "http://127.0.0.1:0"],
        env={"PATH": "/usr/bin:/bin"},
    )

    with anyio.fail_after(10):
        async with Client(stdio_client(parameters), mode="auto", cache=None) as client:
            assert client.protocol_version == LATEST_MODERN_VERSION
            listing = await client.list_tools()
            assert [tool.name for tool in listing.tools] == EXPECTED_TOOL_NAMES

            result = await client.call_tool("get_recent_logs", {})
            assert result.result_type == "complete"
            assert result.is_error is True
            assert result.structured_content is not None
            assert result.structured_content["error"] == "service_unavailable"


async def test_sdk_legacy_compatibility_path_lists_the_same_tools() -> None:
    server = create_server()

    async with Client(InMemoryTransport(server), mode="legacy", cache=None) as client:
        listing = await client.list_tools()

        assert client.protocol_version == LATEST_HANDSHAKE_VERSION
        assert client.session.discover_result is None
        assert client.session.initialize_result is not None
        assert [tool.name for tool in listing.tools] == EXPECTED_TOOL_NAMES


def _client_factory(
    handler: Callable[[httpx.Request], Coroutine[None, None, httpx.Response]],
) -> Callable[[], DeviceCoreClient]:
    return lambda: DeviceCoreClient(transport=httpx.MockTransport(handler))


@pytest.mark.parametrize(
    "name, arguments, method, path",
    [
        ("monitor", {"conditions": [{"pattern": "READY"}], "timeout_s": 1}, "POST", "/dut/monitor"),
        (
            "interact",
            {"text": "null", "line_ending": "none", "duration_s": 1},
            "POST",
            "/dut/interact",
        ),
        ("send_uart", {"text": "{}", "line_ending": "none"}, "POST", "/dut/uart/send"),
        ("get_evidence", {"cursor": "null", "wait_s": 0}, "GET", "/dut/evidence"),
        ("list_sessions", {"cursor": "[]"}, "GET", "/sessions"),
        ("get_session", {"session_id": "null"}, "GET", "/sessions/null"),
    ],
)
async def test_modern_tools_preserve_v2_arguments_on_the_wire(name, arguments, method, path):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True, "operation_id": "service-op"})

    server = create_server(client_factory=_client_factory(handler))
    async with Client(InMemoryTransport(server), mode="auto", cache=None) as client:
        result = await client.call_tool(name, arguments)
    assert result.is_error is False
    assert result.result_type == "complete"
    assert result.structured_content == {"ok": True, "operation_id": "service-op"}
    assert len(requests) == 1
    assert (requests[0].method, requests[0].url.path) == (method, path)
    if method == "POST":
        assert json.loads(requests[0].content) == arguments
    elif "cursor" in arguments:
        assert dict(requests[0].url.params)["cursor"] == arguments["cursor"]


@pytest.mark.parametrize("retired", ["force", "cmd", "append_newline"])
async def test_modern_tools_reject_retired_arguments_as_bounded_tool_errors(retired):
    async def handler(request):
        pytest.fail("invalid tool request reached Device Core")

    server = create_server(client_factory=_client_factory(handler))
    async with Client(InMemoryTransport(server), mode="auto", cache=None) as client:
        result = await client.call_tool("send_uart", {"data_b64": "eA==", retired: "x" * 10000})
    assert result.is_error is True
    assert result.structured_content == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Invalid MCP tool arguments",
        "detail_truncated": False,
    }


@pytest.fixture
def service_factory(tmp_path):
    services = []

    def build(**options):
        service = ServiceFixture(tmp_path / f"service-{len(services)}", **options)
        services.append(service)
        return service

    yield build
    for service in reversed(services):
        service.close()


async def service_call(service, client, name, arguments=None, *, status=200):
    """Compare MCP to the actual ASGI response, before the MCP client's projection."""
    before = len(service.transport.responses)
    result = await client.call_tool(name, arguments or {})
    assert len(service.transport.responses) == before + 1
    _, actual_status, payload = service.transport.responses[-1]
    assert actual_status == status
    assert result.result_type == "complete"
    assert result.is_error is (status >= 400)
    assert result.structured_content == payload
    assert json.loads(result.content[0].text) == payload
    return payload


def assert_operation_projection(payload, outcome):
    assert payload["outcome"] == outcome
    assert payload["operation_id"]
    assert payload["start_cursor"]["session_id"]
    assert payload["end_cursor"]["session_id"]
    assert payload["evidence_ranges"]
    for window in payload["evidence_ranges"]:
        assert window["start_evidence_seq"] < window["end_evidence_seq_exclusive"]
    assert payload["integrity"]["observation_scope"] == "debug_helper_rx_buffer"
    assert payload["timestamp_provenance"][0]["segment"]["timestamp"]["source"] == "device"
    assert "matched_condition" in payload and "line_processing_limited" in payload


async def test_actual_service_twelve_tools_share_real_v2_evidence_and_ownership(service_factory):
    service = service_factory()
    session = service.session
    service.publish(b"before attachment\xff\n")
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        assert [tool.name for tool in (await client.list_tools()).tools] == EXPECTED_TOOL_NAMES
        status = await service_call(service, client, "get_status")
        assert status["active_session_id"] == session
        assert status["connection_state"] == "connected"
        assert "uart_send" in status["capabilities"]
        assert status["profile_digest_sha256"] == service.profile.digest_sha256

        attached = await service_call(service, client, "get_evidence", {"wait_s": 0})
        assert attached["records"] == [] and attached["omitted_records"] == 0
        cursor = attached["next_cursor"]
        assert isinstance(cursor, str) and cursor
        elapsed = await service_call(service, client, "monitor", {"duration_s": 0.01})
        assert_operation_projection(elapsed, "elapsed")
        assert elapsed["matched_condition"] is None

        service.physical.on_send = lambda: service.publish(b"asynchronous log\nREADY\n", 30)
        interaction = await service_call(
            service,
            client,
            "interact",
            {
                "text": "null",
                "line_ending": "profile_default",
                "conditions": [{"pattern": "READY", "name": "ready"}],
                "timeout_s": 1,
            },
        )
        assert_operation_projection(interaction, "matched")
        assert interaction["matched_condition"]["excerpt"]["raw_b64"] == "UkVBRFkK"
        assert interaction["data_b64"] == "bnVsbA0K"
        assert interaction["transformation"] == {
            "input_form": "text",
            "line_ending": "profile_default",
            "resolved_line_ending": "crlf",
        }
        assert interaction["tx"]["accepted_bytes"] == 6
        assert interaction["tx"]["audit_status"] == "recorded"
        assert interaction["tx_error"] is None
        service.physical.on_send = lambda: None
        sent = await service_call(service, client, "send_uart", {"data_b64": "AP8="})
        assert sent["data_b64"] == "AP8=" and sent["accepted_bytes"] == 2
        assert sent["attempt_evidence_seq"] < sent["result_evidence_seq"]
        assert service.physical.tx == [b"null\r\n", b"\x00\xff"]

        boot = await service_call(service, client, "set_dut_boot_mode", {"mode": "bootloader"})
        assert boot["mode"] == "bootloader" and boot["performed_at"]
        reset = await service_call(service, client, "reset_dut", {"pulse_ms": 5})
        assert reset["pulse_ms"] == 5 and reset["device_timestamp_us"] is not None
        assert service.physical.controls[-2:] == [
            ("set_control_state", {"channel": "CTRL1", "state": "active"}),
            ("pulse_control", {"channel": "CTRL0", "pulse_ms": 5}),
        ]
        page = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": cursor,
                "limit": 500,
                "wait_s": 0,
            },
        )
        assert page["records"] and page["omitted_records"] == 0
        assert any(
            r["type"] == "uart_rx" and r["data_b64"] == "YXN5bmNocm9ub3VzIGxvZwpSRUFEWQo="
            for r in page["records"]
        )
        logs = await service_call(
            service, client, "get_recent_logs", {"session_id": session, "lines": 1}
        )
        assert logs["session_id"] == session and logs["schema_version"] == 2
        assert logs["complete_lines"][-1]["line_raw_b64"] == "UkVBRFkK"
        assert "response_truncated" in logs and "omitted_complete_lines" in logs
        listing = await service_call(service, client, "list_sessions", {"limit": 1})
        assert listing["items"][0]["session_id"] == session
        assert listing["items"][0]["schema_version"] == 2
        detail = await service_call(service, client, "get_session", {"session_id": session})
        assert detail["operation_counts"]["started"] == 2
        assert detail["evidence_quality"]["backend_integrity"]["loss_status"] == "none_reported"
        assert detail["effective_profile"] == service.profile.projection()
        assert len(detail["segments"]) == 1

        released = await service_call(service, client, "release_connection")
        assert released == {
            "ok": True,
            "connection_state": "released",
            "session_id": session,
            "segment_id": 0,
        }
        assert service.sources[0].closed
        resumed = await service_call(service, client, "reacquire_connection")
        assert resumed == {
            "ok": True,
            "connection_state": "connected",
            "session_id": session,
            "segment_id": 1,
        }
        service.publish(b"after gap\n", 1)
        detail = await service_call(service, client, "get_session", {"session_id": session})
        assert detail["continuity"]["observation_gap_count"] == 1
        assert [segment["segment_id"] for segment in detail["segments"]] == [0, 1]
        assert detail["segments"][0]["end_reason"] == "released"
        boundary = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": page["next_cursor"],
                "wait_s": 0,
            },
        )
        kinds = [r["type"] for r in boundary["records"]]
        assert kinds.index("released") < kinds.index("reacquire_succeeded")
        assert any(r["type"] == "uart_rx" and r["segment_id"] == 1 for r in boundary["records"])
        assert all(source.max_concurrent_reads == 1 for source in service.sources)
        assert {request.url.path for request in service.transport.requests} == {
            "/status",
            "/dut/monitor",
            "/dut/interact",
            "/dut/uart/send",
            "/dut/reset",
            "/dut/boot-mode",
            "/dut/evidence",
            "/dut/logs",
            "/sessions",
            f"/sessions/{session}",
            "/connection/release",
            "/connection/reacquire",
        }
    # MCP EOF does not terminate service ownership or ambient acquisition.
    assert service.runtime.status().connected and not service.source.closed
    service.publish(b"after MCP EOF\n", 50)
    assert b"after MCP EOF\n" in (service.store.root / session / "uart_raw.log").read_bytes()


async def test_actual_service_monitor_match_and_normal_timeout(service_factory, monkeypatch):
    service = service_factory()
    started = Event()
    original = service.recorder.start_monitor_operation

    def start(**kwargs):
        result = original(**kwargs)
        started.set()
        return result

    monkeypatch.setattr(service.recorder, "start_monitor_operation", start)
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        pending = asyncio.create_task(
            service_call(
                service,
                client,
                "monitor",
                {
                    "conditions": [{"pattern": "READY", "name": "ready"}],
                    "timeout_s": 2,
                },
            )
        )
        assert await asyncio.to_thread(started.wait, 2)
        service.publish(b"ambient\nREADY\n")
        matched = await pending
        assert_operation_projection(matched, "matched")
        assert matched["matched_condition"]["condition"] == {"pattern": "READY", "name": "ready"}
        assert matched["matched_condition"]["excerpt"]["raw_b64"] == "UkVBRFkK"
        timed_out = await service_call(
            service,
            client,
            "monitor",
            {
                "conditions": [{"pattern": "NEVER"}],
                "timeout_s": 0.01,
            },
        )
        assert_operation_projection(timed_out, "timeout")
        assert timed_out["matched_condition"] is None
        interaction = await service_call(
            service,
            client,
            "interact",
            {
                "data_b64": "AP8=",
                "conditions": [{"pattern": "NEVER"}],
                "timeout_s": 0.01,
            },
        )
        assert_operation_projection(interaction, "timeout")
        assert interaction["tx"]["data_b64"] == "AP8=" and interaction["tx_error"] is None
        assert service.physical.tx == [b"\x00\xff"]


async def test_actual_service_interact_unknown_tx_is_not_retried(service_factory):
    from dutchmate_core.backends import BackendDisconnectedError, BackendWriteError

    service = service_factory()

    def disconnect_before_ack():
        service.source.publish(BackendDisconnectedError("test transport lost"))
        assert service.recorder.wait_for_disconnect(timeout_s=2)

    service.physical.on_send = disconnect_before_ack
    service.physical.write_failure = BackendWriteError(
        "test ACK lost",
        error="timeout",
        bytes_accepted=None,
    )
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        interaction = await service_call(
            service,
            client,
            "interact",
            {
                "data_b64": "eA==",
                "duration_s": 0.05,
            },
        )
        assert_operation_projection(interaction, "disconnected")
        assert interaction["tx"] is None
        assert interaction["tx_error"]["code"] == "timeout"
        assert interaction["tx_error"]["context"]["bytes_accepted"] is None
        assert interaction["data_b64"] == "eA=="
        assert service.physical.tx == [b"x"]
        records = service.records()
        assert sum(r["type"] == "uart_tx_attempt" for r in records) == 1
        assert sum(r["type"] == "uart_tx_result" for r in records) == 1


async def test_actual_service_evidence_pages_keep_exact_bytes_and_public_cursors(service_factory):
    service = service_factory()
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        attached = await service_call(service, client, "get_evidence", {"wait_s": 0})
        service.publish(b"\x00\xffRAW\n")
        service.publish(b"second\n", 21)
        first = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": attached["next_cursor"],
                "limit": 1,
                "wait_s": 0,
            },
        )
        assert len(first["records"]) == 1 and first["omitted_records"] == 0
        assert first["records"][0]["data_b64"] == "AP9SQVcK"
        assert first["next_cursor"] != attached["next_cursor"]
        second = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": first["next_cursor"],
                "limit": 1,
                "wait_s": 0,
            },
        )
        assert len(second["records"]) == 1 and second["records"][0]["data_b64"] == "c2Vjb25kCg=="
        assert second["records"][0]["evidence_seq"] > first["records"][0]["evidence_seq"]
        logs = await service_call(
            service,
            client,
            "get_recent_logs",
            {
                "session_id": service.session,
                "lines": 2,
            },
        )
        assert logs["session_id"] == service.session
        assert logs["complete_lines"][0]["line_raw_b64"] == "AP9SQVcK"
        invalid = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": "invalid-public-cursor",
                "wait_s": 0,
            },
            status=400,
        )
        assert invalid["error"] == "invalid_argument"
        assert invalid["detail_truncated"] is False


async def test_actual_service_expired_cursor_and_v2_session_pagination(service_factory):
    from dutchmate_core.backends import BackendDisconnectedError

    service = service_factory()
    old_session = service.session
    service.publish(b"old evidence\n")
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        service.source.publish(BackendDisconnectedError("test unplug"))
        assert await asyncio.to_thread(service.recorder.wait_for_disconnect, timeout_s=2)
        service.recorder.close_current_source_for_reconnect()
        service.recorder.reconnect_timed_out()
        terminal_tail = await service_call(service, client, "get_evidence", {"wait_s": 0})
        resumed = await service_call(service, client, "reacquire_connection")
        assert resumed["session_id"] != old_session
        expired = await service_call(
            service,
            client,
            "get_evidence",
            {
                "cursor": terminal_tail["next_cursor"],
                "wait_s": 0,
            },
            status=410,
        )
        assert expired["error"] == "cursor_expired" and expired["context"] == {}
        first = await service_call(service, client, "list_sessions", {"limit": 1})
        assert len(first["items"]) == 1 and isinstance(first["next_cursor"], str)
        second = await service_call(
            service,
            client,
            "list_sessions",
            {
                "limit": 1,
                "cursor": first["next_cursor"],
            },
        )
        assert len(second["items"]) == 1
        assert {first["items"][0]["session_id"], second["items"][0]["session_id"]} == {
            old_session,
            resumed["session_id"],
        }
        assert first["items"][0]["schema_version"] == second["items"][0]["schema_version"] == 2
        old = await service_call(service, client, "get_session", {"session_id": old_session})
        assert old["state"] == "failed"
        logs = await service_call(service, client, "get_recent_logs", {"session_id": old_session})
        assert logs["session_id"] == old_session
        assert logs["complete_lines"][0]["line_raw_b64"] == "b2xkIGV2aWRlbmNlCg=="


@pytest.mark.parametrize(
    "options, tool, arguments, code, context_field, context_value",
    [
        ({"configured": False}, "reset_dut", {}, "not_configured", "required_role", "reset"),
        (
            {"gpio_capable": False},
            "reset_dut",
            {},
            "unsupported_capability",
            "backend_mode",
            "enhanced",
        ),
        (
            {"tx_enabled": False},
            "send_uart",
            {"data_b64": "eA=="},
            "unsupported_capability",
            "disabled_by_policy",
            ["hardware.uart.tx_enabled"],
        ),
    ],
)
async def test_actual_service_preserves_role_capability_and_policy_errors(
    service_factory,
    options,
    tool,
    arguments,
    code,
    context_field,
    context_value,
):
    service = service_factory(**options)
    controls_before = len(service.physical.controls)
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        error = await service_call(service, client, tool, arguments, status=409)
        assert error["error"] == code
        assert error["context"][context_field] == context_value
        assert error["detail_truncated"] is False and 0 < len(error["detail"].encode()) <= 1024
        assert len(service.physical.controls) == controls_before and service.physical.tx == []


async def test_actual_service_invalid_connection_state_is_not_retried(service_factory):
    service = service_factory()
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        error = await service_call(service, client, "reacquire_connection", status=409)
        assert error["error"] == "invalid_connection_state"
        assert len(service.sources) == 1
        await service_call(service, client, "release_connection")
        error = await service_call(service, client, "release_connection", status=409)
        assert error["error"] == "invalid_connection_state"
        assert len(service.sources) == 1


async def test_actual_service_projects_injected_runtime_session_state_failure(
    service_factory, monkeypatch
):
    service = service_factory()
    # None of the twelve read/control tools naturally calls the baseline state gate.
    # Inject that real store failure at the test-owned runtime boundary, keeping
    # the actual route, exception handler, HTTP client and MCP projection intact.
    monkeypatch.setattr(service.runtime, "get_session", service.runtime.mark_baseline)
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        error = await service_call(
            service, client, "get_session", {"session_id": service.session}, status=409
        )
        assert error["error"] == "invalid_session_state"
        assert error["context"]["session_id"] == service.session
        assert error["context"]["operation"] == "mark_baseline"
        assert not (service.store.root / "baseline.json").exists()


async def test_actual_service_truncates_backend_diagnostics_and_preserves_context(service_factory):
    from dutchmate_core.backends import DeviceControlError

    service = service_factory()
    service.physical.control_failure = DeviceControlError(
        error="hardware_fault",
        detail="driver\n" + "λ" * 2000,
    )
    before = len(service.physical.controls)
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        error = await service_call(service, client, "reset_dut", status=502)
        assert error["error"] == "hardware_fault" and error["detail_truncated"] is True
        assert 0 < len(error["detail"].encode()) <= 1024 and "\n" not in error["detail"]
        assert len(service.physical.controls) == before + 1


async def test_actual_service_cancellation_keeps_dispatched_tx_and_releases_exclusivity(
    service_factory,
):
    service = service_factory()
    cancel_ready = anyio.Event()
    cancelled = anyio.Event()
    scope = None

    async def pending_interact(client):
        nonlocal scope
        with anyio.CancelScope() as scope:
            cancel_ready.set()
            await client.call_tool("interact", {"data_b64": "eA==", "duration_s": 30})

    async def record_cancel(ctx, call_next):
        if ctx.method == "notifications/cancelled":
            cancelled.set()
        return await call_next(ctx)

    service.server.middleware.append(record_cancel)
    async with Client(InMemoryTransport(service.server), mode="auto", cache=None) as client:
        async with anyio.create_task_group() as group:
            group.start_soon(pending_interact, client)
            await cancel_ready.wait()
            assert await asyncio.to_thread(service.physical.sent.wait, 2)
            with service.runtime._operation_lock:
                operation = next(iter(service.runtime._active_monitors.values()))
            conflict = await service_call(
                service, client, "send_uart", {"data_b64": "eQ=="}, status=409
            )
            assert conflict["error"] == "operation_active"
            assert service.physical.tx == [b"x"]
            scope.cancel()
            with anyio.fail_after(2):
                await cancelled.wait()
                assert await asyncio.to_thread(operation.completed.wait, 2)
        terminals = [r for r in service.records() if r["type"] == "operation_terminal"]
        assert terminals[-1]["outcome"] == "cancelled"
        assert terminals[-1]["operation_id"] == operation.operation_id
        tx = [r for r in service.records() if r["type"] == "uart_tx_attempt"]
        assert len(tx) == 1 and tx[0]["data_b64"] == "eA=="
        tx_results = [r for r in service.records() if r["type"] == "uart_tx_result"]
        assert len(tx_results) == 1
        assert tx_results[0]["status"] == "success" and tx_results[0]["accepted_bytes"] == 1
        sent = await service_call(service, client, "send_uart", {"data_b64": "eg=="})
        assert sent["audit_status"] == "recorded"
        assert service.physical.tx == [b"x", b"z"]
        assert service.runtime.status().active_operations == ()
    # EOF is protocol cleanup, not service shutdown or action rollback.
    assert service.runtime.status().connected and not service.source.closed
