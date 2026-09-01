from collections.abc import Callable

from dutchmate_core.backends import (
    BackendCapability,
    BackendEvent,
    BackendInfo,
    DeviceControlError,
    SegmentContext,
    SegmentTimestamp,
)
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.device_connection.messages import CommandErrorMessage, CommandSuccessMessage
from dutchmate_core.device_connection.parser import DeviceMessage


class FakeDeviceControl:
    def __init__(
        self,
        responses: list[DeviceMessage] | None = None,
        *,
        on_call: Callable[[str, dict[str, object]], None] | None = None,
    ) -> None:
        self._responses = responses or []
        self._on_call = on_call
        self.calls: list[tuple[str, dict[str, object]]] = []

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        self._record(
            "configure_gpio_mode",
            {
                "channel": channel,
                "mode": mode,
                "active_level": active_level,
                "idle_level": idle_level,
            },
        )
        return self._next_timestamp()

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        self._record("pulse_control", {"channel": channel, "pulse_ms": pulse_ms})
        return self._next_timestamp()

    def set_control_state(self, *, channel: str, state: ControlState) -> int | None:
        self._record("set_control_state", {"channel": channel, "state": state})
        return self._next_timestamp()

    def _record(self, operation: str, arguments: dict[str, object]) -> None:
        self.calls.append((operation, arguments))
        if self._on_call is not None:
            self._on_call(operation, arguments)

    def _next_timestamp(self) -> int | None:
        if not self._responses:
            raise AssertionError("fake control has no queued response")
        response = self._responses.pop(0)
        if isinstance(response, CommandSuccessMessage):
            return response.timestamp_us
        if isinstance(response, CommandErrorMessage):
            raise DeviceControlError(error=response.error, detail=response.detail)
        raise AssertionError(f"unexpected fake control response: {type(response).__name__}")


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
