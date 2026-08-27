# Enhanced Asynchronous Serial Adapter Design

**Date:** 2026-08-27

**Phase:** Phase 1, development checklist step 4

**Status:** Approved direction; written specification awaiting review

## Purpose

DUTchMate's Enhanced backend currently uses `SerialCommandTransport` for both
blocking command requests and blocking event reads. A command request reads
until it finds a response and retains interleaved UART or telemetry messages in
an internal deque. `EnhancedCaptureEventSource` later consumes those retained
messages through a blocking compatibility interface.

The next Phase 1 slice introduces the asynchronous connection boundary that
will replace this arrangement. The adapter must own every read from one
Enhanced serial connection, route command responses without losing interleaved
evidence, and expose the existing normalized asynchronous event-source
contract. This is the prerequisite for continuous service-owned ingestion.

## Scope

This design covers one independently testable subsystem:

- an asynchronous Enhanced serial reader and message dispatcher;
- one pending-command path with ordered, complete frame writes;
- a bounded FIFO of normalized UART and telemetry events;
- Enhanced hello, segment-origin, shutdown, and terminal-error semantics; and
- fake-stream tests for the complete connection boundary.

This slice does **not** replace the production startup or reconnect composition,
convert finite workflows to continuous ingestion, or remove the synchronous
transport. Those changes follow in separate, independently testable slices
after this adapter is proven. No firmware, HTTP, CLI, session-format, or MCP
behavior changes are in scope.

## Architectural Decision

Add one cohesive Enhanced serial adapter in the core backend/adapter layer. One
instance represents one physical Enhanced connection and owns:

- the serial resource;
- one asynchronous reader task;
- one bounded `NdjsonStreamParser`;
- the startup hello result;
- at most one pending command-response waiter;
- one bounded FIFO of normalized backend events; and
- the connection's terminal state.

The adapter implements the asynchronous `BackendEventSource` contract and the
new `AsyncCommandTransport` protocol. Semantic control and UART-send adapters
will consume that command boundary in a later integration slice. No other
component may read from the same serial connection.

The connection-oriented responsibilities belong together because command
responses and unsolicited evidence share one uncorrelated wire stream. Splitting
them into independent readers would introduce races; splitting them into
independent queues before dispatch would add a second processing pipeline.

The implementation lives in
`dutchmate_core.backends.enhanced_serial.AsyncEnhancedSerialAdapter`. The
asynchronous command protocol lives beside the existing synchronous protocol in
`dutchmate_core.device_connection.transport`. Existing pure message
normalization and protocol encoding/parsing remain in their current modules.
Application and domain policy must not import `asyncio`, `serial_asyncio`,
pyserial, or Enhanced wire DTOs.

## Public Boundary

`AsyncEnhancedSerialAdapter` exposes these operations:

- `start(timeout_s)` starts exactly one reader task and waits for a valid
  initial hello within the supplied positive timeout.
- `request(command, timeout_s)` sends one complete bounded NDJSON command and
  awaits its `success` or `error` response.
- `receive_event(timeout_s)` returns the next normalized FIFO event, returns
  `None` only for ordinary inactivity, and otherwise raises the normalized
  disconnect or input error.
- `close()` is asynchronous and idempotent. It stops the reader, closes the
  serial resource, fails waiters, and leaves no background task running.
- `info`, `segment_id`, and `segment` expose the existing backend-neutral
  identity and timestamp-provenance contracts after their values are known.

Only the composition/adapter layer may observe the initial `HelloMessage` while
establishing `BackendInfo`. Production workflows continue to consume
`BackendEvent`, not Enhanced protocol DTOs.

## Serial Read Ownership And Parsing

The reader task is the only caller of the serial read operation. It repeatedly
reads bounded byte chunks and feeds the existing `NdjsonStreamParser`. The
parser continues to enforce the 65,536-byte device-to-host frame limit before
UTF-8 or JSON decoding.

Every parsed message is classified in wire order:

- the first message must be `hello` and completes startup validation;
- `success` and `error` messages target the current pending request;
- `uart`, `buffer_status`, and `buffer_overflow` messages are normalized and
  published to the FIFO; and
- a hello after startup or a response without a pending request is a fatal
  protocol-state error because it cannot be correlated safely.

When one byte chunk contains valid evidence frames followed by an invalid or
oversized frame, normalized events from the valid prefix are published in FIFO
order. The offending frame and all later bytes from that read are not
published. The connection then becomes terminal and any pending command fails.
`NdjsonStreamParser` gains a read-only `terminal_error` property so the reader
can make this decision without performing another physical read.

## Command Serialization And Writes

Enhanced protocol v1 has no request or response correlation identifier.
Therefore exactly one command may be in flight per connection. An asynchronous
lock serializes callers around the complete write-and-response operation; later
callers wait without writing.

Before transmission, the adapter preserves the existing command rules:

- the value is bytes;
- the frame is LF-terminated NDJSON;
- the complete frame is at most 2,048 bytes; and
- no response wait begins until the entire frame has been accepted and flushed.

`pyserial-asyncio` internally retries positive short writes, but its public
`StreamWriter` surface does not expose the number of bytes physically accepted
before a later failure. DUTchMate must retain the stronger Phase 1 diagnostic
contract already implemented by `SerialCommandTransport`. The production
connection will therefore use `pyserial-asyncio` for asynchronous read
readiness while delegating writes to an injected asynchronous frame-writer
boundary that retains exact accepted-byte accounting. The pyserial
implementation runs the extracted ordered write/flush loop with
`asyncio.to_thread()` against the same owned serial resource. It performs no
reads, and the Enhanced adapter remains the sole connection owner.

This boundary is injected in the first slice so fake writers can prove complete
writes, partial failure accounting, and cancellation deterministically. It does
not create a generic transport abstraction for unrelated backends.

## Event Queue And Backpressure

The adapter owns one `asyncio.Queue` with a positive, configurable maximum
event count and a production default of 256 events. Since every normalized
event has protocol-bounded fields, this also places a finite upper bound on
queued evidence memory.

The reader awaits queue capacity rather than dropping, overwriting, or
reordering evidence. This is intentional backpressure. The later continuous
ingestion coordinator is expected to drain the queue throughout the service
lifetime, including when no finite workflow is active.

If the queue remains full, the reader cannot reach a later command response;
the command timeout policy then closes the connection rather than permitting an
ambiguous late response. Device-side overflow remains independently reported by
the existing `buffer_overflow` and `buffer_status` events.

## Identity And Timestamp Provenance

`start()` does not report a ready Enhanced connection until the first parsed
message is a valid hello. The hello establishes immutable `BackendInfo` using
the existing exact identity validation. A missing, malformed, or unexpected
first message fails startup.

The hello and command-response timestamps do not establish a capture segment's
origin. As today, the first timestamped UART or telemetry event establishes
`source_origin_us`. The adapter creates the immutable `SegmentContext` and
normalizes that first event to timestamp zero before placing it in the FIFO.
Consequently `segment` may be `None` before the first evidence event but must be
available before that event is returned.

Each reconnect creates a new adapter instance, reader task, parser, command
state, event FIFO, and segment ID. State never crosses a physical connection
boundary.

## Failure And Cancellation Semantics

The connection has one terminal outcome. The first terminal cause is retained
and is reported consistently to all later operations.

- EOF, serial read failure, or unexpected transport closure becomes
  `BackendDisconnectedError`.
- Malformed, oversized, schema-invalid, or protocol-state input becomes
  `BackendInputError` with the existing bounded classification.
- Write failures retain `TransportWriteError` classification and exact
  `frame_bytes_accepted` internally for the semantic adapter to project.
- An event receive timeout returns `None` and does not alter connection state.
- A command timeout after any command byte may have been accepted closes the
  connection. A late uncorrelated response must never be reused by another
  request.
- Cancellation before a request begins writing leaves the connection usable.
  Cancellation after transmission begins closes the connection for the same
  correlation-safety reason as timeout.
- Closing fails the hello waiter, pending command, blocked event consumer, and
  queued command callers with the retained terminal outcome.

Events from a valid prefix remain observable before the terminal input error.
After those events are drained, `receive_event()` raises the retained error on
every call. Shutdown is idempotent and awaits reader-task termination.

## First Implementation Slice

The first code slice introduces the adapter behind injected asynchronous reader
and frame-writer boundaries. It is not selected by service startup yet. The
slice adds the read-only parser property needed to expose a stored terminal
parse error, but it must not alter accepted wire formats or existing
synchronous behavior.

Tests use deterministic fakes and cover:

1. exactly one reader task across repeated startup calls;
2. valid hello startup and invalid/missing/unexpected hello failure;
3. command success and command error routing;
4. serialized concurrent commands with only one command in flight;
5. interleaved UART and telemetry retained in exact FIFO order;
6. first-event segment-origin establishment before delivery;
7. 65,536-byte receive framing and 2,048-byte command framing boundaries;
8. valid-prefix delivery followed by a retained terminal parse error;
9. bounded-queue backpressure with a deliberately tiny test capacity;
10. disconnect and write-error mapping;
11. request timeout and cancellation before and after transmission;
12. idempotent close, waiter wake-up, and no leaked reader task; and
13. repeatable terminal errors after queued valid events are drained.

Existing synchronous transport, backend, runtime, service, and full-suite tests
must remain green. Ruff, mypy, full pytest, and `git diff --check` remain the
slice validation gate.

## Subsequent Migration Slices

After the first adapter slice passes review:

1. add the real `pyserial-asyncio` read factory and exact-accounting write
   adapter, then select the async Enhanced adapter in service composition;
2. migrate semantic control and UART-send consumers to the asynchronous request
   boundary without exposing wire DTOs to workflows;
3. introduce the separately designed service-owned continuous ingestion
   coordinator for Enhanced and the Basic adapter's existing async FIFO;
4. coordinate reconnect, hello/identity validation, segment replacement, and
   active workflow delivery through that single ingestion path; and
5. remove `SerialCommandTransport`, `EnhancedCaptureEventSource`, blocking
   `CaptureEventSource.read_event()`, and other compatibility code only after no
   production consumer remains.

Each slice updates `docs/development_status.md` in the same commit and remains
independently testable. The continuous ingestion coordinator requires its own
focused design before implementation because it changes workflow event
ownership beyond this serial-connection boundary.

## Rejected Alternatives

### Big-Bang Async Migration

Changing the serial adapter, runtime, workflows, startup, reconnect, and
delivery surfaces in one commit would remove compatibility sooner but combine
too many independent failure modes. It conflicts with the repository rule to
refactor one subsystem at a time.

### Separate Command And Event Readers

Two readers cannot safely classify one uncorrelated serial stream. Either reader
could consume the other's message, causing lost evidence, incorrect command
completion, or reordered events.

### Permanent Thread/Async Compatibility Bridge

Keeping the blocking reader and wrapping it indefinitely with worker threads
would preserve current code shape but would not deliver the required
`pyserial-asyncio` ownership model. A worker-thread write implementation is
permitted only as a narrow adapter for exact write accounting; it never reads
and is removed or retained based on measured production transport behavior.

## Acceptance Criteria

The design is implemented successfully when the first slice proves one reader,
one pending command, bounded parsing, bounded FIFO behavior, FIFO interleaving,
normalized errors, deterministic shutdown, and existing event/provenance
contracts entirely with fakes, while all pre-existing behavior remains green.
No production path may instantiate the new adapter until the following
integration slice explicitly migrates connection ownership.
