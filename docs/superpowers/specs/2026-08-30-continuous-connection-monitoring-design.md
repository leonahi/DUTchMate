# Continuous Connection And Integrity Monitoring Design

**Date:** 2026-08-30

**Status:** Approved for implementation planning

**Phase:** Phase 1, continuous ingestion and asynchronous Enhanced adapter

## Context

DUTchMate now owns one `ContinuousIngestionCoordinator` for each selected Basic
or Enhanced backend. The coordinator is the only consumer of the selected
normalized event source, drains events while no finite workflow is active, and
provides a fresh bounded FIFO to an active workflow.

That slice deliberately stopped short of changing `DeviceCoreStatus`. A backend
can therefore disconnect while the coordinator is idle, yet the runtime may
continue to report the last validated connection until a finite workflow reads
the retained terminal outcome. Enhanced buffer telemetry observed while idle is
also discarded before it can update live integrity status.

The next Phase 1 slice closes that observation gap. It uses the existing
coordinator boundary and does not add another reader, processing pipeline,
monitor thread, or background session.

## Goals

- Detect source terminalization continuously, including while no finite
  workflow is active.
- Make the next `DeviceCoreRuntime.status()` snapshot report an idle terminal as
  disconnected.
- Reconcile source health before any connection-required runtime operation so a
  stale logical connection cannot admit new work.
- Update live Enhanced UART-integrity status from buffer telemetry received
  inside or outside finite workflows.
- Preserve the same telemetry event for finite-workflow FIFO delivery and
  session evidence when a workflow is active.
- Preserve Basic integrity as `not_observable`.
- Preserve one coordinator ingestion thread and one physical reader.
- Keep the core independent from service implementation details.

## Non-Goals

- Automatic reconnect outside finite workflows.
- Migrating Enhanced reconnect to the asynchronous opener.
- Removing the synchronous reconnect compatibility path.
- Adding a background capture session or persisting idle UART/telemetry events.
- Adding public status or error-detail fields.
- Changing finite-workflow reconnect deadlines, segment limits, or evidence
  semantics.
- Changing HTTP, CLI, or MCP response schemas.

The next ordered Phase 1 item remains responsible for background reconnect,
hello and identity validation, source replacement, and segment origins.

## Architectural Decision

Use an optional pull-based monitoring port in core.

The service coordinator continuously maintains an immutable health snapshot.
`DeviceCoreRuntime` reads that snapshot when status is requested and before a
connection-required operation. This avoids a callback cycle between service and
core, eliminates startup callback-registration races, and requires no monitor
thread.

Two alternatives were rejected:

1. Coordinator-to-runtime callbacks would update runtime state immediately but
   introduce callback failure policy, startup replay, and cross-component lock
   ordering.
2. A separate monitor thread would add polling, shutdown coordination, and a
   second concurrency owner without improving source observation.

Graphify navigation identified `ContinuousIngestionCoordinator`,
`DeviceCoreRuntime`, `CaptureWorkflow`, `build_startup_runtime()`, and the
reconnect adapter as the affected ownership path. The current graph has no
direct coordinator-to-runtime call edge; the pull port preserves that direction
while making source health observable through the existing source reference.

## Core Monitoring Contract

Add these backend-neutral contracts beside the existing capture-source ports:

```python
@dataclass(frozen=True, slots=True)
class CaptureSourceHealth:
    connected: bool
    integrity: UartIntegrity | None


@runtime_checkable
class CaptureSourceMonitor(Protocol):
    def capture_source_health(self) -> CaptureSourceHealth:
        """Return one immutable current-source health snapshot."""
```

`integrity=None` means the monitor has no newer integrity projection to publish.
It does not mean `not_observable`, unknown backend mode, or disconnected. The
runtime retains its already validated integrity until the monitor reports a
new value or reports `connected=False`.

Sources that implement only `read_event()` remain compatible. Runtime monitoring
is optional and discovered structurally through the runtime-checkable protocol.

The health contract intentionally omits terminal exception type, message, and
raw context. Public status remains a connection/integrity snapshot, not an
asynchronous error log.

## Coordinator State And Event Projection

The coordinator stores one `CaptureSourceHealth` value under its existing
condition lock. Construction starts with `connected=True` and `integrity=None`.
No additional lock or thread is introduced.

For every outcome from the currently installed concrete source:

1. Read the source outside the coordinator condition lock.
2. Reacquire the condition and confirm source identity.
3. Refresh segment provenance from that same source.
4. Update the health snapshot when the outcome carries health information.
5. If a finite workflow is active, admit the event to its existing bounded FIFO
   using the existing generation and backpressure rules.
6. If idle, discard UART and evidence delivery after health projection.

Stale outcomes from a detached or replaced source cannot update segment,
integrity, connection state, or the active FIFO.

### Ordinary Timeout

`None` remains an ordinary source timeout. It does not change connection or
integrity state and ingestion immediately begins the next source read.

### UART Receive

`UartReceiveEvent` does not change health. It is delivered to an active
workflow or discarded while idle. Idle UART is never persisted or replayed.

### Buffer Overflow

`BufferOverflowEvent` publishes:

```python
UartIntegrity(
    loss_status="loss_reported",
    observation_scope="debug_helper_rx_buffer",
    dropped_bytes=<updated count>,
)
```

When a known dropped-byte count already exists, the event's incremental
`dropped_bytes` value is added. Otherwise the event establishes the first known
count.

### Buffer Status

`BufferStatusEvent` is cumulative telemetry. Its `dropped_bytes_total` is
combined with an existing known count using `max(previous, reported_total)`.
This matches session-summary behavior and prevents an overflow event followed by
its cumulative status from being counted twice.

If neither the current snapshot nor the status reports loss, the projection is:

```python
UartIntegrity(
    loss_status="none_reported",
    observation_scope="debug_helper_rx_buffer",
    dropped_bytes=0,
)
```

Once loss is reported for a connection segment, a later lower or zero
cumulative status cannot erase it.

### Terminal Outcomes

`BackendDisconnectedError`, `BackendInputError`, unexpected reader failure, and
coordinator close all publish `connected=False`. The existing exact terminal
object remains retained for finite-workflow delivery and cleanup behavior.

Terminal health publication occurs before the ingestion thread waits for
replacement or exits. The health snapshot never wraps, replaces, or exposes the
terminal object.

### Replacement

After the existing reconnect adapter validates and transfers a replacement,
`replace_source()` publishes `connected=True`, resets monitor integrity to
`None`, refreshes segment provenance, clears the consumed disconnect terminal,
and resumes the same ingestion thread.

Validated startup and reconnect remain the only authorities that restore
runtime identity, capabilities, and logical connection state. A monitor
snapshot with `connected=True` never restores them by itself.

## Runtime Reconciliation

`DeviceCoreRuntime` adds one private reconciliation helper. When its current
message source implements `CaptureSourceMonitor`, the helper reads one immutable
snapshot.

If `connected=False`, the runtime performs the existing idempotent disconnected
transition:

- `_connected=False`;
- clear commanded boot mode;
- clear backend identity and capabilities;
- clear segment provenance and integrity.

The runtime does not close or detach the coordinator. The retained source and
terminal remain owned by the existing coordinator/reconnect lifecycle.

If `connected=True` and `integrity` is not `None`, the runtime updates only its
live integrity projection. It does not mark the runtime connected and does not
restore identity, capabilities, control state, or policy.

Reconciliation runs:

- at the start of `status()`; and
- before `_require_connected()` decides whether a connection-required operation
  may proceed.

This ensures `GET /status` reflects an idle terminal on its next read and a new
operation cannot begin solely from stale runtime state. The health snapshot is
an observation, not a reservation: a source may still terminalize immediately
after reconciliation, and existing terminal/error handling remains responsible
for that race.

During finite-workflow reconnect, the existing reconnect deadline continues to
project `connection_state="reconnecting"`. Reconciliation must not erase that
deadline. Active-workflow disconnect callbacks remain valid and idempotent with
the monitor result.

## Public Behavior

No public schema changes.

After an idle terminal, the next status response uses existing fields:

- `connected=false`;
- `connection_state="disconnected"`;
- identity, capabilities, timestamp provenance, and integrity cleared according
  to existing disconnected semantics; and
- `reconnect_remaining_s=null` when no finite reconnect is active.

Connection-required operations after an idle terminal use the existing
`service_unavailable` behavior. No asynchronous terminal detail is added to
status or error context.

For Enhanced, live status integrity changes as buffer telemetry arrives. For
Basic, integrity remains `not_observable` because Basic produces no overflow
telemetry.

## Concurrency And Ownership Invariants

1. One coordinator thread remains the only consumer of one installed source.
2. No source read, source close, thread join, or blocking source operation occurs
   while holding the coordinator condition lock.
3. Health mutation and health snapshot reads use the coordinator condition
   lock and do not call runtime code.
4. Runtime may acquire the coordinator lock while holding its reentrant
   operation lock; the coordinator never acquires the runtime lock, so no lock
   cycle is introduced.
5. Source identity is checked before any health publication.
6. A telemetry event may update live health and enter an active workflow FIFO,
   but it is read from the physical source exactly once.
7. Idle events never enter a later workflow generation.
8. Replacement and close preserve existing exact-once ownership and cleanup
   behavior.

## Error Semantics

- Ordinary source timeout: keep monitoring.
- Idle disconnect: publish disconnected health; retain exact terminal for later
  lifecycle handling.
- Idle malformed input: publish disconnected health; retain non-reconnectable
  `BackendInputError`.
- Unexpected ingestion failure: publish disconnected health, close the source,
  and retain existing internal-failure behavior.
- Monitor snapshot read: deterministic in-memory operation with no independent
  error mapping.
- Runtime close: coordinator health becomes disconnected; existing exact-once
  cleanup outcome remains authoritative.

No UART payload, malformed frame, terminal message, or exception detail is
added to status, session metadata, or service error context.

## Test Strategy

### Coordinator Unit Tests

- Idle disconnect publishes disconnected health without workflow activation.
- Idle backend-input and unexpected failures publish disconnected health.
- Repeated `None` timeouts preserve connected health.
- Idle UART does not change health and is not replayed.
- Idle overflow and status telemetry update integrity using incremental and
  cumulative rules without double counting.
- Active telemetry updates health and is delivered exactly once through the
  workflow FIFO.
- A stale detached-source outcome cannot update health.
- Valid replacement publishes connected health and resets monitor integrity.
- Close publishes disconnected health and leaves no ingestion thread.

All concurrency tests use `Event` and `Condition` barriers with bounded waits;
they do not use timing sleeps.

### Runtime Unit Tests

- Status reconciles an idle terminal and clears existing identity, capabilities,
  timestamp provenance, commanded boot mode, and integrity.
- A connection-required operation reconciles before admission even when status
  was not called first.
- Enhanced live telemetry appears in status.
- Basic integrity remains `not_observable`.
- A connected monitor snapshot cannot restore a logically disconnected runtime.
- Plain `CaptureEventSource` implementations remain compatible.
- Reconnecting status and remaining deadline retain precedence.

### Service Integration Tests

- Basic and Enhanced startup continue to construct one coordinator around one
  physical source.
- An idle terminal becomes visible through the existing status endpoint.
- Enhanced idle telemetry updates the existing integrity response fields.
- App-owned shutdown closes the source and leaves no coordinator thread.
- Injected runtimes remain caller-owned.

### Validation Gate

- Focused coordinator, runtime, startup, status, and lifecycle tests.
- Ruff.
- Mypy.
- Full pytest suite.
- `git diff --check`.
- Dependency-direction check confirming core imports no service module.
- `graphify update .` because the slice adds a shared monitoring port and changes
  service-to-core relationships.

## Expected Files

- `core/src/dutchmate_core/workflows/capture.py`
- `core/src/dutchmate_core/runtime.py`
- `apps/service/src/dutchmate_service/continuous_ingestion.py`
- focused unit and service tests for those modules and status/startup behavior
- `docs/development_status.md`
- changed canonical Graphify artifacts

No protocol schema, session schema, CLI model, MCP model, or firmware file is
expected to change.

## Acceptance Criteria

The slice is complete when:

1. a source terminal observed while idle is reflected as disconnected by the
   next runtime/status read;
2. connection-required operations reconcile source health before admission;
3. Enhanced overflow telemetry updates live integrity inside and outside finite
   workflows;
4. active telemetry still reaches session evidence exactly once;
5. idle UART remains unpersisted and unreplayed;
6. Basic integrity and all public schemas remain unchanged;
7. no second reader, processing pipeline, monitor thread, or background session
   exists;
8. current finite-workflow reconnect and exact-once close behavior still pass;
9. architecture and full validation gates pass; and
10. `docs/development_status.md` marks only this queue item complete and selects
    “Coordinate reconnect, hello/identity validation, source replacement, and
    segment origins without creating a second processing pipeline” as the sole
    next step.
