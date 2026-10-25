from pathlib import Path
from threading import Event, Thread

import pytest
from runtime_test_support import (
    FakeCaptureSource,
    FakeDeviceControl,
    FakeMonotonicClock,
    enhanced_info,
)

from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import ReconnectedCaptureSource


def test_runtime_close_closes_current_source_once(tmp_path: Path) -> None:
    """Catch a close that leaves the source owned or repeats source shutdown."""

    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )

    runtime.close()
    runtime.close()

    assert source.close_count == 1


def test_runtime_close_stops_reconnect_before_closing_source(tmp_path: Path) -> None:
    """Catch source cleanup racing a still-running reconnect lifecycle."""

    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = TracingCaptureSource(clock=clock, trace=trace)
    reconnect = ClosableReconnect(trace=trace)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )

    runtime.close()

    assert trace == ["reconnect_close", "source_close"]


def test_runtime_close_retains_reconnect_error_and_continues_source_cleanup(
    tmp_path: Path,
) -> None:
    """Catch reconnect shutdown failure masking or skipping source cleanup."""

    reconnect_error = RuntimeError("reconnect close failed")
    source_error = RuntimeError("source close failed")
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = TracingCaptureSource(
        clock=clock,
        trace=trace,
        close_error=source_error,
    )
    reconnect = ClosableReconnect(trace=trace, close_error=reconnect_error)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )

    with pytest.raises(RuntimeError) as raised:
        runtime.close()

    assert raised.value is reconnect_error
    assert trace == ["reconnect_close", "source_close"]


def test_concurrent_runtime_closers_wait_for_and_share_cleanup_error(tmp_path: Path) -> None:
    """Catch later close calls returning before the first cleanup outcome is known."""

    close_error = RuntimeError("source close failed")
    clock = FakeMonotonicClock()
    source = BlockingCloseCaptureSource(clock=clock, close_error=close_error)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
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


def test_runtime_close_publishes_disconnected_status(tmp_path: Path) -> None:
    """Catch runtime shutdown leaving service-visible backend metadata connected."""

    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
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


class TracingCaptureSource(FakeCaptureSource):
    def __init__(
        self,
        *,
        clock: FakeMonotonicClock,
        trace: list[str],
        close_error: BaseException | None = None,
    ) -> None:
        super().__init__([], clock=clock)
        self._trace = trace
        self._close_error = close_error

    def close(self) -> None:
        self.close_count += 1
        self._trace.append("source_close")
        if self._close_error is not None:
            raise self._close_error


class ClosableReconnect:
    def __init__(
        self,
        *,
        trace: list[str],
        close_error: BaseException | None = None,
    ) -> None:
        self._trace = trace
        self._close_error = close_error

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        del segment_id, deadline
        raise AssertionError("reconnect attempt was not expected")

    def close(self) -> None:
        self._trace.append("reconnect_close")
        if self._close_error is not None:
            raise self._close_error
