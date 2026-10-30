from collections.abc import Callable
from threading import Condition, Event
from typing import cast

import pytest

from dutchmate_core.backends import (
    BackendCapability,
    BackendCapabilityPolicy,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    BackendUartSendResult,
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
    BackendReconnectCoordinator,
    ReplaceableDeviceControl,
    ReplaceableUartSender,
    build_basic_capture_reconnect,
    build_enhanced_capture_reconnect,
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
    def __init__(self, *, close_error: BaseException | None = None) -> None:
        self.close_count = 0
        self._close_error = close_error

    def read(self, size: int = 1) -> bytes:
        del size
        return b""

    def write(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


class FakeSourceOwner:
    def __init__(
        self,
        *,
        order: list[str] | None = None,
        record_install_order: bool = False,
    ) -> None:
        self.closed_current = 0
        self.idle_claims = 0
        self.active_claims = 0
        self.replacements: list[CaptureEventSource] = []
        self.replacement_snapshots: list[BackendSnapshot | None] = []
        self.close_count = 0
        self._order = order
        self._record_install_order = record_install_order
        self._condition = Condition()
        self._idle_disconnected = False
        self._closed = False
        self.idle_wait_calls = 0
        self.idle_disconnect_observed = Event()
        self.reconnect_timeouts = 0

    def read_event(self) -> BackendEvent | None:
        return None

    def disconnect_while_idle(self) -> None:
        with self._condition:
            self._idle_disconnected = True
            self._condition.notify_all()

    def wait_for_idle_disconnect(self, timeout_s: float) -> bool:
        with self._condition:
            self.idle_wait_calls += 1
            self._condition.notify_all()
            self._condition.wait_for(
                lambda: self._idle_disconnected or self._closed,
                timeout=timeout_s,
            )
            disconnected = self._idle_disconnected and not self._closed
        if disconnected:
            self.idle_disconnect_observed.set()
        return disconnected

    def close_current_source_for_reconnect(self, *, idle: bool = False) -> None:
        with self._condition:
            if idle:
                if not self._idle_disconnected:
                    raise RuntimeError("idle disconnect is no longer claimable")
                self.idle_claims += 1
                self._idle_disconnected = False
            else:
                self.active_claims += 1
            self.closed_current += 1
            self._condition.notify_all()
        if self._order is not None:
            self._order.append("current_closed")

    def replace_source(
        self,
        replacement: CaptureEventSource,
        *,
        backend_snapshot: BackendSnapshot | None = None,
        before_connected: Callable[[], None] | None = None,
    ) -> None:
        if before_connected is not None:
            before_connected()
        with self._condition:
            self.replacements.append(replacement)
            self.replacement_snapshots.append(backend_snapshot)
            self._idle_disconnected = False
            self._condition.notify_all()
        if self._order is not None and self._record_install_order:
            self._order.append("source_installed")

    def reconnect_timed_out(self) -> None:
        with self._condition:
            self.reconnect_timeouts += 1
            self._condition.notify_all()

    def wait_for_replacements(self, count: int, timeout_s: float = 1.0) -> bool:
        with self._condition:
            return self._condition.wait_for(
                lambda: len(self.replacements) >= count,
                timeout=timeout_s,
            )

    def close(self) -> None:
        with self._condition:
            self.close_count += 1
            self._closed = True
            self._condition.notify_all()


class FakeControl:
    def __init__(self, marker: int) -> None:
        self._control_marker = marker
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
        return self._control_marker

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int:
        self.pulse_requests.append((channel, pulse_ms))
        return self._control_marker

    def set_control_state(self, *, channel: str, state: ControlState) -> int:
        self.state_requests.append((channel, state))
        return self._control_marker


class FakeSender:
    def __init__(self, marker: int) -> None:
        self._sender_marker = marker
        self.requests: list[bytes] = []

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        self.requests.append(data)
        return BackendUartSendResult(
            bytes_accepted=len(data),
            device_timestamp_us=self._sender_marker,
        )


class FakeEnhancedReconnectHost(FakeControl, FakeSender):
    def __init__(
        self,
        *,
        info: BackendInfo,
        segment: SegmentContext | None,
        established_segment: SegmentContext | None = None,
        events: list[BackendEvent] | None = None,
        wait_hook: Callable[[float], None] | None = None,
        close_error: BaseException | None = None,
    ) -> None:
        FakeControl.__init__(self, marker=123)
        FakeSender.__init__(self, marker=456)
        self.info = info
        self._segment = segment
        self._established_segment = established_segment
        self._events = list(events or [])
        self._wait_hook = wait_hook
        self.segment_wait_timeouts: list[float] = []
        self.close_count = 0
        self._close_error = close_error

    @property
    def segment(self) -> SegmentContext | None:
        return self._segment

    def wait_for_segment(self, timeout_s: float) -> SegmentContext | None:
        self.segment_wait_timeouts.append(timeout_s)
        if self._wait_hook is not None:
            self._wait_hook(timeout_s)
        if self._established_segment is not None:
            self._segment = self._established_segment
        return self._segment

    def read_event(self) -> BackendEvent | None:
        if not self._events:
            return None
        return self._events.pop(0)

    def close(self) -> None:
        self.close_count += 1
        if self._close_error is not None:
            raise self._close_error


def test_idle_reconnect_retries_transient_open_and_publishes_once() -> None:
    owner = FakeSourceOwner()
    replacement_source = ClosableSource()
    replacement = ReconnectedCaptureSource(
        source=replacement_source,
        backend_snapshot=_snapshot(0),
    )
    attempts = 0
    retry_delays: list[float] = []

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        nonlocal attempts
        assert segment_id == 0
        assert deadline == 5.0
        assert not stop_requested.is_set()
        attempts += 1
        if attempts == 1:
            raise OSError("port unavailable")
        return replacement

    def wait_for_idle_retry(delay: float) -> bool:
        retry_delays.append(delay)
        return False

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        wait_for_idle_retry=wait_for_idle_retry,
        reconnect_timeout_s=5.0,
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    assert attempts == 2
    assert retry_delays == [0.1]
    assert owner.idle_claims == 1
    assert owner.replacements == [replacement_source]
    assert owner.replacement_snapshots == [replacement.backend_snapshot]


def test_idle_reconnect_stops_at_profile_deadline_and_reports_timeout() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
    recorded_delays: list[float] = []
    timed_out = Event()

    def open_replacement(**_kwargs: object) -> ReconnectedCaptureSource:
        raise OSError("still unavailable")

    def wait_for_idle_retry(delay: float) -> bool:
        recorded_delays.append(delay)
        clock.sleep(delay)
        return False

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        wait_for_idle_retry=wait_for_idle_retry,
        reconnect_timeout_s=0.35,
        monotonic_clock=clock,
    )
    original_timeout = owner.reconnect_timed_out

    def record_timeout() -> None:
        original_timeout()
        timed_out.set()

    owner.reconnect_timed_out = record_timeout  # type: ignore[method-assign]
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert timed_out.wait(timeout=1.0)
    finally:
        reconnect.close()

    assert recorded_delays == pytest.approx([0.1, 0.2, 0.05])
    assert owner.idle_claims == 1
    assert owner.reconnect_timeouts == 1


def test_idle_reconnect_retries_backend_input() -> None:
    owner = FakeSourceOwner()
    replacement_source = ClosableSource()
    attempts = 0

    def open_replacement(**_kwargs: object) -> ReconnectedCaptureSource:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise BackendInputError("incompatible idle candidate")
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(0),
        )

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        wait_for_idle_retry=lambda _delay: False,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    assert attempts == 2
    assert owner.replacements == [replacement_source]


def test_close_interrupts_idle_retry_and_joins_worker() -> None:
    owner = FakeSourceOwner()
    open_failed = Event()
    attempts = 0

    def open_replacement(**_kwargs: object) -> ReconnectedCaptureSource:
        nonlocal attempts
        attempts += 1
        open_failed.set()
        raise OSError("port unavailable")

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
    )
    reconnect.start()
    worker = reconnect._worker
    assert worker is not None
    owner.disconnect_while_idle()
    assert open_failed.wait(timeout=1.0)

    reconnect.close()
    reconnect.close()

    assert attempts == 1
    assert not worker.is_alive()
    assert owner.replacements == []


def test_close_rejects_candidate_returned_after_shutdown_begins() -> None:
    owner = FakeSourceOwner()
    opening = Event()
    replacement_source = ClosableSource()

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        assert segment_id == 0
        assert deadline is not None
        opening.set()
        assert stop_requested.wait(timeout=1.0)
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(0),
        )

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
    )
    reconnect.start()
    owner.disconnect_while_idle()
    assert opening.wait(timeout=1.0)

    reconnect.close()

    assert replacement_source.closed is True
    assert owner.replacements == []


def test_idle_callback_can_close_without_waiting_on_its_own_attempt() -> None:
    owner = FakeSourceOwner()
    replacement_source = ClosableSource()
    callback_entered = Event()
    callback_returned = Event()
    reconnect: BackendReconnectCoordinator

    def close_from_callback(_replacement: ReconnectedCaptureSource) -> None:
        callback_entered.set()
        reconnect.close()
        callback_returned.set()

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=lambda **_kwargs: ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(0),
        ),
        on_connected=close_from_callback,
    )
    reconnect.start()
    worker = reconnect._worker
    assert worker is not None
    owner.disconnect_while_idle()
    assert callback_entered.wait(timeout=1.0)
    returned_without_self_deadlock = callback_returned.wait(timeout=0.1)
    if not returned_without_self_deadlock:
        _release_stuck_attempt(reconnect)
    worker.join(timeout=1.0)

    assert returned_without_self_deadlock
    assert not worker.is_alive()
    assert replacement_source.closed is True
    assert owner.replacements == []
    reconnect.close()


def _release_stuck_attempt(reconnect: BackendReconnectCoordinator) -> None:
    with reconnect._condition:
        reconnect._attempt_active = False
        reconnect._condition.notify_all()


def test_enhanced_idle_candidate_waits_for_origin_before_publish() -> None:
    expected_info = _enhanced_info()
    origin = _segment(0, source_origin_us=4_000)
    host = FakeEnhancedReconnectHost(
        info=expected_info,
        segment=None,
        established_segment=origin,
    )
    owner = FakeSourceOwner()
    opened = Event()

    def open_host(**_kwargs: object) -> FakeEnhancedReconnectHost:
        opened.set()
        return host

    reconnect = build_enhanced_capture_reconnect(
        settings=_enhanced_settings(),
        source_owner=owner,
        expected_info=expected_info,
        control=ReplaceableDeviceControl(FakeControl(10)),
        sender=ReplaceableUartSender(FakeSender(20)),
        open_host=open_host,
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert opened.wait(timeout=1.0)
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    assert host.segment_wait_timeouts == [0.1]
    assert owner.replacements == [host]
    snapshot = owner.replacement_snapshots[0]
    assert snapshot is not None
    assert snapshot.info == expected_info
    assert snapshot.segment == origin


def test_enhanced_idle_identity_mismatch_closes_host_then_retries() -> None:
    mismatched = FakeEnhancedReconnectHost(
        info=_enhanced_info(device="other-helper"),
        segment=None,
    )
    accepted = FakeEnhancedReconnectHost(
        info=_enhanced_info(),
        segment=None,
        established_segment=_segment(0),
    )
    candidates = [mismatched, accepted]
    owner = FakeSourceOwner()

    reconnect = build_enhanced_capture_reconnect(
        settings=_enhanced_settings(),
        source_owner=owner,
        expected_info=_enhanced_info(),
        control=ReplaceableDeviceControl(FakeControl(10)),
        sender=ReplaceableUartSender(FakeSender(20)),
        open_host=lambda **_kwargs: candidates.pop(0),
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    assert mismatched.close_count == 1
    assert accepted.close_count == 0
    assert owner.replacements == [accepted]


def test_enhanced_idle_capability_mismatch_closes_host_then_retries() -> None:
    mismatched = FakeEnhancedReconnectHost(
        info=_enhanced_info(capabilities=frozenset({"gpio_control", "device_timestamp"})),
        segment=None,
    )
    accepted = FakeEnhancedReconnectHost(
        info=_enhanced_info(),
        segment=None,
        established_segment=_segment(0),
    )
    candidates = [mismatched, accepted]
    owner = FakeSourceOwner()

    reconnect = build_enhanced_capture_reconnect(
        settings=_enhanced_settings(),
        source_owner=owner,
        expected_info=_enhanced_info(),
        control=ReplaceableDeviceControl(FakeControl(10)),
        sender=ReplaceableUartSender(FakeSender(20)),
        open_host=lambda **_kwargs: candidates.pop(0),
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    assert mismatched.close_count == 1
    assert accepted.close_count == 0
    assert owner.replacements == [accepted]


def test_basic_idle_candidate_preserves_identity_and_segment_zero() -> None:
    settings = _basic_settings(port="/dev/ttyUSB0")
    expected = BasicBackendEventSource(
        BasicBackendConnection(serial_port=FakeBasicSerial(), settings=settings),
        segment_id=0,
    ).snapshot
    replacement = BasicBackendConnection(
        serial_port=FakeBasicSerial(),
        settings=settings,
    )
    owner = FakeSourceOwner()
    reconnect = build_basic_capture_reconnect(
        settings=settings,
        source_owner=owner,
        expected_snapshot=expected,
        open_connection=lambda _settings: replacement,
        sender=ReplaceableUartSender(FakeSender(20)),
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert owner.wait_for_replacements(1)
    finally:
        reconnect.close()

    snapshot = owner.replacement_snapshots[0]
    assert snapshot is not None
    assert snapshot.info == expected.info
    assert snapshot.capability_policy == expected.capability_policy
    assert snapshot.segment is not None
    assert snapshot.segment.segment_id == 0
    cast(BasicBackendEventSource, owner.replacements[0]).close()


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
            device="dutchmate-rp2350",
            firmware="0.1.0",
            capabilities=frozenset({"uart_receive"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
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


def _segment(segment_id: int, *, source_origin_us: int = 1_000) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=source_origin_us,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )


def _enhanced_info(
    *,
    device: str = "dutchmate-rp2350",
    firmware: str = "0.1.0",
    capabilities: frozenset[BackendCapability] | None = None,
) -> BackendInfo:
    return BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device=device,
        firmware=firmware,
        capabilities=(
            capabilities
            if capabilities is not None
            else frozenset(
                {
                    "uart_receive",
                    "uart_send",
                    "gpio_control",
                    "device_timestamp",
                }
            )
        ),
    )


def _enhanced_settings() -> BackendSettings:
    return BackendSettings(
        mode="enhanced",
        serial_port="/dev/ttyACM0",
        reconnect_timeout_s=1.0,
        baudrate=460800,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=False,
    )


def _basic_settings(*, port: str, tx_enabled: bool = False) -> BackendSettings:
    return BackendSettings(
        mode="basic",
        serial_port=port,
        reconnect_timeout_s=1.0,
        baudrate=115200,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=tx_enabled,
    )
