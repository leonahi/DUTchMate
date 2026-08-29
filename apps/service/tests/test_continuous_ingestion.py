from __future__ import annotations

from collections import deque
from threading import Condition, Event, Thread
from threading import enumerate as enumerate_threads

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
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

    def pending_outcomes(self) -> int:
        with self._condition:
            return len(self._outcomes)

    def close(self) -> None:
        with self._condition:
            self.close_count += 1
            self.closed = True
            self._condition.notify_all()


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
