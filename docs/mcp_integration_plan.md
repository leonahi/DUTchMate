# MCP Integration Plan

> Scope: Phase 2 stdio adapter migration to the accepted Phase 1 v2 service API.
> [Project context](project_context.md) and the
> [Phase 1 specification](phase1_implementation_spec.md) define product and
> service behavior. This plan maps those contracts; it does not redefine them.
> [Development status](development_status.md) alone owns readiness, progress and
> the next task. Dated audit evidence belongs in
> [development history](development_history.md#mcp-v2-start-prerequisite-and-contract-audit--2026-10-30).

## Sequencing and Architectural Boundaries

Apply the MCP start prerequisites and hardware evidence boundaries in
[specification §4.1](phase1_implementation_spec.md#41-software-sequencing-and-hardware-acceptance-boundaries):
accepted Device Core/service/CLI software baseline plus available functional
Enhanced HIL. Legacy EAGLE functional HIL is permitted. Manufactured KiCad Rev-A
physical/electrical acceptance is a separate gate for final Stage 8, Phase 1B and
Phase 1 completion; MCP work neither closes that gate nor the historical EAGLE
UART electrical/oscilloscope gap. KiCad source review remains source verification.

The process boundary remains:

```text
coding agent -> MCP stdio -> thin HTTP service client
             -> authoritative Device Core Service -> Device Core -> backend/DUT
```

MCP must not open serial devices, import backend/firmware transports, recreate
connection ownership or operation timing/state machines, keep independent
session/evidence truth, invoke an LLM, or run the Debug Agent. One service owns
physical acquisition. Tool calls request existing bounded operations or retrieve
existing evidence; they do not own the UART reader. User configuration and
service startup remain explicit, outside MCP tools.

## Preserve the Existing Transport Foundation

Retain stdio-only Phase 2 transport, MCP `2026-07-28`, official Python SDK
`mcp>=2.0,<3` (locked `2.0.0`), and `MCPServer`. The existing composition uses
modern `server/discover`, per-request protocol/client-capability `_meta`, no
application handshake/session state, tools-only capabilities, and complete
structured results. Let the SDK validate protocol metadata and emit
`resultType`/server identity. Do not replace it with SDK 1.x or `FastMCP`.

The fixed tool catalog has deterministic registration order, `listChanged: false`
and finite private cache hints (existing TTL: 300,000 ms). SDK legacy-client
compatibility may remain, but DUTchMate does not depend on it. Phase 2 adds no
resources, prompts, subscriptions, Multi Round-Trip Requests, protocol tasks,
Roots, Sampling, or protocol Logging. Process logs go to stderr.

Retain `dutchmate mcp [--service-url URL] [--log-level LEVEL]` and its
`dutchmate-mcp` entrypoint. URL precedence is explicit flag, then
`DUTCHMATE_SERVICE_URL`, then `http://127.0.0.1:2040`; existing log-level handling
and sibling-executable launch remain. Do not silently start/stop the Device Core
Service. An unavailable service returns a bounded actionable tool error.

Streamable HTTP and deprecated HTTP+SSE are not Phase 2 deliverables. A named
client/deployment requirement and a separate approved transport/security design
are required before adding hosted MCP. No open-ended MCP streaming is required;
finite evidence long-polling is an ordinary bounded tool call.

## Migration Inventory

The inventory distinguishes reusable infrastructure from obsolete adapter
behavior. Existing MCP source/tests are evidence of transport behavior, not of
v2 tool compatibility. Tests using mocked HTTP success for obsolete endpoints
cannot establish acceptance against the real v2 service.

| Existing consumer/path | Migration action |
|---|---|
| `apps/mcp_server/src/dutchmate_mcp_server/service_client.py` | Keep one async HTTP client, URL validation, dependency injection, JSON/error handling and no-redirect/no-proxy behavior; add the mappings below. |
| `apps/mcp_server/src/dutchmate_mcp_server/server.py` | Keep composition, discovery, result wrapping and cache policy; replace the tool catalog and its argument schemas. |
| `capture_uart`, `wait_for_uart_pattern`, `/dut/capture`, `/dut/wait-pattern` | Retire from the MCP target surface; use `monitor`. Service-only compatibility aliases do not become MCP tools. |
| `run_boot_test`, `/dut/boot-test` | Remove MCP registration/client method/tests; the live service has no such endpoint. Use client composition below. |
| `send_uart_command(cmd, append_newline, force)` | Replace with `send_uart` and the v2 byte/text payload contract; retire implicit newline and bypass fields. |
| `get_recent_uart_log`, `get_debug_session`, `list_debug_sessions` | Migrate to `get_recent_logs`, `get_session`, `list_sessions`, preserving service fields and compatibility discriminators. |
| MCP server/client/protocol tests | Replace obsolete target fixtures/assertions; keep modern protocol, error, cancellation and stdio coverage. |
| `apps/cli/src/dutchmate_cli/mcp.py`, MCP `main.py`, entrypoint/CLI tests | Preserve existing launch implementation; refresh catalog/installed-launch acceptance only where needed. |

No production code changes are part of this audit. During implementation,
remove retired methods once registration/tests no longer consume them; do not
create service compatibility behavior to keep an obsolete MCP tool working.

## Target Tool Catalog

Register these twelve tools in the table order. Names follow the existing
service handler/operation names, except MCP tool `set_dut_boot_mode` maps to the
unchanged service operation `set_boot_mode` at `POST /dut/boot-mode`. Forward the
documented body/query without inventing another API model. Each result is the
service's bounded JSON object
in structured content, mirrored as compact JSON text; do not insert invented
success fields or discard evidence/provenance fields.

| Tool | Accepted service mapping and arguments | Coding-agent use |
|---|---|---|
| `get_status()` | `GET /status` | Inspect connection/profile, effective capabilities, active operations and policy before acting. |
| `monitor(duration_s?, conditions?, timeout_s?)` | `POST /dut/monitor`; `MonitorRequest` | Bounded duration observation or literal-condition wait. |
| `interact(data_b64?, text?, line_ending?, duration_s?, conditions?, timeout_s?)` | `POST /dut/interact`; `InteractRequest` | One exact audited TX plus bounded observation. |
| `send_uart(data_b64?, text?, line_ending?)` | `POST /dut/uart/send`; `UartSendRequest` | Standalone audited TX without claiming a command-response window. |
| `reset_dut(pulse_ms=100)` | `POST /dut/reset`, body `pulse_ms` | Pulse the already-configured reset role. |
| `set_dut_boot_mode(mode)` | `POST /dut/boot-mode`, body `mode` | Command the configured boot role to `normal` or `bootloader`. |
| `get_evidence(cursor?, limit=100, wait_s=1.0)` | `GET /dut/evidence`, query `cursor`, `limit`, `wait_s` | Establish a durable tail boundary or retrieve a finite page across actions/reconnects. |
| `get_recent_logs(session_id?, lines=300)` | `GET /dut/logs`, query `session_id`, `lines` | Retrieve bounded historical UART, including from an explicitly selected session. |
| `list_sessions(limit=50, cursor?)` | `GET /sessions`, query `limit`, `cursor` | Find recent evidence sessions using stable pagination. |
| `get_session(session_id)` | `GET /sessions/{session_id}`; validated/escaped path ID | Inspect lifecycle, quality, segments, unresolved actions and artifact references. |
| `release_connection()` | `POST /connection/release`, no body | Explicitly hand the transport to an external flash/tool process. |
| `reacquire_connection()` | `POST /connection/reacquire`, no body | Resume service ownership and expose the new segment boundary. |

Do not mechanically expose the remaining endpoints. Phase 2 has no profile/GPIO
configuration tool, arbitrary raw GPIO, baseline mutation/comparison tool,
service lifecycle tool, follow/console stream, or dedicated boot-validation tool.
The twelve tools cover observation, exact interaction, configured control,
bounded evidence and an external-tool handoff without broad configuration or
analysis surfaces.

### Requests and deadlines

Use the accepted schemas/validators rather than independent policy:

- Monitor and Interact require exactly one completion mode: finite
  `0 < duration_s <= 300`, or 1..8 ordered `{pattern, name?}` conditions plus
  finite `0 < timeout_s <= 300`. Reject booleans/nonfinite times, mixed modes,
  missing bounds and invalid literals/names before HTTP dispatch. Literals are
  case-sensitive, 1..256 UTF-8 bytes, without CR/LF; no regex/glob interpretation.
- Send and Interact require exactly one payload: valid `data_b64` with no
  `line_ending`, or `text` with explicit `line_ending` in `none`, `lf`, `cr`,
  `crlf`, `profile_default`. Final bytes must be 1..1024. Forward the request;
  Device Core resolves the active profile default. Do not pre-encode text into
  a different request, trim bytes, deduplicate terminators or add implicit LF.
  Reject retired `cmd`, `append_newline` and `force` fields.
- Reset accepts only integer `pulse_ms` 1..10000, default 100. Boot-mode values
  are exactly `normal` and `bootloader`; they are commanded state, not pin readback.
- Evidence `limit` is integer 1..500; `wait_s` is finite 0..30. Session-list
  `limit` is integer 1..100; log `lines` is integer 1..1000. Preserve opaque
  cursors as strings, validated using the corresponding service contract.

The client retains its 2-second ordinary request timeout and 2-second transport
grace for bounded Monitor/Interact and evidence long-poll requests, sized from
the accepted `duration_s`, `timeout_s` or `wait_s`. Connection mutations reuse
the existing CLI client's 65-second HTTP timeout, allowing the service's
configured reacquire deadline to run without a second reconnect loop or status
polling. This is transport allowance, not a new service deadline. Do not shorten
or extend Device Core's monotonic deadlines, automatically retry
TX/Control/Interact/reacquire, or substitute a new operation/session after a
timeout. An HTTP timeout means state
may be unknown, not that an action was undone or bytes were never sent.

### Result and evidence preservation

- Status preserves actual `active_session_id`, `active_operations`, connection
  state/error, profile/digest/effective settings, raw and effective capabilities,
  `capability_policy`, integrity/provenance, commanded boot mode, controls and
  retention fields. Effective `capabilities` determine permission; raw physical
  capabilities do not override policy. TX policy is not electrical isolation.
- Monitor/Interact preserve `operation_id`, all service outcomes (`elapsed`,
  `matched`, `timeout`, `disconnected`, `released`, `cancelled`, `error`), mode,
  accepted parameters, `start_cursor`, `end_cursor`, half-open `evidence_ranges`,
  `matched_condition`, `line_processing_limited`, `integrity` and
  `timestamp_provenance`. Preserve exact match excerpts/base64/offsets. Interact
  also preserves `data_b64`, `transformation`, nullable `tx` and `tx_error`.
  A service-returned terminal result stays a result; ordinary condition timeout
  is not an MCP/HTTP transport error.
- Send preserves `attempt_id`, exact `data_b64`, `accepted_bytes`, status,
  `audit_status`, `transformation`, attempt/result session IDs and evidence
  sequence references, `performed_at` and nullable `device_timestamp_us`.
  Acceptance by a backend is not proof of electrical DUT receipt. Preserve
  partial/unknown TX and unresolved attempts; never manufacture success.
- Reset/boot success preserves the fields actually returned by
  `device_action_payload`: `ok`, `performed_at`, nullable `device_timestamp_us`,
  and accepted `pulse_ms` or `mode`. These responses do not contain operation
  IDs or audit cursors; obtain control audit records through saved evidence
  cursors instead of inventing them. Do not relabel raw device clocks as
  normalized segment-relative time.
- Evidence preserves `records`, exact `data_b64` and action/connection/telemetry
  records, `next_cursor`, and `omitted_records`. Omitting `cursor` attaches at the
  current durable tail with no historical replay. The public opaque cursor is
  distinct from Monitor/Interact's structured `{session_id, next_evidence_seq}`
  positions; do not interconvert or decode either into a fabricated cursor.
- Recent logs preserve actual `complete_lines`, `partial_lines`,
  `oversized_lines`, exact raw base64, lossy text, segment/channel/byte
  coordinates, `schema_version`, `session_selection`, snapshot/provenance,
  integrity/line-processing, storage/truncation and response-omission fields.
  Keep service ordering; never merge arrays using timestamps across segments.
- Session list/detail preserve the v2 `schema_version`/`compatibility`, lifecycle,
  profile, rollover chain, segments, `evidence_quality`, storage, operation/action
  counts, unresolved attempt counts, `first_error` and manifest fields wherever
  returned by that endpoint. Do not require detail-only fields on list items.
  Keep v0/v1 read-only compatibility shapes and schema errors; do not upgrade,
  rewrite or fill missing native fields on historical data.
- Release/reacquire preserve `ok`, `connection_state`, `session_id`, `segment_id`.
  Intentional gaps, automatic reconnect and timestamp-origin changes remain
  service evidence. MCP never opens an external port or assumes continuity.

Evidence/log pages are already capped at 262144 compact UTF-8 bytes. Preserve
whole records and service omission counts. Response omission, recording loss,
backend loss, observation gaps and line-processing limits are different facts;
`none_reported` is not global losslessness. Do not impose a schema-v1 result or
copy journal truth into an MCP-owned cache/store.

### Error projection and cancellation

Keep SDK `CallToolResult` wrapping: success and bounded terminal operation
results are complete structured results; input/service/client failures use
`isError: true`. Unknown tools, malformed protocol requests and unsupported
protocol versions remain protocol errors. Preserve service `ok: false`, `error`,
`detail`, `detail_truncated` and optional bounded `context` without renaming
codes. Reuse the shared diagnostic projection for locally generated errors;
never copy raw frames, UART data, secrets or exception dumps into diagnostics.

Preserve `invalid_argument`, `unsupported_capability` (including disabled-policy
source), `not_configured`, `operation_active`, `invalid_connection_state`,
`invalid_session_state`, `cursor_expired`, schema/persistence/backend errors and
the service's exact context. Missing physical capability is distinct from a
missing configured role. Preserve HTTP 410 cursor expiry; do not silently
reattach or select another session. Keep malformed/non-object service responses
as bounded `service_protocol_error`, and unreachable service as
`service_unavailable` without attempting service startup.

Propagate cancellation through the SDK/HTTP request path. Device Core owns
terminalization and durable `cancelled` evidence; cancellation cannot roll back
an action already dispatched. Phase 2 adds no cancel-by-ID API or client-owned
operation state machine.

### Client-composed boot validation

Follow [specification §24](phase1_implementation_spec.md#24-client-composition-of-atomic-capabilities):
obtain a tail cursor with `get_evidence`, optionally select boot mode, call
`reset_dut`, then consume evidence from the saved cursor. A later Monitor is
optional for subsequent bounded conditions; it does not retroactively match
bytes acquired before its start. The caller explicitly restores `normal` when
appropriate. No MCP handler combines these actions, automatically chooses boot
mode or sleeps/reads the serial port.

## Independently Testable Implementation Sequence

This is dependency order, not a second progress tracker. Preserve the existing
protocol/dependency/server foundation; do not repeat its original implementation.

1. **V2 HTTP service-client mappings and error projection.** Change MCP
   `service_client.py` and `test_service_client.py` to implement the catalog's
   twelve mappings with the existing injected HTTP transport. Cover exact
   bodies/queries, v2 payloads, finite timeouts, opaque cursor round trips and
   canonical errors. Additive methods may coexist with still-registered old
   consumers within this slice; no new compatibility API is added to the
   service. Exit: focused mapping tests pass without hardware; SDK baseline,
   existing catalog and launch tests stay passing. Public tool registration
   changes belong to slice 2.
2. **V2 tool catalog and removal of retired adapter paths.** Update `server.py`
   and `test_server.py`, replacing registration/argument schemas with the table
   order and service-shaped arguments. Update catalog-dependent protocol
   fixtures so each commit remains testable. Remove obsolete methods/tests once
   consumers migrate. Exit: all twelve tools dispatch exactly once; retired
   tools/fields are absent or rejected; structured success/errors, duration and
   condition outcomes, binary payloads and line endings are preserved.
3. **Actual service and modern protocol integration.** Extend
   `test_protocol_integration.py` and client/server tests to call the real service
   app through an injected ASGI transport with deterministic fake backends.
   Verify v2 operation/evidence/session projections instead of merely returning
   mocked success for a path. Exit: protocol metadata/discovery/version/cache,
   actual v2 endpoint mappings, error/cursor propagation and cancellation/EOF
   tests pass; no real hardware, second owner or evidence-store truth in MCP.
4. **Installed launch and boundary regressions.** Preserve CLI/entrypoint
   implementation unless a concrete regression requires a change. Refresh
   installed `dutchmate mcp` stdio catalog/unavailable-service tests, CLI flag/env
   and sibling-launch tests, packaging and architecture checks. Exit: modern
   discovery and exact tool listing work without a venv on PATH, no non-protocol
   stdout, clean startup/shutdown, no hosted MCP command or forbidden imports.
5. **Scoped protocol/host acceptance and documentation.** Refresh named VS Code
   and Claude Code registration examples only as needed; perform the gate below
   for the migrated catalog. Record unavailable host UI checks truthfully.
   Preserve historical acceptance evidence without relabelling it as v2 tool
   acceptance. Remove superseded working-plan material when migration finishes,
   preserving durable contracts in authoritative documentation.

Every implementation slice runs focused tests during development and the
repository-required Ruff, mypy, full pytest and `git diff --check` gate before
completion. Apply the repository Graphify policy only when interfaces or
structure actually change. No firmware, protocol or hardware redesign is needed
for this mapping migration.

## Test and Acceptance Matrix

| Area | Required checks for the migrated adapter |
|---|---|
| Mapping/validation | Each tool's exact method/path/body/query; invalid finite bounds, modes, literals, IDs, booleans and payload combinations rejected before dispatch; no retired fields. |
| Monitor/Interact | Duration elapsed, condition matched/timeout and other terminal outcomes; operation IDs, cross-session half-open ranges, exact match excerpts and nullable TX/error fields unchanged. |
| Exact TX | Binary/invalid-UTF-8 base64, multibyte text, all explicit endings including profile resolution; byte limits after transformation; no terminator deduplication or implicit LF; audit/partial/unknown outcomes retained. |
| Control | Reset default/range and boot enum; capability/policy/role errors; only actual action response fields; boot validation remains composed by the caller. |
| Evidence/sessions | Tail attach, opaque public cursor versus operation positions, long-poll bound, 410 expiry, omission counts, segments/gaps/rollover, v2 quality/counts, explicit logs selection and read-only v0/v1 compatibility. |
| Ownership | Release/reacquire exact projection, invalid-state/conflict errors, no automatic retry/reopen, no serial imports or MCP-owned sessions/reader. |
| Errors | Preserve canonical bounded service code/detail/truncation/context; malformed JSON/non-object/error contracts, unreachable service and unknown timeout state; no action retry. |
| Protocol | Existing MCP 2.x/`2026-07-28` baseline, modern metadata, version rejection, discovery, exact ordered twelve-tool listing, private finite TTL, complete structured success/error, cancellation and EOF. |
| Launch/dependencies | Existing URL precedence/logging/sibling executable behavior, installed real stdio process without service or venv PATH, deterministic listing, actionable unavailable-service result, stderr-only logs, clean shutdown. |
| Boundaries | No serial/backend imports, LLM/Debug Agent dependency, raw GPIO, hidden operation/session truth, boot-test composite, open-ended stream or hosted MCP endpoint. |

Final v2 adapter acceptance requires actual service-backed integration and a
modern SDK real-stdio subprocess test of the exact catalog, unavailable-service
error and clean shutdown. Re-run strict Inspector `tools/list` validation through
the absolute installed launcher and record named host checks when available.
Prior nine-tool mock/protocol or host evidence does not accept the new catalog.

Retain the existing scoped conformance policy. The pinned official runner
`@modelcontextprotocol/conformance@0.2.0-alpha.11` accepts an HTTP server URL,
not a stdio command. A temporary loopback HTTP projection of the same
`create_server()` composition is supporting protocol evidence only, never a
Phase 2 product endpoint. Run its frozen `2026-07-28` requirement set: applicable
`server-stateless` checks must pass except the two synthetic
`test_missing_capability` sampling-tool checks; all three `tools-list` checks
and the tools-list cache/TTL/scope/wire-schema checks must pass. Record other
optional-fixture results as out-of-scope evidence, not passes or stdio product
failures. Reconcile any changed runner behavior explicitly rather than silently
changing the protocol policy. Ruff, mypy, full pytest and diff checks must pass.

## Source and Contract References

- [Service endpoints](../apps/service/src/dutchmate_service/app.py),
  [request/response schemas](../apps/service/src/dutchmate_service/schemas.py),
  [canonical errors](../apps/service/src/dutchmate_service/errors.py).
- [Operation/cursor models](../core/src/dutchmate_core/operations/monitor.py),
  [byte-first validation](../core/src/dutchmate_core/validation.py),
  [public evidence pages](../core/src/dutchmate_core/evidence/tail.py).
- [MCP source](../apps/mcp_server/src/dutchmate_mcp_server/server.py),
  [service client](../apps/mcp_server/src/dutchmate_mcp_server/service_client.py),
  [protocol baseline tests](../apps/mcp_server/tests/test_protocol_baseline.py),
  [protocol/stdio tests](../apps/mcp_server/tests/test_protocol_integration.py).
- [Migration sequencing](dutchmate_phase1_v2_coding_agent_plan.md#5-after-software-baseline-acceptance--migrate-mcp-resume-phase-4-separately).
- [MCP specification 2026-07-28](https://modelcontextprotocol.io/specification/2026-07-28),
  [stdio transport](https://modelcontextprotocol.io/specification/2026-07-28/basic/transports/stdio),
  [official Python SDK](https://github.com/modelcontextprotocol/python-sdk),
  [conformance runner](https://github.com/modelcontextprotocol/conformance),
  [Inspector CLI](https://github.com/modelcontextprotocol/inspector/blob/main/clients/cli/README.md).
