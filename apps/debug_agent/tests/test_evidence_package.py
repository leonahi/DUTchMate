from __future__ import annotations

import json
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path

import pytest

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
from dutchmate_core.session_store.models import (
    BaselineError,
    SessionComparison,
    SessionHandle,
    SessionQueryError,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_debug_agent.evidence_package import build_session_evidence


def test_evidence_prioritizes_early_failure_patterns_and_boot_edges(tmp_path: Path) -> None:
    store, handle = _native_session(tmp_path)
    lines = ["BOOT_BEGIN\n", "ERROR early\n"]
    lines.extend(f"noise {index:03d}\n" for index in range(697))
    lines[150] = "BOOT_OK\n"
    lines.append("BOOT_END\n")
    _append_lines(store, handle, lines)
    store.complete_session(handle)

    package = build_session_evidence(store, handle.session_id)
    excerpt_text = [line.text for line in package.uart_excerpts]

    assert package.facts.first_error is not None
    assert package.limits.uart_lines == 300
    assert package.limits.uart_text_bytes == 65536
    assert len(excerpt_text) == 300
    assert excerpt_text[:2] == lines[:2]
    assert "BOOT_OK\n" in excerpt_text
    assert excerpt_text[-1] == "BOOT_END\n"
    assert package.omitted_uart_lines == len(lines) - 300
    assert package.context_truncated is True
    assert all(line.session_id == handle.session_id for line in package.uart_excerpts)
    assert all(line.segment_id == 0 and line.timestamp_us >= 0 for line in package.uart_excerpts)
    assert package.uart_text_bytes == sum(len(text.encode("utf-8")) for text in excerpt_text)
    assert any(
        line.pattern_indexes for line in package.uart_excerpts if line.text == "ERROR early\n"
    )
    assert any(line.pattern_indexes for line in package.uart_excerpts if line.text == "BOOT_OK\n")
    json.dumps(asdict(package))


def test_text_budget_never_expands_oversized_line_or_first_error_excerpt(tmp_path: Path) -> None:
    store, handle = _native_session(tmp_path)
    _append_lines(store, handle, ["ERROR " + "x" * 39000 + "\n", "y" * 39000 + "\n"])
    oversized = UartReceiveEvent(0, 99, 0, b"z" * (MAX_UART_LINE_BYTES + 1) + b"\n")
    store.append_uart_capture(
        handle,
        event=oversized,
        result=UartCaptureProcessor().process_event(oversized),
    )
    store.complete_session(handle)

    package = build_session_evidence(store, handle.session_id)

    assert len(package.uart_excerpts) == 1
    assert package.uart_excerpts[0].text.startswith("ERROR ")
    assert package.uart_text_bytes <= package.limits.uart_text_bytes
    assert package.omitted_uart_lines == 1
    assert package.facts.first_error is not None
    assert len(package.facts.first_error.match_excerpt.text.encode("utf-8")) <= 4096
    assert package.facts.line_processing.oversized_line_count == 1
    assert any(event.type == "line_limit_exceeded" for event in package.hardware_excerpts)
    assert "z" * 100 not in package.uart_excerpts[0].text


def test_hardware_cap_preserves_failed_and_unknown_tx_outcomes(tmp_path: Path) -> None:
    store, handle = _native_session(tmp_path)
    for index in range(102):
        store.append_buffer_status(
            handle,
            event=BufferStatusEvent(0, index, 32768, 0, 0, 0, 0),
        )
    store.append_uart_tx_attempt(
        handle,
        attempt_id="failed-tx",
        segment_id=0,
        attempted_at="2026-09-20T12:00:00Z",
        data=b"PING",
    )
    store.append_uart_tx_result(
        handle,
        attempt_id="failed-tx",
        segment_id=0,
        completed_at="2026-09-20T12:00:01Z",
        outcome="failed",
        error="timeout",
        bytes_accepted=2,
        timestamp_us=None,
        device_timestamp_us=None,
    )
    store.append_uart_tx_attempt(
        handle,
        attempt_id="unknown-tx",
        segment_id=0,
        attempted_at="2026-09-20T12:00:02Z",
        data=b"RESET",
    )
    store.append_uart_tx_attempt(
        handle,
        attempt_id="successful-tx",
        segment_id=0,
        attempted_at="2026-09-20T12:00:03Z",
        data=b"OK",
    )
    store.append_uart_tx_result(
        handle,
        attempt_id="successful-tx",
        segment_id=0,
        completed_at="2026-09-20T12:00:04Z",
        outcome="success",
        error=None,
        bytes_accepted=2,
        timestamp_us=None,
        device_timestamp_us=None,
    )
    store.complete_session(handle)

    package = build_session_evidence(store, handle.session_id)
    by_id = {outcome.attempt_id: outcome for outcome in package.tx_outcomes}
    event_ids = {event.record.get("attempt_id") for event in package.hardware_excerpts}

    assert len(package.hardware_excerpts) == 100
    assert package.omitted_hardware_events == 7
    assert package.context_truncated is True
    assert by_id["failed-tx"].status == "failed"
    assert by_id["failed-tx"].bytes_accepted == 2
    assert by_id["failed-tx"].payload_bytes == 4
    assert by_id["failed-tx"].partial_acceptance is True
    assert by_id["unknown-tx"].status == "unknown"
    assert package.successful_uart_tx_attempts == 1
    assert "successful-tx" not in by_id
    assert package.facts.unresolved_uart_tx_attempts == 1
    assert "failed-tx" in event_ids and "unknown-tx" in event_ids
    assert all("data_b64" not in event.record for event in package.hardware_excerpts)


def test_evidence_rejects_legacy_sessions(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    handle = store.create_session(command="capture", firmware="0.0.1", device="legacy")

    with pytest.raises(SessionQueryError) as raised:
        build_session_evidence(store, handle.session_id)

    assert raised.value.error == "unsupported_session_schema"


def test_active_session_without_concurrent_writes_has_no_omissions(tmp_path: Path) -> None:
    store, handle = _native_session(tmp_path)
    _append_lines(store, handle, ["READY\n"])

    package = build_session_evidence(store, handle.session_id)

    assert package.facts.state == "active"
    assert [line.text for line in package.uart_excerpts] == ["READY\n"]
    assert package.omitted_uart_lines == 0
    assert package.omitted_hardware_events == 0
    assert package.context_truncated is False


def test_rejects_inconsistent_uart_text_even_when_artifact_size_is_unchanged(
    tmp_path: Path,
) -> None:
    store, handle = _native_session(tmp_path)
    _append_lines(store, handle, ["HELLO\n"])
    store.complete_session(handle)
    original = handle.paths.uart_events.read_bytes()
    changed = original.replace(b"HELLO", b"WRONG")
    assert changed != original and len(changed) == len(original)
    handle.paths.uart_events.write_bytes(changed)

    with pytest.raises(SessionQueryError) as raised:
        build_session_evidence(store, handle.session_id)

    assert raised.value.error == "persistence_fault"
    assert "UART text disagrees" in str(raised.value)


def test_reconnect_keeps_partial_line_in_its_original_segment(tmp_path: Path) -> None:
    store, handle = _native_session(tmp_path)
    processor = UartCaptureProcessor()
    before = UartReceiveEvent(0, 10, 0, b"before-reconnect")
    store.append_uart_capture(handle, event=before, result=processor.process_event(before))
    store.record_backend_disconnect(handle, segment_id=0)
    assert store.resume_session(handle, backend_snapshot=_snapshot(1)) == 1
    after = UartReceiveEvent(1, 20, 0, b"after-reconnect\n")
    store.append_uart_capture(handle, event=after, result=processor.process_event(after))
    store.complete_session(handle)

    package = build_session_evidence(store, handle.session_id)

    assert [line.text for line in package.uart_excerpts] == [
        "before-reconnect",
        "after-reconnect\n",
    ]
    assert [(line.segment_id, line.partial) for line in package.uart_excerpts] == [
        (0, True),
        (1, False),
    ]


def test_completed_sessions_do_not_gain_a_heuristic_baseline(tmp_path: Path) -> None:
    store, earlier = _native_session(tmp_path, suffix="earlier")
    store.complete_session(earlier)
    store, subject = _native_session(tmp_path, suffix="subject")
    store.complete_session(subject)

    package = build_session_evidence(store, subject.session_id)

    assert package.baseline_context is None


def test_designated_baseline_adds_bounded_comparison_summary(tmp_path: Path) -> None:
    store, baseline = _native_session(tmp_path, suffix="baseline")
    _append_lines(store, baseline, ["READY\n", "BOOT_OK\n"])
    store.complete_session(baseline)
    store, subject = _native_session(tmp_path, suffix="subject")
    _append_lines(store, subject, ["READY\n", "ERROR\n"])
    store.complete_session(subject)
    store.mark_baseline(baseline.session_id)

    context = build_session_evidence(store, subject.session_id).baseline_context

    assert context is not None
    assert context.baseline_session_id == baseline.session_id
    assert context.comparison_available is True
    assert context.timing_comparable is True
    assert context.timing_incompatibility_reason is None
    assert tuple(asdict(count) for count in context.pattern_counts) == (
        {"type": "failure", "baseline_count": 0, "subject_count": 1, "delta": 1},
        {"type": "success", "baseline_count": 1, "subject_count": 0, "delta": -1},
    )
    assert context.line_changes_in_window == 2
    assert not hasattr(context, "line_changes")


def test_designated_baseline_preserves_incomparable_timing(tmp_path: Path) -> None:
    store, baseline = _native_session(tmp_path, suffix="baseline")
    _append_lines(store, baseline, ["READY\n"])
    store.complete_session(baseline)
    basic = replace(
        _snapshot(0),
        info=BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=1000,
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
    store, subject = _native_session(tmp_path, suffix="subject", snapshot=basic)
    _append_lines(store, subject, ["READY\n"])
    store.complete_session(subject)
    store.mark_baseline(baseline.session_id)

    context = build_session_evidence(store, subject.session_id).baseline_context

    assert context is not None
    assert context.baseline_session_id == baseline.session_id
    assert context.comparison_available is True
    assert context.timing_comparable is False
    assert context.timing_incompatibility_reason == "timestamp_provenance_mismatch"
    assert context.window_span_delta_us is None


def test_designated_baseline_reports_active_subject_as_unavailable(tmp_path: Path) -> None:
    store, baseline = _native_session(tmp_path, suffix="baseline")
    store.complete_session(baseline)
    store, subject = _native_session(tmp_path, suffix="subject")
    store.mark_baseline(baseline.session_id)

    context = build_session_evidence(store, subject.session_id).baseline_context

    assert context is not None
    assert context.baseline_session_id == baseline.session_id
    assert context.comparison_available is False
    assert context.unavailable_reason == "state_not_terminal"
    assert context.timing_comparable is None


def test_corrupt_designated_baseline_is_an_error_not_an_omission(tmp_path: Path) -> None:
    store, subject = _native_session(tmp_path)
    store.complete_session(subject)
    (tmp_path / "baseline.json").write_text("not JSON", encoding="utf-8")

    with pytest.raises(BaselineError) as raised:
        build_session_evidence(store, subject.session_id)
    assert raised.value.error == "persistence_fault"


def test_baseline_retargeted_during_assembly_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, first = _native_session(tmp_path, suffix="first")
    store.complete_session(first)
    store, second = _native_session(tmp_path, suffix="second")
    store.complete_session(second)
    store, subject = _native_session(tmp_path, suffix="subject")
    store.complete_session(subject)
    store.mark_baseline(first.session_id)
    compare = store.compare_session

    def compare_then_retarget(session_id: str) -> SessionComparison:
        result = compare(session_id)
        store.mark_baseline(second.session_id)
        return result

    monkeypatch.setattr(store, "compare_session", compare_then_retarget)

    with pytest.raises(BaselineError, match="changed during evidence assembly"):
        build_session_evidence(store, subject.session_id)


def _native_session(
    root: Path,
    *,
    suffix: str = "evidence",
    snapshot: BackendSnapshot | None = None,
) -> tuple[SessionStore, SessionHandle]:
    store = SessionStore(
        root=root,
        clock=lambda: datetime(2026, 9, 20, 12, tzinfo=timezone.utc),
        id_factory=lambda: suffix,
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=snapshot or _snapshot(0),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    return store, handle


def _snapshot(segment_id: int) -> BackendSnapshot:
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2350",
            firmware="0.1.0",
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
        ),
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=1000,
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


def _append_lines(store: SessionStore, handle: SessionHandle, lines: list[str]) -> None:
    processor = UartCaptureProcessor()
    captures = []
    for index in range(0, len(lines), 20):
        event = UartReceiveEvent(
            segment_id=0,
            timestamp_us=index + 1,
            channel=0,
            data="".join(lines[index : index + 20]).encode("utf-8"),
        )
        captures.append((event, processor.process_event(event)))
    store.append_uart_capture_batch(handle, captures=captures)
