"""Bounded comparison against the explicitly designated project baseline."""

from __future__ import annotations

import base64
import binascii
import hashlib
from collections import Counter
from pathlib import Path
from typing import Final

from dutchmate_core.diagnostics import project_diagnostic_detail
from dutchmate_core.session_store.baseline import read_baseline_pointer
from dutchmate_core.session_store.log_replay import replay_recent_logs
from dutchmate_core.session_store.models import (
    BaselineError,
    ComparisonSessionEvidence,
    LegacySessionDetail,
    LineCountComparison,
    NativeSessionDetail,
    PatternCountComparison,
    RecentLogLine,
    RecentLogs,
    SessionComparison,
    SessionComparisonError,
    SessionQueryError,
)
from dutchmate_core.session_store.retrieval import get_session_detail

COMPARISON_LINE_WINDOW: Final = 300
MAX_COMPARISON_LINE_CHANGES: Final = 50
_TIMESTAMP_IDENTITY_FIELDS: Final = (
    "source",
    "clock",
    "observation_point",
    "event_granularity",
)
_COMPARABLE_WORKFLOWS: Final = frozenset({"capture", "boot_test"})
_TERMINAL_STATES: Final = frozenset({"completed", "failed", "abandoned"})


def compare_session(root: Path, session_id: str) -> SessionComparison:
    """Compare one terminal capture or boot test with the current baseline."""

    try:
        pointer = read_baseline_pointer(root, operation="compare_session")
    except BaselineError as exc:
        raise SessionComparisonError(
            error="persistence_fault",
            session_id=exc.session_id,
            detail=str(exc),
        ) from exc
    if pointer is None:
        raise SessionComparisonError(
            error="not_found",
            session_id=session_id,
            reason="baseline_not_designated",
            detail="No project baseline is designated",
        )

    subject = _native_detail(root, session_id, pointer_target=False)
    _require_comparable_subject(subject)
    baseline = _native_detail(root, pointer.session_id, pointer_target=True)
    baseline_logs = _logs(root, pointer.session_id, pointer_target=True)
    subject_logs = _logs(root, session_id, pointer_target=False)

    pattern_counts = _compare_pattern_counts(baseline, subject)
    line_changes, omitted_line_changes = _compare_lines(baseline_logs, subject_logs)
    timing_reason = _timing_incompatibility_reason(baseline, subject)
    timing_comparable = timing_reason is None
    baseline_span = _window_span_us(baseline_logs) if timing_comparable else None
    subject_span = _window_span_us(subject_logs) if timing_comparable else None
    span_delta = (
        subject_span - baseline_span
        if baseline_span is not None and subject_span is not None
        else None
    )
    return SessionComparison(
        session_id=session_id,
        baseline_session_id=pointer.session_id,
        baseline_marked_at=pointer.marked_at,
        baseline=_evidence_summary(baseline, baseline_logs),
        subject=_evidence_summary(subject, subject_logs),
        pattern_counts=pattern_counts,
        line_window_limit=COMPARISON_LINE_WINDOW,
        line_changes=line_changes,
        omitted_line_changes=omitted_line_changes,
        timing_comparable=timing_comparable,
        timing_incompatibility_reason=timing_reason,
        baseline_window_span_us=baseline_span,
        subject_window_span_us=subject_span,
        window_span_delta_us=span_delta,
    )


def _native_detail(
    root: Path,
    session_id: str,
    *,
    pointer_target: bool,
) -> NativeSessionDetail:
    try:
        detail = get_session_detail(root, session_id)
    except SessionQueryError as exc:
        if pointer_target:
            raise SessionComparisonError(
                error="persistence_fault",
                session_id=session_id,
                detail=f"Baseline pointer target is invalid: {exc}",
            ) from exc
        raise SessionComparisonError(
            error=exc.error,
            session_id=session_id,
            detected_schema_version=exc.detected_schema_version,
            detail=str(exc),
        ) from exc
    if isinstance(detail, LegacySessionDetail):
        if pointer_target:
            raise SessionComparisonError(
                error="persistence_fault",
                session_id=session_id,
                detail="Baseline pointer target is not a native session",
            )
        raise SessionComparisonError(
            error="unsupported_session_schema",
            session_id=session_id,
            detected_schema_version=detail.summary.schema_version,
            detail="Only native schema-v1 sessions can be compared",
        )
    return detail


def _require_comparable_subject(detail: NativeSessionDetail) -> None:
    summary = detail.summary
    if summary.state not in _TERMINAL_STATES:
        raise SessionComparisonError(
            error="invalid_session_state",
            session_id=summary.session_id,
            reason="state_not_terminal",
            detail="Comparison subject must be terminal",
        )
    if summary.workflow not in _COMPARABLE_WORKFLOWS:
        raise SessionComparisonError(
            error="invalid_session_state",
            session_id=summary.session_id,
            reason="workflow_not_comparable",
            detail="Comparison subject must be a capture or boot-test session",
        )


def _logs(root: Path, session_id: str, *, pointer_target: bool) -> RecentLogs:
    try:
        return replay_recent_logs(
            root,
            session_id=session_id,
            lines=COMPARISON_LINE_WINDOW,
        )
    except SessionQueryError as exc:
        if pointer_target:
            raise SessionComparisonError(
                error="persistence_fault",
                session_id=session_id,
                detail=f"Baseline UART evidence is invalid: {exc}",
            ) from exc
        raise SessionComparisonError(
            error=exc.error,
            session_id=session_id,
            detected_schema_version=exc.detected_schema_version,
            detail=str(exc),
        ) from exc


def _compare_pattern_counts(
    baseline: NativeSessionDetail,
    subject: NativeSessionDetail,
) -> tuple[PatternCountComparison, ...]:
    baseline_counts = {item.type: item.count for item in baseline.pattern_counts}
    subject_counts = {item.type: item.count for item in subject.pattern_counts}
    return tuple(
        PatternCountComparison(
            type=classification,
            baseline_count=baseline_counts.get(classification, 0),
            subject_count=subject_counts.get(classification, 0),
            delta=(
                subject_counts.get(classification, 0)
                - baseline_counts.get(classification, 0)
            ),
        )
        for classification in sorted(baseline_counts.keys() | subject_counts.keys())
    )


def _compare_lines(
    baseline: RecentLogs,
    subject: RecentLogs,
) -> tuple[tuple[LineCountComparison, ...], int]:
    baseline_counts = Counter(
        (line.channel, line.line_raw_b64) for line in baseline.complete_lines
    )
    subject_counts = Counter(
        (line.channel, line.line_raw_b64) for line in subject.complete_lines
    )
    representatives = {
        (line.channel, line.line_raw_b64): line
        for line in (*baseline.complete_lines, *subject.complete_lines)
    }
    changes: list[LineCountComparison] = []
    for channel, raw_b64 in baseline_counts.keys() | subject_counts.keys():
        baseline_count = baseline_counts[(channel, raw_b64)]
        subject_count = subject_counts[(channel, raw_b64)]
        if baseline_count == subject_count:
            continue
        raw = _decode_line(raw_b64)
        line = representatives[(channel, raw_b64)]
        excerpt, excerpt_truncated = _line_excerpt(line)
        changes.append(
            LineCountComparison(
                channel=channel,
                line_sha256=hashlib.sha256(raw).hexdigest(),
                line_bytes=len(raw),
                text_excerpt=excerpt,
                excerpt_truncated=excerpt_truncated,
                baseline_count=baseline_count,
                subject_count=subject_count,
                delta=subject_count - baseline_count,
            )
        )
    changes.sort(key=lambda item: (-abs(item.delta), item.channel, item.line_sha256))
    omitted = max(0, len(changes) - MAX_COMPARISON_LINE_CHANGES)
    return tuple(changes[:MAX_COMPARISON_LINE_CHANGES]), omitted


def _decode_line(raw_b64: str) -> bytes:
    try:
        return base64.b64decode(raw_b64, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise SessionComparisonError(
            error="persistence_fault",
            detail="Replayed UART line contains invalid base64",
        ) from exc


def _line_excerpt(line: RecentLogLine) -> tuple[str, bool]:
    if not line.line_text:
        return "", False
    return project_diagnostic_detail(
        fallback_code="uart_line",
        detail=line.line_text,
    )


def _evidence_summary(
    detail: NativeSessionDetail,
    logs: RecentLogs,
) -> ComparisonSessionEvidence:
    summary = detail.summary
    return ComparisonSessionEvidence(
        session_id=summary.session_id,
        state=summary.state,
        workflow=summary.workflow,
        backend_mode=summary.backend_mode,
        integrity=summary.integrity,
        truncated=summary.truncated,
        interrupted=summary.interrupted,
        resumed=summary.resumed,
        segment_count=summary.segment_count,
        complete_lines_in_window=len(logs.complete_lines),
        omitted_complete_lines=logs.omitted_complete_lines,
        partial_lines_in_window=len(logs.partial_lines),
        omitted_partial_lines=logs.omitted_partial_lines,
        oversized_lines_in_window=len(logs.oversized_lines),
        omitted_oversized_lines=logs.omitted_oversized_lines,
    )


def _timing_incompatibility_reason(
    baseline: NativeSessionDetail,
    subject: NativeSessionDetail,
) -> str | None:
    if baseline.summary.interrupted:
        return "baseline_interrupted"
    if subject.summary.interrupted:
        return "subject_interrupted"
    if baseline.summary.segment_count != 1:
        return "baseline_multiple_segments"
    if subject.summary.segment_count != 1:
        return "subject_multiple_segments"
    baseline_timestamp = _timestamp_identity(baseline)
    subject_timestamp = _timestamp_identity(subject)
    if baseline_timestamp is None or subject_timestamp is None:
        return "timestamp_provenance_missing"
    if baseline_timestamp != subject_timestamp:
        return "timestamp_provenance_mismatch"
    return None


def _timestamp_identity(detail: NativeSessionDetail) -> tuple[object, ...] | None:
    if len(detail.segments) != 1:
        return None
    timestamp = detail.segments[0].get("timestamp")
    if not isinstance(timestamp, dict):
        return None
    if any(field not in timestamp for field in _TIMESTAMP_IDENTITY_FIELDS):
        return None
    return tuple(timestamp[field] for field in _TIMESTAMP_IDENTITY_FIELDS)


def _window_span_us(logs: RecentLogs) -> int | None:
    if not logs.complete_lines:
        return None
    timestamps = [line.timestamp_us for line in logs.complete_lines]
    return max(timestamps) - min(timestamps)
