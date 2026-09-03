import json
from pathlib import Path

import pytest
from capture_test_support import (
    EnhancedCaptureFixtureRecorder,
    FakeCaptureEventSource,
    FakeMonotonicClock,
    LifecycleCaptureEventSource,
    fixed_clock,
    fixed_id,
    read_jsonl,
    run_enhanced_capture_fixture,
)

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import CaptureWorkflow
from dutchmate_core.workflows.device_actions import DeviceActionResult


def test_stream_recorder_records_complete_uart_ndjson(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = EnhancedCaptureFixtureRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"Qk9PVF9PSwo="}\n'
    )

    assert [result.event_type for result in results] == ["uart_receive"]
    assert [line.text for line in results[0].lines] == ["BOOT_OK\n"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"BOOT_OK\n"


def test_stream_recorder_buffers_split_ndjson_until_complete(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = EnhancedCaptureFixtureRecorder.start(session_store=store, command="capture")

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
    recorder = EnhancedCaptureFixtureRecorder.start(session_store=store, command="capture")

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
    recorder = EnhancedCaptureFixtureRecorder.start(session_store=store, command="capture")

    results = recorder.feed(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350",'
        b'"capabilities":[]}\n'
        b'{"ok":true,"timestamp_us":10}\n'
        b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"WAo="}\n'
    )

    assert [result.event_type for result in results] == ["uart_receive"]
    assert recorder.session_handle.paths.uart_raw.read_bytes() == b"X\n"


def test_stream_recorder_requires_bytes(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    recorder = EnhancedCaptureFixtureRecorder.start(session_store=store, command="capture")

    with pytest.raises(TypeError):
        recorder.feed("not bytes")  # type: ignore[arg-type]


def test_enhanced_capture_fixture_returns_final_session_summary(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_enhanced_capture_fixture(
        chunks=[
            b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350",'
            b'"capabilities":[]}\n',
            b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"Qk9PVF9PSwo="}\n',
            b'{"type":"buffer_status","timestamp_us":200,"uart_rx_size_bytes":32768,'
            b'"uart_rx_used_bytes":10,"uart_rx_high_water_bytes":100,'
            b'"dropped_bytes_total":0,"overflow_events":0}\n',
        ],
        session_store=store,
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2350",
    )

    assert summary.session_id == "20260714T123045Z-capture01"
    assert summary.command == "capture"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2350"
    assert summary.overflow is False
    assert summary.segment_count == 1


def test_enhanced_capture_fixture_summary_reflects_overflow(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_enhanced_capture_fixture(
        chunks=[
            b'{"type":"uart","channel":0,"timestamp_us":100,"data_b64":"WAo="}\n',
            b'{"type":"buffer_overflow","channel":0,"timestamp_us":200,"dropped_bytes":64}\n',
        ],
        session_store=store,
        command="capture",
    )

    assert summary.overflow is True


def test_enhanced_capture_fixture_persists_capture_evidence(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    summary = run_enhanced_capture_fixture(
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
        device="dutchmate-rp2350",
        monotonic_clock=clock,
    )

    assert summary.command == "capture --seconds 0.6"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2350"
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
            clock="rp2350_timer",
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


def test_capture_activates_cursor_after_session_creation_before_callbacks(
    tmp_path: Path,
) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureEventSource(
        [None],
        clock=clock,
        trace=trace,
        session_exists=lambda: any(tmp_path.iterdir()),
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=0.1,
        command="capture",
        monotonic_clock=clock,
        on_session_started=lambda _session_id: trace.append("callback"),
    )

    assert trace[0:2] == ["begin", "callback"]
    assert trace[-1] == "end"
    assert trace.index("begin") < trace.index("read")


def test_capture_ends_cursor_when_session_started_callback_fails(tmp_path: Path) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureEventSource(
        [],
        clock=clock,
        trace=trace,
        session_exists=lambda: any(tmp_path.iterdir()),
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    with pytest.raises(RuntimeError, match="callback failed"):
        CaptureWorkflow(session_store=store).run(
            source=source,
            duration_s=0.1,
            command="capture",
            monotonic_clock=clock,
            backend_snapshot=_native_snapshot(),
            on_session_started=lambda _session_id: _failing_session_callback(trace),
        )

    summary = store.summarize_session("20260714T123045Z-capture01")
    assert summary.state == "failed"
    assert trace == ["begin", "callback", "end"]


def test_capture_activates_cursor_before_boot_action_and_first_read(tmp_path: Path) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureEventSource(
        [None],
        clock=clock,
        trace=trace,
        session_exists=lambda: any(tmp_path.iterdir()),
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=0.1,
        command="boot-test",
        monotonic_clock=clock,
        backend_snapshot=_native_snapshot(),
        on_session_started=lambda _session_id: trace.append("callback"),
        start_action=lambda: _start_action(trace),
    )

    assert trace.index("begin") < trace.index("callback")
    assert trace.index("callback") < trace.index("start_action")
    assert trace.index("start_action") < trace.index("read")
    assert trace[-1] == "end"


def test_capture_does_not_activate_cursor_when_session_creation_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trace: list[str] = []
    clock = FakeMonotonicClock()
    source = LifecycleCaptureEventSource(
        [],
        clock=clock,
        trace=trace,
        session_exists=lambda: any(tmp_path.iterdir()),
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    def fail_create_session(**_kwargs: object) -> None:
        raise SessionPersistenceError(
            operation="create",
            path=tmp_path / "metadata.json",
            detail="simulated session creation failure",
        )

    monkeypatch.setattr(store, "create_session", fail_create_session)

    with pytest.raises(SessionPersistenceError, match="simulated session creation failure"):
        CaptureWorkflow(session_store=store).run(
            source=source,
            duration_s=0.1,
            command="capture",
            monotonic_clock=clock,
        )

    assert trace == []


def _start_action(trace: list[str]) -> DeviceActionResult:
    trace.append("start_action")
    return DeviceActionResult(
        action="reset",
        pulse_ms=100,
        performed_at="2026-07-14T12:30:45Z",
    )


def _failing_session_callback(trace: list[str]) -> None:
    trace.append("callback")
    raise RuntimeError("callback failed")


def _native_snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2350",
            firmware="0.1.0",
            capabilities=frozenset({"uart_receive"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
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
