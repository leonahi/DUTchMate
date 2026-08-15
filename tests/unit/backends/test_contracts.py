"""Shared contract tests for normalized Basic and Enhanced event sources."""

from collections import deque
from collections.abc import Callable, Iterable
from dataclasses import FrozenInstanceError

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
    BackendEventSource,
    BackendInfo,
    BackendInputError,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)

SourceFactory = Callable[..., BackendEventSource]


class FakeBackendEventSource:
    """Deterministic source used to exercise the shared backend contract."""

    def __init__(
        self,
        *,
        info: BackendInfo,
        segment: SegmentContext,
        outcomes: Iterable[BackendEvent | Exception] = (),
    ) -> None:
        self._info = info
        self._segment = segment
        self._outcomes = deque(outcomes)

    @property
    def info(self) -> BackendInfo:
        return self._info

    @property
    def segment_id(self) -> int:
        return self._segment.segment_id

    @property
    def segment(self) -> SegmentContext:
        return self._segment

    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
        if not self._outcomes:
            return None
        outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def _basic_source(*outcomes: BackendEvent | Exception) -> BackendEventSource:
    return FakeBackendEventSource(
        info=BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=1_000_000,
                observation_point="host_serial_read",
                event_granularity="serial_read_chunk",
            ),
        ),
        outcomes=outcomes,
    )


def _enhanced_source(*outcomes: BackendEvent | Exception) -> BackendEventSource:
    return FakeBackendEventSource(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2040",
            firmware="0.1.0",
            capabilities=frozenset(
                {
                    "uart_receive",
                    "uart_send",
                    "gpio_control",
                    "device_timestamp",
                    "overflow_telemetry",
                }
            ),
        ),
        segment=SegmentContext(
            segment_id=2,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=500,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        ),
        outcomes=outcomes,
    )


@pytest.mark.parametrize(
    ("source_factory", "segment_id"),
    [(_basic_source, 0), (_enhanced_source, 2)],
)
async def test_backend_sources_preserve_fifo_uart_events(
    source_factory: SourceFactory,
    segment_id: int,
) -> None:
    first = UartReceiveEvent(
        segment_id=segment_id,
        timestamp_us=0,
        channel=0,
        data=b"boot \xff",
    )
    second = UartReceiveEvent(
        segment_id=segment_id,
        timestamp_us=10,
        channel=0,
        data=b"ready\n",
    )
    source = source_factory(first, second)

    assert await source.receive_event() == first
    assert await source.receive_event() == second
    assert await source.receive_event(timeout_s=0.01) is None
    assert first.data == b"boot \xff"


async def test_enhanced_source_preserves_telemetry_order() -> None:
    overflow = BufferOverflowEvent(
        segment_id=2,
        timestamp_us=20,
        channel=0,
        dropped_bytes=512,
    )
    status = BufferStatusEvent(
        segment_id=2,
        timestamp_us=30,
        size_bytes=32768,
        used_bytes=4096,
        high_water_bytes=18432,
        dropped_bytes_total=512,
        overflow_events=1,
    )
    source = _enhanced_source(overflow, status)

    assert await source.receive_event() == overflow
    assert await source.receive_event() == status


@pytest.mark.parametrize("source_factory", [_basic_source, _enhanced_source])
async def test_backend_sources_raise_disconnect_distinctly(
    source_factory: SourceFactory,
) -> None:
    source = source_factory(BackendDisconnectedError("connection lost"))

    with pytest.raises(BackendDisconnectedError, match="connection lost"):
        await source.receive_event()


async def test_enhanced_source_raises_invalid_input_distinctly() -> None:
    source = _enhanced_source(BackendInputError("invalid frame"))

    with pytest.raises(BackendInputError, match="invalid frame"):
        await source.receive_event()


def test_basic_and_enhanced_identity_and_provenance_are_explicit() -> None:
    basic = _basic_source()
    enhanced = _enhanced_source()

    assert basic.info.mode == "basic"
    assert basic.info.device is None
    assert basic.segment is not None
    assert basic.segment.timestamp.source == "host"
    assert enhanced.info.mode == "enhanced"
    assert enhanced.info.device == "dutchmate-rp2040"
    assert enhanced.segment is not None
    assert enhanced.segment.timestamp.source == "device"
    assert enhanced.segment_id == 2


def test_contract_values_are_immutable() -> None:
    source = _basic_source()

    with pytest.raises(FrozenInstanceError):
        source.info.port = "/dev/other"  # type: ignore[misc]
