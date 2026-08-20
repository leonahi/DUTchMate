from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.workflows.capture import ReconnectedCaptureSource
from dutchmate_service.backend_reconnect import (
    ReplaceableDeviceControl,
    RetryingCaptureReconnect,
)


class FakeClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def sleep(self, seconds: float) -> None:
        self.value += seconds


class ClosableSource:
    def __init__(self) -> None:
        self.closed = False

    def read_event(self) -> None:
        return None

    def close(self) -> None:
        self.closed = True


class FakeControl:
    def __init__(self, marker: int) -> None:
        self.marker = marker

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        role: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int:
        del channel, role, mode, active_level, idle_level
        return self.marker

    def reset_dut(self, *, pulse_ms: int) -> int:
        return self.marker + pulse_ms

    def set_boot_mode(self, *, mode: str) -> int:
        return self.marker + len(mode)


def test_reconnect_retries_open_and_closes_previous_source() -> None:
    clock = FakeClock()
    previous = ClosableSource()
    replacement_source = ClosableSource()
    replacement = ReconnectedCaptureSource(
        source=replacement_source,
        backend_snapshot=_snapshot(1),
    )
    attempts: list[int] = []
    published: list[ReconnectedCaptureSource] = []

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline == 1.0
        attempts.append(segment_id)
        if len(attempts) == 1:
            raise OSError("port unavailable")
        return replacement

    reconnect = RetryingCaptureReconnect(
        current_source=previous,
        open_replacement=open_replacement,
        on_connected=published.append,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    result = reconnect(segment_id=1, deadline=1.0)

    assert result is replacement
    assert previous.closed is True
    assert replacement_source.closed is False
    assert attempts == [1, 1]
    assert published == [replacement]


def test_reconnect_rejects_source_opened_at_deadline() -> None:
    clock = FakeClock()
    previous = ClosableSource()
    replacement_source = ClosableSource()

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        clock.value = deadline
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(segment_id),
        )

    reconnect = RetryingCaptureReconnect(
        current_source=previous,
        open_replacement=open_replacement,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    assert reconnect(segment_id=1, deadline=0.5) is None
    assert previous.closed is True
    assert replacement_source.closed is True


def test_reconnect_does_not_retry_fatal_backend_input() -> None:
    clock = FakeClock()
    attempts = 0

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        del segment_id, deadline
        nonlocal attempts
        attempts += 1
        raise BackendInputError("invalid reconnect hello")

    reconnect = RetryingCaptureReconnect(
        current_source=ClosableSource(),
        open_replacement=open_replacement,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    try:
        reconnect(segment_id=1, deadline=1.0)
    except BackendInputError as error:
        assert str(error) == "invalid reconnect hello"
    else:
        raise AssertionError("fatal backend input error was not raised")
    assert attempts == 1


def test_replaceable_device_control_forwards_to_latest_adapter() -> None:
    control = ReplaceableDeviceControl(FakeControl(10))

    assert control.reset_dut(pulse_ms=2) == 12

    control.replace(FakeControl(20))

    assert control.reset_dut(pulse_ms=2) == 22
    assert control.set_boot_mode(mode="normal") == 26


def _snapshot(segment_id: int) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2040",
            firmware="0.1.0",
            capabilities=frozenset({"uart_receive"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=1_000,
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
