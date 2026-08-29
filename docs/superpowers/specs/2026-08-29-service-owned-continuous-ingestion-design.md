# Service-Owned Continuous Ingestion Design

**Date:** 2026-08-29

**Status:** Approved design

**Phase:** Phase 1 — continuous ingestion and asynchronous Enhanced adapter

## Context

DUTchMate now selects one service-owned `EnhancedAsyncHost` for initial
Enhanced control, UART send, and finite capture. Basic and Enhanced sources
both expose an existing normalized FIFO boundary, but `DeviceCoreRuntime`
consumes that boundary only while a finite capture, boot-test, or wait-pattern
workflow is active.

The Enhanced adapter intentionally applies bounded backpressure. Without a
lifetime consumer, its event queue can fill while the service is otherwise
idle and prevent the reader from reaching later command responses. The Basic
source likewise benefits from continuously draining its existing reader FIFO.

The next slice introduces one service-owned coordinator that continuously
consumes the selected backend without creating another physical serial reader.
It preserves explicit finite sessions: idle UART is not persisted and cannot
leak into a later workflow.

## Goals

- Continuously drain the selected Basic or Enhanced normalized event source
  throughout the service runtime.
- Keep one physical serial reader and one logical consumer of its normalized
  event boundary.
- Preserve exact FIFO ordering and lossless backpressure while a finite
  workflow is active.
- Give every finite workflow a fresh event cursor established before any
  boot/reset action.
- Keep asyncio, threads, and mutable source replacement in the service layer.
- Keep `DeviceCoreRuntime` and `CaptureWorkflow` backend-neutral.
- Preserve the current synchronous Enhanced reconnect opener for this slice.
- Provide deterministic, idempotent shutdown with no leaked source, thread,
  producer, or consumer.

## Non-Goals

- Persisting an always-on or background UART session.
- Prepending idle UART traffic to the next finite workflow.
- Continuously projecting connection or integrity changes into service status.
- Migrating reconnect opening to the asynchronous Enhanced factory.
- Adding API, CLI, or MCP surfaces.
- Adding RP2040 firmware, HIL behavior, or configuration knobs.
- Removing the synchronous reconnect compatibility path.

## Architectural Decision

Add `ContinuousIngestionCoordinator` under `apps/service/`. One coordinator is
created for the selected backend and remains stable for the lifetime of its
`DeviceCoreRuntime`.

The coordinator owns one ingestion thread. That thread calls the selected
source's existing synchronous `read_event()` compatibility boundary. For Basic,
this consumes `BasicBackendEventSource`'s existing reader FIFO; for Enhanced,
it delegates through `EnhancedAsyncHost` to the adapter on its owner loop. It
does not open a serial port or perform a second physical read.

The coordinator itself exposes the synchronous capture-source surface consumed
by `DeviceCoreRuntime`. It also exposes explicit workflow lifecycle operations
and service-only source-terminalization/replacement operations. The runtime
therefore keeps a stable source identity while service composition remains
responsible for opening concrete backend resources.

This is preferred over recreating a coordinator per connection because it
keeps workflow admission, active FIFO ownership, and shutdown state in one
lifetime object. It is preferred over placing ingestion in `DeviceCoreRuntime`
because core policy must not own service threading or transport lifecycle.

## Components And Boundaries

### `ContinuousIngestionCoordinator`

The service coordinator owns:

- the current normalized `CaptureEventSource`;
- one ingestion thread;
- one bounded active-workflow FIFO, with production capacity 256 and an
  injectable smaller capacity for deterministic tests;
- an explicit lifecycle state;
- a workflow-active flag and generation/cursor identity;
- the retained terminal backend outcome, if any;
- a close-completion barrier and retained cleanup outcome; and
- thread-safe snapshots of the current segment and source-facing metadata
  needed by the existing runtime boundary.

It implements the existing synchronous operations used by finite workflows:

- `read_event()`;
- `discard_pending_events()` where compatibility requires it;
- `segment` and other already-consumed source properties; and
- `close()`.

It additionally provides service/workflow lifecycle operations:

- `begin_workflow()`;
- `end_workflow()`;
- `close_current_source_for_reconnect()`; and
- `replace_source(replacement)` for the existing reconnect adapter.

No new generic transport abstraction is introduced.

### Workflow Lifecycle Port

Core gains a small explicit workflow-lifecycle port associated with capture
event sources. It defines `begin_workflow()` and `end_workflow()` and exists to
solve one concrete race: boot UART may arrive after a reset action but before
the first `read_event()` call.

`CaptureWorkflow` invokes the lifecycle only when the supplied source supports
that port. Existing simple sources and test fakes remain valid capture sources.
The lifecycle is backend-neutral and contains no threading or service types.

### Startup Composition

For a connected Basic or Enhanced backend, startup:

1. opens the existing concrete source exactly as today;
2. constructs and starts one `ContinuousIngestionCoordinator` around it;
3. passes the coordinator to `DeviceCoreRuntime` as its message source; and
4. retains existing device-control and UART-send composition.

Disconnected startup remains unchanged. A failure after coordinator creation
closes the coordinator before propagating the primary startup error. Cleanup
failure must not mask that primary error.

## Coordinator State Model

The coordinator has four externally meaningful states:

### Idle

The ingestion thread continuously reads the selected source. Ordinary `None`
timeouts continue the loop. Normalized UART and telemetry events are discarded
without persistence or replay. No idle event backlog is retained; memory is
bounded to coordinator state and the active FIFO. A terminal backend outcome
is retained so the next workflow cannot wait indefinitely on a dead source.

### Active

`begin_workflow()` atomically creates a fresh empty FIFO and marks one workflow
active. Runtime serialization already prevents two finite workflows, and the
coordinator rejects a second activation defensively.

Every later normalized event is placed into the bounded FIFO in exact source
order. `read_event()` consumes that FIFO. When the FIFO is full, the ingestion
thread waits for capacity. It does not drop, overwrite, or reorder evidence.
Sustained blockage therefore propagates through the existing backend
backpressure and timeout/disconnect policy.

### Terminal

The coordinator retains `BackendInputError` or `BackendDisconnectedError`
after all earlier admitted events. During an active workflow, `read_event()`
observes the valid FIFO prefix before the same terminal outcome. During idle,
the retained terminal outcome is presented when the next workflow activates or
reads.

`BackendInputError` remains non-reconnectable. `BackendDisconnectedError`
continues into the existing finite-workflow reconnect path.

### Closing / Closed

Closing rejects new workflow activation and source replacement. It wakes
blocked producers and consumers, closes the current concrete source, waits for
the ingestion thread, retains the first cleanup outcome, and publishes one
completion barrier.

Concurrent and later callers wait for the same completion and observe the same
retained cleanup error object. No source read, close, condition wait, or thread
join occurs while holding the coordinator state lock.

## Finite Workflow Ordering

For a coordinator-backed source, `CaptureWorkflow` follows this order:

1. validate the request and establish the backend snapshot;
2. create the durable session/recorder;
3. activate the coordinator, establishing a fresh cursor;
4. publish session-start callbacks;
5. perform the optional boot/reset start action;
6. consume the coordinator FIFO until the existing deadline or terminal
   outcome; and
7. end coordinator workflow ownership in `finally` after session
   terminalization logic.

Activation before the start action ensures the first boot byte is eligible for
the session. Activation after durable session creation prevents a failed
session admission from accumulating evidence that cannot be owned.

`end_workflow()` returns the coordinator to idle, clears unread workflow-local
events, and releases any blocked producer. A later workflow always receives a
new generation and cannot observe the previous workflow's unread events.

Existing `discard_pending_events()` behavior remains for compatibility with
non-coordinator sources and wait-pattern tests. Coordinator activation itself
is the authoritative fresh-cursor boundary.

## Reconnect Compatibility

This slice does not change how a replacement connection is opened. The current
`RetryingCaptureReconnect` retains its bounded retry/deadline policy,
synchronous replacement opener, identity/provenance validation, and
control/UART-send replacement behavior. It no longer owns a second reference
that may close the current concrete source; it delegates concrete-source
terminalization and publication to the stable coordinator that owns that
source.

A service wrapper maps the validated concrete replacement into the stable
coordinator:

1. the active coordinator publishes the ordered disconnect outcome and pauses
   its ingestion thread in terminal state;
2. the reconnect adapter calls
   `close_current_source_for_reconnect()`, which atomically detaches and closes
   the failed concrete source under the coordinator's ownership;
3. the existing reconnect adapter opens and validates a concrete replacement;
4. `replace_source()` transfers ownership of that replacement into the
   coordinator, clears the consumed disconnect terminal, updates segment
   snapshots, and resumes ingestion; and
5. reconnect returns the same coordinator facade with the replacement backend
   snapshot to `DeviceCoreRuntime`.

The synchronous opener remains the only reconnect opener. The coordinator does
not open transports or validate hello/identity itself.

If replacement races with shutdown, `replace_source()` rejects and closes the
incoming source. It is never published. Runtime close continues to wait for its
in-flight reconnect boundary, so no replacement resource survives after close
returns.

## Error Semantics

- Ordinary read timeout: continue ingestion.
- Backend disconnect: preserve FIFO prefix, then deliver the retained
  `BackendDisconnectedError` identity.
- Malformed/backend input: preserve FIFO prefix, then deliver the retained
  `BackendInputError`; do not reconnect.
- Unexpected ingestion failure: close the current source, stop coordinator
  ingestion, and let the existing bounded `internal_error` projection handle
  the failure; do not reinterpret it as a reconnectable disconnect.
- Active FIFO full: apply lossless backpressure.
- Workflow ends with unread events: discard them when returning to idle.
- Replacement rejected after close: close it and preserve the primary close
  outcome.
- Source/ingestion cleanup failure: retain one primary cleanup error and share
  it with all close callers.

No UART payload or malformed input is added to service error context or
session metadata outside the established bounded evidence paths.

## Status And Persistence

This slice does not add background sessions and does not change the session
schema. Only events admitted after `begin_workflow()` can reach
`CaptureRecorder`.

The coordinator retains enough terminal state to avoid blocking a later
workflow on a dead source, but it does not independently change
`DeviceCoreStatus`. Continuous connection/integrity monitoring is a separate
approved Phase 1 queue item and will consume the coordinator boundary later.

Existing HTTP, CLI, and MCP-visible schemas remain unchanged.

## Concurrency Invariants

1. Exactly one coordinator ingestion thread consumes one selected normalized
   source at a time.
2. The coordinator never opens a serial resource and never creates a physical
   reader.
3. At most one finite workflow generation is active.
4. Idle events never enter a later workflow generation.
5. Active events are delivered exactly once in FIFO order or remain subject to
   explicit backend terminalization; they are never silently dropped.
6. Concrete source replacement is atomic with respect to close and workflow
   reads.
7. The coordinator is the sole concrete-source owner after installation; a
   rejected or invalid replacement is closed exactly once by the owner that has
   not yet transferred it.
8. `close()` returns only after source and ingestion-thread cleanup completes.
9. No blocking resource operation occurs while holding the coordinator state
   lock.

## Testing Strategy

Coordinator unit tests use event barriers, condition variables, and join
timeouts rather than sleeps. They cover:

- immediate idle draining with no session persistence;
- fresh workflow activation and no idle-event leakage;
- activation before boot/reset output is produced;
- exact FIFO delivery;
- a capacity-one queue proving lossless producer backpressure;
- workflow end clearing unread events and unblocking the producer;
- ordinary timeouts;
- valid-prefix-before-disconnect and valid-prefix-before-input-error ordering;
- retained idle terminal outcomes;
- Basic and Enhanced facade parity;
- validated source replacement and segment-snapshot publication;
- replacement failure and replacement-versus-close races;
- close while idle, active, blocked on read, and blocked on queue capacity;
- concurrent close callers sharing completion and cleanup errors; and
- rejection of workflow activation after close.

Workflow tests prove lifecycle ordering around durable session creation,
callbacks, boot/reset actions, persistence failure, normal completion, and
exceptions. Startup and reconnect tests prove one coordinator, one source, no
second serial opener/reader, stable facade identity, and cleanup on partial
composition failure.

Application lifecycle tests prove FastAPI-owned runtime shutdown leaves no
coordinator thread or backend source alive. Existing endpoint and session tests
remain unchanged at their public boundaries.

Architecture verification includes Graphify navigation plus direct source
inspection. It must show that the service coordinator is the sole normalized
event consumer, Basic retains one physical reader thread, Enhanced retains one
adapter reader task, and core imports no service module.

## Validation

The implementation slice must pass:

- focused coordinator, workflow, startup, reconnect, runtime-lifecycle, and
  application-lifecycle tests;
- Ruff;
- mypy;
- the full pytest suite;
- `git diff --check`; and
- `graphify update .` with only canonical graph artifacts staged.

`docs/development_status.md` remains the only progress and next-step tracker and
is updated only when the implementation slice is completed and reviewed.
