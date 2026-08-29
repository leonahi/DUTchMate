from __future__ import annotations

from collections import deque
from contextlib import suppress
from threading import Condition, Event, Thread
from threading import enumerate as enumerate_threads

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
    BackendInputError,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_service.continuous_ingestion import ContinuousIngestionCoordinator


class ControlledSource:
    def __init__(self, *, segment_id: int = 0) -> None:
        self.segment = segment(segment_id)
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException | None] = deque()
        self.read_count = 0
        self.close_count = 0
        self.read_started = Event()
        self.terminal_raised = Event()
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
            self.terminal_raised.set()
            raise outcome
        return outcome

    def wait_for_reads(self, expected: int) -> bool:
        with self._condition:
            return self._condition.wait_for(
                lambda: self.read_count >= expected,
                timeout=1,
            )

    def pending_outcomes(self) -> int:
        with self._condition:
            return len(self._outcomes)

    def close(self) -> None:
        with self._condition:
            self.close_count += 1
            self.closed = True
            self._condition.notify_all()


class FailingCloseSource(ControlledSource):
    def __init__(self, close_error: BaseException) -> None:
        super().__init__()
        self.close_error = close_error

    def close(self) -> None:
        super().close()
        raise self.close_error


class BlockingCloseSource(ControlledSource):
    def __init__(self) -> None:
        super().__init__()
        self.close_started = Event()
        self.allow_close = Event()

    def close(self) -> None:
        self.close_started.set()
        assert self.allow_close.wait(timeout=1)
        super().close()


class BlockingFailingCloseSource(BlockingCloseSource):
    def __init__(self, close_error: BaseException) -> None:
        super().__init__()
        self.close_error = close_error

    def close(self) -> None:
        super().close()
        raise self.close_error


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


def buffer_status_event(*, segment_id: int = 0) -> BufferStatusEvent:
    return BufferStatusEvent(
        segment_id=segment_id,
        timestamp_us=0,
        size_bytes=256,
        used_bytes=8,
        high_water_bytes=16,
        dropped_bytes_total=0,
        overflow_events=0,
    )


def close_coordinator(coordinator: ContinuousIngestionCoordinator) -> None:
    coordinator.close()
    assert not any(
        thread.name == "dutchmate-continuous-ingestion" and thread.is_alive()
        for thread in enumerate_threads()
    )


@pytest.mark.parametrize(
    "idle_event",
    [uart_event(b"idle\n"), buffer_status_event()],
    ids=["uart", "buffer-status"],
)
def test_idle_source_is_drained_without_replay(idle_event: BackendEvent) -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        assert source.read_started.wait(timeout=1)
        source.publish(idle_event)
        assert source.wait_for_reads(2)
        coordinator.begin_workflow()
        source.publish(uart_event(b"active\n"))
        assert coordinator.read_event() == uart_event(b"active\n")
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


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
        close_coordinator(coordinator)


def test_active_workflow_continues_after_source_timeout() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        coordinator.begin_workflow()
        source.publish(None)
        assert source.wait_for_reads(2)
        source.publish(uart_event(b"after-timeout"))
        assert coordinator.read_event() == uart_event(b"after-timeout")
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


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
        close_coordinator(coordinator)


def test_idle_disconnect_is_retained_for_next_workflow() -> None:
    source = ControlledSource()
    terminal = BackendDisconnectedError("removed while idle")
    coordinator = ContinuousIngestionCoordinator(source, event_wait_timeout_s=0.01)
    try:
        source.publish(terminal)
        assert source.terminal_raised.wait(timeout=1)

        coordinator.begin_workflow()
        with pytest.raises(BackendDisconnectedError) as raised:
            coordinator.read_event()

        assert raised.value is terminal
    finally:
        close_coordinator(coordinator)


def test_unexpected_terminal_is_retained_and_replacement_is_rejected() -> None:
    source = ControlledSource()
    terminal = RuntimeError("unexpected read failure")
    coordinator = ContinuousIngestionCoordinator(source, event_wait_timeout_s=0.01)
    replacement = ControlledSource(segment_id=1)
    try:
        coordinator.begin_workflow()
        source.publish(terminal)

        with pytest.raises(RuntimeError) as raised:
            coordinator.read_event()

        assert raised.value is terminal
        with pytest.raises(RuntimeError, match="cannot accept replacement"):
            coordinator.replace_source(replacement)
        assert replacement.close_count == 1
    finally:
        close_coordinator(coordinator)


def test_replacement_requires_successful_disconnect_source_detachment() -> None:
    source = ControlledSource()
    terminal = BackendDisconnectedError("removed")
    coordinator = ContinuousIngestionCoordinator(source)
    rejected = ControlledSource(segment_id=1)
    accepted = ControlledSource(segment_id=2)
    try:
        coordinator.begin_workflow()
        source.publish(terminal)
        with pytest.raises(BackendDisconnectedError):
            coordinator.read_event()

        with pytest.raises(RuntimeError, match="cannot accept replacement"):
            coordinator.replace_source(rejected)
        assert rejected.close_count == 1
        assert source.close_count == 0

        coordinator.close_current_source_for_reconnect()
        assert source.close_count == 1
        coordinator.replace_source(accepted)
        assert accepted.close_count == 0
    finally:
        close_coordinator(coordinator)


def test_disconnect_replacement_resumes_same_ingestion_thread_and_workflow() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    ingestion_thread = coordinator._thread  # noqa: SLF001 - lifecycle assertion.
    try:
        coordinator.begin_workflow()
        source.publish(BackendDisconnectedError("removed"))
        with pytest.raises(BackendDisconnectedError):
            coordinator.read_event()

        coordinator.close_current_source_for_reconnect()
        replacement = ControlledSource(segment_id=1)
        coordinator.replace_source(replacement)
        assert coordinator._thread is ingestion_thread  # noqa: SLF001
        assert ingestion_thread.is_alive()
        assert coordinator.segment == replacement.segment

        resumed = uart_event(b"resumed", segment_id=1)
        replacement.publish(resumed)
        assert coordinator.read_event() == resumed
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_input_error_rejects_reconnect_detachment_and_replacement() -> None:
    source = ControlledSource()
    terminal = BackendInputError("malformed")
    coordinator = ContinuousIngestionCoordinator(source)
    replacement = ControlledSource(segment_id=1)
    try:
        coordinator.begin_workflow()
        source.publish(terminal)
        with pytest.raises(BackendInputError) as raised:
            coordinator.read_event()
        assert raised.value is terminal

        with pytest.raises(RuntimeError):
            coordinator.close_current_source_for_reconnect()
        with pytest.raises(RuntimeError, match="cannot accept replacement"):
            coordinator.replace_source(replacement)
        assert replacement.close_count == 1
        assert source.close_count == 0
    finally:
        close_coordinator(coordinator)


def test_replacement_racing_with_close_is_closed_once_and_never_published() -> None:
    source = BlockingCloseSource()
    coordinator = ContinuousIngestionCoordinator(source)
    replacement = ControlledSource(segment_id=1)
    close_errors: list[BaseException] = []

    def close() -> None:
        try:
            coordinator.close()
        except BaseException as exc:
            close_errors.append(exc)

    closer = Thread(target=close)
    closer.start()
    assert source.close_started.wait(timeout=1)
    try:
        with pytest.raises(RuntimeError, match="cannot accept replacement"):
            coordinator.replace_source(replacement)
        assert replacement.close_count == 1
        assert replacement.read_count == 0
        assert coordinator.segment != replacement.segment
    finally:
        source.allow_close.set()
        closer.join(timeout=1)

    assert not closer.is_alive()
    assert close_errors == []
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_reconnect_source_close_failure_prevents_and_is_retained_by_close() -> None:
    close_error = RuntimeError("old source close failed")
    source = FailingCloseSource(close_error)
    coordinator = ContinuousIngestionCoordinator(source)
    replacement = ControlledSource(segment_id=1)
    try:
        coordinator.begin_workflow()
        source.publish(BackendDisconnectedError("removed"))
        with pytest.raises(BackendDisconnectedError):
            coordinator.read_event()

        with pytest.raises(RuntimeError) as detach_failure:
            coordinator.close_current_source_for_reconnect()
        assert detach_failure.value is close_error
        assert source.close_count == 1

        with pytest.raises(RuntimeError, match="cannot accept replacement"):
            coordinator.replace_source(replacement)
        assert replacement.close_count == 1

        with pytest.raises(RuntimeError) as first_close:
            coordinator.close()
        with pytest.raises(RuntimeError) as repeated_close:
            coordinator.close()
        assert first_close.value is close_error
        assert repeated_close.value is close_error
        assert not coordinator._thread.is_alive()  # noqa: SLF001
    finally:
        with suppress(RuntimeError):
            coordinator.close()


def test_second_begin_workflow_is_rejected() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        coordinator.begin_workflow()
        with pytest.raises(RuntimeError, match="already active"):
            coordinator.begin_workflow()
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_read_event_outside_active_workflow_is_rejected() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        with pytest.raises(RuntimeError, match="workflow is not active"):
            coordinator.read_event()
    finally:
        close_coordinator(coordinator)


def test_end_workflow_clears_unread_events_from_next_workflow() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source, event_wait_timeout_s=0.01)
    try:
        coordinator.begin_workflow()
        source.publish(uart_event(b"old-A"))
        source.publish(uart_event(b"old-B"))
        assert source.wait_for_reads(3)

        coordinator.end_workflow()
        coordinator.begin_workflow()
        assert coordinator.read_event() is None
        source.publish(uart_event(b"new"))
        assert coordinator.read_event() == uart_event(b"new")
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_discard_pending_events_does_not_discard_active_fifo() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        coordinator.begin_workflow()
        source.publish(uart_event(b"kept"))
        assert source.wait_for_reads(2)
        coordinator.discard_pending_events()
        assert coordinator.read_event() == uart_event(b"kept")
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_segment_snapshot_refreshes_after_source_read() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    try:
        assert coordinator.segment == segment(0)
        coordinator.begin_workflow()
        source.segment = segment(1)
        source.publish(uart_event(b"new-segment", segment_id=1))
        assert coordinator.read_event() == uart_event(b"new-segment", segment_id=1)
        assert coordinator.segment == segment(1)
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


@pytest.mark.parametrize("queue_capacity", [0, -1, True, 1.5, "1"])
def test_queue_capacity_must_be_a_positive_non_boolean_integer(
    queue_capacity: object,
) -> None:
    source = ControlledSource()
    with pytest.raises(ValueError, match="queue capacity must be a positive integer"):
        ContinuousIngestionCoordinator(source, queue_capacity=queue_capacity)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "event_wait_timeout_s",
    [0, -0.1, float("inf"), float("-inf"), float("nan"), True, "0.1"],
)
def test_event_wait_timeout_must_be_positive_and_finite(
    event_wait_timeout_s: object,
) -> None:
    source = ControlledSource()
    with pytest.raises(ValueError, match="event wait timeout must be positive and finite"):
        ContinuousIngestionCoordinator(
            source,
            event_wait_timeout_s=event_wait_timeout_s,  # type: ignore[arg-type]
        )


def test_constructor_closes_source_when_thread_start_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    start_error = RuntimeError("thread start failed")

    def fail_start(thread: Thread) -> None:
        del thread
        raise start_error

    monkeypatch.setattr(Thread, "start", fail_start)

    with pytest.raises(RuntimeError) as raised:
        ContinuousIngestionCoordinator(source)

    assert raised.value is start_error
    assert source.close_count == 1


def test_capacity_one_backpressure_preserves_exact_order() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source, queue_capacity=1)
    try:
        coordinator.begin_workflow()
        expected = [uart_event(b"A"), uart_event(b"B"), uart_event(b"C")]
        for event in expected:
            source.publish(event)

        assert source.wait_for_reads(2)
        assert source.read_count == 2
        assert source.pending_outcomes() == 1

        assert coordinator.read_event() == expected[0]
        assert source.wait_for_reads(3)
        assert coordinator.read_event() == expected[1]
        assert coordinator.read_event() == expected[2]
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_ending_workflow_unblocks_producer_without_leaking_blocked_event() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(
        source,
        queue_capacity=1,
        event_wait_timeout_s=0.01,
    )
    try:
        coordinator.begin_workflow()
        source.publish(uart_event(b"queued"))
        source.publish(uart_event(b"blocked"))
        assert source.wait_for_reads(2)
        assert source.read_count == 2

        coordinator.end_workflow()
        assert source.wait_for_reads(3)
        coordinator.begin_workflow()
        assert coordinator.read_event() is None
        source.publish(uart_event(b"fresh"))
        assert coordinator.read_event() == uart_event(b"fresh")
        coordinator.end_workflow()
    finally:
        close_coordinator(coordinator)


def test_close_while_idle_after_timeout_draining_stops_thread() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    source.publish(None)
    assert source.wait_for_reads(2)

    coordinator.close()

    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_close_while_workflow_active_is_safe_for_finally_cleanup() -> None:
    source = BlockingCloseSource()
    coordinator = ContinuousIngestionCoordinator(source)
    coordinator.begin_workflow()

    closer = Thread(target=coordinator.close)
    closer.start()
    assert source.close_started.wait(timeout=1)
    try:
        coordinator.end_workflow()
        coordinator.end_workflow()
        with pytest.raises(RuntimeError):
            coordinator.begin_workflow()
    finally:
        source.allow_close.set()
        closer.join(timeout=1)

    assert not closer.is_alive()
    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_close_while_source_read_is_blocked_stops_thread() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    assert source.read_started.wait(timeout=1)

    coordinator.close()

    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_close_while_fifo_producer_is_blocked_stops_thread() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source, queue_capacity=1)
    coordinator.begin_workflow()
    source.publish(uart_event(b"queued"))
    source.publish(uart_event(b"blocked"))
    assert source.wait_for_reads(2)

    coordinator.close()

    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_close_while_ingestion_waits_for_replacement_stops_thread() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source)
    coordinator.begin_workflow()
    source.publish(BackendDisconnectedError("removed"))
    with pytest.raises(BackendDisconnectedError):
        coordinator.read_event()
    coordinator.close_current_source_for_reconnect()

    coordinator.close()

    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.


def test_close_wakes_active_reader_with_coordinator_owned_disconnect() -> None:
    source = ControlledSource()
    coordinator = ContinuousIngestionCoordinator(source, event_wait_timeout_s=10)
    coordinator.begin_workflow()
    reader_waiting = Event()
    original_wait = coordinator._condition.wait  # noqa: SLF001

    def signaling_wait(timeout: float | None = None) -> bool:
        reader_waiting.set()
        return original_wait(timeout)

    coordinator._condition.wait = signaling_wait  # type: ignore[method-assign]  # noqa: SLF001
    outcomes: list[BackendEvent | None | BaseException] = []

    def read() -> None:
        try:
            outcomes.append(coordinator.read_event())
        except BaseException as exc:
            outcomes.append(exc)

    reader = Thread(target=read)
    reader.start()
    assert reader_waiting.wait(timeout=1)

    coordinator.close()
    reader.join(timeout=1)

    assert not reader.is_alive()
    assert len(outcomes) == 1
    terminal = outcomes[0]
    assert isinstance(terminal, BackendDisconnectedError)
    assert str(terminal) == "continuous ingestion coordinator is closed"


def test_concurrent_close_calls_share_exact_cleanup_error_and_close_once() -> None:
    close_error = RuntimeError("source close failed")
    source = BlockingFailingCloseSource(close_error)
    coordinator = ContinuousIngestionCoordinator(source)
    errors: list[BaseException] = []

    def close() -> None:
        try:
            coordinator.close()
        except BaseException as exc:
            errors.append(exc)

    first = Thread(target=close)
    second = Thread(target=close)
    first.start()
    assert source.close_started.wait(timeout=1)
    second.start()
    second.join(timeout=0.05)
    assert second.is_alive()
    source.allow_close.set()
    first.join(timeout=1)
    second.join(timeout=1)

    assert not first.is_alive()
    assert not second.is_alive()
    assert source.close_count == 1
    assert not coordinator._thread.is_alive()  # noqa: SLF001 - lifecycle assertion.
    assert errors == [close_error, close_error]
    with pytest.raises(RuntimeError) as repeated:
        coordinator.close()
    assert repeated.value is close_error
