"""Filesystem-backed debug session storage."""

import json
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Literal

import dutchmate_core.session_store.evidence as _evidence
import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.backends.contracts import (
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartReceiveEvent,
)
from dutchmate_core.session_store.models import (
    EvidenceQuotaExceeded,
    FirstError,
    LineProcessing,
    MatchExcerpt,
    SessionHandle,
    SessionPaths,
    SessionRecoveryDiagnostic,
    SessionRecoveryError,
    SessionRecoveryResult,
    SessionState,
    SessionSummary,
    SessionWorkflow,
)
from dutchmate_core.uart_capture.processor import UartCaptureResult
from dutchmate_core.validation import (
    DEFAULT_SESSION_MAX_SIZE_MB,
    session_evidence_budget_bytes,
)

__all__ = [
    "DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES",
    "EvidenceQuotaExceeded",
    "FirstError",
    "LineProcessing",
    "MatchExcerpt",
    "SessionHandle",
    "SessionPaths",
    "SessionRecoveryDiagnostic",
    "SessionRecoveryError",
    "SessionRecoveryResult",
    "SessionState",
    "SessionStore",
    "SessionSummary",
    "SessionWorkflow",
]

DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES = session_evidence_budget_bytes(
    DEFAULT_SESSION_MAX_SIZE_MB
)


class SessionStore:
    """Create filesystem-backed debug sessions."""

    def __init__(
        self,
        root: Path | str = Path(".dutchmate/sessions"),
        *,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], str] | None = None,
        evidence_budget_bytes: int = DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    ) -> None:
        self._root = Path(root)
        self._clock = clock or _metadata._utc_now
        self._id_factory = id_factory or _metadata._random_suffix
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
            paths = _persistence.session_paths(session_root)
            if not paths.metadata.is_file():
                continue
            session_id = session_root.name
            try:
                _metadata._validate_session_id(session_id)
                metadata = _persistence.read_json_object(paths.metadata)
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
                _metadata._validate_native_lifecycle_metadata(
                    state=state,
                    ended_at=_metadata._optional_str(metadata, "ended_at"),
                    end_reason=_metadata._optional_str(metadata, "end_reason"),
                    error=_metadata._optional_object(metadata.get("error"), "error"),
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
            elif paths.terminal_reserve.stat().st_size != _metadata.METADATA_MAX_BYTES:
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

        _metadata._validate_session_command(command)
        _metadata._validate_native_lifecycle_inputs(
            workflow=workflow,
            duration_s=duration_s,
            reconnect_timeout_s=reconnect_timeout_s,
            backend_snapshot=backend_snapshot,
        )

        started_at = self._clock()
        session_id = _metadata._validate_session_id(
            f"{_metadata._format_session_id_timestamp(started_at)}-{self._id_factory()}"
        )
        paths = _persistence.session_paths(self._root / session_id)

        paths.root.mkdir(parents=True, exist_ok=False)
        metadata = _metadata._initial_metadata(
            session_id=session_id,
            started_at=_metadata._format_utc_timestamp(started_at),
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
            paths.terminal_reserve.write_bytes(b"\0" * _metadata.METADATA_MAX_BYTES)
        paths.uart_raw.write_bytes(b"")
        paths.uart_events.write_text("", encoding="utf-8")
        paths.hardware_events.write_text("", encoding="utf-8")
        _persistence.write_json(paths.detected_patterns, [])
        _persistence.write_json(paths.metadata, metadata)

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
            error=_metadata._bounded_error(error_code, detail),
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
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 1:
            raise ValueError("only native schema-v1 sessions can be terminalized")
        if metadata.get("state") != "active":
            raise ValueError("session lifecycle transition requires active state")
        if metadata_mutator is not None:
            metadata_mutator(metadata)
        ended_at = _metadata._format_utc_timestamp(self._clock())
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
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        handle.paths.terminal_reserve.unlink(missing_ok=True)
        _persistence.write_json_atomic(handle.paths.metadata, metadata)

    def load_metadata(self, session_id: str) -> dict[str, object]:
        """Load a session's metadata JSON."""

        session_name = _metadata._validate_session_id(session_id)
        metadata_path = _persistence.session_paths(self._root / session_name).metadata
        with metadata_path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
        if not isinstance(loaded, dict):
            raise ValueError("session metadata must be a JSON object")
        return loaded

    def summarize_session(self, session_id: str) -> SessionSummary:
        """Load and summarize one session's metadata."""

        session_name = _metadata._validate_session_id(session_id)
        paths = _persistence.session_paths(self._root / session_name)
        metadata = self.load_metadata(session_name)
        metadata_summary = _metadata._summary_from_metadata(metadata, detected_patterns=[])
        if metadata_summary.session_id != session_name:
            raise ValueError("session metadata ID must match its directory name")
        return _metadata._summary_from_metadata(
            metadata,
            detected_patterns=_persistence.read_json_list(paths.detected_patterns),
        )

    def list_sessions(self, *, limit: int | None = None) -> tuple[SessionSummary, ...]:
        """Return stored session summaries in newest-first order."""

        _metadata._validate_session_limit(limit)
        if not self._root.exists():
            return ()

        summaries: list[SessionSummary] = []
        for session_root in self._root.iterdir():
            if (
                session_root.is_symlink()
                or not session_root.is_dir()
                or not _persistence.session_paths(session_root).metadata.is_file()
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

        _persistence.require_session_appendable(handle)
        if event.segment_id != result.segment_id:
            raise ValueError("UART event and capture result segments must match")
        if event.channel != result.channel:
            raise ValueError("UART event and capture result channels must match")
        if event.timestamp_us != result.timestamp_us:
            raise ValueError("UART event and capture result timestamps must match")

        uart_event_bytes = _persistence.serialize_jsonl(
            _evidence.uart_event_json(event, timestamp_epoch)
        )
        pattern_records = _evidence.detected_pattern_records(
            result,
            segment_id=event.segment_id,
            timestamp_epoch=timestamp_epoch,
        )
        detected_patterns_bytes: bytes | None = None
        detected_patterns_delta = 0
        if pattern_records:
            detected_patterns = _persistence.read_json_list(handle.paths.detected_patterns)
            detected_patterns.extend(pattern_records)
            detected_patterns_bytes = _persistence.serialize_json(detected_patterns)
            detected_patterns_delta = (
                len(detected_patterns_bytes) - handle.paths.detected_patterns.stat().st_size
            )
        hardware_event_bytes = tuple(
            _persistence.serialize_jsonl(
                _evidence.line_limit_exceeded_event_json(
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

        _persistence.append_bytes(handle.paths.uart_raw, event.data)
        _persistence.append_serialized(handle.paths.uart_events, uart_event_bytes)
        if detected_patterns_bytes is not None:
            _persistence.write_serialized(handle.paths.detected_patterns, detected_patterns_bytes)
        for record in hardware_event_bytes:
            _persistence.append_serialized(handle.paths.hardware_events, record)

        metadata = _persistence.read_json_object(handle.paths.metadata)
        if result.newly_oversized_line_count:
            _metadata._record_line_processing(
                metadata,
                newly_oversized_line_count=result.newly_oversized_line_count,
            )
        _metadata._record_metadata_segment_timestamp(
            metadata,
            segment_id=event.segment_id,
            timestamp_us=event.timestamp_us,
        )
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        _persistence.write_json(handle.paths.metadata, metadata)
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
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 1:
            return
        storage = _metadata._optional_object(metadata.get("storage"), "storage")
        if storage is None:
            raise ValueError("native session storage metadata is required")
        budget = storage.get("evidence_budget_bytes")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
            raise ValueError("native session evidence budget is invalid")
        current_bytes = _persistence.evidence_file_bytes(handle.paths)
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
            "occurred_at": _metadata._format_utc_timestamp(self._clock()),
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

        _persistence.require_session_appendable(handle)
        for oversized_line in result.oversized_lines:
            event_bytes = _persistence.serialize_jsonl(
                _evidence.line_limit_exceeded_event_json(
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
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
        if result.oversized_lines:
            metadata = _persistence.read_json_object(handle.paths.metadata)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            _persistence.write_json(handle.paths.metadata, metadata)

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer overflow event to a session."""

        _persistence.require_session_appendable(handle)
        event_bytes = _persistence.serialize_jsonl(
            _evidence.buffer_overflow_event_json(event, timestamp_epoch)
        )

        def record_summary(metadata: dict[str, object]) -> None:
            _metadata._record_metadata_segment_timestamp(
                metadata,
                segment_id=event.segment_id,
                timestamp_us=event.timestamp_us,
            )
            metadata["overflow"] = True
            _metadata._record_integrity_loss(
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
        metadata = _persistence.read_json_object(handle.paths.metadata)
        record_summary(metadata)

        _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        _persistence.write_json(handle.paths.metadata, metadata)
    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Append one buffer status telemetry event to a session."""

        _persistence.require_session_appendable(handle)
        event_bytes = _persistence.serialize_jsonl(
            _evidence.buffer_status_event_json(event, timestamp_epoch)
        )

        def record_summary(metadata: dict[str, object]) -> None:
            _metadata._record_metadata_segment_timestamp(
                metadata,
                segment_id=event.segment_id,
                timestamp_us=event.timestamp_us,
            )
            if event.dropped_bytes_total > 0 or event.overflow_events > 0:
                metadata["overflow"] = True
                _metadata._record_integrity_loss(
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
        metadata = _persistence.read_json_object(handle.paths.metadata)
        record_summary(metadata)

        _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        _persistence.write_json(handle.paths.metadata, metadata)

    def record_segment_context(
        self,
        handle: SessionHandle,
        context: SegmentContext,
    ) -> None:
        """Persist timing provenance before the segment's first evidence event."""

        _persistence.require_session_appendable(handle)
        metadata = _persistence.read_json_object(handle.paths.metadata)
        segment = _metadata._metadata_segment(metadata, context.segment_id)
        timestamp = _metadata._timestamp_json(context.timestamp)
        existing = segment.get("timestamp")
        if existing is not None and existing != timestamp:
            raise ValueError("session segment timestamp provenance cannot change")
        if existing is None:
            segment["timestamp"] = timestamp
            _persistence.write_json(handle.paths.metadata, metadata)

    def _record_segment_timestamp(
        self,
        handle: SessionHandle,
        *,
        segment_id: int,
        timestamp_us: int,
    ) -> None:
        metadata = _persistence.read_json_object(handle.paths.metadata)
        _metadata._record_metadata_segment_timestamp(
            metadata,
            segment_id=segment_id,
            timestamp_us=timestamp_us,
        )
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        _persistence.write_json(handle.paths.metadata, metadata)
