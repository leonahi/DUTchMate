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

uart_capture
  turns UART byte chunks into complete lines and capture results

log_processing
  detects configured patterns on complete UART lines

device_connection
  owns host-device protocol models, parsing, encoding, and NDJSON framing
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

## Dependency Direction

Dependencies should point from higher-level orchestration toward lower-level
building blocks.

```text
workflows
  -> session_store
  -> uart_capture
  -> device_connection

session_store
  -> device_connection message models
  -> uart_capture capture result model

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

Important behavior:

- `data_b64` is decoded to raw bytes.
- UART display text is derived with lossy UTF-8 replacement.
- Protocol validation errors are raised before data reaches higher layers.

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

### `workflows`

Owns current host-side capture coordination.

Implemented responsibilities:

- `CaptureRecorder` records already-parsed capture messages:
  - `UartMessage`
  - `BufferOverflowMessage`
  - `BufferStatusMessage`
- `CaptureStreamRecorder` accepts raw NDJSON byte chunks and routes supported
  capture messages into `CaptureRecorder`.
- `run_mock_capture(...)` records a finite mocked NDJSON stream and returns a
  `SessionSummary`.

Important behavior:

- `hello` and command response messages are ignored by capture recorders for
  now.
- The workflow layer is hardware-free; it does not open serial ports.
- Tests exercise the current capture path using mocked NDJSON bytes.

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
- Session summaries.
- Capture recorders from typed messages and NDJSON byte chunks.
- Mock capture summary generation.

Focused host-side core test command:

```bash
uv run pytest tests/unit/workflows tests/unit/session_store tests/unit/log_processing tests/unit/uart_capture tests/unit/protocol
```

## Not Implemented Yet

The following layers or behaviors are not part of the current implemented
architecture yet:

- `reset_control` package.
- GPIO mode state machine.
- Reset and boot-mode workflow enforcement.
- Serial port transport abstraction.
- Long-running capture with duration/timeout handling.
- Reconnect/resume session mutation helpers.
- Device Core Service API.
- CLI HTTP client behavior.
- RP2040 firmware.
- Hardware smoke tests.
