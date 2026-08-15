import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendEvent,
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import (
    CaptureRecorder,
    CaptureRecordResult,
    run_transport_capture,
)
from dutchmate_core.workflows.enhanced_capture import CaptureStreamRecorder, run_mock_capture


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "capture01"


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeCaptureEventSource:
    def __init__(
        self,
        script: list[BackendEvent | None],
        *,
        clock: FakeMonotonicClock,
        read_duration_s: float = 0.1,
    ) -> None:
        self._script = script
        self._clock = clock
        self._read_duration_s = read_duration_s
        self.read_count = 0

    def read_event(self) -> BackendEvent | None:
        self.read_count += 1
        self._clock.advance(self._read_duration_s)
        if not self._script:
            return None
        return self._script.pop(0)


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


def test_record_uart_event_processes_lines_patterns_and_session_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"BOOT_OK\n")

    result = recorder.record_event(event)

    assert result.event_type == "uart_receive"
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
        event["timestamp_us"]
        for event in _read_jsonl(recorder.session_handle.paths.uart_events)
    ]
    assert event_timestamps == [100, 200]


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


def test_record_event_rejects_unsupported_value(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.record_event("not a capture event")  # type: ignore[arg-type]


def test_stream_recorder_records_complete_uart_ndjson(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"Qk9PVF9PSwo="}\n'
    )

    assert [result.event_type for result in results] == ["uart_receive"]
    assert [line.text for line in results[0].lines] == ["BOOT_OK\n"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"


def test_stream_recorder_buffers_split_ndjson_until_complete(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    assert recorder.feed(b'{"type":"uart","channel":0,') == []
    assert recorder.pending_bytes == b'{"type":"uart","channel":0,'

    results = recorder.feed(b'"timestamp_us":100,"data_b64":"Qk9PVF8="}\n')

    assert [result.event_type for result in results] == ["uart_receive"]
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

    assert [result.event_type for result in results] == [
        "uart_receive",
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

    assert [result.event_type for result in results] == ["uart_receive"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"X\n"


def test_stream_recorder_requires_bytes(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = CaptureStreamRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.feed("not bytes")  # type: ignore[arg-type]


def test_run_mock_capture_returns_final_session_summary(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_mock_capture(
        chunks=[
            b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
            b'"capabilities":[]}\n',
            b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"Qk9PVF9PSwo="}\n',
            b'{"type":"buffer_status","timestamp_us":200,"uart_rx_size_bytes":32768,'
            b'"uart_rx_used_bytes":10,"uart_rx_high_water_bytes":100,'
            b'"dropped_bytes_total":0,"overflow_events":0}\n',
        ],
        session_store=store,
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2040",
    )

    assert summary.session_id == "20260714T123045Z-capture01"
    assert summary.command == "capture"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2040"
    assert summary.overflow is False
    assert summary.segment_count == 1


def test_run_mock_capture_summary_reflects_overflow(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_mock_capture(
        chunks=[
            b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"WAo="}\n',
            b'{"type":"buffer_overflow","channel":0,"timestamp_us":200,"dropped_bytes":64}\n',
        ],
        session_store=store,
        command="capture",
    )

    assert summary.overflow is True


def test_run_mock_capture_persists_capture_evidence(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_mock_capture(
        chunks=[
            b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"RVJST1IK"}\n',
        ],
        session_store=store,
        command="capture",
    )
    session_root = tmp_path / summary.session_id

    assert (session_root / "uart_raw.log").read_bytes() == b"ERROR\n"
    assert json.loads((session_root / "detected_patterns.json").read_text()) == [
        {
            "pattern": "ERROR",
            "segment_id": 0,
            "timestamp_epoch": 0,
            "timestamp_us": 100,
            "channel": 0,
            "line_text": "ERROR\n",
            "line_raw_b64": "RVJST1IK",
        }
    ]


def test_run_transport_capture_records_capture_messages_until_deadline(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
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
            None,
        ],
        clock=clock,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_transport_capture(
        transport=transport,
        duration_s=0.6,
        session_store=store,
        command="capture --seconds 0.6",
        firmware="0.1.0",
        device="dutchmate-rp2040",
        monotonic_clock=clock,
    )

    assert summary.command == "capture --seconds 0.6"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2040"
    session_root = tmp_path / summary.session_id
    assert (session_root / "uart_raw.log").read_bytes() == b"BOOT_OK\n"
    assert [
        event["type"] for event in _read_jsonl(session_root / "hardware_events.jsonl")
    ] == ["buffer_status"]


def test_run_transport_capture_continues_after_read_timeout(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
        [
            None,
            UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"READY\n"),
        ],
        clock=clock,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_transport_capture(
        transport=transport,
        duration_s=0.4,
        session_store=store,
        command="capture",
        monotonic_clock=clock,
    )

    assert transport.read_count == 4
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"READY\n"


def test_run_transport_capture_does_not_record_event_after_deadline(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
        [UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"LATE\n")],
        clock=clock,
        read_duration_s=0.2,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_transport_capture(
        transport=transport,
        duration_s=0.1,
        session_store=store,
        command="capture",
        monotonic_clock=clock,
    )

    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b""


@pytest.mark.parametrize(
    "duration_s",
    [0.0, -1.0, 300.1, float("inf"), float("nan"), True],
)
def test_run_transport_capture_rejects_invalid_duration(
    tmp_path: Path,
    duration_s: float,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource([], clock=clock)
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    with pytest.raises(ValueError, match="positive finite"):
        run_transport_capture(
            transport=transport,
            duration_s=duration_s,
            session_store=store,
            command="capture",
            monotonic_clock=clock,
        )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line
    ]
