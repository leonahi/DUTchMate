"""Filesystem-backed debug session storage."""

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

from dutchmate_core.backends.contracts import (
    BackendCapabilityPolicy,
    BackendMode,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.uart_capture.processor import UartCaptureResult

_FAILURE_PATTERNS = frozenset({"ERROR", "ASSERT", "PANIC", "HardFault"})
_MAX_MATCH_EXCERPT_BYTES = 4096


@dataclass(frozen=True, slots=True)
class SessionPaths:
    """Filesystem paths for the required Phase 1 session files."""

    root: Path
    metadata: Path
    uart_raw: Path
    uart_events: Path
    hardware_events: Path
    detected_patterns: Path


@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Reference to a created debug session."""

    session_id: str
    paths: SessionPaths


@dataclass(frozen=True, slots=True)
class MatchExcerpt:
    """Bounded exact-byte evidence surrounding one detected pattern."""

    start_byte: int
    end_byte: int
    text: str
    raw_b64: str
    excerpt_truncated: bool


@dataclass(frozen=True, slots=True)
class FirstError:
    """Reference-bearing view of the first stored failure-pattern match."""

    pattern: str
    detected_pattern_index: int
    segment_id: int
    timestamp_us: int
    channel: int
    ingestion_index: int
    line_index_in_event: int
    line_start_ingestion_index: int
    line_start_event_offset: int
    line_end_ingestion_index: int
    line_end_event_offset: int
    total_line_bytes: int
    match_start_byte: int
    match_end_byte: int
    match_excerpt: MatchExcerpt


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Compact summary of a debug session for workflow/API responses."""

    session_id: str
    started_at: str
    command: str
    truncated: bool
    interrupted: bool
    resumed: bool
    overflow: bool
    baseline: bool
    firmware: str | None
    device: str | None
    segment_count: int
    backend_mode: BackendMode | None = None
    port: str | None = None
    backend_capabilities: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    capability_policy: BackendCapabilityPolicy | None = None
    integrity: UartIntegrity | None = None
    segment_contexts: tuple[SegmentContext, ...] = ()
    first_error: FirstError | None = None


class SessionStore:
    """Create filesystem-backed debug sessions."""

    def __init__(
        self,
        root: Path | str = Path(".dutchmate/sessions"),
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._root = Path(root)
        self._clock = clock or _utc_now
        self._id_factory = id_factory or _random_suffix

    @property
    def root(self) -> Path:
        """Directory containing all sessions."""

        return self._root

    def create_session(
        self,
        *,
        command: str,
        firmware: str | None = None,
        device: str | None = None,
        baseline: bool = False,
        backend_snapshot: BackendSnapshot | None = None,
    ) -> SessionHandle:
        """Create a new session directory and initialize required files."""

        if not command:
            raise ValueError("session command must not be empty")

        started_at = self._clock()
        session_id = _validate_session_id(
            f"{_format_session_id_timestamp(started_at)}-{self._id_factory()}"
        )
        paths = _session_paths(self._root / session_id)

        paths.root.mkdir(parents=True, exist_ok=False)
        metadata = _initial_metadata(
            session_id=session_id,
            started_at=_format_utc_timestamp(started_at),
            command=command,
            firmware=firmware,
            device=device,
            baseline=baseline,
            backend_snapshot=backend_snapshot,
        )

        _write_json(paths.metadata, metadata)
        paths.uart_raw.write_bytes(b"")
        paths.uart_events.write_text("", encoding="utf-8")
        paths.hardware_events.write_text("", encoding="utf-8")
        _write_json(paths.detected_patterns, [])

        return SessionHandle(session_id=session_id, paths=paths)

    def load_metadata(self, session_id: str) -> dict[str, object]:
        """Load a session's metadata JSON."""

        session_name = _validate_session_id(session_id)
        metadata_path = _session_paths(self._root / session_name).metadata
        with metadata_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            raise ValueError("session metadata must be a JSON object")
        return loaded

    def summarize_session(self, session_id: str) -> SessionSummary:
        """Load and summarize one session's metadata."""

        session_name = _validate_session_id(session_id)
        paths = _session_paths(self._root / session_name)
        metadata = self.load_metadata(session_name)
        metadata_summary = _summary_from_metadata(metadata, detected_patterns=[])
        if metadata_summary.session_id != session_name:
            raise ValueError("session metadata ID must match its directory name")
        return _summary_from_metadata(
            metadata,
            detected_patterns=_read_json_list(paths.detected_patterns),
        )

    def list_sessions(self, *, limit: int | None = None) -> tuple[SessionSummary, ...]:
        """Return stored session summaries in newest-first order."""

        _validate_session_limit(limit)
        if not self._root.exists():
            return ()

        summaries: list[SessionSummary] = []
        for session_root in self._root.iterdir():
            if (
                session_root.is_symlink()
                or not session_root.is_dir()
                or not _session_paths(session_root).metadata.is_file()
            ):
                continue
            summaries.append(self.summarize_session(session_root.name))

        summaries.sort(
            key=lambda summary: (summary.started_at, summary.session_id),
            reverse=True,
        )
        if limit is not None:
            summaries = summaries[:limit]
        return tuple(summaries)

    def latest_session(self) -> SessionSummary | None:
        """Return the newest stored session summary, if one exists."""

        sessions = self.list_sessions(limit=1)
        return sessions[0] if sessions else None

    def append_uart_capture(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        result: UartCaptureResult,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one processed normalized UART event to a session."""

        if event.segment_id != result.segment_id:
            raise ValueError("UART event and capture result segments must match")
        if event.channel != result.channel:
            raise ValueError("UART event and capture result channels must match")
        if event.timestamp_us != result.timestamp_us:
            raise ValueError("UART event and capture result timestamps must match")

        _append_bytes(handle.paths.uart_raw, event.data)
        _append_jsonl(
            handle.paths.uart_events,
            _uart_event_json(event, timestamp_epoch),
        )
        _append_detected_patterns(
            handle.paths.detected_patterns,
            result,
            segment_id=event.segment_id,
            timestamp_epoch=timestamp_epoch,
        )
        self._record_segment_timestamp(
            handle,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
        )

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer overflow event to a session."""

        metadata = _read_json_object(handle.paths.metadata)
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
        )
        metadata["overflow"] = True
        _record_integrity_loss(metadata, dropped_bytes=event.dropped_bytes, cumulative=False)

        _append_jsonl(
            handle.paths.hardware_events,
            _buffer_overflow_event_json(event, timestamp_epoch),
        )
        _write_json(handle.paths.metadata, metadata)

    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer status telemetry event to a session."""

        metadata = _read_json_object(handle.paths.metadata)
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
        )
        if event.dropped_bytes_total > 0 or event.overflow_events > 0:
            metadata["overflow"] = True
            _record_integrity_loss(
                metadata,
                dropped_bytes=event.dropped_bytes_total,
                cumulative=True,
            )

        _append_jsonl(
            handle.paths.hardware_events,
            _buffer_status_event_json(event, timestamp_epoch),
        )
        _write_json(handle.paths.metadata, metadata)

    def record_segment_context(
        self,
        handle: SessionHandle,
        context: SegmentContext,
    ) -> None:
        """Persist timing provenance before the segment's first evidence event."""

        metadata = _read_json_object(handle.paths.metadata)
        segment = _metadata_segment(metadata, context.segment_id)
        timestamp = _timestamp_json(context.timestamp)
        existing = segment.get("timestamp")
        if existing is not None and existing != timestamp:
            raise ValueError("session segment timestamp provenance cannot change")
        if existing is None:
            segment["timestamp"] = timestamp
            _write_json(handle.paths.metadata, metadata)

    def _record_segment_timestamp(
        self,
        handle: SessionHandle,
        *,
        segment_id: int,
        timestamp_us: int,
    ) -> None:
        metadata = _read_json_object(handle.paths.metadata)
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=segment_id,
            timestamp_us=timestamp_us,
        )
        _write_json(handle.paths.metadata, metadata)


def _session_paths(root: Path) -> SessionPaths:
    return SessionPaths(
        root=root,
        metadata=root / "metadata.json",
        uart_raw=root / "uart_raw.log",
        uart_events=root / "uart_events.jsonl",
        hardware_events=root / "hardware_events.jsonl",
        detected_patterns=root / "detected_patterns.json",
    )


def _validate_session_id(session_id: str) -> str:
    if (
        not isinstance(session_id, str)
        or not session_id
        or session_id.strip() != session_id
        or session_id in {".", ".."}
        or "/" in session_id
        or "\\" in session_id
    ):
        raise ValueError("session ID must be a non-empty path-safe name")
    return session_id


def _validate_session_limit(limit: int | None) -> None:
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0):
        raise ValueError("session limit must be a positive integer")


def _initial_metadata(
    *,
    session_id: str,
    started_at: str,
    command: str,
    firmware: str | None,
    device: str | None,
    baseline: bool,
    backend_snapshot: BackendSnapshot | None,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "session_id": session_id,
        "started_at": started_at,
        "command": command,
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "baseline": baseline,
        "firmware": firmware,
        "device": device,
        "segments": [
            {
                "segment_id": 0,
                "started_at": started_at,
                "ended_at": None,
                "end_reason": None,
                "hello": None,
                "first_device_timestamp_us": None,
                "last_device_timestamp_us": None,
                "timestamp_epoch": 0,
            }
        ],
    }
    if backend_snapshot is None:
        return metadata

    metadata.update(
        {
            "backend_mode": backend_snapshot.info.mode,
            "backend_identity": {
                "port": backend_snapshot.info.port,
                "device": backend_snapshot.info.device,
                "firmware": backend_snapshot.info.firmware,
            },
            "backend_capabilities": sorted(backend_snapshot.info.capabilities),
            "capabilities": sorted(backend_snapshot.capabilities),
            "capability_policy": _capability_policy_json(backend_snapshot.capability_policy),
            "integrity": _integrity_json(backend_snapshot.integrity),
            "segments": [
                _backend_segment_json(
                    backend_snapshot,
                    started_at=started_at,
                )
            ],
        }
    )
    return metadata


def _summary_from_metadata(
    metadata: dict[str, object],
    *,
    detected_patterns: list[object],
) -> SessionSummary:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

    backend_mode = _optional_backend_mode(metadata.get("backend_mode"))
    backend_identity = _optional_object(metadata.get("backend_identity"), "backend_identity")
    return SessionSummary(
        session_id=_required_str(metadata, "session_id"),
        started_at=_required_str(metadata, "started_at"),
        command=_required_str(metadata, "command"),
        truncated=_required_bool(metadata, "truncated"),
        interrupted=_required_bool(metadata, "interrupted"),
        resumed=_required_bool(metadata, "resumed"),
        overflow=_required_bool(metadata, "overflow"),
        baseline=_required_bool(metadata, "baseline"),
        firmware=_optional_str(metadata, "firmware"),
        device=_optional_str(metadata, "device"),
        segment_count=len(segments),
        backend_mode=backend_mode,
        port=(_optional_str(backend_identity, "port") if backend_identity is not None else None),
        backend_capabilities=_optional_string_tuple(metadata, "backend_capabilities"),
        capabilities=_optional_string_tuple(metadata, "capabilities"),
        capability_policy=_optional_capability_policy(metadata.get("capability_policy")),
        integrity=_optional_integrity(metadata.get("integrity")),
        segment_contexts=_segment_contexts(segments),
        first_error=_first_error(detected_patterns, segments),
    )


def _backend_segment_json(
    snapshot: BackendSnapshot,
    *,
    started_at: str,
) -> dict[str, object]:
    segment_id = snapshot.segment.segment_id if snapshot.segment is not None else 0
    return {
        "segment_id": segment_id,
        "started_at": started_at,
        "ended_at": None,
        "end_reason": None,
        "backend": {
            "mode": snapshot.info.mode,
            "port": snapshot.info.port,
            "device": snapshot.info.device,
            "firmware": snapshot.info.firmware,
            "backend_capabilities": sorted(snapshot.info.capabilities),
            "capabilities": sorted(snapshot.capabilities),
            "capability_policy": _capability_policy_json(snapshot.capability_policy),
        },
        "timestamp": (
            _timestamp_json(snapshot.segment.timestamp) if snapshot.segment is not None else None
        ),
        "first_timestamp_us": None,
        "last_timestamp_us": None,
    }


def _capability_policy_json(policy: BackendCapabilityPolicy) -> dict[str, object]:
    return {
        "uart_send": {
            "tx_policy_enabled": policy.uart_send.tx_policy_enabled,
            "source": policy.uart_send.source,
        }
    }


def _integrity_json(integrity: UartIntegrity) -> dict[str, object]:
    return {
        "loss_status": integrity.loss_status,
        "observation_scope": integrity.observation_scope,
        "dropped_bytes": integrity.dropped_bytes,
    }


def _timestamp_json(timestamp: SegmentTimestamp) -> dict[str, object]:
    return {
        "source": timestamp.source,
        "clock": timestamp.clock,
        "unit": timestamp.unit,
        "origin": timestamp.origin,
        "source_origin_us": timestamp.source_origin_us,
        "observation_point": timestamp.observation_point,
        "event_granularity": timestamp.event_granularity,
    }


def _required_str(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"session metadata '{key}' must be a non-empty string")
    return value


def _optional_str(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"session metadata '{key}' must be null or a non-empty string")
    return value


def _optional_object(value: object, field: str) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"session metadata '{field}' must be a JSON object")
    return cast(dict[str, object], value)


def _optional_backend_mode(value: object) -> BackendMode | None:
    if value is None:
        return None
    if value not in {"basic", "enhanced"}:
        raise ValueError("session metadata 'backend_mode' must be basic or enhanced")
    return value


def _optional_string_tuple(metadata: dict[str, object], key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"session metadata '{key}' must be an array of strings")
    return tuple(cast(list[str], value))


def _optional_capability_policy(value: object) -> BackendCapabilityPolicy | None:
    policy = _optional_object(value, "capability_policy")
    if policy is None:
        return None
    uart_send = _optional_object(policy.get("uart_send"), "capability_policy.uart_send")
    if uart_send is None:
        raise ValueError("session metadata capability policy must contain uart_send")
    enabled = uart_send.get("tx_policy_enabled")
    source = uart_send.get("source")
    if not isinstance(enabled, bool):
        raise ValueError("session metadata tx_policy_enabled must be a boolean")
    if source != "hardware.uart.tx_enabled":
        raise ValueError("session metadata UART-send policy source is invalid")
    return BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=enabled))


def _optional_integrity(value: object) -> UartIntegrity | None:
    integrity = _optional_object(value, "integrity")
    if integrity is None:
        return None
    loss_status = integrity.get("loss_status")
    if loss_status not in {"none_reported", "loss_reported", "not_observable"}:
        raise ValueError("session metadata integrity loss_status is invalid")
    observation_scope = integrity.get("observation_scope")
    if observation_scope not in {None, "debug_helper_rx_buffer"}:
        raise ValueError("session metadata integrity observation_scope is invalid")
    dropped_bytes = integrity.get("dropped_bytes")
    if dropped_bytes is not None and (
        isinstance(dropped_bytes, bool) or not isinstance(dropped_bytes, int) or dropped_bytes < 0
    ):
        raise ValueError("session metadata integrity dropped_bytes is invalid")
    return UartIntegrity(
        loss_status=loss_status,
        observation_scope=observation_scope,
        dropped_bytes=dropped_bytes,
    )


def _segment_contexts(segments: list[object]) -> tuple[SegmentContext, ...]:
    contexts: list[SegmentContext] = []
    for raw_segment in segments:
        if not isinstance(raw_segment, dict):
            raise ValueError("session metadata segments must contain JSON objects")
        segment = cast(dict[str, object], raw_segment)
        segment_id = segment.get("segment_id")
        if isinstance(segment_id, bool) or not isinstance(segment_id, int) or segment_id < 0:
            raise ValueError("session metadata segment_id is invalid")
        timestamp = _optional_object(segment.get("timestamp"), "segments.timestamp")
        if timestamp is None:
            continue
        source = timestamp.get("source")
        clock = timestamp.get("clock")
        unit = timestamp.get("unit")
        origin = timestamp.get("origin")
        source_origin_us = timestamp.get("source_origin_us")
        observation_point = timestamp.get("observation_point")
        event_granularity = timestamp.get("event_granularity")
        if source not in {"host", "device"} or clock not in {
            "monotonic",
            "rp2040_timer",
        }:
            raise ValueError("session metadata timestamp source or clock is invalid")
        if unit != "us" or origin != "segment_start":
            raise ValueError("session metadata timestamp unit or origin is invalid")
        if (
            isinstance(source_origin_us, bool)
            or not isinstance(source_origin_us, int)
            or source_origin_us < 0
        ):
            raise ValueError("session metadata timestamp source_origin_us is invalid")
        if not isinstance(observation_point, str) or not observation_point:
            raise ValueError("session metadata timestamp observation_point is invalid")
        if not isinstance(event_granularity, str) or not event_granularity:
            raise ValueError("session metadata timestamp event_granularity is invalid")
        contexts.append(
            SegmentContext(
                segment_id=segment_id,
                timestamp=SegmentTimestamp(
                    source=source,
                    clock=clock,
                    unit="us",
                    origin="segment_start",
                    source_origin_us=source_origin_us,
                    observation_point=observation_point,
                    event_granularity=event_granularity,
                ),
            )
        )
    return tuple(contexts)


def _required_bool(metadata: dict[str, object], key: str) -> bool:
    value = metadata.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"session metadata '{key}' must be a boolean")
    return value


def _write_json(path: Path, value: object) -> None:
    with path.open("w", encoding="utf-8") as file:
        json.dump(value, file, indent=2)
        file.write("\n")


def _read_json_object(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return cast(dict[str, object], loaded)


def _read_json_list(path: Path) -> list[object]:
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return cast(list[object], loaded)


def _append_bytes(path: Path, data: bytes) -> None:
    with path.open("ab") as file:
        file.write(data)


def _append_jsonl(path: Path, value: dict[str, object]) -> None:
    with path.open("a", encoding="utf-8") as file:
        json.dump(value, file, separators=(",", ":"))
        file.write("\n")


def _append_detected_patterns(
    path: Path,
    result: UartCaptureResult,
    *,
    segment_id: int,
    timestamp_epoch: int,
) -> None:
    if not result.matches:
        return

    patterns = _read_json_list(path)
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
                "timestamp_epoch": timestamp_epoch,
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
    _write_json(path, patterns)


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


def _first_error(
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
        error = FirstError(
            pattern=pattern_name,
            detected_pattern_index=detected_pattern_index,
            segment_id=segment_id,
            timestamp_us=_pattern_int(pattern, "timestamp_us"),
            channel=_pattern_int(pattern, "channel"),
            ingestion_index=ingestion_index,
            line_index_in_event=line_index_in_event,
            line_start_ingestion_index=_pattern_int(pattern, "line_start_ingestion_index"),
            line_start_event_offset=_pattern_int(pattern, "line_start_event_offset"),
            line_end_ingestion_index=_pattern_int(pattern, "line_end_ingestion_index"),
            line_end_event_offset=_pattern_int(pattern, "line_end_event_offset"),
            total_line_bytes=_pattern_int(pattern, "total_line_bytes"),
            match_start_byte=_pattern_int(pattern, "match_start_byte"),
            match_end_byte=_pattern_int(pattern, "match_end_byte"),
            match_excerpt=_pattern_excerpt(pattern.get("match_excerpt")),
        )
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


def _pattern_int(pattern: dict[str, object], key: str) -> int:
    value = pattern.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"detected pattern '{key}' must be a non-negative integer")
    return value


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


def _uart_event_json(
    event: UartReceiveEvent,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "uart",
        "segment_id": event.segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": event.timestamp_us,
        "channel": event.channel,
        "data_b64": _bytes_to_b64(event.data),
        "text": event.data.decode("utf-8", errors="replace"),
    }


def _buffer_overflow_event_json(
    event: BufferOverflowEvent,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "buffer_overflow",
        "segment_id": event.segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": event.timestamp_us,
        "channel": event.channel,
        "dropped_bytes": event.dropped_bytes,
    }


def _buffer_status_event_json(
    event: BufferStatusEvent,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "buffer_status",
        "segment_id": event.segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": event.timestamp_us,
        "uart_rx_size_bytes": event.size_bytes,
        "uart_rx_used_bytes": event.used_bytes,
        "uart_rx_high_water_bytes": event.high_water_bytes,
        "dropped_bytes_total": event.dropped_bytes_total,
        "overflow_events": event.overflow_events,
    }


def _record_metadata_segment_timestamp(
    metadata: dict[str, object],
    *,
    segment_id: int,
    timestamp_us: int,
) -> None:
    segment = _metadata_segment(metadata, segment_id)

    first_key = (
        "first_timestamp_us" if "first_timestamp_us" in segment else "first_device_timestamp_us"
    )
    last_key = "last_timestamp_us" if "last_timestamp_us" in segment else "last_device_timestamp_us"
    if segment[first_key] is None:
        segment[first_key] = timestamp_us
    segment[last_key] = timestamp_us


def _record_integrity_loss(
    metadata: dict[str, object],
    *,
    dropped_bytes: int,
    cumulative: bool,
) -> None:
    integrity = metadata.get("integrity")
    if not isinstance(integrity, dict):
        return
    typed_integrity = cast(dict[str, object], integrity)
    previous = typed_integrity.get("dropped_bytes")
    if cumulative:
        updated = (
            max(previous, dropped_bytes)
            if isinstance(previous, int) and not isinstance(previous, bool)
            else dropped_bytes
        )
    elif isinstance(previous, int) and not isinstance(previous, bool):
        updated = previous + dropped_bytes
    else:
        updated = None
    typed_integrity.update(
        {
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": updated,
        }
    )


def _metadata_segment(metadata: dict[str, object], segment_id: int) -> dict[str, object]:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("session metadata segments must contain JSON objects")
        typed_segment = cast(dict[str, object], segment)
        if typed_segment.get("segment_id") == segment_id:
            return typed_segment

    raise ValueError(f"session metadata has no segment {segment_id}")


def _bytes_to_b64(data: bytes) -> str:
    return base64.b64encode(data).decode("ascii")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _random_suffix() -> str:
    return uuid4().hex[:8]


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_session_id_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
