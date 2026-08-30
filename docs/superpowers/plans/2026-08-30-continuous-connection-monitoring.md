# Continuous Connection Monitoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Continuously project backend connection and Enhanced UART-integrity health through the existing ingestion coordinator so status and connection-required operations cannot rely on stale runtime state.

**Architecture:** Add a small optional pull port beside the core capture-source contract. The service-owned `ContinuousIngestionCoordinator` projects immutable health under its existing condition lock, and `DeviceCoreRuntime` reconciles that snapshot under its operation lock without callbacks, another reader, another monitor thread, or public schema changes.

**Tech Stack:** Python 3.10+, dataclasses, typing protocols, `threading.Condition`, existing DUTchMate backend/workflow contracts, FastAPI TestClient, pytest, Ruff, mypy, Graphify

**Spec:** `docs/superpowers/specs/2026-08-30-continuous-connection-monitoring-design.md`

## Global Constraints

- `docs/development_status.md` remains the sole progress and next-step tracker; this plan's checkboxes express execution order only.
- Preserve one service-owned `ContinuousIngestionCoordinator`, one ingestion thread, one installed normalized source, and one physical reader.
- Keep the monitoring contract backend-neutral in `dutchmate_core`; core must not import `dutchmate_service`, FastAPI, serial libraries, or service threading details.
- Monitoring is optional and structurally discovered; sources implementing only `read_event() -> BackendEvent | None` remain compatible.
- The runtime pulls immutable health snapshots. Do not add callbacks, callback registration, polling threads, background sessions, or another processing pipeline.
- `None` source timeouts and `UartReceiveEvent` do not change health.
- Idle UART is discarded and is never persisted, buffered for later replay, or exposed through status.
- `BufferOverflowEvent.dropped_bytes` is incremental. `BufferStatusEvent.dropped_bytes_total` is cumulative and combines with a known count using `max(previous, reported_total)`.
- Once a connection segment reports loss, a lower or zero cumulative status cannot erase it.
- Active telemetry updates live health and enters the existing active-workflow FIFO exactly once.
- A terminal publishes `connected=False` before the ingestion thread waits for replacement or exits; the exact terminal object remains authoritative for workflow and cleanup behavior.
- A validated replacement publishes `connected=True`, resets monitor integrity to `None`, refreshes segment provenance, and resumes the same ingestion thread.
- Only startup and validated reconnect restore runtime logical connection, identity, and capabilities. A monitor snapshot with `connected=True` never reconnects the runtime.
- Runtime reconciliation preserves an active reconnect deadline and its `connection_state="reconnecting"` precedence.
- Do not add status fields, asynchronous error detail, HTTP/CLI/MCP model changes, session schema changes, protocol schema changes, firmware changes, or automatic reconnect in this slice.
- Use event and condition barriers with bounded waits in concurrency tests; do not use timing sleeps to establish ordering.
- Use RTK-wrapped commands when supported. Correctness and exact diagnostic output take priority when RTK filtering is insufficient.
- Complete structural validation with Ruff, mypy, full pytest, `git diff --check`, a dependency-direction search, and `graphify update .`; stage only canonical Graphify artifacts.

## File Responsibility Map

- `core/src/dutchmate_core/workflows/capture.py`: optional core monitoring port and immutable `CaptureSourceHealth` value.
- `apps/service/src/dutchmate_service/continuous_ingestion.py`: current-source connection/integrity projection under the existing coordinator condition lock.
- `apps/service/tests/test_continuous_ingestion.py`: deterministic coordinator health, telemetry, replacement, FIFO, and close behavior.
- `core/src/dutchmate_core/runtime.py`: pull-based health reconciliation before status snapshots and connection admission.
- `tests/unit/runtime/test_device_core_monitoring.py`: focused runtime monitoring compatibility, state invalidation, integrity, and reconnect-precedence coverage.
- `apps/service/tests/test_connection_monitoring.py`: real coordinator/runtime/FastAPI boundary proof for idle disconnect and Enhanced telemetry.
- `apps/service/tests/test_startup_config.py`: existing Basic and Enhanced construction coverage; validation target only, because startup already injects the coordinator as `message_source`.
- `apps/service/tests/test_app_lifecycle.py`: existing shutdown ownership/thread coverage; validation target only.
- `docs/development_status.md`: completed queue item, current milestone, validation evidence, reviewed code baseline, and sole next step.
- `graphify-out/`: refreshed canonical architecture graph after adding the shared port and new core/service relationship.

---

### Task 1: Publish Current-Source Connection Health

**Files:**
- Modify: `core/src/dutchmate_core/workflows/capture.py:12-56`
- Modify: `apps/service/src/dutchmate_service/continuous_ingestion.py:11-18,23-84,175-200,202-349`
- Modify: `apps/service/tests/test_continuous_ingestion.py:1-19,103-329,553-691`

**Interfaces:**
- Consumes: `CaptureEventSource.read_event() -> BackendEvent | None` and the coordinator's existing condition/source-identity boundary.
- Produces: `CaptureSourceHealth(connected: bool, integrity: UartIntegrity | None)` and runtime-checkable `CaptureSourceMonitor.capture_source_health() -> CaptureSourceHealth`.
- Preserves: exact terminal retention, reconnect eligibility, source ownership, segment refresh, queue semantics, and simple-source compatibility.

- [ ] **Step 1: Add failing connection-health tests**

Extend imports in `apps/service/tests/test_continuous_ingestion.py`:

```python
from collections.abc import Callable

from dutchmate_core.workflows.capture import CaptureSourceHealth
```

Add this deterministic condition helper after `close_coordinator()`:

```python
def wait_for_health(
    coordinator: ContinuousIngestionCoordinator,
    predicate: Callable[[CaptureSourceHealth], bool],
) -> CaptureSourceHealth:
    condition = coordinator._condition  # noqa: SLF001 - deterministic barrier.
    with condition:
        assert condition.wait_for(
            lambda: predicate(coordinator.capture_source_health()),
            timeout=1,
        )
        return coordinator.capture_source_health()
```

Add tests covering inactivity, UART, terminal categories, replacement, and close:

```python
def test_initial_timeout_and_uart_preserve_connected_health() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        expected = CaptureSourceHealth(connected=True, integrity=None)
        assert coordinator.capture_source_health() == expected
        source.publish(None)
        assert source.wait_for_reads(2)
        source.publish(uart_event(b"idle"))
        assert source.wait_for_reads(3)
        assert coordinator.capture_source_health() == expected
    finally:
        close_coordinator(coordinator)


@pytest.mark.parametrize(
    "terminal",
    [
        BackendDisconnectedError("removed"),
        BackendInputError("malformed"),
        RuntimeError("reader failed"),
    ],
    ids=["disconnect", "input", "unexpected"],
)
def test_idle_terminal_publishes_disconnected_health(
    terminal: BaseException,
) -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        source.publish(terminal)
        health = wait_for_health(coordinator, lambda candidate: not candidate.connected)
        assert health.connected is False
    finally:
        close_coordinator(coordinator)


def test_valid_replacement_restores_monitor_health_without_restarting_thread() -> None:
    source = ControlledSource()
    replacement = ControlledSource(segment_id=1)
    coordinator = ContinuousIngestionCoordinator(source)
    ingestion_thread = coordinator._thread  # noqa: SLF001 - lifecycle assertion.
    try:
        coordinator.begin_workflow()
        source.publish(BackendDisconnectedError("removed"))
        with pytest.raises(BackendDisconnectedError):
            coordinator.read_event()
        assert coordinator.capture_source_health().connected is False
        coordinator.close_current_source_for_reconnect()
        coordinator.replace_source(replacement)
        assert coordinator.capture_source_health() == CaptureSourceHealth(True, None)
        assert coordinator._thread is ingestion_thread  # noqa: SLF001
        assert ingestion_thread.is_alive()
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_close_publishes_disconnected_health() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    close_coordinator(coordinator)
    assert coordinator.capture_source_health().connected is False
```

- [ ] **Step 2: Run the focused tests and capture RED**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k "health or replacement" -v
```

Expected: collection or test failure because `CaptureSourceHealth` and `capture_source_health()` do not exist.

- [ ] **Step 3: Define the optional core monitoring port**

Add `UartIntegrity` to the imports from `dutchmate_core.backends.contracts` in
`capture.py`, then add beside `CaptureEventSource`:

```python
@dataclass(frozen=True, slots=True)
class CaptureSourceHealth:
    """Immutable current-source connection and integrity projection."""

    connected: bool
    integrity: UartIntegrity | None


@runtime_checkable
class CaptureSourceMonitor(Protocol):
    """Optional current-source health observation boundary."""

    def capture_source_health(self) -> CaptureSourceHealth:
        """Return one immutable current-source health snapshot."""
```

Do not export these through `dutchmate_core.__init__`; defining modules remain the intentionally small public API for workflow ports.

- [ ] **Step 4: Project coordinator connection transitions**

Import `CaptureSourceHealth` in `continuous_ingestion.py`, initialize
`self._health = CaptureSourceHealth(connected=True, integrity=None)`, and add:

```python
def capture_source_health(self) -> CaptureSourceHealth:
    """Return one immutable health snapshot for the installed source."""

    with self._condition:
        return self._health
```

In both expected-terminal and unexpected-terminal paths, publish disconnected
health while holding `_condition`, after confirming `source is self._source`
and before waiting, detaching, or closing:

```python
self._health = CaptureSourceHealth(
    connected=False,
    integrity=self._health.integrity,
)
```

In `replace_source()`, publish the accepted replacement atomically:

```python
self._source = replacement
self._segment = _source_segment(replacement)
self._health = CaptureSourceHealth(connected=True, integrity=None)
self._terminal_error = None
```

In the first-close branch of `close()`, publish `connected=False` before
notifying the ingestion thread. Preserve monitor integrity there; runtime clears
public integrity whenever `connected` is false.

- [ ] **Step 5: Run coordinator tests**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -v
```

Expected: PASS; terminal identity, replacement, close races, queue ordering, and thread cleanup remain unchanged.

- [ ] **Step 6: Commit connection-health publication**

```bash
git add core/src/dutchmate_core/workflows/capture.py apps/service/src/dutchmate_service/continuous_ingestion.py apps/service/tests/test_continuous_ingestion.py
git commit -m "Add continuous source health monitoring"
```

---

### Task 2: Project Enhanced Integrity Without Double Delivery

**Files:**
- Modify: `apps/service/src/dutchmate_service/continuous_ingestion.py:11-18,264-320,351-359`
- Modify: `apps/service/tests/test_continuous_ingestion.py:10-18,118-329`

**Interfaces:**
- Consumes: `CaptureSourceHealth` from Task 1 and normalized `BufferOverflowEvent`/`BufferStatusEvent` values.
- Produces: `_project_event_health(CaptureSourceHealth, BackendEvent) -> CaptureSourceHealth`.
- Preserves: the exact event object enters the active FIFO once; idle events never enter a later workflow.

- [ ] **Step 1: Add failing telemetry-projection tests**

Import `BufferOverflowEvent` and `UartIntegrity`. Replace the fixed status helper and add an overflow helper:

```python
def buffer_overflow_event(dropped_bytes: int, *, segment_id: int = 0) -> BufferOverflowEvent:
    return BufferOverflowEvent(
        segment_id=segment_id,
        timestamp_us=0,
        channel=0,
        dropped_bytes=dropped_bytes,
    )


def buffer_status_event(
    *,
    dropped_bytes_total: int = 0,
    overflow_events: int = 0,
    segment_id: int = 0,
) -> BufferStatusEvent:
    return BufferStatusEvent(
        segment_id=segment_id,
        timestamp_us=0,
        size_bytes=256,
        used_bytes=8,
        high_water_bytes=16,
        dropped_bytes_total=dropped_bytes_total,
        overflow_events=overflow_events,
    )
```

Add:

```python
def test_idle_zero_status_publishes_none_reported_integrity() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        source.publish(buffer_status_event())
        assert source.wait_for_reads(2)
        assert coordinator.capture_source_health().integrity == UartIntegrity(
            "none_reported", "debug_helper_rx_buffer", 0
        )
    finally:
        close_coordinator(coordinator)


def test_idle_incremental_and_cumulative_telemetry_do_not_double_count() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        source.publish(buffer_overflow_event(5))
        source.publish(buffer_status_event(dropped_bytes_total=5, overflow_events=1))
        source.publish(buffer_status_event(dropped_bytes_total=3))
        source.publish(buffer_status_event(dropped_bytes_total=9, overflow_events=1))
        assert source.wait_for_reads(5)
        assert coordinator.capture_source_health().integrity == UartIntegrity(
            "loss_reported", "debug_helper_rx_buffer", 9
        )
    finally:
        close_coordinator(coordinator)


def test_active_telemetry_updates_health_and_enters_fifo_once() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source, event_wait_timeout_s=0.01)
    event = buffer_overflow_event(7)
    try:
        coordinator.begin_workflow()
        source.publish(event)
        assert coordinator.read_event() is event
        assert coordinator.capture_source_health().integrity == UartIntegrity(
            "loss_reported", "debug_helper_rx_buffer", 7
        )
        assert coordinator.read_event() is None
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_replacement_resets_monitor_integrity() -> None:
    source = ControlledSource()
    replacement = ControlledSource(segment_id=1)
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        source.publish(buffer_overflow_event(4))
        assert source.wait_for_reads(2)
        coordinator.begin_workflow()
        source.publish(BackendDisconnectedError("removed"))
        with pytest.raises(BackendDisconnectedError):
            coordinator.read_event()
        coordinator.close_current_source_for_reconnect()
        coordinator.replace_source(replacement)
        assert coordinator.capture_source_health() == CaptureSourceHealth(True, None)
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


class EventReleasedByCloseSource(ControlledSource):
    def __init__(self, event: BackendEvent) -> None:
        super().__init__()
        self._event = event
        self._release_read = Event()

    def read_event(self) -> BackendEvent:
        self.read_started.set()
        assert self._release_read.wait(timeout=1)
        return self._event

    def close(self) -> None:
        self.close_count += 1
        self.closed = True
        self._release_read.set()


def test_outcome_released_by_close_cannot_update_disconnected_health() -> None:
    source = EventReleasedByCloseSource(
        buffer_status_event(dropped_bytes_total=8, overflow_events=1)
    )
    coordinator = ContinuousIngestionCoordinator(source)
    assert source.read_started.wait(timeout=1)

    close_coordinator(coordinator)

    assert coordinator.capture_source_health() == CaptureSourceHealth(False, None)
```

- [ ] **Step 2: Run telemetry tests and capture RED**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py -k "integrity or telemetry" -v
```

Expected: FAIL because ordinary coordinator events do not update `_health`.

- [ ] **Step 3: Implement pure telemetry projection**

Import `BufferOverflowEvent`, `BufferStatusEvent`, and `UartIntegrity` in
`continuous_ingestion.py`. Add near `_source_segment()`:

```python
def _project_event_health(
    health: CaptureSourceHealth,
    event: BackendEvent,
) -> CaptureSourceHealth:
    integrity = health.integrity
    previous_dropped = (
        integrity.dropped_bytes
        if integrity is not None and integrity.dropped_bytes is not None
        else 0
    )
    if isinstance(event, BufferOverflowEvent):
        return CaptureSourceHealth(
            health.connected,
            UartIntegrity(
                "loss_reported",
                "debug_helper_rx_buffer",
                previous_dropped + event.dropped_bytes,
            ),
        )
    if isinstance(event, BufferStatusEvent):
        reported_loss = event.dropped_bytes_total > 0 or event.overflow_events > 0
        prior_loss = integrity is not None and integrity.loss_status == "loss_reported"
        return CaptureSourceHealth(
            health.connected,
            UartIntegrity(
                "loss_reported" if prior_loss or reported_loss else "none_reported",
                "debug_helper_rx_buffer",
                max(previous_dropped, event.dropped_bytes_total),
            ),
        )
    return health
```

`overflow_events > 0` with a zero byte count stays `loss_reported` with
`dropped_bytes=0`, matching existing session-summary classification.

- [ ] **Step 4: Project before idle discard or active FIFO admission**

In `_ingest()`, update health only while the source is still current and the
coordinator is not closing, before testing `_workflow_active`:

```python
source_segment = _source_segment(source)
with self._condition:
    if source is self._source and not self._closing:
        self._segment = source_segment
        if event is not None:
            self._health = _project_event_health(self._health, event)
    if self._closing:
        return
    if source is not self._source or event is None or not self._workflow_active:
        continue
```

Append the same `event` object through the existing generation/capacity path.

- [ ] **Step 5: Run coordinator and workflow persistence tests**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py tests/unit/workflows/test_capture_workflows.py tests/unit/runtime/test_device_core_capture.py -v
```

Expected: PASS; active telemetry reaches session evidence once, idle UART does not replay, and cumulative reports do not double-count incremental overflow.

- [ ] **Step 6: Commit integrity projection**

```bash
git add apps/service/src/dutchmate_service/continuous_ingestion.py apps/service/tests/test_continuous_ingestion.py
git commit -m "Project continuous UART integrity health"
```

---

### Task 3: Reconcile Runtime State Before Observation And Admission

**Files:**
- Create: `tests/unit/runtime/test_device_core_monitoring.py`
- Modify: `core/src/dutchmate_core/runtime.py:34-52,203-288,434-499,874-881,987-989`

**Interfaces:**
- Consumes: runtime-checkable `CaptureSourceMonitor` and immutable `CaptureSourceHealth` from Task 1.
- Produces: private `DeviceCoreRuntime._reconcile_capture_source_health() -> None`.
- Preserves: `DeviceCoreStatus`, all public API models, reconnect deadline precedence, source ownership, and plain `CaptureEventSource` behavior.

- [ ] **Step 1: Create focused failing runtime tests**

Create `tests/unit/runtime/test_device_core_monitoring.py` with:

```python
from pathlib import Path

import pytest
from runtime_test_support import FakeCaptureSource, FakeMonotonicClock, FakeTransport, enhanced_info

from dutchmate_core.backends import BackendInfo, SegmentContext, SegmentTimestamp, UartIntegrity
from dutchmate_core.backends.enhanced import EnhancedDeviceControl
from dutchmate_core.runtime import DeviceCoreRuntime, DeviceCoreRuntimeError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import CaptureSourceHealth


class MutableHealthSource:
    def __init__(self, health: CaptureSourceHealth) -> None:
        self.health = health
        self.close_count = 0
        self.segment = SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        )

    def read_event(self) -> None:
        return None

    def capture_source_health(self) -> CaptureSourceHealth:
        return self.health

    def close(self) -> None:
        self.close_count += 1


def monitored_runtime(
    tmp_path: Path,
    source: MutableHealthSource,
    *,
    clock: FakeMonotonicClock | None = None,
) -> DeviceCoreRuntime:
    return DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
```

Add state and admission tests:

```python
def test_status_reconciles_idle_terminal_and_clears_connection_state(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    runtime._commanded_boot_mode = "bootloader"  # noqa: SLF001 - invalidation proof.
    source.health = CaptureSourceHealth(False, None)

    status = runtime.status()

    assert status.connected is False
    assert status.connection_state == "disconnected"
    assert status.commanded_boot_mode is None
    assert status.firmware is None
    assert status.device is None
    assert status.backend_capabilities == ()
    assert status.capabilities == ()
    assert status.timestamp_provenance is None
    assert status.integrity is None
    runtime.close()


def test_connection_required_operation_reconciles_before_admission(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    source.health = CaptureSourceHealth(False, None)

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.capture_uart(duration_s=0.1)

    assert runtime.status().active_session_id is None
    runtime.close()
```

Add integrity, compatibility, and reconnect-precedence tests:

```python
def test_connected_enhanced_monitor_updates_live_integrity(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    expected = UartIntegrity("loss_reported", "debug_helper_rx_buffer", 12)
    source.health = CaptureSourceHealth(True, expected)
    assert runtime.status().integrity == expected
    runtime.close()


def test_basic_monitor_without_integrity_stays_not_observable(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )
    assert runtime.status().integrity == UartIntegrity("not_observable", None, None)
    runtime.close()


def test_connected_monitor_cannot_restore_disconnected_runtime(tmp_path: Path) -> None:
    expected = UartIntegrity("loss_reported", "debug_helper_rx_buffer", 3)
    source = MutableHealthSource(CaptureSourceHealth(True, expected))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    runtime.disconnect()
    status = runtime.status()
    assert status.connected is False
    assert status.connection_state == "disconnected"
    assert status.integrity is None
    runtime.close()


def test_plain_capture_source_remains_compatible(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())
    assert runtime.status().connected is True
    runtime.close()


def test_disconnected_monitor_does_not_erase_reconnect_deadline(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source, clock=clock)
    runtime.record_backend_connection(enhanced_info())
    runtime._reconnect_deadline = 10.0  # noqa: SLF001 - precedence assertion.
    source.health = CaptureSourceHealth(False, None)
    status = runtime.status()
    assert status.connected is False
    assert status.connection_state == "reconnecting"
    assert status.reconnect_remaining_s == 10.0
    runtime._reconnect_deadline = None  # noqa: SLF001 - test cleanup.
    runtime.close()
```

- [ ] **Step 2: Run monitoring tests and capture RED**

```bash
rtk pytest tests/unit/runtime/test_device_core_monitoring.py -v
```

Expected: idle terminal and telemetry assertions fail because runtime does not yet read `CaptureSourceMonitor`.

- [ ] **Step 3: Implement pull-based runtime reconciliation**

Import `CaptureSourceMonitor` in `runtime.py`. Add beside
`_mark_backend_disconnected()`:

```python
def _reconcile_capture_source_health(self) -> None:
    source = self._message_source
    if not isinstance(source, CaptureSourceMonitor):
        return
    health = source.capture_source_health()
    if not health.connected:
        self._connected = False
        self._commanded_boot_mode = None
        self._backend_info = None
        self._backend_capabilities = frozenset()
        self._segment_context = None
        self._integrity = None
        return
    if self._connected and health.integrity is not None:
        self._integrity = health.integrity
```

The `_connected` guard prevents a positive monitor observation from restoring
integrity after an explicit logical disconnect. Do not mutate `_port`,
`_backend_mode`, `_capability_policy`, `_message_source`, or `_reconnect_deadline`.

- [ ] **Step 4: Reconcile at both required boundaries**

At the start of the existing `status()` operation-lock body, call:

```python
self._reconcile_capture_source_health()
```

At the start of `_require_connected()`, call the same helper:

```python
def _require_connected(self) -> None:
    self._reconcile_capture_source_health()
    if not self._connected:
        raise DeviceCoreRuntimeError("Debug Helper is not connected")
```

All current callers hold the runtime's reentrant operation lock. The
coordinator never calls runtime code, so runtime-lock then coordinator-lock
acquisition cannot form a cycle.

- [ ] **Step 5: Run focused runtime regression tests**

```bash
rtk pytest tests/unit/runtime/test_device_core_monitoring.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_uart_send.py tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: PASS; existing disconnect callbacks, finite reconnect status, plain sources, UART send, and close ownership remain valid.

- [ ] **Step 6: Commit runtime reconciliation**

```bash
git add core/src/dutchmate_core/runtime.py tests/unit/runtime/test_device_core_monitoring.py
git commit -m "Reconcile continuous source health in runtime"
```

---

### Task 4: Prove Existing Service Status Boundary End To End

**Files:**
- Create: `apps/service/tests/test_connection_monitoring.py`
- Validate only: `apps/service/src/dutchmate_service/startup.py`
- Validate only: `apps/service/src/dutchmate_service/app.py`
- Validate only: `apps/service/tests/test_startup_config.py`
- Validate only: `apps/service/tests/test_app_lifecycle.py`

**Interfaces:**
- Consumes: real `ContinuousIngestionCoordinator`, `DeviceCoreRuntime.status()`, and existing `GET /status` serialization.
- Produces: service evidence that idle Basic disconnect and idle Enhanced telemetry reach unchanged response fields.
- Preserves: caller-owned injected runtime lifecycle and app-owned startup cleanup.

- [ ] **Step 1: Create the real-boundary integration fixture**

Create `apps/service/tests/test_connection_monitoring.py`:

```python
from __future__ import annotations

from collections import deque
from pathlib import Path
from threading import Condition

from fastapi.testclient import TestClient

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BufferStatusEvent,
)
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_service.app import create_app
from dutchmate_service.continuous_ingestion import ContinuousIngestionCoordinator


class QueueSource:
    def __init__(self) -> None:
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException] = deque()
        self.read_count = 0
        self.closed = False

    def publish(self, outcome: BackendEvent | BaseException) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            self.read_count += 1
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
            self.closed = True
            self._condition.notify_all()


class NoopDeviceControl:
    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> None:
        del channel, mode, active_level, idle_level

    def pulse_control(self, *, channel: str, pulse_ms: int) -> None:
        del channel, pulse_ms

    def set_control_state(self, *, channel: str, state: ControlState) -> None:
        del channel, state
```

- [ ] **Step 2: Add idle disconnect and telemetry endpoint tests**

Append:

```python
def test_idle_basic_disconnect_reaches_existing_status_response(tmp_path: Path) -> None:
    source = QueueSource()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="basic",
        port="/dev/ttyUSB0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        condition = coordinator._condition  # noqa: SLF001 - deterministic barrier.
        with condition:
            assert condition.wait_for(
                lambda: not coordinator.capture_source_health().connected,
                timeout=1,
            )
        response = TestClient(create_app(runtime)).get("/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["connected"] is False
        assert payload["connection_state"] == "disconnected"
        assert payload["backend_capabilities"] == []
        assert payload["integrity"] is None
        assert payload["reconnect_remaining_s"] is None
    finally:
        runtime.close()


def test_idle_enhanced_telemetry_reaches_existing_integrity_response(
    tmp_path: Path,
) -> None:
    source = QueueSource()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="enhanced",
        port="/dev/ttyACM0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=10,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=21,
                overflow_events=1,
            )
        )
        assert source.wait_for_reads(2)
        response = TestClient(create_app(runtime)).get("/status")
        assert response.status_code == 200
        assert response.json()["integrity"] == {
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 21,
        }
    finally:
        runtime.close()
```

- [ ] **Step 3: Run service integration tests**

```bash
rtk pytest apps/service/tests/test_connection_monitoring.py apps/service/tests/test_status_endpoint.py apps/service/tests/test_startup_config.py apps/service/tests/test_app_lifecycle.py -v
```

Expected: PASS. Existing startup tests still prove both selected backends wrap
one source in one coordinator, and lifecycle tests still prove shutdown leaves
no coordinator thread.

- [ ] **Step 4: Commit service boundary coverage**

```bash
git add apps/service/tests/test_connection_monitoring.py
git commit -m "Test continuous monitoring through service status"
```

---

### Task 5: Validate Architecture, Refresh Graph, And Advance Phase Status

**Files:**
- Modify: `docs/development_status.md:3-97,187-217`
- Modify canonical outputs only: `graphify-out/graph.json`, `graphify-out/graph.html`, `graphify-out/GRAPH_REPORT.md`, `graphify-out/manifest.json`, `graphify-out/.graphify_labels.json`, `graphify-out/.graphify_labels.json.sig`, `graphify-out/.vocab.txt`, `graphify-out/cost.json`

**Interfaces:**
- Consumes: all implementation and tests from Tasks 1-4.
- Produces: one verified Phase 1 status transition and refreshed architecture navigation artifacts.
- Selects as sole next step: `Coordinate reconnect, hello/identity validation, source replacement, and segment origins without creating a second processing pipeline.`

- [ ] **Step 1: Run the complete focused gate**

```bash
rtk pytest apps/service/tests/test_continuous_ingestion.py apps/service/tests/test_connection_monitoring.py apps/service/tests/test_backend_reconnect.py apps/service/tests/test_startup_config.py apps/service/tests/test_status_endpoint.py apps/service/tests/test_app_lifecycle.py tests/unit/workflows/test_capture_workflows.py tests/unit/workflows/test_capture_reconnect.py tests/unit/runtime/test_device_core_monitoring.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_uart_send.py tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: PASS with no leaked `dutchmate-continuous-ingestion` thread warning.
Record the exact test count and duration for `docs/development_status.md`.

- [ ] **Step 2: Run static and full-suite validation**

```bash
rtk ruff check .
MYPYPATH=core/src rtk mypy
rtk pytest
rtk run 'git diff --check'
```

Expected: Ruff passes, mypy reports no issues, the full suite passes, and the
diff check produces no output. If RTK omits counts needed for status evidence,
rerun that validation command without filtering and record the exact result.

- [ ] **Step 3: Verify dependency direction and single-reader ownership**

```bash
rtk rg -n "dutchmate_service|fastapi|serial_asyncio|pyserial|serial\." core/src/dutchmate_core/workflows/capture.py core/src/dutchmate_core/runtime.py
rtk rg -n "\.read_event\(" core/src apps/service/src
rtk rg -n "Thread\(|create_task\(" apps/service/src/dutchmate_service/continuous_ingestion.py core/src/dutchmate_core/runtime.py
```

Expected: the first search has no matches; `read_event()` ownership remains the
existing coordinator/core protocol and compatibility boundaries; the only
monitoring concurrency remains the coordinator's pre-existing ingestion thread.

- [ ] **Step 4: Refresh and inspect Graphify canonical artifacts**

```bash
rtk run 'graphify update .'
rtk git status --short
```

Expected: Graphify reflects `CaptureSourceHealth`, `CaptureSourceMonitor`, the
coordinator implementation, runtime consumption, and new tests. Investigate any
unexpected tracked file. Do not stage dated snapshots, caches, query memory,
reflections, interpreter/root paths, query stamps, or extraction temporaries.

- [ ] **Step 5: Update the sole development-status source**

Run `git rev-parse HEAD` and use that exact Task 4 commit hash as the reviewed
code baseline in `docs/development_status.md`. Update the review date to
`2026-08-30`, then make these changes:

- Current milestone: continuous connection/integrity monitoring is complete for
  both selected backends through the single coordinator; finite-workflow
  reconnect remains synchronous/transitional.
- Next step: `Coordinate reconnect, hello/identity validation, source replacement, and segment origins without creating a second processing pipeline.`
- Phase 1 assessment and Enhanced host-adapter table row: remove continuous
  monitoring from remaining work; retain reconnect migration, RP2040 firmware,
  prototype/ring-buffer validation, and Enhanced HIL.
- Latest validation: replace prior focused/static/full-suite/Graphify evidence
  with the exact results from Steps 1-4.
- Already complete: add continuous idle connection-state and Enhanced integrity
  projection through the existing status contract.
- Active queue item at current line 208: change `[ ]` to `[x]`; leave all later
  queue items unchecked and ordered.

Do not add progress summaries to the design spec, implementation plan, Phase 1
specification, or validation documents.

- [ ] **Step 6: Verify final scope and stage only intended artifacts**

```bash
rtk git diff
rtk run 'git diff --check'
git add docs/development_status.md graphify-out/graph.json graphify-out/graph.html graphify-out/GRAPH_REPORT.md graphify-out/manifest.json graphify-out/.graphify_labels.json graphify-out/.graphify_labels.json.sig graphify-out/.vocab.txt graphify-out/cost.json
rtk git diff --cached --name-only
rtk run 'git diff --cached --check'
```

Expected staged scope: `docs/development_status.md` plus only changed canonical
Graphify files from the explicit list. The cached diff check produces no output.

- [ ] **Step 7: Commit status and graph reconciliation**

```bash
git commit -m "Complete continuous connection monitoring slice"
```

- [ ] **Step 8: Verify committed completion evidence**

```bash
rtk git status --short --branch
rtk git show --stat --oneline --summary HEAD
rtk run 'git diff HEAD^..HEAD --check'
```

Expected: clean working tree, the final commit contains only status and canonical
Graphify reconciliation, and the committed diff check produces no output.

## Requirement Coverage Check

- Idle terminal visibility: Tasks 1, 3, and 4.
- Admission-time stale-state prevention: Task 3.
- Enhanced idle and active integrity projection: Tasks 2-4.
- Incremental/cumulative no-double-count rule: Task 2.
- Active FIFO exact-once delivery and idle no-replay: Task 2 plus the focused gate.
- Basic `not_observable` and plain-source compatibility: Task 3.
- Reconnect deadline, replacement reset, and same-thread preservation: Tasks 1-3.
- Existing public schemas, source ownership, shutdown, and dependency direction: Tasks 4-5.
- Sole status tracker and exact next Phase 1 queue item: Task 5.
