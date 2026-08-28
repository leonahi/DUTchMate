# Enhanced Asynchronous Serial I/O Design

**Date:** 2026-08-28

**Phase:** Phase 1, continuous ingestion and asynchronous Enhanced adapter

**Status:** Approved on 2026-08-28

## Purpose

`AsyncEnhancedSerialAdapter` now proves the connection-level concurrency and
protocol behavior with injected readers and writers. Production still opens
`SerialCommandTransport`, which owns blocking reads and writes. The next safe
slice supplies the real `pyserial-asyncio` read boundary and the exact-accounting
writer needed by the async adapter.

This slice deliberately does not select the async adapter in the running
service. The current `DeviceCoreRuntime`, semantic control adapters, UART sender,
capture workflows, and reconnect coordinator are synchronous consumers. Selecting
the async adapter before those consumers migrate would either remove working
Enhanced behavior or require a second serial reader. Both outcomes violate the
approved single-owner design.

The production factory created here is the concrete dependency that the next
service integration slice will select atomically with migrated consumers.

## Scope

This slice includes:

- a production `pyserial-asyncio` connection factory for one Enhanced serial
  resource;
- an async reader wrapper that owns connection shutdown;
- an exact-accounting async frame writer using the same serial resource;
- extraction and reuse of the existing ordered write/flush algorithm;
- startup hello validation and failure cleanup through
  `AsyncEnhancedSerialAdapter.start()`; and
- deterministic adapter-level tests for the real I/O seams without hardware.

This slice does not include:

- changing service startup to select the async adapter;
- changing FastAPI endpoints or `DeviceCoreRuntime` method shapes;
- migrating semantic control or UART-send adapters;
- introducing the service-owned continuous ingestion coordinator;
- changing reconnect behavior;
- removing `SerialCommandTransport` or `EnhancedCaptureEventSource`;
- firmware, HTTP, CLI, MCP, session-format, or configuration changes; or
- adding another transport abstraction for Basic or unrelated backends.

## Sequencing Correction

The earlier adapter design listed production I/O creation and service selection
as one migration slice. Source inspection shows that this ordering is not
independently deployable:

1. `build_startup_runtime()` currently constructs synchronous control, UART-send,
   capture, and reconnect consumers around `SerialCommandTransport`.
2. `AsyncEnhancedSerialAdapter` exposes only asynchronous event and command
   operations.
3. Opening the synchronous and asynchronous transports together would create two
   serial resources and competing readers for the same Debug Helper.
4. Selecting only the async transport would leave the current runtime consumers
   unusable.

Therefore production I/O is implemented and proven first, but service selection
remains on the synchronous compatibility path until the required consumers can
move together. This is a correction to slice boundaries, not a change to the
target architecture.

## Module Ownership

### `dutchmate_core.device_connection.serial_transport`

The existing serial module continues to own pyserial-compatible exact write
semantics. Extract the ordered write/flush loop from
`SerialCommandTransport.request()` into one reusable function. The function:

- accepts a narrow serial frame sink with `write(bytes) -> int` and `flush()`;
- validates the complete LF-terminated frame before dispatch;
- retries positive short writes in order;
- rejects boolean, zero, negative, non-integer, or over-reported progress;
- retains exact `frame_bytes_accepted` on write and flush failures; and
- preserves the existing timeout versus hardware-fault classification.

`SerialCommandTransport` calls this function while holding its existing lock, so
synchronous behavior remains unchanged.

### `dutchmate_core.backends.enhanced_serial_io`

A new adapter module owns the external `pyserial-asyncio` integration. Keeping it
separate from `enhanced_serial.py` isolates library-specific connection setup and
thread delegation from the already reviewed protocol dispatcher.

The module contains three cohesive pieces:

1. An async reader wrapper around `asyncio.StreamReader` plus its paired
   `StreamWriter`. `read(size)` delegates to the stream reader. `close()` closes
   the stream writer, awaits `wait_closed()`, and is idempotent.
2. An async frame writer around the underlying pyserial object. It delegates the
   shared exact write/flush function through `asyncio.to_thread()`. It never
   performs a read and never calls `StreamWriter.write()`.
3. A production factory that opens one `pyserial-asyncio` stream pair, obtains
   the same underlying serial object from the stream transport, constructs one
   `AsyncEnhancedSerialAdapter`, validates the initial hello, and returns only a
   started adapter.

Library importing stays inside this infrastructure adapter. Application and
domain policy do not import `asyncio`, `serial_asyncio`, pyserial, or Enhanced
wire DTOs.

## Connection And Resource Ownership

The factory calls `serial_asyncio.open_serial_connection()` with the selected
port, baud rate, and a bounded stream-reader limit aligned with the 65,536-byte
device frame limit. The adapter continues to request 4,096-byte chunks and feeds
its existing bounded `NdjsonStreamParser`.

The existing dependency floor remains `pyserial-asyncio>=0.6`; this slice adds
no dependency or version change.

The returned stream transport owns the physical serial object. Both adapter
halves reference that one object:

- only the stream reader performs physical reads;
- only the exact frame writer performs command writes and flushes; and
- the async reader wrapper owns closing the stream transport and serial resource.

The pyserial-asyncio `StreamWriter` is never used for command data because its
buffered API cannot report exact accepted bytes after a partial failure. Its
transport is retained solely for connection ownership and orderly shutdown.

No second serial handle, reader coroutine, protocol parser, or event queue is
created for one adapter instance.

## Factory Contract

The production entry point is
`open_async_enhanced_serial_adapter(*, port, segment_id, baudrate=115200,
hello_timeout_s=1.0, event_queue_capacity=256, open_connection=None)`. It accepts:

- serial port;
- baud rate;
- segment ID;
- positive hello timeout;
- positive event queue capacity, defaulting to 256; and
- an injectable async stream opener for deterministic tests.

It returns a fully started `AsyncEnhancedSerialAdapter`. Callers never receive a
half-open adapter.

If opening, transport inspection, adapter construction, or hello validation
fails, the factory closes the stream pair exactly once and re-raises the original
classified error. Cleanup failure must not replace the primary startup error.

The factory does not retry. Reconnect policy remains a service composition
responsibility in a later slice, where identity and segment replacement can be
coordinated with active consumers.

## Write Semantics

Host command frames remain LF-terminated NDJSON with a maximum complete size of
2,048 bytes. Exact write behavior is identical for synchronous and asynchronous
production adapters because both call the same extracted algorithm.

The async writer delegates only the ordered write/flush operation to a worker
thread. It does not delegate reads, parsing, response routing, or event delivery.
The serial object is configured by pyserial-asyncio for non-blocking operation,
so zero progress remains a classified timeout rather than an unbounded retry.

`AsyncEnhancedSerialAdapter` remains responsible for serializing commands,
canceling a failed or abandoned request, retaining terminal connection state,
and preventing a late response from being reused.

## Read, Close, And Failure Semantics

The async reader wrapper preserves the stream contract expected by
`AsyncEnhancedSerialAdapter`:

- bytes are returned in arrival order;
- empty bytes mean EOF;
- stream exceptions propagate to the adapter for disconnect normalization; and
- close is asynchronous, idempotent, and waits for transport closure.

The factory relies on the adapter's established behavior for malformed hello,
hello timeout, parser failure, read failure, request cancellation, and terminal
error retention. A failed factory call must leave no reader task or open stream
transport.

The first error remains authoritative. Cleanup exceptions are suppressed only
after the primary open/start failure has been retained.

## Testing Strategy

Tests use injected fake stream openers, stream readers, stream writers,
transports, and pyserial sinks. They prove:

1. the opener receives the exact port, baud rate, and bounded reader limit;
2. the reader and exact writer share the same underlying serial object;
3. no command data is sent through `StreamWriter.write()`;
4. positive short writes complete in order and flush once;
5. invalid progress, write failure, and flush failure retain exact accepted-byte
   accounting and classification;
6. synchronous `SerialCommandTransport` behavior remains unchanged after helper
   extraction;
7. a valid hello returns a started adapter with normalized identity;
8. open, inspection, construction, and hello failures close exactly once without
   hiding the primary error;
9. repeated adapter close is idempotent and waits for stream closure;
10. the 65,536-byte device and 2,048-byte host boundaries remain enforced; and
11. there is one stream reader and no competing physical read path.

The validation gate is Ruff, mypy, the full pytest suite, and
`git diff --check`. Because this adds a module and a production dependency path,
Graphify is updated and the path from `AsyncEnhancedSerialAdapter` to the
pyserial-asyncio factory is verified.

## Subsequent Slice

After this factory is reviewed, the next design/implementation slice migrates
Enhanced semantic control and UART-send consumers to the async request boundary
and defines service lifecycle ownership. Continuous ingestion and reconnect are
then introduced without creating a second reader or processing pipeline. Only
after those consumers are ready does service startup switch from
`SerialCommandTransport` to the async factory.

## Acceptance Criteria

The slice is complete when one production-capable async factory opens and closes
one Enhanced serial resource, supplies the reviewed async adapter with one reader
and an exact-accounting writer, validates hello before return, cleans up every
failed start, and preserves all synchronous behavior. Production service startup
must still select the synchronous compatibility path at the end of this slice.
