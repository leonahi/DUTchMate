"""Session evidence record construction and pattern projection."""

import base64
from typing import cast

from dutchmate_core.session_store.models import FirstError, MatchExcerpt, V2FirstError
from dutchmate_core.uart_capture.line_buffer import OversizedUartLine
from dutchmate_core.uart_capture.processor import UartCaptureResult

_FAILURE_PATTERNS = frozenset({"ERROR", "ASSERT", "PANIC", "HardFault"})
_MAX_MATCH_EXCERPT_BYTES = 4096


def detected_pattern_records(
    result: UartCaptureResult,
    *,
    segment_id: int,
) -> list[dict[str, object]]:
    if not result.matches:
        return []

    patterns: list[dict[str, object]] = []
    for match in result.matches:
        match_start_byte = _match_coordinate(match.match_start_byte, "match_start_byte")
        match_end_byte = _match_coordinate(match.match_end_byte, "match_end_byte")
        excerpt = _match_excerpt(
            match.line_raw,
            match_start_byte=match_start_byte,
            match_end_byte=match_end_byte,
        )
        patterns.append(
            {
                "pattern": match.pattern,
                "segment_id": segment_id,
                "timestamp_us": result.timestamp_us,
                "channel": result.channel,
                "ingestion_index": _match_coordinate(match.ingestion_index, "ingestion_index"),
                "line_index_in_event": _match_coordinate(
                    match.line_index_in_event, "line_index_in_event"
                ),
                "line_start_ingestion_index": _match_coordinate(
                    match.line_start_ingestion_index,
                    "line_start_ingestion_index",
                ),
                "line_start_event_offset": _match_coordinate(
                    match.line_start_event_offset, "line_start_event_offset"
                ),
                "line_end_ingestion_index": _match_coordinate(
                    match.line_end_ingestion_index, "line_end_ingestion_index"
                ),
                "line_end_event_offset": _match_coordinate(
                    match.line_end_event_offset, "line_end_event_offset"
                ),
                "total_line_bytes": len(match.line_raw),
                "match_start_byte": match_start_byte,
                "match_end_byte": match_end_byte,
                "match_excerpt": {
                    "start_byte": excerpt.start_byte,
                    "end_byte": excerpt.end_byte,
                    "text": excerpt.text,
                    "raw_b64": excerpt.raw_b64,
                    "excerpt_truncated": excerpt.excerpt_truncated,
                },
            }
        )
    return patterns


def first_error(
    detected_patterns: list[object],
    segments: list[object],
) -> FirstError | None:
    segment_order: dict[int, int] = {}
    for position, raw_segment in enumerate(segments):
        if isinstance(raw_segment, dict):
            segment_id = raw_segment.get("segment_id")
            if isinstance(segment_id, int) and not isinstance(segment_id, bool):
                segment_order[segment_id] = position

    candidates: list[tuple[tuple[int, int, int, int], FirstError]] = []
    for detected_pattern_index, raw_pattern in enumerate(detected_patterns):
        if not isinstance(raw_pattern, dict):
            raise ValueError("detected patterns must contain JSON objects")
        pattern = cast(dict[str, object], raw_pattern)
        pattern_name = pattern.get("pattern")
        if pattern_name not in _FAILURE_PATTERNS:
            continue

        segment_id = _pattern_int(pattern, "segment_id")
        ingestion_index = _pattern_int(pattern, "ingestion_index")
        line_index_in_event = _pattern_int(pattern, "line_index_in_event")
        error = detected_pattern_at(detected_patterns, detected_pattern_index)
        candidates.append(
            (
                (
                    segment_order.get(segment_id, len(segment_order) + segment_id),
                    ingestion_index,
                    line_index_in_event,
                    detected_pattern_index,
                ),
                error,
            )
        )

    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[0])[1]


def v2_first_error(detected_patterns: list[object]) -> V2FirstError | None:
    """Return the earliest stored v2 failure match by primary evidence order."""

    candidates: list[tuple[tuple[int, int, int], V2FirstError]] = []
    for detected_pattern_index, raw_pattern in enumerate(detected_patterns):
        if not isinstance(raw_pattern, dict):
            raise ValueError("detected patterns must contain JSON objects")
        pattern = cast(dict[str, object], raw_pattern)
        source_evidence_seq = _pattern_int(pattern, "source_evidence_seq")
        base_error = detected_pattern_at(detected_patterns, detected_pattern_index)
        if base_error.pattern not in _FAILURE_PATTERNS:
            continue
        error = _v2_first_error(base_error, source_evidence_seq=source_evidence_seq)
        candidates.append(
            (
                (
                    source_evidence_seq,
                    base_error.line_index_in_event,
                    detected_pattern_index,
                ),
                error,
            )
        )

    if not candidates:
        return None
    return min(candidates, key=lambda candidate: candidate[0])[1]


def detected_pattern_at(
    detected_patterns: list[object],
    detected_pattern_index: int,
) -> FirstError:
    """Return one validated reference-bearing stored detected-pattern record."""

    if (
        isinstance(detected_pattern_index, bool)
        or not isinstance(detected_pattern_index, int)
        or not 0 <= detected_pattern_index < len(detected_patterns)
    ):
        raise ValueError("detected-pattern index is out of range")
    raw_pattern = detected_patterns[detected_pattern_index]
    if not isinstance(raw_pattern, dict):
        raise ValueError("detected patterns must contain JSON objects")
    pattern = cast(dict[str, object], raw_pattern)
    pattern_name = pattern.get("pattern")
    if not isinstance(pattern_name, str) or not pattern_name:
        raise ValueError("detected pattern name is invalid")
    return FirstError(
        pattern=pattern_name,
        detected_pattern_index=detected_pattern_index,
        segment_id=_pattern_int(pattern, "segment_id"),
        timestamp_us=_pattern_int(pattern, "timestamp_us"),
        channel=_pattern_int(pattern, "channel"),
        ingestion_index=_pattern_int(pattern, "ingestion_index"),
        line_index_in_event=_pattern_int(pattern, "line_index_in_event"),
        line_start_ingestion_index=_pattern_int(pattern, "line_start_ingestion_index"),
        line_start_event_offset=_pattern_int(pattern, "line_start_event_offset"),
        line_end_ingestion_index=_pattern_int(pattern, "line_end_ingestion_index"),
        line_end_event_offset=_pattern_int(pattern, "line_end_event_offset"),
        total_line_bytes=_pattern_int(pattern, "total_line_bytes"),
        match_start_byte=_pattern_int(pattern, "match_start_byte"),
        match_end_byte=_pattern_int(pattern, "match_end_byte"),
        match_excerpt=_pattern_excerpt(pattern.get("match_excerpt")),
    )


def line_limit_exceeded_event_json(
    result: UartCaptureResult,
    line: OversizedUartLine,
) -> dict[str, object]:
    return {
        "type": "line_limit_exceeded",
        "segment_id": result.segment_id,
        "timestamp_us": line.timestamp_us,
        "channel": result.channel,
        "ingestion_index": _match_coordinate(line.ingestion_index, "ingestion_index"),
        "line_index_in_event": _match_coordinate(line.line_index_in_event, "line_index_in_event"),
        "line_start_ingestion_index": _match_coordinate(
            line.start_ingestion_index, "line_start_ingestion_index"
        ),
        "line_start_event_offset": _match_coordinate(
            line.start_event_offset, "line_start_event_offset"
        ),
        "line_end_ingestion_index": _match_coordinate(
            line.end_ingestion_index, "line_end_ingestion_index"
        ),
        "line_end_event_offset": _match_coordinate(line.end_event_offset, "line_end_event_offset"),
        "total_line_bytes": line.total_bytes,
        "terminated": line.terminated,
    }


def _match_coordinate(value: int | None, field: str) -> int:
    if value is None:
        raise ValueError(f"pattern match is missing {field}")
    return value


def _match_excerpt(
    line_raw: bytes,
    *,
    match_start_byte: int,
    match_end_byte: int,
) -> MatchExcerpt:
    if len(line_raw) <= _MAX_MATCH_EXCERPT_BYTES:
        start_byte = 0
        end_byte = len(line_raw)
    else:
        match_bytes = match_end_byte - match_start_byte
        leading_budget = (_MAX_MATCH_EXCERPT_BYTES - match_bytes) // 2
        start_byte = max(0, match_start_byte - leading_budget)
        start_byte = min(start_byte, len(line_raw) - _MAX_MATCH_EXCERPT_BYTES)
        end_byte = start_byte + _MAX_MATCH_EXCERPT_BYTES

    raw = line_raw[start_byte:end_byte]
    return MatchExcerpt(
        start_byte=start_byte,
        end_byte=end_byte,
        text=raw.decode("utf-8", errors="replace"),
        raw_b64=_bytes_to_b64(raw),
        excerpt_truncated=len(raw) != len(line_raw),
    )


def _pattern_int(pattern: dict[str, object], key: str) -> int:
    value = pattern.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"detected pattern '{key}' must be a non-negative integer")
    return value


def _v2_first_error(error: FirstError, *, source_evidence_seq: int) -> V2FirstError:
    return V2FirstError(
        pattern=error.pattern,
        detected_pattern_index=error.detected_pattern_index,
        segment_id=error.segment_id,
        timestamp_us=error.timestamp_us,
        channel=error.channel,
        ingestion_index=error.ingestion_index,
        line_index_in_event=error.line_index_in_event,
        line_start_ingestion_index=error.line_start_ingestion_index,
        line_start_event_offset=error.line_start_event_offset,
        line_end_ingestion_index=error.line_end_ingestion_index,
        line_end_event_offset=error.line_end_event_offset,
        total_line_bytes=error.total_line_bytes,
        match_start_byte=error.match_start_byte,
        match_end_byte=error.match_end_byte,
        match_excerpt=error.match_excerpt,
        source_evidence_seq=source_evidence_seq,
    )


def _pattern_excerpt(value: object) -> MatchExcerpt:
    if not isinstance(value, dict):
        raise ValueError("detected pattern match_excerpt must be a JSON object")
    excerpt = cast(dict[str, object], value)
    text = excerpt.get("text")
    raw_b64 = excerpt.get("raw_b64")
    truncated = excerpt.get("excerpt_truncated")
    if not isinstance(text, str) or not isinstance(raw_b64, str):
        raise ValueError("detected pattern excerpt text/base64 is invalid")
    if not isinstance(truncated, bool):
        raise ValueError("detected pattern excerpt_truncated must be a boolean")
    return MatchExcerpt(
        start_byte=_pattern_int(excerpt, "start_byte"),
        end_byte=_pattern_int(excerpt, "end_byte"),
        text=text,
        raw_b64=raw_b64,
        excerpt_truncated=truncated,
    )


def _bytes_to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")
