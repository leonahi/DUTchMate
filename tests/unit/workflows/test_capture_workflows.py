import json
from pathlib import Path

import pytest
from capture_test_support import (
    FakeCaptureEventSource,
    FakeMonotonicClock,
    fixed_clock,
    fixed_id,
    read_jsonl,
)

from dutchmate_core.backends import (
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import CaptureWorkflow
from dutchmate_core.workflows.enhanced_capture import CaptureStreamRecorder, run_mock_capture


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
        event["type"] for event in read_jsonl(recorder.session_handle.paths.hardware_events)
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
            "ingestion_index": 0,
            "line_index_in_event": 0,
            "line_start_ingestion_index": 0,
            "line_start_event_offset": 0,
            "line_end_ingestion_index": 0,
            "line_end_event_offset": 6,
            "total_line_bytes": 6,
            "match_start_byte": 0,
            "match_end_byte": 5,
            "match_excerpt": {
                "start_byte": 0,
                "end_byte": 6,
                "text": "ERROR\n",
                "raw_b64": "RVJST1IK",
                "excerpt_truncated": False,
            },
        }
    ]


def test_capture_workflow_records_capture_messages_until_deadline(
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

    summary = CaptureWorkflow(session_store=store).run(
        source=transport,
        duration_s=0.6,
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
    assert [event["type"] for event in read_jsonl(session_root / "hardware_events.jsonl")] == [
        "buffer_status"
    ]


def test_transport_capture_persists_source_segment_context_before_event(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
        [UartReceiveEvent(segment_id=0, channel=0, timestamp_us=0, data=b"READY\n")],
        clock=clock,
    )
    transport.segment = SegmentContext(
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
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = CaptureWorkflow(session_store=store).run(
        source=transport,
        duration_s=0.3,
        command="capture",
        monotonic_clock=clock,
    )

    assert summary.segment_contexts == (transport.segment,)
    metadata = store.load_metadata(summary.session_id)
    assert metadata["segments"][0]["timestamp"]["source_origin_us"] == 8_500  # type: ignore[index]


def test_capture_workflow_continues_after_read_timeout(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
        [
            None,
            UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"READY\n"),
        ],
        clock=clock,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = CaptureWorkflow(session_store=store).run(
        source=transport,
        duration_s=0.4,
        command="capture",
        monotonic_clock=clock,
    )

    assert transport.read_count == 4
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"READY\n"


def test_capture_workflow_does_not_record_event_after_deadline(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource(
        [UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"LATE\n")],
        clock=clock,
        read_duration_s=0.2,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = CaptureWorkflow(session_store=store).run(
        source=transport,
        duration_s=0.1,
        command="capture",
        monotonic_clock=clock,
    )

    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b""


@pytest.mark.parametrize(
    "duration_s",
    [0.0, -1.0, 300.1, float("inf"), float("nan"), True],
)
def test_capture_workflow_rejects_invalid_duration(
    tmp_path: Path,
    duration_s: float,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeCaptureEventSource([], clock=clock)
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    with pytest.raises(ValueError, match="positive finite"):
        CaptureWorkflow(session_store=store).run(
            source=transport,
            duration_s=duration_s,
            command="capture",
            monotonic_clock=clock,
        )
