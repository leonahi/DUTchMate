# Software Architecture

> Status: current-state reference
> Scope: host-side Python architecture implemented so far for Phase 1.

This document explains how the current DUTchMate Python core is organized, how
data flows through it, and which dependencies are allowed. It describes the
code that exists now. It is not a roadmap.

## Goals

- Keep protocol parsing, UART processing, session storage, and workflows in
  separate layers.
- Preserve raw hardware evidence before deriving higher-level views from it.
- Make the host-side capture flow testable without real serial hardware.
- Keep `core` independent from CLI, service, MCP, and AI/LLM code.

## Layer Overview

```text
workflows
  coordinates capture flows and returns workflow/session results

session_store
  persists evidence and metadata to filesystem sessions

gpio_config
  sends GPIO mode configuration commands through an injected transport and tracks accepted/rejected state

uart_capture
  turns UART byte chunks into complete lines and capture results

log_processing
  detects configured patterns on complete UART lines

device_connection
  owns host-device protocol models, parsing, encoding, NDJSON framing,
  serial discovery, and synchronous command transport
```

The main implemented host-side capture path is:

```text
NDJSON byte chunks
  -> device_connection.NdjsonStreamParser
  -> device_connection.parse_device_message
  -> workflows.CaptureStreamRecorder
  -> workflows.CaptureRecorder
  -> uart_capture.UartCaptureProcessor
  -> uart_capture.UartLineBuffer
  -> log_processing.PatternDetector
  -> session_store.SessionStore
  -> session_store.SessionSummary
```

The finite transport-backed capture path is:

```text
device_connection.SerialCommandTransport queued/new messages
  -> runtime.DeviceCoreRuntime.capture_uart
  -> workflows.TransportCaptureRunner
  -> workflows.CaptureRecorder
  -> uart_capture.UartCaptureProcessor
  -> log_processing.PatternDetector
  -> session_store.SessionStore
  -> session_store.SessionSummary
```

## Dependency Direction

Dependencies should point from higher-level orchestration toward lower-level
building blocks.

```text
workflows
  -> session_store
  -> uart_capture
  -> gpio_config
  -> device_connection

session_store
  -> device_connection message models
  -> uart_capture capture result model

gpio_config
  -> device_connection GPIO command encoder and command response models

uart_capture
  -> device_connection UART message model
  -> log_processing pattern detector

log_processing
  -> uart_capture UartLine model

device_connection
  -> no DUTchMate core layers below it
```

Boundary rules:

- `core` must not import `apps/cli`, `apps/service`, `apps/mcp_server`, or AI
  packages.
- `device_connection` should stay protocol-focused. It should not know about
  sessions, files, workflows, HTTP, CLI, or MCP.
- `log_processing` should remain pure text/line processing.
- `uart_capture` may hold buffering state, but should not write files.
- `session_store` owns filesystem persistence, not serial parsing.
- `gpio_config` owns GPIO hardware mapping validation and GPIO mode
  configuration workflow/state. It sends encoded commands through an injected
  transport, but does not open serial ports or toggle physical pins directly.
- `workflows` may coordinate lower layers, but should not contain low-level
  protocol validation logic.

## Module Responsibilities

### `device_connection`

Owns the v1 host-device protocol.

Implemented responsibilities:

- Typed device-to-host messages:
  - `HelloMessage`
  - `UartMessage`
  - `BufferOverflowMessage`
  - `BufferStatusMessage`
  - command success/error responses
- Host-to-device command encoders:
  - `configure_gpio_mode`
  - `reset`
  - `set_boot_mode`
  - `uart_send`
- `parse_device_message(...)` for one complete JSON message.
- `NdjsonStreamParser` for buffering serial byte chunks into complete NDJSON
  messages.
- Serial-port discovery with normalized USB metadata and DUTchMate text-hint
  filtering.
- `SerialCommandTransport` for newline-terminated command exchange over a
  pyserial port.
- `open_serial_command_transport(...)` for opening the selected device.

Important behavior:

- `data_b64` is decoded to raw bytes.
- UART display text is derived with lossy UTF-8 replacement.
- Protocol validation errors are raised before data reaches higher layers.
- Command requests queue intervening non-response messages in FIFO order until
  a command success or error is received.
- `read_message()` returns queued messages before reading new serial data, and
  `drain_pending_messages()` provides non-blocking access to the current queue.
- Serial read timeouts and incomplete lines raise transport errors.

### `uart_capture`

Owns UART byte-to-line processing.

Implemented responsibilities:

- `UartLineBuffer` buffers raw UART bytes until newline-terminated lines are
  available.
- `UartLine` carries both raw line bytes and lossy display text.
- `UartCaptureProcessor` processes `UartMessage` objects into:
  - completed UART lines
  - detected pattern matches
  - channel/timestamp context

Important behavior:

- Raw UART chunks may split log lines; line buffering prevents pattern detection
  from missing split patterns.
- Buffers are kept per UART channel, so different channels cannot be joined
  accidentally.
- `message.data` is the source of truth for capture bytes.

### `log_processing`

Owns pattern detection on completed UART lines.

Implemented responsibilities:

- `PatternDetector` scans `UartLine.text`.
- `PatternMatch` records the matched pattern plus the source line text/raw
  bytes.
- Default patterns:
  - `ERROR`
  - `ASSERT`
  - `PANIC`
  - `HardFault`
  - `BOOT_OK`

Important behavior:

- Pattern matching is case-sensitive.
- Pattern detection uses complete decoded lines, not partial UART chunks.
- Pattern detection uses text, while raw bytes remain preserved separately.

### `session_store`

Owns filesystem-backed session persistence.

Implemented responsibilities:

- Creates session directories under `.dutchmate/sessions/<session_id>/`.
- Initializes required Phase 1 files:

```text
metadata.json
uart_raw.log
uart_events.jsonl
hardware_events.jsonl
detected_patterns.json
```

- Appends UART evidence incrementally:
  - raw bytes to `uart_raw.log`
  - structured UART events to `uart_events.jsonl`
  - detected pattern records to `detected_patterns.json`
- Appends hardware telemetry:
  - `buffer_overflow`
  - `buffer_status`
- Updates metadata:
  - `overflow`
  - segment first/last device timestamps
- Provides `SessionSummary` via `summarize_session(...)`.

Important behavior:

- Raw UART bytes are preserved losslessly.
- JSONL event files are append-only for incoming events.
- UART events include `segment_id` and `timestamp_epoch`.
- Buffer telemetry with drops or overflow events marks the session as overflowed.

### `gpio_config`

Owns current Debug Helper GPIO mapping validation and mode configuration
workflow/state.

Implemented responsibilities:

- Loads and validates `[hardware.control.*]` TOML mappings for Phase 1 control
  roles.
- Builds and sends `configure_gpio_mode` commands through a caller-provided
  transport.
- Updates state only after a command success or command error response.
- Tracks Phase 1 physical control channels:
  - `CTRL0`
  - `CTRL1`
  - `CTRL2`
  - `CTRL3`
- Tracks whether each channel is:
  - `unconfigured`
  - `configured`
  - `rejected`
- Records role, physical channel, DUT schematic signal name, accepted mode,
  active/idle levels, source, host timestamp, optional device timestamp, and
  last rejection detail.
- Preserves the previous accepted mode when a later runtime override is
  rejected.
- Provides role lookup helpers for reset/boot workflows.

Important behavior:

- Invalid channel/role/mode/level values are rejected before a transport
  request is made.
- Config-file mappings reject unknown fields, missing required fields, invalid
  DUT I/O voltage, and duplicate physical channels.
- A configured role can be moved to another channel without leaving a duplicate
  role assignment behind.
- `accept_mode(...)` records that firmware already accepted a GPIO mode request.
- `reject_mode(...)` records that firmware or Device Core rejected a GPIO mode
  request.
- Unexpected non-command responses raise `GpioConfigurationError` and do not
  update registry state.
- This package does not own the real serial transport and does not toggle
  physical pins directly.
- Debug Helper channel identity is separate from DUT signal role. For example,
  `channel="CTRL0"` and `role="reset"` are stored as different fields.

### `workflows`

Owns current host-side workflow coordination.

Implemented responsibilities:

- `CaptureRecorder` records already-parsed capture messages:
  - `UartMessage`
  - `BufferOverflowMessage`
  - `BufferStatusMessage`
- `CaptureStreamRecorder` accepts raw NDJSON byte chunks and routes supported
  capture messages into `CaptureRecorder`.
- `run_mock_capture(...)` records a finite mocked NDJSON stream and returns a
  `SessionSummary`.
- `run_transport_capture(...)` reads parsed transport messages until a
  host-monotonic deadline, records supported capture messages, and returns a
  `SessionSummary`.
- `TransportCaptureRunner` lets the service-facing runtime reserve the active
  session before the finite transport read loop begins.
- `DeviceActionRunner` sends reset and boot-mode commands through a
  caller-provided transport.
- Reset actions require the `reset` role to be configured.
- Boot-mode actions require the `boot` role to be configured.

Important behavior:

- `hello` and command response messages are ignored by capture recorders for
  now.
- Transport read timeouts do not end a quiet capture before its requested
  duration.
- `DeviceCoreRuntime.capture_uart(...)` exposes the finite capture workflow to
  service orchestration, reports the active session in status, and clears it
  after success or failure.
- Runtime GPIO, reset, boot-mode, and overlapping capture operations return
  `capture_active` while a capture owns the serial message stream.
- Reset/boot command arguments are validated before checking configuration
  state or sending transport requests.
- Firmware command errors are raised as `DeviceActionError`.
- The workflow layer is hardware-free; it does not open serial ports.
- Tests exercise the current workflow paths using mocked NDJSON bytes and mock
  command transports.

## Session File Contract

### `metadata.json`

Current required fields:

```json
{
  "session_id": "...",
  "started_at": "...",
  "command": "...",
  "truncated": false,
  "interrupted": false,
  "resumed": false,
  "overflow": false,
  "baseline": false,
  "firmware": null,
  "device": null,
  "segments": []
}
```

Segments represent continuous device timestamp epochs. The current
implementation initializes segment `0` and updates its first/last device
timestamps as UART or telemetry messages are recorded.

Reconnect and multi-segment mutation helpers are not implemented yet.

### `uart_raw.log`

Append-only raw UART bytes exactly as received after base64 decoding.

This file is the primary evidence file for UART capture. Higher-level decoded
views must not replace it.

### `uart_events.jsonl`

One JSON object per UART protocol event.

Current shape:

```json
{
  "type": "uart",
  "segment_id": 0,
  "timestamp_epoch": 0,
  "timestamp_us": 100,
  "channel": 0,
  "data_b64": "...",
  "text": "..."
}
```

### `hardware_events.jsonl`

One JSON object per hardware/session telemetry event.

Currently implemented event types:

- `buffer_overflow`
- `buffer_status`

### `detected_patterns.json`

JSON array of detected pattern records.

Current shape:

```json
{
  "pattern": "ERROR",
  "segment_id": 0,
  "timestamp_epoch": 0,
  "timestamp_us": 100,
  "channel": 0,
  "line_text": "ERROR\n",
  "line_raw_b64": "RVJST1IK"
}
```

## Current Test Coverage

Current unit tests cover:

- Protocol parsing and host command encoding.
- NDJSON stream buffering.
- UART line buffering.
- Pattern detection.
- UART capture processing.
- Session creation and incremental evidence writes.
- Buffer overflow and buffer status persistence.
- GPIO configuration workflow/state tracking.
- Session summaries.
- Capture recorders from typed messages and NDJSON byte chunks.
- Reset and boot-mode workflow enforcement.
- Mock capture summary generation.
- Finite transport-backed capture deadlines and timeout handling.
- Runtime active-session reporting, conflict guards, and failure cleanup.
- Device Core Service endpoints for status, GPIO mode, reset, and boot-mode.
- CLI HTTP client commands for service lifecycle, status, GPIO mode, reset, and
  boot-mode.
- Serial command transport, serial-port discovery, startup `hello` validation,
  and startup hardware mapping application.
- CLI device listing and single-candidate startup selection.

Focused host-side core test command:

```bash
uv run pytest tests/unit/gpio_config tests/unit/runtime tests/unit/workflows tests/unit/session_store tests/unit/log_processing tests/unit/uart_capture tests/unit/protocol
```

## Not Implemented Yet

The following layers or behaviors are not part of the current implemented
architecture yet:

- Built-in workflow semantics for control roles beyond Phase 1 `reset` and
  `boot`.
- Background serial ingestion outside finite capture requests.
- Reconnect/resume session mutation helpers.
- Capture/log/session Device Core Service endpoints and request handling.
- Capture/log/session CLI commands.
- MCP server runtime.
- RP2040 firmware.
- Hardware smoke tests.
