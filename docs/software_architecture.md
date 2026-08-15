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
  -> device_connection

core/workflows
  -> session_store
  -> uart_capture
  -> gpio_config
  -> device_connection

core/uart_capture
  -> log_processing
  -> device_connection message models

core/session_store
  -> uart_capture results
  -> device_connection message models

core/device_connection
  -> no higher DUTchMate layer
```

The current dependency on `device_connection` message models in shared capture
and storage code is the main Phase 1 migration boundary. The target graph is:

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
`docs/phase1_implementation_spec.md`.

## Data Flow

The implemented fixture/mock path is:

```text
NDJSON bytes
  -> NdjsonStreamParser
  -> parse_device_message
  -> CaptureStreamRecorder
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
- buffers are independent per UART channel
- `UartLine` retains raw bytes and lossy display text
- `UartCaptureProcessor` sends complete lines to pattern detection

It does not write files. It currently consumes Enhanced `UartMessage` objects
and has no line-size limit. Phase 1 changes the input to normalized UART events
and adds bounded per-segment/channel line assembly while keeping raw session
evidence intact.

### `log_processing`

Owns case-sensitive pattern detection on complete lossy-display lines. Current
defaults are `ERROR`, `ASSERT`, `PANIC`, `HardFault`, and `BOOT_OK`.

Current `PatternMatch` records the complete source line. Phase 1 classifies
failure versus success patterns, chooses deterministic `first_error`, retains
raw byte offsets, and stores a bounded excerpt. It remains pure processing and
does not own persistence or backend I/O.

### `session_store`

Owns filesystem-backed sessions under
`.dutchmate/sessions/<session_id>/`. It currently:

- creates `metadata.json`, `uart_raw.log`, `uart_events.jsonl`,
  `hardware_events.jsonl`, and `detected_patterns.json`
- appends exact UART bytes and structured events incrementally
- stores buffer overflow/status telemetry and detected patterns
- summarizes one session, lists valid sessions newest-first, and resolves the
  latest session
- rejects path-unsafe session IDs

Current metadata is unversioned and lacks the target lifecycle, quota,
retention, baseline, reconnect, backend identity, timestamp provenance, and
bounded replay contracts. Those rules are centralized in the Phase 1 spec and
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

The current validators accept broadly non-empty identifiers and inconsistently
trim them. Phase 1 introduces one exact shared identifier validator and the
mode-specific electrical matrix. The canonical state, validation order, and
workflow rules live in `docs/gpio_configuration_semantics.md`.

### `workflows`

Owns deterministic orchestration, not serial-port discovery or low-level
protocol validation. Current behavior includes:

- capture from parsed messages or NDJSON fixtures
- finite transport-backed capture using a host-monotonic deadline
- reset and boot-mode actions through an injected transport
- reset-triggered boot-test recording
- active-session publication and conflict cleanup in `DeviceCoreRuntime`
- required accepted `reset`/`boot` role checks

Current duration validation rejects invalid/non-positive values but does not
enforce the target 300-second maximum. Wait-pattern, UART-send exposure,
reconnect/resume, and durable lifecycle handling remain Phase 1 work.

### `backends` (Contract Foundation)

This package now defines backend-neutral identity, timestamp provenance,
normalized UART/telemetry events, the asynchronous event-source protocol, and
distinct disconnect/input errors. Shared fake Basic and Enhanced sources verify
the same FIFO/timeout/error contract. It will additionally own:

- Basic raw-serial adaptation with host timestamp provenance
- Enhanced NDJSON adaptation with device timestamp and telemetry provenance
- one reader and FIFO event queue per selected backend
- backend support versus effective host-policy capabilities
- separate capability-gated UART send, control, and future event interfaces

It will not decode lines, detect patterns, persist sessions, handle HTTP, or
format CLI output.

## Application Boundaries

### Device Core Service

`apps/service` owns the local FastAPI process, selected serial connection, and
runtime composition. Current endpoints cover status, finite capture, boot-test,
GPIO mode, reset, and boot mode. Handlers should remain thin: core code owns
validation order, state transitions, and deterministic behavior; service code
owns request/response serialization and HTTP error mapping.

The service currently treats selected devices as Enhanced and validates a
`hello`. Explicit Basic/Enhanced startup, background ingestion, reconnect,
bounded log/session retrieval, wait-pattern, UART send, baseline operations,
and the complete target error projection remain Phase 1 work.

### CLI

`apps/cli` is an HTTP client for the Device Core Service. It owns process
lifecycle commands, request construction, and human-readable output. It must
not import low-level transport code or open serial ports for debug workflows.

Current commands cover service lifecycle, device listing, status, capture,
boot-test, GPIO mode, reset, and boot mode. Target Basic/Enhanced selection,
logs, sessions, wait-pattern, UART send, and baseline commands remain pending.

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
service endpoints; CLI clients; serial discovery; startup `hello` validation;
and startup hardware mapping.

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
