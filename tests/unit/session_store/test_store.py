import base64
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.store import (
    EvidenceQuotaExceeded,
    LineProcessing,
    SessionHandle,
    SessionStore,
    SessionSummary,
)
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "abc12345"


def enhanced_snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2040",
            firmware="0.1.0",
            capabilities=frozenset({"gpio_control", "uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=0,
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


def test_create_session_initializes_required_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(command="capture", firmware="0.1.0", device="dutchmate-rp2040")

    assert handle == SessionHandle(
        session_id="20260714T123045Z-abc12345",
        paths=handle.paths,
    )
    assert handle.paths.root == tmp_path / "20260714T123045Z-abc12345"
    assert handle.paths.metadata.exists()
    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_text(encoding="utf-8") == ""
    assert handle.paths.hardware_events.read_text(encoding="utf-8") == ""
    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == []


def test_create_session_writes_initial_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2040",
        baseline=True,
    )

    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8")) == {
        "session_id": "20260714T123045Z-abc12345",
        "started_at": "2026-07-14T12:30:45Z",
        "command": "boot-test --seconds 15",
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "baseline": True,
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "line_processing": {
            "status": "complete",
            "max_line_bytes": 65536,
            "oversized_line_count": 0,
        },
        "segments": [
            {
                "segment_id": 0,
                "started_at": "2026-07-14T12:30:45Z",
                "ended_at": None,
                "end_reason": None,
                "hello": None,
                "first_device_timestamp_us": None,
                "last_device_timestamp_us": None,
                "timestamp_epoch": 0,
            }
        ],
    }


def test_create_session_writes_backend_identity_policy_and_provenance(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="capture --seconds 1",
        firmware="0.1.0",
        device="dutchmate-rp2040",
        backend_snapshot=enhanced_snapshot(),
    )

    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["backend_mode"] == "enhanced"
    assert metadata["backend_identity"] == {
        "port": "/dev/ttyACM0",
        "device": "dutchmate-rp2040",
        "firmware": "0.1.0",
    }
    assert metadata["backend_capabilities"] == [
        "gpio_control",
        "uart_receive",
        "uart_send",
    ]
    assert metadata["capabilities"] == ["gpio_control", "uart_receive"]
    assert metadata["capability_policy"] == {
        "uart_send": {
            "tx_policy_enabled": False,
            "source": "hardware.uart.tx_enabled",
        }
    }
    assert metadata["integrity"] == {
        "loss_status": "none_reported",
        "observation_scope": "debug_helper_rx_buffer",
        "dropped_bytes": 0,
    }
    assert metadata["segments"][0]["timestamp"] == {
        "source": "device",
        "clock": "rp2040_timer",
        "unit": "us",
        "origin": "segment_start",
        "source_origin_us": 1_000,
        "observation_point": "debug_helper_uart_receive",
        "event_granularity": "uart_event",
    }

    summary = store.summarize_session(handle.session_id)
    assert summary.backend_mode == "enhanced"
    assert summary.port == "/dev/ttyACM0"
    assert summary.integrity == enhanced_snapshot().integrity
    assert summary.segment_contexts == (enhanced_snapshot().segment,)


def test_create_native_session_writes_active_schema_v1_and_terminal_reserve(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="capture --seconds 2.5",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=2.5,
        reconnect_timeout_s=4.0,
    )
    metadata = store.load_metadata(handle.session_id)
    summary = store.summarize_session(handle.session_id)

    assert metadata["schema_version"] == 1
    assert metadata["state"] == "active"
    assert metadata["workflow"] == "capture"
    assert metadata["duration_s"] == 2.5
    assert metadata["reconnect_timeout_s"] == 4.0
    assert metadata["ended_at"] is None
    assert metadata["end_reason"] is None
    assert metadata["error"] is None
    assert metadata["commanded_boot_mode"] is None
    assert "firmware" not in metadata
    assert "device" not in metadata
    assert metadata["storage"] == {
        "evidence_budget_bytes": 50 * 1024 * 1024,
        "evidence_bytes_written": 3,
        "metadata_max_bytes": 262144,
    }
    assert handle.paths.terminal_reserve.stat().st_size == 262144
    assert summary.schema_version == 1
    assert summary.state == "active"
    assert summary.workflow == "capture"


def test_complete_native_session_is_terminal_and_one_way(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.complete_session(handle)
    summary = store.summarize_session(handle.session_id)

    assert summary.state == "completed"
    assert summary.end_reason == "duration_elapsed"
    assert summary.ended_at == "2026-07-14T12:30:45Z"
    assert summary.error is None
    assert not handle.paths.terminal_reserve.exists()
    with pytest.raises(ValueError, match="requires active"):
        store.complete_session(handle)
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=1,
        data=b"late\n",
    )
    with pytest.raises(ValueError, match="only append while active"):
        store.append_uart_capture(
            handle,
            event=event,
            result=UartCaptureProcessor().process_event(event),
        )


def test_native_uart_evidence_admits_exact_budget_with_pattern_growth(
    tmp_path: Path,
) -> None:
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=100,
        data=b"BOOT_OK\n",
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
    reference_store.append_uart_capture(
        reference_handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )
    exact_budget = _evidence_bytes(reference_handle)

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

    store.append_uart_capture(
        handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )

    metadata = store.load_metadata(handle.session_id)
    assert _evidence_bytes(handle) == exact_budget
    assert metadata["storage"]["evidence_bytes_written"] == exact_budget  # type: ignore[index]
    assert metadata["truncated"] is False
    assert metadata["state"] == "active"
    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8"))[0][
        "pattern"
    ] == "BOOT_OK"


def test_native_uart_evidence_rejects_one_byte_over_without_counted_mutation(
    tmp_path: Path,
) -> None:
    event = UartReceiveEvent(
        segment_id=0,
        channel=1,
        timestamp_us=321,
        data=b"BOOT_OK\n",
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
    reference_store.append_uart_capture(
        reference_handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )
    projected_bytes = _evidence_bytes(reference_handle)

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
        store.append_uart_capture(
            handle,
            event=event,
            result=UartCaptureProcessor().process_event(event),
        )

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    assert handle.paths.hardware_events.read_bytes() == b""
    assert handle.paths.detected_patterns.read_bytes() == b"[]\n"
    assert _evidence_bytes(handle) == 3
    assert raised.value.truncation == {
        "reason": "size_limit",
        "rejected_unit_type": "uart_receive",
        "rejected_unit_evidence_bytes": projected_bytes - 3,
        "projected_evidence_bytes": projected_bytes,
        "rejected_uart_payload_bytes": len(event.data),
        "segment_id": 0,
        "channel": 1,
        "timestamp_us": 321,
        "occurred_at": "2026-07-14T12:30:45Z",
    }
    summary = store.summarize_session(handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.error is None
    assert summary.truncation == raised.value.truncation
    assert store.load_metadata(handle.session_id)["storage"][  # type: ignore[index]
        "evidence_bytes_written"
    ] == 3


def test_rejected_uart_unit_omits_associated_line_processing_event(
    tmp_path: Path,
) -> None:
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=500,
        data=(b"x" * 65537) + b"\n",
    )
    result = UartCaptureProcessor().process_event(event)
    assert len(result.oversized_lines) == 1

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
    reference_store.append_uart_capture(reference_handle, event=event, result=result)
    projected_bytes = _evidence_bytes(reference_handle)

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

    with pytest.raises(EvidenceQuotaExceeded):
        store.append_uart_capture(handle, event=event, result=result)

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    assert handle.paths.hardware_events.read_bytes() == b""
    assert handle.paths.detected_patterns.read_bytes() == b"[]\n"
    assert store.summarize_session(handle.session_id).line_processing == LineProcessing()


def test_finalized_line_event_uses_exact_session_event_quota_boundary(
    tmp_path: Path,
) -> None:
    event = UartReceiveEvent(
        segment_id=0,
        channel=1,
        timestamp_us=700,
        data=b"x" * 65537,
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
    reference_processor = UartCaptureProcessor()
    reference_store.append_uart_capture(
        reference_handle,
        event=event,
        result=reference_processor.process_event(event),
    )
    reference_result = reference_processor.flush_all()[0]
    admitted_uart_bytes = _evidence_bytes(reference_handle)
    reference_store.append_uart_processing_result(
        reference_handle,
        result=reference_result,
    )
    exact_budget = _evidence_bytes(reference_handle)
    assert exact_budget > admitted_uart_bytes

    exact_store = SessionStore(
        root=tmp_path / "exact",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=exact_budget,
    )
    exact_handle = exact_store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    exact_processor = UartCaptureProcessor()
    exact_store.append_uart_capture(
        exact_handle,
        event=event,
        result=exact_processor.process_event(event),
    )
    exact_store.append_uart_processing_result(
        exact_handle,
        result=exact_processor.flush_all()[0],
    )
    assert _evidence_bytes(exact_handle) == exact_budget
    assert exact_store.summarize_session(exact_handle.session_id).truncated is False

    rejected_store = SessionStore(
        root=tmp_path / "rejected",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=exact_budget - 1,
    )
    rejected_handle = rejected_store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    rejected_processor = UartCaptureProcessor()
    rejected_store.append_uart_capture(
        rejected_handle,
        event=event,
        result=rejected_processor.process_event(event),
    )

    with pytest.raises(EvidenceQuotaExceeded) as raised:
        rejected_store.append_uart_processing_result(
            rejected_handle,
            result=rejected_processor.flush_all()[0],
        )

    assert _evidence_bytes(rejected_handle) == admitted_uart_bytes
    assert rejected_handle.paths.hardware_events.read_bytes() == b""
    assert raised.value.truncation["rejected_unit_type"] == "session_event"
    assert raised.value.truncation["rejected_unit_evidence_bytes"] == (
        exact_budget - admitted_uart_bytes
    )
    summary = rejected_store.summarize_session(rejected_handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.line_processing.status == "limit_exceeded"


def test_failed_native_session_sanitizes_and_bounds_error_detail(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.fail_session(
        handle,
        end_reason="backend_error",
        error_code="hardware_fault",
        detail=("failed\n\t" + ("\u00e9" * 600)),
    )
    summary = store.summarize_session(handle.session_id)

    assert summary.state == "failed"
    assert summary.error is not None
    assert summary.error["code"] == "hardware_fault"
    assert summary.error["detail_truncated"] is True
    detail = summary.error["detail"]
    assert isinstance(detail, str)
    assert "\n" not in detail and "\t" not in detail
    assert len(detail.encode("utf-8")) <= 1024


def test_load_metadata_reads_metadata_json(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    metadata = store.load_metadata(handle.session_id)

    assert metadata["session_id"] == "20260714T123045Z-abc12345"
    assert metadata["command"] == "capture"


def test_record_segment_context_sets_unknown_provenance_once(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    context = SegmentContext(
        segment_id=0,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2040_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=8_500,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )

    store.record_segment_context(handle, context)
    store.record_segment_context(handle, context)

    metadata = store.load_metadata(handle.session_id)
    assert metadata["segments"][0]["timestamp"]["source_origin_us"] == 8_500  # type: ignore[index]

    conflicting = SegmentContext(
        segment_id=0,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2040_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=9_000,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )
    with pytest.raises(ValueError, match="cannot change"):
        store.record_segment_context(handle, conflicting)


def test_summarize_session_returns_compact_metadata_summary(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2040",
        baseline=True,
    )

    summary = store.summarize_session(handle.session_id)

    assert summary == SessionSummary(
        session_id="20260714T123045Z-abc12345",
        started_at="2026-07-14T12:30:45Z",
        command="boot-test --seconds 15",
        truncated=False,
        interrupted=False,
        resumed=False,
        overflow=False,
        baseline=True,
        firmware="0.1.0",
        device="dutchmate-rp2040",
        segment_count=1,
    )


def test_summarize_session_reflects_metadata_updates(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["interrupted"] = True
    metadata["resumed"] = True
    metadata["truncated"] = True
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
            segment_id=0,
            channel=0,
            timestamp_us=100,
            dropped_bytes=10,
        ),
    )

    summary = store.summarize_session(handle.session_id)

    assert summary.truncated is True
    assert summary.interrupted is True
    assert summary.resumed is True
    assert summary.overflow is True
    assert summary.segment_count == 2


def test_summarize_session_rejects_invalid_segments_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"] = "not a list"
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError):
        store.summarize_session(handle.session_id)


def test_summarize_session_rejects_invalid_required_metadata_type(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["overflow"] = "false"
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError):
        store.summarize_session(handle.session_id)


def test_create_session_defaults_optional_metadata_to_none_and_false(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(command="capture")

    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["firmware"] is None
    assert metadata["device"] is None
    assert metadata["baseline"] is False


def test_create_session_requires_command(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    with pytest.raises(ValueError):
        store.create_session(command="")


def test_create_session_fails_if_generated_session_id_already_exists(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    store.create_session(command="capture")

    with pytest.raises(FileExistsError):
        store.create_session(command="capture")


def test_append_uart_capture_preserves_raw_bytes_and_writes_uart_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=1234, data=b"BOOT_OK\n")
    result = processor.process_event(event)

    store.append_uart_capture(handle, event=event, result=result)

    assert handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    assert _read_jsonl(handle.paths.uart_events) == [
        {
            "type": "uart",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 1234,
            "channel": 0,
            "data_b64": "Qk9PVF9PSwo=",
            "text": "BOOT_OK\n",
        }
    ]


def test_append_uart_capture_appends_multiple_uart_events(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    first = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"one\n")
    second = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=200, data=b"two\n")

    store.append_uart_capture(handle, event=first, result=processor.process_event(first))
    store.append_uart_capture(handle, event=second, result=processor.process_event(second))

    assert handle.paths.uart_raw.read_bytes() == b"one\ntwo\n"
    assert [event["timestamp_us"] for event in _read_jsonl(handle.paths.uart_events)] == [100, 200]


def test_append_uart_capture_writes_detected_patterns(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(
        segment_id=0,
        channel=1,
        timestamp_us=500,
        data=b"ERROR: failed\n",
    )
    result = processor.process_event(event)

    store.append_uart_capture(
        handle,
        event=event,
        result=result,
    )

    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == [
        {
            "pattern": "ERROR",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 500,
            "channel": 1,
            "ingestion_index": 0,
            "line_index_in_event": 0,
            "line_start_ingestion_index": 0,
            "line_start_event_offset": 0,
            "line_end_ingestion_index": 0,
            "line_end_event_offset": 14,
            "total_line_bytes": 14,
            "match_start_byte": 0,
            "match_end_byte": 5,
            "match_excerpt": {
                "start_byte": 0,
                "end_byte": 14,
                "text": "ERROR: failed\n",
                "raw_b64": "RVJST1I6IGZhaWxlZAo=",
                "excerpt_truncated": False,
            },
        }
    ]


def test_append_uart_capture_leaves_detected_patterns_empty_when_no_match(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=500, data=b"idle\n")

    store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == []


def test_summary_selects_first_error_by_segment_then_ingestion_order(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"].append({**metadata["segments"][0], "segment_id": 1})
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")
    events = (
        UartReceiveEvent(
            segment_id=1,
            channel=0,
            timestamp_us=1,
            data=b"PANIC in later segment\n",
        ),
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=500,
            data=b"BOOT_OK\n",
        ),
        UartReceiveEvent(
            segment_id=0,
            channel=1,
            timestamp_us=999,
            data=b"prefix ERROR suffix\n",
        ),
        UartReceiveEvent(
            segment_id=0,
            channel=1,
            timestamp_us=2,
            data=b"ASSERT later event\n",
        ),
    )
    for event in events:
        store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    first_error = store.summarize_session(handle.session_id).first_error

    assert first_error is not None
    assert first_error.pattern == "ERROR"
    assert first_error.detected_pattern_index == 2
    assert (first_error.segment_id, first_error.timestamp_us, first_error.channel) == (
        0,
        999,
        1,
    )
    assert (first_error.ingestion_index, first_error.line_index_in_event) == (2, 0)
    assert (first_error.match_start_byte, first_error.match_end_byte) == (7, 12)
    assert first_error.match_excerpt.text == "prefix ERROR suffix\n"


def test_summary_returns_null_first_error_for_success_marker_only(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=1,
        data=b"BOOT_OK\n",
    )
    store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    assert store.summarize_session(handle.session_id).first_error is None


def test_detected_pattern_excerpt_is_bounded_and_contains_match(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    line_raw = (b"a" * 4990) + b"ERROR\n"
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=1,
        data=line_raw,
    )
    store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    first_error = store.summarize_session(handle.session_id).first_error

    assert first_error is not None
    excerpt = first_error.match_excerpt
    excerpt_raw = base64.b64decode(excerpt.raw_b64)
    assert len(excerpt_raw) == 4096
    assert excerpt_raw == line_raw[excerpt.start_byte : excerpt.end_byte]
    assert b"ERROR" in excerpt_raw
    assert excerpt.end_byte - excerpt.start_byte == 4096
    assert excerpt.excerpt_truncated is True


def test_oversized_line_updates_metadata_without_omitting_raw_evidence(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    chunks = (
        b"a" * 65536,
        b"x",
        b"ERROR\n",
    )
    for index, chunk in enumerate(chunks):
        event = UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=index + 1,
            data=chunk,
        )
        store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    summary = store.summarize_session(handle.session_id)

    assert handle.paths.uart_raw.read_bytes() == b"".join(chunks)
    assert summary.truncated is False
    assert summary.line_processing.status == "limit_exceeded"
    assert summary.line_processing.max_line_bytes == 65536
    assert summary.line_processing.oversized_line_count == 1
    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == []
    assert _read_jsonl(handle.paths.hardware_events) == [
        {
            "type": "line_limit_exceeded",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 3,
            "channel": 0,
            "ingestion_index": 2,
            "line_index_in_event": 0,
            "line_start_ingestion_index": 0,
            "line_start_event_offset": 0,
            "line_end_ingestion_index": 2,
            "line_end_event_offset": 6,
            "total_line_bytes": 65543,
            "terminated": True,
        }
    ]


def test_append_uart_capture_updates_segment_device_timestamps(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    first = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"one\n")
    second = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=250, data=b"two\n")

    store.append_uart_capture(handle, event=first, result=processor.process_event(first))
    store.append_uart_capture(handle, event=second, result=processor.process_event(second))

    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][0]
    assert segment["first_device_timestamp_us"] == 100
    assert segment["last_device_timestamp_us"] == 250


def test_append_uart_capture_can_write_nonzero_segment_and_epoch(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(segment_id=1, channel=0, timestamp_us=100, data=b"idle\n")
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

    store.append_uart_capture(
        handle,
        event=event,
        result=processor.process_event(event),
        timestamp_epoch=1,
    )

    event = _read_jsonl(handle.paths.uart_events)[0]
    segment = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["segments"][1]
    assert event["segment_id"] == 1
    assert event["timestamp_epoch"] == 1
    assert segment["first_device_timestamp_us"] == 100
    assert segment["last_device_timestamp_us"] == 100


def test_append_uart_capture_rejects_channel_mismatch(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"idle\n")
    result = UartCaptureResult(
        segment_id=0,
        channel=1,
        timestamp_us=100,
        lines=(),
        matches=(),
    )

    with pytest.raises(ValueError):
        store.append_uart_capture(handle, event=event, result=result)


def test_append_uart_capture_rejects_segment_mismatch(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"idle\n")
    result = UartCaptureResult(
        segment_id=1,
        channel=0,
        timestamp_us=100,
        lines=(),
        matches=(),
    )

    with pytest.raises(ValueError, match="segments"):
        store.append_uart_capture(handle, event=event, result=result)


def test_append_uart_capture_rejects_timestamp_mismatch(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"idle\n")
    result = UartCaptureResult(
        segment_id=0,
        channel=0,
        timestamp_us=200,
        lines=(),
        matches=(),
    )

    with pytest.raises(ValueError):
        store.append_uart_capture(handle, event=event, result=result)


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

    assert _read_jsonl(handle.paths.hardware_events) == [
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
    exact_budget = _evidence_bytes(reference_handle)

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
    assert _evidence_bytes(handle) == exact_budget
    assert metadata["storage"]["evidence_bytes_written"] == exact_budget  # type: ignore[index]
    assert metadata["state"] == "active"
    assert metadata["truncated"] is False
    assert _read_jsonl(handle.paths.hardware_events)[0]["type"] == "buffer_status"


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
    projected_bytes = _evidence_bytes(reference_handle)

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
    assert _evidence_bytes(handle) == 3
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


def test_append_buffer_overflow_can_write_nonzero_segment_and_epoch(tmp_path: Path) -> None:
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
        timestamp_epoch=1,
    )

    event = _read_jsonl(handle.paths.hardware_events)[0]
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
            timestamp_epoch=99,
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

    assert _read_jsonl(handle.paths.hardware_events) == [
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


def test_append_buffer_status_updates_backend_integrity_loss(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2040",
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


def test_append_buffer_status_can_write_nonzero_segment_and_epoch(tmp_path: Path) -> None:
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
        timestamp_epoch=1,
    )

    event = _read_jsonl(handle.paths.hardware_events)[0]
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
            timestamp_epoch=99,
        )

    assert handle.paths.hardware_events.read_text(encoding="utf-8") == ""
    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["overflow"] is False


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _evidence_bytes(handle: SessionHandle) -> int:
    return sum(
        path.stat().st_size
        for path in (
            handle.paths.uart_raw,
            handle.paths.uart_events,
            handle.paths.hardware_events,
            handle.paths.detected_patterns,
        )
    )
