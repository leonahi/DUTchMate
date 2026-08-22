import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from runtime_test_support import (
    AdvancingMonotonicClock,
    FakeCaptureSource,
    FakeMonotonicClock,
    FakeSerial,
    FakeTransport,
    enhanced_info,
)

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendSnapshot,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.enhanced import EnhancedCaptureEventSource, EnhancedDeviceControl
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
)
from dutchmate_core.device_connection.serial_transport import SerialCommandTransport
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import (
    DeviceCoreRuntime,
    DeviceCoreRuntimeError,
    DeviceCoreStatus,
)
from dutchmate_core.session_store.store import SessionPersistenceError, SessionStore
from dutchmate_core.workflows.capture import ReconnectedCaptureSource
from dutchmate_core.workflows.device_actions import DeviceActionError


def test_capture_uart_records_transport_messages_and_connection_metadata(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=100,
                data=b"BOOT_OK\n",
            ),
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=200,
                size_bytes=32768,
                used_bytes=10,
                high_water_bytes=100,
                dropped_bytes_total=0,
                overflow_events=0,
            ),
        ],
        clock=clock,
    )
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "runtime",
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=0.4)

    assert summary.command == "capture --seconds 0.4"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2040"
    assert summary.backend_mode == "enhanced"
    assert summary.port == "/dev/ttyACM0"
    assert summary.backend_capabilities == (
        "gpio_control",
        "uart_receive",
        "uart_send",
    )
    assert summary.capabilities == ("gpio_control", "uart_receive")
    assert summary.capability_policy is not None
    assert summary.capability_policy.uart_send.tx_policy_enabled is False
    assert summary.integrity is not None
    assert summary.integrity.loss_status == "none_reported"
    assert summary.segment_contexts[0].timestamp.observation_point == ("debug_helper_uart_receive")
    assert summary.schema_version == 1
    assert summary.state == "completed"
    assert summary.workflow == "capture"
    assert summary.duration_s == 0.4
    assert summary.reconnect_timeout_s == 5.0
    assert summary.end_reason == "duration_elapsed"
    assert summary.ended_at == "2026-07-27T12:00:00Z"
    assert runtime.status().active_session_id is None
    session_root = tmp_path / summary.session_id
    assert (session_root / "uart_raw.log").read_bytes() == b"BOOT_OK\n"
    assert not (session_root / ".terminal-reserve").exists()
    metadata = store.load_metadata(summary.session_id)
    evidence_bytes = sum(
        session_root.joinpath(name).stat().st_size
        for name in (
            "uart_raw.log",
            "uart_events.jsonl",
            "hardware_events.jsonl",
            "detected_patterns.json",
        )
    )
    assert metadata["storage"]["evidence_bytes_written"] == evidence_bytes  # type: ignore[index]


def test_capture_snapshots_commanded_boot_mode_at_session_start(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    transport = FakeTransport(
        [
            CommandSuccessMessage(timestamp_us=100),
            CommandSuccessMessage(timestamp_us=200),
        ]
    )
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "boot-mode-snapshot",
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info())
    runtime.configure_gpio_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
    )
    runtime.set_boot_mode(mode="bootloader")

    summary = runtime.capture_uart(duration_s=0.2)

    assert store.load_metadata(summary.session_id)["commanded_boot_mode"] == "bootloader"
    assert runtime.get_session(summary.session_id).commanded_boot_mode == "bootloader"


def test_runtime_publishes_reconnect_state_and_replacement_source(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial_source = FakeCaptureSource(
        [BackendDisconnectedError("serial disconnected")],
        clock=clock,
    )
    replacement_snapshot = _replacement_snapshot(1)
    replacement_source = FakeCaptureSource(
        [UartReceiveEvent(segment_id=1, channel=0, timestamp_us=0, data=b"READY\n")],
        clock=clock,
    )
    assert replacement_snapshot.segment is not None
    replacement_source.segment = replacement_snapshot.segment
    observed_reconnect_status: list[DeviceCoreStatus] = []
    runtime: DeviceCoreRuntime

    def reconnect(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        assert segment_id == 1
        observed_reconnect_status.append(runtime.status())
        assert deadline == pytest.approx(0.6)
        return ReconnectedCaptureSource(
            source=replacement_source,
            backend_snapshot=replacement_snapshot,
        )

    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=initial_source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=0.6)

    assert summary.state == "completed"
    assert summary.interrupted is True
    assert summary.resumed is True
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"READY\n"
    reconnect_status = observed_reconnect_status[0]
    assert reconnect_status.connected is False
    assert reconnect_status.connection_state == "reconnecting"
    assert reconnect_status.active_workflow == "capture"
    assert reconnect_status.reconnect_remaining_s == pytest.approx(0.5)
    status = runtime.status()
    assert status.connected is True
    assert status.connection_state == "connected"
    assert status.active_workflow is None
    assert status.reconnect_remaining_s is None
    assert status.timestamp_provenance == replacement_snapshot.segment


def test_new_capture_remaps_live_connection_to_session_segment_zero(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    live_snapshot = _replacement_snapshot(3)
    assert live_snapshot.segment is not None
    source = FakeCaptureSource(
        [UartReceiveEvent(segment_id=3, channel=0, timestamp_us=50, data=b"NEXT\n")],
        clock=clock,
    )
    source.segment = live_snapshot.segment
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(live_snapshot.info)

    summary = runtime.capture_uart(duration_s=0.3)

    assert summary.segment_count == 1
    assert summary.segment_contexts[0].segment_id == 0
    uart_events = [
        json.loads(line)
        for line in (tmp_path / summary.session_id / "uart_events.jsonl").read_text().splitlines()
    ]
    assert uart_events[0]["segment_id"] == 0
    assert "timestamp_epoch" not in uart_events[0]
    status = runtime.status()
    assert status.timestamp_provenance is not None
    assert status.timestamp_provenance.segment_id == 3


def test_capture_uart_exposes_active_session_and_rejects_hardware_operations(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    runtime: DeviceCoreRuntime

    def assert_capture_guards() -> None:
        assert runtime.status().active_session_id is not None
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.capture_uart(duration_s=0.1)
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.run_boot_test(duration_s=0.1)
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.wait_pattern(pattern="READY", timeout_s=0.1)
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.reset_dut()
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.set_boot_mode(mode="normal")
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.configure_gpio_mode(
                role="power_en",
                channel="CTRL2",
                dut_signal="POWER_EN",
                mode="push_pull",
                active_level="high",
                idle_level="low",
            )

    source = FakeCaptureSource([], clock=clock, on_read=assert_capture_guards)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None


def test_capture_uart_stops_cleanly_when_first_uart_unit_exceeds_budget(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=100,
                data=b"BOOT_OK\n",
            ),
            UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=200,
                data=b"LATE\n",
            ),
        ],
        clock=clock,
    )
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "quota",
        evidence_budget_bytes=3,
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=1.0)

    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.error is None
    assert summary.truncation is not None
    assert summary.truncation["rejected_unit_type"] == "uart_receive"
    assert summary.truncation["rejected_uart_payload_bytes"] == 8
    session_root = tmp_path / summary.session_id
    assert (session_root / "uart_raw.log").read_bytes() == b""
    assert (session_root / "uart_events.jsonl").read_bytes() == b""
    assert (session_root / "hardware_events.jsonl").read_bytes() == b""
    assert (session_root / "detected_patterns.json").read_bytes() == b"[]\n"
    assert runtime.status().active_session_id is None


def test_capture_uart_stops_cleanly_when_hardware_event_exceeds_budget(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=150,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=37,
                overflow_events=1,
            ),
            UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=200,
                data=b"LATE\n",
            ),
        ],
        clock=clock,
    )
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "hardware-quota",
        evidence_budget_bytes=3,
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=1.0)

    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.overflow is True
    assert summary.integrity is not None
    assert summary.integrity.loss_status == "loss_reported"
    assert summary.integrity.dropped_bytes == 37
    assert summary.truncation is not None
    assert summary.truncation["rejected_unit_type"] == "hardware_event"
    assert summary.truncation["rejected_uart_payload_bytes"] is None
    assert summary.truncation["channel"] is None
    assert summary.truncation["timestamp_us"] == 150
    session_root = tmp_path / summary.session_id
    assert (session_root / "uart_raw.log").read_bytes() == b""
    assert (session_root / "uart_events.jsonl").read_bytes() == b""
    assert (session_root / "hardware_events.jsonl").read_bytes() == b""
    assert (session_root / "detected_patterns.json").read_bytes() == b"[]\n"
    assert runtime.status().active_session_id is None


def test_capture_uart_terminalizes_cleanly_when_final_session_event_exceeds_budget(
    tmp_path: Path,
) -> None:
    uart_event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=250,
        data=b"x" * 65537,
    )
    reference_clock = FakeMonotonicClock()
    reference_store = SessionStore(
        root=tmp_path / "reference",
        clock=_fixed_session_time,
        id_factory=lambda: "reference",
    )
    reference_runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource([uart_event], clock=reference_clock),
        capture_clock=reference_clock,
        session_store=reference_store,
    )
    reference_runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))
    reference_summary = reference_runtime.capture_uart(duration_s=0.3)
    reference_root = tmp_path / "reference" / reference_summary.session_id
    exact_budget = sum(
        reference_root.joinpath(name).stat().st_size
        for name in (
            "uart_raw.log",
            "uart_events.jsonl",
            "hardware_events.jsonl",
            "detected_patterns.json",
        )
    )

    clock = FakeMonotonicClock()
    store = SessionStore(
        root=tmp_path / "rejected",
        clock=_fixed_session_time,
        id_factory=lambda: "session-event-quota",
        evidence_budget_bytes=exact_budget - 1,
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource([uart_event], clock=clock),
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=0.3)

    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.line_processing.status == "limit_exceeded"
    assert summary.truncation is not None
    assert summary.truncation["rejected_unit_type"] == "session_event"
    session_root = tmp_path / "rejected" / summary.session_id
    assert (session_root / "uart_raw.log").read_bytes() == uart_event.data
    assert (session_root / "hardware_events.jsonl").read_bytes() == b""
    assert runtime.status().active_session_id is None

    collision_clock = FakeMonotonicClock()
    collision_store = SessionStore(
        root=tmp_path / "collision",
        clock=_fixed_session_time,
        id_factory=lambda: "session-event-collision",
        evidence_budget_bytes=exact_budget - 1,
    )
    collision_runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource(
            [uart_event, DeviceCoreRuntimeError("backend disconnected")],
            clock=collision_clock,
        ),
        capture_clock=collision_clock,
        session_store=collision_store,
    )
    collision_runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    collision_summary = collision_runtime.capture_uart(duration_s=0.3)

    assert collision_summary.state == "completed"
    assert collision_summary.end_reason == "size_limit"
    assert collision_summary.error is None


def test_capture_updates_connected_integrity_from_buffer_telemetry(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=200,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=37,
                overflow_events=1,
            )
        ],
        clock=clock,
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    summary = runtime.capture_uart(duration_s=0.3)

    assert summary.integrity is not None
    assert summary.integrity.loss_status == "loss_reported"
    assert summary.integrity.dropped_bytes == 37
    status = runtime.status()
    assert status.integrity == summary.integrity


def test_capture_uart_requires_connection(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.capture_uart(duration_s=0.1)


def test_capture_uart_requires_message_source(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    with pytest.raises(DeviceCoreRuntimeError, match="message source"):
        runtime.capture_uart(duration_s=0.1)


def test_capture_uart_clears_active_session_after_transport_failure(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([RuntimeError("serial failed")], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    with pytest.raises(RuntimeError, match="serial failed"):
        runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None
    session_id = next(tmp_path.iterdir()).name
    summary = runtime.session_store.summarize_session(session_id)
    assert summary.state == "failed"
    assert summary.end_reason == "backend_error"
    assert summary.error == {
        "code": "internal_error",
        "detail": "serial failed",
        "detail_truncated": False,
    }


def test_capture_uart_records_persistence_failure_and_clears_active_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"READY\n")],
        clock=clock,
    )
    store = SessionStore(root=tmp_path)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    def fail_append(*args: object, **kwargs: object) -> None:
        raise SessionPersistenceError(
            operation="append",
            path=tmp_path / "uart_events.jsonl",
            detail="simulated storage failure",
        )

    monkeypatch.setattr(store, "append_uart_capture", fail_append)

    with pytest.raises(SessionPersistenceError, match="simulated storage failure"):
        runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None
    session_id = next(tmp_path.iterdir()).name
    summary = store.summarize_session(session_id)
    assert summary.state == "failed"
    assert summary.end_reason == "persistence_error"
    assert summary.error == {
        "code": "persistence_fault",
        "detail": (
            "session persistence append failed for uart_events.jsonl: simulated storage failure"
        ),
        "detail_truncated": False,
    }


def test_capture_uart_does_not_terminalize_when_persistence_state_is_unsafe(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"READY\n")],
        clock=clock,
    )
    store = SessionStore(root=tmp_path)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    def fail_append(*args: object, **kwargs: object) -> None:
        raise SessionPersistenceError(
            operation="recover transaction",
            path=tmp_path / ".evidence-transaction.json",
            detail="preimage is unavailable",
            terminalization_safe=False,
        )

    monkeypatch.setattr(store, "append_uart_capture", fail_append)

    with pytest.raises(SessionPersistenceError, match="preimage is unavailable"):
        runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None
    session_id = next(tmp_path.iterdir()).name
    assert store.summarize_session(session_id).state == "active"


@pytest.mark.parametrize("duration_s", [0, 300.1, True])
def test_capture_uart_rejects_invalid_duration_before_creating_session(
    tmp_path: Path,
    duration_s: object,
) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    with pytest.raises(ValueError, match="positive finite"):
        runtime.capture_uart(duration_s=duration_s)  # type: ignore[arg-type]

    assert list(tmp_path.iterdir()) == []


def test_run_boot_test_creates_session_before_reset_and_records_queued_uart(
    tmp_path: Path,
) -> None:
    runtime: DeviceCoreRuntime

    def assert_session_reserved_before_reset(command: bytes) -> None:
        if b'"cmd":"reset"' not in command:
            return
        active_session_id = runtime.status().active_session_id
        assert active_session_id is not None
        session_root = tmp_path / active_session_id
        assert json.loads(session_root.joinpath("metadata.json").read_text())["state"] == "active"
        assert session_root.joinpath(".terminal-reserve").stat().st_size == 262144

    serial = FakeSerial(
        [
            b'{"ok":true,"timestamp_us":10}\n',
            b'{"type":"uart","channel":0,"timestamp_us":20,"data_b64":"Qk9PVF9PSwo="}\n',
            b'{"ok":true,"timestamp_us":30}\n',
        ],
        on_write=assert_session_reserved_before_reset,
    )
    transport = SerialCommandTransport(serial)
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "boot-test",
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        message_source=EnhancedCaptureEventSource(
            transport,
            segment_id=0,
            source_origin_us=0,
        ),
        capture_clock=AdvancingMonotonicClock(),
        session_store=store,
        action_wall_clock=_fixed_session_time,
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL2",
        dut_signal="NRST",
        mode="open_drain",
        active_level="low",
    )

    summary = runtime.run_boot_test(duration_s=0.4)

    assert summary.command == "boot-test --seconds 0.4"
    assert summary.schema_version == 1
    assert summary.state == "completed"
    assert summary.workflow == "boot_test"
    assert serial.writes == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL2","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"reset","pulse_ms":100}\n',
    ]
    session_root = tmp_path / summary.session_id
    assert session_root.joinpath("uart_raw.log").read_bytes() == b"BOOT_OK\n"
    assert _read_jsonl(session_root / "hardware_events.jsonl") == [
        {
            "type": "control_action",
            "action": "reset",
            "segment_id": 0,
            "performed_at": "2026-07-27T12:00:00Z",
            "pulse_ms": 100,
            "timestamp_us": 30,
            "device_timestamp_us": 30,
        }
    ]
    assert runtime.status().active_session_id is None


def test_run_boot_test_requires_reset_role_before_creating_session(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeTransport()
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))

    with pytest.raises(GpioConfigurationError, match="'reset'.*not configured") as exc_info:
        runtime.run_boot_test(duration_s=0.2)

    assert exc_info.value.operation == "boot_test"
    assert exc_info.value.required_role == "reset"
    assert exc_info.value.role_state == "unconfigured"
    assert transport.requests == []
    assert list(tmp_path.iterdir()) == []


def test_run_boot_test_clears_active_session_after_reset_failure(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    transport = FakeTransport(
        [
            CommandErrorMessage(
                error="hardware_fault",
                detail="reset pulse failed",
            )
        ]
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))
    runtime.gpio_registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    with pytest.raises(DeviceActionError, match="reset pulse failed"):
        runtime.run_boot_test(duration_s=0.2)

    assert transport.requests == [b'{"cmd":"reset","pulse_ms":100}\n']
    assert runtime.status().active_session_id is None
    assert len(list(tmp_path.iterdir())) == 1
    session_id = next(tmp_path.iterdir()).name
    summary = runtime.session_store.summarize_session(session_id)
    assert summary.state == "failed"
    assert summary.error == {
        "code": "hardware_fault",
        "detail": "reset pulse failed",
        "detail_truncated": False,
    }
    assert (tmp_path / session_id / "hardware_events.jsonl").read_bytes() == b""


@pytest.mark.parametrize("duration_s", [0, 300.1, True])
def test_run_boot_test_rejects_invalid_duration_before_creating_session(
    tmp_path: Path,
    duration_s: object,
) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    with pytest.raises(ValueError, match="positive finite"):
        runtime.run_boot_test(duration_s=duration_s)  # type: ignore[arg-type]

    assert list(tmp_path.iterdir()) == []


def _fixed_session_time() -> datetime:
    return datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _replacement_snapshot(segment_id: int) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=enhanced_info(port="/dev/ttyACM0"),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
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
