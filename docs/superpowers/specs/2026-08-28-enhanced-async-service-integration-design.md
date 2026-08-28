# Enhanced Async Service Integration Design

**Date:** 2026-08-28

**Phase:** Phase 1, continuous ingestion and asynchronous Enhanced adapter

**Status:** Approved on 2026-08-28

## Purpose

Production-capable Enhanced asynchronous serial I/O now exists, but the Device
Core Service still composes synchronous semantic control, UART-send, capture,
and reconnect consumers around `SerialCommandTransport`. This slice migrates
the initial production Enhanced connection to `AsyncEnhancedSerialAdapter`
without changing the synchronous `DeviceCoreRuntime` or HTTP contracts and
without creating another serial reader.

The service composition layer will own one dedicated asyncio loop and the one
Enhanced adapter running on it. Core asynchronous semantic adapters will
translate control and UART-send operations at the existing async request
boundary. A narrow synchronous service bridge will let the existing runtime and
finite workflows use those adapters during this staged migration.

## Architectural Decision

Use a service-owned asynchronous host with synchronous facades.

This is preferred over putting event-loop and thread ownership in
`dutchmate_core`, which would mix infrastructure lifecycle into application
policy. It is also preferred over converting the complete runtime, workflows,
FastAPI endpoints, Basic backend, and reconnect coordinator to async in one
slice. That larger conversion would combine several independently reviewable
Phase 1 checklist items.

The resulting dependency direction remains:

1. core semantic adapters depend on core transport contracts;
2. the service adapter depends on the core async adapter and semantic adapters;
3. service startup composes the service adapter behind existing core ports; and
4. core policy does not import service, FastAPI, thread, or serial-framework
   details.

## Scope

This slice includes:

- asynchronous Enhanced semantic control and UART-send consumers;
- shared pure response interpretation between synchronous and asynchronous
  Enhanced consumers;
- one service-owned event-loop thread and adapter lifecycle;
- synchronous control, UART-send, and finite-capture facades over that one
  adapter;
- initial Enhanced service startup through
  `open_async_enhanced_serial_adapter()`;
- explicit runtime and FastAPI shutdown ownership; and
- deterministic unit and integration coverage of the bridge and startup path.

This slice does not include:

- continuous ingestion outside finite workflows;
- always-on connection-state monitoring;
- migration of reconnect opening to the async factory;
- removal of `SerialCommandTransport`, `EnhancedCaptureEventSource`, or the
  synchronous Enhanced semantic adapters;
- async conversion of `DeviceCoreRuntime`, workflows, or FastAPI endpoints;
- changes to Basic backend behavior;
- changes to HTTP, CLI, MCP, configuration, or session evidence formats; or
- firmware or hardware work.

## Core Async Semantic Consumers

`dutchmate_core.backends.enhanced` will add asynchronous equivalents of the
current semantic adapters:

- `AsyncEnhancedDeviceControl` awaits an `AsyncCommandTransport` for GPIO
  configuration, pulse, and active/idle state commands.
- `AsyncEnhancedUartSender` awaits an `AsyncCommandTransport` for complete UART
  payload transmission.

Both accept the existing narrow `AsyncCommandTransport` contract. This
boundary has concrete value because deterministic tests can substitute command
responses without constructing an event loop, serial stream, or full adapter.

The existing one-second Enhanced command timeout remains the default so the
migration does not introduce a new configuration surface. The asynchronous
consumers pass that timeout to `request()` for every operation.

Command construction and public error mapping remain unchanged. Private pure
helpers will interpret command success, firmware error, unexpected response,
and UART acknowledgement fields. The synchronous and asynchronous adapters use
the same helpers so they cannot drift in timestamp, byte-acceptance, timeout,
write-error, or protocol-input behavior.

No service module interprets Enhanced wire messages or imports wire DTOs.

## Service-Owned Enhanced Host

A new cohesive service adapter, `EnhancedAsyncHost`, will own one physical
Enhanced connection. It owns:

- one background thread;
- one asyncio event loop created and run by that thread;
- one `AsyncEnhancedSerialAdapter` opened on that loop;
- one `AsyncEnhancedDeviceControl` and one `AsyncEnhancedUartSender` sharing
  that adapter; and
- the synchronous facade methods consumed by the current runtime.

Host construction starts the loop, schedules the injected async adapter
factory on it, and waits until the factory returns a fully started,
hello-validated adapter. The adapter object is constructed and operated only on
its owning loop. The host caches immutable identity and segment ID after open.
After each event operation, it updates a lock-protected immutable segment
snapshot using state read on the owner loop. Synchronous properties read only
those host snapshots and never inspect mutable adapter state across threads.

Synchronous facade operations submit coroutines with
`asyncio.run_coroutine_threadsafe()` and wait for their result. The host exposes
the existing semantic method shapes for `DeviceControl` and `UartSender`, plus
the existing synchronous capture-source surface:

- `read_event()` submits `receive_event(timeout_s=0.1)`, preserving the current
  bounded finite-workflow polling cadence;
- `discard_pending_events()` drains queued adapter events only through an
  adapter-owned async operation added for this purpose;
- `info`, `segment_id`, and `segment` expose the host's thread-safe snapshots of
  validated adapter state; and
- `close()` owns complete adapter, loop, and thread shutdown.

The facade never reads a stream, parses NDJSON, creates another event queue, or
routes a command response. Those responsibilities remain exclusively in
`AsyncEnhancedSerialAdapter`.

## Startup Composition

For an initially selected Enhanced backend, `build_startup_runtime()` will:

1. recover stale sessions before opening hardware, as it does now;
2. construct one `EnhancedAsyncHost` using
   `open_async_enhanced_serial_adapter()` and segment ID zero;
3. obtain normalized identity from the host's validated adapter;
4. pass that same host through `ReplaceableDeviceControl` and
   `ReplaceableUartSender` and use it as the initial capture source;
5. retain the current synchronous reconnect coordinator for this transitional
   slice; and
6. record the normalized backend connection in `DeviceCoreRuntime`.

The initial Enhanced branch must not call `open_serial_command_transport()`,
`read_startup_hello()`, or construct `EnhancedCaptureEventSource`. The async
factory has already completed hello validation before the host is published.

If host construction succeeds but later runtime composition fails, startup
closes the host before propagating the original exception. Factory and host
cleanup failures must not replace the primary startup failure.

The Basic and disconnected startup branches remain unchanged.

## Runtime And FastAPI Lifecycle

`DeviceCoreRuntime` will gain an idempotent `close()` operation that closes its
current event source when that source exposes `close()`. The runtime remains
backend-neutral; it does not know about asyncio, threads, or Enhanced protocol
details.

`create_app()` records whether it constructed the runtime internally. Its
FastAPI lifespan closes only an internally owned runtime during application
shutdown. A runtime injected by a test or external caller remains caller-owned.

If applying startup hardware configuration raises unexpectedly after an
internal runtime was created, application construction closes that runtime
before re-raising. Expected firmware rejection remains visible through the
existing configuration/status behavior.

On Enhanced shutdown, closing the current source closes the adapter, waits for
its resource closure, stops the loop, and joins the thread. Repeated runtime,
host, or adapter closure is safe and waits for the same completed cleanup.

## Command And Event Data Flow

A control or UART-send request follows this path:

1. a synchronous FastAPI endpoint calls `DeviceCoreRuntime`;
2. the runtime workflow calls its stable replaceable semantic port;
3. `EnhancedAsyncHost` submits the async semantic operation to its loop;
4. the async semantic adapter builds the Enhanced command and awaits
   `AsyncEnhancedSerialAdapter.request()`;
5. the adapter's writer sends the frame while its sole reader continues reading;
6. the reader resolves the pending command response and queues interleaved UART
   or telemetry events; and
7. the mapped semantic result returns through the synchronous facade.

A finite capture follows this path:

1. the existing workflow calls `read_event()`;
2. the host submits one bounded `receive_event()` operation;
3. the adapter returns the oldest FIFO event, ordinary timeout, or terminal
   failure; and
4. the unchanged shared processing and session pipeline persists the event.

The adapter command lock remains the sole command serializer. A capture wait
and forced UART send may coexist because both are asynchronous operations on the
same loop and the reader remains independently runnable. No call path acquires
a second physical read capability.

## Failure And Shutdown Semantics

Existing protocol, transport, device-control, UART-send, and backend-input
exceptions retain their public classifications and details. The synchronous
bridge unwraps the submitted future and propagates the original operation
exception rather than inventing a service-specific wrapper.

The host rejects submissions immediately once closure begins or if its loop is
no longer available. Terminal adapter failures wake pending command and event
waiters. Valid events already admitted to the adapter queue remain FIFO and are
returned before the terminal failure, matching the approved adapter contract.

Shutdown order is:

1. prevent new host submissions;
2. schedule and await `AsyncEnhancedSerialAdapter.close()` on its owner loop;
3. stop the loop;
4. close the loop after its runner exits; and
5. join the thread.

The host must not attempt to join its own loop thread. All production closure
enters through the synchronous service/runtime boundary.

Blocked receive, command, or writer operations are terminalized by adapter
closure. Cleanup is idempotent, and no serial resource, adapter task, loop, or
thread may remain after `close()` returns.

## Transitional Reconnect Boundary

Finite-workflow reconnect remains on the existing synchronous compatibility
path for this slice. On disconnect, `RetryingCaptureReconnect` first closes the
current source. For the initial async source, that closes and joins the complete
host before the reconnect coordinator opens `SerialCommandTransport`.

The replacement source and semantic ports are then published through the
existing replaceable wrappers. Consequently the process never has an async and
synchronous reader open for the same configured port at the same time.

This staging preserves current finite-workflow reconnect behavior while keeping
the dedicated continuous-ingestion/reconnect migration independently
reviewable. A later slice will reopen through the async factory, coordinate
always-on ingestion, and remove this transitional path.

## Testing Strategy

Core semantic parity tests use fake synchronous and asynchronous command
transports. They prove identical command bytes and result/error behavior for:

- successful GPIO configuration, pulse, and state changes;
- successful complete UART acknowledgement;
- firmware command rejection;
- missing timestamp or incomplete byte acknowledgement;
- unexpected response type;
- command timeout;
- classified write failure; and
- malformed protocol input.

Service-host tests use injected async factories and adapters. They prove:

- the adapter is opened and operated on its owner loop;
- one host instance serves control, UART-send, and event operations;
- concurrent event waiting and command requests make progress;
- FIFO events interleaved with command responses are preserved;
- facade timeout returns `None` only for ordinary inactivity;
- original operation errors cross the synchronous bridge unchanged;
- startup failure stops the loop and thread;
- close terminalizes pending operations and closes exactly once;
- repeated close waits for the same cleanup;
- submissions after close fail immediately; and
- no loop thread remains after close returns.

Startup and application integration tests prove:

- Enhanced initial startup calls the async factory and never opens the
  synchronous transport;
- validated hello identity and capabilities reach runtime status;
- configured hardware mappings execute through async semantic control;
- finite capture and UART send use the same host;
- internal runtime ownership closes during FastAPI lifespan shutdown;
- injected runtimes remain caller-owned;
- Basic and disconnected startup behavior is unchanged; and
- reconnect opens the synchronous replacement only after async-host closure.

The validation gate is Ruff, mypy, the full pytest suite, and
`git diff --check`. Because this slice adds a service module, shared semantic
interfaces, and lifecycle dependencies, `graphify update .` is required and the
canonical graph outputs are committed.

## Acceptance Criteria

The slice is complete when:

1. initial production Enhanced startup selects
   `open_async_enhanced_serial_adapter()`;
2. one adapter owns the only Enhanced serial reader and physical resource;
3. semantic GPIO control and UART send operate through the async request
   boundary with unchanged public results and errors;
4. finite capture consumes the adapter FIFO through the unchanged runtime API;
5. current finite-workflow reconnect remains available without overlapping
   serial readers;
6. service shutdown leaves no serial resource, adapter task, event loop, or
   thread running;
7. Basic behavior and all external service contracts remain unchanged;
8. the complete validation gate passes; and
9. `docs/development_status.md` marks this item complete and selects the
   service-owned continuous ingestion coordinator as the sole next step.

## Subsequent Slice

After this integration is implemented and reviewed, the next Phase 1 slice adds
one service-owned continuous ingestion coordinator for the selected backend.
That coordinator will continuously process evidence and connection state
outside finite workflows without creating a second reader or processing
pipeline. Async reconnect coordination and removal of synchronous compatibility
follow in their existing status order.
