# MCP Integration Plan

> Status: draft decision
> Scope: Phase 2 MCP server transport, launch model, and tool contract.

## Decision Summary

Phase 2 uses **MCP stdio transport as the default**.

The MCP server is launched by the coding agent as a subprocess and communicates MCP JSON-RPC over stdin/stdout. The MCP server does not own hardware and does not open the serial port. It calls the already-running Device Core Service over local HTTP at `http://localhost:2040` by default.

Streamable HTTP can be added later for clients that need an independently hosted MCP endpoint. The deprecated HTTP+SSE MCP transport is not the Phase 2 default.

## Process Model

```text
Coding Agent / IDE Agent
        |
        | MCP stdio
        v
MCP Server process (`dutchmate mcp`)
        |
        | HTTP Device Core Service API
        v
Device Core Service (`dutchmate start`, localhost:2040)
        |
        | USB CDC serial
        v
RP2040 Debug Helper
```

The MCP server is a thin adapter:

- Receives MCP tool calls.
- Validates tool arguments.
- Calls the Device Core Service API.
- Returns compact structured results.
- Never imports serial transport or firmware protocol code directly.
- Never exposes raw GPIO writes as default tools.

## Launch Commands

Default Phase 2 command:

```bash
dutchmate mcp
```

Optional flags:

```bash
dutchmate mcp --service-url http://localhost:2040
dutchmate mcp --log-level info
```

The command must write only valid MCP JSON-RPC messages to stdout. Logs go to stderr.

If the Device Core Service is not running, MCP tool calls return a structured tool error that tells the agent to run:

```bash
dutchmate start
```

The MCP server should not silently start the Device Core Service in Phase 2. Keeping service lifecycle explicit avoids surprise hardware ownership and makes failures easier to understand.

## Optional Streamable HTTP Mode

Optional future command:

```bash
dutchmate mcp-http --host 127.0.0.1 --port 2041 --path /mcp
```

Rules:

- Bind to `127.0.0.1` by default.
- Use one MCP endpoint path, `/mcp`.
- Validate `Origin` for HTTP requests.
- Do not expose this server on `0.0.0.0` without explicit user configuration.
- Implement authentication before supporting shared workstations, CI, or remote clients.

The old HTTP+SSE transport is compatibility-only and should not be used for new DUTchMate MCP integration.

## MCP Tool Set

Phase 2 tools:

| Tool | Device Core Service endpoint |
|---|---|
| `reset_dut()` | `POST /dut/reset` |
| `set_boot_mode(mode)` | `POST /dut/boot-mode` |
| `capture_uart(seconds)` | `POST /dut/capture` |
| `get_recent_uart_log(lines)` | `GET /dut/logs` |
| `wait_for_uart_pattern(pattern, timeout_s)` | `POST /dut/wait-pattern` |
| `run_boot_test(duration_s)` | `POST /dut/boot-test` |
| `send_uart_command(cmd, force=False)` | `POST /dut/uart/send` |
| `get_debug_session(session_id)` | `GET /sessions/{id}` |
| `list_debug_sessions()` | `GET /sessions` |

Phase 4 tool:

| Tool | Device Core Service endpoint |
|---|---|
| `compare_boot_log(session_id)` | `GET /sessions/{id}/compare` |

## Tool Response Rules

MCP tools return compact JSON-compatible objects. They should preserve evidence quality flags rather than hiding them in text.

Capture-like tools must include:

- `session_id`
- `overflow`
- `interrupted`
- `resumed`
- `segments`
- relevant log excerpts when available

Failure-analysis tools must not claim complete evidence if `overflow`, `truncated`, or `interrupted` is true.

Tool errors should preserve Device Core Service error codes:

```json
{
  "ok": false,
  "error": "not_configured",
  "detail": "configure_gpio_mode not called for reset pin"
}
```

## Streaming Policy

For Phase 2, prefer bounded tools over open-ended streaming:

- `capture_uart(seconds)`
- `wait_for_uart_pattern(pattern, timeout_s)`
- `run_boot_test(duration_s)`

The MCP server may call the Device Core Service's `GET /dut/events` SSE endpoint internally later, but Phase 2 tools should return finite results. This avoids long-running MCP streams until the core workflow is stable.

## Registration Example

Generic MCP client configuration shape:

```json
{
  "mcpServers": {
    "dutchmate": {
      "command": "dutchmate",
      "args": ["mcp"],
      "env": {
        "DUTCHMATE_SERVICE_URL": "http://localhost:2040"
      }
    }
  }
}
```

Exact registration keys vary by coding agent. DUTchMate documentation should keep examples per client separate from the core architecture.

## Test Requirements

Minimum Phase 2 tests:

- MCP server starts over stdio without writing logs to stdout.
- Tool call fails clearly when Device Core Service is not running.
- Tool arguments are validated before calling the service.
- Device Core Service errors are preserved in MCP tool results.
- Capture-like tools include `overflow`, `interrupted`, `resumed`, and `segments`.
- No default MCP tool can drive arbitrary raw GPIO state.
- MCP server does not import serial transport modules.

## References

- MCP transports, version 2025-06-18: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
