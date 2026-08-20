"""Bounded replay of persisted native UART evidence."""

from __future__ import annotations

import base64
import binascii
import heapq
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Generic, TypeVar, cast

import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.models import (
    NativeSessionDetail,
    OversizedLogLine,
    RecentLogLine,
    RecentLogs,
    SessionPaths,
    SessionQueryError,
    SessionSelection,
)
from dutchmate_core.session_store.retrieval import (
    _exception_detail,
    _query_fault,
    _read_metadata,
    _schema_version,
    _transaction_active,
    _unsupported_schema,
    _validated_summary,
    get_session_detail,
)
from dutchmate_core.uart_capture.line_buffer import OversizedUartLine, UartLineBuffer
from dutchmate_core.validation import InputValidationError, validate_session_id

DEFAULT_RECENT_LOG_LINES: Final = 300
MAX_RECENT_LOG_LINES: Final = 1000
_SNAPSHOT_ATTEMPTS: Final = 20
_UART_EVENT_KEYS: Final = frozenset(
    {
        "type",
        "segment_id",
        "timestamp_epoch",
        "timestamp_us",
        "channel",
        "data_b64",
        "text",
    }
)
_TERMINAL_STATES: Final = frozenset({"completed", "failed", "abandoned"})
_T = TypeVar("_T", RecentLogLine, OversizedLogLine)


def replay_recent_logs(
    root: Path,
    *,
    session_id: str | None = None,
    lines: int = DEFAULT_RECENT_LOG_LINES,
    active_session_id: str | None = None,
) -> RecentLogs:
    """Select one native session and replay its newest bounded UART lines."""

    _validate_lines(lines)
    paths, selection = _select_session(
        root,
        session_id=session_id,
        active_session_id=active_session_id,
    )
    uart_prefix, metadata = _stable_uart_snapshot(paths)
    try:
        summary = _validated_summary(metadata, [], paths, operation="get_logs")
        if summary.state is None or summary.integrity is None:
            raise ValueError("native log session is missing required lifecycle facts")
        if summary.reconnect_timeout_s is None:
            raise ValueError("native log session is missing reconnect timeout")
        storage = metadata.get("storage")
        if not isinstance(storage, dict):
            raise ValueError("native log session storage must be an object")
        segments = _metadata._contiguous_native_segments(metadata)
        replay = _replay_uart_prefix(
            uart_prefix,
            lines=lines,
            valid_segment_ids=frozenset(range(len(segments))),
        )
        replayed_oversized_count = (
            len(replay.oversized_lines) + replay.omitted_oversized_lines
        )
        if replayed_oversized_count != summary.line_processing.oversized_line_count:
            raise ValueError(
                "replayed oversized-line count does not match session metadata"
            )
    except SessionQueryError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        raise _query_fault(
            operation="get_logs",
            session_id=paths.root.name,
            detail=f"Session UART evidence is invalid: {_exception_detail(exc)}",
        ) from exc

    referenced_segments = {
        record.segment_id
        for record in (*replay.complete_lines, *replay.partial_lines)
    }
    referenced_segments.update(
        record.segment_id for record in replay.oversized_lines
    )
    provenance = tuple(
        segment.copy()
        for segment in segments
        if cast(int, segment["segment_id"]) in referenced_segments
    )
    return RecentLogs(
        session_selection=selection,
        session_id=paths.root.name,
        active=summary.state == "active",
        snapshot_event_count=replay.snapshot_event_count,
        complete_lines=replay.complete_lines,
        partial_lines=replay.partial_lines,
        oversized_lines=replay.oversized_lines,
        integrity=summary.integrity,
        line_processing=summary.line_processing,
        reconnect_timeout_s=summary.reconnect_timeout_s,
        interrupted=summary.interrupted,
        resumed=summary.resumed,
        storage=cast(dict[str, object], storage).copy(),
        truncated=summary.truncated,
        truncation=summary.truncation.copy() if summary.truncation is not None else None,
        timestamp_provenance=provenance,
        omitted_complete_lines=replay.omitted_complete_lines,
        omitted_partial_lines=replay.omitted_partial_lines,
        omitted_oversized_lines=replay.omitted_oversized_lines,
    )


def _select_session(
    root: Path,
    *,
    session_id: str | None,
    active_session_id: str | None,
) -> tuple[SessionPaths, SessionSelection]:
    if session_id is not None:
        session_name = validate_session_id(session_id)
        paths = _existing_paths(root, session_name)
        metadata = _read_metadata(paths, operation="get_logs")
        _require_native_schema(metadata, session_name)
        _validate_terminal_detail(paths, metadata)
        return paths, "explicit"

    if active_session_id is not None:
        active_name = validate_session_id(active_session_id)
        active_root = root / active_name
        if active_root.is_dir() and not active_root.is_symlink():
            paths = _persistence.session_paths(active_root)
            metadata = _read_metadata(paths, operation="get_logs")
            schema_version = _schema_version(
                metadata,
                operation="get_logs",
                session_id=active_name,
            )
            if schema_version == 1 and metadata.get("state") == "active":
                return paths, "active"

    latest_paths = _latest_terminal_native(root)
    if latest_paths is None:
        raise SessionQueryError(
            error="not_found",
            operation="get_logs",
            detail="No native active or terminal session is available",
        )
    metadata = _read_metadata(latest_paths, operation="get_logs")
    _validate_terminal_detail(latest_paths, metadata)
    return latest_paths, "latest_terminal"


def _existing_paths(root: Path, session_id: str) -> SessionPaths:
    session_root = root / session_id
    if session_root.is_symlink() or not session_root.exists():
        raise SessionQueryError(
            error="not_found",
            operation="get_logs",
            session_id=session_id,
            detail=f"Session '{session_id}' was not found",
        )
    if not session_root.is_dir():
        raise _query_fault(
            operation="get_logs",
            session_id=session_id,
            detail="Session path is not a directory",
        )
    return _persistence.session_paths(session_root)


def _latest_terminal_native(root: Path) -> SessionPaths | None:
    if not root.exists():
        return None
    try:
        session_roots = tuple(root.iterdir())
    except OSError as exc:
        raise _query_fault(
            operation="get_logs",
            session_id=None,
            detail=f"Unable to enumerate session storage: {_exception_detail(exc)}",
        ) from exc

    candidates: list[tuple[str, str, SessionPaths]] = []
    for session_root in session_roots:
        if session_root.is_symlink() or not session_root.is_dir():
            continue
        paths = _persistence.session_paths(session_root)
        if not paths.metadata.is_file():
            continue
        metadata = _read_metadata(paths, operation="get_logs")
        schema_version = _schema_version(
            metadata,
            operation="get_logs",
            session_id=session_root.name,
        )
        if schema_version != 1:
            continue
        state = metadata.get("state")
        if state == "active":
            continue
        if state not in _TERMINAL_STATES:
            raise _query_fault(
                operation="get_logs",
                session_id=session_root.name,
                detail="Native session lifecycle state is malformed",
            )
        summary = _validated_summary(metadata, [], paths, operation="get_logs")
        candidates.append((summary.started_at, summary.session_id, paths))
    if not candidates:
        return None
    return max(candidates, key=lambda candidate: (candidate[0], candidate[1]))[2]


def _require_native_schema(metadata: dict[str, object], session_id: str) -> None:
    schema_version = _schema_version(
        metadata,
        operation="get_logs",
        session_id=session_id,
    )
    if schema_version != 1:
        raise _unsupported_schema(
            operation="get_logs",
            session_id=session_id,
            detected=schema_version,
        )


def _validate_terminal_detail(paths: SessionPaths, metadata: dict[str, object]) -> None:
    if metadata.get("state") == "active":
        return
    try:
        detail = get_session_detail(paths.root.parent, paths.root.name)
    except SessionQueryError as exc:
        raise SessionQueryError(
            error=exc.error,
            operation="get_logs",
            session_id=exc.session_id,
            detected_schema_version=exc.detected_schema_version,
            detail=str(exc),
        ) from exc
    if not isinstance(detail, NativeSessionDetail):
        raise _unsupported_schema(
            operation="get_logs",
            session_id=paths.root.name,
            detected=0,
        )


def _stable_uart_snapshot(paths: SessionPaths) -> tuple[bytes, dict[str, object]]:
    metadata = _read_metadata(paths, operation="get_logs")
    _require_native_schema(metadata, paths.root.name)
    for _attempt in range(_SNAPSHOT_ATTEMPTS):
        if _transaction_active(paths):
            time.sleep(0.001)
            metadata = _read_metadata(paths, operation="get_logs")
            continue
        try:
            if paths.uart_events.is_symlink() or not paths.uart_events.is_file():
                raise ValueError("required artifact uart_events.jsonl is missing or invalid")
            uart_bytes = paths.uart_events.read_bytes()
            cursor = uart_bytes.rfind(b"\n") + 1
            if metadata.get("state") != "active" and cursor != len(uart_bytes):
                raise ValueError("terminal uart_events.jsonl contains an incomplete record")
            prefix = uart_bytes[:cursor]
            _validate_snapshot_storage(metadata, paths)
            metadata_after = _read_metadata(paths, operation="get_logs")
        except (OSError, ValueError) as exc:
            raise _query_fault(
                operation="get_logs",
                session_id=paths.root.name,
                detail=f"Unable to snapshot UART evidence: {_exception_detail(exc)}",
            ) from exc
        if not _transaction_active(paths) and metadata_after == metadata:
            return prefix, metadata
        metadata = metadata_after
        time.sleep(0.001)
    raise _query_fault(
        operation="get_logs",
        session_id=paths.root.name,
        detail="Session changed continuously while creating a UART snapshot",
    )


@dataclass(frozen=True, slots=True)
class _ReplayResult:
    snapshot_event_count: int
    complete_lines: tuple[RecentLogLine, ...]
    partial_lines: tuple[RecentLogLine, ...]
    oversized_lines: tuple[OversizedLogLine, ...]
    omitted_complete_lines: int
    omitted_partial_lines: int
    omitted_oversized_lines: int


class _BoundedNewest(Generic[_T]):
    """Retain the newest coordinate-ordered records with bounded memory."""

    def __init__(self, limit: int) -> None:
        self._limit = limit
        self._next_sequence = 0
        self._heap: list[tuple[int, int, int, _T]] = []
        self.omitted = 0

    def add(self, record: _T) -> None:
        ingestion_index, line_index = _record_key(record)
        entry = (ingestion_index, line_index, self._next_sequence, record)
        self._next_sequence += 1
        if len(self._heap) < self._limit:
            heapq.heappush(self._heap, entry)
            return
        self.omitted += 1
        if entry[:2] > self._heap[0][:2]:
            heapq.heapreplace(self._heap, entry)

    def values(self) -> tuple[_T, ...]:
        return tuple(entry[3] for entry in sorted(self._heap))


def _replay_uart_prefix(
    prefix: bytes,
    *,
    lines: int,
    valid_segment_ids: frozenset[int],
) -> _ReplayResult:
    buffers: dict[tuple[int, int], UartLineBuffer] = {}
    last_timestamps: dict[tuple[int, int], int] = {}
    complete = _BoundedNewest[RecentLogLine](lines)
    partial = _BoundedNewest[RecentLogLine](lines)
    oversized = _BoundedNewest[OversizedLogLine](lines)
    event_count = 0

    for ingestion_index, raw_record in enumerate(prefix.splitlines(keepends=True)):
        event = _decode_uart_event(raw_record, valid_segment_ids=valid_segment_ids)
        segment_id, channel, timestamp_us, data = event
        key = segment_id, channel
        buffer = buffers.setdefault(key, UartLineBuffer())
        result = buffer.feed_result(
            data,
            ingestion_index=ingestion_index,
            timestamp_us=timestamp_us,
        )
        last_timestamps[key] = timestamp_us
        for line in result.lines:
            complete.add(
                _normal_record(
                    line.raw,
                    line.text,
                    segment_id=segment_id,
                    channel=channel,
                    timestamp_us=timestamp_us,
                    ingestion_index=_required_coordinate(line.ingestion_index),
                    line_index_in_event=_required_coordinate(line.line_index_in_event),
                    partial=False,
                )
            )
        for oversized_line in result.oversized_lines:
            oversized.add(
                _oversized_record(
                    oversized_line,
                    segment_id=segment_id,
                    channel=channel,
                )
            )
        event_count += 1

    for (segment_id, channel), buffer in buffers.items():
        result = buffer.flush_result()
        for line in result.lines:
            partial.add(
                _normal_record(
                    line.raw,
                    line.text,
                    segment_id=segment_id,
                    channel=channel,
                    timestamp_us=last_timestamps[(segment_id, channel)],
                    ingestion_index=_required_coordinate(line.ingestion_index),
                    line_index_in_event=_required_coordinate(line.line_index_in_event),
                    partial=True,
                )
            )
        for oversized_line in result.oversized_lines:
            oversized.add(
                _oversized_record(
                    oversized_line,
                    segment_id=segment_id,
                    channel=channel,
                )
            )

    return _ReplayResult(
        snapshot_event_count=event_count,
        complete_lines=complete.values(),
        partial_lines=partial.values(),
        oversized_lines=oversized.values(),
        omitted_complete_lines=complete.omitted,
        omitted_partial_lines=partial.omitted,
        omitted_oversized_lines=oversized.omitted,
    )


def _decode_uart_event(
    raw_record: bytes,
    *,
    valid_segment_ids: frozenset[int],
) -> tuple[int, int, int, bytes]:
    if not raw_record.endswith(b"\n") or raw_record == b"\n":
        raise ValueError("uart_events.jsonl contains an incomplete or empty record")
    value = json.loads(raw_record.decode("utf-8"))
    if not isinstance(value, dict) or set(value) != _UART_EVENT_KEYS:
        raise ValueError("UART evidence record fields are invalid")
    event = cast(dict[str, object], value)
    if event.get("type") != "uart":
        raise ValueError("UART evidence record type is invalid")
    segment_id = _non_negative_int(event.get("segment_id"), "segment_id")
    if segment_id not in valid_segment_ids:
        raise ValueError("UART evidence references an unknown segment")
    _non_negative_int(event.get("timestamp_epoch"), "timestamp_epoch")
    timestamp_us = _non_negative_int(event.get("timestamp_us"), "timestamp_us")
    channel = _non_negative_int(event.get("channel"), "channel")
    data_b64 = event.get("data_b64")
    if not isinstance(data_b64, str):
        raise ValueError("UART evidence data_b64 must be a string")
    try:
        data = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("UART evidence data_b64 is invalid") from exc
    if event.get("text") != data.decode("utf-8", errors="replace"):
        raise ValueError("UART evidence text projection does not match exact bytes")
    return segment_id, channel, timestamp_us, data


def _normal_record(
    raw: bytes,
    text: str,
    *,
    segment_id: int,
    channel: int,
    timestamp_us: int,
    ingestion_index: int,
    line_index_in_event: int,
    partial: bool,
) -> RecentLogLine:
    return RecentLogLine(
        segment_id=segment_id,
        channel=channel,
        timestamp_us=timestamp_us,
        ingestion_index=ingestion_index,
        line_index_in_event=line_index_in_event,
        line_raw_b64=base64.b64encode(raw).decode("ascii"),
        line_text=text,
        partial=partial,
    )


def _oversized_record(
    line: OversizedUartLine,
    *,
    segment_id: int,
    channel: int,
) -> OversizedLogLine:
    return OversizedLogLine(
        segment_id=segment_id,
        channel=channel,
        ingestion_index=_required_coordinate(line.ingestion_index),
        line_index_in_event=_required_coordinate(line.line_index_in_event),
        line_start_ingestion_index=_required_coordinate(line.start_ingestion_index),
        line_start_event_offset=_required_coordinate(line.start_event_offset),
        line_end_ingestion_index=_required_coordinate(line.end_ingestion_index),
        line_end_event_offset=_required_coordinate(line.end_event_offset),
        total_line_bytes=line.total_bytes,
        terminated=line.terminated,
        timestamp_us=_required_coordinate(line.timestamp_us),
    )


def _record_key(record: RecentLogLine | OversizedLogLine) -> tuple[int, int]:
    return record.ingestion_index, record.line_index_in_event


def _required_coordinate(value: int | None) -> int:
    if value is None:
        raise ValueError("replayed UART line is missing an evidence coordinate")
    return value


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"UART evidence {field} must be a non-negative integer")
    return value


def _validate_lines(lines: object) -> None:
    if (
        isinstance(lines, bool)
        or not isinstance(lines, int)
        or not 1 <= lines <= MAX_RECENT_LOG_LINES
    ):
        raise InputValidationError(
            f"log lines must be an integer from 1 to {MAX_RECENT_LOG_LINES}"
        )


def _validate_snapshot_storage(metadata: dict[str, object], paths: SessionPaths) -> None:
    storage = metadata.get("storage")
    if not isinstance(storage, dict):
        raise ValueError("native session storage must be an object")
    written = storage.get("evidence_bytes_written")
    budget = storage.get("evidence_budget_bytes")
    metadata_max = storage.get("metadata_max_bytes")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("native session evidence budget is invalid")
    if isinstance(written, bool) or not isinstance(written, int) or written < 0:
        raise ValueError("native session evidence byte accounting is invalid")
    if metadata_max != _metadata.METADATA_MAX_BYTES:
        raise ValueError("native session metadata byte limit is invalid")
    evidence_paths = (
        paths.uart_raw,
        paths.uart_events,
        paths.hardware_events,
        paths.detected_patterns,
    )
    for path in evidence_paths:
        if path.is_symlink() or not path.is_file():
            raise ValueError(f"required artifact {path.name} is missing or invalid")
    actual = sum(path.stat().st_size for path in evidence_paths)
    if written != actual:
        raise ValueError("native evidence byte accounting does not match artifacts")
