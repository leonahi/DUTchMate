"""Stateless MCP server composition for the stdio delivery adapter."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import Annotated, Final, Literal, TypeAlias, cast

from mcp.server import CacheHint, MCPServer
from mcp.server.caching import CacheableMethod
from mcp.server.context import ServerRequestContext
from mcp.server.mcpserver import Context
from mcp.types import (
    LATEST_PROTOCOL_VERSION,
    CallToolResult,
    DiscoverResult,
    RequestParams,
    ServerCapabilities,
    TextContent,
    ToolsCapability,
)
from pydantic import ValidationError, WithJsonSchema

from dutchmate_core.diagnostics import project_diagnostic_detail
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
LogLevel: TypeAlias = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

PulseMsArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": 10_000}),
]
BootModeArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "string", "enum": ["normal", "bootloader"]}),
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
OptionalDurationArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema(
        {
            "anyOf": [
                {"type": "number", "exclusiveMinimum": 0, "maximum": 300},
                {"type": "null"},
            ]
        }
    ),
]
ConditionsArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema(
        {
            "anyOf": [
                {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 8,
                    "items": {
                        "type": "object",
                        "properties": {
                            "pattern": {"type": "string", "minLength": 1},
                            "name": {"anyOf": [{"type": "string"}, {"type": "null"}]},
                        },
                        "required": ["pattern"],
                    },
                },
                {"type": "null"},
            ]
        }
    ),
]
LineEndingArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"enum": ["none", "lf", "cr", "crlf", "profile_default", None]}),
]
EvidenceLimitArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": 500}),
]
EvidenceWaitArgument: TypeAlias = Annotated[
    object,
    WithJsonSchema({"type": "number", "minimum": 0, "maximum": 30}),
]


class _ExactArgumentsServer(MCPServer[object]):
    """Validate raw tool arguments without the SDK's JSON-string convenience parsing."""

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, object],
        context: Context[object, object] | None = None,
    ) -> CallToolResult:
        tool = self._tool_manager.get_tool(name)
        if tool is None:
            return cast(CallToolResult, await super().call_tool(name, arguments, context))
        try:
            validated = tool.fn_metadata.arg_model.model_validate(
                arguments,
                strict=True,
                extra="forbid",
            )
        except ValidationError:
            # SDK validation errors can embed the original payload. Keep tool diagnostics bounded.
            return _tool_result(
                _validation_error_payload(ValueError("Invalid MCP tool arguments")),
                is_error=True,
            )
        # Every registered handler is async, context-free, and returns a CallToolResult.
        # Reuse the SDK argument model while preserving exact text and opaque cursor strings.
        return cast(CallToolResult, await tool.fn(**validated.model_dump_one_level()))


def create_server(
    service_url: str = DEFAULT_SERVICE_URL,
    *,
    log_level: LogLevel = "INFO",
    client_factory: ClientFactory | None = None,
) -> MCPServer[object]:
    """Create one stateless MCP server with fixed protocol-facing metadata."""

    cache_hints: dict[CacheableMethod, CacheHint] = {
        "server/discover": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
        "tools/list": CacheHint(ttl_ms=CACHE_TTL_MS, scope="private"),
    }
    server = _ExactArgumentsServer(
        name=SERVER_NAME,
        title=SERVER_TITLE,
        description=SERVER_DESCRIPTION,
        instructions=SERVER_INSTRUCTIONS,
        version=SERVER_VERSION,
        tools=[],
        log_level=log_level,
        cache_hints=cache_hints,
    )
    # SDK 2 registers these handlers even for empty catalogs. Remove them so
    # the served methods agree with our tools-only discovery capabilities.
    for method in (
        "prompts/list",
        "prompts/get",
        "resources/list",
        "resources/templates/list",
        "resources/read",
        "subscriptions/listen",
    ):
        server._lowlevel_server._request_handlers.pop(method, None)
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
    async def get_status() -> CallToolResult:
        """Inspect DUT connection, profile, effective capabilities and active operations."""
        return await _execute(factory, lambda client: client.get_status())

    @server.tool()
    async def monitor(
        duration_s: OptionalDurationArgument = None,
        conditions: ConditionsArgument = None,
        timeout_s: OptionalDurationArgument = None,
    ) -> CallToolResult:
        """Observe UART for duration_s or 1..8 literal conditions with timeout_s."""
        return await _execute(
            factory,
            lambda client: client.monitor(
                duration_s=cast(float | None, duration_s),
                conditions=cast(Sequence[Mapping[str, object]] | None, conditions),
                timeout_s=cast(float | None, timeout_s),
            ),
        )

    @server.tool()
    async def interact(
        data_b64: OptionalStringArgument = None,
        text: OptionalStringArgument = None,
        line_ending: LineEndingArgument = None,
        duration_s: OptionalDurationArgument = None,
        conditions: ConditionsArgument = None,
        timeout_s: OptionalDurationArgument = None,
    ) -> CallToolResult:
        """Send exact bytes or explicitly terminated text, then observe with a finite bound."""
        return await _execute(
            factory,
            lambda client: client.interact(
                data_b64=cast(str | None, data_b64),
                text=cast(str | None, text),
                line_ending=cast(str | None, line_ending),
                duration_s=cast(float | None, duration_s),
                conditions=cast(Sequence[Mapping[str, object]] | None, conditions),
                timeout_s=cast(float | None, timeout_s),
            ),
        )

    @server.tool()
    async def send_uart(
        data_b64: OptionalStringArgument = None,
        text: OptionalStringArgument = None,
        line_ending: LineEndingArgument = None,
    ) -> CallToolResult:
        """Send audited exact base64 bytes or text with an explicit line ending; no RX window."""
        return await _execute(
            factory,
            lambda client: client.send_uart(
                data_b64=cast(str | None, data_b64),
                text=cast(str | None, text),
                line_ending=cast(str | None, line_ending),
            ),
        )

    @server.tool()
    async def reset_dut(pulse_ms: PulseMsArgument = 100) -> CallToolResult:
        """Pulse the configured DUT reset role for 1..10000 milliseconds."""
        return await _execute(
            factory, lambda client: client.reset_dut(pulse_ms=cast(int, pulse_ms))
        )

    @server.tool()
    async def set_dut_boot_mode(mode: BootModeArgument) -> CallToolResult:
        """Command the configured DUT boot role to normal or bootloader; no reset or observation."""
        return await _execute(
            factory, lambda client: client.set_dut_boot_mode(mode=cast(str, mode))
        )

    @server.tool()
    async def get_evidence(
        cursor: OptionalStringArgument = None,
        limit: EvidenceLimitArgument = 100,
        wait_s: EvidenceWaitArgument = 1.0,
    ) -> CallToolResult:
        """Read a bounded durable evidence page; omit cursor to attach at the current tail."""
        return await _execute(
            factory,
            lambda client: client.get_evidence(
                cursor=cast(str | None, cursor),
                limit=cast(int, limit),
                wait_s=cast(float, wait_s),
            ),
        )

    @server.tool()
    async def get_recent_logs(
        session_id: OptionalStringArgument = None,
        lines: LogLinesArgument = 300,
    ) -> CallToolResult:
        """Read bounded UART lines from an explicit or service-selected historical session."""
        return await _execute(
            factory,
            lambda client: client.get_recent_logs(
                session_id=cast(str | None, session_id),
                lines=cast(int, lines),
            ),
        )

    @server.tool()
    async def list_sessions(
        limit: SessionLimitArgument = 50,
        cursor: OptionalStringArgument = None,
    ) -> CallToolResult:
        """List a bounded session page, preserving the opaque service cursor."""
        return await _execute(
            factory,
            lambda client: client.list_sessions(
                limit=cast(int, limit),
                cursor=cast(str | None, cursor),
            ),
        )

    @server.tool()
    async def get_session(session_id: RequiredStringArgument) -> CallToolResult:
        """Inspect bounded session metadata, quality, segments and artifact references."""
        return await _execute(
            factory, lambda client: client.get_session(session_id=cast(str, session_id))
        )

    @server.tool()
    async def release_connection() -> CallToolResult:
        """Explicitly release service transport ownership for an external tool."""
        return await _execute(factory, lambda client: client.release_connection())

    @server.tool()
    async def reacquire_connection() -> CallToolResult:
        """Reacquire the released transport through the service and return its segment boundary."""
        return await _execute(factory, lambda client: client.reacquire_connection())

    for tool in server._tool_manager.list_tools():
        tool.parameters["additionalProperties"] = False
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
    detail, truncated = project_diagnostic_detail(fallback_code="invalid_argument", detail=str(exc))
    payload: dict[str, object] = {
        "ok": False,
        "error": "invalid_argument",
        "detail": detail,
        "detail_truncated": truncated,
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


def run_stdio(
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    log_level: LogLevel = "INFO",
) -> None:
    """Run the server over stdio; no other MCP transport is exposed."""

    create_server(service_url, log_level=log_level).run("stdio")
