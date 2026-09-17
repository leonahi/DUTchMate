from __future__ import annotations

from collections.abc import Callable, Coroutine

import anyio
import httpx
import pytest
from mcp.client import Client, ClientSession
from mcp.client._memory import InMemoryTransport
from mcp.server.context import CallNext, HandlerResult, ServerRequestContext
from mcp.shared.exceptions import MCPError
from mcp.types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
    UNSUPPORTED_PROTOCOL_VERSION,
    CallToolResult,
    Implementation,
)
from mcp.types.version import LATEST_HANDSHAKE_VERSION, LATEST_MODERN_VERSION

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
    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/dut/reset")
    ]

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
            await client.call_tool("capture_uart", {"duration_s": 10})

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
