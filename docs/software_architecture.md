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
  -> backends.contracts
  -> session_store models

core/workflows.capture
  -> session_store
  -> uart_capture
  -> backends.contracts

core/uart_capture
  -> log_processing
  -> backends.contracts

core/session_store
  -> uart_capture results
  -> backends.contracts
  -> diagnostics

core/workflows.device_actions, gpio_config
  -> backends.contracts
  -> validation

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

Enhanced byte-chunk compatibility composition is test-only:

```text
NDJSON bytes
  -> NdjsonStreamParser
  -> parse_device_message
  -> EnhancedNdjsonEventStream
  -> normalized backend events
  -> test fixture recorder
  -> CaptureRecorder
  -> UartCaptureProcessor
  -> UartLineBuffer
  -> PatternDetector
  -> SessionStore
  -> SessionSummary
```

Production workflows receive normalized events and never import Enhanced wire
messages, parsers, commands, or transports.

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

## Supported Core Facades

The intentionally small package facades are:

- `dutchmate_core`: the service-facing runtime and status types;
- `dutchmate_core.backends`: normalized backend contracts and events.

Concrete adapters, protocol DTOs, storage implementations, validation helpers,
and workflows are imported from their defining modules. Their package
`__init__.py` files are not a compatibility promise during Phase 1.

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
- retries short filesystem writes, fsyncs accepted append records, and rolls
  partial appends back to their prior length when a write fails
- replaces complete JSON documents through a synced temporary file, atomic
  rename, and parent-directory fsync
- wraps current UART, buffer-telemetry, and finalized line-limit units in a
  durable internal transaction marker with append offsets and hard-linked
  metadata/pattern preimages
- consumes normalized UART and buffer-telemetry events rather than Enhanced
  wire-message models
- stores buffer overflow/status telemetry and detected patterns
- stores bounded detected-pattern excerpts and derives deterministic
  reference-bearing `first_error` summaries in segment/event order
- stores `line_processing` status/counts and finalized `line_limit_exceeded`
  descriptors without changing UART integrity or session truncation
- preflights exact whole-unit evidence for UART receive, buffer telemetry, and
  finalized line-limit events; over-budget units are omitted atomically and
  terminalize native sessions as successful `size_limit` truncations
- creates native runtime sessions with versioned workflow/lifecycle fields and
  a terminal reserve, then transitions them once to completed or failed
- atomically closes disconnected segments and appends validated contiguous
  reconnect segments with `usb_disconnect`, `usb_reconnect`, and
  `timestamp_discontinuity` evidence
- performs schema-aware startup recovery before backend opening, abandoning
  stale native active sessions while preserving legacy/unsupported evidence
- resolves interrupted evidence transactions first: metadata-last digest
  matching commits a complete unit, while any earlier interruption restores all
  append offsets and complete-document preimages
- exposes filesystem read/write failures as a typed `persistence_fault`; native
  workflow failures use the terminal reason `persistence_error`
- summarizes one session, lists valid sessions newest-first, and resolves the
  latest session
- returns stable opaque-cursor pages and bounded native/legacy detail without
  expanding raw UART, JSONL, or detected-pattern arrays
- selects an explicit, active, or newest terminal native session and replays
  persisted UART events through the shared segment/channel line buffer, retaining
  bounded complete, partial, and oversized records with evidence coordinates
- records wait-pattern policy and authoritative detected-pattern references in
  the same native lifecycle/evidence schema used by other capture-like workflows
- rejects path-unsafe session IDs

Session persistence and service delivery share the core `diagnostics`
projection for non-empty, control-sanitized, UTF-8-safe 1024-byte error detail.
The projection owns only bounded diagnostic text; error codes, HTTP status, and
schema-defined context remain responsibilities of their originating workflow
and delivery adapter.

Runtime capture/boot-test sessions with complete backend identity now use schema
version 1 and snapshot backend facts, accepted timing policy, integrity, line
processing, storage accounting, and one-way lifecycle state. Older direct-store
fixtures retain their recognized unversioned legacy shape. The CLI propagates
the positive `sessions.max_size_mb` and optional positive `sessions.max_count`
settings through service startup. Each native session snapshots and enforces
the exact resulting byte budget. When the count limit is configured, the store
runs retention after startup recovery and terminal transitions under the same
lock used by bounded readers. It removes oldest terminal native sessions while
protecting active, legacy, baseline-designated, and in-progress read evidence;
blocked or unsafe passes are exposed through service status. The adjacent
baseline module owns the atomic versioned `baseline.json` pointer, target
eligibility, idempotent mark/clear semantics, and pointer validation. Native
list/detail baseline flags are derived only from that pointer. The comparison
module owns bounded pattern and exact-line count deltas plus timing-provenance
compatibility against that explicit pointer; it does not select a baseline
heuristically or expose unbounded raw evidence.
Startup recovery
retains structured diagnostics for malformed/reserve conditions and treats a
failed terminal metadata replacement or unrecoverable transaction preimage as a
startup error. Transaction bookkeeping is internal and does not change schema-v0
or schema-v1 evidence formats.
The remaining rules are centralized in the Phase 1 spec and
`docs/reconnect_session_semantics.md`; they are not repeated here.

### `gpio_config`

Owns host control-channel mapping, validation, and accepted/rejected state. It:

- loads `[hardware.control.*]` mappings
- tracks `CTRL0` through `CTRL3` as `unconfigured`, `configured`, or `rejected`
- sends configuration through an injected semantic device-control port
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

- capture from normalized backend events
- finite source-backed capture using a host-monotonic deadline
- disconnect recovery through an injected backend reopen operation, with one
  immutable deadline across all replacement sources
- per-segment UART finalization before reconnect so partial and oversized lines
  never cross a connection boundary
- reset and boot-mode actions through an injected semantic device-control port
- reset-triggered boot-test recording
- active-session publication and conflict cleanup in `DeviceCoreRuntime`
- required accepted `reset`/`boot` role checks
- literal new-evidence-only wait-pattern sessions
- text-only bounded UART send through an injected backend sender port
- forced-send attempt/result persistence under the same mutation guard as
  capture evidence and terminalization

Capture and boot-test validation consistently enforces the Phase 1
`0 < duration_s <= 300` contract before HTTP dispatch or workflow/session work.
Native workflows persist and echo accepted duration/reconnect policy and
terminal lifecycle state, and startup resolves interrupted evidence units and
abandons stale active sessions before opening a backend. The session store owns
durable disconnect/resume mutations. The capture workflow owns deadline
precedence, the 32-segment stop, source replacement, and canonical reconnect
failures through a small injected reopen port and does not own serial details.
Service composition retries the configured Basic port or reopens Enhanced,
validates an exact identity and timestamp provenance, and replaces the live
control and UART-send transports. Runtime publishes connected, disconnected,
and reconnecting state plus the active workflow and remaining reconnect window.

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
- future background lifecycle ownership for normalized UART-send and control interfaces

It will not decode lines, detect patterns, persist sessions, handle HTTP, or
format CLI output.

## Application Boundaries

### Device Core Service

`apps/service` owns the local FastAPI process, selected serial connection, and
runtime composition. Current endpoints cover status, finite capture, boot-test,
wait-pattern, bounded UART send, GPIO mode, reset, boot mode, bounded session
list/detail and comparison, baseline mark/clear, and bounded recent UART replay.
Handlers remain thin: core code owns
validation order, state transitions, and deterministic behavior; service code
owns request/response serialization and HTTP error mapping.

The service accepts one explicit Basic/Enhanced selection. Basic requires and
opens a raw serial port without `hello`, wiring its normalized source into the
same finite capture path. Enhanced validates `hello` when a port is selected
and may start disconnected without one. Status and finite capture responses
serialize backend identity, raw/effective capabilities, TX-policy provenance,
segment timing, UART-loss integrity, and volatile reconnect state. Active
capture/boot-test workflows reopen the selected Basic port or validate an exact
Enhanced hello before resuming. Continuous background ingestion outside active
workflows and remaining error-specific structured contexts remain Phase 1 work.

### CLI

`apps/cli` is an HTTP client for the Device Core Service. It owns process
lifecycle commands, request construction, and human-readable output. It must
not import low-level transport code or open serial ports for debug workflows.

Current commands cover explicit Basic/Enhanced startup selection, service
lifecycle, labeled device listing, status, capture, boot-test, GPIO mode,
reset, boot mode, session listing, session detail, recent logs, and literal
wait-pattern, plus bounded UART send. Baseline commands remain pending.

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
