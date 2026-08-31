# Coordinated Background Reconnect Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Automatically reconnect either selected backend while idle, preserve bounded active-workflow reconnect, and use the single-reader asynchronous Enhanced host for every production Enhanced connection.

**Architecture:** Add non-consuming segment readiness to the async Enhanced adapter, extend the pull monitor with versioned validated connection snapshots, and make the service reconnect component serialize idle and active replacement. `ContinuousIngestionCoordinator` remains the only normalized-event consumer; `DeviceCoreRuntime` adopts newer validated generations without learning serial, asyncio, or service-thread details.

**Tech Stack:** Python 3.10+, asyncio, threading, dataclasses, typing protocols, pyserial-asyncio, DUTchMate backend/workflow contracts, pytest, Ruff, mypy, Graphify

**Spec:** `docs/superpowers/specs/2026-08-31-coordinated-background-reconnect-design.md`

## Global Constraints

- `docs/development_status.md` is the sole progress and next-step tracker; plan checkboxes express execution order only.
- Preserve exactly one `ContinuousIngestionCoordinator`, one normalized-event consumer, and one physical serial reader.
- Every production Enhanced open, including reconnect, uses `EnhancedAsyncHost`; production reconnect never opens `SerialCommandTransport`.
- Core does not import `dutchmate_service`, asyncio, threads, serial libraries, FastAPI, Typer, or MCP frameworks.
- Idle retry uses interruptible exponential backoff from exactly `0.1` to exactly `2.0` seconds and adds no public setting.
- Active retry retains its fixed `0.1`-second interval, caller deadline, 32-segment gate, evidence semantics, and deadline precedence.
- Active invalid hello, malformed input, and identity mismatch fail immediately; idle invalid candidates close and retry.
- Active Enhanced replacement requires provenance before publication; idle replacement may publish with `segment=None`.
- Segment readiness never dequeues, duplicates, reorders, or synthesizes the first timestamped event.
- Semantic control and UART sender publish before source installation exposes connected health.
- Runtime restores logical state only from a newer connected health generation carrying a validated `BackendSnapshot`.
- Preserve all public HTTP, CLI, MCP, status, error, protocol, and session schemas.
- Do not delete synchronous compatibility classes in this slice; that is the next Phase 1 item.
- Concurrency tests use events, conditions, and bounded waits, never timing sleeps for ordering.
- Every task uses red-green-refactor TDD and ends with focused tests plus `git diff --check`.
- Final validation requires Ruff, mypy, full pytest, dependency searches, `git diff --check`, and `graphify update .`.

## File Responsibility Map

- `core/src/dutchmate_core/backends/enhanced_serial.py`: reader-owned, non-consuming segment-ready signal.
- `tests/unit/backends/test_enhanced_serial.py`: readiness, FIFO, terminal, timeout, and close tests.
- `apps/service/src/dutchmate_service/enhanced_async.py`: synchronous owner-loop segment-ready bridge.
- `apps/service/tests/test_enhanced_async.py`: bridge and no-consumption tests.
- `core/src/dutchmate_core/workflows/capture.py`: versioned validated source-health value.
- `core/src/dutchmate_core/runtime.py`: newer-generation adoption and optional reconnect lifecycle closure.
- `tests/unit/runtime/test_device_core_monitoring.py`: generation, stale snapshot, policy, and disconnect tests.
- `apps/service/src/dutchmate_service/continuous_ingestion.py`: idle claim and atomic replacement commit point.
- `apps/service/tests/test_continuous_ingestion.py`: claim exclusion, generation, replacement, and close tests.
- `apps/service/src/dutchmate_service/backend_reconnect.py`: idle/active state engine and backend candidate builders.
- `apps/service/tests/test_backend_reconnect.py`: state-engine and candidate tests.
- `apps/service/src/dutchmate_service/startup.py`: initial snapshots, async reconnect selection, and cleanup.
- `apps/service/tests/test_startup_config.py`: Basic/Enhanced composition and single-reader integration.
- `apps/service/tests/test_connection_monitoring.py`: coordinator/runtime/HTTP idle-recovery proof.
- `apps/service/tests/test_app_lifecycle.py`: reconnect-worker and candidate shutdown proof.
- `docs/software_architecture.md`: reconnect ownership and all-async production Enhanced path.
- `docs/development_status.md`: completion evidence and compatibility-removal next step.
- `graphify-out/`: refreshed canonical architecture graph.

---

### Task 1: Add Non-Consuming Enhanced Segment Readiness

**Files:**
- Modify: `core/src/dutchmate_core/backends/enhanced_serial.py:59-124,205-320,365-405`
- Modify: `tests/unit/backends/test_enhanced_serial.py`
- Modify: `apps/service/src/dutchmate_service/enhanced_async.py:27-58,79-177,271-298`
- Modify: `apps/service/tests/test_enhanced_async.py:34-131`

**Interfaces:**
- Consumes: the adapter reader's immutable `segment` assignment and retained terminal state.
- Produces: `AsyncEnhancedSerialAdapter.wait_for_segment(timeout_s: float | None = None) -> SegmentContext | None` and `EnhancedAsyncHost.wait_for_segment(timeout_s: float) -> SegmentContext | None`.
- Preserves: bounded FIFO, `receive_event()`, one reader task, and exact terminal propagation.

- [ ] **Step 1: Write failing adapter readiness tests**

Use existing reader/frame helpers to add:

```python
async def test_wait_for_segment_preserves_origin_event_in_fifo() -> None:
    adapter, reader = make_adapter(segment_id=3)
    await reader.publish(_hello_frame())
    await adapter.start(timeout_s=1.0)
    waiter = asyncio.create_task(adapter.wait_for_segment(timeout_s=1.0))
    await reader.publish(_uart_frame(timestamp_us=4_200, data=b"boot\n"))

    assert await waiter == enhanced_segment_context(3, 4_200)
    assert await adapter.receive_event(timeout_s=0) == UartReceiveEvent(
        segment_id=3,
        timestamp_us=0,
        channel=0,
        data=b"boot\n",
    )
    await adapter.close()


async def test_wait_for_segment_timeout_does_not_consume_later_event() -> None:
    adapter, reader = make_adapter(segment_id=1)
    await reader.publish(_hello_frame())
    await adapter.start(timeout_s=1.0)
    assert await adapter.wait_for_segment(timeout_s=0) is None
    await reader.publish(_uart_frame(timestamp_us=9_000, data=b"later"))
    assert await adapter.wait_for_segment(timeout_s=1.0) == enhanced_segment_context(
        1, 9_000
    )
    assert await adapter.receive_event(timeout_s=0) is not None
    await adapter.close()
```

Also assert retained disconnect/input errors wake and re-raise from the waiter.

- [ ] **Step 2: Run tests and confirm red**

```bash
rtk pytest tests/unit/backends/test_enhanced_serial.py -k wait_for_segment -v
```

Expected: FAIL because `wait_for_segment` does not exist.

- [ ] **Step 3: Implement adapter readiness**

Add `self._segment_ready = asyncio.Event()` beside `_segment`. When a timestamp
first establishes `segment`, set `_segment`, signal `_segment_ready`, then put
the normalized event into `_events`. Add:

```python
async def wait_for_segment(
    self,
    timeout_s: float | None = None,
) -> SegmentContext | None:
    if timeout_s is not None:
        _validate_timeout(timeout_s, field="Enhanced segment timeout", allow_zero=True)
    if self._segment is not None:
        return self._segment
    self._raise_if_terminal()
    segment_task = asyncio.create_task(self._segment_ready.wait())
    terminal_task = asyncio.create_task(self._terminal.wait())
    try:
        done, _ = await asyncio.wait(
            {segment_task, terminal_task},
            timeout=timeout_s,
            return_when=asyncio.FIRST_COMPLETED,
        )
        if not done:
            return None
        if self._segment_ready.is_set():
            assert self._segment is not None
            return self._segment
        self._raise_if_terminal()
        raise AssertionError("terminal event set without terminal error")
    finally:
        for task in (segment_task, terminal_task):
            if not task.done():
                task.cancel()
            with suppress(asyncio.CancelledError):
                await task
```

- [ ] **Step 4: Add and implement the host bridge**

Extend `_AsyncEnhancedAdapter` and the service fake with the async signature.
Test that the host calls it on `owner_thread_id`, never calls `receive_event()`,
and updates `host.segment`. Implement:

```python
def wait_for_segment(self, timeout_s: float) -> SegmentContext | None:
    adapter = self._adapter_for_operation()
    segment = self._submit(lambda: adapter.wait_for_segment(timeout_s))
    with self._state_lock:
        self._segment = segment
    return segment
```

- [ ] **Step 5: Verify and commit Task 1**

```bash
rtk pytest tests/unit/backends/test_enhanced_serial.py apps/service/tests/test_enhanced_async.py -v
git diff --check
git add core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py apps/service/src/dutchmate_service/enhanced_async.py apps/service/tests/test_enhanced_async.py
git commit -m "feat: expose enhanced segment readiness"
```

---

### Task 2: Carry And Adopt Versioned Validated Connection Health

**Files:**
- Modify: `core/src/dutchmate_core/workflows/capture.py:39-63`
- Modify: `core/src/dutchmate_core/runtime.py:218-286,420-462,878-965`
- Modify: `tests/unit/runtime/test_device_core_monitoring.py`

**Interfaces:**
- Consumes: `BackendSnapshot`, `CaptureSourceMonitor`, and runtime capability policy.
- Produces: default-compatible health fields `backend_snapshot` and `connection_generation` plus one-time runtime adoption.
- Preserves: `CaptureSourceHealth(True, None)` and monitor implementations carrying only integrity.

- [ ] **Step 1: Write failing runtime tests**

Add tests proving: generation `1` restores a disconnected runtime from a valid
snapshot; replaying generation `1` after another disconnect cannot restore it;
generation `2` can restore it; and changed capability policy raises
`ValueError("reconnected backend capability policy changed")`.

Core assertion shape:

```python
source.health = CaptureSourceHealth(
    connected=True,
    integrity=replacement.integrity,
    backend_snapshot=replacement,
    connection_generation=1,
)
status = runtime.status()
assert status.connected is True
assert status.backend_capabilities == tuple(sorted(replacement.info.capabilities))
assert status.timestamp_provenance == replacement.segment
```

- [ ] **Step 2: Run tests and confirm red**

```bash
rtk pytest tests/unit/runtime/test_device_core_monitoring.py -k generation -v
```

Expected: FAIL because health lacks the fields and runtime cannot adopt them.

- [ ] **Step 3: Extend the backend-neutral value**

```python
@dataclass(frozen=True, slots=True)
class CaptureSourceHealth:
    connected: bool
    integrity: UartIntegrity | None
    backend_snapshot: BackendSnapshot | None = None
    connection_generation: int = 0

    def __post_init__(self) -> None:
        if self.connection_generation < 0:
            raise ValueError("source connection generation must be non-negative")
```

Disconnected health may retain the last snapshot/generation for stale replay
detection; runtime never adopts it while `connected=False`.

- [ ] **Step 4: Implement runtime adoption**

Initialize `_source_connection_generation: int | None = None`. Add:

```python
def _adopt_backend_snapshot(self, snapshot: BackendSnapshot) -> None:
    if snapshot.capability_policy != self._capability_policy:
        raise ValueError("reconnected backend capability policy changed")
    self._connected = True
    self._commanded_boot_mode = None
    self._backend_mode = snapshot.info.mode
    self._backend_info = snapshot.info
    self._backend_capabilities = snapshot.info.capabilities
    self._segment_context = snapshot.segment
    self._integrity = snapshot.integrity
    self._port = snapshot.info.port
```

In `_reconcile_capture_source_health()`, disconnect first. Otherwise adopt only
when snapshot exists and generation differs from the last adopted generation;
then retain the existing integrity-only update for the same generation.

- [ ] **Step 5: Verify and commit Task 2**

```bash
rtk pytest tests/unit/runtime/test_device_core_monitoring.py tests/unit/runtime/test_device_core_lifecycle.py -v
git diff --check
git add core/src/dutchmate_core/workflows/capture.py core/src/dutchmate_core/runtime.py tests/unit/runtime/test_device_core_monitoring.py
git commit -m "feat: adopt versioned backend health"
```

---

### Task 3: Make Ingestion The Idle-Reconnect Commit Point

**Files:**
- Modify: `apps/service/src/dutchmate_service/continuous_ingestion.py:26-213,285-410`
- Modify: `apps/service/tests/test_continuous_ingestion.py`
- Modify: `apps/service/tests/test_connection_monitoring.py`

**Interfaces:**
- Consumes: Task 2 health fields and existing terminal/source condition state.
- Produces: `wait_for_idle_disconnect(timeout_s)`, idle-aware source detach, and snapshot-bearing replacement.
- Preserves: existing active callers, exact terminal retention, one ingestion thread, and source ownership.

- [ ] **Step 1: Write failing source-transition tests**

Add deterministic tests proving idle disconnect can be claimed without
`read_event()`, active workflow blocks idle claim, active terminal consumption
still permits detach, replacement increments generation, failed publication
closes candidate, fatal `BackendInputError` never becomes idle-reconnectable,
and close wakes idle waiters.

```python
source.publish(BackendDisconnectedError("idle removal"))
assert coordinator.wait_for_idle_disconnect(timeout_s=1.0)
coordinator.close_current_source_for_reconnect(idle=True)
coordinator.replace_source(replacement, backend_snapshot=snapshot)
health = coordinator.capture_source_health()
assert health.backend_snapshot is snapshot
assert health.connection_generation == 1
```

- [ ] **Step 2: Run tests and confirm red**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k 'idle or generation' -v
```

Expected: FAIL because idle observation/claim and generation publication do not
exist.

- [ ] **Step 3: Add the idle observation and claim methods**

Accept `backend_snapshot: BackendSnapshot | None = None` in `__init__`, initialize
generation `0`, and add:

```python
def wait_for_idle_disconnect(self, timeout_s: float) -> bool:
    with self._condition:
        self._condition.wait_for(
            lambda: self._closing
            or self._closed
            or self._ingestion_stopped
            or (
                not self._workflow_active
                and isinstance(self._terminal_error, BackendDisconnectedError)
                and self._replacement_allowed
                and self._source is not None
            ),
            timeout=timeout_s,
        )
        return (
            not self._closing
            and not self._closed
            and not self._ingestion_stopped
            and not self._workflow_active
            and isinstance(self._terminal_error, BackendDisconnectedError)
            and self._replacement_allowed
            and self._source is not None
        )
```

Change `close_current_source_for_reconnect()` to accept `idle: bool = False`.
Idle requires no workflow and marks the retained disconnect consumed inside the
same condition critical section. Active preserves existing consumption rules.

- [ ] **Step 4: Make replacement the connected-health commit**

Extend `replace_source()` with keyword-only `backend_snapshot=None`. Increment
generation and set source, segment, and complete connected health atomically.
Use `dataclasses.replace(health, integrity=updated_integrity)` in telemetry
projection so snapshot/generation survive. Disconnected/close health retains
the previous snapshot and generation while setting `connected=False`.

- [ ] **Step 5: Extend the HTTP proof, verify, and commit**

Drive disconnect plus validated replacement in
`test_connection_monitoring.py`; assert existing `/status` returns restored
identity, capabilities, integrity, and segment without schema additions.

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py apps/service/tests/test_connection_monitoring.py -v
git diff --check
git add apps/service/src/dutchmate_service/continuous_ingestion.py apps/service/tests/test_continuous_ingestion.py apps/service/tests/test_connection_monitoring.py
git commit -m "feat: expose idle reconnect source transition"
```

---

### Task 4: Add The Idle/Active Reconnect State Engine

**Files:**
- Modify: `apps/service/src/dutchmate_service/backend_reconnect.py:1-156`
- Modify: `apps/service/tests/test_backend_reconnect.py:1-280`

**Interfaces:**
- Consumes: Task 3 source-owner methods and `OpenCaptureReplacement(segment_id, deadline, stop_requested)`.
- Produces: `BackendReconnectCoordinator.start()`, callable active reconnect, and `close()`.
- Preserves: stable source facade returned to workflows and fatal active `BackendInputError` behavior.

- [ ] **Step 1: Write failing state-engine tests**

Extend `FakeSourceOwner` with idle/active disconnect barriers and Task 3
signatures. Add tests proving:

- idle worker retries one transient failure and publishes exactly once;
- idle delays are exactly `[0.1, 0.2, 0.4, 0.8, 1.6, 2.0, 2.0]`;
- active reconnect suppresses idle claiming and opening never overlaps;
- active `BackendInputError` re-raises immediately, while idle input retries;
- a source opened at/after active deadline closes and is not published;
- port callback runs before source installation;
- close interrupts retry, prevents publication, joins the worker, and is
  idempotent.

Core test form:

```python
reconnect = BackendReconnectCoordinator(
    source_owner=owner,
    open_replacement=open_replacement,
    wait_for_idle_retry=lambda delay: recorded_delays.append(delay) or False,
)
reconnect.start()
try:
    assert owner.wait_for_replacements(1)
    assert owner.idle_claims == 1
    assert owner.replacements == [replacement]
finally:
    reconnect.close()
```

- [ ] **Step 2: Run tests and confirm red**

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py -k 'idle or active or close' -v
```

Expected: FAIL because `BackendReconnectCoordinator` does not exist.

- [ ] **Step 3: Define exact service-only protocols**

```python
class OpenCaptureReplacement(Protocol):
    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource: ...


class ReplaceableCaptureSource(CaptureEventSource, Protocol):
    def wait_for_idle_disconnect(self, timeout_s: float) -> bool: ...
    def close_current_source_for_reconnect(self, *, idle: bool = False) -> None: ...
    def replace_source(
        self,
        replacement: CaptureEventSource,
        *,
        backend_snapshot: BackendSnapshot | None = None,
    ) -> None: ...
    def close(self) -> None: ...
```

Use this constructor contract:

```python
def __init__(
    self,
    *,
    source_owner: ReplaceableCaptureSource,
    open_replacement: OpenCaptureReplacement,
    on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], None] = time.sleep,
    wait_for_idle_retry: Callable[[float], bool] | None = None,
    active_retry_interval_s: float = 0.1,
    idle_initial_retry_s: float = 0.1,
    idle_max_retry_s: float = 2.0,
) -> None: ...
```

When `wait_for_idle_retry` is omitted, use the coordinator stop event's
`wait(timeout)` method; `True` means shutdown interrupted the wait.

- [ ] **Step 4: Implement coordinator state and active retry**

Replace `RetryingCaptureReconnect` with a coordinator holding one `Condition`,
one stop `Event`, one optional non-daemon worker, and one attempt-active flag.

```python
def start(self) -> None:
    with self._condition:
        if self._closing or self._closed:
            raise RuntimeError("backend reconnect coordinator is closed")
        if self._worker is not None:
            raise RuntimeError("backend reconnect coordinator is already started")
        self._worker = Thread(
            target=self._run_idle,
            name="dutchmate-backend-reconnect",
            daemon=False,
        )
        self._worker.start()


def __call__(
    self,
    *,
    segment_id: int,
    deadline: float,
) -> ReconnectedCaptureSource | None:
    with self._condition:
        if self._closing or self._closed:
            return None
        if self._attempt_active:
            raise RuntimeError("backend reconnect is already active")
        self._attempt_active = True
    try:
        self._source_owner.close_current_source_for_reconnect()
        return self._retry_active(segment_id=segment_id, deadline=deadline)
    finally:
        with self._condition:
            self._attempt_active = False
            self._condition.notify_all()
```

Active retry clips each `0.1`-second wait to remaining deadline, closes late
candidates, retries transient exceptions, and re-raises `BackendInputError`.

- [ ] **Step 5: Implement idle retry, ordered publication, and close**

`_run_idle()` waits through `wait_for_idle_disconnect(0.1)`, reserves the
attempt, claims with `idle=True`, and retries with capped exponential delay.
Idle `BackendInputError` is a rejected candidate, not worker termination.

```python
def _publish(
    self,
    replacement: ReconnectedCaptureSource,
) -> ReconnectedCaptureSource:
    if self._on_connected is not None:
        self._on_connected(replacement)
    self._source_owner.replace_source(
        replacement.source,
        backend_snapshot=replacement.backend_snapshot,
    )
    return ReconnectedCaptureSource(
        source=self._source_owner,
        backend_snapshot=replacement.backend_snapshot,
    )
```

`close()` sets stop, wakes retry waits, blocks new claims/publication, joins the
worker outside the condition, retains first cleanup failure, and returns the
same outcome to concurrent/repeated closers.

- [ ] **Step 6: Verify and commit Task 4**

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py -k 'Coordinator or reconnect' -v
git diff --check
git add apps/service/src/dutchmate_service/backend_reconnect.py apps/service/tests/test_backend_reconnect.py
git commit -m "feat: coordinate idle and active reconnect"
```

---

### Task 5: Build Basic And Async Enhanced Candidates

**Files:**
- Modify: `apps/service/src/dutchmate_service/backend_reconnect.py:158-410`
- Modify: `apps/service/tests/test_backend_reconnect.py:280-end`

**Interfaces:**
- Consumes: Task 1 host readiness, Task 4 state engine, Basic factory, and stable control/sender wrappers.
- Produces: both backend builders returning `BackendReconnectCoordinator`; Enhanced builder accepts `open_host` rather than `open_transport`.
- Preserves: Basic identity, Enhanced mode/port/device/firmware identity, policy-derived capabilities, and source-bound segment IDs.

- [ ] **Step 1: Write failing async candidate tests**

Replace synchronous transport expectations with a fake host implementing event
source, control, sender, and `wait_for_segment()`. Prove:

- active Enhanced open receives requested segment ID and waits for origin;
- origin wait leaves its first queued UART event available;
- idle Enhanced open publishes valid hello/identity with `segment=None` without
  waiting;
- identity mismatch closes host and is fatal only to active use;
- active origin timeout closes host;
- control and sender replace before source installation;
- Basic idle/active candidates retain existing identity and close behavior.

```python
result = reconnect(segment_id=1, deadline=1.0)
assert result is not None
assert opened == [("/dev/ttyACM0", 460800, 1)]
assert host.segment_wait_timeouts
assert host.read_event() == origin_event
```

- [ ] **Step 2: Run tests and confirm red**

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py -k 'enhanced or basic' -v
```

Expected: FAIL because Enhanced builder still opens a synchronous transport.

- [ ] **Step 3: Define the async reconnect host boundary**

```python
class EnhancedReconnectHost(CaptureEventSource, DeviceControl, UartSender, Protocol):
    @property
    def info(self) -> BackendInfo: ...
    @property
    def segment(self) -> SegmentContext | None: ...
    def wait_for_segment(self, timeout_s: float) -> SegmentContext | None: ...
    def close(self) -> None: ...


class OpenEnhancedHost(Protocol):
    def __call__(
        self,
        *,
        port: str,
        baudrate: int,
        segment_id: int,
    ) -> EnhancedReconnectHost: ...
```

- [ ] **Step 4: Implement Enhanced candidate preparation**

Open the host, validate exact identity, and for active use wait in bounded
`0.1`-second slices so shutdown can be observed:

```python
while host.segment is None:
    if stop_requested.is_set():
        raise RuntimeError("backend reconnect coordinator is closing")
    assert deadline is not None
    remaining_s = deadline - monotonic_clock()
    if remaining_s <= 0:
        raise TimeoutError("Enhanced timestamp provenance was not established")
    host.wait_for_segment(min(0.1, remaining_s))
```

For idle use, `deadline is None`, so skip the loop. Build the snapshot with
`segment=host.segment`; map host to both replacement semantic ports; close host
on every pre-publication failure.

- [ ] **Step 5: Adapt Basic and verify both builders**

Basic opener accepts `deadline: float | None` and `stop_requested: Event`,
checks stop, preserves snapshot validation, and returns the Task 4 coordinator.

```bash
rtk pytest apps/service/tests/test_backend_reconnect.py apps/service/tests/test_enhanced_async.py tests/unit/backends/test_enhanced_serial.py -v
git diff --check
git add apps/service/src/dutchmate_service/backend_reconnect.py apps/service/tests/test_backend_reconnect.py
git commit -m "feat: reopen enhanced through async host"
```

---

### Task 6: Select Background Reconnect In Startup And Runtime Lifecycle

**Files:**
- Modify: `apps/service/src/dutchmate_service/startup.py:1-205`
- Modify: `core/src/dutchmate_core/runtime.py:306-375,896-965`
- Modify: `apps/service/tests/test_startup_config.py:400-1150`
- Modify: `apps/service/tests/test_connection_monitoring.py`
- Modify: `apps/service/tests/test_app_lifecycle.py`

**Interfaces:**
- Consumes: Tasks 2-5 health, source transition, coordinator, and async builder.
- Produces: production-started reconnect worker and runtime-owned optional reconnect lifecycle.
- Preserves: disconnected startup, injected runtime ownership, Basic startup, and FastAPI lifespan behavior.

- [ ] **Step 1: Write failing integration tests**

Update reconnect fixtures so initial and replacement Enhanced connections are
fake async hosts. Install a forbidden synchronous opener:

```python
def fail_sync_open(**_kwargs: object) -> NoReturn:
    raise AssertionError("synchronous Enhanced reconnect opener was selected")
```

Prove idle Enhanced and Basic disconnect automatically replace and restore
existing status; active Enhanced capture persists the replacement origin event
and exactly two segment snapshots; idle and active attempts never overlap; and
shutdown during retry/origin wait leaves no worker, host, reader, or loop.

- [ ] **Step 2: Run integration tests and confirm red**

```bash
rtk pytest apps/service/tests/test_startup_config.py apps/service/tests/test_app_lifecycle.py -k 'reconnect or shutdown' -v
```

Expected: FAIL because startup still injects the sync opener and no idle worker
is started or closed.

- [ ] **Step 3: Compose initial validated health**

Pass `basic_source.snapshot` to the Basic coordinator. Promote the service
snapshot helper to `backend_snapshot()` and use:

```python
initial_snapshot = backend_snapshot(
    info=enhanced_host.info,
    segment=enhanced_host.segment,
    tx_enabled=backend_settings.tx_enabled,
)
coordinator = ContinuousIngestionCoordinator(
    enhanced_host,
    backend_snapshot=initial_snapshot,
)
```

- [ ] **Step 4: Select and start reconnect after runtime readiness**

Enhanced passes `open_enhanced_async_host` as `open_host`; remove production
`open_serial_command_transport` injection. For both backends:

```python
runtime = DeviceCoreRuntime(
    device_control=control,
    uart_sender=sender,
    message_source=coordinator,
    session_store=session_store,
    capture_clock=monotonic_clock,
    port=serial_port,
    backend_mode="enhanced",
    tx_policy_enabled=backend_settings.tx_enabled,
    reconnect_timeout_s=backend_settings.reconnect_timeout_s,
    backend_reconnect=reconnect,
)
runtime.record_backend_connection(initial_snapshot.info)
reconnect.start()
return runtime
```

If runtime creation, recording, or start fails, close reconnect first and
ingestion second while retaining the first exception.

- [ ] **Step 5: Close the optional reconnect lifecycle**

The first runtime closer calls `close()` on `_backend_reconnect` when callable,
before waiting for active reconnect/source cleanup:

```python
reconnect_close = getattr(self._backend_reconnect, "close", None)
if callable(reconnect_close):
    reconnect_close()
```

Continue source cleanup after an error and retain the first failure. Function
fakes without `close` remain compatible.

- [ ] **Step 6: Verify and commit Task 6**

```bash
rtk pytest apps/service/tests/test_startup_config.py apps/service/tests/test_connection_monitoring.py apps/service/tests/test_app_lifecycle.py tests/unit/runtime/test_device_core_lifecycle.py tests/unit/workflows/test_capture_reconnect.py -v
git diff --check
git add apps/service/src/dutchmate_service/startup.py core/src/dutchmate_core/runtime.py apps/service/tests/test_startup_config.py apps/service/tests/test_connection_monitoring.py apps/service/tests/test_app_lifecycle.py tests/unit/runtime/test_device_core_lifecycle.py
git commit -m "feat: select coordinated background reconnect"
```

---

### Task 7: Reconcile Architecture, Status, Graph, And Full Validation

**Files:**
- Modify: `docs/software_architecture.md`
- Modify: `docs/development_status.md`
- Modify: canonical `graphify-out/` files changed by `graphify update .`
- Validate: all production and test packages

**Interfaces:**
- Consumes: completed Tasks 1-6 and approved acceptance criteria.
- Produces: accurate architecture, one next step, refreshed graph, and full evidence.
- Preserves: reference documents without competing progress queues.

- [ ] **Step 1: Run acceptance searches**

```bash
rtk proxy rg -n "open_serial_command_transport|SerialCommandTransport|EnhancedCaptureEventSource|EnhancedDeviceControl|EnhancedUartSender" apps/service/src core/src
rtk proxy rg -n "from (apps|dutchmate_service)|import (apps|dutchmate_service)" core/src
rtk proxy rg -n "BackendReconnectCoordinator|wait_for_segment|connection_generation|wait_for_idle_disconnect" core/src apps/service/src
```

Expected: production startup/reconnect has no sync Enhanced opener; remaining
sync types are compatibility definitions for the next item; core has no service
import; new ownership symbols remain in intended layers.

- [ ] **Step 2: Update architecture documentation**

Document: service reconnect coordinator ownership; one async host for Enhanced
startup/replacement; versioned pull adoption; idle backoff `0.1..2.0`; active
deadline precedence; non-consuming origin wait; and runtime-owned reconnect
shutdown. Do not add a progress checklist.

- [ ] **Step 3: Run the complete validation gate**

```bash
rtk ruff check .
rtk mypy
rtk pytest
git diff --check
rtk proxy rg -n "from (apps|dutchmate_service)|import (apps|dutchmate_service)" core/src
```

Expected: all commands exit `0`; pytest has zero failures; dependency search
has no matches.

- [ ] **Step 4: Refresh and audit Graphify**

```bash
rtk proxy graphify update .
rtk git status --short
```

Stage only changed canonical artifacts: `graph.json`, `graph.html`,
`GRAPH_REPORT.md`, `manifest.json`, `.graphify_labels.json`, its `.sig`,
`.vocab.txt`, and `cost.json`. Never stage cache, snapshots, query memory,
reflections, learning state, query stamps, interpreter paths, or temporary
files. Never use `git add graphify-out/`.

- [ ] **Step 5: Update the sole development status**

Set review date `2026-08-31`; mark coordinated reconnect checked; state both
backends now reconnect idle/active and production Enhanced stays async; record
exact validation counts; select only “Remove the obsolete synchronous
compatibility path after all production consumers migrate”; reconcile the code
baseline after the final commit.

- [ ] **Step 6: Verify final diff and commit**

```bash
git diff --check
rtk git diff --stat
rtk git status --short
git add docs/software_architecture.md docs/development_status.md
git add graphify-out/graph.json graphify-out/graph.html graphify-out/GRAPH_REPORT.md graphify-out/manifest.json graphify-out/.graphify_labels.json graphify-out/.graphify_labels.json.sig graphify-out/.vocab.txt graphify-out/cost.json
git commit -m "docs: complete coordinated reconnect migration"
```

Omit unchanged Graphify paths from `git add`. If the final implementation hash
cannot be recorded inside its own commit, use one immediate status-only commit
to reconcile the baseline reference.
