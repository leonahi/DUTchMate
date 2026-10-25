"""Monitor request validation and operation-local matching models."""

from __future__ import annotations

import unicodedata
from base64 import b64encode
from collections.abc import Sequence
from dataclasses import dataclass
from threading import Event
from typing import Literal, Protocol

from dutchmate_core.backends import SegmentContext, UartIntegrity
from dutchmate_core.uart_capture.line_buffer import (
    MAX_UART_LINE_BYTES,
    UartLine,
    UartLineBuffer,
)
from dutchmate_core.validation import (
    validate_capture_duration,
    validate_wait_pattern,
    validate_wait_timeout,
)

MAX_MONITOR_CONDITIONS = 8
MAX_MONITOR_CONDITION_NAME_BYTES = 64
MAX_MONITOR_MATCH_EXCERPT_BYTES = 4096


@dataclass(frozen=True, slots=True)
class MonitorCondition:
    """One case-sensitive literal completion condition."""

    pattern: str
    name: str | None = None


@dataclass(frozen=True, slots=True)
class MonitorRequest:
    """One validated finite Monitor completion request."""

    mode: Literal["duration", "conditions"]
    duration_s: float | None
    conditions: tuple[MonitorCondition, ...]
    timeout_s: float | None


@dataclass(frozen=True, slots=True)
class MonitorEvidence:
    """One durable UART evidence unit eligible for operation-local matching."""

    session_id: str
    evidence_seq: int
    segment_id: int
    timestamp_us: int
    channel: int
    data: bytes


@dataclass(frozen=True, slots=True)
class MonitorMatch:
    """Deterministic requested-condition match with exact raw coordinates."""

    condition_index: int
    condition: MonitorCondition
    session_id: str
    source_evidence_seq: int
    segment_id: int
    timestamp_us: int
    channel: int
    line_start_evidence_seq: int
    line_start_event_offset: int
    line_end_evidence_seq: int
    line_end_event_offset: int
    total_line_bytes: int
    match_start_byte: int
    match_end_byte: int
    excerpt_start_byte: int
    excerpt_end_byte: int
    excerpt_raw: bytes
    excerpt_text: str
    excerpt_truncated: bool

    def persistence_projection(self) -> dict[str, object]:
        """Return the bounded schema-v2 terminal-record representation."""

        return {
            "condition_index": self.condition_index,
            "condition": {
                "pattern": self.condition.pattern,
                "name": self.condition.name,
            },
            "source": {
                "session_id": self.session_id,
                "evidence_seq": self.source_evidence_seq,
                "segment_id": self.segment_id,
                "timestamp_us": self.timestamp_us,
                "channel": self.channel,
            },
            "line": {
                "start_evidence_seq": self.line_start_evidence_seq,
                "start_event_offset": self.line_start_event_offset,
                "end_evidence_seq": self.line_end_evidence_seq,
                "end_event_offset": self.line_end_event_offset,
                "total_bytes": self.total_line_bytes,
            },
            "match_start_byte": self.match_start_byte,
            "match_end_byte": self.match_end_byte,
            "excerpt": {
                "start_byte": self.excerpt_start_byte,
                "end_byte": self.excerpt_end_byte,
                "raw_b64": b64encode(self.excerpt_raw).decode("ascii"),
                "text": self.excerpt_text,
                "truncated": self.excerpt_truncated,
            },
        }


@dataclass(frozen=True, slots=True)
class EvidenceCursor:
    """Internal precise position in schema-v2 durable evidence."""

    session_id: str
    next_evidence_seq: int


@dataclass(frozen=True, slots=True)
class EvidenceRange:
    """One half-open session-local portion of an operation window."""

    session_id: str
    start_evidence_seq: int
    end_evidence_seq_exclusive: int


class MonitorEvidenceReader(Protocol):
    """Operation-local incremental reader over newly admitted UART evidence."""

    def read_to(self, end: EvidenceCursor) -> tuple[MonitorEvidence, ...]: ...

    def close(self) -> None:
        """Release the bounded retention lease held for this operation."""

        ...


@dataclass(frozen=True, slots=True)
class MonitorTimestampProvenance:
    """Timestamp provenance for one session-local segment in an operation range."""

    session_id: str
    segment: SegmentContext


MonitorOutcome = Literal[
    "elapsed",
    "matched",
    "timeout",
    "disconnected",
    "released",
    "cancelled",
    "error",
]


@dataclass(frozen=True, slots=True)
class MonitorResult:
    """Terminal durable result for one bounded Monitor operation."""

    operation_id: str
    outcome: MonitorOutcome
    mode: Literal["duration", "conditions"]
    duration_s: float | None
    conditions: tuple[MonitorCondition, ...]
    timeout_s: float | None
    start_cursor: EvidenceCursor
    end_cursor: EvidenceCursor
    evidence_ranges: tuple[EvidenceRange, ...]
    match: MonitorMatch | None
    line_processing_limited: bool
    integrity: UartIntegrity | None
    timestamp_provenance: tuple[MonitorTimestampProvenance, ...]


@dataclass(frozen=True, slots=True)
class ActiveMonitorSummary:
    """Bounded status projection for one currently running Monitor."""

    operation_id: str
    mode: Literal["duration", "conditions"]
    deadline_remaining_s: float
    operation_type: Literal["monitor", "interact"] = "monitor"


@dataclass(frozen=True, slots=True)
class ActiveMonitor:
    """Runtime-owned cancellation and completion state."""

    operation_id: str
    mode: Literal["duration", "conditions"]
    deadline: float
    cancellation: Event
    completed: Event
    operation_type: Literal["monitor", "interact"] = "monitor"


class MonitorMatcher:
    """Match requested literals without reading pre-cursor line state."""

    def __init__(
        self,
        conditions: Sequence[MonitorCondition],
        *,
        incomplete_channels: frozenset[tuple[str, int, int]] = frozenset(),
    ) -> None:
        if not conditions:
            raise ValueError("Monitor matcher requires at least one condition")
        self._conditions = tuple(conditions)
        self._buffers: dict[tuple[str, int, int], UartLineBuffer] = {}
        self._discard_first_line = set(incomplete_channels)
        self._discarded_byte_counts: dict[tuple[str, int, int], int] = {}
        self._line_processing_limited = False

    @property
    def line_processing_limited(self) -> bool:
        """Whether an eligible physical line exceeded the derived line bound."""

        return self._line_processing_limited

    def process(self, evidence: Sequence[MonitorEvidence]) -> MonitorMatch | None:
        """Return the deterministic first match from ordered durable UART evidence."""

        for event in evidence:
            key = (event.session_id, event.segment_id, event.channel)
            data = event.data
            event_offset_base = 0
            if key in self._discard_first_line:
                newline_offset = data.find(b"\n")
                discarded_bytes = (
                    len(data) if newline_offset < 0 else newline_offset + 1
                )
                discarded_total = (
                    self._discarded_byte_counts.get(key, 0) + discarded_bytes
                )
                if discarded_total > MAX_UART_LINE_BYTES:
                    self._line_processing_limited = True
                if newline_offset < 0:
                    self._discarded_byte_counts[key] = discarded_total
                    continue
                self._discard_first_line.remove(key)
                self._discarded_byte_counts.pop(key, None)
                event_offset_base = discarded_bytes
                data = data[discarded_bytes:]
                if not data:
                    continue
            buffer = self._buffers.setdefault(key, UartLineBuffer())
            result = buffer.feed_result(
                data,
                ingestion_index=event.evidence_seq,
                timestamp_us=event.timestamp_us,
                event_offset_base=event_offset_base,
            )
            lines = result.lines
            if result.newly_oversized_line_count:
                self._line_processing_limited = True
            for line in lines:
                match = self._match_line(event, line)
                if match is not None:
                    return match
        return None

    def _match_line(
        self,
        event: MonitorEvidence,
        line: UartLine,
    ) -> MonitorMatch | None:
        candidates: list[tuple[int, int, int]] = []
        for index, condition in enumerate(self._conditions):
            encoded = condition.pattern.encode("utf-8")
            offset = line.raw.find(encoded)
            if offset >= 0:
                candidates.append((offset, index, len(encoded)))
        if not candidates:
            return None
        match_start, condition_index, pattern_bytes = min(candidates)
        match_end = match_start + pattern_bytes
        excerpt_start = min(
            match_start,
            max(0, len(line.raw) - MAX_MONITOR_MATCH_EXCERPT_BYTES),
        )
        excerpt_end = min(
            len(line.raw),
            excerpt_start + MAX_MONITOR_MATCH_EXCERPT_BYTES,
        )
        excerpt = line.raw[excerpt_start:excerpt_end]
        return MonitorMatch(
            condition_index=condition_index,
            condition=self._conditions[condition_index],
            session_id=event.session_id,
            source_evidence_seq=event.evidence_seq,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
            channel=event.channel,
            line_start_evidence_seq=_required_coordinate(
                line.start_ingestion_index,
                "line start evidence sequence",
            ),
            line_start_event_offset=_required_coordinate(
                line.start_event_offset,
                "line start event offset",
            ),
            line_end_evidence_seq=_required_coordinate(
                line.end_ingestion_index,
                "line end evidence sequence",
            ),
            line_end_event_offset=_required_coordinate(
                line.end_event_offset,
                "line end event offset",
            ),
            total_line_bytes=len(line.raw),
            match_start_byte=match_start,
            match_end_byte=match_end,
            excerpt_start_byte=excerpt_start,
            excerpt_end_byte=excerpt_end,
            excerpt_raw=excerpt,
            excerpt_text=excerpt.decode("utf-8", errors="replace"),
            excerpt_truncated=len(excerpt) != len(line.raw),
        )


def validate_monitor_request(
    *,
    duration_s: object | None,
    conditions: Sequence[MonitorCondition] | None,
    timeout_s: object | None,
) -> MonitorRequest:
    """Validate exactly one bounded Monitor completion mode."""

    if duration_s is not None and conditions is None and timeout_s is None:
        return MonitorRequest(
            mode="duration",
            duration_s=validate_capture_duration(duration_s),
            conditions=(),
            timeout_s=None,
        )
    if duration_s is None and conditions is not None and timeout_s is not None:
        if isinstance(conditions, (str, bytes)) or not 1 <= len(conditions) <= 8:
            raise ValueError(
                f"Monitor conditions must contain 1..{MAX_MONITOR_CONDITIONS} items"
            )
        validated_conditions = tuple(_validate_condition(item) for item in conditions)
        return MonitorRequest(
            mode="conditions",
            duration_s=None,
            conditions=validated_conditions,
            timeout_s=validate_wait_timeout(timeout_s),
        )
    raise ValueError(
        "Monitor requires exactly one completion mode: duration_s or conditions plus timeout_s"
    )


def _validate_condition(condition: MonitorCondition) -> MonitorCondition:
    if not isinstance(condition, MonitorCondition):
        raise ValueError("Monitor conditions must be MonitorCondition values")
    pattern = validate_wait_pattern(condition.pattern)
    name = condition.name
    if name is not None:
        if not isinstance(name, str):
            raise ValueError("Monitor condition name must be a string or null")
        try:
            encoded_name = name.encode("utf-8")
        except UnicodeEncodeError as exc:
            raise ValueError("Monitor condition name must be valid Unicode") from exc
        if not 1 <= len(encoded_name) <= MAX_MONITOR_CONDITION_NAME_BYTES:
            raise ValueError(
                "Monitor condition name must encode to "
                f"1..{MAX_MONITOR_CONDITION_NAME_BYTES} UTF-8 bytes"
            )
        if name[0].isspace() or name[-1].isspace():
            raise ValueError(
                "Monitor condition name must not have leading or trailing Unicode whitespace"
            )
        if any(unicodedata.category(character) == "Cc" for character in name):
            raise ValueError("Monitor condition name must not contain control characters")
    return MonitorCondition(pattern=pattern, name=name)


def _required_coordinate(value: int | None, field: str) -> int:
    if value is None:
        raise ValueError(f"Monitor match omitted {field}")
    return value
