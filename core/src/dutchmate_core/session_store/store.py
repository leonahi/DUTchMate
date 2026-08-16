"""Filesystem-backed debug session storage."""

import base64
import json
import math
import os
import unicodedata
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, cast
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
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES, OversizedUartLine
from dutchmate_core.uart_capture.processor import UartCaptureResult

_FAILURE_PATTERNS = frozenset({"ERROR", "ASSERT", "PANIC", "HardFault"})
_MAX_MATCH_EXCERPT_BYTES = 4096
_DEFAULT_EVIDENCE_BUDGET_BYTES = 50 * 1024 * 1024
_METADATA_MAX_BYTES = 262144

SessionState = Literal["active", "completed", "failed", "abandoned"]
SessionWorkflow = Literal["capture", "boot_test", "wait_pattern"]


@dataclass(frozen=True, slots=True)
class SessionPaths:
    """Filesystem paths for the required Phase 1 session files."""

    root: Path
    metadata: Path
    uart_raw: Path
    uart_events: Path
    hardware_events: Path
    detected_patterns: Path
    terminal_reserve: Path


@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Reference to a created debug session."""

    session_id: str
    paths: SessionPaths


@dataclass(frozen=True, slots=True)
class SessionRecoveryDiagnostic:
    """One non-fatal startup-recovery observation for a stored session."""

    session_id: str
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class SessionRecoveryResult:
    """Sessions abandoned at startup plus non-fatal compatibility diagnostics."""

    recovered_session_ids: tuple[str, ...] = ()
    diagnostics: tuple[SessionRecoveryDiagnostic, ...] = ()


class SessionRecoveryError(RuntimeError):
    """Raised when stale native session metadata cannot be safely replaced."""


class EvidenceQuotaExceeded(RuntimeError):
    """Raised after an evidence unit is rejected and its session is terminalized."""

    def __init__(self, truncation: dict[str, object]) -> None:
        self.truncation = truncation.copy()
        super().__init__("session evidence budget would be exceeded")


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
class LineProcessing:
    """Bounded derived-line processing status for one session."""

    status: Literal["complete", "limit_exceeded"] = "complete"
    max_line_bytes: int = MAX_UART_LINE_BYTES
    oversized_line_count: int = 0

    def __post_init__(self) -> None:
        if self.max_line_bytes != MAX_UART_LINE_BYTES:
            raise ValueError("line-processing max_line_bytes must be 65536")
        if (
            isinstance(self.oversized_line_count, bool)
            or not isinstance(self.oversized_line_count, int)
            or self.oversized_line_count < 0
        ):
            raise ValueError("oversized-line count must be a non-negative integer")
        if (self.status == "complete") != (self.oversized_line_count == 0):
            raise ValueError("line-processing status/count must agree")


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
    line_processing: LineProcessing = LineProcessing()
    schema_version: int = 0
    state: SessionState | None = None
    workflow: SessionWorkflow | None = None
    duration_s: float | None = None
    reconnect_timeout_s: float | None = None
    ended_at: str | None = None
    end_reason: str | None = None
    error: dict[str, object] | None = None
    truncation: dict[str, object] | None = None


class SessionStore:
    """Create filesystem-backed debug sessions."""

    def __init__(
        self,
        root: Path | str = Path(".dutchmate/sessions"),
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        evidence_budget_bytes: int = _DEFAULT_EVIDENCE_BUDGET_BYTES,
    ) -> None:
        self._root = Path(root)
        self._clock = clock or _utc_now
        self._id_factory = id_factory or _random_suffix
        if (
            isinstance(evidence_budget_bytes, bool)
            or not isinstance(evidence_budget_bytes, int)
            or evidence_budget_bytes <= 0
        ):
            raise ValueError("session evidence budget must be a positive integer")
        self._evidence_budget_bytes = evidence_budget_bytes
        self._last_recovery = SessionRecoveryResult()

    @property
    def root(self) -> Path:
        """Directory containing all sessions."""

        return self._root

    @property
    def last_recovery(self) -> SessionRecoveryResult:
        """Most recent startup-recovery result for this store instance."""

        return self._last_recovery

    def recover_stale_sessions(self) -> SessionRecoveryResult:
        """Abandon stale native active sessions without mutating other schemas."""

        if not self._root.exists():
            self._last_recovery = SessionRecoveryResult()
            return self._last_recovery

        recovered: list[str] = []
        diagnostics: list[SessionRecoveryDiagnostic] = []
        for session_root in sorted(self._root.iterdir(), key=lambda path: path.name):
            if session_root.is_symlink() or not session_root.is_dir():
                continue
            paths = _session_paths(session_root)
            if not paths.metadata.is_file():
                continue
            session_id = session_root.name
            try:
                _validate_session_id(session_id)
                metadata = _read_json_object(paths.metadata)
            except (OSError, ValueError, json.JSONDecodeError) as exc:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="persistence_fault",
                        detail=str(exc),
                    )
                )
                continue

            schema_version = metadata.get("schema_version", 0)
            if isinstance(schema_version, bool) or not isinstance(schema_version, int):
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="persistence_fault",
                        detail="session schema_version is malformed",
                    )
                )
                continue
            if schema_version == 0:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="legacy_session_skipped",
                        detail="unversioned schema-v0 session was not mutated",
                    )
                )
                continue
            if schema_version != 1:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="unsupported_session_schema",
                        detail=f"session schema version {schema_version} was not mutated",
                    )
                )
                continue
            if metadata.get("session_id") != session_id:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="persistence_fault",
                        detail="session metadata ID does not match its directory",
                    )
                )
                continue
            state = metadata.get("state")
            if state not in {"active", "completed", "failed", "abandoned"}:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="persistence_fault",
                        detail="native session lifecycle state is malformed",
                    )
                )
                continue
            try:
                _validate_native_lifecycle_metadata(
                    state=state,
                    ended_at=_optional_str(metadata, "ended_at"),
                    end_reason=_optional_str(metadata, "end_reason"),
                    error=_optional_object(metadata.get("error"), "error"),
                )
            except ValueError as exc:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="persistence_fault",
                        detail=str(exc),
                    )
                )
                continue
            if state != "active":
                continue

            if paths.terminal_reserve.is_symlink():
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="terminal_reserve_invalid",
                        detail="stale active session terminal reserve is a symbolic link",
                    )
                )
            elif not paths.terminal_reserve.is_file():
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="terminal_reserve_missing",
                        detail="stale active session terminal reserve is missing",
                    )
                )
            elif paths.terminal_reserve.stat().st_size != _METADATA_MAX_BYTES:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_id,
                        code="terminal_reserve_invalid",
                        detail="stale active session terminal reserve has an invalid size",
                    )
                )

            handle = SessionHandle(session_id=session_id, paths=paths)
            try:
                self.abandon_session(handle)
            except (OSError, ValueError) as exc:
                raise SessionRecoveryError(
                    f"failed to recover stale session {session_id}: {exc}"
                ) from exc
            recovered.append(session_id)

        self._last_recovery = SessionRecoveryResult(
            recovered_session_ids=tuple(recovered),
            diagnostics=tuple(diagnostics),
        )
        return self._last_recovery

    def create_session(
        self,
        *,
        command: str,
        firmware: str | None = None,
        device: str | None = None,
        baseline: bool = False,
        backend_snapshot: BackendSnapshot | None = None,
        workflow: SessionWorkflow | None = None,
        duration_s: float | None = None,
        reconnect_timeout_s: float | None = None,
    ) -> SessionHandle:
        """Create a new session directory and initialize required files."""

        _validate_session_command(command)
        _validate_native_lifecycle_inputs(
            workflow=workflow,
            duration_s=duration_s,
            reconnect_timeout_s=reconnect_timeout_s,
            backend_snapshot=backend_snapshot,
        )

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
            workflow=workflow,
            duration_s=duration_s,
            reconnect_timeout_s=reconnect_timeout_s,
            evidence_budget_bytes=self._evidence_budget_bytes,
        )

        if workflow is not None:
            paths.terminal_reserve.write_bytes(b"\0" * _METADATA_MAX_BYTES)
        paths.uart_raw.write_bytes(b"")
        paths.uart_events.write_text("", encoding="utf-8")
        paths.hardware_events.write_text("", encoding="utf-8")
        _write_json(paths.detected_patterns, [])
        _write_json(paths.metadata, metadata)

        return SessionHandle(session_id=session_id, paths=paths)

    def complete_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str = "duration_elapsed",
    ) -> None:
        """Transition one active native session to completed exactly once."""

        self._terminalize_session(
            handle,
            state="completed",
            end_reason=end_reason,
            error=None,
            truncation=None,
        )

    def fail_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str,
        error_code: str,
        detail: str,
    ) -> None:
        """Transition one active native session to failed with bounded detail."""

        self._terminalize_session(
            handle,
            state="failed",
            end_reason=end_reason,
            error=_bounded_error(error_code, detail),
            truncation=None,
        )

    def abandon_session(self, handle: SessionHandle) -> None:
        """Transition one stale active native session during startup recovery."""

        self._terminalize_session(
            handle,
            state="abandoned",
            end_reason="service_restart",
            error=None,
            truncation=None,
        )

    def _terminalize_session(
        self,
        handle: SessionHandle,
        *,
        state: Literal["completed", "failed", "abandoned"],
        end_reason: str,
        error: dict[str, object] | None,
        truncation: dict[str, object] | None,
        metadata_mutator: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        metadata = _read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 1:
            raise ValueError("only native schema-v1 sessions can be terminalized")
        if metadata.get("state") != "active":
            raise ValueError("session lifecycle transition requires active state")
        if metadata_mutator is not None:
            metadata_mutator(metadata)
        ended_at = _format_utc_timestamp(self._clock())
        metadata["state"] = state
        metadata["ended_at"] = ended_at
        metadata["end_reason"] = end_reason
        metadata["error"] = error
        if truncation is not None:
            metadata["truncated"] = True
            metadata["truncation"] = truncation
        segments = metadata.get("segments")
        if not isinstance(segments, list) or not segments or not isinstance(segments[-1], dict):
            raise ValueError("native session must contain a current segment")
        segments[-1]["ended_at"] = ended_at
        segments[-1]["end_reason"] = end_reason
        _refresh_storage_accounting(metadata, handle.paths)
        handle.paths.terminal_reserve.unlink(missing_ok=True)
        _write_json_atomic(handle.paths.metadata, metadata)

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

        _require_session_appendable(handle)
        if event.segment_id != result.segment_id:
            raise ValueError("UART event and capture result segments must match")
        if event.channel != result.channel:
            raise ValueError("UART event and capture result channels must match")
        if event.timestamp_us != result.timestamp_us:
            raise ValueError("UART event and capture result timestamps must match")

        uart_event_bytes = _serialize_jsonl(_uart_event_json(event, timestamp_epoch))
        pattern_records = _detected_pattern_records(
            result,
            segment_id=event.segment_id,
            timestamp_epoch=timestamp_epoch,
        )
        detected_patterns_bytes: bytes | None = None
        detected_patterns_delta = 0
        if pattern_records:
            detected_patterns = _read_json_list(handle.paths.detected_patterns)
            detected_patterns.extend(pattern_records)
            detected_patterns_bytes = _serialize_json(detected_patterns)
            detected_patterns_delta = (
                len(detected_patterns_bytes) - handle.paths.detected_patterns.stat().st_size
            )
        hardware_event_bytes = tuple(
            _serialize_jsonl(
                _line_limit_exceeded_event_json(
                    result,
                    oversized_line,
                    timestamp_epoch=timestamp_epoch,
                )
            )
            for oversized_line in result.oversized_lines
        )
        evidence_bytes = (
            len(event.data)
            + len(uart_event_bytes)
            + detected_patterns_delta
            + sum(len(record) for record in hardware_event_bytes)
        )
        self._preflight_evidence(
            handle,
            evidence_bytes=evidence_bytes,
            rejected_unit_type="uart_receive",
            rejected_uart_payload_bytes=len(event.data),
            segment_id=event.segment_id,
            channel=event.channel,
            timestamp_us=event.timestamp_us,
        )

        _append_bytes(handle.paths.uart_raw, event.data)
        _append_serialized(handle.paths.uart_events, uart_event_bytes)
        if detected_patterns_bytes is not None:
            _write_serialized(handle.paths.detected_patterns, detected_patterns_bytes)
        for record in hardware_event_bytes:
            _append_serialized(handle.paths.hardware_events, record)

        metadata = _read_json_object(handle.paths.metadata)
        if result.newly_oversized_line_count:
            _record_line_processing(
                metadata,
                newly_oversized_line_count=result.newly_oversized_line_count,
            )
        _record_metadata_segment_timestamp(
            metadata,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
        )
        _refresh_storage_accounting(metadata, handle.paths)
        _write_json(handle.paths.metadata, metadata)

    def _preflight_evidence(
        self,
        handle: SessionHandle,
        *,
        evidence_bytes: int,
        rejected_unit_type: Literal[
            "uart_receive", "hardware_event", "session_event", "uart_tx_attempt"
        ],
        rejected_uart_payload_bytes: int | None,
        segment_id: int | None,
        channel: int | None,
        timestamp_us: int | None,
        rejected_metadata_mutator: Callable[[dict[str, object]], None] | None = None,
    ) -> None:
        metadata = _read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 1:
            return
        storage = _optional_object(metadata.get("storage"), "storage")
        if storage is None:
            raise ValueError("native session storage metadata is required")
        budget = storage.get("evidence_budget_bytes")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
            raise ValueError("native session evidence budget is invalid")
        current_bytes = _evidence_file_bytes(handle.paths)
        projected_bytes = current_bytes + evidence_bytes
        if projected_bytes <= budget:
            return

        truncation: dict[str, object] = {
            "reason": "size_limit",
            "rejected_unit_type": rejected_unit_type,
            "rejected_unit_evidence_bytes": evidence_bytes,
            "projected_evidence_bytes": projected_bytes,
            "rejected_uart_payload_bytes": rejected_uart_payload_bytes,
            "segment_id": segment_id,
            "channel": channel,
            "timestamp_us": timestamp_us,
            "occurred_at": _format_utc_timestamp(self._clock()),
        }
        self._terminalize_session(
            handle,
            state="completed",
            end_reason="size_limit",
            error=None,
            truncation=truncation,
            metadata_mutator=rejected_metadata_mutator,
        )
        raise EvidenceQuotaExceeded(truncation)

    def append_uart_processing_result(
        self,
        handle: SessionHandle,
        *,
        result: UartCaptureResult,
        timestamp_epoch: int = 0,
    ) -> None:
        """Persist derived records finalized at segment or session close."""

        _require_session_appendable(handle)
        for oversized_line in result.oversized_lines:
            event_bytes = _serialize_jsonl(
                _line_limit_exceeded_event_json(
                    result,
                    oversized_line,
                    timestamp_epoch=timestamp_epoch,
                )
            )
            self._preflight_evidence(
                handle,
                evidence_bytes=len(event_bytes),
                rejected_unit_type="session_event",
                rejected_uart_payload_bytes=None,
                segment_id=result.segment_id,
                channel=result.channel,
                timestamp_us=oversized_line.timestamp_us,
            )
            _append_serialized(handle.paths.hardware_events, event_bytes)
        if result.oversized_lines:
            metadata = _read_json_object(handle.paths.metadata)
            _refresh_storage_accounting(metadata, handle.paths)
            _write_json(handle.paths.metadata, metadata)

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer overflow event to a session."""

        _require_session_appendable(handle)
        event_bytes = _serialize_jsonl(_buffer_overflow_event_json(event, timestamp_epoch))

        def record_summary(metadata: dict[str, object]) -> None:
            _record_metadata_segment_timestamp(
                metadata,
                segment_id=event.segment_id,
                timestamp_us=event.timestamp_us,
            )
            metadata["overflow"] = True
            _record_integrity_loss(
                metadata,
                dropped_bytes=event.dropped_bytes,
                cumulative=False,
            )

        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes),
            rejected_unit_type="hardware_event",
            rejected_uart_payload_bytes=None,
            segment_id=event.segment_id,
            channel=event.channel,
            timestamp_us=event.timestamp_us,
            rejected_metadata_mutator=record_summary,
        )
        metadata = _read_json_object(handle.paths.metadata)
        record_summary(metadata)

        _append_serialized(handle.paths.hardware_events, event_bytes)
        _refresh_storage_accounting(metadata, handle.paths)
        _write_json(handle.paths.metadata, metadata)

    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer status telemetry event to a session."""

        _require_session_appendable(handle)
        event_bytes = _serialize_jsonl(_buffer_status_event_json(event, timestamp_epoch))

        def record_summary(metadata: dict[str, object]) -> None:
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

        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes),
            rejected_unit_type="hardware_event",
            rejected_uart_payload_bytes=None,
            segment_id=event.segment_id,
            channel=None,
            timestamp_us=event.timestamp_us,
            rejected_metadata_mutator=record_summary,
        )
        metadata = _read_json_object(handle.paths.metadata)
        record_summary(metadata)

        _append_serialized(handle.paths.hardware_events, event_bytes)
        _refresh_storage_accounting(metadata, handle.paths)
        _write_json(handle.paths.metadata, metadata)

    def record_segment_context(
        self,
        handle: SessionHandle,
        context: SegmentContext,
    ) -> None:
        """Persist timing provenance before the segment's first evidence event."""

        _require_session_appendable(handle)
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
        _refresh_storage_accounting(metadata, handle.paths)
        _write_json(handle.paths.metadata, metadata)


def _session_paths(root: Path) -> SessionPaths:
    return SessionPaths(
        root=root,
        metadata=root / "metadata.json",
        uart_raw=root / "uart_raw.log",
        uart_events=root / "uart_events.jsonl",
        hardware_events=root / "hardware_events.jsonl",
        detected_patterns=root / "detected_patterns.json",
        terminal_reserve=root / ".terminal-reserve",
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


def _validate_session_command(command: str) -> None:
    if not isinstance(command, str) or not command:
        raise ValueError("session command must not be empty")
    if len(command.encode("utf-8")) > 256:
        raise ValueError("session command must contain at most 256 UTF-8 bytes")
    if any(unicodedata.category(character) == "Cc" for character in command):
        raise ValueError("session command must not contain control characters")


def _validate_native_lifecycle_inputs(
    *,
    workflow: SessionWorkflow | None,
    duration_s: float | None,
    reconnect_timeout_s: float | None,
    backend_snapshot: BackendSnapshot | None,
) -> None:
    if workflow is None:
        if duration_s is not None or reconnect_timeout_s is not None:
            raise ValueError("native lifecycle values require a workflow")
        return
    if backend_snapshot is None:
        raise ValueError("native sessions require a backend snapshot")
    if workflow in {"capture", "boot_test"}:
        _require_positive_number(duration_s, "duration_s")
    elif duration_s is not None:
        raise ValueError("wait-pattern duration_s must be null")
    _require_positive_number(reconnect_timeout_s, "reconnect_timeout_s")


def _require_positive_number(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ValueError(f"native session {field} must be a positive finite number")
    return float(value)


def _initial_metadata(
    *,
    session_id: str,
    started_at: str,
    command: str,
    firmware: str | None,
    device: str | None,
    baseline: bool,
    backend_snapshot: BackendSnapshot | None,
    workflow: SessionWorkflow | None,
    duration_s: float | None,
    reconnect_timeout_s: float | None,
    evidence_budget_bytes: int,
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
        "line_processing": _line_processing_json(LineProcessing()),
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
    if workflow is not None:
        metadata = {
            "schema_version": 1,
            "session_id": session_id,
            "started_at": started_at,
            "state": "active",
            "workflow": workflow,
            "duration_s": duration_s,
            "reconnect_timeout_s": reconnect_timeout_s,
            "ended_at": None,
            "end_reason": None,
            "error": None,
            "command": command,
            "backend_mode": backend_snapshot.info.mode,
            "backend_identity": {
                "port": backend_snapshot.info.port,
                "device": backend_snapshot.info.device,
                "firmware": backend_snapshot.info.firmware,
            },
            "backend_capabilities": sorted(backend_snapshot.info.capabilities),
            "capabilities": sorted(backend_snapshot.capabilities),
            "capability_policy": _capability_policy_json(backend_snapshot.capability_policy),
            "commanded_boot_mode": None,
            "integrity": _integrity_json(backend_snapshot.integrity),
            "line_processing": _line_processing_json(LineProcessing()),
            "storage": {
                "evidence_budget_bytes": evidence_budget_bytes,
                "evidence_bytes_written": 3,
                "metadata_max_bytes": _METADATA_MAX_BYTES,
            },
            "truncated": False,
            "truncation": None,
            "interrupted": False,
            "resumed": False,
            "overflow": False,
            "segments": [_backend_segment_json(backend_snapshot, started_at=started_at)],
        }
    return metadata


def _summary_from_metadata(
    metadata: dict[str, object],
    *,
    detected_patterns: list[object],
) -> SessionSummary:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

    schema_version = metadata.get("schema_version", 0)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise ValueError("session metadata schema_version must be an integer")
    if schema_version not in {0, 1}:
        raise ValueError(f"unsupported session schema version: {schema_version}")
    native = schema_version == 1
    backend_mode = _optional_backend_mode(metadata.get("backend_mode"))
    backend_identity = _optional_object(metadata.get("backend_identity"), "backend_identity")
    state = _native_state(metadata.get("state")) if native else None
    workflow = _native_workflow(metadata.get("workflow")) if native else None
    duration_s = _optional_positive_number(metadata.get("duration_s")) if native else None
    reconnect_timeout_s = (
        _optional_positive_number(metadata.get("reconnect_timeout_s")) if native else None
    )
    ended_at = _optional_str(metadata, "ended_at") if native else None
    end_reason = _optional_str(metadata, "end_reason") if native else None
    error = _optional_object(metadata.get("error"), "error") if native else None
    if native:
        if backend_mode is None or backend_identity is None:
            raise ValueError("native session backend identity is required")
        if not 1 <= len(segments) <= 32:
            raise ValueError("native session must contain 1..32 segments")
        if workflow in {"capture", "boot_test"} and duration_s is None:
            raise ValueError("native capture-like session duration_s is required")
        if reconnect_timeout_s is None:
            raise ValueError("native session reconnect_timeout_s is required")
        _validate_native_lifecycle_metadata(
            state=state,
            ended_at=ended_at,
            end_reason=end_reason,
            error=error,
        )
    return SessionSummary(
        session_id=_required_str(metadata, "session_id"),
        started_at=_required_str(metadata, "started_at"),
        command=_required_str(metadata, "command"),
        truncated=_required_bool(metadata, "truncated"),
        interrupted=_required_bool(metadata, "interrupted"),
        resumed=_required_bool(metadata, "resumed"),
        overflow=_required_bool(metadata, "overflow"),
        baseline=False if native else _required_bool(metadata, "baseline"),
        firmware=(
            _optional_str(backend_identity, "firmware")
            if native and backend_identity is not None
            else _optional_str(metadata, "firmware")
        ),
        device=(
            _optional_str(backend_identity, "device")
            if native and backend_identity is not None
            else _optional_str(metadata, "device")
        ),
        segment_count=len(segments),
        backend_mode=backend_mode,
        port=(_optional_str(backend_identity, "port") if backend_identity is not None else None),
        backend_capabilities=_optional_string_tuple(metadata, "backend_capabilities"),
        capabilities=_optional_string_tuple(metadata, "capabilities"),
        capability_policy=_optional_capability_policy(metadata.get("capability_policy")),
        integrity=_optional_integrity(metadata.get("integrity")),
        segment_contexts=_segment_contexts(segments),
        first_error=_first_error(detected_patterns, segments),
        line_processing=_optional_line_processing(metadata.get("line_processing")),
        schema_version=schema_version,
        state=state,
        workflow=workflow,
        duration_s=duration_s,
        reconnect_timeout_s=reconnect_timeout_s,
        ended_at=ended_at,
        end_reason=end_reason,
        error=error,
        truncation=_optional_object(metadata.get("truncation"), "truncation") if native else None,
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


def _line_processing_json(line_processing: LineProcessing) -> dict[str, object]:
    return {
        "status": line_processing.status,
        "max_line_bytes": line_processing.max_line_bytes,
        "oversized_line_count": line_processing.oversized_line_count,
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


def _native_state(value: object) -> SessionState:
    if value not in {"active", "completed", "failed", "abandoned"}:
        raise ValueError("native session state is invalid")
    return value


def _native_workflow(value: object) -> SessionWorkflow:
    if value not in {"capture", "boot_test", "wait_pattern"}:
        raise ValueError("native session workflow is invalid")
    return value


def _validate_native_lifecycle_metadata(
    *,
    state: SessionState | None,
    ended_at: str | None,
    end_reason: str | None,
    error: dict[str, object] | None,
) -> None:
    if state == "active":
        if ended_at is not None or end_reason is not None or error is not None:
            raise ValueError("active session terminal fields must be null")
        return
    if ended_at is None or end_reason is None:
        raise ValueError("terminal session must contain ended_at and end_reason")
    if state == "failed":
        if error is None:
            raise ValueError("failed session must contain an error")
    elif error is not None:
        raise ValueError("completed or abandoned session error must be null")


def _optional_positive_number(value: object) -> float | None:
    if value is None:
        return None
    return _require_positive_number(value, "numeric lifecycle value")


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


def _optional_line_processing(value: object) -> LineProcessing:
    if value is None:
        return LineProcessing()
    line_processing = _optional_object(value, "line_processing")
    if line_processing is None:
        return LineProcessing()
    status = line_processing.get("status")
    max_line_bytes = line_processing.get("max_line_bytes")
    oversized_line_count = line_processing.get("oversized_line_count")
    if status not in {"complete", "limit_exceeded"}:
        raise ValueError("session metadata line-processing status is invalid")
    if max_line_bytes != MAX_UART_LINE_BYTES:
        raise ValueError("session metadata max_line_bytes is invalid")
    if (
        isinstance(oversized_line_count, bool)
        or not isinstance(oversized_line_count, int)
        or oversized_line_count < 0
    ):
        raise ValueError("session metadata oversized_line_count is invalid")
    if (status == "complete") != (oversized_line_count == 0):
        raise ValueError("session metadata line-processing status/count disagree")
    return LineProcessing(
        status=status,
        max_line_bytes=max_line_bytes,
        oversized_line_count=oversized_line_count,
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
    _write_serialized(path, _serialize_json(value))


def _write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        _write_json(temporary, value)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _refresh_storage_accounting(
    metadata: dict[str, object],
    paths: SessionPaths,
) -> None:
    storage = _optional_object(metadata.get("storage"), "storage")
    if storage is None:
        return
    storage["evidence_bytes_written"] = _evidence_file_bytes(paths)


def _evidence_file_bytes(paths: SessionPaths) -> int:
    return sum(
        path.stat().st_size
        for path in (
            paths.uart_raw,
            paths.uart_events,
            paths.hardware_events,
            paths.detected_patterns,
        )
    )


def _bounded_error(code: str, detail: str) -> dict[str, object]:
    if not isinstance(code, str) or not code:
        raise ValueError("session error code must be a non-empty string")
    if not isinstance(detail, str):
        raise TypeError("session error detail must be a string")
    cleaned = "".join(
        " "
        if character in {"\r", "\n", "\t"}
        else "\ufffd"
        if unicodedata.category(character) == "Cc"
        else character
        for character in detail
    )
    if not cleaned:
        cleaned = code.replace("_", " ")
    encoded = cleaned.encode("utf-8")
    truncated = len(encoded) > 1024
    if truncated:
        prefix = encoded[:1024]
        while True:
            try:
                cleaned = prefix.decode("utf-8")
                break
            except UnicodeDecodeError:
                prefix = prefix[:-1]
    return {
        "code": code,
        "detail": cleaned,
        "detail_truncated": truncated,
    }


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


def _require_session_appendable(handle: SessionHandle) -> None:
    metadata = _read_json_object(handle.paths.metadata)
    schema_version = metadata.get("schema_version", 0)
    if schema_version == 1 and metadata.get("state") != "active":
        raise ValueError("native session evidence can only append while active")


def _append_bytes(path: Path, data: bytes) -> None:
    with path.open("ab") as file:
        file.write(data)


def _append_jsonl(path: Path, value: dict[str, object]) -> None:
    _append_serialized(path, _serialize_jsonl(value))


def _serialize_json(value: object) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def _serialize_jsonl(value: dict[str, object]) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")


def _write_serialized(path: Path, data: bytes) -> None:
    with path.open("wb") as file:
        file.write(data)


def _append_serialized(path: Path, data: bytes) -> None:
    with path.open("ab") as file:
        file.write(data)


def _detected_pattern_records(
    result: UartCaptureResult,
    *,
    segment_id: int,
    timestamp_epoch: int,
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
    return patterns


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


def _line_limit_exceeded_event_json(
    result: UartCaptureResult,
    line: OversizedUartLine,
    *,
    timestamp_epoch: int,
) -> dict[str, object]:
    return {
        "type": "line_limit_exceeded",
        "segment_id": result.segment_id,
        "timestamp_epoch": timestamp_epoch,
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


def _record_line_processing(
    metadata: dict[str, object],
    *,
    newly_oversized_line_count: int,
) -> None:
    current = _optional_line_processing(metadata.get("line_processing"))
    count = current.oversized_line_count + newly_oversized_line_count
    metadata["line_processing"] = _line_processing_json(
        LineProcessing(
            status="limit_exceeded" if count else "complete",
            oversized_line_count=count,
        )
    )


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
