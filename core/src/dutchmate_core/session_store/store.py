"""Filesystem-backed debug session storage."""

import base64
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    UartMessage,
)
from dutchmate_core.uart_capture.processor import UartCaptureResult


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
        summary = _summary_from_metadata(self.load_metadata(session_name))
        if summary.session_id != session_name:
            raise ValueError("session metadata ID must match its directory name")
        return summary

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
        message: UartMessage,
        result: UartCaptureResult,
        segment_id: int = 0,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one processed UART capture message to a session."""

        if message.channel != result.channel:
            raise ValueError("UART message and capture result channels must match")
        if message.timestamp_us != result.timestamp_us:
            raise ValueError("UART message and capture result timestamps must match")

        _append_bytes(handle.paths.uart_raw, message.data)
        _append_jsonl(
            handle.paths.uart_events,
            _uart_event_json(message, segment_id, timestamp_epoch),
        )
        _append_detected_patterns(
            handle.paths.detected_patterns,
            result,
            segment_id=segment_id,
            timestamp_epoch=timestamp_epoch,
        )
        self._record_segment_timestamp(
            handle,
            segment_id=segment_id,
            timestamp_us=message.timestamp_us,
        )

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        message: BufferOverflowMessage,
        segment_id: int = 0,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer overflow event to a session."""

        metadata = _read_json_object(handle.paths.metadata)
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=segment_id,
            timestamp_us=message.timestamp_us,
        )
        metadata["overflow"] = True

        _append_jsonl(
            handle.paths.hardware_events,
            _buffer_overflow_event_json(message, segment_id, timestamp_epoch),
        )
        _write_json(handle.paths.metadata, metadata)

    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        message: BufferStatusMessage,
        segment_id: int = 0,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer status telemetry event to a session."""

        metadata = _read_json_object(handle.paths.metadata)
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=segment_id,
            timestamp_us=message.timestamp_us,
        )
        if message.dropped_bytes_total > 0 or message.overflow_events > 0:
            metadata["overflow"] = True

        _append_jsonl(
            handle.paths.hardware_events,
            _buffer_status_event_json(message, segment_id, timestamp_epoch),
        )
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
    if limit is not None and (
        isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0
    ):
        raise ValueError("session limit must be a positive integer")


def _initial_metadata(
    *,
    session_id: str,
    started_at: str,
    command: str,
    firmware: str | None,
    device: str | None,
    baseline: bool,
) -> dict[str, object]:
    return {
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


def _summary_from_metadata(metadata: dict[str, object]) -> SessionSummary:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

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
    )


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
        patterns.append(
            {
                "pattern": match.pattern,
                "segment_id": segment_id,
                "timestamp_epoch": timestamp_epoch,
                "timestamp_us": result.timestamp_us,
                "channel": result.channel,
                "line_text": match.line_text,
                "line_raw_b64": _bytes_to_b64(match.line_raw),
            }
        )
    _write_json(path, patterns)


def _uart_event_json(
    message: UartMessage,
    segment_id: int,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "uart",
        "segment_id": segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": message.timestamp_us,
        "channel": message.channel,
        "data_b64": _bytes_to_b64(message.data),
        "text": message.text,
    }


def _buffer_overflow_event_json(
    message: BufferOverflowMessage,
    segment_id: int,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "buffer_overflow",
        "segment_id": segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": message.timestamp_us,
        "channel": message.channel,
        "dropped_bytes": message.dropped_bytes,
    }


def _buffer_status_event_json(
    message: BufferStatusMessage,
    segment_id: int,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "buffer_status",
        "segment_id": segment_id,
        "timestamp_epoch": timestamp_epoch,
        "timestamp_us": message.timestamp_us,
        "uart_rx_size_bytes": message.uart_rx_size_bytes,
        "uart_rx_used_bytes": message.uart_rx_used_bytes,
        "uart_rx_high_water_bytes": message.uart_rx_high_water_bytes,
        "dropped_bytes_total": message.dropped_bytes_total,
        "overflow_events": message.overflow_events,
    }


def _record_metadata_segment_timestamp(
    metadata: dict[str, object],
    *,
    segment_id: int,
    timestamp_us: int,
) -> None:
    segment = _metadata_segment(metadata, segment_id)

    if segment["first_device_timestamp_us"] is None:
        segment["first_device_timestamp_us"] = timestamp_us
    segment["last_device_timestamp_us"] = timestamp_us


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
