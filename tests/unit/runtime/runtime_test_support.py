from collections.abc import Callable

from dutchmate_core.backends import (
    BackendCapability,
    BackendEvent,
    BackendInfo,
    SegmentContext,
    SegmentTimestamp,
)
from dutchmate_core.device_connection.parser import DeviceMessage


class FakeTransport:
    def __init__(self, responses: list[DeviceMessage] | None = None) -> None:
        self.responses = responses or []
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> DeviceMessage:
        self.requests.append(command)
        if not self.responses:
            raise AssertionError("fake transport has no queued response")
        return self.responses.pop(0)


class FakeSerial:
    def __init__(
        self,
        reads: list[bytes],
        *,
        on_write: Callable[[bytes], None] | None = None,
    ) -> None:
        self.reads = reads
        self.on_write = on_write
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        if self.on_write is not None:
            self.on_write(data)
        return len(data)

    def flush(self) -> None:
        pass

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        if not self.reads:
            return b""
        return self.reads.pop(0)

    def close(self) -> None:
        pass


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class AdvancingMonotonicClock:
    def __init__(self, *, step_s: float = 0.1) -> None:
        self.value = 0.0
        self._step_s = step_s

    def __call__(self) -> float:
        self.value += self._step_s
        return self.value


class FakeCaptureSource:
    def __init__(
        self,
        script: list[BackendEvent | Exception | None],
        *,
        clock: FakeMonotonicClock,
        on_read: Callable[[], None] | None = None,
        read_duration_s: float = 0.1,
    ) -> None:
        self._script = script
        self._clock = clock
        self._on_read = on_read
        self._read_duration_s = read_duration_s
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

    def read_event(self) -> BackendEvent | None:
        if self._on_read is not None:
            on_read = self._on_read
            self._on_read = None
            on_read()
        self._clock.advance(self._read_duration_s)
        if not self._script:
            return None

        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self) -> None:
        self.close_count += 1


def enhanced_info(
    *,
    port: str = "/dev/ttyACM0",
    capabilities: frozenset[BackendCapability] = frozenset(
        {"gpio_control", "uart_receive", "uart_send"}
    ),
) -> BackendInfo:
    return BackendInfo(
        mode="enhanced",
        port=port,
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=capabilities,
    )
