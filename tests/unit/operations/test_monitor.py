"""Bounded Monitor operation contract tests."""

import pytest

from dutchmate_core.operations.monitor import (
    MonitorCondition,
    MonitorEvidence,
    MonitorMatcher,
    validate_monitor_request,
)
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES


@pytest.mark.parametrize("duration_s", [0.001, 300, 300.0])
def test_duration_monitor_accepts_positive_fraction_and_upper_bound(
    duration_s: float,
) -> None:
    request = validate_monitor_request(
        duration_s=duration_s,
        conditions=None,
        timeout_s=None,
    )

    assert request.mode == "duration"
    assert request.duration_s == float(duration_s)
    assert request.conditions == ()
    assert request.timeout_s is None


@pytest.mark.parametrize("duration_s", [True, 0, -0.1, 300.001, float("inf")])
def test_duration_monitor_rejects_invalid_bounds(duration_s: object) -> None:
    with pytest.raises(ValueError, match="duration"):
        validate_monitor_request(
            duration_s=duration_s,
            conditions=None,
            timeout_s=None,
        )


def test_monitor_requires_exactly_one_completion_mode() -> None:
    with pytest.raises(ValueError, match="exactly one"):
        validate_monitor_request(duration_s=None, conditions=None, timeout_s=None)
    with pytest.raises(ValueError, match="exactly one"):
        validate_monitor_request(
            duration_s=1.0,
            conditions=(MonitorCondition(pattern="READY"),),
            timeout_s=1.0,
        )


def test_condition_monitor_validates_and_preserves_request_order() -> None:
    request = validate_monitor_request(
        duration_s=None,
        conditions=(
            MonitorCondition(pattern="READY", name="ready"),
            MonitorCondition(pattern="ERROR"),
        ),
        timeout_s=12.5,
    )

    assert request.mode == "conditions"
    assert request.duration_s is None
    assert request.conditions == (
        MonitorCondition(pattern="READY", name="ready"),
        MonitorCondition(pattern="ERROR"),
    )
    assert request.timeout_s == 12.5


@pytest.mark.parametrize("name", ["", " ready", "ready ", "bad\u0000name", "x" * 65])
def test_condition_name_rejects_invalid_values(name: str) -> None:
    with pytest.raises(ValueError, match="condition name"):
        validate_monitor_request(
            duration_s=None,
            conditions=(MonitorCondition(pattern="READY", name=name),),
            timeout_s=1.0,
        )


def test_condition_monitor_rejects_more_than_eight_conditions() -> None:
    with pytest.raises(ValueError, match="1..8"):
        validate_monitor_request(
            duration_s=None,
            conditions=tuple(
                MonitorCondition(pattern=f"condition-{index}") for index in range(9)
            ),
            timeout_s=1.0,
        )


def _evidence(
    evidence_seq: int,
    data: bytes,
    *,
    session_id: str = "session-a",
    segment_id: int = 0,
    channel: int = 0,
) -> MonitorEvidence:
    return MonitorEvidence(
        session_id=session_id,
        evidence_seq=evidence_seq,
        segment_id=segment_id,
        timestamp_us=evidence_seq * 10,
        channel=channel,
        data=data,
    )


def test_requested_matcher_does_not_use_pre_cursor_partial_line() -> None:
    matcher = MonitorMatcher(
        (MonitorCondition(pattern="ADY"),),
        incomplete_channels=frozenset({("session-a", 0, 0)}),
    )

    assert matcher.process((_evidence(5, b"ADY\n"),)) is None
    match = matcher.process((_evidence(6, b"ADY\n"),))

    assert match is not None
    assert match.source_evidence_seq == 6
    assert match.match_start_byte == 0
    assert match.match_end_byte == 3


def test_requested_matcher_preserves_next_line_after_oversized_pre_cursor_line() -> None:
    matcher = MonitorMatcher(
        (MonitorCondition(pattern="READY"),),
        incomplete_channels=frozenset({("session-a", 0, 0)}),
    )
    discarded_continuation = b"x" * (MAX_UART_LINE_BYTES + 1) + b"\n"

    match = matcher.process(
        (_evidence(6, discarded_continuation + b"READY\n"),)
    )

    assert match is not None
    assert match.excerpt_raw == b"READY\n"
    assert match.line_start_event_offset == len(discarded_continuation)
    assert matcher.line_processing_limited is True


def test_requested_matcher_uses_offset_then_request_order_tie_break() -> None:
    matcher = MonitorMatcher(
        (
            MonitorCondition(pattern="READ", name="short"),
            MonitorCondition(pattern="READY", name="ready"),
            MonitorCondition(pattern="ERROR", name="error"),
        )
    )

    match = matcher.process((_evidence(7, b"READY ERROR\n"),))

    assert match is not None
    assert match.condition_index == 0
    assert match.condition == MonitorCondition(pattern="READ", name="short")
    assert match.match_start_byte == 0
    assert match.source_evidence_seq == 7


def test_requested_matcher_selects_earliest_completed_line() -> None:
    matcher = MonitorMatcher(
        (
            MonitorCondition(pattern="second"),
            MonitorCondition(pattern="first"),
        )
    )

    match = matcher.process(
        (
            _evidence(8, b"first\n"),
            _evidence(9, b"second\n"),
        )
    )

    assert match is not None
    assert match.condition.pattern == "first"
    assert match.source_evidence_seq == 8


def test_requested_matcher_excludes_oversized_physical_line() -> None:
    matcher = MonitorMatcher((MonitorCondition(pattern="READY"),))

    match = matcher.process(
        (_evidence(10, b"READY" + b"x" * MAX_UART_LINE_BYTES + b"\n"),)
    )

    assert match is None
    assert matcher.line_processing_limited is True
