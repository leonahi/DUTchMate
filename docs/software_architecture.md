# Software Architecture

> Status: current implementation with Phase 1 migration boundaries
> Scope: host-side Python layers, dependency direction, data flow, and code ownership.

This document describes how the repository is organized today. It records
target behavior only when needed to explain a current migration boundary.
`docs/phase1_implementation_spec.md` owns the complete target contracts and done
criteria.

## Goals

- Keep protocol parsing, UART processing, persistence, and workflows separate.
- Preserve raw evidence before deriving text, lines, patterns, or summaries.
- Test the host pipeline without physical serial hardware.
- Keep `core` independent from CLI, service, MCP, and AI packages.
- Place Basic and Enhanced backends behind one normalized event boundary.

## Current Layers

```text
apps/cli
  -> HTTP client for apps/service

apps/service
  -> process/runtime ownership
  -> core

core/runtime
  -> workflows
  -> gpio_config
  -> backends contracts/adapters
  -> device_connection

core/workflows.capture
  -> session_store
  -> uart_capture
  -> backends.contracts

core/workflows.enhanced_capture
  -> workflows.capture
  -> backends.enhanced

core/uart_capture
  -> log_processing
  -> backends.contracts

core/session_store
  -> uart_capture results
  -> backends.contracts

core/workflows.device_actions, gpio_config
  -> device_connection commands/responses

core/device_connection
  -> no higher DUTchMate layer
```

Shared capture, UART processing, and storage now use the target normalized event
dependency direction:

```text
workflows, uart_capture, session_store
  -> backends.contracts

backends.basic
  -> serial primitives
  -> backends.contracts

backends.enhanced
  -> device_connection
  -> backends.contracts

device_connection
  -> Enhanced wire protocol only
```

Only the Enhanced adapter may translate `HelloMessage`, `UartMessage`, command
responses, and telemetry messages. Shared layers consume the normalized
`BackendEventSource` contract defined in
`docs/phase1_implementation_spec.md`. The remaining migration boundary is the
synchronous interim source: Phase 1 replaces it with one asynchronous
background reader and complete connection/segment coordinator.

## Data Flow

The implemented fixture/mock path is:

```text
NDJSON bytes
  -> NdjsonStreamParser
  -> parse_device_message
  -> EnhancedNdjsonEventStream
  -> normalized backend events
  -> enhanced_capture.CaptureStreamRecorder
  -> CaptureRecorder
  -> UartCaptureProcessor
  -> UartLineBuffer
  -> PatternDetector
  -> SessionStore
  -> SessionSummary
```

The implemented finite serial path is:

```text
SerialCommandTransport queued/new messages
  -> EnhancedCaptureEventSource
  -> normalized backend events
  -> DeviceCoreRuntime.capture_uart / run_boot_test
  -> TransportCaptureRunner
  -> CaptureRecorder
  -> UartCaptureProcessor
  -> PatternDetector
  -> SessionStore
  -> SessionSummary
```

`DeviceCoreRuntime` publishes the active session while a finite workflow runs
and rejects conflicting capture or hardware-changing operations. The current
serial path is synchronous and Debug Helper-oriented. Phase 1 replaces its
input edge with one continuous reader and a FIFO normalized event source for
either backend; downstream processing remains shared.

## Module Ownership

### `device_connection`

Owns the current Enhanced v1 wire protocol and serial primitives:

- typed `hello`, UART, buffer telemetry, and command-response messages
- host command encoders for GPIO mode, reset, boot mode, and UART send
- base64 decoding and lossy UART display projection
- NDJSON chunk buffering and message validation
- serial-port discovery and the synchronous command transport
- queuing non-response UART/telemetry messages while waiting for a command
  response, then returning them in FIFO order

Current limitations that move together in Phase 1B:

- the capability is still named `uart_capture` rather than `uart_receive`
- wire actions are role-specific `reset`/`set_boot_mode` rather than generic
  configured-channel actions
- `configure_gpio_mode` still sends host role metadata
- receive framing is unbounded and uses generic surrounding-whitespace removal
- schemas and runtime validators do not yet enforce all target byte limits
- the transport does not yet prove complete acceptance of short serial writes

Schemas, examples, parser/encoder models, tests, and firmware must change
atomically. `hardware/protocol/v1/` is the wire authority.

### `uart_capture`

Owns raw UART byte-to-line processing:

- `UartLineBuffer` assembles newline-terminated lines
- buffers are independent per segment and UART channel
- `UartLine` retains raw bytes, lossy display text, and source event/byte boundaries
- `UartCaptureProcessor` sends complete lines to pattern detection
- derived state is capped at 65536 exact bytes per physical line; oversized
  lines switch to constant-memory counting and produce boundary-only descriptors

It does not write files. It consumes normalized `UartReceiveEvent` objects and
isolates line assembly and limit state by segment/channel. The limit never
truncates raw session evidence and matching resumes with the next physical line.

### `log_processing`

Owns case-sensitive pattern detection on complete lossy-display lines. Current
defaults are `ERROR`, `ASSERT`, `PANIC`, `HardFault`, and `BOOT_OK`.

`PatternMatch` records the complete source line internally plus the first raw
byte span for each matching literal. Session persistence classifies failure
versus success patterns, chooses deterministic `first_error`, and stores a
bounded exact-byte excerpt. Pattern processing remains pure and does not own
persistence or backend I/O.

### `session_store`

Owns filesystem-backed sessions under
`.dutchmate/sessions/<session_id>/`. It currently:

- creates `metadata.json`, `uart_raw.log`, `uart_events.jsonl`,
  `hardware_events.jsonl`, and `detected_patterns.json`
- appends exact UART bytes and structured events incrementally
- consumes normalized UART and buffer-telemetry events rather than Enhanced
  wire-message models
- stores buffer overflow/status telemetry and detected patterns
- stores bounded detected-pattern excerpts and derives deterministic
  reference-bearing `first_error` summaries in segment/event order
- stores `line_processing` status/counts and finalized `line_limit_exceeded`
  descriptors without changing UART integrity or session truncation
- creates native runtime sessions with versioned workflow/lifecycle fields and
  a terminal reserve, then transitions them once to completed or failed
- performs schema-aware startup recovery before backend opening, abandoning
  stale native active sessions while preserving legacy/unsupported evidence
- summarizes one session, lists valid sessions newest-first, and resolves the
  latest session
- rejects path-unsafe session IDs

Runtime capture/boot-test sessions with complete backend identity now use schema
version 1 and snapshot backend facts, accepted timing policy, integrity, line
processing, storage accounting, and one-way lifecycle state. Older direct-store
fixtures retain their recognized unversioned legacy shape. Admission quotas,
retention, baseline, reconnect, and bounded replay remain. Startup recovery
retains structured diagnostics for malformed/reserve conditions and treats a
failed terminal metadata replacement as a startup error.
The remaining rules are centralized in the Phase 1 spec and
`docs/reconnect_session_semantics.md`; they are not repeated here.

### `gpio_config`

Owns host control-channel mapping, validation, and accepted/rejected state. It:

- loads `[hardware.control.*]` mappings
- tracks `CTRL0` through `CTRL3` as `unconfigured`, `configured`, or `rejected`
- sends configuration through an injected transport
- changes accepted state only after firmware acknowledgement
- preserves a prior accepted state when an override is rejected
- records role, channel, DUT signal, mode/levels, source, host configuration
  time, optional raw device timestamp, and rejection detail
- resolves roles for reset and boot workflows

The shared validator preserves exact 1..64-byte UTF-8 role and DUT-signal
identifiers, rejects edge whitespace and Unicode control characters, and
enforces the open-drain/push-pull electrical matrix. Config loading, runtime
state, Enhanced command encoding, service schemas, and CLI dispatch use the
same contract. The canonical state, validation order, and workflow rules live
in `docs/gpio_configuration_semantics.md`.

### `workflows`

Owns deterministic orchestration, not serial-port discovery or low-level
protocol validation. Current behavior includes:

- capture from parsed messages or NDJSON fixtures
- finite transport-backed capture using a host-monotonic deadline
- reset and boot-mode actions through an injected transport
- reset-triggered boot-test recording
- active-session publication and conflict cleanup in `DeviceCoreRuntime`
- required accepted `reset`/`boot` role checks

Capture and boot-test validation consistently enforces the Phase 1
`0 < duration_s <= 300` contract before HTTP dispatch or workflow/session work.
Native workflows persist and echo accepted duration/reconnect policy and
terminal lifecycle state, and startup abandons stale active sessions before
opening a backend. Wait-pattern, UART-send exposure, reconnect/resume, and full
durability guarantees remain Phase 1 work.

### `backends` (Contract Foundation)

This package defines backend-neutral identity, timestamp provenance, normalized
UART/telemetry events, the asynchronous event-source protocol, and distinct
disconnect/input errors. Shared fake Basic and Enhanced sources verify the same
FIFO/timeout/error contract. Shared settings resolve explicit Basic/Enhanced
selection, exact serial ports, backend-specific baudrates, 8-N-1 framing, TX
policy, and reconnect timeout. Basic connection setup opens raw serial without
reading a `hello`. Its event source lazily starts one serial-reader thread,
converts each delivered byte chunk to one FIFO normalized event with
host-monotonic provenance, and exposes a blocking compatibility read to the
current shared capture runner. Basic UART writes are capability-gated and retry
ordered short writes to completion. An interim Enhanced adapter translates
parsed v1 messages and synchronous read timeouts before shared capture. When
its device-timer origin is unavailable at connection creation, the first
timestamped evidence event establishes the segment origin and is normalized to
zero before its immutable context is persisted. The package will additionally
own:

- Enhanced NDJSON adaptation with device timestamp and telemetry provenance
- continuous background ingestion and lifecycle ownership beyond finite captures
- normalized UART-send completion results plus control and future event interfaces

It will not decode lines, detect patterns, persist sessions, handle HTTP, or
format CLI output.

## Application Boundaries

### Device Core Service

`apps/service` owns the local FastAPI process, selected serial connection, and
runtime composition. Current endpoints cover status, finite capture, boot-test,
GPIO mode, reset, and boot mode. Handlers should remain thin: core code owns
validation order, state transitions, and deterministic behavior; service code
owns request/response serialization and HTTP error mapping.

The service accepts one explicit Basic/Enhanced selection. Basic requires and
opens a raw serial port without `hello`, wiring its normalized source into the
same finite capture path. Enhanced validates `hello` when a port is selected
and may start disconnected without one. Status and finite capture responses
serialize backend identity, raw/effective capabilities, TX-policy provenance,
segment timing, and UART-loss integrity. Continuous background ingestion,
reconnect, bounded log/session retrieval, wait-pattern, public UART send,
baseline operations, and the complete target error projection remain Phase 1
work.

### CLI

`apps/cli` is an HTTP client for the Device Core Service. It owns process
lifecycle commands, request construction, and human-readable output. It must
not import low-level transport code or open serial ports for debug workflows.

Current commands cover explicit Basic/Enhanced startup selection, service
lifecycle, labeled device listing, status, capture, boot-test, GPIO mode,
reset, and boot mode. Logs, sessions, wait-pattern, UART send, and baseline
commands remain pending.

### MCP Server

`apps/mcp_server` is a Phase 2 package scaffold. The future stdio server calls
the same Device Core Service API as the CLI and owns no serial, session, GPIO,
or AI logic. See `docs/mcp_integration_plan.md`.

## Boundary Rules

- `core` does not import any app or AI package.
- `device_connection` knows the Enhanced protocol, not sessions or workflows.
- `backends` owns device-specific adaptation, not line or session processing.
- `uart_capture` owns bounded derived buffering, not persistence.
- `log_processing` remains deterministic and hardware-free.
- `session_store` owns durable evidence, not serial parsing.
- `gpio_config` owns accepted mapping state, not physical transport ownership.
- `workflows` coordinate lower layers but do not duplicate wire validation.
- Service and CLI layers do not reinterpret core state or error semantics.

## Current Verification Surface

The test suite currently covers protocol parsing/encoding and NDJSON buffering;
UART line processing and patterns; session creation, evidence writes, telemetry,
summaries, and discovery; GPIO configuration state; fixture and finite transport
capture; reset/boot-mode and boot-test orchestration; runtime conflict cleanup;
service endpoints; CLI clients; serial discovery and backend selection; Basic
no-hello raw opening, normalized FIFO receive/provenance, shared capture, and
full-write behavior; capability-policy filtering; backend/session identity,
per-segment provenance, and integrity serialization; Enhanced startup `hello`
validation; and startup hardware mapping.

Use focused tests during development and the full suite before a commit:

```bash
uv run pytest tests/unit/protocol
uv run pytest tests/unit/uart_capture tests/unit/log_processing
uv run pytest tests/unit/session_store tests/unit/workflows tests/unit/runtime
uv run pytest apps/service/tests apps/cli/tests
uv run pytest
```

Phase 1 test requirements, backend-specific coverage, HIL fixture behavior, and
done criteria are maintained only in `docs/phase1_implementation_spec.md`.
