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
from dutchmate_core.evidence.recorder import ContinuousEvidenceRecorder
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_service.app import create_app


class QueueSource:
    def __init__(self, *, segment_id: int = 0) -> None:
        self.segment = _segment(segment_id)
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException] = deque()
        self.closed = False

    def publish(self, outcome: BackendEvent | BaseException) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            while not self._outcomes and not self.closed:
                self._condition.wait()
            if self.closed:
                raise BackendDisconnectedError("source closed")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

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


def test_initial_validated_snapshot_reaches_status_response(tmp_path: Path) -> None:
    source = QueueSource()
    snapshot = _snapshot()
    runtime, _recorder = _runtime(tmp_path, source=source, snapshot=snapshot)

    try:
        response = TestClient(create_app(runtime)).get("/status")
    finally:
        runtime.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["device"] == "dutchmate-rp2350"
    assert payload["active_session_id"] is not None
    assert payload["timestamp_provenance"]["segment_id"] == 0
    assert payload["integrity"] == {
        "loss_status": "none_reported",
        "observation_scope": "debug_helper_rx_buffer",
        "dropped_bytes": 0,
    }


def test_idle_disconnect_keeps_session_owned_while_reconnecting(tmp_path: Path) -> None:
    source = QueueSource()
    snapshot = _snapshot()
    runtime, recorder = _runtime(tmp_path, source=source, snapshot=snapshot)
    session_id = recorder.active_session_id

    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        response = TestClient(create_app(runtime)).get("/status")
    finally:
        runtime.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is False
    assert payload["connection_state"] == "reconnecting"
    assert payload["active_session_id"] == session_id


def test_reconnect_timeout_projects_disconnected_without_active_session(
    tmp_path: Path,
) -> None:
    source = QueueSource()
    snapshot = _snapshot()
    runtime, recorder = _runtime(tmp_path, source=source, snapshot=snapshot)
    session_id = recorder.active_session_id

    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect(idle=True)
        recorder.reconnect_timed_out()
        response = TestClient(create_app(runtime)).get("/status")
        metadata = runtime.session_store.load_metadata(session_id)
    finally:
        runtime.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is False
    assert payload["connection_state"] == "disconnected"
    assert payload["active_session_id"] is None
    assert metadata["state"] == "failed"
    assert metadata["end_reason"] == "reconnect_timeout"


def test_idle_telemetry_reaches_integrity_response_and_storage(tmp_path: Path) -> None:
    source = QueueSource()
    snapshot = _snapshot()
    runtime, recorder = _runtime(tmp_path, source=source, snapshot=snapshot)
    tail = recorder.durable_tail()

    try:
        source.publish(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=5,
                size_bytes=32768,
                used_bytes=0,
                high_water_bytes=0,
                dropped_bytes_total=0,
                overflow_events=0,
            )
        )
        baseline_tail = recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert baseline_tail is not None
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
        assert recorder.wait_for_durable_tail(baseline_tail, timeout_s=1) is not None
        response = TestClient(create_app(runtime)).get("/status")
        metadata = runtime.session_store.load_metadata(recorder.active_session_id)
    finally:
        runtime.close()

    expected = {
        "loss_status": "loss_reported",
        "observation_scope": "debug_helper_rx_buffer",
        "dropped_bytes": 21,
    }
    assert response.status_code == 200
    assert response.json()["integrity"] == expected
    assert metadata["evidence_quality"]["backend_integrity"] == expected  # type: ignore[index]


def test_idle_replacement_projects_new_identity_and_session_segment(
    tmp_path: Path,
) -> None:
    source = QueueSource()
    replacement = QueueSource()
    initial = _snapshot()
    runtime, recorder = _runtime(tmp_path, source=source, snapshot=initial)
    replacement_snapshot = _snapshot(firmware="0.2.0")

    try:
        source.publish(BackendDisconnectedError("removed while idle"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect(idle=True)
        recorder.replace_source(replacement, backend_snapshot=replacement_snapshot)
        response = TestClient(create_app(runtime)).get("/status")
    finally:
        runtime.close()

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["connection_state"] == "connected"
    assert payload["firmware"] == "0.2.0"
    assert payload["timestamp_provenance"]["segment_id"] == 1


def _runtime(
    root: Path,
    *,
    source: QueueSource,
    snapshot: BackendSnapshot,
) -> tuple[DeviceCoreRuntime, ContinuousEvidenceRecorder]:
    profile = resolve_dut_profile(
        DutProfileConfig(),
        mode="enhanced",
        serial_port="/dev/ttyACM0",
    )
    store = SessionStore(root=root)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=profile,
        backend_snapshot=snapshot,
    )
    runtime = DeviceCoreRuntime(
        device_control=NoopDeviceControl(),
        session_store=store,
        profile=profile,
        evidence_recorder=recorder,
    )
    runtime.record_backend_connection(snapshot.info)
    return runtime, recorder


def _snapshot(*, firmware: str = "0.1.0") -> BackendSnapshot:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
    )
    info = BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        firmware=firmware,
        device="dutchmate-rp2350",
        capabilities=frozenset({"gpio_control", "uart_receive"}),
    )
    return BackendSnapshot(
        info=info,
        capabilities=info.capabilities,
        capability_policy=policy,
        segment=_segment(0),
        integrity=UartIntegrity(
            loss_status="none_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=0,
        ),
    )


def _segment(segment_id: int) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=10_000,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )
