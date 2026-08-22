import base64
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

from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.session_store.store import (
    EvidenceQuotaExceeded,
    LineProcessing,
    SessionStore,
)
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult


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

    store.append_uart_capture(
        handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )

    metadata = store.load_metadata(handle.session_id)
    assert evidence_bytes(handle) == exact_budget
    assert metadata["storage"]["evidence_bytes_written"] == exact_budget  # type: ignore[index]
    assert metadata["truncated"] is False
    assert metadata["state"] == "active"
    uart_record = read_jsonl(handle.paths.uart_events)[0]
    pattern_record = json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8"))[0]
    assert uart_record["segment_id"] == 0
    assert pattern_record["segment_id"] == 0
    assert pattern_record["pattern"] == "BOOT_OK"
    assert "timestamp_epoch" not in uart_record
    assert "timestamp_epoch" not in pattern_record


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
        store.append_uart_capture(
            handle,
            event=event,
            result=UartCaptureProcessor().process_event(event),
        )

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    assert handle.paths.hardware_events.read_bytes() == b""
    assert handle.paths.detected_patterns.read_bytes() == b"[]\n"
    assert evidence_bytes(handle) == 3
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
    admitted_uart_bytes = evidence_bytes(reference_handle)
    reference_store.append_uart_processing_result(
        reference_handle,
        result=reference_result,
    )
    exact_budget = evidence_bytes(reference_handle)
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
    assert evidence_bytes(exact_handle) == exact_budget
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

    assert evidence_bytes(rejected_handle) == admitted_uart_bytes
    assert rejected_handle.paths.hardware_events.read_bytes() == b""
    assert raised.value.truncation["rejected_unit_type"] == "session_event"
    assert raised.value.truncation["rejected_unit_evidence_bytes"] == (
        exact_budget - admitted_uart_bytes
    )
    summary = rejected_store.summarize_session(rejected_handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.line_processing.status == "limit_exceeded"



def test_append_uart_capture_preserves_raw_bytes_and_writes_uart_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=1234, data=b"BOOT_OK\n")
    result = processor.process_event(event)

    store.append_uart_capture(handle, event=event, result=result)

    assert handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    assert read_jsonl(handle.paths.uart_events) == [
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
    assert [event["timestamp_us"] for event in read_jsonl(handle.paths.uart_events)] == [100, 200]


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
    assert read_jsonl(handle.paths.hardware_events) == [
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


def test_append_uart_capture_can_write_nonzero_segment(tmp_path: Path) -> None:
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
    )

    event = read_jsonl(handle.paths.uart_events)[0]
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
