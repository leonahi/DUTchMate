# Software Architecture

> Scope: host-side Python layers, dependency direction, data flow, and code ownership.
>
> The target behavior is defined normatively by `project_context.md` and
> `phase1_implementation_spec.md`. This document records module ownership and
> dependency direction, not migration progress or next steps.

This document describes repository organization and ownership. Requirements
belong to their contract documents; progress and next-step status belong only
to `docs/development_status.md`.

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
  -> process replacement for apps/mcp_server executable

apps/mcp_server
  -> HTTP client for apps/service

apps/debug_agent
  -> bounded, schema-aware session facts from core/session_store
  -> optional provider adapters outside apps/service and core

apps/service
  -> process/runtime ownership
  -> core/profile
  -> core

core/profile
  -> validated effective DUT/serial/GPIO configuration
  -> backends.settings adapter projection
  -> gpio_config

core/runtime
  -> profile status projection
  -> connection ownership contract
  -> evidence
  -> operations
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

core/evidence
  -> session_store
  -> connection ownership values
  -> uart_capture
  -> backends.contracts

core/operations
  -> uart_capture
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

The CLI and service load `.dutchmate/config.toml` into the profile model and
apply supported startup overrides before any backend opens. The resolved profile
is immutable and owns backend selection, serial selector/current path, reconnect
timeout, topology, UART policy, requested DTR/RTS open behavior, default line
ending, and Enhanced GPIO configuration. Its bounded canonical JSON projection
and SHA-256 digest are exposed through runtime status. Physical adapters consume
only the derived `BackendSettings`; they do not resolve project configuration.

The Debug Agent application reads native session evidence through the validated
`SessionStore` query boundary. Its deterministic session-facts projection keeps
backend identity, capability policy, lifecycle, integrity, timestamp provenance,
stored first-error reference, and bounded event counts without loading raw UART
or hardware-event arrays. The evidence packer then reads a stable validated
artifact snapshot, replays UART lines, and selects first-error, detected-pattern,
session start/end, and recent context within 300 lines and 64 KiB of display
text.
Hardware excerpts stop at 100 events; failure and unmatched UART TX outcomes
remain explicit summaries even when their records are omitted. Package omissions
and trimmed fields are reported. A baseline comparison is added only through
the validated project pointer. The package retains its session ID, timing
comparability, pattern deltas, and bounded line-change counts without copying
comparison UART text; an ineligible subject gets an explicit reason. Provider
adapters remain within `apps/debug_agent`; neither Device Core nor `core`
depends on that app.

The Debug Agent also validates the optional Coding Agent context package as
caller-supplied data. It checks version, session correlation, source/diff
provenance, byte and line budgets, repository-relative paths, and known
secret material without opening repository files. Its versioned analysis
request combines that validated context with the bounded native evidence for
each selected session. Provider invocation remains a separate application
boundary and is not part of evidence assembly.

The Debug Agent report validator checks the common provider response against
selected session, UART, hardware, TX-outcome, and source/diff references. It
attaches request metadata and provenance warnings itself, preserving the
native first-error coordinates without copying captured text into report
metadata. The provider boundary freezes canonical request bytes, exposes a
manifest before submission, defaults to disabled, requires separate remote
processing opt-in, and validates the response before returning a report.
The Debug Agent CLI previews the manifest and requires its digest before
submitting to the local-only Ollama adapter. That adapter uses the bounded
chat response path; the shared report validator remains provider-independent.
Neither the CLI nor adapter stores credentials or changes Device Core state.

Shared capture, UART processing, and storage use this normalized event
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
`docs/phase1_implementation_spec.md`. Production Enhanced input enters through
one service-owned async host and the core-owned continuous evidence recorder.
No synchronous Enhanced command/source path or second physical reader remains.

## Data Flow

Enhanced byte-chunk normalization is tested independently of evidence ownership:

```text
NDJSON bytes
  -> NdjsonStreamParser
  -> parse_device_message
  -> EnhancedNdjsonEventStream
  -> normalized backend events
```

Production workflows receive normalized events and never import Enhanced wire
messages, parsers, commands, or transports.

The production Enhanced path is:

```text
EnhancedAsyncHost (one owner loop and one async adapter)
  -> normalized backend events
  -> ContinuousEvidenceRecorder (core/evidence)
  -> schema-v2 SessionStore admission
  -> durable tail notification
  -> DeviceCoreRuntime bounded Monitor / Interact and audited Control
  -> operation-local MonitorMatcher over durable UART records
```

`DeviceCoreRuntime` publishes an active schema-v2 ownership session for the
whole connected/reconnecting interval, including when no bounded operation is
running. The recorder owns the only normalized receive path, persists UART and
telemetry before advancing its durable tail, maintains continuous line/pattern
projections, and transfers a validated replacement source into the same session
with a new session-local segment. Basic and Enhanced use the same recorder
contract. Bounded operations observe published durable tails and read stable UART
records through operation-local seek cursors; they never call the physical
backend source or rescan accumulated UART history under the store mutation lock.

For replacement Enhanced connections, the runtime installs a required
initialization callback on the recorder. The recorder persists the replacement
segment, the runtime reuses canonical audited GPIO configuration from the
immutable Profile, and only then does the recorder publish lifecycle success
and transfer authoritative receive ownership. Service reconnect coordination
still owns candidate opening/identity/cleanup and supplies final readiness
checks. Physical commands and mutation-lock waits do not hold evidence admission
or the coordinator's status lock. Interact's operation lease excludes competing
user mutations while observation leaves the mutation lock available for this
internal connection initialization. No delivery dependency enters core.

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
- host command encoders for GPIO mode, generic channel actions, and UART send
- base64 decoding and lossy UART display projection
- NDJSON chunk buffering and message validation
- serial-port discovery, host-frame validation, and the shared exact-write
  primitive used by the async Enhanced serial adapter

`hardware/protocol/v1/` is the wire authority. Its schemas, examples,
parser/encoder models, tests, and firmware handling change atomically.

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

### `evidence`

Owns continuous normalized receive and authoritative admission into schema-v2
storage. `ContinuousEvidenceRecorder` starts only after profile, persistence,
backend identity, and segment provenance are ready. It preserves ambient UART,
telemetry, connection boundaries, line-limit facts, and default-pattern
projections; publishes tail positions only after durable admission; resets
session-local line state across disconnect, rollover, and shutdown boundaries;
and faults and closes physical ownership when authoritative persistence cannot
continue. Clean shutdown first stops physical input, drains already-normalized
source events, and then terminalizes the active v2 session.

It also serializes bounded-operation lifecycle and TX/Control attempt/result
admissions with receive/connection admissions, snapshots the operation start cursor and pre-cursor partial-line
state in the final start session, flushes continuous line state before a
lifecycle or action admission rolls over, exposes incremental cursor-bounded UART reads,
and resolves lifecycle-owned terminal records. Each reader owns a bounded
retention lease that terminal persistence atomically extends across its final
evidence ranges and runtime result construction releases. Reconnect replacement
and failure use the same admission ordering, so bounded operations cannot create
a second physical reader.

`evidence.tail` defines the independent public durable-tail page contract and
query bounds. It does not reuse the Monitor/Interact operation cursor or own
acquisition. Runtime uses recorder notifications only to wake long polls; page
contents always come from persisted primary evidence.

### `connection`

`connection.py` owns the normalized seven-state ownership vocabulary, boundary
result, lifecycle error, and replaceable ownership port. Runtime derives the
compatibility `connected` flag from its explicit state, arbitrates lifecycle
requests with a nonblocking claim, and rejects release during submitted mutations
or Interact. Active read-only Monitor operations finish as `released`; follow
continues observing journal evidence without acquiring transport ownership.

The recorder persists `release_requested` before closing its source, drains
already-normalized RX through the same admission path, flushes line boundaries,
and records `released`. Persistence closes the segment with reason `released`
and increments the explicit observation-gap count while keeping the journal
active. Reacquire records start/success/failure facts and publishes a fresh
segment before resuming RX. It continues a valid active journal or creates a new
v2 session when the prior journal is terminal. New sessions reset session-local
integrity; segment-limit rollover uses the existing explicit successor chain.
Journal rollover during a released interval preserves the closed connection
and its gap rather than creating a synthetic physical reopen.

### `operations`

Owns framework-independent bounded observation and Interact result values, validation,
active-operation summaries, evidence cursors/ranges, and operation-local literal
matching. `MonitorMatcher` reconstructs lines independently by
session/segment/channel from persisted UART records, excludes pre-cursor partial
lines and oversized physical lines, and returns exact raw coordinates and a
bounded excerpt using the normative deterministic tie-break. It owns neither
backend receive nor persistence writes.

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
- records schema-v2 operation start/terminal evidence, transfers active ranges
  across rollover, opens seek-based incremental UART readers for bounded operations, and
  derives operation result integrity from telemetry inside exact half-open
  ranges plus timestamp provenance across every range
- stores `line_processing` status/counts and finalized `line_limit_exceeded`
  descriptors without changing UART integrity or session truncation
- preflights exact whole units for RX, telemetry, bounded-operation lifecycle,
  and TX/Control evidence; v2 rolls over before admitting an over-budget unit,
  flushes continuous line boundaries, and transfers pending operation/action ownership
- creates schema-v2 ownership sessions with a terminal reserve and one-way
  lifecycle; no schema-v0/v1 creation or append API ships in production
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
- `session_store.tail` merges committed v2 UART, operation, hardware, and connection
  streams in `evidence_seq` order. Its versioned opaque cursor encodes the session,
  next sequence, and four seek offsets. Snapshots open files and capture committed
  lengths under the store lock, then replay outside that lock. Reference-counted
  retention leases protect only an in-flight snapshot, never an attached client
- follows only explicit v2 successor links across rollover. A missing cursor
  session returns `cursor_expired`; without a retained proof of continuity it
  never guesses a successor or jumps to the latest session
- projects exact UART bytes/raw offsets and segment timestamp provenance, plus
  bounded scalar action/operation/connection markers without exception detail.
  Pages contain at most 500 records and 262144 compact UTF-8 bytes, including the
  envelope. `omitted_records` counts whole records deferred from the selected
  limit-bounded window by the byte cap; `next_cursor` leaves those records unread
- selects an explicit, active, or newest terminal native session and replays
  persisted UART events through the shared segment/channel line buffer, retaining
  bounded complete, partial, and oversized records with evidence coordinates
- serves capture/wait aliases through the same bounded Monitor operation records
- rejects path-unsafe session IDs

Session persistence and service delivery share the core `diagnostics`
projection for non-empty, control-sanitized, UTF-8-safe 1024-byte error detail.
The projection owns only bounded diagnostic text; error codes, HTTP status, and
schema-defined context remain responsibilities of their originating workflow
and delivery adapter.

Production connection ownership uses schema version 2 and snapshots the
effective profile, backend facts, reconnect policy, integrity, line processing,
storage accounting, contiguous primary evidence order, and one-way lifecycle
state. Schema-v0/v1 sessions remain explicit read-only compatibility data. The
CLI propagates
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
Startup recovery skips schema-v0/v1 artifacts, including transaction markers,
without mutation. It retains structured diagnostics for malformed/reserve
conditions and treats a
failed terminal metadata replacement or unrecoverable transaction preimage as a
startup error. Transaction bookkeeping is internal and does not change schema-v0
or schema-v1 evidence formats.
Evidence and reconnect requirements are centralized in the Phase 1 spec and
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

Owns exact-byte TX dispatch and configured semantic Control execution through
backend-neutral ports. `DeviceActionRunner` and `GpioConfigurator` retain role,
electrical, and accepted-state policy; runtime wraps every physical mutation in
durable v2 attempt/result evidence. Failed attempts/results preserve actual or
unknown outcomes. TX never enters the receive-only raw log.

`DeviceCoreRuntime` serializes standalone TX, reset, boot mode, and GPIO mode
changes with one mutation lock. It does not hold the operation/status or recorder
admission locks across physical dispatch. Read-only Monitor remains independent;
Interact holds exclusive mutation ownership across its complete bounded window
and rejects competing mutations with `operation_active`. Shutdown cancels bounded
operations and waits for in-flight action result evidence before closing ownership.

Monitor and Interact share the existing operation lifecycle, incremental UART
reader, matcher, exact-range quality projection, retention lease, cancellation, and
reconnect machinery. Interact establishes its durable cursor before TX, never retries
TX after reconnect, and exposes exact bytes plus known or unknown acceptance.

Device Core does not own a dedicated boot-test composite. Higher-level procedures
such as reset-and-observe or bootloader validation are composed by clients from
audited Control plus durable evidence access and, when useful, Monitor. Continuous
recording remains authoritative between those atomic requests.

The former finite `CaptureWorkflow`, `CaptureRecorder`, transport runner,
workflow-only reader lifecycle, runtime capture-exclusion flags, session-source
rebasing, and per-capture reconnect ownership have been removed. The
`workflows.capture` module retains normalized source/health/reconnect contracts
used by backend/service consumers. Capture/wait spellings remain thin Monitor
aliases; they cannot create v1 sessions or independent readers. Historical v0/v1
session reading, replay, and compatibility fixtures remain available.

Legacy fixture construction is isolated in `tests/support/legacy_*`; those modules
are absent from all distributable source roots. Compatibility reader and Debug
Agent tests consume these fixtures through the production query boundary.
The Debug Agent requires schema-v1 `NativeSessionDetail`; v2 evidence packages,
operations, and Control/TX references need its separate Phase 4 migration.

The service-owned `BackendReconnectCoordinator` continues to reopen and validate
replacement sources and publish stable control/TX ports. The core continuous
recorder owns evidence and connection generations. New v2 runtime actions use
explicit payload transformations; the public send API and CLI have no `force`
or implicit newline append. Low-level protocol and deferred MCP text helpers are
unchanged and do not restore the retired service request contract.

The coordinator has no finite-workflow callable/retry path. Its continuous worker
and explicit release/reacquire share one attempt claim. Adapter and host APIs
cannot discard normalized events at a workflow boundary. Runtime receives only a
shutdown contract for the reconnect supervisor, separate from ownership actions.

Manual release/reacquire share the coordinator's attempt claim with automatic
reconnect. Release suspends automatic opening; competing lifecycle requests fail
busy. Shutdown/detach cancels pending publication, closes rejected candidates,
and waits for submitted physical mutations to finish their result evidence.
Failed-open cleanup is a separate ownership fact: confirmed cleanup permits
retry; unknown cleanup retains a blocking fault and never reports the port free.
Basic and Enhanced close paths retain cleanup failures across repeated calls.
Enhanced open failures retain the primary exception identity together with
cleanup certainty; persistence failures retain their `persistence_fault` error.

### `backends` (Contract Foundation)

This package defines backend-neutral identity, timestamp provenance, normalized
UART/telemetry events, the asynchronous event-source protocol, and distinct
disconnect/input errors. Shared fake Basic and Enhanced sources verify the same
FIFO/timeout/error contract. Shared settings resolve explicit Basic/Enhanced
selection, exact serial ports, backend-specific baudrates, 8-N-1 framing, TX
policy, and reconnect timeout. Basic connection setup opens raw serial without
reading a `hello`. Its event source lazily starts one serial-reader thread,
converts each delivered byte chunk to one FIFO normalized event with
host-monotonic provenance, and feeds the recorder through a fixed-capacity queue
that applies bounded backpressure. Basic UART writes are capability-gated and retry
ordered short writes to completion. The Enhanced adapter translates
parsed v1 messages and async receive timeouts before shared capture. Its one
service-owned async host remains the resource owner across event, control, and
  UART-send operations and retains already-normalized events that are queued or
  blocked on bounded queue admission while physical receive closes so the recorder
  can drain them. When the device-timer origin is unavailable at connection
  creation, the first timestamped evidence establishes the segment origin and is
normalized to zero before its immutable context is persisted; the adapter's
origin wait observes that transition without dequeuing the event.

It will not decode lines, detect patterns, persist sessions, handle HTTP, or
format CLI output.

Basic constructs an unopened serial object, applies requested DTR/RTS states,
then opens the configured path. Segment `serial` provenance records effective
framing/flow settings, requested line states, RTS ownership, and
`preconfigured`/`driver_managed` open intent. The provenance makes no guarantee of
glitch-free electrical transitions or electrical readback. Phase 1 rejects RTS
application ownership with hardware flow control before opening. Optional
semantic `serial_line_control` remains unavailable; Basic never advertises GPIO
control or exposes raw line toggles.

`backends.selection` owns USB discovery and unique identity matching. An optional
`[backend.selector]` table supplies all three of `vid`, `pid`, and `serial_number`
for `native_usb_console`; VID/PID are unsigned 16-bit integers and the serial
number is bounded and nonempty. Only a unique exact identity match can select a
changed path. External UART and native USB without that selector retain exact
path selection. The service consumes selected backend settings and normalized
snapshots; it does not choose between discovery candidates. CLI startup forwards
the resolved selector to the service process. Ambiguity opens nothing, leaves
automatic reconnect disconnected, and exposes `service_unavailable` with reason
`ambiguous_device` through bounded status diagnostics. USB absence remains a real
segment boundary and unobserved gap.

## Application Boundaries

### Device Core Service

`apps/service` owns the local FastAPI process, selected serial connection, and
runtime composition. Startup creates the active schema-v2 session and core
recorder before starting reconnect supervision. Handlers remain thin: core code
owns validation order, state transitions, and deterministic behavior; service
code owns request/response serialization and HTTP error mapping.

The service accepts one explicit Basic/Enhanced selection. Basic opens a raw
serial port without `hello`. Enhanced validates `hello`, waits for timestamp
provenance while its async adapter buffers interleaved events, and then transfers
the host to the recorder without adding a reader. The service-owned reconnect
coordinator owns physical reopen callbacks; the core recorder remains the stable
source and evidence owner. Status serializes backend identity, raw/effective
capabilities, TX-policy provenance, the active v2 session, normalized segment
timing, UART-loss integrity, and connection/reconnect/fault state.

`GET /dut/evidence` validates cursor/limit/wait bounds and returns the core's
compact page without a second serialization format. A cursorless request
establishes the current durable tail and returns no historical records; runtime
resamples if rollover retention retires its initial tail during attachment.
Cursor requests page persisted evidence and may wait up to 30 seconds for a
durable-tail notification. Deleted positions map to HTTP 410 `cursor_expired`.
If reacquire must create an unrelated journal after the prior session ended,
an exhausted old cursor also explicitly expires. The API never silently joins
independent ownership sessions; ordinary same-session release/reacquire and
explicit rollover links continue normally.

`POST /connection/release` and `/connection/reacquire` return the resulting
connection state and durable session/segment boundary. Status preserves the
active journal ID while released/reacquiring and includes bounded
`connection_error` diagnostics when ownership selection or cleanup fails.

### CLI

`apps/cli` is an HTTP client for the Device Core Service. It owns process
lifecycle commands, request construction, and human-readable output. It must
not import low-level transport code or open serial ports for debug workflows.

Current commands cover explicit Basic/Enhanced startup selection, service
lifecycle, labeled device listing, status, capture, GPIO mode, reset, boot mode,
session listing, session detail, recent logs, and literal
wait-pattern, bounded Monitor/Interact, audited byte-first UART send, durable
`follow`, line-oriented `console`, explicit `release`/`reacquire`, and baseline
mark/clear. `dutchmate mcp`
replaces the CLI process with the aggregator-owned `dutchmate-mcp` entry point,
which targets the separately packaged MCP adapter. This preserves the
delivery-package import boundary and gives the MCP adapter direct ownership of
stdin, stdout, and stderr.

Follow attaches at the durable tail by default (or resumes `--cursor`), renders
lossy UART text and bounded markers, and advances only after rendering each
page. Byte-deferred records are replayed by the next request; expiry is explicit
and never triggers silent reattachment. Console uses the same view in a client
thread while reading complete input lines. It requires effective `uart_send`,
resolves `profile_default` from the service's immutable effective profile, and
sends an explicit resolved ending through audited `/dut/uart/send`. Interact
rejections are reported without retry. EOF/Ctrl-C stops and joins the view only;
neither command changes recorder/session ownership or opens serial transport.

### Public Distribution Composition

`packages/dutchmate` owns the public `dutchmate`, `dm`, `dutchmate-service`, and
`dutchmate-mcp` executables. It is the only composition layer permitted to
reference the CLI, service, and MCP delivery entry APIs. The Debug Agent remains
a separate workspace package with its own `dutchmate-debug` development
entrypoint; it is excluded from the public `v0.1.0` dependency and command
surface and is planned for public release in `v0.2.0`. CLI, service, MCP, and
Debug Agent packages do not import one another.

### MCP Server

`apps/mcp_server` is a delivery adapter. Its asynchronous
HTTP client maps the bounded Phase 2 tool surface to the Device Core Service,
validates tool-shaped arguments before dispatch, and preserves structured
service errors without owning serial, session, GPIO, or AI logic. The package is
locked to official MCP Python SDK 2.x and the stateless `2026-07-28` protocol
model; Device Core IDs remain explicit tool data rather than hidden MCP session
state. Its fixed-identity `MCPServer` composition delegates discovery, per-request
metadata, result typing, private cache hints, and stdio framing to the SDK. The
entrypoint resolves the Device Core URL from `--service-url`, then
`DUTCHMATE_SERVICE_URL`, then its loopback default. It configures SDK logging
on stderr while keeping stdout reserved for protocol frames. The tool contract
is defined in `docs/mcp_integration_plan.md`.

## Boundary Rules

- The public `dutchmate` package composes delivery entry APIs but contains no
  Device Core, backend, protocol, or hardware behavior.
- `core` does not import any app or AI package.
- `device_connection` knows the Enhanced protocol, not sessions or workflows.
- `backends` owns device-specific adaptation, not line or session processing.
- `uart_capture` owns bounded derived buffering, not persistence.
- `log_processing` remains deterministic and hardware-free.
- `session_store` owns durable evidence, not serial parsing.
- `gpio_config` owns accepted mapping state, not physical transport ownership.
- `workflows` coordinate lower layers but do not duplicate wire validation.
- Service and CLI layers do not reinterpret core state or error semantics.

Testing commands live in `docs/developer_guide.md`; Phase 1 acceptance coverage
lives in `docs/phase1_implementation_spec.md`.
