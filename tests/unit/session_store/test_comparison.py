from dataclasses import replace
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot

from dutchmate_core.backends import (
    BackendInfo,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
)
from dutchmate_core.session_store.models import (
    PatternCountComparison,
    SessionComparisonError,
)
from dutchmate_core.session_store.store import SessionHandle, SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def test_comparison_reports_bounded_line_pattern_and_timing_deltas(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, ["base1111", "subject1"])
    baseline = _capture_with_lines(
        store,
        (b"READY\n", b"BOOT_OK\n"),
        timestamps=(100, 200),
    )
    subject = _capture_with_lines(
        store,
        (b"READY\n", b"ERROR\n"),
        timestamps=(100, 260),
    )
    store.mark_baseline(baseline.session_id)

    result = store.compare_session(subject.session_id)

    assert result.session_id == subject.session_id
    assert result.baseline_session_id == baseline.session_id
    assert result.baseline.session_id == baseline.session_id
    assert result.subject.session_id == subject.session_id
    assert result.baseline.complete_lines_in_window == 2
    assert result.subject.complete_lines_in_window == 2
    assert result.pattern_counts == (
        _pattern("failure", baseline=0, subject=1),
        _pattern("success", baseline=1, subject=0),
    )
    assert {change.text_excerpt for change in result.line_changes} == {
        "BOOT_OK ",
        "ERROR ",
    }
    assert all(len(change.line_sha256) == 64 for change in result.line_changes)
    assert result.omitted_line_changes == 0
    assert result.timing_comparable is True
    assert result.timing_incompatibility_reason is None
    assert result.baseline_window_span_us == 100
    assert result.subject_window_span_us == 160
    assert result.window_span_delta_us == 60


def test_comparison_allows_cross_backend_logs_but_rejects_timing_mismatch(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, ["base1111", "subject1"])
    baseline = _capture_with_lines(store, (b"READY\n",))
    basic_snapshot = replace(
        enhanced_snapshot(),
        info=BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=1_000,
                observation_point="host_serial_read",
                event_granularity="uart_event",
            ),
        ),
        integrity=UartIntegrity(
            loss_status="not_observable",
            observation_scope=None,
            dropped_bytes=None,
        ),
    )
    subject = _capture_with_lines(store, (b"READY\n",), snapshot=basic_snapshot)
    store.mark_baseline(baseline.session_id)

    result = store.compare_session(subject.session_id)

    assert result.baseline.backend_mode == "enhanced"
    assert result.subject.backend_mode == "basic"
    assert result.line_changes == ()
    assert result.timing_comparable is False
    assert result.timing_incompatibility_reason == "timestamp_provenance_mismatch"
    assert result.baseline_window_span_us is None
    assert result.subject_window_span_us is None
    assert result.window_span_delta_us is None


def test_comparison_requires_designation_and_comparable_subject(tmp_path: Path) -> None:
    store = _store(tmp_path, ["base1111", "active11", "legacy11", "waiting1"])
    baseline = _capture_with_lines(store, ())
    active = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    legacy = store.create_session(command="capture")
    wait = store.create_session(
        command="wait-pattern READY --timeout 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="wait_pattern",
        reconnect_timeout_s=5.0,
        wait_pattern="READY",
        timeout_s=1.0,
    )
    store.complete_wait_pattern(wait, matched=False, detected_pattern_index=None)

    with pytest.raises(SessionComparisonError) as no_baseline:
        store.compare_session(active.session_id)
    assert no_baseline.value.error == "not_found"
    assert no_baseline.value.reason == "baseline_not_designated"

    store.mark_baseline(baseline.session_id)
    with pytest.raises(SessionComparisonError) as active_error:
        store.compare_session(active.session_id)
    with pytest.raises(SessionComparisonError) as legacy_error:
        store.compare_session(legacy.session_id)
    with pytest.raises(SessionComparisonError) as workflow_error:
        store.compare_session(wait.session_id)

    assert active_error.value.reason == "state_not_terminal"
    assert legacy_error.value.error == "unsupported_session_schema"
    assert legacy_error.value.detected_schema_version == 0
    assert workflow_error.value.reason == "workflow_not_comparable"


def test_failed_subject_is_comparable_without_becoming_baseline_eligible(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, ["base1111", "subject1"])
    baseline = _capture_with_lines(store, (b"READY\n",))
    subject = _active_capture(store)
    store.fail_session(
        subject,
        end_reason="backend_error",
        error_code="hardware_fault",
        detail="device disconnected",
    )
    store.mark_baseline(baseline.session_id)

    result = store.compare_session(subject.session_id)

    assert result.subject.state == "failed"
    assert result.subject.workflow == "capture"


def test_corrupt_baseline_pointer_is_a_comparison_persistence_fault(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path, ["subject1"])
    subject = _capture_with_lines(store, ())
    (tmp_path / "baseline.json").write_text("not JSON", encoding="utf-8")

    with pytest.raises(SessionComparisonError) as error:
        store.compare_session(subject.session_id)

    assert error.value.error == "persistence_fault"
    assert error.value.operation == "compare_session"


def _store(root: Path, suffixes: list[str]) -> SessionStore:
    ticks = count()
    suffix_iter = iter(suffixes)
    started = datetime(2026, 8, 21, 22, 0, tzinfo=timezone.utc)
    return SessionStore(
        root=root,
        clock=lambda: started + timedelta(seconds=next(ticks)),
        id_factory=lambda: next(suffix_iter),
    )


def _active_capture(
    store: SessionStore,
    *,
    snapshot: BackendSnapshot | None = None,
) -> SessionHandle:
    return store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot() if snapshot is None else snapshot,
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )


def _capture_with_lines(
    store: SessionStore,
    lines: tuple[bytes, ...],
    *,
    timestamps: tuple[int, ...] | None = None,
    snapshot: BackendSnapshot | None = None,
) -> SessionHandle:
    handle = _active_capture(store, snapshot=snapshot)
    processor = UartCaptureProcessor()
    event_timestamps = timestamps or tuple(range(100, 100 + len(lines)))
    for timestamp_us, data in zip(event_timestamps, lines, strict=True):
        event = UartReceiveEvent(
            segment_id=0,
            timestamp_us=timestamp_us,
            channel=0,
            data=data,
        )
        store.append_uart_capture(
            handle,
            event=event,
            result=processor.process_event(event),
        )
    store.complete_session(handle)
    return handle


def _pattern(
    kind: str,
    *,
    baseline: int,
    subject: int,
) -> PatternCountComparison:
    return PatternCountComparison(
        type=kind,
        baseline_count=baseline,
        subject_count=subject,
        delta=subject - baseline,
    )
