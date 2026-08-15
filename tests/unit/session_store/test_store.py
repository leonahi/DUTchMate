import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.session_store.store import SessionHandle, SessionStore, SessionSummary
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "abc12345"


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


def test_load_metadata_reads_metadata_json(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    metadata = store.load_metadata(handle.session_id)

    assert metadata["session_id"] == "20260714T123045Z-abc12345"
    assert metadata["command"] == "capture"


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
            "line_text": "ERROR: failed\n",
            "line_raw_b64": "RVJST1I6IGZhaWxlZAo=",
        }
    ]


def test_append_uart_capture_leaves_detected_patterns_empty_when_no_match(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=500, data=b"idle\n")

    store.append_uart_capture(handle, event=event, result=processor.process_event(event))

    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == []


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
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
