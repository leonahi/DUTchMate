import json
from dataclasses import replace
from pathlib import Path

import pytest
from capture_test_support import enhanced_snapshot, fixed_clock, fixed_id, read_jsonl

from dutchmate_core.backends import (
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import (
    CaptureRecorder,
    CaptureRecordResult,
)


def test_start_creates_session_with_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    recorder = CaptureRecorder.start(
        session_store=store,
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2350",
    )

    assert recorder.session_id == "20260714T123045Z-capture01"
    metadata = json.loads(recorder.session_handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["command"] == "boot-test --seconds 15"
    assert metadata["firmware"] == "0.1.0"
    assert metadata["device"] == "dutchmate-rp2350"


def test_record_uart_event_processes_lines_patterns_and_session_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"BOOT_OK\n")

    result = recorder.record_event(event)

    assert result.event_type == "uart_receive"
    assert [line.text for line in result.lines] == ["BOOT_OK\n"]
    assert [match.pattern for match in result.matches] == ["BOOT_OK"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    assert read_jsonl(recorder.session_handle.paths.uart_events) == [
        {
            "type": "uart",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 100,
            "channel": 0,
            "data_b64": "Qk9PVF9PSwo=",
            "text": "BOOT_OK\n",
        }
    ]
    assert json.loads(recorder.session_handle.paths.detected_patterns.read_text()) == [
        {
            "pattern": "BOOT_OK",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 100,
            "channel": 0,
            "ingestion_index": 0,
            "line_index_in_event": 0,
            "line_start_ingestion_index": 0,
            "line_start_event_offset": 0,
            "line_end_ingestion_index": 0,
            "line_end_event_offset": 8,
            "total_line_bytes": 8,
            "match_start_byte": 0,
            "match_end_byte": 7,
            "match_excerpt": {
                "start_byte": 0,
                "end_byte": 8,
                "text": "BOOT_OK\n",
                "raw_b64": "Qk9PVF9PSwo=",
                "excerpt_truncated": False,
            },
        }
    ]


def test_finalize_persists_unterminated_oversized_line_descriptor(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")
    recorder.record_event(
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=1,
            data=b"a" * 65536,
        )
    )
    recorder.record_event(
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=2,
            data=b"x",
        )
    )

    recorder.finalize()

    assert store.summarize_session(recorder.session_id).line_processing.oversized_line_count == 1
    assert read_jsonl(recorder.session_handle.paths.hardware_events) == [
        {
            "type": "line_limit_exceeded",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 2,
            "channel": 0,
            "ingestion_index": 1,
            "line_index_in_event": 0,
            "line_start_ingestion_index": 0,
            "line_start_event_offset": 0,
            "line_end_ingestion_index": 1,
            "line_end_event_offset": 1,
            "total_line_bytes": 65537,
            "terminated": False,
        }
    ]
    assert json.loads(recorder.session_handle.paths.detected_patterns.read_text()) == []


def test_record_uart_event_buffers_split_pattern_across_events(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    first = recorder.record_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"BOOT_")
    )
    second = recorder.record_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=200, data=b"OK\n")
    )

    assert first == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        event_type="uart_receive",
    )
    assert [line.text for line in second.lines] == ["BOOT_OK\n"]
    assert [match.pattern for match in second.matches] == ["BOOT_OK"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    event_timestamps = [
        event["timestamp_us"] for event in read_jsonl(recorder.session_handle.paths.uart_events)
    ]
    assert event_timestamps == [100, 200]


def test_record_uart_events_falls_back_to_exact_ordered_quota_prefix(tmp_path: Path) -> None:
    events = (
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"one\n"),
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=200, data=b"two\n"),
    )
    reference_store = SessionStore(
        root=tmp_path / "reference",
        clock=fixed_clock,
        id_factory=fixed_id,
    )
    reference_recorder = CaptureRecorder.start(
        session_store=reference_store,
        command="capture",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    reference_recorder.record_event(events[0])
    first_event_budget = sum(
        path.stat().st_size
        for path in (
            reference_recorder.session_handle.paths.uart_raw,
            reference_recorder.session_handle.paths.uart_events,
            reference_recorder.session_handle.paths.hardware_events,
            reference_recorder.session_handle.paths.detected_patterns,
        )
    )
    reference_result = reference_recorder.record_event(events[1])
    assert reference_result.event_type == "uart_receive"

    store = SessionStore(
        root=tmp_path / "batch",
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=first_event_budget,
    )
    recorder = CaptureRecorder.start(
        session_store=store,
        command="capture",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    results = recorder.record_uart_events(events)

    assert [result.event_type for result in results] == ["uart_receive", "size_limit"]
    assert recorder.terminalized is True
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"one\n"
    uart_events = read_jsonl(recorder.session_handle.paths.uart_events)
    assert [event["timestamp_us"] for event in uart_events] == [100]
    summary = store.summarize_session(recorder.session_id)
    assert summary.truncated is True
    assert summary.truncation is not None
    assert summary.truncation["timestamp_us"] == 200


def test_record_buffer_overflow_writes_hardware_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    result = recorder.record_event(
        BufferOverflowEvent(
            segment_id=0,
            channel=0,
            timestamp_us=300,
            dropped_bytes=512,
        )
    )

    assert result == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        event_type="buffer_overflow",
    )
    assert read_jsonl(recorder.session_handle.paths.hardware_events) == [
        {
            "type": "buffer_overflow",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 300,
            "channel": 0,
            "dropped_bytes": 512,
        }
    ]
    metadata = json.loads(recorder.session_handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["overflow"] is True


def test_record_buffer_status_writes_hardware_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    result = recorder.record_event(
        BufferStatusEvent(
            segment_id=0,
            timestamp_us=400,
            size_bytes=32768,
            used_bytes=1200,
            high_water_bytes=8000,
            dropped_bytes_total=0,
            overflow_events=0,
        )
    )

    assert result == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        event_type="buffer_status",
    )
    assert read_jsonl(recorder.session_handle.paths.hardware_events) == [
        {
            "type": "buffer_status",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 400,
            "uart_rx_size_bytes": 32768,
            "uart_rx_used_bytes": 1200,
            "uart_rx_high_water_bytes": 8000,
            "dropped_bytes_total": 0,
            "overflow_events": 0,
        }
    ]


def test_prior_mcu_overflow_counters_do_not_mark_a_new_capture_lost(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(
        session_store=store,
        command="boot-test --seconds 15",
        backend_snapshot=enhanced_snapshot(),
    )

    for timestamp_us in (100, 200):
        recorder.record_event(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=timestamp_us,
                size_bytes=32768,
                used_bytes=0,
                high_water_bytes=6045,
                dropped_bytes_total=23663,
                overflow_events=6,
            )
        )

    summary = store.summarize_session(recorder.session_id)
    assert summary.overflow is False
    assert summary.integrity is not None
    assert summary.integrity.loss_status == "none_reported"
    assert summary.integrity.dropped_bytes == 0
    assert [
        event["dropped_bytes_total"]
        for event in read_jsonl(recorder.session_handle.paths.hardware_events)
    ] == [23663, 23663]


def test_status_only_loss_accumulates_across_reconnect_segments(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    snapshot = enhanced_snapshot()
    recorder = CaptureRecorder.start(
        session_store=store,
        command="capture --seconds 5",
        backend_snapshot=snapshot,
        workflow="capture",
        duration_s=5.0,
        reconnect_timeout_s=5.0,
    )

    def status(segment_id: int, timestamp_us: int, total: int) -> BufferStatusEvent:
        return BufferStatusEvent(
            segment_id=segment_id,
            timestamp_us=timestamp_us,
            size_bytes=32768,
            used_bytes=0,
            high_water_bytes=6045,
            dropped_bytes_total=total,
            overflow_events=(total - 23663) // 100 + 6,
        )

    recorder.record_event(status(0, 100, 23663))
    recorder.record_event(status(0, 200, 23763))
    assert recorder.record_backend_disconnect(0) == 1
    assert snapshot.segment is not None
    replacement = replace(
        snapshot,
        segment=replace(snapshot.segment, segment_id=1, timestamp=replace(
            snapshot.segment.timestamp, source_origin_us=2_000
        )),
    )
    assert recorder.resume_session(replacement) == 1
    recorder.record_event(status(1, 100, 23763))
    recorder.record_event(status(1, 200, 23863))

    summary = store.summarize_session(recorder.session_id)
    assert summary.integrity is not None
    assert summary.integrity.dropped_bytes == 200


def test_status_loss_after_first_explicit_overflow_adds_to_session_total(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(
        session_store=store, command="capture", backend_snapshot=enhanced_snapshot()
    )
    recorder.record_event(
        BufferOverflowEvent(segment_id=0, timestamp_us=100, channel=0, dropped_bytes=100)
    )
    recorder.record_event(
        BufferStatusEvent(
            segment_id=0,
            timestamp_us=200,
            size_bytes=32768,
            used_bytes=0,
            high_water_bytes=6045,
            dropped_bytes_total=23763,
            overflow_events=7,
        )
    )
    recorder.record_event(
        BufferStatusEvent(
            segment_id=0,
            timestamp_us=300,
            size_bytes=32768,
            used_bytes=0,
            high_water_bytes=6045,
            dropped_bytes_total=23813,
            overflow_events=8,
        )
    )

    summary = store.summarize_session(recorder.session_id)
    assert summary.integrity is not None
    assert summary.integrity.dropped_bytes == 150


def test_record_event_rejects_unsupported_value(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.record_event("not a capture event")  # type: ignore[arg-type]
