"""Explicit project-baseline context for a bounded Debug Agent evidence package."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from dutchmate_core.session_store.models import (
    BaselineError,
    BaselinePointer,
    ComparisonSessionEvidence,
    PatternCountComparison,
    SessionComparison,
    SessionComparisonError,
)
from dutchmate_core.session_store.store import SessionStore


@dataclass(frozen=True, slots=True)
class BaselineComparisonSummary:
    """Bounded comparison facts without repeating UART line text."""

    baseline_session_id: str
    baseline_marked_at: str
    baseline: ComparisonSessionEvidence
    subject: ComparisonSessionEvidence
    pattern_counts: tuple[PatternCountComparison, ...]
    line_window_limit: int
    line_changes_in_window: int
    omitted_line_changes: int
    timing_comparable: bool
    timing_incompatibility_reason: str | None
    baseline_window_span_us: int | None
    subject_window_span_us: int | None
    window_span_delta_us: int | None
    comparison_available: Literal[True] = True


@dataclass(frozen=True, slots=True)
class BaselineComparisonUnavailable:
    """A valid baseline exists, but the subject cannot be compared yet."""

    baseline_session_id: str
    baseline_marked_at: str
    unavailable_reason: str
    timing_comparable: None = None
    comparison_available: Literal[False] = False


BaselineContext = BaselineComparisonSummary | BaselineComparisonUnavailable


def load_baseline_context(
    store: SessionStore,
    session_id: str,
    *,
    expected_baseline: bool,
) -> BaselineContext | None:
    """Use only the validated project pointer; never pick a baseline by recency."""

    pointer = store.read_baseline()
    if expected_baseline != (pointer is not None and pointer.session_id == session_id):
        raise _pointer_changed(session_id)
    if pointer is None:
        return None

    try:
        comparison = store.compare_session(session_id)
    except SessionComparisonError as exc:
        if exc.error != "invalid_session_state":
            raise
        context: BaselineContext = BaselineComparisonUnavailable(
            baseline_session_id=pointer.session_id,
            baseline_marked_at=pointer.marked_at,
            unavailable_reason=exc.reason or exc.error,
        )
    else:
        _require_same_pointer(comparison, pointer, session_id)
        context = _summarize(comparison)

    if store.read_baseline() != pointer:
        raise _pointer_changed(session_id)
    return context


def _require_same_pointer(
    comparison: SessionComparison,
    pointer: BaselinePointer,
    session_id: str,
) -> None:
    if (
        comparison.session_id != session_id
        or comparison.baseline_session_id != pointer.session_id
        or comparison.baseline_marked_at != pointer.marked_at
    ):
        raise _pointer_changed(session_id)


def _pointer_changed(session_id: str) -> BaselineError:
    return BaselineError(
        error="persistence_fault",
        operation="read_baseline",
        session_id=session_id,
        detail="Project baseline designation changed during evidence assembly",
    )


def _summarize(comparison: SessionComparison) -> BaselineComparisonSummary:
    return BaselineComparisonSummary(
        baseline_session_id=comparison.baseline_session_id,
        baseline_marked_at=comparison.baseline_marked_at,
        baseline=comparison.baseline,
        subject=comparison.subject,
        pattern_counts=comparison.pattern_counts,
        line_window_limit=comparison.line_window_limit,
        line_changes_in_window=len(comparison.line_changes),
        omitted_line_changes=comparison.omitted_line_changes,
        timing_comparable=comparison.timing_comparable,
        timing_incompatibility_reason=comparison.timing_incompatibility_reason,
        baseline_window_span_us=comparison.baseline_window_span_us,
        subject_window_span_us=comparison.subject_window_span_us,
        window_span_delta_us=comparison.window_span_delta_us,
    )
