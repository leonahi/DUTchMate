from __future__ import annotations

from collections import deque
from pathlib import Path
from threading import Condition

from fastapi.testclient import TestClient

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendSnapshot,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_service.app import create_app
from dutchmate_service.continuous_ingestion import ContinuousIngestionCoordinator


class QueueSource:
    def __init__(self) -> None:
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException] = deque()
        self.read_count = 0
        self.closed = False

    def publish(self, outcome: BackendEvent | BaseException) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            self.read_count += 1
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

    def close(self) -> None:
        with self._condition:
            self.closed = True
            self._condition.notify_all()


class NoopDeviceControl:
    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> None:
        del channel, mode, active_level, idle_level

    def pulse_control(self, *, channel: str, pulse_ms: int) -> None:
        del channel, pulse_ms

    def set_control_state(self, *, channel: str, state: ControlState) -> None:
        del channel, state


def enhanced_replacement_snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
    )
    info = BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        firmware="0.2.0",
        device="dutchmate-rp2350-replacement",
        capabilities=frozenset({"gpio_control", "uart_receive"}),
    )
    return BackendSnapshot(
        info=info,
        capabilities=info.capabilities,
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=1,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=10_000,
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


def test_initial_validated_snapshot_reaches_existing_status_response(
    tmp_path: Path,
) -> None:
    """Catch startup health omitting initial identity, segment, or integrity."""

    source = QueueSource()
    snapshot = enhanced_replacement_snapshot()
    coordinator = ContinuousIngestionCoordinator(
        source,
        backend_snapshot=snapshot,
    )
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="enhanced",
        port="/dev/ttyACM0",
    )
    runtime.record_backend_connection(snapshot.info)

    try:
        response = TestClient(create_app(runtime)).get("/status")
    finally:
        runtime.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["device"] == "dutchmate-rp2350-replacement"
    assert payload["timestamp_provenance"]["segment_id"] == 1
    assert payload["integrity"] == {
        "loss_status": "none_reported",
        "observation_scope": "debug_helper_rx_buffer",
        "dropped_bytes": 0,
    }


def test_idle_basic_disconnect_reaches_existing_status_response(tmp_path: Path) -> None:
    source = QueueSource()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="basic",
        port="/dev/ttyUSB0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        condition = coordinator._condition  # noqa: SLF001 - deterministic barrier.
        with condition:
            assert condition.wait_for(
                lambda: not coordinator.capture_source_health().connected,
                timeout=1,
            )
        response = TestClient(create_app(runtime)).get("/status")
        assert response.status_code == 200
        payload = response.json()
        assert payload["connected"] is False
        assert payload["connection_state"] == "disconnected"
        assert payload["backend_capabilities"] == []
        assert payload["integrity"] is None
        assert payload["reconnect_remaining_s"] is None
    finally:
        runtime.close()


def test_idle_enhanced_telemetry_reaches_existing_integrity_response(
    tmp_path: Path,
) -> None:
    source = QueueSource()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="enhanced",
        port="/dev/ttyACM0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            firmware="0.1.0",
            device="dutchmate-rp2350",
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=10,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=21,
                overflow_events=1,
            )
        )
        assert source.wait_for_reads(2)
        response = TestClient(create_app(runtime)).get("/status")
        assert response.status_code == 200
        assert response.json()["integrity"] == {
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 21,
        }
    finally:
        runtime.close()


def test_idle_replacement_restores_existing_status_identity_and_segment(
    tmp_path: Path,
) -> None:
    """Catches replacement health omitting identity, integrity, or segment projection."""

    source = QueueSource()
    replacement = QueueSource()
    snapshot = enhanced_replacement_snapshot()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="basic",
        port="/dev/ttyUSB0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        assert coordinator.wait_for_idle_disconnect(timeout_s=1.0)
        coordinator.close_current_source_for_reconnect(idle=True)
        coordinator.replace_source(replacement, backend_snapshot=snapshot)

        response = TestClient(create_app(runtime)).get("/status")

        assert response.status_code == 200
        payload = response.json()
        assert payload["connected"] is True
        assert payload["connection_state"] == "connected"
        assert payload["backend_mode"] == "enhanced"
        assert payload["firmware"] == "0.2.0"
        assert payload["device"] == "dutchmate-rp2350-replacement"
        assert payload["backend_capabilities"] == ["gpio_control", "uart_receive"]
        assert payload["integrity"] == {
            "loss_status": "none_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 0,
        }
        assert payload["timestamp_provenance"]["segment_id"] == 1
    finally:
        runtime.close()


def test_first_status_after_idle_replacement_projects_new_telemetry(
    tmp_path: Path,
) -> None:
    """Catches first status retaining snapshot integrity after replacement telemetry."""

    source = QueueSource()
    replacement = QueueSource()
    snapshot = enhanced_replacement_snapshot()
    coordinator = ContinuousIngestionCoordinator(source)
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        message_source=coordinator,
        session_store=SessionStore(root=tmp_path),
        backend_mode="basic",
        port="/dev/ttyUSB0",
    )
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )
    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        assert coordinator.wait_for_idle_disconnect(timeout_s=1.0)
        coordinator.close_current_source_for_reconnect(idle=True)
        coordinator.replace_source(replacement, backend_snapshot=snapshot)
        replacement.publish(
            BufferStatusEvent(
                segment_id=1,
                timestamp_us=20,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=21,
                overflow_events=1,
            )
        )
        assert replacement.wait_for_reads(2)

        response = TestClient(create_app(runtime)).get("/status")

        assert response.status_code == 200
        assert response.json()["integrity"] == {
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 21,
        }
    finally:
        runtime.close()
