"""Frozen pre-v2 fixture construction from Stage 7 (9a228fcc).

Test-only: never imported by a distribution. Production SessionStore has no
legacy creation/append API. These builders preserve compatibility test inputs;
the inherited production queries are the read-only boundary under test.
"""

from collections.abc import Callable, Sequence
from typing import Literal

import legacy_evidence as _evidence
import legacy_metadata as _metadata

import dutchmate_core.session_store.persistence as _persistence
import dutchmate_core.session_store.transactions as _transactions
from dutchmate_core.backends.contracts import (
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartReceiveEvent,
)
from dutchmate_core.session_store.models import (
    CommandedBootMode,
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionWorkflow,
)
from dutchmate_core.session_store.store import (
    SessionStore,
    _relinquish_v2_ownership,
    _require_metadata_capacity,
)
from dutchmate_core.uart_capture.processor import UartCaptureResult


class LegacySessionFixtureBuilder(SessionStore):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._uart_tx_result_reservations = {}

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
            if detected_pattern is not None and detected_pattern.pattern != metadata.get("pattern"):
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

    def append_uart_capture(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        result: UartCaptureResult,
    ) -> tuple[int, ...]:
        """Append one processed normalized UART event to a session."""

        _require_legacy_appendable(handle)
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
            detected_pattern_indexes = tuple(range(first_index, first_index + len(pattern_records)))
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
        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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

        _require_legacy_appendable(handle)
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
        if (
            schema_version == 1
            and metadata.get("workflow") == "wait_pattern"
            and metadata.get("matched") is None
        ):
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


def _require_legacy_appendable(handle):
    metadata = _persistence.read_json_object(handle.paths.metadata)
    if metadata.get("schema_version") == 1 and metadata.get("state") != "active":
        raise ValueError("native session evidence can only append while active")
