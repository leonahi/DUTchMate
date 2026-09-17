"""Stateless MCP server composition for the stdio delivery adapter."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable
from typing import Annotated, Final, TypeAlias, cast

from mcp.server import CacheHint, MCPServer
from mcp.server.caching import CacheableMethod
from mcp.server.context import ServerRequestContext
from mcp.types import (
    LATEST_PROTOCOL_VERSION,
    CallToolResult,
    DiscoverResult,
    RequestParams,
    ServerCapabilities,
    TextContent,
    ToolsCapability,
)
from pydantic import WithJsonSchema

from dutchmate_core.validation import UartSendValidationError
from dutchmate_mcp_server.service_client import (
    DEFAULT_SERVICE_URL,
    DeviceCoreClient,
    DeviceCoreProtocolError,
    DeviceCoreServiceError,
    DeviceCoreUnavailableError,
)

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

ClientFactory: TypeAlias = Callable[[], DeviceCoreClient]
ClientOperation: TypeAlias = Callable[[DeviceCoreClient], Awaitable[dict[str, object]]]

PulseMsArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": 10_000}),
]
BootModeArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "string", "enum": ["normal", "bootloader"]}),
]
DurationArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "number", "exclusiveMinimum": 0, "maximum": 300}),
]
LogLinesArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": 1000}),
]
SessionLimitArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": 100}),
]
RequiredStringArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "string"}),
]
OptionalStringArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"anyOf": [{"type": "string"}, {"type": "null"}]}),
]
BooleanArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "boolean"}),
]


def create_server(
    service_url: str = DEFAULT_SERVICE_URL,
    *,
    client_factory: ClientFactory | None = None,
) -> MCPServer[object]:
    """Create one stateless MCP server with fixed protocol-facing metadata."""

    cache_hints: dict[CacheableMethod, CacheHint] = {
        "server/discover": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
        "tools/list": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
    }
    server = MCPServer[object](
        name=SERVER_NAME,
        title=SERVER_TITLE,
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
        version=SERVER_VERSION,
        tools=[],
        cache_hints=cache_hints,
    )
    factory = client_factory or (lambda: DeviceCoreClient(service_url))

    async def discover(
        ctx: ServerRequestContext[object, object],
        params: RequestParams | None,
    ) -> DiscoverResult:
        del ctx, params
        return DiscoverResult(
            supported_versions=[LATEST_PROTOCOL_VERSION],
            capabilities=ServerCapabilities(tools=ToolsCapability(list_changed=False)),
            instructions=SERVER_INSTRUCTIONS,
        )

    server._lowlevel_server.add_request_handler(
        "server/discover",
        RequestParams,
        discover,
    )

    @server.tool()
    async def reset_dut(pulse_ms: PulseMsArgument = 100) -> CallToolResult:
        """Pulse the configured DUT reset control for 1..10000 milliseconds."""

        return await _execute(
            factory,
            lambda client: client.reset_dut(pulse_ms=cast(int, pulse_ms)),
        )

    @server.tool()
    async def set_boot_mode(mode: BootModeArgument) -> CallToolResult:
        """Command the configured DUT boot role to normal or bootloader mode."""

        return await _execute(
            factory,
            lambda client: client.set_boot_mode(mode=cast(str, mode)),
        )

    @server.tool()
    async def capture_uart(duration_s: DurationArgument) -> CallToolResult:
        """Capture bounded UART evidence for the requested duration in seconds."""

        return await _execute(
            factory,
            lambda client: client.capture_uart(duration_s=cast(float, duration_s)),
        )

    @server.tool()
    async def get_recent_uart_log(
        lines: LogLinesArgument = 300,
        session_id: OptionalStringArgument = None,
    ) -> CallToolResult:
        """Read bounded recent UART lines from an explicit or selected session."""

        return await _execute(
            factory,
            lambda client: client.get_recent_uart_log(
                lines=cast(int, lines),
                session_id=cast(str | None, session_id),
            ),
        )

    @server.tool()
    async def wait_for_uart_pattern(
        pattern: RequiredStringArgument,
        timeout_s: DurationArgument,
    ) -> CallToolResult:
        """Wait for a case-sensitive literal in new complete UART lines."""

        return await _execute(
            factory,
            lambda client: client.wait_for_uart_pattern(
                pattern=cast(str, pattern),
                timeout_s=cast(float, timeout_s),
            ),
        )

    @server.tool()
    async def run_boot_test(duration_s: DurationArgument) -> CallToolResult:
        """Reset the DUT and capture bounded boot evidence in its current boot mode."""

        return await _execute(
            factory,
            lambda client: client.run_boot_test(duration_s=cast(float, duration_s)),
        )

    @server.tool()
    async def send_uart_command(
        cmd: RequiredStringArgument,
        append_newline: BooleanArgument = True,
        force: BooleanArgument = False,
    ) -> CallToolResult:
        """Send one bounded UTF-8 command through the configured UART backend."""

        return await _execute(
            factory,
            lambda client: client.send_uart_command(
                cmd=cast(str, cmd),
                append_newline=cast(bool, append_newline),
                force=cast(bool, force),
            ),
        )

    @server.tool()
    async def get_debug_session(session_id: RequiredStringArgument) -> CallToolResult:
        """Get bounded lifecycle metadata for one explicit debug session."""

        return await _execute(
            factory,
            lambda client: client.get_debug_session(cast(str, session_id)),
        )

    @server.tool()
    async def list_debug_sessions(
        limit: SessionLimitArgument = 50,
        cursor: OptionalStringArgument = None,
    ) -> CallToolResult:
        """List a bounded page of debug-session summaries."""

        return await _execute(
            factory,
            lambda client: client.list_debug_sessions(
                limit=cast(int, limit),
                cursor=cast(str | None, cursor),
            ),
        )

    return server


async def _execute(factory: ClientFactory, operation: ClientOperation) -> CallToolResult:
    try:
        async with factory() as client:
            payload = await operation(client)
    except UartSendValidationError as exc:
        context: dict[str, object] | None = None
        if exc.actual_bytes is not None:
            context = {
                "actual_bytes": exc.actual_bytes,
                "max_bytes": exc.max_bytes,
            }
        return _tool_result(_validation_error_payload(exc, context=context), is_error=True)
    except ValueError as exc:
        return _tool_result(_validation_error_payload(exc), is_error=True)
    except (DeviceCoreServiceError, DeviceCoreUnavailableError) as exc:
        return _tool_result(exc.payload(), is_error=True)
    except DeviceCoreProtocolError as exc:
        return _tool_result(
            {
                "ok": False,
                "error": "service_protocol_error",
                "detail": str(exc),
                "detail_truncated": False,
            },
            is_error=True,
        )
    return _tool_result(payload)


def _validation_error_payload(
    exc: ValueError,
    *,
    context: dict[str, object] | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "ok": False,
        "error": "invalid_argument",
        "detail": str(exc),
        "detail_truncated": False,
    }
    if context is not None:
        payload["context"] = context
    return payload


def _tool_result(payload: dict[str, object], *, is_error: bool = False) -> CallToolResult:
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return CallToolResult(
        content=[TextContent(type="text", text=text)],
        structured_content=payload,
        is_error=is_error,
    )


def run_stdio() -> None:
    """Run the server over stdio; no other MCP transport is exposed."""

    create_server().run("stdio")
