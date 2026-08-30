import pytest

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.basic import BasicBackendConnection, BasicBackendEventSource
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.workflows.capture import CaptureEventSource, ReconnectedCaptureSource
from dutchmate_service.backend_reconnect import (
    ReplaceableDeviceControl,
    ReplaceableUartSender,
    RetryingCaptureReconnect,
    build_basic_capture_reconnect,
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


class FakeBasicSerial:
    def __init__(self) -> None:
        self.close_count = 0

    def read(self, size: int = 1) -> bytes:
        del size
        return b""

    def write(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        self.close_count += 1


class FakeSourceOwner:
    def __init__(self, *, order: list[str] | None = None) -> None:
        self.closed_current = 0
        self.replacements: list[CaptureEventSource] = []
        self.close_count = 0
        self._order = order

    def read_event(self) -> BackendEvent | None:
        return None

    def close_current_source_for_reconnect(self) -> None:
        self.closed_current += 1
        if self._order is not None:
            self._order.append("current_closed")

    def replace_source(self, replacement: CaptureEventSource) -> None:
        self.replacements.append(replacement)

    def close(self) -> None:
        self.close_count += 1


class FakeControl:
    def __init__(self, marker: int) -> None:
        self.marker = marker
        self.configuration_requests: list[tuple[str, str, str, str | None]] = []
        self.pulse_requests: list[tuple[str, int]] = []
        self.state_requests: list[tuple[str, str]] = []

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int:
        self.configuration_requests.append((channel, mode, active_level, idle_level))
        return self.marker

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int:
        self.pulse_requests.append((channel, pulse_ms))
        return self.marker

    def set_control_state(self, *, channel: str, state: ControlState) -> int:
        self.state_requests.append((channel, state))
        return self.marker


def test_reconnect_retries_open_and_publishes_stable_source_owner() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
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
        source_owner=owner,
        open_replacement=open_replacement,
        on_connected=published.append,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    result = reconnect(segment_id=1, deadline=1.0)

    assert result == ReconnectedCaptureSource(
        source=owner,
        backend_snapshot=replacement.backend_snapshot,
    )
    assert owner.closed_current == 1
    assert owner.replacements == [replacement_source]
    assert replacement_source.closed is False
    assert attempts == [1, 1]
    assert published == [replacement]


def test_reconnect_closes_owned_source_before_opening_replacement() -> None:
    clock = FakeClock()
    order: list[str] = []
    owner = FakeSourceOwner(order=order)
    replacement_source = ClosableSource()

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline == 1.0
        assert order == ["current_closed"]
        order.append("replacement_opened")
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(segment_id),
        )

    reconnect = RetryingCaptureReconnect(
        source_owner=owner,
        open_replacement=open_replacement,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    assert reconnect(segment_id=1, deadline=1.0) is not None
    assert order == ["current_closed", "replacement_opened"]
    assert owner.closed_current == 1
    assert owner.replacements == [replacement_source]


def test_reconnect_rejects_source_opened_at_deadline() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
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
        source_owner=owner,
        open_replacement=open_replacement,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    assert reconnect(segment_id=1, deadline=0.5) is None
    assert owner.closed_current == 1
    assert owner.replacements == []
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
        source_owner=FakeSourceOwner(),
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


def test_reconnect_closes_source_owner_when_adapter_publication_fails() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
    replacement_source = ClosableSource()
    replacement = ReconnectedCaptureSource(
        source=replacement_source,
        backend_snapshot=_snapshot(1),
    )
    publication_error = RuntimeError("adapter publication failed")

    def fail_publication(_replacement: ReconnectedCaptureSource) -> None:
        raise publication_error

    reconnect = RetryingCaptureReconnect(
        source_owner=owner,
        open_replacement=lambda **_kwargs: replacement,
        on_connected=fail_publication,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    with pytest.raises(RuntimeError) as raised:
        reconnect(segment_id=1, deadline=1.0)

    assert raised.value is publication_error
    assert owner.closed_current == 1
    assert owner.replacements == [replacement_source]
    assert owner.close_count == 1


def test_basic_reconnect_rejects_identity_before_transferring_source() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
    expected_settings = _basic_settings(port="/dev/ttyUSB0")
    expected_source = BasicBackendEventSource(
        BasicBackendConnection(
            serial_port=FakeBasicSerial(),
            settings=expected_settings,
        ),
        segment_id=0,
    )
    replacement_serial = FakeBasicSerial()
    replacement_connection = BasicBackendConnection(
        serial_port=replacement_serial,
        settings=_basic_settings(port="/dev/ttyUSB1"),
    )
    reconnect = build_basic_capture_reconnect(
        settings=expected_settings,
        source_owner=owner,
        expected_snapshot=expected_source.snapshot,
        open_connection=lambda _settings: replacement_connection,
        sender=ReplaceableUartSender(replacement_connection),
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    with pytest.raises(
        BackendInputError,
        match="Reconnected Basic backend identity changed",
    ) as raised:
        reconnect(segment_id=1, deadline=1.0)

    assert raised.value.backend_mode == "basic"
    assert owner.closed_current == 1
    assert owner.replacements == []
    assert replacement_serial.close_count == 1


def test_replaceable_device_control_forwards_to_latest_adapter() -> None:
    first = FakeControl(10)
    control = ReplaceableDeviceControl(first)

    assert control.pulse_control(channel="CTRL0", pulse_ms=2) == 10
    assert first.pulse_requests == [("CTRL0", 2)]

    replacement = FakeControl(20)
    control.replace(replacement)

    assert (
        control.configure_gpio_mode(
            channel="CTRL3",
            mode="push_pull",
            active_level="low",
            idle_level="high",
        )
        == 20
    )
    assert control.pulse_control(channel="CTRL1", pulse_ms=3) == 20
    assert control.set_control_state(channel="CTRL2", state="idle") == 20
    assert replacement.configuration_requests == [
        ("CTRL3", "push_pull", "low", "high")
    ]
    assert replacement.pulse_requests == [("CTRL1", 3)]
    assert replacement.state_requests == [("CTRL2", "idle")]


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


def _basic_settings(*, port: str) -> BackendSettings:
    return BackendSettings(
        mode="basic",
        serial_port=port,
        reconnect_timeout_s=1.0,
        baudrate=115200,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=False,
    )
