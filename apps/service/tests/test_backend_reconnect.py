from threading import Condition, Event, Lock, Thread

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
    BackendReconnectCoordinator,
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

    def wait_for_idle_waits(self, count: int, timeout_s: float = 1.0) -> bool:
        with self._condition:
            return self._condition.wait_for(
                lambda: self.idle_wait_calls >= count,
                timeout=timeout_s,
            )

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
    ) -> None:
        with self._condition:
            self.replacements.append(replacement)
            self.replacement_snapshots.append(backend_snapshot)
            self._idle_disconnected = False
            self._condition.notify_all()
        if self._order is not None and self._record_install_order:
            self._order.append("source_installed")

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
        assert deadline is None
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


def test_idle_reconnect_uses_capped_exponential_delays() -> None:
    owner = FakeSourceOwner()
    recorded_delays: list[float] = []
    delays_recorded = Event()

    def open_replacement(**_kwargs: object) -> ReconnectedCaptureSource:
        raise OSError("still unavailable")

    def wait_for_idle_retry(delay: float) -> bool:
        recorded_delays.append(delay)
        if len(recorded_delays) == 7:
            delays_recorded.set()
            return True
        return False

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        wait_for_idle_retry=wait_for_idle_retry,
    )
    reconnect.start()
    try:
        owner.disconnect_while_idle()
        assert delays_recorded.wait(timeout=1.0)
    finally:
        reconnect.close()

    assert recorded_delays == [0.1, 0.2, 0.4, 0.8, 1.6, 2.0, 2.0]
    assert owner.idle_claims == 1


def test_active_reconnect_suppresses_stale_idle_claim_and_open_overlap() -> None:
    owner = FakeSourceOwner()
    active_opened = Event()
    release_active = Event()
    concurrent_lock = Lock()
    concurrent_opens = 0
    maximum_concurrent_opens = 0
    active_result: list[ReconnectedCaptureSource | None] = []

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        nonlocal concurrent_opens, maximum_concurrent_opens
        assert deadline == 1.0
        assert not stop_requested.is_set()
        with concurrent_lock:
            concurrent_opens += 1
            maximum_concurrent_opens = max(maximum_concurrent_opens, concurrent_opens)
        try:
            active_opened.set()
            assert release_active.wait(timeout=1.0)
            return ReconnectedCaptureSource(
                source=ClosableSource(),
                backend_snapshot=_snapshot(segment_id),
            )
        finally:
            with concurrent_lock:
                concurrent_opens -= 1

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        monotonic_clock=lambda: 0.0,
    )
    reconnect.start()
    active_thread = Thread(
        target=lambda: active_result.append(reconnect(segment_id=1, deadline=1.0))
    )
    active_thread.start()
    try:
        assert active_opened.wait(timeout=1.0)
        owner.disconnect_while_idle()
        assert owner.idle_disconnect_observed.wait(timeout=1.0)
        assert owner.idle_claims == 0
        release_active.set()
        active_thread.join(timeout=1.0)
        assert not active_thread.is_alive()
        assert owner.wait_for_idle_waits(2)
    finally:
        release_active.set()
        active_thread.join(timeout=1.0)
        reconnect.close()

    assert maximum_concurrent_opens == 1
    assert owner.active_claims == 1
    assert owner.idle_claims == 0
    assert len(active_result) == 1
    assert active_result[0] is not None


def test_active_reconnect_reraises_backend_input_without_retry() -> None:
    owner = FakeSourceOwner()
    attempts = 0

    def open_replacement(**_kwargs: object) -> ReconnectedCaptureSource:
        nonlocal attempts
        attempts += 1
        raise BackendInputError("invalid reconnect hello")

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        monotonic_clock=lambda: 0.0,
    )

    with pytest.raises(BackendInputError, match="invalid reconnect hello"):
        reconnect(segment_id=1, deadline=1.0)
    reconnect.close()

    assert attempts == 1
    assert owner.active_claims == 1


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


def test_active_reconnect_closes_candidate_opened_at_deadline() -> None:
    clock = FakeClock()
    owner = FakeSourceOwner()
    replacement_source = ClosableSource()

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        del stop_requested
        assert deadline is not None
        clock.value = deadline
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=_snapshot(segment_id),
        )

    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=open_replacement,
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    assert reconnect(segment_id=1, deadline=0.5) is None
    reconnect.close()

    assert replacement_source.closed is True
    assert owner.replacements == []


def test_reconnect_publishes_ports_before_source_with_snapshot() -> None:
    clock = FakeClock()
    order: list[str] = []
    owner = FakeSourceOwner(order=order, record_install_order=True)
    replacement_source = ClosableSource()
    replacement = ReconnectedCaptureSource(
        source=replacement_source,
        backend_snapshot=_snapshot(1),
    )
    reconnect = BackendReconnectCoordinator(
        source_owner=owner,
        open_replacement=lambda **_kwargs: replacement,
        on_connected=lambda _replacement: order.append("ports_published"),
        monotonic_clock=clock,
        sleep=clock.sleep,
    )

    result = reconnect(segment_id=1, deadline=1.0)
    reconnect.close()

    assert result == ReconnectedCaptureSource(
        source=owner,
        backend_snapshot=replacement.backend_snapshot,
    )
    assert order == ["current_closed", "ports_published", "source_installed"]
    assert owner.replacement_snapshots == [replacement.backend_snapshot]


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
        assert deadline is None
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
