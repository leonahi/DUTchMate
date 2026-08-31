# Coordinated Background Reconnect Design

**Date:** 2026-08-31

**Status:** Approved for implementation planning

**Phase:** Phase 1, continuous ingestion and asynchronous Enhanced adapter

## Context

DUTchMate now selects one service-owned `ContinuousIngestionCoordinator` for
either backend. That coordinator is the only consumer of normalized backend
events and continuously projects connection and integrity health. Enhanced
initial startup, control actions, UART send, and event receive use one
`EnhancedAsyncHost` and one asynchronous serial adapter.

Finite-workflow Enhanced reconnect is the remaining transitional path. It
closes the asynchronous host, opens `SerialCommandTransport`, validates hello
and identity, creates `EnhancedCaptureEventSource`, and publishes synchronous
control and UART-send adapters. Reconnect is also initiated only after an active
workflow consumes a disconnect. An idle disconnect therefore remains
disconnected until later service action, and production can return to the old
synchronous Enhanced stack after reconnect.

This slice coordinates idle and active reconnect through the existing stable
source boundary. It selects the asynchronous Enhanced opener for replacement
without adding another event consumer or physical serial reader. Deletion of
the now-unused synchronous compatibility implementation remains the following,
separately reviewable Phase 1 item.

## Goals

- Reconnect automatically after an idle Basic or Enhanced disconnect.
- Preserve the existing active-workflow reconnect deadline, segment limit,
  evidence, and failure semantics.
- Use `EnhancedAsyncHost` for every production Enhanced connection, including
  replacements.
- Validate Enhanced hello and exact configured identity before publication.
- Publish control, UART-send, event-source, health, identity, capability,
  integrity, and segment state as one ordered replacement transition.
- Establish required active-session segment provenance without removing the
  first timestamped event from the adapter FIFO.
- Preserve one normalized-event consumer and one physical reader.
- Make retry and shutdown deterministic and testable.
- Keep transport opening and service concurrency out of `dutchmate_core`.

## Non-Goals

- Removing synchronous compatibility classes and tests in the same slice.
- Changing public HTTP, CLI, MCP, status, or error schemas.
- Adding a persistent background session or retaining idle UART evidence.
- Changing session formats, the 32-segment maximum, workflow deadlines, or
  reconnect-timeout configuration.
- Adding a public idle-retry setting.
- Changing protocol schemas or firmware behavior.
- Reconnecting after a fatal backend-input error from an already published
  source; that remains distinct from a disconnect.

## Considered Approaches

### Extend `ContinuousIngestionCoordinator`

The ingestion thread could open, validate, retry, and install replacements
itself. This uses fewer objects but gives one class independently changing
responsibilities: event draining, workflow FIFO behavior, backend-specific
opening, identity policy, retry timing, and shutdown. It is rejected.

### Add A Service-Owned Reconnect Coordinator

A service-owned coordinator owns retry state and replacement publication while
the ingestion coordinator remains the only normalized-event consumer. The same
object serves idle reconnect and the existing `CaptureReconnect` call used by
active workflows. This is selected.

### Move Background Reconnect Into `DeviceCoreRuntime`

The runtime could own a worker and call backend openers directly. This would
pull transport selection, service lifecycle, and concurrency policy into core
application code and reverse the intended dependency direction. It is
rejected.

## Ownership And Boundaries

The service layer adds one `BackendReconnectCoordinator` per configured
runtime. It owns:

- the idle reconnect worker and interruptible retry wait;
- mutual exclusion between idle and active reconnect attempts;
- candidate open, validation, publication, and failed-candidate cleanup;
- the immutable expected backend identity and capability policy;
- shutdown of an unpublished candidate; and
- the existing callable active-workflow reconnect boundary.

`ContinuousIngestionCoordinator` continues to own the installed concrete event
source, its ingestion thread, workflow cursor, retained terminal, health
projection, and atomic source replacement. It exposes only the small state and
coordination operations needed to observe and claim a disconnected source.
Neither the reconnect coordinator nor `DeviceCoreRuntime` reads normalized
events.

`EnhancedAsyncHost` continues to own one asyncio loop, asynchronous adapter,
reader task, control adapter, and UART sender for one physical connection. A
replacement host is a new source bound permanently to the requested segment
ID; a host is never rebound across reconnects.

Core retains backend-neutral value types and optional source-monitor contracts.
It does not import the service coordinator, threads, asyncio, serial libraries,
or backend open factories.

## Reconnect State Model

The service reconnect coordinator serializes these states:

```text
connected
  -> disconnected_unclaimed
  -> opening_idle | opening_active
  -> publishing
  -> connected

opening_* -> retry_wait | rejected | closing
retry_wait -> opening_* | closing
```

At most one open candidate exists. Idle and active attempts cannot overlap.
The old source is detached and closed before a candidate opens, so no old and
new reader can own the configured port simultaneously.

### Idle Disconnect

When the ingestion coordinator observes `BackendDisconnectedError` while no
workflow cursor is active, it retains the exact terminal, publishes
disconnected health, and wakes the reconnect worker. The worker atomically
claims the terminal, detaches and closes the old source, then opens candidates
until one publishes or service shutdown begins.

Idle retry is indefinite for the lifetime of the configured service. It uses
interruptible exponential backoff beginning at 0.1 seconds and capped at 2.0
seconds. The clock, wait primitive, and retry values are injectable in tests.
No public setting is added. A successful publication resets the next retry
sequence to 0.1 seconds.

An idle Enhanced candidate may publish after valid hello and identity while
its segment context is still `None`. There is no active session requiring
durable segment metadata at that moment. The first later timestamped event
establishes the immutable origin through the existing adapter behavior. The
coordinator updates its segment projection, and a later new session uses that
connection as session-local segment `0` through the existing runtime facade.

### Active-Workflow Disconnect

When a workflow cursor is active, the background worker does not claim the
terminal. The finite workflow consumes it, persists interruption and old
segment finalization, applies the 32-segment gate, and calls the reconnect
coordinator with the next session-local segment ID and the existing minimum of
workflow and reconnect deadlines.

That caller owns active retry until success, deadline, fatal input failure, or
shutdown. Active retry preserves the current fixed 0.1-second retry interval
and immutable caller deadline. A deadline tie, normal workflow deadline,
reconnect timeout, explicit stop, evidence-quota stop, and reconnect-limit
outcome remain unchanged.

Because runtime rejects new connection-required work while disconnected, a new
workflow cannot begin midway through an idle reconnect. A workflow already
active at disconnect always owns the active path.

## Enhanced Candidate Preparation

Enhanced reconnect opens `EnhancedAsyncHost` through the same asynchronous
production factory selected at initial startup. Adapter startup owns the sole
reader and validates the first complete message as hello. Service composition
then compares the normalized replacement identity with the immutable expected
mode, configured port, device, firmware, and capabilities required by current
policy. An incompatible candidate is never published.

Active reconnect additionally requires segment provenance before returning a
replacement. The asynchronous adapter gains a wait-only segment-ready
operation. Its reader sets the immutable segment context before placing the
first timestamped normalized event into the bounded FIFO and signals readiness
without dequeuing that event. The synchronous host facade bridges this wait on
the existing owner loop. Therefore:

- hello and command responses do not invent an origin;
- the first timestamped evidence event remains FIFO-visible to the ingestion
  coordinator and active workflow;
- terminal input/disconnect errors wake the segment waiter unchanged; and
- the active deadline bounds provenance waiting without a polling reader.

Idle candidates do not wait for origin before publication. Active candidates
that cannot establish origin by the caller deadline close and fail according
to existing reconnect precedence.

Basic candidate preparation keeps the existing connection factory, identity
check, host-monotonic segment context, and normalized event source. It uses the
same reconnect coordinator and publication rules but adds no serial reader.

## Atomic Replacement Publication

A candidate is externally invisible until opening and validation succeed.
Publication occurs in this order:

1. prepare the complete candidate and backend snapshot;
2. replace the stable semantic control and UART-send targets;
3. transfer the candidate source into `ContinuousIngestionCoordinator`;
4. publish connected health with the validated snapshot and a monotonically
   increasing connection generation; and
5. allow `DeviceCoreRuntime` to adopt that generation through its existing
   pull-based source-monitor reconciliation.

Source installation is the commit point because it changes monitor health to
connected only after semantic ports are ready. Runtime connection-required
operations reconcile monitor state before admission, so they cannot call a
partially published port. A failure before the commit point closes the
candidate and retains disconnected health. Operations after the commit point
are idempotent state projection and cannot reopen or consume the source.

The backend-neutral health snapshot is extended with an optional validated
`BackendSnapshot` and connection generation. Existing disconnected and
integrity-only behavior remains valid. Runtime records the last adopted
generation and restores logical identity, capabilities, policy, segment, and
integrity only from a newer connected validated snapshot. `connected=True`
without a newer validated snapshot still cannot restore runtime state.

For active reconnect, runtime retains its existing independent comparison
against the active session snapshot before accepting the replacement. It then
adopts the same published generation. This preserves defense in depth without
opening or reading a transport in core.

## Failure Semantics

- Transient open failure or pre-publication disconnect retries while the
  applicable idle lifetime or active deadline remains.
- Active invalid hello, malformed protocol input, or identity mismatch remains
  immediate `backend_input_error`; the active session fails without reconnect
  retry.
- Idle invalid or incompatible candidates are closed and rejected. The service
  remains disconnected and retries with bounded backoff so compatible firmware
  can later be attached.
- A fatal backend-input error from a published source remains terminal and is
  not converted to a reconnect opportunity.
- Events already admitted before a terminal remain FIFO-visible under existing
  coordinator rules.
- Candidate cleanup failures are retained and surfaced through shutdown rather
  than hidden by retry.

## Shutdown And Races

Service shutdown prevents new reconnect claims, interrupts idle backoff, wakes
active waiters, and waits for the reconnect worker. An unpublished candidate is
closed exactly once. The ingestion coordinator then closes or waits for its
currently installed source using its existing idempotent lifecycle. No loop,
reader task, serial resource, ingestion thread, reconnect worker, or blocked
waiter remains after runtime closure returns.

Lock ordering is service reconnect state, then source-owner transition. No
service lock is held while blocking on serial open, adapter segment readiness,
sleep/backoff, thread join, or source close. Runtime continues to pull an
immutable monitor snapshot and never calls back into service while holding a
service lock.

## Testing Strategy

Deterministic service tests prove:

1. idle Basic and Enhanced disconnect wake exactly one reconnect worker;
2. an active workflow owns reconnect and suppresses idle claiming;
3. idle and active opening never overlap;
4. Enhanced reconnect uses the async host factory and never the synchronous
   transport factory;
5. valid hello and exact identity are required before publication;
6. idle Enhanced publication may precede origin, while active publication
   waits for provenance;
7. segment readiness preserves the first event in exact FIFO order;
8. replacement ports become ready before connected health is visible;
9. runtime adopts each validated connection generation once;
10. active deadlines, deadline ties, segment IDs, and reconnect-limit outcomes
    remain unchanged;
11. transient idle failures use bounded interruptible backoff;
12. active invalid input fails immediately while idle invalid candidates retry;
13. close during open, origin wait, retry wait, and publication leaves no
    candidate, reader, loop, or worker; and
14. Basic, Enhanced, runtime, session, HTTP, CLI, and MCP behavior remains
    externally compatible.

Adapter tests add segment-ready signaling, terminal propagation, timeout,
cancellation, first-event preservation, and close wake-up coverage. Existing
shared fake-backend, reconnect, session-segment, monitoring, startup, and
shutdown tests remain green.

## Documentation And Validation

Implementation updates `docs/software_architecture.md` to identify the new
service reconnect owner and removes wording that production reconnect uses the
synchronous compatibility source. `docs/development_status.md` remains the sole
progress tracker and selects compatibility-path removal only after this slice
passes.

The structural validation gate is:

- Ruff;
- mypy;
- full pytest;
- `git diff --check`; and
- `graphify update .`, with only canonical graph artifacts committed.

## Acceptance Criteria

The slice is complete when:

1. both backends reconnect automatically after an idle disconnect;
2. active-workflow reconnect semantics and persisted evidence are unchanged;
3. every production Enhanced open uses one async host and one reader;
4. Enhanced hello, identity, and active segment origin are validated before
   active replacement publication;
5. the first origin-establishing event is not consumed by preparation;
6. source, semantic ports, health, and runtime state publish in safe order;
7. idle and active reconnect cannot overlap;
8. shutdown is deterministic with no leaked resources or workers;
9. the complete validation gate passes; and
10. `docs/development_status.md` marks coordinated reconnect complete and names
    synchronous compatibility removal as the sole next step.
