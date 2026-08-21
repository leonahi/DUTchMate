# MCP Integration Plan

> Status: accepted Phase 2 transport decision
> Scope: Phase 2 MCP server transport, launch model, and tool contract.

## Decision Summary

Phase 2 implements **MCP stdio transport only**.

The planned MCP server is launched by the coding agent as a subprocess and
communicates MCP JSON-RPC over stdin/stdout. The MCP server does not own
hardware and does not open the serial port. It calls the already-running Device
Core Service over local HTTP at `http://127.0.0.1:2040` by default.

Current implementation note: `apps/mcp_server` contains the tested asynchronous
Device Core HTTP client for the nine Phase 2 endpoint mappings. It validates
tool-shaped arguments before dispatch, uses bounded workflow timeouts, preserves
canonical service error payloads, and distinguishes unavailable or malformed
service responses. The stdio tool server is still pending: `dutchmate mcp`
exits with a placeholder error, and the `dutchmate-mcp` console script raises
`NotImplementedError`.

No current DUTchMate client or deployment requires an independently hosted MCP
endpoint, so Streamable HTTP is outside Phase 2 scope. The deprecated HTTP+SSE
transport will not be implemented.

## Process Model

```text
Coding Agent / IDE Agent
        |
        | MCP stdio
        v
MCP Server process (`dutchmate mcp`, planned)
        |
        | HTTP Device Core Service API
        v
Device Core Service (`dutchmate start`, 127.0.0.1:2040)
        |
        | selected backend serial connection
        v
Basic generic USB-to-UART (raw UART) or Enhanced RP2040 Debug Helper (NDJSON)
```

The planned MCP server is a thin adapter:

- Receives MCP tool calls.
- Validates tool arguments.
- Calls the Device Core Service API.
- Returns compact structured results.
- Returns deterministic Device Core evidence and does not invoke an LLM,
  provider adapter, or Debug Agent report generator in Phase 2.
- Never imports serial transport or firmware protocol code directly.
- Never exposes raw GPIO writes as default tools.

## Launch Commands

Planned default Phase 2 command:

```bash
dutchmate mcp
```

Optional flags:

```bash
dutchmate mcp --service-url http://127.0.0.1:2040
dutchmate mcp --log-level info
```

These flags are not implemented yet. When implemented, the command must write
only valid MCP JSON-RPC messages to stdout. Logs go to stderr.

If the Device Core Service is not running, MCP tool calls return a structured
tool error that tells the agent to select one backend, for example:

```bash
dutchmate start --backend basic --serial-port /dev/ttyUSB0
# or: dutchmate start --backend enhanced
```

Plain `dutchmate start` is sufficient only when `[backend].mode` and any
required Basic serial port are already configured.

The MCP server should not silently start the Device Core Service in Phase 2. Keeping service lifecycle explicit avoids surprise hardware ownership and makes failures easier to understand.

## Deferred Streamable HTTP Trigger

Do not add a `dutchmate mcp-http` command or HTTP MCP server during Phase 2.
Reconsider Streamable HTTP only when at least one concrete requirement is
documented:

- A named supported client cannot launch a local stdio subprocess.
- An approved deployment needs one independently hosted MCP endpoint shared by
  multiple clients.
- A remote or containerized deployment cannot use a local stdio process and has
  an identified operator/security owner.

Before implementation, a follow-up design decision must define:

- the target client and deployment topology
- the MCP specification/SDK version to implement
- localhost versus remote exposure and TLS/reverse-proxy ownership
- authentication and authorization
- mandatory `Origin` validation and DNS-rebinding protection
- session, concurrency, cancellation, and reconnect behavior
- audit logging and secret handling
- integration and security tests

If approved, the server should bind to `127.0.0.1` by default and use one `/mcp`
endpoint unless the documented deployment requires otherwise. Binding to
non-loopback interfaces requires authentication and an explicit threat review.

Legacy HTTP+SSE is not a fallback deliverable. A future compatibility request
must identify a named legacy client and be reviewed separately; new DUTchMate
integrations use stdio or, after the trigger above, Streamable HTTP.

## MCP Tool Set

Phase 2 tools:

| Tool | Device Core Service endpoint |
|---|---|
| `reset_dut(pulse_ms=100)` | `POST /dut/reset` |
| `set_boot_mode(mode)` | `POST /dut/boot-mode` |
| `capture_uart(duration_s)` | `POST /dut/capture` |
| `get_recent_uart_log(lines=300, session_id=None)` | `GET /dut/logs` |
| `wait_for_uart_pattern(pattern, timeout_s)` | `POST /dut/wait-pattern` |
| `run_boot_test(duration_s)` | `POST /dut/boot-test` |
| `send_uart_command(cmd, append_newline=True, force=False)` | `POST /dut/uart/send` |
| `get_debug_session(session_id)` | `GET /sessions/{id}` |
| `list_debug_sessions(limit=50, cursor=None)` | `GET /sessions` |

Phase 4 tool:

| Tool | Device Core Service endpoint |
|---|---|
| `compare_boot_log(session_id)` | `GET /sessions/{id}/compare` |

`compare_boot_log` never selects a baseline heuristically. Device Core resolves
the one project-session-store `baseline.json` pointer; no designation preserves
`not_found`, and a corrupt or dangling pointer preserves `persistence_fault`.
Both baseline and subject must be native session schema version `1`; MCP
preserves `unsupported_session_schema` for non-native evidence. The subject must
be a terminal capture or boot-test session. Text/pattern
comparison may cross backend modes, while timing comparison is returned only
for uninterrupted single-segment sessions with matching timestamp source,
clock, observation point, and event granularity. MCP preserves
`baseline_session_id`, `timing_comparable`, and the incompatibility reason.

## Tool Response Rules

MCP tools return compact JSON-compatible objects. They should preserve evidence quality flags rather than hiding them in text.

Capture-like tools must include:

- `session_id`
- `schema_version: 1`
- accepted `duration_s` for capture/boot-test
- `integrity` with `loss_status`, `observation_scope`, and `dropped_bytes`
- `line_processing` with `status`, `max_line_bytes`, and
  `oversized_line_count`
- `storage` with evidence budget/written bytes and nullable `truncation`
- `truncated`
- `interrupted`
- `resumed`
- integer `segments` count in 1..32 for capture-like results
- relevant log excerpts when available

Timestamped excerpts must include `segment_id` and segment-relative
`timestamp_us`. MCP tools must not compare timestamps across segments or imply
finer timing than the segment's `event_granularity` metadata.

MCP does not retry or start a replacement workflow when Device Core returns
`service_unavailable` for `reconnect_limit`. It preserves the failed session ID,
the exact `segment_count: 32` / `max_segments: 32` context, and all retrievable
session evidence for an explicit follow-up decision.

The same no-retry rule applies to `reconnect_timeout`. MCP preserves
`operation`, `session_id`, and the snapshotted `reconnect_timeout_s` from the
service error and never appends to or replaces the terminal session implicitly.

`get_recent_uart_log` forwards optional `session_id` and integer `lines` in the
1..1000 range. Without an ID it preserves Device Core selection: active session
first, otherwise newest terminal session (`completed`, `failed`, or
`abandoned`). MCP must preserve `session_id`,
`schema_version: 1`, `session_selection`, `active`, `snapshot_event_count`,
complete `lines`,
`partial_lines`, response-omission counts, session integrity/truncation facts,
`oversized_lines` descriptors, line-processing facts, and referenced segment
provenance. It also preserves storage accounting and quota-truncation detail;
response omission must never be conflated with session quota truncation. It
preserves `ingestion_index` and
`line_index_in_event`, which are the only supported way to merge complete and
partial/oversized arrays; MCP must not merge them by comparing timestamps.
Device Core limits replay to native session schema version `1`; MCP preserves
`unsupported_session_schema` for explicit legacy or unknown-version requests
and does not silently substitute another session.

`list_debug_sessions` forwards `limit` and opaque `cursor` without decoding or
rewriting the cursor. It preserves the `{items, next_cursor}` page and every
item's `schema_version` and `compatibility`. For native items it also preserves
lifecycle, backend, baseline, integrity, truncation/reconnect, segment count,
line-processing state, and compact reference-only `first_error` fields. A legacy
version `0` item remains the service's bounded `legacy_read_only` identity shape;
MCP must not populate absent native fields. `get_debug_session` preserves the
complete bounded lifecycle metadata for native sessions,
`first_error.match_excerpt`, grouped evidence counts, unresolved forced-send
count, storage/truncation accounting, the 1..32 complete `metadata.json`
segment objects, and artifact manifest. For legacy version
`0`, it preserves only the bounded compatibility detail and artifact sizes.
Unknown versions preserve `unsupported_session_schema`. Neither tool expands
raw logs, JSONL events, or
full detected-pattern arrays; callers use `get_recent_uart_log` for bounded UART
evidence.

For normal lines the tool returns exact `line_raw_b64` plus lossy `line_text`;
it must not replace raw evidence with display text. A physical line over 65536
bytes remains an `oversized_lines` descriptor without invented text/base64.
MCP must not synthesize reconnect markers, silently discard partial/oversized
records, or present `response_truncated` as session evidence loss. Device Core's
compact JSON response remains capped at 262144 bytes. A missing explicit or
implicit session preserves the `not_found` service error.

Control-tool responses preserve the Device Core Service fields:
`configured_at` for GPIO configuration, `performed_at` for reset/boot actions,
and optional raw `device_timestamp_us`. MCP must not rename a raw device clock
to unqualified `timestamp_us`; that name is reserved for normalized session
evidence accompanied by `segment_id`.

`reset_dut` validates or forwards only integer `pulse_ms` values from 1 through
10000 and preserves the service default of 100 ms. Its result includes the
accepted `pulse_ms`; MCP must not omit that value from a successful response.

`set_boot_mode` preserves the accepted `mode` in its result. `normal` selects
the configured boot role's idle behavior and `bootloader` its active behavior;
the reported mode is commanded state, not DUT pin readback. `run_boot_test`
uses the current or externally selected state, requires only reset control, and
must not silently select or restore a boot mode. A Coding Agent that needs a
bootloader test explicitly calls `set_boot_mode("bootloader")`, runs the test,
and then calls `set_boot_mode("normal")`.

`capture_uart` and `run_boot_test` require an explicit numeric `duration_s` with
no MCP default. They accept finite integers/fractions satisfying
`0 < duration_s <= 300`; booleans and all other types/ranges are invalid. MCP
forwards the value unchanged and preserves Device Core's accepted `duration_s`
in success responses. It must not retry with a shorter/longer value, round the
duration, or dispatch boot-mode/reset tools after duration validation fails. A
client/tool-call timeout may include bounded protocol grace beyond the requested
duration but never changes the Device Core monotonic workflow deadline.

`wait_for_uart_pattern` accepts a Unicode literal whose UTF-8 encoding is
1..256 bytes with no CR/LF and a finite `0 < timeout_s <= 300`; booleans are
invalid. Matching is case-sensitive on complete lines received after the new
wait session starts. MCP must not interpret regex/glob syntax, search prior
logs, attach to an active session, or retry `capture_active` automatically.

The tool preserves `session_id`, `pattern`, `matched`, `end_reason`, bounded
`match_excerpt` with byte offsets/exact base64, detected-pattern reference,
segment/timestamp provenance, integrity, and line-processing fields. It never
expands that excerpt to the complete source line. `matched: false` with
`end_reason: "timeout"` is a successful bounded no-match result, not a tool
error. Service/backend failures still preserve their canonical error codes.

`send_uart_command` accepts Unicode text, encodes it as UTF-8, and defaults
`append_newline = true`. Device Core appends one LF only when the encoded bytes
do not already end in LF, preserving existing LF and CRLF endings. Setting it
to `false` sends the UTF-8 bytes without an added terminator. MCP does not
expose raw bytes or base64 payload input in Phase 2.

The final encoded payload must contain 1..1024 bytes after optional LF
insertion. MCP validates or forwards this exact contract and preserves
`invalid_argument` context containing `actual_bytes` and `max_bytes` for an
oversized request. The limit is measured in UTF-8 bytes, not characters. Empty
text with default newline sends one LF; empty text with
`append_newline = false` is invalid.

`hardware.uart.tx_enabled` defaults false and filters `uart_send` for both
backend modes. MCP must use effective `capabilities`, never infer permission
from raw `backend_capabilities`, and preserve `disabled_by_policy` context when
Device Core reports that TX was explicitly disabled.

Status/session `tx_policy_enabled` means only that Device Core may submit UART
bytes. MCP must not describe it as physical TX enable, high impedance, wiring
detection, or electrical isolation. Setting it false does not disconnect Basic
adapter TX and cannot independently disable the Enhanced Revision A transmit
direction while its shared UART translator is enabled for receive.

`send_uart_command` defaults to `force = false`. During an active capture,
boot-test, or wait-pattern session, the default preserves evidence isolation by
returning `capture_active`; explicit `force = true` may bypass only that
ownership conflict. It never bypasses argument validation, effective
`uart_send` capability policy, `tx_enabled = false`, connection state, or
backend errors.
MCP must preserve `performed_at`, optional `device_timestamp_us`, and
`perturbation_logged` from Device Core. It also preserves `attempt_id` on a
forced in-session success or dispatched failure and preserves nullable
`bytes_accepted` in error context.

The MCP server must not infer `force = true` or automatically retry a
`capture_active` response with force. A caller must request it explicitly. A
forced in-session send is dispatched only after Device Core durably records
`uart_tx_attempt`, and success returns only after the matching `uart_tx_result`
is durable. MCP must not present either record or an accepted-byte count as
proof that the DUT electrically received the bytes. A failed result may report
partial acceptance; an unmatched attempt means completion is unknown and must
be surfaced as such. `persistence_fault` after result dispatch must not be
recast as a failed-to-transmit guarantee. Outside an active session, force has
no additional effect.

Before a forced attempt is dispatched, Device Core quota admission reserves the
maximum matching-result record size. MCP does not expose, alter, or release that
reservation. If the session reaches its evidence cap, MCP preserves
`completed`/`size_limit`, `truncated`, and rejected-unit accounting; a physical
write failure remains `persistence_fault` and must not be recast as clean quota
truncation.

Failure-analysis tools must surface `loss_reported` and `not_observable` without
turning `none_reported` into a global lossless guarantee. They must also preserve
independent `truncated` and `interrupted` flags.

Tool errors should preserve Device Core Service error codes:

```json
{
  "ok": false,
  "error": "not_configured",
  "detail": "reset role is not configured",
  "detail_truncated": false,
  "context": {
    "operation": "boot_test",
    "required_role": "reset",
    "role_state": "unconfigured"
  }
}
```

In particular, MCP preserves `backend_input_error` and its bounded category/frame
size context when the Enhanced backend emits malformed or oversized NDJSON. It
must not retry the failed workflow, substitute another session, expose the raw
offending frame, or recast the failure as timeout, disconnect, UART loss, or
session truncation.

They must also preserve the optional structured `context`. In particular,
`unsupported_capability` means the selected backend cannot perform the
operation, while `not_configured` means the capability exists but the required
user role is not configured. MCP tools must not infer missing role
configuration when Device Core reports an absent physical capability.

## Streaming Policy

For Phase 2, prefer bounded tools over open-ended streaming:

- `capture_uart(duration_s)`
- `wait_for_uart_pattern(pattern, timeout_s)`
- `run_boot_test(duration_s)`

The MCP server may call the Device Core Service's `GET /dut/events` SSE endpoint
internally later, but Phase 2 tools should return finite results. This avoids
long-running MCP streams until the core workflow is stable. Capture, boot-test,
and wait-pattern remain capped at 300 seconds even if an MCP client allows a
longer tool-call timeout.

## Registration Example

Planned generic MCP client configuration shape:

```json
{
  "mcpServers": {
    "dutchmate": {
      "command": "dutchmate",
      "args": ["mcp"],
      "env": {
        "DUTCHMATE_SERVICE_URL": "http://127.0.0.1:2040"
      }
    }
  }
}
```

This is not runnable yet because the MCP server is not implemented. Exact
registration keys vary by coding agent. DUTchMate documentation should keep
examples per client separate from the core architecture.

## Test Requirements

Minimum Phase 2 tests:

- MCP server starts over stdio without writing logs to stdout.
- Phase 2 packaging and CLI expose no Streamable HTTP or legacy HTTP+SSE server
  command.
- Tool call fails clearly when Device Core Service is not running.
- Tool arguments are validated before calling the service.
- Device Core Service errors are preserved in MCP tool results.
- Capture-like tools include accepted duration when applicable, `integrity`,
  `line_processing`, storage/truncation accounting, `truncated`, `interrupted`,
  `resumed`, and `segments`.
- Capture and boot-test reject invalid or over-300-second durations without
  calling Device Core and preserve the accepted duration from success responses.
- Quota truncation remains distinct from response omission, backend loss, and
  persistence failure; forced-send result reservations are not exposed or
  modified by MCP.
- Reconnect-limit and reconnect-timeout failures preserve their exact bounded
  service context and failed session without an MCP retry or replacement
  workflow.
- Timestamped evidence preserves `segment_id` and never orders events across
  segments by `timestamp_us`.
- Control tools preserve `configured_at`/`performed_at` and
  `device_timestamp_us` without presenting the raw device clock as normalized
  session time.
- `reset_dut` defaults to 100 ms, rejects invalid duration types/ranges, and
  returns the accepted `pulse_ms`.
- No default MCP tool can drive arbitrary raw GPIO state.
- MCP server does not import serial transport modules.
- MCP tool execution does not invoke an LLM or require model-provider
  configuration.

## References

- MCP transports, version 2025-06-18: https://modelcontextprotocol.io/specification/2025-06-18/basic/transports
