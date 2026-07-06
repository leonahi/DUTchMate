# Phase 1 Implementation Spec

> Status: draft
> Scope: RP2040 Debug Helper MVP, Device Core Service, host CLI, and testable protocol/session contracts.

## Goal

Prove the core hardware-in-the-loop workflow:

```text
build firmware -> flash DUT externally -> reset DUT -> capture timestamped UART logs -> store evidence -> detect failure
```

Phase 1 is successful when DUTchMate can run a boot test against one DUT, preserve raw UART evidence, and return structured results through the local CLI and Device Core Service.

## Non-Goals

- MCP integration
- AI log summaries or LLM-based diagnosis
- MessagePack + COBS protocol encoding
- GUI
- Multi-DUT support
- Power/current/voltage sensing
- JTAG/SWD debugging
- Firmware flashing

Phase 2 MCP integration is planned in `docs/mcp_integration_plan.md`. Phase 1 should keep the Device Core Service API stable enough for the later `dutchmate mcp` stdio adapter, but must not implement MCP before CLI workflows are validated.

## Implementation Order

Phase 1 should be built host-side first with mocked protocol fixtures, then connected to real firmware and hardware.

1. Define protocol schemas and canonical examples.
2. Implement Device Core protocol parsing and event models.
3. Implement UART byte preservation, lossy UTF-8 display text, and complete-line buffering.
4. Implement session storage.
5. Implement pattern detection on complete decoded lines.
6. Implement Device Core workflows using a mock serial transport.
7. Expose workflows through the Device Core Service API.
8. Add the CLI as a thin HTTP client.
9. Implement RP2040 firmware to satisfy the v1 protocol.
10. Run hardware smoke tests with a real DUT.

## Package Layout

```text
apps/
  cli/           Human-facing command-line client.
  service/       FastAPI Device Core Service; owns the serial port.
  mcp_server/    Phase 2 only.

core/
  device_connection/   Serial transport and host-device protocol handling.
  uart_capture/        UART event ingestion, byte preservation, and line buffering.
  reset_control/       Reset and boot-mode workflows.
  session_store/       Debug session persistence and retention.
  log_processing/      Pattern detection and log extraction.
  workflows/           Boot test, capture, wait-pattern, and reset-capture flows.

hardware/
  firmware/      RP2040 firmware.
  protocol/      Versioned protocol schemas, examples, and fixtures.
  schematics/    Debug Helper hardware design files.

tests/
  unit/          Parser, line-buffering, pattern, and session tests.
  integration/   Device Core Service tests using mock serial streams.
  fixtures/      Pre-recorded protocol streams and expected outputs.
```

## Phase 1 Protocol Contract

The host-device protocol is NDJSON over USB CDC serial. Each line is one JSON message. The v1 schemas live under `hardware/protocol/v1/`.

Only the following host-to-device commands are in scope:

- `configure_gpio_mode`
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
- Enforce accepted GPIO modes before reset and boot-mode operations.
- Track each GPIO mode as `unconfigured`, `configured`, or `rejected`.
- Treat config-file GPIO modes as explicit configuration only after firmware accepts them.
- Preserve the previous accepted GPIO mode when a runtime override is rejected.
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

## Device Core Service Requirements

The Device Core Service is a persistent FastAPI process that owns the serial port and exposes local HTTP endpoints.

Minimum Phase 1 endpoints:

- `GET /status`
- `POST /gpio/mode`
- `POST /dut/reset`
- `POST /dut/boot-mode`
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

`GET /status` must include `gpio_modes` so users and agents can see which pins are configured, rejected, or still unconfigured.

`POST /gpio/mode` must return the accepted pin, mode, source, and optional firmware timestamp. Rejections must leave prior accepted state unchanged.

Capture-like responses must include `interrupted`, `resumed`, and `segments` in addition to `overflow`.

Buffer sizing and validation are defined in `docs/ring_buffer_sizing_plan.md`. Phase 1 firmware must make overflow observable and should expose high-water mark, dropped-byte count, and overflow-event count for validation.

## CLI Requirements

The CLI is a thin HTTP client. It must not import hardware transport code directly.

Minimum Phase 1 commands:

- `dutchmate start`
- `dutchmate stop`
- `dutchmate status`
- `dutchmate gpio-mode <pin> <mode>`
- `dutchmate reset`
- `dutchmate boot-mode <normal|bootloader>`
- `dutchmate capture --seconds <seconds>`
- `dutchmate logs --last <lines>`
- `dutchmate wait <pattern> --timeout <seconds>`
- `dutchmate boot-test --seconds <seconds>`
- `dutchmate send <cmd> [--force]`
- `dutchmate mark-baseline <session_id>`

If the service is not running, commands must fail with:

```text
Error: service not running. Run 'dutchmate start' first.
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
- Reset rejected before GPIO mode configuration.
- Config-file GPIO mode accepted after firmware `hello`.
- Startup GPIO mode rejection visible in service status.
- Runtime GPIO mode override leaves prior accepted mode unchanged if rejected.
- Hardware command rejected while capture is active.

## Done Criteria

Phase 1 is done when:

- `dutchmate start` starts the local Device Core Service.
- The service connects to one DUTchMate Debug Helper.
- `dutchmate gpio-mode reset open_drain` configures reset behavior.
- `dutchmate boot-test --seconds 15` creates a session.
- The session contains raw UART bytes, parsed events, metadata, and detected patterns.
- `overflow`, `truncated`, `interrupted`, `resumed`, and segment count are represented in session metadata and API responses.
- 32 KiB UART RX buffer passes the Phase 1 validation criteria or the sizing plan records why it changed.
- The CLI can retrieve recent logs and mark a baseline session.
- Host-side unit and integration tests pass with mocked NDJSON streams.
- A real RP2040 + DUT smoke test demonstrates reset, capture, and session storage.
