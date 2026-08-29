# Service-Owned Continuous Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continuously drain the selected Basic or Enhanced backend through one service-owned coordinator while preserving fresh finite-workflow cursors, lossless active FIFO ordering, synchronous reconnect compatibility, and deterministic shutdown.

**Architecture:** Add a backend-neutral workflow-lifecycle port in core, then implement one stable `ContinuousIngestionCoordinator` in the service layer around the already-normalized synchronous event source. The coordinator owns the concrete source and one ingestion thread, discards idle events, queues active-workflow events with bounded backpressure, and swaps validated reconnect sources without creating another physical reader.

**Tech Stack:** Python 3.10+, `threading`, `collections.deque`, existing DUTchMate backend/workflow contracts, pytest, Ruff, mypy, Graphify

**Spec:** `docs/superpowers/specs/2026-08-29-service-owned-continuous-ingestion-design.md`

## Global Constraints

- `docs/development_status.md` remains the sole progress and next-step tracker.
- This plan's checkboxes express execution order only; they do not become a
  competing resume/status record.
- Keep `DeviceCoreRuntime`, `CaptureWorkflow`, session persistence, HTTP, CLI, and MCP contracts backend-neutral and synchronous.
- Keep coordinator/thread/source-replacement ownership in `apps/service`; core must not import service modules or threading details.
- Use the selected backend's existing normalized `read_event()` boundary; do not open a serial resource or create another Basic reader thread or Enhanced reader task.
- Production active-workflow FIFO capacity is exactly 256; tests may inject a smaller positive capacity.
- Idle UART and telemetry events are discarded, not persisted, buffered, or replayed into a later workflow.
- A workflow cursor starts after durable session creation and before callbacks or a boot/reset start action.
- Active events are lossless and FIFO ordered; a full active queue applies producer backpressure without drop, overwrite, or reorder.
- Preserve valid-event-prefix-before-terminal ordering and the exact retained `BackendDisconnectedError` or `BackendInputError` object.
- `BackendInputError` and unexpected ingestion failures do not reconnect; only `BackendDisconnectedError` enters the existing finite-workflow reconnect path.
- Preserve the synchronous reconnect opener, retry interval, deadline, Enhanced hello/identity checks, segment provenance, and stable control/UART-send facades.
- Source replacement must never permit two live concrete sources; the coordinator becomes the sole concrete-source owner when constructed or when replacement is accepted.
- Runtime/application close remains idempotent, waits for in-flight reconnect and coordinator cleanup, and shares one retained cleanup error across concurrent callers.
- Add no connection/status monitor, asynchronous reconnect factory, background session, public endpoint, configuration option, firmware, or HIL behavior in this slice.
- Use event barriers, condition variables, and bounded joins in concurrency tests; do not use timing sleeps to establish ordering.
- Complete structural validation with Ruff, mypy, full pytest, `git diff --check`, and `graphify update .`; stage only canonical Graphify artifacts.
- Preserve the user's unrelated unstaged `AGENTS.md` change throughout execution.

## File Responsibility Map

- `core/src/dutchmate_core/workflows/capture.py`: backend-neutral optional workflow cursor lifecycle and exact activation/terminalization ordering.
- `tests/unit/workflows/test_capture_workflows.py`: durable-session-before-activation, callback/start-action ordering, and `finally` cleanup behavior.
- `core/src/dutchmate_core/runtime.py`: session-local lifecycle delegation plus reconnect-source ownership while runtime close waits.
- `tests/unit/runtime/test_device_core_lifecycle.py`: session-view delegation and close/reconnect ownership races.
- `apps/service/src/dutchmate_service/continuous_ingestion.py`: stable source owner, idle drain, active bounded FIFO, terminal ordering, source replacement, and deterministic close.
- `apps/service/tests/test_continuous_ingestion.py`: deterministic coordinator behavior and concurrency tests for both backend-shaped sources.
- `apps/service/src/dutchmate_service/backend_reconnect.py`: reconnect against the stable coordinator without retaining a second concrete-source reference.
- `apps/service/tests/test_backend_reconnect.py`: close-before-open, validation-before-transfer, stable-facade return, deadline, and publication failure coverage.
- `apps/service/src/dutchmate_service/startup.py`: construct exactly one coordinator for Basic or Enhanced startup and pass it to runtime/reconnect.
- `apps/service/tests/test_startup_config.py`: selected-backend coordinator wiring, finite capture/reconnect behavior, and partial-startup cleanup.
- `apps/service/tests/test_app_lifecycle.py`: FastAPI-owned runtime shutdown reaches coordinator, ingestion thread, and concrete source.
- `docs/development_status.md`: completed slice, validation evidence, reviewed code baseline, and the next ordered Phase 1 item.
- `graphify-out/`: canonical graph artifacts refreshed after the structural changes.

---

### Task 1: Add The Backend-Neutral Workflow Cursor Lifecycle

**Files:**
- Modify: `core/src/dutchmate_core/workflows/capture.py:38-56,551-730`
- Modify: `core/src/dutchmate_core/runtime.py:148-181`
- Modify: `tests/unit/workflows/capture_test_support.py`
- Modify: `tests/unit/workflows/test_capture_workflows.py`
- Modify: `tests/unit/runtime/test_device_core_lifecycle.py`

**Interfaces:**
- Consumes: existing `CaptureEventSource.read_event() -> BackendEvent | None` and optional duck-typed source properties.
- Produces: runtime-checkable `CaptureWorkflowLifecycle` with `begin_workflow() -> None` and `end_workflow() -> None`.
- Preserves: all existing sources that implement only `read_event()`; `_SessionCaptureSource` delegates lifecycle calls when its wrapped source supports them.

- [ ] **Step 1: Write failing workflow lifecycle-order tests**

Add a lifecycle-aware fake beside `FakeCaptureEventSource` in
`tests/unit/workflows/capture_test_support.py`; extend its `collections.abc`
import to include `Callable`:

```python
class LifecycleCaptureEventSource(FakeCaptureEventSource):
    def __init__(
        self,
        script: list[BackendEvent | None],
        *,
        clock: FakeMonotonicClock,
        trace: list[str],
        session_exists: Callable[[], bool],
    ) -> None:
        super().__init__(script, clock=clock)
        self._trace = trace
        self._session_exists = session_exists

    def begin_workflow(self) -> None:
        assert self._session_exists()
        self._trace.append("begin")

    def end_workflow(self) -> None:
        self._trace.append("end")

    def read_event(self) -> BackendEvent | None:
        self._trace.append("read")
        return super().read_event()
```

In `test_capture_workflows.py`, add:

```python
def test_capture_activates_cursor_after_session_creation_before_callbacks(
    tmp_path: Path,
) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureEventSource(
        [None],
        clock=clock,
        trace=trace,
        session_exists=lambda: any(tmp_path.iterdir()),
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=0.1,
        command="capture",
        monotonic_clock=clock,
        on_session_started=lambda _session_id: trace.append("callback"),
    )

    assert trace[0:2] == ["begin", "callback"]
    assert trace[-1] == "end"
    assert trace.index("begin") < trace.index("read")
```

Add a second test whose `on_session_started` raises one retained exception and
asserts the session is failed and `trace == ["begin", "callback", "end"]`.
Add a boot-action test with a valid `DeviceActionResult` and assert
`begin < callback < start_action < first read < end`.

- [ ] **Step 2: Run the lifecycle tests and capture RED**

Run:

```bash
rtk pytest tests/unit/workflows/test_capture_workflows.py -k "activates_cursor or ends_cursor or cursor_before_boot" -v
```

Expected: FAIL because `CaptureWorkflow` does not call `begin_workflow()` or
`end_workflow()`.

- [ ] **Step 3: Define the lifecycle port and place it around the existing workflow body**

In `capture.py`, import `runtime_checkable` and add:

```python
@runtime_checkable
class CaptureWorkflowLifecycle(Protocol):
    """Optional fresh-cursor lifecycle implemented by continuous sources."""

    def begin_workflow(self) -> None:
        """Activate one new finite-workflow cursor."""

    def end_workflow(self) -> None:
        """Release the active cursor and discard its unread events."""
```

After `CaptureRecorder.start()` succeeds, resolve the optional lifecycle:

```python
lifecycle = source if isinstance(source, CaptureWorkflowLifecycle) else None
workflow_cursor_active = False
```

As the first statements of the existing `try`, before either callback, add:

```python
if lifecycle is not None:
    lifecycle.begin_workflow()
    workflow_cursor_active = True
```

Keep the current workflow and `except Exception` statements inline. After that
existing `except` block, add:

```python
finally:
    if workflow_cursor_active:
        lifecycle.end_workflow()
```

Ensure all existing early returns still execute this `finally` block.

- [ ] **Step 4: Add session-local lifecycle delegation**

Extend `_SessionCaptureSource` in `runtime.py` so a coordinator remains visible
through the segment-zero mapping used after reconnect:

```python
def begin_workflow(self) -> None:
    lifecycle = self._source if isinstance(self._source, CaptureWorkflowLifecycle) else None
    if lifecycle is not None:
        lifecycle.begin_workflow()

def end_workflow(self) -> None:
    lifecycle = self._source if isinstance(self._source, CaptureWorkflowLifecycle) else None
    if lifecycle is not None:
        lifecycle.end_workflow()
```

Import `CaptureWorkflowLifecycle` from `dutchmate_core.workflows.capture`. Add a
runtime test with a source bound to `segment_id=3`; run a finite capture and
assert one begin/end pair while the persisted session still uses segment zero.

- [ ] **Step 5: Run focused workflow and runtime tests**

Run:

```bash
rtk pytest tests/unit/workflows/test_capture_workflows.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: PASS, including the new lifecycle ordering/delegation tests and all
existing simple-source tests.

- [ ] **Step 6: Commit the lifecycle port**

```bash
rtk git add core/src/dutchmate_core/workflows/capture.py core/src/dutchmate_core/runtime.py tests/unit/workflows/capture_test_support.py tests/unit/workflows/test_capture_workflows.py tests/unit/runtime/test_device_core_lifecycle.py
rtk git commit -m "Add finite workflow cursor lifecycle"
```

---

### Task 2: Implement Idle Drain And Active Lossless FIFO

**Files:**
- Create: `apps/service/src/dutchmate_service/continuous_ingestion.py`
- Create: `apps/service/tests/test_continuous_ingestion.py`

**Interfaces:**
- Consumes: `CaptureEventSource`, `CaptureWorkflowLifecycle`, `BackendEvent`, and `SegmentContext` from core.
- Produces: `DEFAULT_INGESTION_QUEUE_CAPACITY = 256` and `ContinuousIngestionCoordinator(source, *, queue_capacity=256, event_wait_timeout_s=0.1)`.
- Produces methods/properties: `segment`, `begin_workflow()`, `end_workflow()`, `read_event()`, `discard_pending_events()`, and `close()`.
- Defers to Task 3: terminal replacement methods are added after the FIFO behavior is proven.

- [ ] **Step 1: Create deterministic source and event helpers**

In `test_continuous_ingestion.py`, import `deque` from `collections` and
`Condition`/`Event` from `threading`, then create a condition-backed source whose
`read_event()` blocks until a test publishes an outcome or calls `close()`:

```python
class ControlledSource:
    def __init__(self, *, segment_id: int = 0) -> None:
        self.segment = segment(segment_id)
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException | None] = deque()
        self.read_count = 0
        self.close_count = 0
        self.read_started = Event()
        self.closed = False

    def publish(self, outcome: BackendEvent | BaseException | None) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            self.read_count += 1
            self.read_started.set()
            self._condition.notify_all()
            while not self._outcomes and not self.closed:
                self._condition.wait()
            if self.closed:
                raise BackendDisconnectedError("source closed")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def wait_for_reads(self, expected: int) -> bool:
        with self._condition:
            return self._condition.wait_for(
                lambda: self.read_count >= expected,
                timeout=1,
            )

    def close(self) -> None:
        with self._condition:
            self.close_count += 1
            self.closed = True
            self._condition.notify_all()
```

Define real-value helpers in the same test module:

```python
def segment(segment_id: int) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="host",
            clock="monotonic",
            unit="us",
            origin="segment_start",
            source_origin_us=0,
            observation_point="host_serial_read",
            event_granularity="serial_read_chunk",
        ),
    )


def uart_event(data: bytes, *, segment_id: int = 0) -> UartReceiveEvent:
    return UartReceiveEvent(
        segment_id=segment_id,
        timestamp_us=0,
        channel=0,
        data=data,
    )
```

- [ ] **Step 2: Write failing idle/fresh-cursor/FIFO tests**

Add these exact behaviors:

```python
def test_idle_source_is_drained_without_replay() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        assert source.read_started.wait(timeout=1)
        source.publish(uart_event(b"idle\n"))
        assert source.wait_for_reads(2)
        coordinator.begin_workflow()
        source.publish(uart_event(b"active\n"))
        assert coordinator.read_event() == uart_event(b"active\n")
        coordinator.end_workflow()
    finally:
        coordinator.close()


def test_active_fifo_preserves_exact_order() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        coordinator.begin_workflow()
        expected = [uart_event(b"A"), uart_event(b"B"), uart_event(b"C")]
        for event in expected:
            source.publish(event)
        assert [coordinator.read_event() for _ in expected] == expected
        coordinator.end_workflow()
    finally:
        coordinator.close()
```

Add `test_active_workflow_continues_after_source_timeout`: activate, publish
`None`, wait until the source begins its next read, publish one UART event, and
assert `read_event()` returns that event rather than terminalizing. Parameterize
the idle-drain test over `UartReceiveEvent` and `BufferStatusEvent` so neither
idle UART nor idle telemetry is replayed.

Also assert a second `begin_workflow()` is rejected, `read_event()` outside an
active workflow is rejected, `end_workflow()` clears unread events, and a new
workflow cannot observe them.

- [ ] **Step 3: Run the coordinator tests and capture RED**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k "idle or fifo or workflow" -v
```

Expected: collection fails because `continuous_ingestion.py` and
`ContinuousIngestionCoordinator` do not exist.

- [ ] **Step 4: Implement construction, idle drain, workflow admission, and FIFO reads**

Use one `Condition`, a `deque[BackendEvent]`, and one non-daemon ingestion
thread. Validate `queue_capacity` as a positive non-boolean integer and
`event_wait_timeout_s` as a positive finite number. The public shape is:

```python
DEFAULT_INGESTION_QUEUE_CAPACITY: Final = 256
DEFAULT_INGESTION_EVENT_WAIT_TIMEOUT_S: Final = 0.1


class ContinuousIngestionCoordinator:
    def __init__(
        self,
        source: CaptureEventSource,
        *,
        queue_capacity: int = DEFAULT_INGESTION_QUEUE_CAPACITY,
        event_wait_timeout_s: float = DEFAULT_INGESTION_EVENT_WAIT_TIMEOUT_S,
    ) -> None:
        self._condition = Condition(RLock())
        self._source: CaptureEventSource | None = source
        self._segment = _source_segment(source)
        self._events: deque[BackendEvent] = deque()
        self._queue_capacity = queue_capacity
        self._event_wait_timeout_s = event_wait_timeout_s
        self._workflow_active = False
        self._generation = 0
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._close_error: BaseException | None = None
        self._thread = Thread(
            target=self._ingest,
            name="dutchmate-continuous-ingestion",
        )
        self._thread.start()
```

The ingestion loop reads the captured source outside the condition lock. After
each ordinary event, reacquire the condition: discard it when idle; when active,
wait while `len(self._events) >= self._queue_capacity`; append and notify after
capacity exists. Re-check source identity, workflow activity, and closing state
after every wake so stale-source or ended-workflow events are not admitted.

Implement active reads with bounded inactivity polling:

```python
def read_event(self) -> BackendEvent | None:
    with self._condition:
        if not self._workflow_active:
            raise RuntimeError("continuous ingestion workflow is not active")
        if not self._events:
            self._condition.wait(timeout=self._event_wait_timeout_s)
        if self._events:
            event = self._events.popleft()
            self._condition.notify_all()
            return event
        return None
```

`begin_workflow()` increments the generation and starts with an empty deque;
`end_workflow()` clears the deque, marks idle, and notifies a producer blocked
on capacity. `discard_pending_events()` is an intentional no-op because
activation is the authoritative fresh-cursor boundary.

After every `read_event()` return, refresh `_segment` from that same captured
source before publishing the outcome; this preserves Enhanced provenance that
becomes available during ingestion. Implement the initial single-caller
`close()` by marking closing, notifying the condition, closing the source, and
joining the ingestion thread outside the condition. Task 3 adds concurrent
closer/error retention. If `Thread.start()` fails in the constructor, close the
source under `suppress(BaseException)` and re-raise the original start failure;
cover this with `test_constructor_closes_source_when_thread_start_fails`.

- [ ] **Step 5: Prove capacity-one backpressure without sleeps**

Add a test with `queue_capacity=1`. Publish `A`, `B`, and `C`; use source read
count barriers to prove the ingestion thread stops consuming further source
outcomes while the active queue has no capacity. Consume `A`, then `B`, then
`C`, asserting exact order and that every producer/consumer thread joins within
one second. Add a second test ending the workflow while the producer is blocked;
assert the producer returns to idle draining and the next workflow starts empty.

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k "backpressure or blocked or order" -v
```

Expected: PASS with no live `dutchmate-continuous-ingestion` thread after each
test cleanup.

- [ ] **Step 6: Run all coordinator tests and commit the FIFO slice**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -v
```

Expected: PASS.

```bash
rtk git add apps/service/src/dutchmate_service/continuous_ingestion.py apps/service/tests/test_continuous_ingestion.py
rtk git commit -m "Add continuous ingestion coordinator"
```

---

### Task 3: Add Terminal Ordering, Source Replacement, And Deterministic Close

**Files:**
- Modify: `apps/service/src/dutchmate_service/continuous_ingestion.py`
- Modify: `apps/service/tests/test_continuous_ingestion.py`

**Interfaces:**
- Extends `ContinuousIngestionCoordinator` with `close_current_source_for_reconnect() -> None` and `replace_source(replacement: CaptureEventSource) -> None`.
- Preserves: exact terminal object identity, valid FIFO prefix ordering, source ownership transfer, and idempotent `close()`.
- Rejects: replacement after closing/closed, replacement before terminal detachment, and reconnect after a non-disconnect terminal.

- [ ] **Step 1: Write failing terminal-order tests**

Add parameterized tests for `BackendDisconnectedError` and `BackendInputError`:

```python
@pytest.mark.parametrize(
    "terminal",
    [BackendDisconnectedError("removed"), BackendInputError("malformed")],
)
def test_active_workflow_drains_valid_prefix_before_same_terminal(
    terminal: BaseException,
) -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        coordinator.begin_workflow()
        first = uart_event(b"first")
        second = uart_event(b"second")
        source.publish(first)
        source.publish(second)
        source.publish(terminal)
        assert coordinator.read_event() is first
        assert coordinator.read_event() is second
        with pytest.raises(type(terminal)) as raised:
            coordinator.read_event()
        assert raised.value is terminal
    finally:
        coordinator.close()
```

Add an idle-terminal test: publish a disconnect before activation, wait for the
source to stop being read, activate, and assert the exact terminal object is
raised without blocking. Add an unexpected `RuntimeError` test and assert it is
retained but `replace_source()` is rejected.

- [ ] **Step 2: Run terminal tests and capture RED**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k "terminal or disconnect or input_error or unexpected" -v
```

Expected: FAIL because the Task 2 loop does not retain and replay terminal
outcomes.

- [ ] **Step 3: Implement terminal state and exact-prefix delivery**

Store `_terminal_error: BaseException | None`,
`_replacement_allowed: bool`, and `_ingestion_stopped: bool`. The ingestion
loop handles outcomes as follows:

```python
except (BackendDisconnectedError, BackendInputError) as exc:
    with self._condition:
        if source is self._source:
            self._terminal_error = exc
            self._replacement_allowed = isinstance(exc, BackendDisconnectedError)
            self._condition.notify_all()
            while (
                source is self._source
                and not self._closing
                and not self._ingestion_stopped
            ):
                self._condition.wait()
except Exception as exc:
    self._terminalize_unexpected(source, exc)
```

`read_event()` first returns queued events, then raises `_terminal_error` by
identity. Never wrap `BackendDisconnectedError` or `BackendInputError`.
`_terminalize_unexpected()` atomically detaches the source, records the primary
exception, closes the source outside the condition, marks ingestion stopped,
and lets the existing workflow failure projection classify it as
`internal_error`.

- [ ] **Step 4: Write failing replacement ownership tests**

Add tests proving:

- `close_current_source_for_reconnect()` closes the failed source before a
  replacement can be accepted;
- `replace_source()` updates `segment`, clears only a consumed disconnect
  terminal, resumes the same ingestion thread, and delivers replacement events
  to the still-active workflow;
- replacement is rejected after `BackendInputError` or unexpected failure;
- replacement racing with close is closed exactly once and never published;
- a close failure while terminalizing the old source prevents replacement and
  is returned by later coordinator close calls.

Use this stable-facade assertion:

```python
coordinator.begin_workflow()
source.publish(BackendDisconnectedError("removed"))
with pytest.raises(BackendDisconnectedError):
    coordinator.read_event()
coordinator.close_current_source_for_reconnect()
replacement = ControlledSource(segment_id=1)
coordinator.replace_source(replacement)
replacement.publish(uart_event(b"resumed", segment_id=1))
assert coordinator.read_event() == uart_event(b"resumed", segment_id=1)
assert coordinator.segment == replacement.segment
```

- [ ] **Step 5: Implement reconnect-owned detachment and transfer**

`close_current_source_for_reconnect()` must:

1. require a retained `BackendDisconnectedError` and no earlier reconnect-close
   failure;
2. detach the current concrete source under the condition and notify the
   ingestion thread;
3. close that source outside the condition;
4. retain and raise the exact cleanup exception if close fails; and
5. leave the coordinator ready for one replacement only after successful close.

`replace_source(replacement)` must validate that no concrete source is installed
and the prior disconnect was detached successfully. Under the condition it
publishes the replacement and segment snapshot, clears the disconnect terminal,
and notifies the existing ingestion thread. If closing, closed, or not
replaceable, close `replacement` outside the condition and raise
`RuntimeError("continuous ingestion coordinator cannot accept replacement")`.

- [ ] **Step 6: Write failing close-concurrency tests**

Add tests for close while idle, active, blocked on source read, blocked on FIFO
capacity, and waiting for replacement. Add two concurrent closers around a
source whose close waits on an event and raises one `RuntimeError`; assert:

```python
assert source.close_count == 1
assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.
assert errors == [close_error, close_error]
with pytest.raises(RuntimeError) as repeated:
    coordinator.close()
assert repeated.value is close_error
```

Do not expose a production testing method solely for this assertion. Either
keep a private `_thread` assertion under `# noqa: SLF001` in the test or enumerate
live threads by the exact coordinator thread name.

- [ ] **Step 7: Implement exact-once close and shared completion**

Follow the existing `EnhancedAsyncHost.close()` first-closer pattern:

- mark closing and capture the installed source under the condition;
- notify blocked queue readers/producers and replacement waiters;
- close the concrete source and join the ingestion thread outside the condition;
- retain the first cleanup error without replacing an earlier primary error;
- publish `_closed` and `_close_complete` in `finally`; and
- make concurrent/later closers wait and raise the same retained object.

Closing rejects `begin_workflow()` and replacement, but `end_workflow()` remains
safe and idempotent so workflow `finally` cleanup cannot mask a concurrent
runtime close. Wake an active `read_event()` with a coordinator-owned
`BackendDisconnectedError("continuous ingestion coordinator is closed")` only
when no earlier terminal outcome exists.

Do not perform `source.read_event()`, `source.close()`, `Condition.wait()`, or
`Thread.join()` while holding the coordinator state lock.

- [ ] **Step 8: Run coordinator tests and commit terminal/lifecycle behavior**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -v
```

Expected: PASS with exact terminal identities and no coordinator threads alive.

```bash
rtk git add apps/service/src/dutchmate_service/continuous_ingestion.py apps/service/tests/test_continuous_ingestion.py
rtk git commit -m "Complete ingestion source lifecycle"
```

---

### Task 4: Reconnect And Compose Through The Stable Coordinator

**Files:**
- Modify: `apps/service/src/dutchmate_service/backend_reconnect.py`
- Modify: `apps/service/tests/test_backend_reconnect.py`
- Modify: `apps/service/src/dutchmate_service/startup.py`
- Modify: `apps/service/tests/test_startup_config.py`
- Modify: `apps/service/tests/test_app_lifecycle.py`
- Modify: `core/src/dutchmate_core/runtime.py`
- Modify: `tests/unit/runtime/test_device_core_lifecycle.py`

**Interfaces:**
- Consumes: `ContinuousIngestionCoordinator.close_current_source_for_reconnect()` and `replace_source(replacement)` from Task 3.
- Changes: `RetryingCaptureReconnect` accepts `source_owner` instead of `current_source` and never stores a concrete replacement source.
- Produces: successful reconnect returns `ReconnectedCaptureSource(source=source_owner, backend_snapshot=validated_snapshot)`.
- Produces: one coordinator per connected runtime, used as both `message_source` and reconnect `source_owner`.
- Preserves: synchronous openers, 0.1-second retry interval, supplied monotonic deadline, backend-specific validation, and replaceable control/UART sender publication.

- [ ] **Step 1: Rewrite reconnect unit expectations to require stable ownership**

Replace the simple current-source fake with a `FakeSourceOwner` implementing the
coordinator ownership surface:

```python
class FakeSourceOwner:
    def __init__(self) -> None:
        self.closed_current = 0
        self.replacements: list[CaptureEventSource] = []
        self.close_count = 0

    def read_event(self) -> BackendEvent | None:
        return None

    def close_current_source_for_reconnect(self) -> None:
        self.closed_current += 1

    def replace_source(self, replacement: CaptureEventSource) -> None:
        self.replacements.append(replacement)

    def close(self) -> None:
        self.close_count += 1
```

Update the retry-success test to assert:

```python
result = reconnect(segment_id=1, deadline=1.0)
assert result == ReconnectedCaptureSource(
    source=owner,
    backend_snapshot=replacement.backend_snapshot,
)
assert owner.closed_current == 1
assert owner.replacements == [replacement_source]
assert published == [replacement]
```

Retain and adapt tests for fatal `BackendInputError`, source opened at deadline,
and close-before-open ordering. Add a publication-failure test proving the
accepted concrete source is re-terminalized through the owner and not leaked.

- [ ] **Step 2: Run reconnect tests and capture RED**

Run:

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py -v
```

Expected: FAIL because `RetryingCaptureReconnect` still accepts and stores
`current_source` and returns the concrete replacement.

- [ ] **Step 3: Refactor retrying reconnect to transfer ownership once**

Define a service-local protocol:

```python
class ReplaceableCaptureSource(CaptureEventSource, Protocol):
    def close_current_source_for_reconnect(self) -> None:
        pass

    def replace_source(self, replacement: CaptureEventSource) -> None:
        pass

    def close(self) -> None:
        pass
```

Change the constructor to:

```python
def __init__(
    self,
    *,
    source_owner: ReplaceableCaptureSource,
    open_replacement: OpenCaptureReplacement,
    on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    retry_interval_s: float = 0.1,
) -> None:
```

Call `source_owner.close_current_source_for_reconnect()` exactly once before the
first open attempt. For a successful concrete replacement, enforce the deadline,
transfer it with `source_owner.replace_source(replacement.source)`, publish the
control/sender adapters, and return a new `ReconnectedCaptureSource` whose
`source` is the stable owner. If publication fails after transfer, close the
source owner under `suppress(BaseException)` and propagate the primary
publication error.

Do not add `_current_source`; the coordinator is the only concrete-source owner.

- [ ] **Step 4: Keep backend-specific validation before ownership transfer**

For Basic, capture the initial `BackendSnapshot` during startup and pass it to
`build_basic_capture_reconnect` through its `expected_snapshot` keyword. Before returning an
opened Basic replacement, compare mode, port, device, firmware, and capability
policy with the expected snapshot; close the new source and raise
`BackendInputError("Reconnected Basic backend identity changed", backend_mode="basic")`
on mismatch.

For Enhanced, retain `read_enhanced_hello()`,
`_require_matching_enhanced_identity()`, timestamp-provenance priming, and
policy construction before `open_replacement()` returns. The coordinator must
not receive a source until these checks pass.

- [ ] **Step 5: Write failing runtime reconnect/close ownership tests**

Extend `test_device_core_lifecycle.py` for these cases:

- reconnect returns the same original facade with a new segment and runtime
  keeps that facade as `_message_source`;
- reconnect returns `None`, runtime retains the original facade so later close
  can stop its coordinator thread;
- runtime close begins while reopen is blocked, waits, rejects the returned
  facade, and closes it once;
- cleanup errors from a rejected replacement are shared with the close caller;
- a reconnect attempted after close never calls the opener.

Use an explicit `_reconnect_source` ownership slot in expectations; never infer
ownership from timing.

- [ ] **Step 6: Implement runtime's in-flight reconnect ownership slot**

Add `self._reconnect_source: CaptureEventSource | None = None`. At reconnect
start, move `_message_source` into `_reconnect_source`. When reconnect succeeds,
clear `_reconnect_source` and publish `replacement.source`. If reconnect returns
`None` or raises while runtime remains open, restore the original facade. If
runtime is closing, leave the source in the ownership slot for the waiting close
path.

When a replacement arrives during closing, clear the old ownership slot because
the reconnect callable has completed its old-source responsibility, close the
returned replacement facade, and return `None`. In `close()`, after waiting for
`_reconnect_complete`, atomically take either `_message_source` or
`_reconnect_source`, clear both slots, and close the selected owner outside
`_operation_lock`.

- [ ] **Step 7: Run the isolated reconnect and runtime lifecycle tests**

Run:

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py tests/unit/runtime/test_device_core_lifecycle.py tests/unit/workflows/test_capture_reconnect.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py -v
```

Expected: PASS with stable coordinator identity, no double-owned concrete
source, preserved session segment behavior, and deterministic close races.

Continue directly into startup composition before committing so the changed
reconnect-builder signatures and all production call sites remain one
independently testable change.

#### Startup Composition

**Files:**
- Modify: `apps/service/src/dutchmate_service/startup.py`
- Modify: `apps/service/tests/test_startup_config.py`
- Modify: `apps/service/tests/test_app_lifecycle.py`

**Additional Interfaces:**
- Consumes: `ContinuousIngestionCoordinator` and the Task 4 reconnect builders.
- Produces: one coordinator per connected `DeviceCoreRuntime`, used as both `message_source` and reconnect `source_owner`.
- Preserves: initial Basic/Enhanced opener selection, one serial resource, stable `ReplaceableDeviceControl`/`ReplaceableUartSender`, public status/session results, and FastAPI ownership rules.

- [ ] **Step 8: Add failing Basic startup ownership tests**

Update `test_build_startup_runtime_opens_basic_without_hello` to spy on
`startup.ContinuousIngestionCoordinator`. Assert it receives exactly one
`BasicBackendEventSource`, runtime receives the coordinator rather than the
concrete source, and the Basic serial port still has one reader owner.

Add a real-coordinator integration test using a condition-backed Basic-shaped
source: establish an idle UART event and prove it is drained; run
`CaptureWorkflow` against the coordinator, publish a later event only after the
workflow-start callback, and assert only the later event is persisted.

- [ ] **Step 9: Add failing Enhanced startup and cleanup tests**

Update the Enhanced startup tests to assert:

```python
assert coordinator_factory_calls == [initial_host]
assert runtime._message_source is coordinator  # noqa: SLF001
assert initial_host.close_count == 0
runtime.close()
assert initial_host.close_count == 1
```

Replace preloaded-event assumptions in finite capture tests: continuous idle
ingestion intentionally consumes preloaded UART before a workflow. Publish
workflow evidence through a barrier after `begin_workflow()` instead.

For connection-recording and runtime-construction failures, assert cleanup
closes the coordinator, which joins ingestion and closes the host; a coordinator
cleanup failure must not mask the primary startup exception.

- [ ] **Step 10: Run startup tests and capture RED**

Run:

```bash
rtk pytest apps/service/tests/test_startup_config.py -k "startup or reconnect or coordinator or capture" -v
```

Expected: FAIL because startup passes concrete sources directly to runtime and
reconnect.

- [ ] **Step 11: Wire the Basic startup path**

In `build_startup_runtime()`:

```python
connection = open_basic_backend_connection(backend_settings)
basic_source = BasicBackendEventSource(connection, segment_id=0)
initial_snapshot = basic_source.snapshot
coordinator = ContinuousIngestionCoordinator(basic_source)
sender = ReplaceableUartSender(connection)
control = ReplaceableDeviceControl(_UnavailableDeviceControl(connection))
reconnect = build_basic_capture_reconnect(
    settings=backend_settings,
    source_owner=coordinator,
    expected_snapshot=initial_snapshot,
    open_connection=open_basic_backend_connection,
    sender=sender,
    monotonic_clock=reconnect_clock,
    sleep=reconnect_sleep,
)
```

Pass `coordinator` as `message_source`. Wrap every operation after coordinator
construction in `try/except BaseException`; close the coordinator under
`suppress(BaseException)` before re-raising the primary error.

- [ ] **Step 12: Wire the Enhanced startup path**

Construct `EnhancedAsyncHost`, then immediately transfer it into one
`ContinuousIngestionCoordinator`. Use the coordinator as runtime message source
and reconnect source owner while retaining the host as the initial control and
UART sender:

```python
enhanced_host = open_enhanced_async_host(
    port=serial_port,
    baudrate=backend_settings.baudrate,
    segment_id=0,
)
coordinator = ContinuousIngestionCoordinator(enhanced_host)
control = ReplaceableDeviceControl(enhanced_host)
sender = ReplaceableUartSender(enhanced_host)
reconnect = build_enhanced_capture_reconnect(
    settings=backend_settings,
    source_owner=coordinator,
    expected_info=enhanced_host.info,
    control=control,
    sender=sender,
    open_transport=open_serial_command_transport,
    monotonic_clock=reconnect_clock,
    sleep=reconnect_sleep,
)
```

After transfer, cleanup always calls `coordinator.close()`, never
`enhanced_host.close()` directly. Initial Enhanced startup still opens no
synchronous `SerialCommandTransport`.

- [ ] **Step 13: Prove app-owned shutdown reaches the coordinator**

Add an application lifespan test with a real `DeviceCoreRuntime`, a real
coordinator, and a blocking fake source. Exit `TestClient` and assert the source
was closed once and no `dutchmate-continuous-ingestion` thread remains. Retain
the existing rule that an injected runtime remains caller-owned.

- [ ] **Step 14: Run the service/core integration gate**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py apps/service/tests/test_backend_reconnect.py apps/service/tests/test_startup_config.py apps/service/tests/test_app_lifecycle.py tests/unit/workflows/test_capture_workflows.py tests/unit/workflows/test_capture_reconnect.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: PASS. Verify no thread/task/resource-leak warning is emitted.

- [ ] **Step 15: Commit reconnect and startup integration**

```bash
rtk git add apps/service/src/dutchmate_service/backend_reconnect.py apps/service/tests/test_backend_reconnect.py apps/service/src/dutchmate_service/startup.py apps/service/tests/test_startup_config.py apps/service/tests/test_app_lifecycle.py core/src/dutchmate_core/runtime.py tests/unit/runtime/test_device_core_lifecycle.py
rtk git commit -m "Integrate continuous ingestion ownership"
```

---

### Task 5: Validate Architecture And Advance The Phase 1 Status

**Files:**
- Modify: `docs/development_status.md`
- Modify if generated: `graphify-out/graph.json`
- Modify if generated: `graphify-out/graph.html`
- Modify if generated: `graphify-out/GRAPH_REPORT.md`
- Modify if generated: `graphify-out/manifest.json`
- Modify if generated: `graphify-out/.graphify_labels.json`
- Modify if generated: `graphify-out/.graphify_labels.json.sig`
- Modify if generated: `graphify-out/.vocab.txt`
- Modify if generated: `graphify-out/cost.json`

**Interfaces:**
- Consumes: all implementation commits from Tasks 1-4.
- Produces: fresh validation evidence, canonical Graphify topology, and one authoritative next step in `docs/development_status.md`.
- Preserves: ignored Graphify caches, dated snapshots, query memory, reflections, query stamps, and temporary extraction artifacts as local-only runtime state.

- [ ] **Step 1: Run focused behavioral tests**

Run:

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py apps/service/tests/test_backend_reconnect.py apps/service/tests/test_startup_config.py apps/service/tests/test_app_lifecycle.py tests/unit/workflows/test_capture_workflows.py tests/unit/workflows/test_capture_reconnect.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: PASS with zero failed tests and no leaked-thread warnings.

- [ ] **Step 2: Run repository-wide static and behavioral validation**

Run each command independently and retain the exact counts/output for the status
record:

```bash
rtk ruff check .
rtk run 'MYPYPATH=core/src .venv/bin/mypy'
rtk pytest
rtk run 'git diff --check'
```

Expected: Ruff passes, mypy reports no issues, pytest reports zero failures,
and `git diff --check` emits no whitespace errors.

- [ ] **Step 3: Verify dependency direction directly**

Run:

```bash
rtk rg -n "dutchmate_service|threading|fastapi|serial" core/src/dutchmate_core/workflows/capture.py core/src/dutchmate_core/runtime.py
rtk rg -n "read_event\(" apps/service/src/dutchmate_service core/src/dutchmate_core
```

Expected: core has no `dutchmate_service`, FastAPI, or serial import; threading
remains absent from workflow policy; production normalized-source consumption is
the service coordinator plus backend-local compatibility implementations, with
no new physical reader.

- [ ] **Step 4: Refresh and verify Graphify canonical artifacts**

Run:

```bash
rtk graphify update .
rtk graphify query "continuous ingestion service backend workflow reconnect source runtime reader adapter" --budget 3500
rtk graphify path "ContinuousIngestionCoordinator" "CaptureWorkflow"
rtk graphify path "ContinuousIngestionCoordinator" "RetryingCaptureReconnect"
```

Verify the paths against actual imports/calls. Stage only these canonical files
when changed: `graph.json`, `graph.html`, `GRAPH_REPORT.md`, `manifest.json`,
`.graphify_labels.json`, `.graphify_labels.json.sig`, `.vocab.txt`, and
`cost.json`. Do not stage `cache/`, dated folders, `memory/`, `reflections/`,
query stamps, `.graphify_python`, or `.graphify_root`.

- [ ] **Step 5: Update the sole development-status record**

In `docs/development_status.md`:

- set the review date to the execution date and code baseline to the Task 4
  implementation commit;
- update the current milestone to say service-owned continuous ingestion is
  complete for both selected backends;
- check only “Add one service-owned continuous ingestion coordinator”; and
- set the next step to “Continuously ingest and monitor connection state outside
  finite workflows for either backend.”

Record the focused test count, full pytest count, Ruff/mypy results,
`git diff --check`, Graphify update result, and any pre-existing Graphify parser
warning. Do not copy a progress checklist into the spec, plan, architecture, or
validation documents.

- [ ] **Step 6: Review the complete diff and commit status/graph evidence**

Run:

```bash
rtk git status --short
rtk git diff --stat
rtk run 'git diff --check'
```

Confirm `AGENTS.md` remains unstaged and absent from the intended commit. Then:

```bash
rtk git add docs/development_status.md graphify-out/graph.json graphify-out/graph.html graphify-out/GRAPH_REPORT.md graphify-out/manifest.json graphify-out/.graphify_labels.json graphify-out/.graphify_labels.json.sig graphify-out/.vocab.txt graphify-out/cost.json
rtk run 'git diff --cached --check'
rtk git commit -m "Complete continuous ingestion slice"
```

If a listed canonical Graphify file is unchanged, omit it from `git add`; do not
force a no-op modification.

- [ ] **Step 7: Verify the committed repository state**

Run:

```bash
rtk git status --short --branch
rtk git show --stat --oneline --summary HEAD
```

Expected: only the user's pre-existing unstaged `AGENTS.md` change remains;
the implementation, tests, status evidence, and changed canonical Graphify
artifacts are committed.
