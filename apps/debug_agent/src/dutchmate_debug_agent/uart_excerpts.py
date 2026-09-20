"""Priority selection of bounded native UART text excerpts."""

from __future__ import annotations

import base64
import json
from collections import deque
from dataclasses import dataclass
from typing import Final

from dutchmate_core.session_store.evidence import detected_pattern_at
from dutchmate_core.uart_capture.line_buffer import UartLine, UartLineBuffer
from dutchmate_debug_agent.evidence_source import _integer, _jsonl_objects
from dutchmate_debug_agent.session_facts import SessionFacts

_UART_LINES: Final = 300
_UART_TEXT_BYTES: Final = 64 * 1024
_PATTERN_REFS_PER_LINE: Final = 16
_ERROR_CONTEXT_LINES: Final = 5
_BOOT_EDGE_LINES: Final = 20
_UART_KEYS: Final = frozenset({"type", "segment_id", "timestamp_us", "channel", "data_b64", "text"})


@dataclass(frozen=True, slots=True)
class UartExcerpt:
    session_id: str
    ordinal: int
    segment_id: int
    channel: int
    timestamp_us: int
    ingestion_index: int
    line_index_in_event: int
    text: str
    partial: bool
    pattern_indexes: tuple[int, ...]
    omitted_pattern_indexes: int


def _pattern_references(data: bytes) -> dict[tuple[int, int, int, int], list[int]]:
    raw = json.loads(data.decode("utf-8"))
    if not isinstance(raw, list):
        raise ValueError("detected patterns must be a list")
    refs: dict[tuple[int, int, int, int], list[int]] = {}
    for index in range(len(raw)):
        pattern = detected_pattern_at(raw, index)
        key = (
            pattern.segment_id,
            pattern.channel,
            pattern.ingestion_index,
            pattern.line_index_in_event,
        )
        refs.setdefault(key, []).append(index)
    return refs


def _uart_record(record: dict[str, object]) -> tuple[int, int, int, bytes]:
    if set(record) != _UART_KEYS or record.get("type") != "uart":
        raise ValueError("UART event record fields are invalid")
    segment_id = _integer(record.get("segment_id"), "segment_id")
    channel = _integer(record.get("channel"), "channel")
    timestamp_us = _integer(record.get("timestamp_us"), "timestamp_us")
    encoded = record.get("data_b64")
    if not isinstance(encoded, str):
        raise ValueError("UART data_b64 must be text")
    data = base64.b64decode(encoded, validate=True)
    if record.get("text") != data.decode("utf-8", errors="replace"):
        raise ValueError("UART text disagrees with recorded bytes")
    return segment_id, channel, timestamp_us, data


class _UartSelector:
    def __init__(
        self,
        facts: SessionFacts,
        patterns: dict[tuple[int, int, int, int], list[int]],
    ) -> None:
        self.facts = facts
        self.patterns = patterns
        self.count = 0
        self.oversized_count = 0
        self.first_error_found = False
        self._after_error = 0
        self._before = deque[UartExcerpt](maxlen=_ERROR_CONTEXT_LINES)
        self._error: list[UartExcerpt] = []
        self._pattern: list[UartExcerpt] = []
        self._start: list[UartExcerpt] = []
        self._end = deque[UartExcerpt](maxlen=_BOOT_EDGE_LINES)
        self._recent = deque[UartExcerpt](maxlen=_UART_LINES)

    def read(self, data: bytes) -> None:
        buffers: dict[tuple[int, int], UartLineBuffer] = {}
        timestamps: dict[tuple[int, int], int] = {}
        current_segment: int | None = None
        valid_segments = {
            _integer(segment.get("segment_id"), "segment_id") for segment in self.facts.segments
        }
        for ingestion_index, record in enumerate(_jsonl_objects(data)):
            segment_id, channel, timestamp_us, payload = _uart_record(record)
            if segment_id not in valid_segments:
                raise ValueError("UART event references an unknown segment")
            if current_segment is not None and segment_id != current_segment:
                if segment_id < current_segment:
                    raise ValueError("UART event segment order regressed")
                self._flush_segment(buffers, timestamps, current_segment)
            current_segment = segment_id
            key = (segment_id, channel)
            buffer = buffers.setdefault(key, UartLineBuffer())
            result = buffer.feed_result(
                payload, ingestion_index=ingestion_index, timestamp_us=timestamp_us
            )
            timestamps[key] = timestamp_us
            self.oversized_count += len(result.oversized_lines)
            for line in result.lines:
                self._observe(line, segment_id, channel, timestamp_us, partial=False)
        if current_segment is not None:
            self._flush_segment(buffers, timestamps, current_segment)

    def _flush_segment(
        self,
        buffers: dict[tuple[int, int], UartLineBuffer],
        timestamps: dict[tuple[int, int], int],
        segment_id: int,
    ) -> None:
        pending: list[tuple[int, int, UartLine, int]] = []
        for key in tuple(buffers):
            if key[0] != segment_id:
                continue
            _, channel = key
            buffer = buffers.pop(key)
            timestamp_us = timestamps.pop(key)
            result = buffer.flush_result()
            self.oversized_count += len(result.oversized_lines)
            for line in result.lines:
                if line.ingestion_index is None:
                    raise ValueError("partial UART line is missing ingestion index")
                pending.append((line.ingestion_index, channel, line, timestamp_us))
        for _, channel, line, timestamp_us in sorted(pending, key=lambda item: item[:2]):
            self._observe(line, segment_id, channel, timestamp_us, partial=True)

    def _observe(
        self,
        line: UartLine,
        segment_id: int,
        channel: int,
        timestamp_us: int,
        *,
        partial: bool,
    ) -> None:
        if line.ingestion_index is None or line.line_index_in_event is None:
            raise ValueError("UART line is missing evidence coordinates")
        key = (segment_id, channel, line.ingestion_index, line.line_index_in_event)
        refs = self.patterns.get(key, [])
        excerpt = UartExcerpt(
            session_id=self.facts.session_id,
            ordinal=self.count,
            segment_id=segment_id,
            channel=channel,
            timestamp_us=timestamp_us,
            ingestion_index=line.ingestion_index,
            line_index_in_event=line.line_index_in_event,
            text=line.text,
            partial=partial,
            pattern_indexes=tuple(refs[:_PATTERN_REFS_PER_LINE]),
            omitted_pattern_indexes=max(0, len(refs) - _PATTERN_REFS_PER_LINE),
        )
        self.count += 1
        error = self.facts.first_error
        error_key = (
            (error.segment_id, error.channel, error.ingestion_index, error.line_index_in_event)
            if error is not None
            else None
        )
        if key == error_key:
            self.first_error_found = True
            self._error.extend(self._before)
            self._error.append(excerpt)
            self._after_error = _ERROR_CONTEXT_LINES
        elif self._after_error:
            self._error.append(excerpt)
            self._after_error -= 1
        self._before.append(excerpt)
        if refs and len(self._pattern) < _UART_LINES:
            self._pattern.append(excerpt)
        if len(self._start) < _BOOT_EDGE_LINES:
            self._start.append(excerpt)
        self._end.append(excerpt)
        self._recent.append(excerpt)

    def select(self) -> tuple[tuple[UartExcerpt, ...], int]:
        selected: dict[int, UartExcerpt] = {}
        text_bytes = 0
        for excerpt in (*self._error, *self._pattern, *self._start, *self._end, *self._recent):
            if excerpt.ordinal in selected:
                continue
            size = len(excerpt.text.encode("utf-8"))
            if len(selected) >= _UART_LINES or text_bytes + size > _UART_TEXT_BYTES:
                continue
            selected[excerpt.ordinal] = excerpt
            text_bytes += size
        return tuple(selected[key] for key in sorted(selected)), text_bytes
