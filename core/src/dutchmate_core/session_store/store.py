"""Filesystem-backed debug session storage."""

import base64
import json
import unicodedata
from collections.abc import Callable, Sequence
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Final, Literal, cast

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
from dutchmate_core.profile import DutProfile
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
    V2EvidenceAdmission,
    V2SessionDetail,
    V2SessionListItem,
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
    "V2EvidenceAdmission",
    "V2SessionDetail",
    "V2SessionListItem",
]

DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES = session_evidence_budget_bytes(
    DEFAULT_SESSION_MAX_SIZE_MB
)
_V2_OPERATION_OUTCOMES: Final = frozenset(
    {
        "elapsed",
        "matched",
        "timeout",
        "disconnected",
        "released",
        "cancelled",
        "error",
    }
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
        self._v2_profiles: dict[str, DutProfile] = {}
        self._v2_snapshots: dict[str, BackendSnapshot] = {}

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
            if schema_version not in {1, 2}:
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

    def create_v2_session(
        self,
        *,
        profile: DutProfile,
        backend_snapshot: BackendSnapshot,
    ) -> SessionHandle:
        """Create and durably publish one active schema-v2 ownership session."""

        with self._store_lock:
            return self._create_v2_session_locked(
                profile=profile,
                backend_snapshot=backend_snapshot,
                predecessor_session_id=None,
            )

    def _create_v2_session_locked(
        self,
        *,
        profile: DutProfile,
        backend_snapshot: BackendSnapshot,
        predecessor_session_id: str | None,
    ) -> SessionHandle:
        if self._evidence_budget_bytes < _metadata.MIN_V2_EVIDENCE_BUDGET_BYTES:
            raise ValueError(
                "schema-v2 evidence budget must be at least "
                f"{_metadata.MIN_V2_EVIDENCE_BUDGET_BYTES} bytes"
            )
        if backend_snapshot.info.mode != profile.backend_mode:
            raise ValueError("v2 backend snapshot mode must match the DUT Profile")
        if backend_snapshot.segment is None:
            raise ValueError("v2 session creation requires timestamp provenance")
        if backend_snapshot.info.port != profile.current_serial_port:
            raise ValueError("v2 backend snapshot port must match the DUT Profile")

        started_at = self._clock()
        session_id = _metadata._validate_session_id(
            f"{_metadata._format_session_id_timestamp(started_at)}-{self._id_factory()}"
        )
        paths = _persistence.session_paths(self._root / session_id)
        _persistence.create_directory(paths.root)
        metadata = _metadata._initial_v2_metadata(
            session_id=session_id,
            started_at=_metadata._format_utc_timestamp(started_at),
            profile=profile,
            backend_snapshot=backend_snapshot,
            evidence_budget_bytes=self._evidence_budget_bytes,
            predecessor_session_id=predecessor_session_id,
        )
        try:
            _persistence.write_serialized(
                paths.terminal_reserve,
                b"\0" * _metadata.METADATA_MAX_BYTES,
            )
            _persistence.write_serialized(paths.uart_raw, b"")
            _persistence.write_serialized(paths.uart_events, b"")
            _persistence.write_serialized(paths.operation_events, b"")
            _persistence.write_serialized(paths.hardware_events, b"")
            _persistence.write_serialized(paths.connection_events, b"")
            _persistence.write_serialized(
                paths.detected_patterns,
                _persistence.serialize_compact_json([]),
            )
            serialized_metadata = _persistence.serialize_compact_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            _persistence.write_serialized(paths.metadata, serialized_metadata)
        except BaseException as exc:
            try:
                _persistence.remove_session_directory(paths.root)
            except SessionPersistenceError as cleanup_error:
                raise cleanup_error from exc
            raise
        handle = SessionHandle(session_id=session_id, paths=paths)
        self._v2_profiles[session_id] = profile
        self._v2_snapshots[session_id] = backend_snapshot
        return handle

    def append_v2_uart_receive(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        detected_patterns: Sequence[dict[str, object]] = (),
        capture_result: UartCaptureResult | None = None,
        rollover_capture_result: UartCaptureResult | None = None,
    ) -> V2EvidenceAdmission:
        """Atomically admit exact UART RX bytes and their schema-v2 record."""

        if not event.data or len(event.data) > 32768:
            raise ValueError("v2 UART RX payload must contain 1..32768 bytes")
        if capture_result is not None:
            _require_matching_capture_result(event, capture_result)
            if detected_patterns:
                raise ValueError(
                    "v2 UART admission accepts detected_patterns or capture_result, not both"
                )
        if rollover_capture_result is not None and capture_result is None:
            raise ValueError("rollover capture result requires a primary capture result")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            admitted_event = event
            admitted_result = capture_result
            admitted_patterns = (
                tuple(
                    _evidence.detected_pattern_records(
                        admitted_result,
                        segment_id=event.segment_id,
                    )
                )
                if admitted_result is not None
                else detected_patterns
            )
            unit = self._v2_uart_unit(
                handle,
                metadata=metadata,
                event=admitted_event,
                detected_patterns=admitted_patterns,
                capture_result=admitted_result,
            )
            rolled_over = False
            if not self._v2_unit_fits(metadata, unit_bytes=unit[1]):
                handle = self._rollover_v2_locked(handle, end_reason="rollover_size")
                metadata = self._require_active_v2_metadata(handle)
                successor_segment_id = _current_v2_segment_id(metadata)
                admitted_event = replace(event, segment_id=successor_segment_id)
                admitted_result = (
                    rollover_capture_result
                    if rollover_capture_result is not None
                    else replace(capture_result, segment_id=successor_segment_id)
                    if capture_result is not None
                    else None
                )
                if admitted_result is not None:
                    _require_matching_capture_result(admitted_event, admitted_result)
                    admitted_patterns = tuple(
                        _evidence.detected_pattern_records(
                            admitted_result,
                            segment_id=successor_segment_id,
                        )
                    )
                else:
                    admitted_patterns = tuple(
                        {**pattern, "segment_id": successor_segment_id}
                        for pattern in detected_patterns
                    )
                unit = self._v2_uart_unit(
                    handle,
                    metadata=metadata,
                    event=admitted_event,
                    detected_patterns=admitted_patterns,
                    capture_result=admitted_result,
                )
                rolled_over = True
                if not self._v2_unit_fits(metadata, unit_bytes=unit[1]):
                    raise SessionPersistenceError(
                        operation="preflight v2 evidence",
                        path=handle.paths.root,
                        detail="one schema-valid UART unit exceeds the session budget",
                    )

            record, _unit_bytes, serialized_patterns, hardware_event_bytes = unit
            evidence_seq = record["evidence_seq"]
            if not isinstance(evidence_seq, int):
                raise ValueError("v2 evidence sequence is invalid")
            serialized_record = _persistence.serialize_jsonl(record)
            append_paths = [handle.paths.uart_raw, handle.paths.uart_events]
            if hardware_event_bytes:
                append_paths.append(handle.paths.hardware_events)
            try:
                with _transactions.evidence_transaction(
                    handle.paths,
                    append_paths=append_paths,
                    replace_detected_patterns=serialized_patterns is not None,
                ) as transaction:
                    _persistence.append_serialized(handle.paths.uart_raw, admitted_event.data)
                    _persistence.append_serialized(handle.paths.uart_events, serialized_record)
                    for hardware_event in hardware_event_bytes:
                        _persistence.append_serialized(
                            handle.paths.hardware_events,
                            hardware_event,
                        )
                    if serialized_patterns is not None:
                        _persistence.write_serialized(
                            handle.paths.detected_patterns,
                            serialized_patterns,
                        )
                    metadata["next_evidence_seq"] = evidence_seq + 1 + len(
                        hardware_event_bytes
                    )
                    if admitted_result is not None:
                        if admitted_result.newly_oversized_line_count:
                            _metadata._record_line_processing(
                                metadata,
                                newly_oversized_line_count=(
                                    admitted_result.newly_oversized_line_count
                                ),
                            )
                        _metadata._record_metadata_segment_timestamp(
                            metadata,
                            segment_id=admitted_event.segment_id,
                            timestamp_us=admitted_event.timestamp_us,
                        )
                    _persistence.refresh_storage_accounting(metadata, handle.paths)
                    serialized_metadata = _persistence.serialize_compact_json(metadata)
                    _require_metadata_capacity(serialized_metadata)
                    transaction.prepare_metadata(serialized_metadata)
                    _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
            except SessionPersistenceError as exc:
                self._fail_active_v2_persistence_locked(handle, cause=exc)
                raise
            return V2EvidenceAdmission(
                handle=handle,
                evidence_seq=evidence_seq,
                rolled_over=rolled_over,
                next_evidence_seq=evidence_seq + 1 + len(hardware_event_bytes),
            )

    def v2_uart_receive_will_rollover(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        capture_result: UartCaptureResult,
    ) -> bool:
        """Return whether this exact UART unit requires a successor session."""

        _require_matching_capture_result(event, capture_result)
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            patterns = tuple(
                _evidence.detected_pattern_records(
                    capture_result,
                    segment_id=event.segment_id,
                )
            )
            unit = self._v2_uart_unit(
                handle,
                metadata=metadata,
                event=event,
                detected_patterns=patterns,
                capture_result=capture_result,
            )
            return not self._v2_unit_fits(metadata, unit_bytes=unit[1])

    def append_v2_line_boundary(
        self,
        handle: SessionHandle,
        *,
        results: Sequence[UartCaptureResult],
    ) -> tuple[V2EvidenceAdmission, ...]:
        """Persist derived oversized-line facts finalized at a hard boundary."""

        admissions: list[V2EvidenceAdmission] = []
        with self._store_lock:
            current = handle
            for result in results:
                for oversized_line in result.oversized_lines:
                    fields = {
                        key: value
                        for key, value in _evidence.line_limit_exceeded_event_json(
                            result,
                            oversized_line,
                        ).items()
                        if key not in {"type", "segment_id"}
                    }

                    def boundary_fields(
                        _current_handle: SessionHandle,
                        updated: dict[str, object],
                        _evidence_seq: int,
                        *,
                        finalized_fields: dict[str, object] = fields,
                    ) -> dict[str, object]:
                        return {
                            "segment_id": _current_v2_segment_id(updated),
                            **finalized_fields,
                        }

                    admission = self._append_v2_record_locked(
                        current,
                        stream="hardware",
                        record_type="line_limit_exceeded",
                        fields=boundary_fields,
                    )
                    admissions.append(admission)
                    current = admission.handle
        return tuple(admissions)

    def _v2_uart_unit(
        self,
        handle: SessionHandle,
        *,
        metadata: dict[str, object],
        event: UartReceiveEvent,
        detected_patterns: Sequence[dict[str, object]],
        capture_result: UartCaptureResult | None,
    ) -> tuple[dict[str, object], int, bytes | None, tuple[bytes, ...]]:
        segments = metadata.get("segments")
        if not isinstance(segments, list) or not segments or not isinstance(segments[-1], dict):
            raise ValueError("v2 session must contain a current segment")
        if event.segment_id != segments[-1].get("segment_id"):
            raise ValueError("v2 UART event must reference the current segment")
        evidence_seq = metadata.get("next_evidence_seq")
        if isinstance(evidence_seq, bool) or not isinstance(evidence_seq, int):
            raise ValueError("v2 next_evidence_seq must be a non-negative integer")
        try:
            raw_start = handle.paths.uart_raw.stat().st_size
        except OSError as exc:
            raise SessionPersistenceError(
                operation="read UART offset",
                path=handle.paths.uart_raw,
                detail=str(exc),
            ) from exc
        record: dict[str, object] = {
            "evidence_seq": evidence_seq,
            "type": "uart_rx",
            "segment_id": event.segment_id,
            "timestamp_us": event.timestamp_us,
            "recorded_at": _metadata._format_utc_timestamp(self._clock()),
            "channel": event.channel,
            "data_b64": base64.b64encode(event.data).decode("ascii"),
            "raw_offset_start": raw_start,
            "raw_offset_end": raw_start + len(event.data),
        }
        record_bytes = _persistence.serialize_jsonl(record)
        if len(record_bytes) > _metadata.MAX_V2_JSONL_RECORD_BYTES:
            raise ValueError("schema-v2 primary JSONL record exceeds its size limit")
        serialized_patterns, pattern_growth = _v2_pattern_document(
            handle,
            source_evidence_seq=evidence_seq,
            event=event,
            detected_patterns=detected_patterns,
        )
        hardware_event_bytes: tuple[bytes, ...] = ()
        if capture_result is not None:
            hardware_event_bytes = tuple(
                _persistence.serialize_jsonl(
                    self._v2_record(
                        handle,
                        metadata=metadata,
                        evidence_seq=evidence_seq + index + 1,
                        record_type="line_limit_exceeded",
                        fields={
                            key: value
                            for key, value in _evidence.line_limit_exceeded_event_json(
                                capture_result,
                                oversized_line,
                            ).items()
                            if key != "type"
                        },
                    )
                )
                for index, oversized_line in enumerate(capture_result.oversized_lines)
            )
        return (
            record,
            len(event.data)
            + len(record_bytes)
            + pattern_growth
            + sum(len(item) for item in hardware_event_bytes),
            serialized_patterns,
            hardware_event_bytes,
        )

    def _fail_active_v2_persistence_locked(
        self,
        handle: SessionHandle,
        *,
        cause: SessionPersistenceError,
    ) -> None:
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 2 or metadata.get("state") != "active":
            return

        def record_persistence_fault(updated: dict[str, object]) -> None:
            quality = updated.get("evidence_quality")
            if not isinstance(quality, dict):
                raise ValueError("v2 evidence_quality must be an object")
            quality["local_recording"] = "persistence_fault"

        self._terminalize_session_locked(
            handle,
            state="failed",
            end_reason="persistence_error",
            error=_metadata._bounded_error("persistence_fault", str(cause)),
            truncation=None,
            metadata_mutator=record_persistence_fault,
        )

    @staticmethod
    def _v2_unit_fits(metadata: dict[str, object], *, unit_bytes: int) -> bool:
        storage = metadata.get("storage")
        if not isinstance(storage, dict):
            raise ValueError("v2 storage metadata must be an object")
        written = storage.get("evidence_bytes_written")
        budget = storage.get("evidence_budget_bytes")
        if (
            isinstance(written, bool)
            or not isinstance(written, int)
            or isinstance(budget, bool)
            or not isinstance(budget, int)
        ):
            raise ValueError("v2 evidence accounting is invalid")
        return written + unit_bytes <= budget

    def _require_active_v2_metadata(self, handle: SessionHandle) -> dict[str, object]:
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 2 or metadata.get("state") != "active":
            raise ValueError("schema-v2 evidence can only append while active")
        if metadata.get("session_id") != handle.session_id:
            raise ValueError("schema-v2 handle does not match session metadata")
        return metadata

    def _rollover_v2_locked(
        self,
        handle: SessionHandle,
        *,
        end_reason: Literal["rollover_size", "rollover_segments"],
        successor_snapshot: BackendSnapshot | None = None,
    ) -> SessionHandle:
        predecessor_metadata = self._require_active_v2_metadata(handle)
        pending_attempts = {
            key: dict(value)
            for key, value in _v2_pending_attempts(predecessor_metadata).items()
        }
        raw_active_operations = predecessor_metadata.get("active_operations")
        if not isinstance(raw_active_operations, dict):
            raise ValueError("v2 active_operations must be an object")
        active_operations: dict[str, dict[str, object]] = {}
        for operation_id, raw_operation in raw_active_operations.items():
            if not isinstance(operation_id, str) or not isinstance(raw_operation, dict):
                raise ValueError("v2 active operation metadata is malformed")
            raw_ranges = raw_operation.get("ranges")
            if not isinstance(raw_ranges, list) or not raw_ranges:
                raise ValueError("v2 active operation ranges are malformed")
            ranges = [dict(item) for item in raw_ranges if isinstance(item, dict)]
            if len(ranges) != len(raw_ranges):
                raise ValueError("v2 active operation range is malformed")
            ranges[-1]["end_evidence_seq_exclusive"] = _v2_next_sequence(
                predecessor_metadata
            )
            active_operations[operation_id] = {
                "operation_type": raw_operation.get("operation_type"),
                "ranges": ranges,
            }
        try:
            profile = self._v2_profiles[handle.session_id]
            snapshot = successor_snapshot or self._v2_snapshots[handle.session_id]
        except KeyError as exc:
            raise SessionPersistenceError(
                operation="create v2 successor",
                path=handle.paths.root,
                detail="effective profile or backend snapshot is unavailable",
            ) from exc
        try:
            successor = self._create_v2_session_locked(
                profile=profile,
                backend_snapshot=snapshot,
                predecessor_session_id=handle.session_id,
            )
        except SessionPersistenceError as exc:

            def record_persistence_fault(metadata: dict[str, object]) -> None:
                quality = metadata.get("evidence_quality")
                if not isinstance(quality, dict):
                    raise ValueError("v2 evidence_quality must be an object")
                quality["local_recording"] = "persistence_fault"

            self._terminalize_session_locked(
                handle,
                state="failed",
                end_reason="persistence_error",
                error=_metadata._bounded_error("persistence_fault", str(exc)),
                truncation=None,
                metadata_mutator=record_persistence_fault,
            )
            raise

        try:
            def transfer_rollover_ownership(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                updated["pending_attempts"] = {
                    key: dict(value) for key, value in pending_attempts.items()
                }

            rollover_admission = self._append_v2_record_locked(
                successor,
                stream="connection",
                record_type="rollover_succeeded",
                fields=lambda _handle, updated, _evidence_seq: {
                    "segment_id": _current_v2_segment_id(updated),
                    "detail": {
                        "predecessor_session_id": handle.session_id,
                        "reason": end_reason,
                    },
                },
                metadata_mutator=transfer_rollover_ownership,
            )
            successor = rollover_admission.handle
            for operation_id, operation in active_operations.items():
                operation_type = operation.get("operation_type")
                previous_ranges = cast(list[dict[str, object]], operation["ranges"])

                def continue_operation(
                    updated: dict[str, object],
                    admission: V2EvidenceAdmission,
                    *,
                    operation_id: str = operation_id,
                    operation_type: object = operation_type,
                    previous_ranges: list[dict[str, object]] = previous_ranges,
                ) -> None:
                    operations = updated.get("active_operations")
                    summary = updated.get("operation_summary")
                    if not isinstance(operations, dict) or not isinstance(summary, dict):
                        raise ValueError("v2 operation metadata is malformed")
                    operations[operation_id] = {
                        "operation_type": operation_type,
                        "ranges": [
                            *[dict(item) for item in previous_ranges],
                            {
                                "session_id": admission.handle.session_id,
                                "start_evidence_seq": admission.evidence_seq,
                                "end_evidence_seq_exclusive": None,
                            },
                        ],
                    }
                    summary["active"] = _v2_count(summary, "active") + 1

                admission = self._append_v2_record_locked(
                    successor,
                    stream="operation",
                    record_type="operation_continued",
                    fields={
                        "operation_id": operation_id,
                        "operation_type": operation_type,
                        "previous_session_id": handle.session_id,
                    },
                    metadata_mutator=continue_operation,
                )
                successor = admission.handle
        except SessionPersistenceError as exc:
            self._fail_active_v2_persistence_locked(handle, cause=exc)
            raise

        def link_successor(metadata: dict[str, object]) -> None:
            metadata["successor_session_id"] = successor.session_id
            operations = metadata.get("active_operations")
            summary = metadata.get("operation_summary")
            predecessor_pending = metadata.get("pending_attempts")
            if not isinstance(operations, dict) or not isinstance(summary, dict):
                raise ValueError("v2 operation metadata is malformed")
            if not isinstance(predecessor_pending, dict):
                raise ValueError("v2 pending_attempts must be an object")
            for operation in operations.values():
                if not isinstance(operation, dict):
                    raise ValueError("v2 active operation metadata is malformed")
                ranges = operation.get("ranges")
                if not isinstance(ranges, list) or not ranges or not isinstance(ranges[-1], dict):
                    raise ValueError("v2 active operation ranges are malformed")
                ranges[-1]["end_evidence_seq_exclusive"] = _v2_next_sequence(metadata)
            if _v2_count(summary, "active") != len(operations):
                raise ValueError("v2 active operation summary disagrees with ownership")
            summary["active"] = 0
            operations.clear()
            predecessor_pending.clear()

        self._terminalize_session_locked(
            handle,
            state="completed",
            end_reason=end_reason,
            error=None,
            truncation=None,
            metadata_mutator=link_successor,
        )
        if not self._recovering:
            self._apply_retention_locked(
                held_session_ids=frozenset({successor.session_id})
            )
        return successor

    def append_v2_segment(
        self,
        handle: SessionHandle,
        *,
        backend_snapshot: BackendSnapshot,
    ) -> SessionHandle:
        """Publish the next contiguous segment or roll before segment 33."""

        segment_context = backend_snapshot.segment
        if segment_context is None:
            raise ValueError("v2 segment requires timestamp provenance")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            segments = metadata.get("segments")
            if not isinstance(segments, list) or not segments:
                raise ValueError("v2 session must contain a current segment")
            expected_id = len(segments)
            if segment_context.segment_id != expected_id:
                raise ValueError("v2 segment ID must be the next contiguous ID")
            if len(segments) == _metadata.MAX_SESSION_SEGMENTS:
                normalized_snapshot = replace(
                    backend_snapshot,
                    segment=replace(segment_context, segment_id=0),
                )
                return self._rollover_v2_locked(
                    handle,
                    end_reason="rollover_segments",
                    successor_snapshot=normalized_snapshot,
                )

            started_at = _metadata._format_utc_timestamp(self._clock())

            def publish_segment(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                updated_segments = updated.get("segments")
                if (
                    not isinstance(updated_segments, list)
                    or not updated_segments
                    or not isinstance(updated_segments[-1], dict)
                ):
                    raise ValueError("v2 session segments are malformed")
                current = updated_segments[-1]
                if current.get("ended_at") is None:
                    current["ended_at"] = started_at
                    current["end_reason"] = "reconnect"
                segment_id = len(updated_segments)
                published_snapshot = replace(
                    backend_snapshot,
                    segment=replace(segment_context, segment_id=segment_id),
                )
                updated_segments.append(
                    _metadata._backend_segment_json(
                        published_snapshot,
                        started_at=started_at,
                    )
                )

            def segment_fields(
                _current_handle: SessionHandle,
                updated: dict[str, object],
                _evidence_seq: int,
            ) -> dict[str, object]:
                updated_segments = updated.get("segments")
                if not isinstance(updated_segments, list) or not updated_segments:
                    raise ValueError("v2 session segments are malformed")
                return {"segment_id": len(updated_segments)}

            admission = self._append_v2_record_locked(
                handle,
                stream="connection",
                record_type="segment_opened",
                fields=segment_fields,
                metadata_mutator=publish_segment,
            )
            published_segment_id = _current_v2_segment_id(
                self._require_active_v2_metadata(admission.handle)
            )
            self._v2_snapshots[admission.handle.session_id] = replace(
                backend_snapshot,
                segment=replace(segment_context, segment_id=published_segment_id),
            )
            return admission.handle

    def start_v2_operation(
        self,
        handle: SessionHandle,
        *,
        operation_id: str,
        operation_type: Literal["monitor", "interact", "boot_test"],
        parameters: dict[str, object],
    ) -> V2EvidenceAdmission:
        """Persist an operation start before operation-owned activity begins.

        The Device Core caller owns globally unique ID generation. This bounded
        persistence layer rejects collisions visible in the current session's
        evidence without retaining an ever-growing historical ID registry.
        """

        _validate_v2_identifier(operation_id, field="operation_id")
        if operation_type not in {"monitor", "interact", "boot_test"}:
            raise ValueError("unsupported v2 operation type")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            active = metadata.get("active_operations")
            if not isinstance(active, dict):
                raise ValueError("v2 active_operations must be an object")
            if operation_id in active or _v2_operation_id_seen(
                handle.paths.operation_events, operation_id
            ):
                raise ValueError("v2 operation ID has already been used")

            def start_fields(
                current_handle: SessionHandle,
                _updated: dict[str, object],
                evidence_seq: int,
            ) -> dict[str, object]:
                return {
                    "operation_id": operation_id,
                    "operation_type": operation_type,
                    "parameters": parameters,
                    "start_cursor": {
                        "session_id": current_handle.session_id,
                        "next_evidence_seq": evidence_seq,
                    },
                }

            def started(updated: dict[str, object], admission: V2EvidenceAdmission) -> None:
                operations = updated.get("active_operations")
                summary = updated.get("operation_summary")
                if not isinstance(operations, dict) or not isinstance(summary, dict):
                    raise ValueError("v2 operation metadata is malformed")
                if operation_id in operations:
                    raise ValueError("v2 operation ID has already been used")
                operations[operation_id] = {
                    "operation_type": operation_type,
                    "ranges": [
                        {
                            "session_id": admission.handle.session_id,
                            "start_evidence_seq": admission.evidence_seq,
                            "end_evidence_seq_exclusive": None,
                        }
                    ],
                }
                summary["started"] = _v2_count(summary, "started") + 1
                summary["active"] = _v2_count(summary, "active") + 1

            return self._append_v2_record_locked(
                handle,
                stream="operation",
                record_type="operation_started",
                fields=start_fields,
                metadata_mutator=started,
            )

    def complete_v2_operation(
        self,
        handle: SessionHandle,
        *,
        operation_id: str,
        outcome: str,
        error: dict[str, object] | None = None,
    ) -> V2EvidenceAdmission:
        """Persist one operation terminal record with durable evidence ranges."""

        _validate_v2_identifier(operation_id, field="operation_id")
        if outcome not in _V2_OPERATION_OUTCOMES:
            raise ValueError("outcome must use the normalized Phase 1 vocabulary")
        if outcome == "error":
            if error is None:
                raise ValueError("error outcome requires bounded error data")
            operation_error = _bounded_v2_operation_error(error)
        else:
            if error is not None:
                raise ValueError("operation error data is only valid for the error outcome")
            operation_error = None
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            active = metadata.get("active_operations")
            if not isinstance(active, dict) or not isinstance(active.get(operation_id), dict):
                raise ValueError("v2 operation is not active")
            def terminal_fields(
                current_handle: SessionHandle,
                updated: dict[str, object],
                terminal_seq: int,
            ) -> dict[str, object]:
                operations = updated.get("active_operations")
                if not isinstance(operations, dict):
                    raise ValueError("v2 active_operations must be an object")
                operation = operations.get(operation_id)
                if not isinstance(operation, dict):
                    raise ValueError("v2 operation is not active")
                ranges = operation.get("ranges")
                if (
                    not isinstance(ranges, list)
                    or not ranges
                    or not isinstance(ranges[-1], dict)
                ):
                    raise ValueError("v2 operation ranges are malformed")
                final_ranges = [dict(item) for item in ranges if isinstance(item, dict)]
                if len(final_ranges) != len(ranges):
                    raise ValueError("v2 operation range is malformed")
                final_ranges[-1]["end_evidence_seq_exclusive"] = terminal_seq + 1
                return {
                    "operation_id": operation_id,
                    "operation_type": operation.get("operation_type"),
                    "outcome": outcome,
                    "error": operation_error,
                    "end_cursor": {
                        "session_id": current_handle.session_id,
                        "next_evidence_seq": terminal_seq + 1,
                    },
                    "evidence_ranges": final_ranges,
                }

            def terminal(updated: dict[str, object], _admission: V2EvidenceAdmission) -> None:
                operations = updated.get("active_operations")
                summary = updated.get("operation_summary")
                if not isinstance(operations, dict) or not isinstance(summary, dict):
                    raise ValueError("v2 operation metadata is malformed")
                del operations[operation_id]
                summary["active"] = _v2_count(summary, "active") - 1
                key = "failed" if outcome == "error" else "completed"
                summary[key] = _v2_count(summary, key) + 1

            return self._append_v2_record_locked(
                handle,
                stream="operation",
                record_type="operation_terminal",
                fields=terminal_fields,
                metadata_mutator=terminal,
            )

    def append_v2_uart_tx_attempt(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        data: bytes,
        operation_id: str | None,
        transformation: dict[str, object],
    ) -> V2EvidenceAdmission:
        """Persist exact UART TX intent before transport dispatch."""

        _validate_v2_identifier(attempt_id, field="attempt_id")
        if operation_id is not None:
            _validate_v2_identifier(operation_id, field="operation_id")
        if not data or len(data) > 1024:
            raise ValueError("v2 UART TX payload must contain 1..1024 bytes")
        with self._store_lock:
            seen, _pending = _v2_attempt_ids(
                handle.paths.operation_events,
                attempt_type="uart_tx_attempt",
                result_type="uart_tx_result",
            )
            if attempt_id in seen:
                raise ValueError("v2 UART TX attempt ID must be unique")
            metadata = self._require_active_v2_metadata(handle)
            _require_v2_operation_active(metadata, operation_id)
            if _v2_pending_attempt(metadata, "uart_tx_attempt", attempt_id) is not None:
                raise ValueError("v2 UART TX attempt ID must be unique")

            def record_pending_attempt(
                updated: dict[str, object],
                admission: V2EvidenceAdmission,
            ) -> None:
                pending = _v2_pending_attempts(updated)
                key = _v2_attempt_key("uart_tx_attempt", attempt_id)
                if key in pending:
                    raise ValueError("v2 UART TX attempt ID must be unique")
                pending[key] = {
                    "attempt_type": "uart_tx_attempt",
                    "attempt_id": attempt_id,
                    "session_id": admission.handle.session_id,
                    "evidence_seq": admission.evidence_seq,
                }

            return self._append_v2_record_locked(
                handle,
                stream="operation",
                record_type="uart_tx_attempt",
                fields=lambda _handle, updated, _evidence_seq: {
                    "attempt_id": attempt_id,
                    "operation_id": operation_id,
                    "data_b64": base64.b64encode(data).decode("ascii"),
                    "byte_length": len(data),
                    "transformation": transformation,
                    "segment_id": _current_v2_segment_id(updated),
                },
                metadata_mutator=record_pending_attempt,
            )

    def append_v2_uart_tx_result(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        status: str,
        accepted_bytes: int | None,
    ) -> V2EvidenceAdmission:
        """Persist the known terminal transport result for one TX attempt."""

        _validate_v2_identifier(attempt_id, field="attempt_id")
        _validate_v2_identifier(status, field="status")
        if accepted_bytes is not None and (
            isinstance(accepted_bytes, bool)
            or not isinstance(accepted_bytes, int)
            or accepted_bytes < 0
        ):
            raise ValueError("accepted_bytes must be a non-negative integer or null")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if _v2_pending_attempt(metadata, "uart_tx_attempt", attempt_id) is None:
                raise ValueError("v2 result requires a preceding unresolved UART TX attempt")

            def result_fields(
                _current_handle: SessionHandle,
                updated: dict[str, object],
                _evidence_seq: int,
            ) -> dict[str, object]:
                attempt = _v2_pending_attempt(updated, "uart_tx_attempt", attempt_id)
                if attempt is None:
                    raise ValueError(
                        "v2 result requires a preceding unresolved UART TX attempt"
                    )
                return {
                    "attempt_id": attempt_id,
                    "attempt_session_id": attempt["session_id"],
                    "attempt_evidence_seq": attempt["evidence_seq"],
                    "status": status,
                    "accepted_bytes": accepted_bytes,
                }

            def resolve_attempt(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                del _v2_pending_attempts(updated)[
                    _v2_attempt_key("uart_tx_attempt", attempt_id)
                ]

            admission = self._append_v2_record_locked(
                handle,
                stream="operation",
                record_type="uart_tx_result",
                fields=result_fields,
                metadata_mutator=resolve_attempt,
            )
            if not self._recovering:
                self._apply_retention_locked(
                    held_session_ids=frozenset({admission.handle.session_id})
                )
            return admission

    def append_v2_control_attempt(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        role: str,
        provider: str,
        parameters: dict[str, object],
        operation_id: str | None,
    ) -> V2EvidenceAdmission:
        """Persist resolved semantic-control intent before dispatch."""

        for value, field in ((attempt_id, "attempt_id"), (role, "role"), (provider, "provider")):
            _validate_v2_identifier(value, field=field)
        if operation_id is not None:
            _validate_v2_identifier(operation_id, field="operation_id")
        with self._store_lock:
            seen, _pending = _v2_attempt_ids(
                handle.paths.hardware_events,
                attempt_type="control_attempt",
                result_type="control_result",
            )
            if attempt_id in seen:
                raise ValueError("v2 control attempt ID must be unique")
            metadata = self._require_active_v2_metadata(handle)
            _require_v2_operation_active(metadata, operation_id)
            if _v2_pending_attempt(metadata, "control_attempt", attempt_id) is not None:
                raise ValueError("v2 control attempt ID must be unique")

            def record_pending_attempt(
                updated: dict[str, object],
                admission: V2EvidenceAdmission,
            ) -> None:
                pending = _v2_pending_attempts(updated)
                key = _v2_attempt_key("control_attempt", attempt_id)
                if key in pending:
                    raise ValueError("v2 control attempt ID must be unique")
                pending[key] = {
                    "attempt_type": "control_attempt",
                    "attempt_id": attempt_id,
                    "session_id": admission.handle.session_id,
                    "evidence_seq": admission.evidence_seq,
                }

            return self._append_v2_record_locked(
                handle,
                stream="hardware",
                record_type="control_attempt",
                fields=lambda _handle, updated, _evidence_seq: {
                    "attempt_id": attempt_id,
                    "operation_id": operation_id,
                    "role": role,
                    "provider": provider,
                    "parameters": parameters,
                    "segment_id": _current_v2_segment_id(updated),
                },
                metadata_mutator=record_pending_attempt,
            )

    def append_v2_control_result(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        status: str,
        device_timestamp_us: int | None = None,
    ) -> V2EvidenceAdmission:
        """Persist a known control result without claiming electrical readback."""

        _validate_v2_identifier(attempt_id, field="attempt_id")
        _validate_v2_identifier(status, field="status")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if _v2_pending_attempt(metadata, "control_attempt", attempt_id) is None:
                raise ValueError("v2 result requires a preceding unresolved control attempt")

            def result_fields(
                _current_handle: SessionHandle,
                updated: dict[str, object],
                _evidence_seq: int,
            ) -> dict[str, object]:
                attempt = _v2_pending_attempt(updated, "control_attempt", attempt_id)
                if attempt is None:
                    raise ValueError(
                        "v2 result requires a preceding unresolved control attempt"
                    )
                return {
                    "attempt_id": attempt_id,
                    "attempt_session_id": attempt["session_id"],
                    "attempt_evidence_seq": attempt["evidence_seq"],
                    "status": status,
                    "device_timestamp_us": device_timestamp_us,
                }

            def resolve_attempt(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                del _v2_pending_attempts(updated)[
                    _v2_attempt_key("control_attempt", attempt_id)
                ]

            admission = self._append_v2_record_locked(
                handle,
                stream="hardware",
                record_type="control_result",
                fields=result_fields,
                metadata_mutator=resolve_attempt,
            )
            if not self._recovering:
                self._apply_retention_locked(
                    held_session_ids=frozenset({admission.handle.session_id})
                )
            return admission

    def append_v2_connection_event(
        self,
        handle: SessionHandle,
        *,
        event_type: str,
        segment_id: int | None,
        detail: dict[str, object],
    ) -> V2EvidenceAdmission:
        """Persist one bounded connection lifecycle fact."""

        _validate_v2_identifier(event_type, field="event_type")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if segment_id is not None and segment_id != _current_v2_segment_id(metadata):
                raise ValueError("v2 connection event must reference the current segment")

            disconnected_at = _metadata._format_utc_timestamp(self._clock())

            def update_continuity(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                if event_type != "unexpected_disconnect":
                    return
                continuity = updated.get("continuity")
                if not isinstance(continuity, dict):
                    raise ValueError("v2 continuity must be an object")
                count = continuity.get("observation_gap_count")
                if isinstance(count, bool) or not isinstance(count, int) or count < 0:
                    raise ValueError("v2 observation gap count is invalid")
                continuity["observation_gap_count"] = count + 1
                segments = updated.get("segments")
                if (
                    not isinstance(segments, list)
                    or not segments
                    or not isinstance(segments[-1], dict)
                ):
                    raise ValueError("v2 session segments are malformed")
                current_segment = segments[-1]
                if current_segment.get("ended_at") is None:
                    current_segment["ended_at"] = disconnected_at
                    current_segment["end_reason"] = "unexpected_disconnect"

            return self._append_v2_record_locked(
                handle,
                stream="connection",
                record_type=event_type,
                fields=lambda _handle, updated, _evidence_seq: {
                    "segment_id": (
                        _current_v2_segment_id(updated) if segment_id is not None else None
                    ),
                    "detail": detail,
                },
                metadata_mutator=update_continuity,
            )

    def v2_telemetry_will_rollover(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent | BufferStatusEvent,
    ) -> bool:
        """Return whether this exact telemetry record requires a successor."""

        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if event.segment_id != _current_v2_segment_id(metadata):
                raise ValueError("v2 telemetry must reference the current segment")
            if isinstance(event, BufferOverflowEvent):
                record_type = "buffer_overflow"
                fields: dict[str, object] = {
                    "segment_id": event.segment_id,
                    "timestamp_us": event.timestamp_us,
                    "channel": event.channel,
                    "dropped_bytes": event.dropped_bytes,
                }
            else:
                record_type = "buffer_status"
                fields = {
                    "segment_id": event.segment_id,
                    "timestamp_us": event.timestamp_us,
                    "uart_rx_size_bytes": event.size_bytes,
                    "uart_rx_used_bytes": event.used_bytes,
                    "uart_rx_high_water_bytes": event.high_water_bytes,
                    "dropped_bytes_total": event.dropped_bytes_total,
                    "overflow_events": event.overflow_events,
                }
            record = self._v2_record(
                handle,
                metadata=metadata,
                evidence_seq=_v2_next_sequence(metadata),
                record_type=record_type,
                fields=fields,
            )
            serialized_record = _persistence.serialize_jsonl(record)
            return not self._v2_unit_fits(
                metadata,
                unit_bytes=len(serialized_record),
            )

    def append_v2_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        session_dropped_bytes: int | None = None,
        rollover_session_dropped_bytes: int | None = None,
    ) -> V2EvidenceAdmission:
        """Persist one Enhanced overflow telemetry event."""

        if session_dropped_bytes is not None and (
            isinstance(session_dropped_bytes, bool)
            or not isinstance(session_dropped_bytes, int)
            or session_dropped_bytes < 0
        ):
            raise ValueError("session_dropped_bytes must be a non-negative integer")
        if rollover_session_dropped_bytes is not None and (
            isinstance(rollover_session_dropped_bytes, bool)
            or not isinstance(rollover_session_dropped_bytes, int)
            or rollover_session_dropped_bytes < 0
        ):
            raise ValueError(
                "rollover_session_dropped_bytes must be a non-negative integer"
            )
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if event.segment_id != _current_v2_segment_id(metadata):
                raise ValueError("v2 telemetry must reference the current segment")

            def record_integrity(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                dropped_bytes = (
                    rollover_session_dropped_bytes
                    if _admission.rolled_over
                    and rollover_session_dropped_bytes is not None
                    else session_dropped_bytes
                    if session_dropped_bytes is not None
                    else event.dropped_bytes
                )
                _record_v2_integrity_loss(
                    updated,
                    dropped_bytes=dropped_bytes,
                    cumulative=(
                        session_dropped_bytes is not None
                        or rollover_session_dropped_bytes is not None
                    ),
                    reported_loss=True,
                )
                _metadata._record_metadata_segment_timestamp(
                    updated,
                    segment_id=_current_v2_segment_id(updated),
                    timestamp_us=event.timestamp_us,
                )

            return self._append_v2_record_locked(
                handle,
                stream="hardware",
                record_type="buffer_overflow",
                fields=lambda _handle, updated, _evidence_seq: {
                    "segment_id": _current_v2_segment_id(updated),
                    "timestamp_us": event.timestamp_us,
                    "channel": event.channel,
                    "dropped_bytes": event.dropped_bytes,
                },
                metadata_mutator=record_integrity,
            )

    def append_v2_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        session_dropped_bytes: int | None = None,
        reported_loss: bool | None = None,
        rollover_session_dropped_bytes: int | None = None,
        rollover_reported_loss: bool | None = None,
    ) -> V2EvidenceAdmission:
        """Persist one Enhanced buffer-status telemetry event."""

        if session_dropped_bytes is not None and (
            isinstance(session_dropped_bytes, bool)
            or not isinstance(session_dropped_bytes, int)
            or session_dropped_bytes < 0
        ):
            raise ValueError("session_dropped_bytes must be a non-negative integer")
        if reported_loss is not None and not isinstance(reported_loss, bool):
            raise ValueError("reported_loss must be a boolean")
        if rollover_session_dropped_bytes is not None and (
            isinstance(rollover_session_dropped_bytes, bool)
            or not isinstance(rollover_session_dropped_bytes, int)
            or rollover_session_dropped_bytes < 0
        ):
            raise ValueError(
                "rollover_session_dropped_bytes must be a non-negative integer"
            )
        if rollover_reported_loss is not None and not isinstance(
            rollover_reported_loss, bool
        ):
            raise ValueError("rollover_reported_loss must be a boolean")
        with self._store_lock:
            metadata = self._require_active_v2_metadata(handle)
            if event.segment_id != _current_v2_segment_id(metadata):
                raise ValueError("v2 telemetry must reference the current segment")

            def record_integrity(
                updated: dict[str, object],
                _admission: V2EvidenceAdmission,
            ) -> None:
                rolled_over = _admission.rolled_over
                dropped_bytes = (
                    rollover_session_dropped_bytes
                    if rolled_over and rollover_session_dropped_bytes is not None
                    else session_dropped_bytes
                    if session_dropped_bytes is not None
                    else event.dropped_bytes_total
                )
                loss = (
                    rollover_reported_loss
                    if rolled_over and rollover_reported_loss is not None
                    else reported_loss
                )
                _record_v2_integrity_loss(
                    updated,
                    dropped_bytes=dropped_bytes,
                    cumulative=True,
                    reported_loss=loss,
                )
                _metadata._record_metadata_segment_timestamp(
                    updated,
                    segment_id=_current_v2_segment_id(updated),
                    timestamp_us=event.timestamp_us,
                )

            return self._append_v2_record_locked(
                handle,
                stream="hardware",
                record_type="buffer_status",
                fields=lambda _handle, updated, _evidence_seq: {
                    "segment_id": _current_v2_segment_id(updated),
                    "timestamp_us": event.timestamp_us,
                    "uart_rx_size_bytes": event.size_bytes,
                    "uart_rx_used_bytes": event.used_bytes,
                    "uart_rx_high_water_bytes": event.high_water_bytes,
                    "dropped_bytes_total": event.dropped_bytes_total,
                    "overflow_events": event.overflow_events,
                },
                metadata_mutator=record_integrity,
            )

    def _append_v2_record_locked(
        self,
        handle: SessionHandle,
        *,
        stream: Literal["operation", "hardware", "connection"],
        record_type: str,
        fields: dict[str, object]
        | Callable[[SessionHandle, dict[str, object], int], dict[str, object]],
        metadata_mutator: Callable[
            [dict[str, object], V2EvidenceAdmission], None
        ]
        | None = None,
    ) -> V2EvidenceAdmission:
        metadata = self._require_active_v2_metadata(handle)
        evidence_seq = _v2_next_sequence(metadata)
        record = self._v2_record(
            handle,
            metadata=metadata,
            evidence_seq=evidence_seq,
            record_type=record_type,
            fields=fields,
        )
        serialized_record = _persistence.serialize_jsonl(record)
        if len(serialized_record) > _metadata.MAX_V2_JSONL_RECORD_BYTES:
            raise ValueError("schema-v2 primary JSONL record exceeds its size limit")
        if not self._v2_unit_fits(metadata, unit_bytes=len(serialized_record)):
            handle = self._rollover_v2_locked(handle, end_reason="rollover_size")
            metadata = self._require_active_v2_metadata(handle)
            evidence_seq = _v2_next_sequence(metadata)
            record = self._v2_record(
                handle,
                metadata=metadata,
                evidence_seq=evidence_seq,
                record_type=record_type,
                fields=fields,
            )
            serialized_record = _persistence.serialize_jsonl(record)
            if len(serialized_record) > _metadata.MAX_V2_JSONL_RECORD_BYTES:
                raise ValueError("schema-v2 primary JSONL record exceeds its size limit")
            if not self._v2_unit_fits(metadata, unit_bytes=len(serialized_record)):
                raise SessionPersistenceError(
                    operation="preflight v2 evidence",
                    path=handle.paths.root,
                    detail="one schema-valid record exceeds the session budget",
                )
            rolled_over = True
        else:
            rolled_over = False
        path = {
            "operation": handle.paths.operation_events,
            "hardware": handle.paths.hardware_events,
            "connection": handle.paths.connection_events,
        }[stream]
        admission = V2EvidenceAdmission(
            handle=handle,
            evidence_seq=evidence_seq,
            rolled_over=rolled_over,
            next_evidence_seq=evidence_seq + 1,
        )
        try:
            with _transactions.evidence_transaction(
                handle.paths,
                append_paths=[path],
            ) as transaction:
                _persistence.append_serialized(path, serialized_record)
                metadata["next_evidence_seq"] = evidence_seq + 1
                if metadata_mutator is not None:
                    metadata_mutator(metadata, admission)
                _persistence.refresh_storage_accounting(metadata, handle.paths)
                serialized_metadata = _persistence.serialize_compact_json(metadata)
                _require_metadata_capacity(serialized_metadata)
                transaction.prepare_metadata(serialized_metadata)
                _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        except SessionPersistenceError as exc:
            self._fail_active_v2_persistence_locked(handle, cause=exc)
            raise
        return admission

    def _v2_record(
        self,
        handle: SessionHandle,
        *,
        metadata: dict[str, object],
        evidence_seq: int,
        record_type: str,
        fields: dict[str, object]
        | Callable[[SessionHandle, dict[str, object], int], dict[str, object]],
    ) -> dict[str, object]:
        record_fields = (
            fields(handle, metadata, evidence_seq) if callable(fields) else fields
        )
        return {
            "evidence_seq": evidence_seq,
            "type": record_type,
            "recorded_at": _metadata._format_utc_timestamp(self._clock()),
            **record_fields,
        }

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
        schema_version = metadata.get("schema_version")
        if schema_version not in {1, 2}:
            raise ValueError("only native schema-v1/v2 sessions can be terminalized")
        if metadata.get("state") != "active":
            raise ValueError("session lifecycle transition requires active state")
        if metadata_mutator is not None:
            metadata_mutator(metadata)
        if schema_version == 2:
            _relinquish_v2_ownership(metadata)
        if schema_version == 1 and metadata.get("workflow") == "wait_pattern" and metadata.get(
            "matched"
        ) is None:
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
        serialized_metadata = (
            _persistence.serialize_compact_json(metadata)
            if schema_version == 2
            else _persistence.serialize_json(metadata)
        )
        _require_metadata_capacity(serialized_metadata)
        _persistence.remove_file(handle.paths.terminal_reserve, missing_ok=True)
        _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        for reservation_key in tuple(self._uart_tx_result_reservations):
            if reservation_key[0] == handle.session_id:
                del self._uart_tx_result_reservations[reservation_key]
        self._v2_profiles.pop(handle.session_id, None)
        self._v2_snapshots.pop(handle.session_id, None)

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
    ) -> tuple[int, ...]:
        """Append one processed normalized UART event to a session."""

        _persistence.require_session_appendable(handle)
        if event.segment_id != result.segment_id:
            raise ValueError("UART event and capture result segments must match")
        if event.channel != result.channel:
            raise ValueError("UART event and capture result channels must match")
        if event.timestamp_us != result.timestamp_us:
            raise ValueError("UART event and capture result timestamps must match")

        metadata = _persistence.read_json_object(handle.paths.metadata)
        uart_event_bytes = _persistence.serialize_jsonl(
            _session_evidence_record(
                _evidence.uart_event_json(event),
                metadata=metadata,
                segment_id=event.segment_id,
            )
        )
        pattern_records = [
            _session_evidence_record(
                record,
                metadata=metadata,
                segment_id=event.segment_id,
            )
            for record in _evidence.detected_pattern_records(
                result,
                segment_id=event.segment_id,
            )
        ]
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
                _session_evidence_record(
                    _evidence.line_limit_exceeded_event_json(result, oversized_line),
                    metadata=metadata,
                    segment_id=result.segment_id,
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

    def append_uart_capture_batch(
        self,
        handle: SessionHandle,
        *,
        captures: Sequence[tuple[UartReceiveEvent, UartCaptureResult]],
    ) -> tuple[tuple[int, ...], ...] | None:
        """Append ordered UART evidence in one transaction when quota permits."""

        if not captures:
            raise ValueError("UART capture batch must not be empty")
        _persistence.require_session_appendable(handle)
        metadata = _persistence.read_json_object(handle.paths.metadata)
        uart_event_parts: list[bytes] = []
        pattern_record_groups: list[list[dict[str, object]]] = []
        hardware_event_parts: list[bytes] = []
        raw_parts: list[bytes] = []

        for event, result in captures:
            if event.segment_id != result.segment_id:
                raise ValueError("UART event and capture result segments must match")
            if event.channel != result.channel:
                raise ValueError("UART event and capture result channels must match")
            if event.timestamp_us != result.timestamp_us:
                raise ValueError("UART event and capture result timestamps must match")
            raw_parts.append(event.data)
            uart_event_parts.append(
                _persistence.serialize_jsonl(
                    _session_evidence_record(
                        _evidence.uart_event_json(event),
                        metadata=metadata,
                        segment_id=event.segment_id,
                    )
                )
            )
            pattern_record_groups.append(
                [
                    _session_evidence_record(
                        record,
                        metadata=metadata,
                        segment_id=event.segment_id,
                    )
                    for record in _evidence.detected_pattern_records(
                        result,
                        segment_id=event.segment_id,
                    )
                ]
            )
            hardware_event_parts.extend(
                _persistence.serialize_jsonl(
                    _session_evidence_record(
                        _evidence.line_limit_exceeded_event_json(result, oversized_line),
                        metadata=metadata,
                        segment_id=result.segment_id,
                    )
                )
                for oversized_line in result.oversized_lines
            )

        detected_patterns_bytes: bytes | None = None
        detected_patterns_delta = 0
        detected_pattern_indexes: list[tuple[int, ...]] = []
        if any(pattern_record_groups):
            detected_patterns = _persistence.read_json_list(handle.paths.detected_patterns)
            for pattern_records in pattern_record_groups:
                first_index = len(detected_patterns)
                detected_patterns.extend(pattern_records)
                detected_pattern_indexes.append(
                    tuple(range(first_index, first_index + len(pattern_records)))
                )
            detected_patterns_bytes = _persistence.serialize_json(detected_patterns)
            detected_patterns_delta = (
                len(detected_patterns_bytes) - handle.paths.detected_patterns.stat().st_size
            )
        else:
            detected_pattern_indexes.extend(() for _capture in captures)

        raw_bytes = b"".join(raw_parts)
        uart_event_bytes = b"".join(uart_event_parts)
        hardware_event_bytes = b"".join(hardware_event_parts)
        evidence_bytes = (
            len(raw_bytes)
            + len(uart_event_bytes)
            + detected_patterns_delta
            + len(hardware_event_bytes)
        )
        if not self._evidence_fits(handle, evidence_bytes=evidence_bytes):
            return None

        for event, result in captures:
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
            _persistence.append_bytes(handle.paths.uart_raw, raw_bytes)
            _persistence.append_serialized(handle.paths.uart_events, uart_event_bytes)
            if detected_patterns_bytes is not None:
                _persistence.write_serialized(
                    handle.paths.detected_patterns,
                    detected_patterns_bytes,
                )
            if hardware_event_bytes:
                _persistence.append_serialized(
                    handle.paths.hardware_events,
                    hardware_event_bytes,
                )
            _persistence.refresh_storage_accounting(metadata, handle.paths)
            serialized_metadata = _persistence.serialize_json(metadata)
            _require_metadata_capacity(serialized_metadata)
            transaction.prepare_metadata(serialized_metadata)
            _persistence.write_serialized(handle.paths.metadata, serialized_metadata)
        return tuple(detected_pattern_indexes)

    def _evidence_fits(
        self,
        handle: SessionHandle,
        *,
        evidence_bytes: int,
        released_uart_tx_reservation: tuple[str, str] | None = None,
    ) -> bool:
        projection = self._evidence_projection(
            handle,
            evidence_bytes=evidence_bytes,
            released_uart_tx_reservation=released_uart_tx_reservation,
        )
        return projection is None or projection[0] <= projection[1]

    def _evidence_projection(
        self,
        handle: SessionHandle,
        *,
        evidence_bytes: int,
        released_uart_tx_reservation: tuple[str, str] | None = None,
    ) -> tuple[int, int] | None:
        metadata = _persistence.read_json_object(handle.paths.metadata)
        if metadata.get("schema_version") != 1:
            return None
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
        return current_bytes + evidence_bytes + reserved_result_bytes, budget

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
        projection = self._evidence_projection(
            handle,
            evidence_bytes=evidence_bytes,
            released_uart_tx_reservation=released_uart_tx_reservation,
        )
        if projection is None:
            return
        projected_bytes, budget = projection
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
    ) -> None:
        """Persist derived records finalized at segment or session close."""

        _persistence.require_session_appendable(handle)
        for oversized_line in result.oversized_lines:
            metadata = _persistence.read_json_object(handle.paths.metadata)
            event_bytes = _persistence.serialize_jsonl(
                _session_evidence_record(
                    _evidence.line_limit_exceeded_event_json(result, oversized_line),
                    metadata=metadata,
                    segment_id=result.segment_id,
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
    ) -> None:
        """Append one buffer overflow event to a session."""

        _persistence.require_session_appendable(handle)
        metadata = _persistence.read_json_object(handle.paths.metadata)
        event_bytes = _persistence.serialize_jsonl(
            _session_evidence_record(
                _evidence.buffer_overflow_event_json(event),
                metadata=metadata,
                segment_id=event.segment_id,
            )
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
        session_dropped_bytes_total: int | None = None,
        session_overflow_events: int | None = None,
    ) -> None:
        """Retain raw MCU status; optionally project capture-window loss into metadata."""

        _persistence.require_session_appendable(handle)
        metadata = _persistence.read_json_object(handle.paths.metadata)
        event_bytes = _persistence.serialize_jsonl(
            _session_evidence_record(
                _evidence.buffer_status_event_json(event),
                metadata=metadata,
                segment_id=event.segment_id,
            )
        )

        observed_dropped = (
            event.dropped_bytes_total
            if session_dropped_bytes_total is None
            else session_dropped_bytes_total
        )
        observed_overflows = (
            event.overflow_events if session_overflow_events is None else session_overflow_events
        )

        def record_summary(metadata: dict[str, object]) -> None:
            _metadata._record_metadata_segment_timestamp(
                metadata,
                segment_id=event.segment_id,
                timestamp_us=event.timestamp_us,
            )
            if observed_dropped > 0 or observed_overflows > 0:
                metadata["overflow"] = True
                _metadata._record_integrity_loss(
                    metadata,
                    dropped_bytes=observed_dropped,
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


def _v2_pattern_document(
    handle: SessionHandle,
    *,
    source_evidence_seq: int,
    event: UartReceiveEvent,
    detected_patterns: Sequence[dict[str, object]],
) -> tuple[bytes | None, int]:
    if not detected_patterns:
        return None, 0
    if len(detected_patterns) > _metadata.MAX_V2_DETECTED_PATTERNS_PER_UART_EVENT:
        raise ValueError("one v2 UART unit may contain at most 12 detected patterns")
    existing = _persistence.read_json_list(handle.paths.detected_patterns)
    projected = list(existing)
    for supplied in detected_patterns:
        pattern = dict(supplied)
        pattern["source_evidence_seq"] = source_evidence_seq
        pattern_name = pattern.get("pattern")
        if (
            not isinstance(pattern_name, str)
            or not 1 <= len(pattern_name.encode("utf-8")) <= 256
            or "\r" in pattern_name
            or "\n" in pattern_name
        ):
            raise ValueError("v2 detected pattern must contain 1..256 UTF-8 bytes without CR/LF")
        if pattern.get("segment_id") != event.segment_id:
            raise ValueError("v2 detected pattern segment does not match source UART")
        if pattern.get("timestamp_us") != event.timestamp_us:
            raise ValueError("v2 detected pattern timestamp does not match source UART")
        if pattern.get("channel") != event.channel:
            raise ValueError("v2 detected pattern channel does not match source UART")
        serialized_record = _persistence.serialize_compact_json(pattern)
        if len(serialized_record) > _metadata.MAX_V2_JSONL_RECORD_BYTES:
            raise ValueError("schema-v2 detected pattern exceeds its size limit")
        projected.append(pattern)
        _evidence.detected_pattern_at(projected, len(projected) - 1)
    serialized = _persistence.serialize_compact_json(projected)
    try:
        current_size = handle.paths.detected_patterns.stat().st_size
    except OSError as exc:
        raise SessionPersistenceError(
            operation="read detected-pattern size",
            path=handle.paths.detected_patterns,
            detail=str(exc),
        ) from exc
    growth = len(serialized) - current_size
    if growth < 0:
        raise ValueError("v2 detected-pattern document cannot shrink during append")
    return serialized, growth


def _v2_next_sequence(metadata: dict[str, object]) -> int:
    value = metadata.get("next_evidence_seq")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("v2 next_evidence_seq must be a non-negative integer")
    return value


def _v2_count(summary: dict[str, object], key: str) -> int:
    value = summary.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"v2 operation summary {key} count is invalid")
    return value


def _current_v2_segment_id(metadata: dict[str, object]) -> int:
    segments = metadata.get("segments")
    if not isinstance(segments, list) or not segments or not isinstance(segments[-1], dict):
        raise ValueError("v2 session must contain a current segment")
    segment_id = segments[-1].get("segment_id")
    if isinstance(segment_id, bool) or not isinstance(segment_id, int) or segment_id < 0:
        raise ValueError("v2 current segment ID is invalid")
    return segment_id


def _validate_v2_identifier(value: object, *, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must contain 1..128 UTF-8 bytes")
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError(f"{field} must not contain Unicode control characters") from exc
    if len(encoded) > 128:
        raise ValueError(f"{field} must contain 1..128 UTF-8 bytes")
    if value[0].isspace() or value[-1].isspace():
        raise ValueError(f"{field} must not contain edge whitespace")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(f"{field} must not contain Unicode control characters")
    return value


def _bounded_v2_operation_error(error: dict[str, object]) -> dict[str, object]:
    if not isinstance(error, dict):
        raise ValueError("operation error data must be an object")
    code = _validate_v2_identifier(error.get("code"), field="operation error code")
    detail = error.get("detail")
    if not isinstance(detail, str):
        raise ValueError("operation error detail must be a string")
    return _metadata._bounded_error(code, detail)


def _require_v2_operation_active(
    metadata: dict[str, object],
    operation_id: str | None,
) -> None:
    if operation_id is None:
        return
    operations = metadata.get("active_operations")
    if not isinstance(operations, dict):
        raise ValueError("v2 active_operations must be an object")
    if not isinstance(operations.get(operation_id), dict):
        raise ValueError("v2 action operation_id must reference an active operation")


def _record_v2_integrity_loss(
    metadata: dict[str, object],
    *,
    dropped_bytes: int,
    cumulative: bool,
    reported_loss: bool | None = None,
) -> None:
    quality = metadata.get("evidence_quality")
    if not isinstance(quality, dict):
        raise ValueError("v2 evidence_quality must be an object")
    integrity = quality.get("backend_integrity")
    if not isinstance(integrity, dict):
        raise ValueError("v2 backend_integrity must be an object")
    previous = integrity.get("dropped_bytes")
    if isinstance(previous, bool) or not isinstance(previous, int) or previous < 0:
        raise ValueError("v2 backend integrity dropped bytes are invalid")
    observed = max(previous, dropped_bytes) if cumulative else previous + dropped_bytes
    integrity.update(
        {
            "loss_status": (
                "loss_reported"
                if observed or reported_loss is True
                else "none_reported"
            ),
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": observed,
        }
    )


def _require_matching_capture_result(
    event: UartReceiveEvent,
    result: UartCaptureResult,
) -> None:
    if event.segment_id != result.segment_id:
        raise ValueError("UART event and capture result segments must match")
    if event.channel != result.channel:
        raise ValueError("UART event and capture result channels must match")
    if event.timestamp_us != result.timestamp_us:
        raise ValueError("UART event and capture result timestamps must match")


def _v2_operation_id_seen(path: Path, operation_id: str) -> bool:
    try:
        with path.open(encoding="utf-8") as records:
            for line in records:
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError(f"{path.name} record must be a JSON object")
                if value.get("type") not in {
                    "operation_started",
                    "operation_continued",
                    "operation_terminal",
                }:
                    continue
                recorded_id = value.get("operation_id")
                if not isinstance(recorded_id, str):
                    raise ValueError(f"{path.name} operation_id is invalid")
                if recorded_id == operation_id:
                    return True
    except OSError as exc:
        raise SessionPersistenceError(
            operation="read operation IDs",
            path=path,
            detail=str(exc),
        ) from exc
    return False


def _v2_attempt_key(attempt_type: str, attempt_id: str) -> str:
    return f"{attempt_type}:{attempt_id}"


def _v2_pending_attempts(
    metadata: dict[str, object],
) -> dict[str, dict[str, object]]:
    raw_pending = metadata.get("pending_attempts")
    if not isinstance(raw_pending, dict):
        raise ValueError("v2 pending_attempts must be an object")
    for key, attempt in raw_pending.items():
        if not isinstance(key, str) or not isinstance(attempt, dict):
            raise ValueError("v2 pending attempt metadata is malformed")
        attempt_type = attempt.get("attempt_type")
        attempt_id = attempt.get("attempt_id")
        session_id = attempt.get("session_id")
        evidence_seq = attempt.get("evidence_seq")
        if attempt_type not in {"uart_tx_attempt", "control_attempt"}:
            raise ValueError("v2 pending attempt type is invalid")
        if not isinstance(attempt_id, str) or key != _v2_attempt_key(
            attempt_type, attempt_id
        ):
            raise ValueError("v2 pending attempt identity is invalid")
        if not isinstance(session_id, str):
            raise ValueError("v2 pending attempt session ID is invalid")
        _metadata._validate_session_id(session_id)
        if (
            isinstance(evidence_seq, bool)
            or not isinstance(evidence_seq, int)
            or evidence_seq < 0
        ):
            raise ValueError("v2 pending attempt evidence sequence is invalid")
    return cast(dict[str, dict[str, object]], raw_pending)


def _v2_pending_attempt(
    metadata: dict[str, object],
    attempt_type: Literal["uart_tx_attempt", "control_attempt"],
    attempt_id: str,
) -> dict[str, object] | None:
    return _v2_pending_attempts(metadata).get(_v2_attempt_key(attempt_type, attempt_id))


def _relinquish_v2_ownership(metadata: dict[str, object]) -> None:
    active = metadata.get("active_operations")
    interrupted = metadata.get("interrupted_operations")
    summary = metadata.get("operation_summary")
    if not isinstance(active, dict) or not isinstance(interrupted, dict):
        raise ValueError("v2 operation ownership metadata is malformed")
    if not isinstance(summary, dict):
        raise ValueError("v2 operation summary is malformed")
    if _v2_count(summary, "active") != len(active):
        raise ValueError("v2 active operation summary disagrees with ownership")
    end_evidence_seq = _v2_next_sequence(metadata)
    for operation_id, raw_operation in active.items():
        if not isinstance(operation_id, str) or not isinstance(raw_operation, dict):
            raise ValueError("v2 active operation metadata is malformed")
        if operation_id in interrupted:
            raise ValueError("v2 interrupted operation ID is duplicated")
        raw_ranges = raw_operation.get("ranges")
        if not isinstance(raw_ranges, list) or not raw_ranges:
            raise ValueError("v2 active operation ranges are malformed")
        ranges = [dict(item) for item in raw_ranges if isinstance(item, dict)]
        if len(ranges) != len(raw_ranges):
            raise ValueError("v2 active operation range is malformed")
        if ranges[-1].get("end_evidence_seq_exclusive") is not None:
            raise ValueError("v2 active operation range is already closed")
        ranges[-1]["end_evidence_seq_exclusive"] = end_evidence_seq
        interrupted[operation_id] = {
            "operation_type": raw_operation.get("operation_type"),
            "ranges": ranges,
        }
    active.clear()
    summary["active"] = 0


def _v2_attempt_ids(
    path: Path,
    *,
    attempt_type: str,
    result_type: str,
) -> tuple[set[str], set[str]]:
    seen: set[str] = set()
    pending: set[str] = set()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as exc:
        raise SessionPersistenceError(
            operation="read attempts",
            path=path,
            detail=str(exc),
        ) from exc
    for line in lines:
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path.name} record must be a JSON object")
        event_type = value.get("type")
        if event_type not in {attempt_type, result_type}:
            continue
        attempt_id = value.get("attempt_id")
        if not isinstance(attempt_id, str):
            raise ValueError(f"{path.name} attempt_id is invalid")
        if event_type == attempt_type:
            if attempt_id in seen:
                raise ValueError(f"{path.name} contains a duplicate attempt ID")
            seen.add(attempt_id)
            pending.add(attempt_id)
        elif value.get("attempt_session_id", path.parent.name) != path.parent.name:
            continue
        elif attempt_id not in pending:
            raise ValueError(f"{path.name} result has no preceding unresolved attempt")
        else:
            pending.remove(attempt_id)
    return seen, pending


def _session_evidence_record(
    record: dict[str, object],
    *,
    metadata: dict[str, object],
    segment_id: int,
) -> dict[str, object]:
    """Retain the recognized unversioned evidence shape without polluting v1."""

    if metadata.get("schema_version", 0) == 0:
        return {**record, "timestamp_epoch": segment_id}
    return record
