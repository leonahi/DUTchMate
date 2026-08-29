from pathlib import Path
from threading import Event, Thread

import pytest
from runtime_test_support import FakeCaptureSource, FakeMonotonicClock, FakeTransport, enhanced_info

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.enhanced import EnhancedDeviceControl
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import ReconnectedCaptureSource


def test_runtime_close_closes_current_source_once(tmp_path: Path) -> None:
    """Catch a close that leaves the source owned or repeats source shutdown."""

    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )

    runtime.close()
    runtime.close()

    assert source.close_count == 1


def test_runtime_close_owns_reconnect_replacement_without_reclosing_original(
    tmp_path: Path,
) -> None:
    """Catch shutdown retaining the pre-reconnect source instead of its replacement."""

    clock = FakeMonotonicClock()
    initial = FakeCaptureSource([], clock=clock)
    replacement = FakeCaptureSource([], clock=clock)
    snapshot = _replacement_snapshot(segment_id=1)
    replacement.segment = snapshot.segment

    def reconnect(*, segment_id: int, deadline: float) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline == 10.0
        initial.close()
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=snapshot)

    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=initial,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )

    assert (
        runtime._reconnect_capture_source(  # noqa: SLF001 - exercises replacement ownership.
            expected_snapshot=snapshot,
            segment_id=1,
            deadline=10.0,
        )
        is not None
    )

    runtime.close()

    assert initial.close_count == 1
    assert replacement.close_count == 1


def test_concurrent_runtime_closers_wait_for_and_share_cleanup_error(tmp_path: Path) -> None:
    """Catch later close calls returning before the first cleanup outcome is known."""

    close_error = RuntimeError("source close failed")
    clock = FakeMonotonicClock()
    source = BlockingCloseCaptureSource(clock=clock, close_error=close_error)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )
    completed = [Event(), Event()]
    errors: list[BaseException | None] = [None, None]

    def close_from(index: int) -> None:
        try:
            runtime.close()
        except BaseException as exc:
            errors[index] = exc
        finally:
            completed[index].set()

    first = Thread(target=close_from, args=(0,))
    second = Thread(target=close_from, args=(1,))
    first.start()
    assert source.close_started.wait(timeout=1)
    second.start()
    try:
        assert not completed[1].wait(timeout=0.1)
    finally:
        source.release_close.set()
        first.join(timeout=1)
        second.join(timeout=1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert source.close_count == 1
    assert errors[0] is close_error
    assert errors[1] is close_error
    with pytest.raises(RuntimeError) as repeated:
        runtime.close()
    assert repeated.value is close_error


@pytest.mark.parametrize("replacement_close_fails", [False, True])
def test_runtime_close_during_reconnect_waits_and_rejects_replacement(
    tmp_path: Path,
    replacement_close_fails: bool,
) -> None:
    """Catch close returning while reconnect can still publish a live replacement."""

    clock = FakeMonotonicClock()
    initial = FakeCaptureSource([], clock=clock)
    replacement_close_error = (
        RuntimeError("replacement close failed") if replacement_close_fails else None
    )
    replacement = BlockingCloseCaptureSource(
        clock=clock,
        close_error=replacement_close_error,
    )
    snapshot = _replacement_snapshot(segment_id=1)
    replacement.segment = snapshot.segment
    reopen_started = Event()
    release_reopen = Event()

    def reconnect(*, segment_id: int, deadline: float) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline == 10.0
        initial.close()
        reopen_started.set()
        assert release_reopen.wait(timeout=1)
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=snapshot)

    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=initial,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )
    runtime.record_backend_connection(snapshot.info)
    reconnect_results: list[ReconnectedCaptureSource | None] = []
    reconnect_errors: list[BaseException] = []
    close_errors: list[BaseException] = []
    close_started = Event()
    close_completed = Event()

    def run_reconnect() -> None:
        try:
            reconnect_results.append(
                runtime._reconnect_capture_source(  # noqa: SLF001 - lifecycle race boundary.
                    expected_snapshot=snapshot,
                    segment_id=1,
                    deadline=10.0,
                )
            )
        except BaseException as exc:
            reconnect_errors.append(exc)

    def run_close() -> None:
        close_started.set()
        try:
            runtime.close()
        except BaseException as exc:
            close_errors.append(exc)
        finally:
            close_completed.set()

    reconnect_thread = Thread(target=run_reconnect)
    close_thread = Thread(target=run_close)
    reconnect_thread.start()
    assert reopen_started.wait(timeout=1)
    close_thread.start()
    assert close_started.wait(timeout=1)
    try:
        assert not close_completed.wait(timeout=0.1)
        release_reopen.set()
        assert replacement.close_started.wait(timeout=1)
        assert not close_completed.wait(timeout=0.1)
    finally:
        release_reopen.set()
        replacement.release_close.set()
        reconnect_thread.join(timeout=1)
        close_thread.join(timeout=1)

    assert not reconnect_thread.is_alive()
    assert not close_thread.is_alive()
    if replacement_close_error is None:
        assert reconnect_results == [None]
        assert reconnect_errors == []
        assert close_errors == []
    else:
        assert reconnect_results == []
        assert reconnect_errors == [replacement_close_error]
        assert close_errors == [replacement_close_error]
        with pytest.raises(RuntimeError) as repeated:
            runtime.close()
        assert repeated.value is replacement_close_error
    assert initial.close_count == 1
    assert replacement.close_count == 1
    assert runtime.status().connected is False


def test_reconnect_after_runtime_close_does_not_open_backend(tmp_path: Path) -> None:
    """Catch a terminal runtime reopening and publishing a backend after close."""

    clock = FakeMonotonicClock()
    initial = FakeCaptureSource([], clock=clock)
    snapshot = _replacement_snapshot(segment_id=1)
    reconnect_calls: list[tuple[int, float]] = []

    def reconnect(*, segment_id: int, deadline: float) -> ReconnectedCaptureSource:
        reconnect_calls.append((segment_id, deadline))
        raise AssertionError("closed runtime attempted to reopen a backend")

    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=initial,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )

    runtime.close()
    replacement = runtime._reconnect_capture_source(  # noqa: SLF001 - lifecycle boundary.
        expected_snapshot=snapshot,
        segment_id=1,
        deadline=10.0,
    )

    assert replacement is None
    assert reconnect_calls == []


def test_runtime_close_publishes_disconnected_status(tmp_path: Path) -> None:
    """Catch runtime shutdown leaving service-visible backend metadata connected."""

    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    runtime.close()

    status = runtime.status()
    assert status.connected is False
    assert status.connection_state == "disconnected"
    assert status.firmware is None
    assert status.device is None
    assert status.backend_capabilities == ()
    assert status.capabilities == ()
    assert status.timestamp_provenance is None
    assert status.integrity is None


def test_session_capture_source_delegates_cursor_lifecycle_for_nonzero_segment(
    tmp_path: Path,
) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureSource([None], clock=clock, trace=trace)
    source.segment = _replacement_snapshot(segment_id=3).segment
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    summary = runtime.capture_uart(duration_s=0.1)

    assert trace.count("begin") == 1
    assert trace.count("end") == 1
    assert summary.segment_contexts[0].segment_id == 0


class BlockingCloseCaptureSource(FakeCaptureSource):
    def __init__(
        self,
        *,
        clock: FakeMonotonicClock,
        close_error: BaseException | None = None,
    ) -> None:
        super().__init__([], clock=clock)
        self.close_started = Event()
        self.release_close = Event()
        self._close_error = close_error

    def close(self) -> None:
        self.close_count += 1
        self.close_started.set()
        assert self.release_close.wait(timeout=1)
        if self._close_error is not None:
            raise self._close_error


class LifecycleCaptureSource(FakeCaptureSource):
    def __init__(self, script: list[None], *, clock: FakeMonotonicClock, trace: list[str]) -> None:
        super().__init__(script, clock=clock)
        self._trace = trace

    def begin_workflow(self) -> None:
        self._trace.append("begin")

    def end_workflow(self) -> None:
        self._trace.append("end")


def _replacement_snapshot(segment_id: int) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=enhanced_info(port="/dev/ttyACM0"),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=10_000,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        ),
        integrity=UartIntegrity(
            loss_status="none_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=0,
        ),
    )
