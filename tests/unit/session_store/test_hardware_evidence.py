import json
from pathlib import Path

import pytest
from session_store_support import (
    enhanced_snapshot,
    evidence_bytes,
    fixed_clock,
    fixed_id,
    read_jsonl,
)

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.backends import BufferOverflowEvent, BufferStatusEvent, UartIntegrity
from dutchmate_core.session_store.models import SessionHandle
from dutchmate_core.session_store.store import (
    EvidenceQuotaExceeded,
    SessionPersistenceError,
    SessionStore,
)


def test_append_control_action_writes_normalized_reset_evidence(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.append_control_action(
        handle,
        action="reset",
        segment_id=0,
        performed_at="2026-07-14T12:30:45Z",
        pulse_ms=250,
        timestamp_us=25,
        device_timestamp_us=1025,
    )

    assert read_jsonl(handle.paths.hardware_events) == [
        {
            "type": "control_action",
            "action": "reset",
            "segment_id": 0,
            "performed_at": "2026-07-14T12:30:45Z",
            "pulse_ms": 250,
            "timestamp_us": 25,
            "device_timestamp_us": 1025,
        }
    ]
    metadata = store.load_metadata(handle.session_id)
    assert metadata["segments"][0]["first_timestamp_us"] == 25  # type: ignore[index]
    assert metadata["segments"][0]["last_timestamp_us"] == 25  # type: ignore[index]
    assert metadata["storage"]["evidence_bytes_written"] == evidence_bytes(  # type: ignore[index]
        handle
    )


def test_control_action_quota_admission_is_whole_unit(tmp_path: Path) -> None:
    def append_action(store: SessionStore, handle: SessionHandle) -> None:
        store.append_control_action(
            handle,
            action="reset",
            segment_id=0,
            performed_at="2026-07-14T12:30:45Z",
            pulse_ms=100,
            timestamp_us=25,
            device_timestamp_us=1025,
        )

    reference = SessionStore(
        root=tmp_path / "reference",
        clock=fixed_clock,
        id_factory=fixed_id,
    )
    reference_handle = reference.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    append_action(reference, reference_handle)
    exact_budget = evidence_bytes(reference_handle)

    exact = SessionStore(
        root=tmp_path / "exact",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=exact_budget,
    )
    exact_handle = exact.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    append_action(exact, exact_handle)
    assert evidence_bytes(exact_handle) == exact_budget

    rejected = SessionStore(
        root=tmp_path / "rejected",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=exact_budget - 1,
    )
    rejected_handle = rejected.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    with pytest.raises(EvidenceQuotaExceeded) as exc_info:
        append_action(rejected, rejected_handle)

    assert rejected_handle.paths.hardware_events.read_bytes() == b""
    metadata = rejected.load_metadata(rejected_handle.session_id)
    assert metadata["state"] == "completed"
    assert metadata["end_reason"] == "size_limit"
    assert exc_info.value.truncation["rejected_unit_type"] == "control_action"


def test_control_action_transaction_rolls_back_partial_append(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    metadata_before = handle.paths.metadata.read_bytes()
    real_append = persistence.append_serialized

    def append_then_fail(path: Path, data: bytes) -> None:
        real_append(path, data)
        if path == handle.paths.hardware_events:
            raise SessionPersistenceError(
                operation="append",
                path=path,
                detail="simulated control-action failure",
            )

    monkeypatch.setattr(persistence, "append_serialized", append_then_fail)

    with pytest.raises(SessionPersistenceError, match="control-action failure"):
        store.append_control_action(
            handle,
            action="reset",
            segment_id=0,
            performed_at="2026-07-14T12:30:45Z",
            pulse_ms=100,
            timestamp_us=25,
            device_timestamp_us=1025,
        )

    assert handle.paths.hardware_events.read_bytes() == b""
    assert handle.paths.metadata.read_bytes() == metadata_before
    assert not (handle.paths.root / ".evidence-transaction.json").exists()


def test_append_buffer_overflow_writes_hardware_event_and_marks_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = BufferOverflowEvent(
        segment_id=0,
        channel=0,
        timestamp_us=1234,
        dropped_bytes=512,
    )

    store.append_buffer_overflow(handle, event=event)

    assert read_jsonl(handle.paths.hardware_events) == [
        {
            "type": "buffer_overflow",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 1234,
            "channel": 0,
            "dropped_bytes": 512,
        }
    ]
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["overflow"] is True


def test_native_hardware_event_admits_exact_budget(tmp_path: Path) -> None:
    event = BufferStatusEvent(
        segment_id=0,
        timestamp_us=1234,
        size_bytes=32768,
        used_bytes=1200,
        high_water_bytes=8000,
        dropped_bytes_total=0,
        overflow_events=0,
    )
    reference_store = SessionStore(
        root=tmp_path / "reference",
        clock=fixed_clock,
        id_factory=fixed_id,
    )
    reference_handle = reference_store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    reference_store.append_buffer_status(reference_handle, event=event)
    exact_budget = evidence_bytes(reference_handle)

    store = SessionStore(
        root=tmp_path / "exact",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=exact_budget,
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.append_buffer_status(handle, event=event)

    metadata = store.load_metadata(handle.session_id)
    assert evidence_bytes(handle) == exact_budget
    assert metadata["storage"]["evidence_bytes_written"] == exact_budget  # type: ignore[index]
    assert metadata["state"] == "active"
    assert metadata["truncated"] is False
    hardware_record = read_jsonl(handle.paths.hardware_events)[0]
    assert hardware_record["type"] == "buffer_status"
    assert hardware_record["segment_id"] == 0
    assert "timestamp_epoch" not in hardware_record


def test_rejected_overflow_event_preserves_summary_facts_without_evidence(
    tmp_path: Path,
) -> None:
    event = BufferOverflowEvent(
        segment_id=0,
        channel=1,
        timestamp_us=4321,
        dropped_bytes=512,
    )
    reference_store = SessionStore(
        root=tmp_path / "reference",
        clock=fixed_clock,
        id_factory=fixed_id,
    )
    reference_handle = reference_store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    reference_store.append_buffer_overflow(reference_handle, event=event)
    projected_bytes = evidence_bytes(reference_handle)

    store = SessionStore(
        root=tmp_path / "rejected",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=projected_bytes - 1,
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    with pytest.raises(EvidenceQuotaExceeded) as raised:
        store.append_buffer_overflow(handle, event=event)

    assert handle.paths.hardware_events.read_bytes() == b""
    assert evidence_bytes(handle) == 3
    assert raised.value.truncation == {
        "reason": "size_limit",
        "rejected_unit_type": "hardware_event",
        "rejected_unit_evidence_bytes": projected_bytes - 3,
        "projected_evidence_bytes": projected_bytes,
        "rejected_uart_payload_bytes": None,
        "segment_id": 0,
        "channel": 1,
        "timestamp_us": 4321,
        "occurred_at": "2026-07-14T12:30:45Z",
    }
    summary = store.summarize_session(handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.overflow is True
    assert summary.integrity == UartIntegrity(
        loss_status="loss_reported",
        observation_scope="debug_helper_rx_buffer",
        dropped_bytes=512,
    )
    metadata = store.load_metadata(handle.session_id)
    assert metadata["segments"][0]["first_timestamp_us"] == 4321  # type: ignore[index]
    assert metadata["segments"][0]["last_timestamp_us"] == 4321  # type: ignore[index]
    assert metadata["storage"]["evidence_bytes_written"] == 3  # type: ignore[index]


def test_append_buffer_overflow_updates_segment_device_timestamps(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    store.append_buffer_overflow(
        handle,
        event=BufferOverflowEvent(
            segment_id=0,
            channel=0,
            timestamp_us=100,
            dropped_bytes=10,
        ),
    )
    store.append_buffer_overflow(
        handle,
        event=BufferOverflowEvent(
            segment_id=0,
            channel=0,
            timestamp_us=250,
            dropped_bytes=20,
        ),
    )

    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][0]
    assert segment["first_device_timestamp_us"] == 100
    assert segment["last_device_timestamp_us"] == 250


def test_append_buffer_overflow_can_write_nonzero_segment(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"].append(
        {
            "segment_id": 1,
            "started_at": "2026-07-14T12:31:00Z",
            "ended_at": None,
            "end_reason": None,
            "hello": None,
            "first_device_timestamp_us": None,
            "last_device_timestamp_us": None,
            "timestamp_epoch": 1,
        }
    )
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    store.append_buffer_overflow(
        handle,
        event=BufferOverflowEvent(
            segment_id=1,
            channel=1,
            timestamp_us=500,
            dropped_bytes=64,
        ),
    )

    event = read_jsonl(handle.paths.hardware_events)[0]
    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][1]
    assert event["segment_id"] == 1
    assert event["timestamp_epoch"] == 1
    assert segment["first_device_timestamp_us"] == 500
    assert segment["last_device_timestamp_us"] == 500


def test_append_buffer_overflow_rejects_missing_segment(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    with pytest.raises(ValueError):
        store.append_buffer_overflow(
            handle,
            event=BufferOverflowEvent(
                segment_id=99,
                channel=0,
                timestamp_us=100,
                dropped_bytes=10,
            ),
        )

    assert handle.paths.hardware_events.read_text(encoding="utf-8") == ""
    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["overflow"] is False


def test_append_buffer_status_writes_hardware_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = BufferStatusEvent(
        segment_id=0,
        timestamp_us=1234,
        size_bytes=32768,
        used_bytes=1200,
        high_water_bytes=8000,
        dropped_bytes_total=0,
        overflow_events=0,
    )

    store.append_buffer_status(handle, event=event)

    assert read_jsonl(handle.paths.hardware_events) == [
        {
            "type": "buffer_status",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 1234,
            "uart_rx_size_bytes": 32768,
            "uart_rx_used_bytes": 1200,
            "uart_rx_high_water_bytes": 8000,
            "dropped_bytes_total": 0,
            "overflow_events": 0,
        }
    ]
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["overflow"] is False


def test_append_buffer_status_marks_overflow_when_telemetry_reports_drops(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = BufferStatusEvent(
        segment_id=0,
        timestamp_us=1234,
        size_bytes=32768,
        used_bytes=32768,
        high_water_bytes=32768,
        dropped_bytes_total=10,
        overflow_events=1,
    )

    store.append_buffer_status(handle, event=event)

    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["overflow"] is True


def test_append_buffer_status_updates_backend_integrity_loss(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2350",
        backend_snapshot=enhanced_snapshot(),
    )

    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=0,
            timestamp_us=1_500,
            size_bytes=32768,
            used_bytes=32768,
            high_water_bytes=32768,
            dropped_bytes_total=37,
            overflow_events=2,
        ),
    )

    summary = store.summarize_session(handle.session_id)
    assert summary.integrity == UartIntegrity(
        loss_status="loss_reported",
        observation_scope="debug_helper_rx_buffer",
        dropped_bytes=37,
    )
    metadata = store.load_metadata(handle.session_id)
    assert metadata["segments"][0]["first_timestamp_us"] == 1_500  # type: ignore[index]
    assert metadata["segments"][0]["last_timestamp_us"] == 1_500  # type: ignore[index]


def test_append_buffer_status_updates_segment_device_timestamps(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=0,
            timestamp_us=100,
            size_bytes=32768,
            used_bytes=10,
            high_water_bytes=100,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )
    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=0,
            timestamp_us=250,
            size_bytes=32768,
            used_bytes=20,
            high_water_bytes=200,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )

    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][0]
    assert segment["first_device_timestamp_us"] == 100
    assert segment["last_device_timestamp_us"] == 250


def test_append_buffer_status_can_write_nonzero_segment(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"].append(
        {
            "segment_id": 1,
            "started_at": "2026-07-14T12:31:00Z",
            "ended_at": None,
            "end_reason": None,
            "hello": None,
            "first_device_timestamp_us": None,
            "last_device_timestamp_us": None,
            "timestamp_epoch": 1,
        }
    )
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=1,
            timestamp_us=500,
            size_bytes=32768,
            used_bytes=25,
            high_water_bytes=400,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )

    event = read_jsonl(handle.paths.hardware_events)[0]
    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][1]
    assert event["segment_id"] == 1
    assert event["timestamp_epoch"] == 1
    assert segment["first_device_timestamp_us"] == 500
    assert segment["last_device_timestamp_us"] == 500


def test_append_buffer_status_rejects_missing_segment(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    with pytest.raises(ValueError):
        store.append_buffer_status(
            handle,
            event=BufferStatusEvent(
                segment_id=99,
                timestamp_us=100,
                size_bytes=32768,
                used_bytes=10,
                high_water_bytes=100,
                dropped_bytes_total=1,
                overflow_events=1,
            ),
        )

    assert handle.paths.hardware_events.read_text(encoding="utf-8") == ""
    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["overflow"] is False
