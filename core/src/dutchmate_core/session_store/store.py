"""Filesystem-backed debug session storage."""

import json
from collections.abc import Callable
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Literal

import dutchmate_core.session_store.baseline as _baseline
import dutchmate_core.session_store.comparison as _comparison
import dutchmate_core.session_store.evidence as _evidence
import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
import dutchmate_core.session_store.retention as _retention
import dutchmate_core.session_store.transactions as _transactions
from dutchmate_core.backends.contracts import (
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartReceiveEvent,
)
from dutchmate_core.session_store.log_replay import (
    DEFAULT_RECENT_LOG_LINES,
)
from dutchmate_core.session_store.log_replay import (
    replay_recent_logs as _replay_recent_logs,
)
from dutchmate_core.session_store.models import (
    BaselineError,
    BaselineMutationResult,
    BaselinePointer,
    CommandedBootMode,
    EvidenceQuotaExceeded,
    FirstError,
    LineProcessing,
    MatchExcerpt,
    RecentLogs,
    SessionComparison,
    SessionComparisonError,
    SessionDetail,
    SessionHandle,
    SessionListPage,
    SessionPaths,
    SessionPersistenceError,
    SessionRecoveryDiagnostic,
    SessionRecoveryError,
    SessionRecoveryResult,
    SessionRetentionStatus,
    SessionState,
    SessionSummary,
    SessionWorkflow,
    WaitPatternResult,
)
from dutchmate_core.session_store.retrieval import (
    DEFAULT_SESSION_PAGE_LIMIT,
)
from dutchmate_core.session_store.retrieval import (
    get_session_detail as _get_session_detail,
)
from dutchmate_core.session_store.retrieval import (
    list_session_page as _list_session_page,
)
from dutchmate_core.uart_capture.processor import UartCaptureResult
from dutchmate_core.validation import (
    DEFAULT_SESSION_MAX_SIZE_MB,
    session_evidence_budget_bytes,
)

__all__ = [
    "DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES",
    "BaselineError",
    "BaselineMutationResult",
    "BaselinePointer",
    "EvidenceQuotaExceeded",
    "FirstError",
    "LineProcessing",
    "MatchExcerpt",
    "RecentLogs",
    "SessionComparison",
    "SessionComparisonError",
    "SessionHandle",
    "SessionDetail",
    "SessionListPage",
    "SessionPaths",
    "SessionPersistenceError",
    "SessionRecoveryDiagnostic",
    "SessionRecoveryError",
    "SessionRecoveryResult",
    "SessionRetentionStatus",
    "SessionState",
    "SessionStore",
    "SessionSummary",
    "SessionWorkflow",
    "WaitPatternResult",
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
        max_count: int | None = None,
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
        if max_count is not None and (
            isinstance(max_count, bool) or not isinstance(max_count, int) or max_count <= 0
        ):
            raise ValueError("session max count must be a positive integer or null")
        self._max_count = max_count
        self._store_lock = RLock()
        self._recovering = False
        self._last_recovery = SessionRecoveryResult()
        self._retention_status = SessionRetentionStatus(
            enabled=max_count is not None,
            max_count=max_count,
        )
        self._uart_tx_result_reservations: dict[
            tuple[str, str], tuple[int, int, int]
        ] = {}

    @property
    def root(self) -> Path:
        """Directory containing all sessions."""

        return self._root

    @property
    def last_recovery(self) -> SessionRecoveryResult:
        """Most recent startup-recovery result for this store instance."""

        return self._last_recovery

    @property
    def retention_status(self) -> SessionRetentionStatus:
        """Return the outcome of the most recent retention pass."""

        with self._store_lock:
            return self._retention_status

    def recover_stale_sessions(self) -> SessionRecoveryResult:
        """Abandon stale native active sessions without mutating other schemas."""

        with self._store_lock:
            self._recovering = True
            try:
                result = self._recover_stale_sessions_locked()
            finally:
                self._recovering = False
            self._apply_retention_locked()
            return result

    def _recover_stale_sessions_locked(self) -> SessionRecoveryResult:
        """Perform startup recovery while the store-wide lock is held."""

        if not self._root.exists():
            self._last_recovery = SessionRecoveryResult()
            return self._last_recovery

        recovered: list[str] = []
        diagnostics: list[SessionRecoveryDiagnostic] = []
        for session_root in sorted(self._root.iterdir(), key=lambda path: path.name):
            if session_root.is_symlink() or not session_root.is_dir():
                continue
            paths = _persistence.session_paths(session_root)
            try:
                transaction_recovery = _transactions.recover_evidence_transaction(paths)
            except SessionPersistenceError as exc:
                raise SessionRecoveryError(
                    "failed to recover evidence transaction "
                    f"{session_root.name}: {exc}"
                ) from exc
            if transaction_recovery is not None:
                diagnostics.append(
                    SessionRecoveryDiagnostic(
                        session_id=session_root.name,
                        code=f"evidence_transaction_{transaction_recovery}",
                        detail=(
                            "interrupted evidence transaction was "
                            f"{transaction_recovery}"
                        ),
                    )
                )
            if not paths.metadata.is_file():
                continue
            session_id = session_root.name
            try:
                _metadata._validate_session_id(session_id)
                metadata = _persistence.read_json_object(paths.metadata)
            except (
                OSError,
                SessionPersistenceError,
                ValueError,
                json.JSONDecodeError,
            ) as exc:
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
            except (OSError, SessionPersistenceError, ValueError) as exc:
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
        commanded_boot_mode: CommandedBootMode | None = None,
        wait_pattern: str | None = None,
        timeout_s: float | None = None,
    ) -> SessionHandle:
        """Create a new session directory and initialize required files."""

        with self._store_lock:
            return self._create_session_locked(
                command=command,
                firmware=firmware,
                device=device,
                baseline=baseline,
                backend_snapshot=backend_snapshot,
                workflow=workflow,
                duration_s=duration_s,
                reconnect_timeout_s=reconnect_timeout_s,
                commanded_boot_mode=commanded_boot_mode,
                wait_pattern=wait_pattern,
                timeout_s=timeout_s,
            )

    def _create_session_locked(
        self,
        *,
        command: str,
        firmware: str | None,
        device: str | None,
        baseline: bool,
        backend_snapshot: BackendSnapshot | None,
        workflow: SessionWorkflow | None,
        duration_s: float | None,
        reconnect_timeout_s: float | None,
        commanded_boot_mode: CommandedBootMode | None,
        wait_pattern: str | None,
        timeout_s: float | None,
    ) -> SessionHandle:
        """Create one session while the store-wide lock is held."""

        _metadata._validate_session_command(command)
        _metadata._validate_native_lifecycle_inputs(
            workflow=workflow,
            duration_s=duration_s,
            reconnect_timeout_s=reconnect_timeout_s,
            commanded_boot_mode=commanded_boot_mode,
            backend_snapshot=backend_snapshot,
            wait_pattern=wait_pattern,
            timeout_s=timeout_s,
        )

        started_at = self._clock()
        session_id = _metadata._validate_session_id(
            f"{_metadata._format_session_id_timestamp(started_at)}-{self._id_factory()}"
        )
        paths = _persistence.session_paths(self._root / session_id)

        _persistence.create_directory(paths.root)
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
            commanded_boot_mode=commanded_boot_mode,
            wait_pattern=wait_pattern,
            timeout_s=timeout_s,
            evidence_budget_bytes=self._evidence_budget_bytes,
        )

        if workflow is not None:
            _persistence.write_serialized(
                paths.terminal_reserve,
                b"\0" * _metadata.METADATA_MAX_BYTES,
            )
        _persistence.write_serialized(paths.uart_raw, b"")
        _persistence.write_serialized(paths.uart_events, b"")
        _persistence.write_serialized(paths.hardware_events, b"")
        _persistence.write_json(paths.detected_patterns, [])
        serialized_metadata = _persistence.serialize_json(metadata)
        _require_metadata_capacity(serialized_metadata)
        _persistence.write_serialized(paths.metadata, serialized_metadata)

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

    def complete_wait_pattern(
        self,
        handle: SessionHandle,
        *,
        matched: bool,
        detected_pattern_index: int | None,
    ) -> None:
        """Complete one wait session with an authoritative optional match index."""

        if not isinstance(matched, bool):
            raise ValueError("wait matched must be a boolean")
        if matched != (detected_pattern_index is not None):
            raise ValueError("wait match flag and detected index must agree")
        if detected_pattern_index is not None and (
            isinstance(detected_pattern_index, bool)
            or not isinstance(detected_pattern_index, int)
            or detected_pattern_index < 0
        ):
            raise ValueError("wait detected-pattern index must be non-negative")
        detected_pattern = (
            _evidence.detected_pattern_at(
                _persistence.read_json_list(handle.paths.detected_patterns),
                detected_pattern_index,
            )
            if detected_pattern_index is not None
            else None
        )

        def record_wait_result(metadata: dict[str, object]) -> None:
            if metadata.get("workflow") != "wait_pattern":
                raise ValueError("wait completion requires a wait-pattern session")
            if detected_pattern is not None and detected_pattern.pattern != metadata.get(
                "pattern"
            ):
                raise ValueError("wait detected record does not match requested pattern")
            metadata["matched"] = matched
            metadata["detected_pattern_index"] = detected_pattern_index

        self._terminalize_session(
            handle,
            state="completed",
            end_reason="pattern_matched" if matched else "timeout",
            error=None,
            truncation=None,
            metadata_mutator=record_wait_result,
        )

    def load_detected_pattern(
        self,
        session_id: str,
        detected_pattern_index: int,
    ) -> FirstError:
        """Load one authoritative reference-bearing detected-pattern record."""

        session_name = _metadata._validate_session_id(session_id)
        paths = _persistence.session_paths(self._root / session_name)
        patterns = _persistence.read_json_list(paths.detected_patterns)
        return _evidence.detected_pattern_at(patterns, detected_pattern_index)

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
        with self._store_lock:
            self._terminalize_session_locked(
                handle,
                state=state,
                end_reason=end_reason,
                error=error,
                truncation=truncation,
                metadata_mutator=metadata_mutator,
            )
            if not self._recovering:
                self._apply_retention_locked(held_session_ids=frozenset({handle.session_id}))

    def _terminalize_session_locked(
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
        if metadata.get("workflow") == "wait_pattern" and metadata.get("matched") is None:
            metadata["matched"] = False
            metadata["detected_pattern_index"] = None
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
        if segments[-1].get("ended_at") is None:
            if segments[-1].get("end_reason") is not None:
                raise ValueError("open session segment cannot have an end reason")
            segments[-1]["ended_at"] = ended_at
            segments[-1]["end_reason"] = end_reason
        elif segments[-1].get("end_reason") is None:
            raise ValueError("closed session segment must have an end reason")
        _persistence.refresh_storage_accounting(metadata, handle.paths)
        serialized_metadata = _persistence.serialize_json(metadata)
        _require_metadata_capacity(serialized_metadata)
        _persistence.remove_file(handle.paths.terminal_reserve, missing_ok=True)
        _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        for reservation_key in tuple(self._uart_tx_result_reservations):
            if reservation_key[0] == handle.session_id:
                del self._uart_tx_result_reservations[reservation_key]

    def load_metadata(self, session_id: str) -> dict[str, object]:
        """Load a session's metadata JSON."""

        with self._store_lock:
            session_name = _metadata._validate_session_id(session_id)
            metadata_path = _persistence.session_paths(self._root / session_name).metadata
            return _persistence.read_json_object(metadata_path)

    def summarize_session(self, session_id: str) -> SessionSummary:
        """Load and summarize one session's metadata."""

        with self._store_lock:
            session_name = _metadata._validate_session_id(session_id)
            paths = _persistence.session_paths(self._root / session_name)
            metadata = self.load_metadata(session_name)
            metadata_summary = _metadata._summary_from_metadata(metadata, detected_patterns=[])
            if metadata_summary.session_id != session_name:
                raise ValueError("session metadata ID must match its directory name")
            summary = _metadata._summary_from_metadata(
                metadata,
                detected_patterns=_persistence.read_json_list(paths.detected_patterns),
            )
            if summary.schema_version != 1:
                return summary
            pointer = _baseline.read_baseline_pointer(self._root)
            return replace(
                summary,
                baseline=pointer is not None and pointer.session_id == session_name,
            )

    def list_sessions(self, *, limit: int | None = None) -> tuple[SessionSummary, ...]:
        """Return stored session summaries in newest-first order."""

        with self._store_lock:
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

    def list_session_page(
        self,
        *,
        limit: int = DEFAULT_SESSION_PAGE_LIMIT,
        cursor: str | None = None,
    ) -> SessionListPage:
        """Return one stable bounded native/legacy session page."""

        with self._store_lock:
            pointer = _baseline.read_baseline_pointer(self._root)
            return _list_session_page(
                self._root,
                limit=limit,
                cursor=cursor,
                baseline_session_id=(pointer.session_id if pointer is not None else None),
            )

    def get_session_detail(self, session_id: str) -> SessionDetail:
        """Return bounded schema-aware detail for one stored session."""

        with self._store_lock:
            _metadata._validate_session_id(session_id)
            pointer = _baseline.read_baseline_pointer(self._root)
            return _get_session_detail(
                self._root,
                session_id,
                baseline_session_id=(pointer.session_id if pointer is not None else None),
            )

    def replay_recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = DEFAULT_RECENT_LOG_LINES,
        active_session_id: str | None = None,
    ) -> RecentLogs:
        """Return bounded replayed UART lines for one selected native session."""

        with self._store_lock:
            return _replay_recent_logs(
                self._root,
                session_id=session_id,
                lines=lines,
                active_session_id=active_session_id,
            )

    def run_retention(self) -> SessionRetentionStatus:
        """Apply the configured count limit and return its current status."""

        with self._store_lock:
            return self._apply_retention_locked()

    def read_baseline(self) -> BaselinePointer | None:
        """Return the validated project-wide baseline pointer, if present."""

        with self._store_lock:
            return _baseline.read_baseline_pointer(self._root)

    def mark_baseline(self, session_id: str) -> BaselineMutationResult:
        """Designate one eligible native session as the project baseline."""

        with self._store_lock:
            result = _baseline.mark_baseline(
                self._root,
                session_id,
                clock=self._clock,
            )
            self._apply_retention_locked()
            return result

    def clear_baseline(self, session_id: str) -> BaselineMutationResult:
        """Clear the project baseline only when it names the requested session."""

        with self._store_lock:
            result = _baseline.clear_baseline(self._root, session_id)
            self._apply_retention_locked()
            return result

    def compare_session(self, session_id: str) -> SessionComparison:
        """Compare one terminal capture or boot test with the current baseline."""

        with self._store_lock:
            _metadata._validate_session_id(session_id)
            return _comparison.compare_session(self._root, session_id)

    def _apply_retention_locked(
        self,
        *,
        held_session_ids: frozenset[str] = frozenset(),
    ) -> SessionRetentionStatus:
        if self._max_count is None:
            self._retention_status = SessionRetentionStatus()
            return self._retention_status
        self._retention_status = _retention.apply_session_retention(
            self._root,
            max_count=self._max_count,
            held_session_ids=held_session_ids,
        )
        return self._retention_status

    def append_uart_capture(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        result: UartCaptureResult,
        timestamp_epoch: int = 0,
    ) -> tuple[int, ...]:
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
        detected_pattern_indexes: tuple[int, ...] = ()
        if pattern_records:
            detected_patterns = _persistence.read_json_list(handle.paths.detected_patterns)
            first_index = len(detected_patterns)
            detected_patterns.extend(pattern_records)
            detected_pattern_indexes = tuple(
                range(first_index, first_index + len(pattern_records))
            )
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
        append_paths = [handle.paths.uart_raw, handle.paths.uart_events]
        if hardware_event_bytes:
            append_paths.append(handle.paths.hardware_events)
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=append_paths,
            replace_detected_patterns=detected_patterns_bytes is not None,
        ) as transaction:
            _persistence.append_bytes(handle.paths.uart_raw, event.data)
            _persistence.append_serialized(handle.paths.uart_events, uart_event_bytes)
            if detected_patterns_bytes is not None:
                _persistence.write_serialized(
                    handle.paths.detected_patterns,
                    detected_patterns_bytes,
                )
            for record in hardware_event_bytes:
                _persistence.append_serialized(handle.paths.hardware_events, record)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        return detected_pattern_indexes

    def _preflight_evidence(
        self,
        handle: SessionHandle,
        *,
        evidence_bytes: int,
        rejected_unit_type: Literal[
            "uart_receive",
            "hardware_event",
            "session_event",
            "control_action",
            "uart_tx_attempt",
        ],
        rejected_uart_payload_bytes: int | None,
        segment_id: int | None,
        channel: int | None,
        timestamp_us: int | None,
        rejected_metadata_mutator: Callable[[dict[str, object]], None] | None = None,
        released_uart_tx_reservation: tuple[str, str] | None = None,
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
        reserved_result_bytes = sum(
            reserved_bytes
            for reservation_key, (reserved_bytes, _payload_bytes, _segment_id) in (
                self._uart_tx_result_reservations.items()
            )
            if reservation_key[0] == handle.session_id
            and reservation_key != released_uart_tx_reservation
        )
        projected_bytes = current_bytes + evidence_bytes + reserved_result_bytes
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
            metadata = _persistence.read_json_object(handle.paths.metadata)
            with _transactions.evidence_transaction(
                handle.paths,
                append_paths=[handle.paths.hardware_events],
            ) as transaction:
                _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
                _persistence.refresh_storage_accounting(metadata, handle.paths)
                serialized_metadata = _persistence.serialize_json(metadata)
                _require_metadata_capacity(serialized_metadata)
                transaction.prepare_metadata(serialized_metadata)
                _persistence.write_serialized(handle.paths.metadata, serialized_metadata)

    def append_control_action(
        self,
        handle: SessionHandle,
        *,
        action: Literal["reset"],
        segment_id: int,
        performed_at: str,
        pulse_ms: int,
        timestamp_us: int | None,
        device_timestamp_us: int | None,
    ) -> None:
        """Append one accepted normalized control action atomically."""

        _persistence.require_session_appendable(handle)
        event_bytes = _persistence.serialize_jsonl(
            _evidence.control_action_event_json(
                action=action,
                segment_id=segment_id,
                performed_at=performed_at,
                pulse_ms=pulse_ms,
                timestamp_us=timestamp_us,
                device_timestamp_us=device_timestamp_us,
            )
        )
        metadata = _persistence.read_json_object(handle.paths.metadata)
        _metadata._metadata_segment(metadata, segment_id)
        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes),
            rejected_unit_type="control_action",
            rejected_uart_payload_bytes=None,
            segment_id=segment_id,
            channel=None,
            timestamp_us=timestamp_us,
        )
        if timestamp_us is not None:
            _metadata._record_metadata_segment_timestamp(
                metadata,
                segment_id=segment_id,
                timestamp_us=timestamp_us,
            )
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)

    def append_uart_tx_attempt(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        segment_id: int,
        attempted_at: str,
        data: bytes,
    ) -> None:
        """Durably append a forced-send attempt and reserve its result record."""

        _persistence.require_session_appendable(handle)
        reservation_key = (handle.session_id, attempt_id)
        if reservation_key in self._uart_tx_result_reservations:
            raise ValueError("UART TX attempt ID is already active")
        event_bytes = _persistence.serialize_jsonl(
            _evidence.uart_tx_attempt_event_json(
                attempt_id=attempt_id,
                segment_id=segment_id,
                attempted_at=attempted_at,
                data=data,
            )
        )
        result_reservation = len(
            _persistence.serialize_jsonl(
                _evidence.uart_tx_result_event_json(
                    attempt_id=attempt_id,
                    segment_id=segment_id,
                    completed_at="9999-12-31T23:59:59.999999Z",
                    outcome="failed",
                    error="x" * 64,
                    bytes_accepted=1024,
                    timestamp_us=9_223_372_036_854_775_807,
                    device_timestamp_us=9_223_372_036_854_775_807,
                )
            )
        )
        metadata = _persistence.read_json_object(handle.paths.metadata)
        _metadata._metadata_segment(metadata, segment_id)
        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes) + result_reservation,
            rejected_unit_type="uart_tx_attempt",
            rejected_uart_payload_bytes=None,
            segment_id=segment_id,
            channel=None,
            timestamp_us=None,
        )
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        self._uart_tx_result_reservations[reservation_key] = (
            result_reservation,
            len(data),
            segment_id,
        )

    def append_uart_tx_result(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        segment_id: int,
        completed_at: str,
        outcome: Literal["success", "failed"],
        error: str | None,
        bytes_accepted: int | None,
        timestamp_us: int | None,
        device_timestamp_us: int | None,
    ) -> None:
        """Durably resolve one admitted forced-send attempt."""

        _persistence.require_session_appendable(handle)
        reservation_key = (handle.session_id, attempt_id)
        reservation = self._uart_tx_result_reservations.get(reservation_key)
        if reservation is None:
            raise ValueError("UART TX result has no active attempt reservation")
        reserved_bytes, payload_bytes, reserved_segment_id = reservation
        if segment_id != reserved_segment_id:
            raise ValueError("UART TX result segment does not match its attempt")
        if outcome == "success" and bytes_accepted != payload_bytes:
            raise ValueError("successful UART TX result must accept the complete payload")
        event_bytes = _persistence.serialize_jsonl(
            _evidence.uart_tx_result_event_json(
                attempt_id=attempt_id,
                segment_id=segment_id,
                completed_at=completed_at,
                outcome=outcome,
                error=error,
                bytes_accepted=bytes_accepted,
                timestamp_us=timestamp_us,
                device_timestamp_us=device_timestamp_us,
            )
        )
        if len(event_bytes) > reserved_bytes:
            raise ValueError("UART TX result exceeds its admitted reservation")
        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes),
            rejected_unit_type="hardware_event",
            rejected_uart_payload_bytes=None,
            segment_id=segment_id,
            channel=None,
            timestamp_us=timestamp_us,
            released_uart_tx_reservation=reservation_key,
        )
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if timestamp_us is not None:
            _metadata._record_metadata_segment_timestamp(
                metadata,
                segment_id=segment_id,
                timestamp_us=timestamp_us,
            )
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        del self._uart_tx_result_reservations[reservation_key]

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

        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)

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

        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)

    def record_backend_disconnect(
        self,
        handle: SessionHandle,
        *,
        segment_id: int,
    ) -> int:
        """Close the current segment and durably admit one disconnect unit."""

        _persistence.require_session_appendable(handle)
        host_timestamp = _metadata._format_utc_timestamp(self._clock())
        event_bytes = _persistence.serialize_jsonl(
            _evidence.usb_disconnect_event_json(
                host_timestamp=host_timestamp,
                segment_id=segment_id,
            )
        )

        def record_summary(metadata: dict[str, object]) -> None:
            _metadata._record_backend_disconnect(
                metadata,
                segment_id=segment_id,
                ended_at=host_timestamp,
            )

        metadata = _persistence.read_json_object(handle.paths.metadata)
        record_summary(metadata)
        self._preflight_evidence(
            handle,
            evidence_bytes=len(event_bytes),
            rejected_unit_type="hardware_event",
            rejected_uart_payload_bytes=None,
            segment_id=segment_id,
            channel=None,
            timestamp_us=None,
            rejected_metadata_mutator=record_summary,
        )
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, event_bytes)
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        segments = metadata["segments"]
        if not isinstance(segments, list):
            raise AssertionError("validated session segments changed type")
        return len(segments)

    def resume_session(
        self,
        handle: SessionHandle,
        *,
        backend_snapshot: BackendSnapshot,
    ) -> int:
        """Append one validated reconnect segment and its discontinuity evidence."""

        _persistence.require_session_appendable(handle)
        host_timestamp = _metadata._format_utc_timestamp(self._clock())
        metadata = _persistence.read_json_object(handle.paths.metadata)
        segment_id = _metadata._append_resumed_backend_segment(
            metadata,
            snapshot=backend_snapshot,
            started_at=host_timestamp,
        )
        reconnect_bytes = _persistence.serialize_jsonl(
            _evidence.usb_reconnect_event_json(
                host_timestamp=host_timestamp,
                segment_id=segment_id,
            )
        )
        discontinuity_bytes = _persistence.serialize_jsonl(
            _evidence.timestamp_discontinuity_event_json(
                host_timestamp=host_timestamp,
                from_segment_id=segment_id - 1,
                to_segment_id=segment_id,
            )
        )
        self._preflight_evidence(
            handle,
            evidence_bytes=len(reconnect_bytes) + len(discontinuity_bytes),
            rejected_unit_type="hardware_event",
            rejected_uart_payload_bytes=None,
            segment_id=segment_id,
            channel=None,
            timestamp_us=None,
        )
        with _transactions.evidence_transaction(
            handle.paths,
            append_paths=[handle.paths.hardware_events],
        ) as transaction:
            _persistence.append_serialized(handle.paths.hardware_events, reconnect_bytes)
            _persistence.append_serialized(
                handle.paths.hardware_events,
                discontinuity_bytes,
            )
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        return segment_id

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
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)

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
        serialized_metadata = _persistence.serialize_json(metadata)
        _require_metadata_capacity(serialized_metadata)
        _persistence.write_serialized(handle.paths.metadata, serialized_metadata)


def _require_metadata_capacity(serialized_metadata: bytes) -> None:
    if len(serialized_metadata) > _metadata.METADATA_MAX_BYTES:
        raise ValueError("session metadata exceeds its fixed size limit")
