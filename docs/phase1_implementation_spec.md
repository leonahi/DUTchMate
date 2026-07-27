# Phase 1 Implementation Spec

> Status: draft
> Scope: RP2040 Debug Helper MVP, Device Core Service, host CLI, and testable protocol/session contracts.

## Goal

Prove the core hardware-in-the-loop workflow:

```text
build firmware -> flash DUT externally -> reset DUT -> capture timestamped UART logs -> store evidence -> detect failure
```

Phase 1 is successful when DUTchMate can run a boot test against one DUT using
user-configured hardware channel mappings, preserve raw UART evidence, and
return structured results through the local CLI and Device Core Service.

## Non-Goals

- MCP integration
- AI log summaries or LLM-based diagnosis
- MessagePack + COBS protocol encoding
- GUI
- Multi-DUT support
- Power/current/voltage sensing
- Arbitrary GPIO control workflows beyond configured Phase 1 roles
- JTAG/SWD debugging
- Firmware flashing

Phase 2 MCP integration is planned in `docs/mcp_integration_plan.md`. Phase 1
should keep the Device Core Service API stable enough for the later MCP stdio
adapter, but must not implement MCP before CLI workflows are validated. The
current `dutchmate mcp` CLI command and `dutchmate-mcp` console script are
placeholders only.

## Implementation Order

Phase 1 should be built host-side first with mocked protocol fixtures, then connected to real firmware and hardware.

1. Define protocol schemas and canonical examples. **Implemented for the channel-aware v1 MVP.**
2. Implement Device Core protocol parsing and event models. **Implemented for v1 MVP.**
3. Implement UART byte preservation, lossy UTF-8 display text, and complete-line buffering. **Implemented.**
4. Implement session storage. **Implemented for creation, incremental UART/event writes, telemetry, and summaries.**
5. Implement pattern detection on complete decoded lines. **Implemented.**
6. Implement Device Core workflows using a mock serial transport. **In progress: mocked NDJSON byte capture, reset/boot action enforcement, and synchronous serial command transport are implemented; continuous capture and the boot-test workflow remain.**
7. Expose workflows through the Device Core Service API. **In progress: status, GPIO mode, reset, and boot-mode endpoints are implemented; capture/log/session endpoints remain.**
8. Add the CLI as a thin HTTP client. **In progress: start, stop, device discovery, status, GPIO mode, reset, and boot-mode commands are implemented; capture/log/session commands remain.**
9. Implement RP2040 firmware to satisfy the channel-aware v1 protocol. **Not started.**
10. Run hardware smoke tests with a real DUT. **Not started.**

### Current Host-Side Core Flow

The implemented mock capture path is:

```text
NDJSON byte chunks
  -> device_connection.NdjsonStreamParser
  -> device_connection.parse_device_message
  -> workflows.CaptureStreamRecorder
  -> uart_capture.UartCaptureProcessor
  -> log_processing.PatternDetector
  -> session_store.SessionStore
  -> session_store.SessionSummary
```

The mock runner `run_mock_capture(...)` records finite NDJSON byte chunks into
a session and returns a `SessionSummary`. It is intentionally host-only and does
not open a serial port.

## Package Layout

```text
apps/
  cli/           Human-facing command-line client.
  service/       FastAPI Device Core Service; owns the serial port.
  mcp_server/    Phase 2 only.

core/
  src/dutchmate_core/
    device_connection/   Protocol models, parsing, command encoding, NDJSON framing.
    uart_capture/        UART event ingestion, byte preservation, and line buffering.
    gpio_config/         Debug Helper GPIO mode configuration workflow/state.
    session_store/       Debug session persistence and summaries.
    log_processing/      Pattern detection on completed UART lines.
    workflows/           Mock capture recording plus guarded reset/boot actions.

hardware/
  firmware/      RP2040 firmware.
  protocol/      Versioned protocol schemas, examples, and fixtures.
  schematics/    Debug Helper hardware design files.

tests/
  unit/          Parser, line-buffering, pattern, and session tests.
  integration/   Device Core Service tests using mock serial streams.
  fixtures/      Pre-recorded protocol streams and expected outputs.
```

## Phase 1 Hardware Mapping Contract

The proposed voltage-domain hardware architecture is defined in
`docs/dutchmate_hardware_architecture.md`. Phase 1 software must follow that
model: physical DUTchMate channels are generic, and the user maps those
channels to DUT schematic signals and workflow roles.

Phase 1 control channels:

```text
CTRL0
CTRL1
CTRL2
CTRL3
```

Phase 1 event channels:

```text
EVENT0
EVENT1
EVENT2
EVENT3
```

Phase 1 workflow roles:

| Role | Required when | Channel type |
|---|---|---|
| `reset` | `reset`, `reset-capture`, and `boot-test` workflows | `CTRLx` |
| `boot` | `boot-mode` workflows and boot tests that change BOOT/control state | `CTRLx` |

The user-provided `.dutchmate/config.toml` hardware mapping should use this
shape:

```toml
[hardware]
dut_io_voltage = 1.8

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"

[hardware.control.boot]
channel = "CTRL1"
dut_signal = "BOOT0"
mode = "push_pull"
active_level = "high"
idle_level = "low"
```

Validation rules:

- Unknown channels are rejected.
- Duplicate physical channel assignments are rejected.
- Control roles must map to `CTRLx` channels.
- Event roles must map to `EVENTx` channels.
- `dut_signal` must be a non-empty user-facing schematic name.
- `reset` must be mapped before reset or boot-test workflows can run.
- `boot` must be mapped before boot-mode workflows can run.
- Custom control roles are accepted as project/user metadata and reported in
  status, but Phase 1 workflows only assume built-in semantics for known roles
  such as `reset` and `boot`.
- If `DUT_VIO` measurement is not implemented in Phase 1 firmware, the service
  may treat configured `dut_io_voltage` as a trusted user declaration. Firmware
  must still keep all control outputs high-impedance until configuration is
  accepted.

Current implementation status:

- Host-side TOML validation accepts `[hardware.control.*]` mappings for any
  non-empty role name and rejects duplicate physical control channels.
- GPIO runtime state is channel-first: `CTRL0` to `CTRL3` are tracked as the
  primary resources, with role lookup used by reset/boot workflows.
- Service startup loads the hardware config and applies accepted mappings after
  validating the firmware `hello` when a serial port is selected.

## Phase 1 Protocol Contract

The host-device protocol is NDJSON over USB CDC serial. Each line is one JSON message. The v1 schemas live under `hardware/protocol/v1/`.

Only the following host-to-device command categories are in scope:

- channel-aware control configuration
- `reset`
- `set_boot_mode`
- `uart_send`

Only the following device-to-host messages are in scope:

- `hello`
- `uart`
- `buffer_overflow`
- `buffer_status`
- command success response
- command error response

The Phase 1 `configure_gpio_mode` command is channel-aware so the Device Core
can tell the Debug Helper which physical control channel a role uses. The
control configuration command carries at least:

- physical channel, such as `CTRL0`
- workflow role, such as `reset`
- electrical mode, such as `open_drain`
- active level, when the role has assertion semantics
- idle level, when required by push-pull behavior

`dut_signal` is host-side metadata for status, logs, and reports. It does not
need to be sent to firmware unless the firmware later exposes user-facing
diagnostics.

Protocol changes must update the schema files, examples, parser tests, and firmware handling in the same change.

## Device Core Requirements

The Device Core library must:

- Own protocol parsing and validation.
- Decode `data_b64` to raw bytes.
- Preserve raw UART bytes losslessly in `uart_raw.log`.
- Produce lossy UTF-8 display text with replacement characters for CLI display and pattern matching.
- Buffer UART bytes into complete lines before running pattern detection.
- Record buffer overflow events.
- Start with a 32 KiB UART RX ring buffer and expose buffer telemetry when firmware provides it.
- Load and validate hardware channel mappings from `.dutchmate/config.toml`.
- Enforce accepted GPIO role modes before reset and boot-mode operations.
- Track each required GPIO role as `unconfigured`, `configured`, or `rejected`.
- Treat config-file GPIO modes as explicit configuration only after firmware accepts them.
- Preserve the previous accepted GPIO mode when a runtime override is rejected.
- Preserve `channel`, `role`, `dut_signal`, mode, source, and last rejection in
  status/reporting models.
- Reject hardware-starting operations while a capture is active.
- Remain independent from MCP and LLM frameworks.

## Session Storage Requirements

Every capture-like workflow creates a session under `.dutchmate/sessions/`.

Minimum Phase 1 files:

```text
metadata.json
uart_raw.log
uart_events.jsonl
hardware_events.jsonl
detected_patterns.json
```

Writes must be incremental. A USB disconnect, process interruption, or capture failure must not discard data already received.

`metadata.json` must include at least:

- `session_id`
- `started_at`
- `command`
- `truncated`
- `interrupted`
- `resumed`
- `overflow`
- `baseline`
- `firmware`
- `device`
- `segments`

Reconnect and resume behavior is defined in `docs/reconnect_session_semantics.md`. UART events written after a reconnect must include `segment_id` and `timestamp_epoch` so device timestamps are never treated as continuous across a disconnect.

Current implementation notes:

- `uart_raw.log` preserves raw UART bytes incrementally.
- `uart_events.jsonl` records base64 UART payloads, lossy display text, `segment_id`, and `timestamp_epoch`.
- `hardware_events.jsonl` records `buffer_overflow` and `buffer_status` events.
- `detected_patterns.json` records complete-line pattern matches with raw line bytes encoded as base64.
- `metadata.json` currently tracks required Phase 1 flags and segment timestamp bounds.
- Reconnect/resume mutation helpers are not implemented yet.

## Device Core Service Requirements

The Device Core Service is a persistent FastAPI process that owns the selected
serial port and exposes local HTTP endpoints. With a serial port, startup opens
the command transport, validates the first `hello`, and applies configured
hardware mappings. Without a selected port, it runs in a disconnected state.

Currently implemented endpoints:

- `GET /status`
- `POST /gpio/mode`
- `POST /dut/reset`
- `POST /dut/boot-mode`

Remaining target Phase 1 endpoints:

- `POST /dut/capture`
- `GET /dut/logs`
- `POST /dut/wait-pattern`
- `POST /dut/boot-test`
- `POST /dut/uart/send`
- `GET /sessions`
- `GET /sessions/{id}`
- `POST /sessions/{id}/baseline`

All endpoints return JSON. Errors use:

```json
{"ok": false, "error": "<code>", "detail": "..."}
```

`GET /status` must include GPIO/control mapping state so users and agents can
see which required roles are configured, rejected, or still unconfigured. The
status payload should include the role, physical channel, DUT signal name, mode,
source, and last rejection detail when present.

`POST /gpio/mode` is the Phase 1 runtime override endpoint for a configured
role. It must return the accepted role, channel, DUT signal name, mode, source,
and optional firmware timestamp. Rejections must leave prior accepted state
unchanged.

Capture-like responses must include `interrupted`, `resumed`, and `segments` in addition to `overflow`.

Buffer sizing and validation are defined in `docs/ring_buffer_sizing_plan.md`. Phase 1 firmware must make overflow observable and should expose high-water mark, dropped-byte count, and overflow-event count for validation.

## CLI Requirements

The CLI is a thin HTTP client. It must not import hardware transport code directly.

Minimum Phase 1 commands:

- `dutchmate start`
- `dutchmate stop`
- `dutchmate status`

Currently implemented startup/discovery behavior:

- `dutchmate devices [--all]` lists DUTchMate candidates or all serial ports.
- `dutchmate start --serial-port <device>` selects an explicit device.
- Without `--serial-port`, start auto-selects exactly one DUTchMate candidate,
  starts disconnected when there are none, and rejects ambiguous multiple
  candidates.

Currently implemented hardware-control commands:

- `dutchmate gpio mode <channel> <role> <dut_signal> --mode <open_drain|push_pull> --active-level <low|high> [--idle-level <low|high>]`
- `dutchmate dut reset [--pulse-ms <ms>]`
- `dutchmate dut boot-mode <normal|bootloader>`

Remaining target Phase 1 commands:

- `dutchmate capture --seconds <seconds>`
- `dutchmate logs --last <lines>`
- `dutchmate wait <pattern> --timeout <seconds>`
- `dutchmate boot-test --seconds <seconds>`
- `dutchmate send <cmd> [--force]`
- `dutchmate mark-baseline <session_id>`

If the service is not running, commands must fail with:

```text
Error: Device Core Service is not running. Run 'dutchmate start' first.
```

## Testing Requirements

Any workflow exposed through the CLI must first pass through these layers:

1. Device Core unit tests using mocked protocol messages.
2. Device Core Service integration tests using a mock serial transport.
3. CLI tests against the service API.
4. Hardware smoke test, when hardware behavior is involved.

Minimum Phase 1 test coverage:

- Valid `hello` handshake.
- Protocol version mismatch.
- Malformed JSON line.
- Unknown message type.
- Invalid base64 payload.
- UART payload containing invalid UTF-8.
- Pattern split across multiple UART packets.
- Buffer overflow event propagation.
- Buffer telemetry records high-water mark and dropped-byte count.
- Deliberate overflow stress sets session `overflow: true`.
- Capture truncation at session size cap.
- USB disconnect marking `interrupted: true`.
- Reconnect before timeout appending a new session segment.
- Reconnect after timeout ending the interrupted session.
- Timestamp discontinuity represented with a new `timestamp_epoch`.
- Reset rejected before `reset` role mapping/mode configuration.
- Boot-mode rejected before `boot` role mapping/mode configuration.
- Invalid hardware mapping rejected: unknown channel, duplicate channel, wrong channel type, or empty `dut_signal`.
- Config-file hardware control mode accepted after firmware `hello`.
- Startup GPIO mode rejection visible in service status.
- Runtime GPIO mode override leaves prior accepted mode unchanged if rejected.
- Hardware command rejected while capture is active.

## Done Criteria

Phase 1 is done when:

- `dutchmate start` starts the local Device Core Service.
- The service connects to one DUTchMate Debug Helper.
- `.dutchmate/config.toml` can map `reset` to a physical `CTRLx` channel and
  DUT schematic signal.
- `dutchmate gpio mode CTRL0 reset RESET_N --mode open_drain --active-level low` configures the mapped reset role.
- `dutchmate boot-test --seconds 15` creates a session.
- The session contains raw UART bytes, parsed events, metadata, and detected patterns.
- `overflow`, `truncated`, `interrupted`, `resumed`, and segment count are represented in session metadata and API responses.
- 32 KiB UART RX buffer passes the Phase 1 validation criteria or the sizing plan records why it changed.
- The CLI can retrieve recent logs and mark a baseline session.
- Host-side unit and integration tests pass with mocked NDJSON streams.
- A real RP2040 + DUT smoke test demonstrates reset, capture, and session storage.
