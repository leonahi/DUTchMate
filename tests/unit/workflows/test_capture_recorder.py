import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    UartMessage,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import (
    CaptureRecorder,
    CaptureRecordResult,
    CaptureStreamRecorder,
)


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "capture01"


def test_start_creates_session_with_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    recorder = CaptureRecorder.start(
        session_store=store,
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2040",
    )

    assert recorder.session_id == "20260714T123045Z-capture01"
    metadata = json.loads(recorder.session_handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["command"] == "boot-test --seconds 15"
    assert metadata["firmware"] == "0.1.0"
    assert metadata["device"] == "dutchmate-rp2040"


def test_record_uart_message_processes_lines_patterns_and_session_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")
    message = UartMessage(channel=0, timestamp_us=100, data=b"BOOT_OK\n", text="BOOT_OK\n")

    result = recorder.record_message(message)

    assert result.message_type == "uart"
    assert [line.text for line in result.lines] == ["BOOT_OK\n"]
    assert [match.pattern for match in result.matches] == ["BOOT_OK"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    assert _read_jsonl(recorder.session_handle.paths.uart_events) == [
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
            "line_text": "BOOT_OK\n",
            "line_raw_b64": "Qk9PVF9PSwo=",
        }
    ]


def test_record_uart_message_buffers_split_pattern_across_messages(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    first = recorder.record_message(
        UartMessage(channel=0, timestamp_us=100, data=b"BOOT_", text="BOOT_")
    )
    second = recorder.record_message(
        UartMessage(channel=0, timestamp_us=200, data=b"OK\n", text="OK\n")
    )

    assert first == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        message_type="uart",
    )
    assert [line.text for line in second.lines] == ["BOOT_OK\n"]
    assert [match.pattern for match in second.matches] == ["BOOT_OK"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"
    event_timestamps = [
        event["timestamp_us"]
        for event in _read_jsonl(recorder.session_handle.paths.uart_events)
    ]
    assert event_timestamps == [100, 200]


def test_record_buffer_overflow_writes_hardware_event(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    result = recorder.record_message(
        BufferOverflowMessage(channel=0, timestamp_us=300, dropped_bytes=512)
    )

    assert result == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        message_type="buffer_overflow",
    )
    assert _read_jsonl(recorder.session_handle.paths.hardware_events) == [
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

    result = recorder.record_message(
        BufferStatusMessage(
            timestamp_us=400,
            uart_rx_size_bytes=32768,
            uart_rx_used_bytes=1200,
            uart_rx_high_water_bytes=8000,
            dropped_bytes_total=0,
            overflow_events=0,
        )
    )

    assert result == CaptureRecordResult(
        session_id="20260714T123045Z-capture01",
        message_type="buffer_status",
    )
    assert _read_jsonl(recorder.session_handle.paths.hardware_events) == [
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


def test_record_message_rejects_unsupported_message(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.record_message("not a capture message")  # type: ignore[arg-type]


def test_stream_recorder_records_complete_uart_ndjson(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"Qk9PVF9PSwo="}\n'
    )

    assert [result.message_type for result in results] == ["uart"]
    assert [line.text for line in results[0].lines] == ["BOOT_OK\n"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"


def test_stream_recorder_buffers_split_ndjson_until_complete(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    assert recorder.feed(b'{"type":"uart","channel":0,') == []
    assert recorder.pending_bytes == b'{"type":"uart","channel":0,'

    results = recorder.feed(b'"timestamp_us":100,"data_b64":"Qk9PVF8="}\n')

    assert [result.message_type for result in results] == ["uart"]
    assert recorder.pending_bytes == b""
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_"


def test_stream_recorder_records_multiple_capture_messages_from_one_chunk(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"WAo="}\n'
        b'{"type":"buffer_status","timestamp_us":200,"uart_rx_size_bytes":32768,'
        b'"uart_rx_used_bytes":10,"uart_rx_high_water_bytes":100,'
        b'"dropped_bytes_total":0,"overflow_events":0}\n'
        b'{"type":"buffer_overflow","channel":0,"timestamp_us":300,"dropped_bytes":64}\n'
    )

    assert [result.message_type for result in results] == [
        "uart",
        "buffer_status",
        "buffer_overflow",
    ]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"X\n"
    event_types = [
        event["type"] for event in _read_jsonl(recorder.session_handle.paths.hardware_events)
    ]
    assert event_types == ["buffer_status", "buffer_overflow"]


def test_stream_recorder_ignores_non_capture_messages(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
        b'"capabilities":[]}\n'
        b'{"ok":true,"timestamp_us":10}\n'
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"WAo="}\n'
    )

    assert [result.message_type for result in results] == ["uart"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"X\n"


def test_stream_recorder_requires_bytes(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.feed("not bytes")  # type: ignore[arg-type]


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
