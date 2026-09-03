from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Sequence

import pytest

from dutchmate_core.backends import (
    BackendEvent,
    BackendInfo,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.device_connection.messages import CommandSuccessMessage
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_service.enhanced_async import open_enhanced_async_host


def _info() -> BackendInfo:
    return BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="DUTchMate Debug Helper",
        firmware="1.0.0",
        capabilities=frozenset(
            {
                "uart_receive",
                "uart_send",
                "gpio_control",
                "device_timestamp",
            }
        ),
    )


def _segment(*, segment_id: int, source_origin_us: int) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=source_origin_us,
            observation_point="debug_helper_uart_rx",
            event_granularity="device_message",
        ),
    )


class FakeAsyncEnhancedAdapter:
    def __init__(
        self,
        *,
        info: BackendInfo,
        segment_id: int,
        request_outcomes: Sequence[DeviceMessage | BaseException] = (),
        event_outcomes: Sequence[BackendEvent | BaseException | None] = (),
        segment_wait_outcomes: Sequence[SegmentContext | BaseException | None] = (),
        segment_after_receive: SegmentContext | None = None,
        block_receive: bool = False,
        block_close: bool = False,
        close_error: BaseException | None = None,
        release_receive_during_close: bool = True,
        before_close: Callable[[], None] | None = None,
    ) -> None:
        self.info = info
        self.segment_id = segment_id
        self.segment: SegmentContext | None = None
        self.request_outcomes = list(request_outcomes)
        self.event_outcomes = list(event_outcomes)
        self.segment_wait_outcomes = list(segment_wait_outcomes)
        self.segment_after_receive = segment_after_receive
        self.block_receive = block_receive
        self.close_error = close_error
        self.release_receive_during_close = release_receive_during_close
        self.before_close = before_close
        self.close_count = 0
        self.discard_count = 0
        self.receive_count = 0
        self.discard_thread_id: int | None = None
        self.wait_for_segment_timeouts: list[float] = []
        self.operation_thread_ids: list[int] = []
        self.receive_started = threading.Event()
        self.release_receive = threading.Event()
        self.close_started = threading.Event()
        self.close_failed = threading.Event()
        self.release_close = threading.Event()
        if not block_close:
            self.release_close.set()

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        del command, timeout_s
        self.operation_thread_ids.append(threading.get_ident())
        if not self.request_outcomes:
            raise AssertionError("unexpected command request")
        outcome = self.request_outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def receive_event(
        self,
        timeout_s: float | None = None,
    ) -> BackendEvent | None:
        del timeout_s
        self.operation_thread_ids.append(threading.get_ident())
        self.receive_count += 1
        self.receive_started.set()
        if self.block_receive:
            await asyncio.to_thread(self.release_receive.wait)
        outcome = self.event_outcomes.pop(0) if self.event_outcomes else None
        if isinstance(outcome, BaseException):
            raise outcome
        self.segment = self.segment_after_receive
        return outcome

    async def wait_for_segment(self, timeout_s: float) -> SegmentContext | None:
        self.operation_thread_ids.append(threading.get_ident())
        self.wait_for_segment_timeouts.append(timeout_s)
        outcome = (
            self.segment_wait_outcomes.pop(0) if self.segment_wait_outcomes else None
        )
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    async def discard_pending_events(self) -> None:
        self.operation_thread_ids.append(threading.get_ident())
        self.discard_thread_id = threading.get_ident()
        self.discard_count += 1

    async def close(self) -> None:
        self.operation_thread_ids.append(threading.get_ident())
        self.close_count += 1
        self.close_started.set()
        if self.release_receive_during_close:
            self.release_receive.set()
        if self.before_close is not None:
            self.before_close()
        await asyncio.to_thread(self.release_close.wait)
        if self.close_error is not None:
            self.close_failed.set()
            raise self.close_error


class OpenAdapterFake:
    def __init__(
        self,
        adapter: FakeAsyncEnhancedAdapter | None,
        *,
        error: BaseException | None = None,
    ) -> None:
        self.adapter = adapter
        self.error = error
        self.thread_id: int | None = None

    async def __call__(
        self,
        *,
        port: str,
        segment_id: int,
        baudrate: int,
    ) -> FakeAsyncEnhancedAdapter:
        self.thread_id = threading.get_ident()
        assert port == "/dev/ttyACM0"
        assert segment_id == 0
        assert baudrate == 460800
        if self.error is not None:
            raise self.error
        assert self.adapter is not None
        return self.adapter


def test_host_opens_on_owner_loop_and_projects_identity() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0)
    opener = OpenAdapterFake(fake)

    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    assert host.info == _info()
    assert host.segment_id == 0
    assert opener.thread_id is not None
    assert host.owner_thread_id == opener.thread_id
    assert host.owner_thread_id != threading.get_ident()
    host.close()
    assert fake.close_count == 1
    assert fake.operation_thread_ids == [opener.thread_id]


def test_control_send_and_capture_share_one_adapter_and_owner_loop() -> None:
    event = UartReceiveEvent(
        segment_id=0,
        timestamp_us=0,
        channel=0,
        data=b"boot\n",
    )
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        request_outcomes=[
            CommandSuccessMessage(timestamp_us=10),
            CommandSuccessMessage(timestamp_us=20, bytes_accepted=3),
        ],
        event_outcomes=[event],
    )
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    assert host.pulse_control(channel="CTRL0", pulse_ms=100) == 10
    assert host.send_uart(b"go\n").device_timestamp_us == 20
    assert host.read_event() == event
    assert set(fake.operation_thread_ids) == {opener.thread_id}
    host.close()


def test_control_facade_delegates_configuration_and_state() -> None:
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        request_outcomes=[
            CommandSuccessMessage(timestamp_us=30),
            CommandSuccessMessage(timestamp_us=40),
        ],
    )
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    assert (
        host.configure_gpio_mode(
            channel="CTRL0",
            mode="push_pull",
            active_level="high",
            idle_level="low",
        )
        == 30
    )
    assert host.set_control_state(channel="CTRL0", state="active") == 40
    assert set(fake.operation_thread_ids) == {opener.thread_id}
    host.close()


def test_event_delivery_updates_a_thread_safe_segment_snapshot() -> None:
    segment = _segment(segment_id=0, source_origin_us=1_000)
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        event_outcomes=[
            UartReceiveEvent(segment_id=0, timestamp_us=0, channel=0, data=b"X")
        ],
        segment_after_receive=segment,
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    assert host.segment is None
    assert host.read_event() is not None
    assert host.segment == segment
    host.close()


def test_segment_readiness_uses_owner_loop_without_consuming_an_event() -> None:
    """Fails if readiness drains FIFO evidence or bypasses the adapter owner loop."""

    segment = _segment(segment_id=0, source_origin_us=1_000)
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        segment_wait_outcomes=[segment],
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    assert host.segment is None
    assert host.wait_for_segment(timeout_s=1.0) == segment
    assert host.segment == segment
    assert fake.wait_for_segment_timeouts == [1.0]
    assert fake.receive_count == 0
    assert fake.operation_thread_ids == [host.owner_thread_id]
    host.close()


def test_discard_is_submitted_to_the_adapter_owner_loop() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0)
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    host.discard_pending_events()

    assert fake.discard_count == 1
    assert fake.discard_thread_id == opener.thread_id
    host.close()


def test_blocked_capture_does_not_block_control_dispatch() -> None:
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        request_outcomes=[CommandSuccessMessage(timestamp_us=11)],
        block_receive=True,
    )
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )
    received: list[BackendEvent | None] = []
    reader = threading.Thread(target=lambda: received.append(host.read_event()))

    reader.start()
    assert fake.receive_started.wait(timeout=1)
    assert host.pulse_control(channel="CTRL0", pulse_ms=100) == 11
    fake.release_receive.set()
    reader.join(timeout=1)

    assert not reader.is_alive()
    assert received == [None]
    assert set(fake.operation_thread_ids) == {opener.thread_id}
    host.close()


def test_factory_failure_stops_owner_thread_and_reraises_same_exception() -> None:
    failure = RuntimeError("factory failed")
    opener = OpenAdapterFake(None, error=failure)

    with pytest.raises(RuntimeError) as raised:
        open_enhanced_async_host(
            port="/dev/ttyACM0",
            baudrate=460800,
            segment_id=0,
            open_adapter=opener,
        )

    assert raised.value is failure
    assert opener.thread_id is not None
    assert not any(thread.ident == opener.thread_id for thread in threading.enumerate())


def test_read_event_returns_none_for_ordinary_timeout() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0, event_outcomes=[None])
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    assert host.read_event() is None
    host.close()


def test_command_and_receive_exceptions_cross_the_bridge_unchanged() -> None:
    command_error = RuntimeError("command failed")
    receive_error = RuntimeError("receive failed")
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        request_outcomes=[command_error],
        event_outcomes=[receive_error],
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    with pytest.raises(RuntimeError) as command_raised:
        host.pulse_control(channel="CTRL0", pulse_ms=100)
    with pytest.raises(RuntimeError) as receive_raised:
        host.read_event()

    assert command_raised.value is command_error
    assert receive_raised.value is receive_error
    host.close()


def test_close_marks_host_closing_before_terminalizing_adapter() -> None:
    close_check: list[BaseException] = []
    host_holder = []

    def attempt_read_while_closing() -> None:
        try:
            host_holder[0].read_event()
        except BaseException as exc:
            close_check.append(exc)

    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        before_close=attempt_read_while_closing,
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )
    host_holder.append(host)

    host.close()

    assert len(close_check) == 1
    assert str(close_check[0]) == "Enhanced async host is closed"


def test_close_wakes_blocked_receive_and_leaves_no_owner_thread() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0, block_receive=True)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )
    received: list[BackendEvent | None] = []
    reader = threading.Thread(target=lambda: received.append(host.read_event()))

    reader.start()
    assert fake.receive_started.wait(timeout=1)
    host.close()
    reader.join(timeout=1)

    assert not reader.is_alive()
    assert received == [None]
    assert not host._thread.is_alive()


def test_concurrent_closers_share_adapter_cleanup_and_wait_for_it() -> None:
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        block_close=True,
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )
    completed = [threading.Event(), threading.Event()]
    errors: list[BaseException] = []

    def close_from(index: int) -> None:
        try:
            host.close()
        except BaseException as exc:
            errors.append(exc)
        finally:
            completed[index].set()

    first = threading.Thread(target=close_from, args=(0,))
    second = threading.Thread(target=close_from, args=(1,))
    first.start()
    assert fake.close_started.wait(timeout=1)
    second.start()
    assert not completed[0].is_set()
    assert not completed[1].is_set()
    fake.release_close.set()
    first.join(timeout=1)
    second.join(timeout=1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert errors == []
    assert fake.close_count == 1
    assert not host._thread.is_alive()


def test_close_error_drains_blocked_receive_and_is_shared_by_concurrent_closers() -> None:
    close_error = RuntimeError("adapter close failed")
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        block_receive=True,
        block_close=True,
        close_error=close_error,
        release_receive_during_close=False,
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )
    loop = host._loop
    assert loop is not None
    original_call_soon_threadsafe = loop.call_soon_threadsafe
    stop_requested = threading.Event()
    allow_stop = threading.Event()
    stop_callback = loop.stop

    def record_stop(callback: object, *args: object, **kwargs: object) -> object:
        if callback == stop_callback:
            stop_requested.set()
            allow_stop.wait()
        return original_call_soon_threadsafe(callback, *args, **kwargs)

    loop.call_soon_threadsafe = record_stop  # type: ignore[method-assign]
    received: list[BackendEvent | None] = []
    reader = threading.Thread(
        target=lambda: received.append(host.read_event()),
        daemon=True,
    )
    completed = [threading.Event(), threading.Event()]
    close_errors: list[BaseException] = []

    def close_from(index: int) -> None:
        try:
            host.close()
        except BaseException as exc:
            close_errors.append(exc)
        finally:
            completed[index].set()

    reader.start()
    assert fake.receive_started.wait(timeout=1)
    first = threading.Thread(target=close_from, args=(0,))
    second = threading.Thread(target=close_from, args=(1,))
    first.start()
    assert fake.close_started.wait(timeout=1)
    second.start()
    fake.release_close.set()
    assert fake.close_failed.wait(timeout=1)
    try:
        assert not stop_requested.wait(timeout=1)
    finally:
        fake.release_receive.set()
        allow_stop.set()
        reader.join(timeout=1)
        first.join(timeout=1)
        second.join(timeout=1)

    assert not reader.is_alive()
    assert not first.is_alive()
    assert not second.is_alive()
    assert received == [None]
    assert close_errors == [close_error, close_error]
    assert not host._thread.is_alive()


def test_calls_after_close_raise_the_closed_host_error() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )
    host.close()

    with pytest.raises(RuntimeError, match="^Enhanced async host is closed$"):
        host.read_event()
