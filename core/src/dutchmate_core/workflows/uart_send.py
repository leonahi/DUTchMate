"""Exact-byte UART dispatch audited in the continuous ownership session."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING
from uuid import uuid4

from dutchmate_core.backends.contracts import (
    BackendInputError,
    BackendWriteError,
    UartSender,
)
from dutchmate_core.session_store.models import SessionPersistenceError, V2EvidenceAdmission
from dutchmate_core.validation import UartTxPayload

if TYPE_CHECKING:
    from dutchmate_core.evidence.recorder import ContinuousEvidenceRecorder


@dataclass(frozen=True, slots=True)
class UartSendResult:
    """Known successful TX with exact payload and durable action references."""

    performed_at: str
    device_timestamp_us: int | None
    attempt_id: str
    data_b64: str
    accepted_bytes: int
    status: str
    audit_status: str
    transformation: dict[str, object]
    attempt_session_id: str
    attempt_evidence_seq: int
    result_session_id: str
    result_evidence_seq: int


class UartSendError(RuntimeError):
    """Canonical TX failure with bounded audit context."""

    def __init__(
        self,
        *,
        error: str,
        detail: str,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail
        self.context = context.copy() if context is not None else None


class UartSendWorkflow:
    """Dispatch once; acquisition continues independently throughout the action."""

    def __init__(
        self,
        *,
        sender: UartSender,
        wall_clock: Callable[[], datetime] | None = None,
        attempt_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._sender = sender
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc))
        self._attempt_id_factory = attempt_id_factory or (lambda: str(uuid4()))

    def run(
        self,
        payload: UartTxPayload,
        *,
        recorder: ContinuousEvidenceRecorder,
        operation_id: str | None = None,
    ) -> UartSendResult:
        connection_generation = recorder.capture_source_health().connection_generation
        attempt_id = self._attempt_id_factory()
        attempt = recorder.audit_uart_attempt(
            attempt_id=attempt_id,
            data=payload.data,
            operation_id=operation_id,
            transformation=payload.transformation(),
        )
        try:
            backend_result = self._sender.send_uart(payload.data)
            if backend_result.bytes_accepted != len(payload.data):
                raise BackendWriteError(
                    "UART backend did not accept the complete payload",
                    bytes_accepted=backend_result.bytes_accepted,
                )
        except (BackendWriteError, BackendInputError) as exc:
            accepted = exc.bytes_accepted if isinstance(exc, BackendWriteError) else None
            health = recorder.capture_source_health()
            interrupted = (
                not health.connected or health.connection_generation != connection_generation
            )
            self._record_result(recorder, attempt_id, exc.error, accepted)
            if isinstance(exc, BackendInputError):
                recorder.backend_input_failed(exc)
            raise UartSendError(
                error=exc.error,
                detail="UART transmission failed",
                context={
                    "attempt_id": attempt_id,
                    "bytes_accepted": accepted,
                    "may_have_reached_dut": True,
                    "connection_interrupted": interrupted,
                },
            ) from exc
        result = self._record_result(
            recorder,
            attempt_id,
            "success",
            backend_result.bytes_accepted,
        )
        performed_at = self._wall_clock()
        if performed_at.tzinfo is None:
            performed_at = performed_at.replace(tzinfo=timezone.utc)
        return UartSendResult(
            performed_at=performed_at.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
            device_timestamp_us=backend_result.device_timestamp_us,
            attempt_id=attempt_id,
            data_b64=payload.data_b64,
            accepted_bytes=backend_result.bytes_accepted,
            status="success",
            audit_status="recorded",
            transformation=payload.transformation(),
            attempt_session_id=attempt.handle.session_id,
            attempt_evidence_seq=attempt.evidence_seq,
            result_session_id=result.handle.session_id,
            result_evidence_seq=result.evidence_seq,
        )

    @staticmethod
    def _record_result(
        recorder: ContinuousEvidenceRecorder,
        attempt_id: str,
        status: str,
        accepted_bytes: int | None,
    ) -> V2EvidenceAdmission:
        try:
            return recorder.audit_uart_result(
                attempt_id=attempt_id,
                status=status,
                accepted_bytes=accepted_bytes,
            )
        except (SessionPersistenceError, RuntimeError, ValueError) as exc:
            raise UartSendError(
                error="persistence_fault",
                detail="UART result could not be stored; the durable attempt outcome is unknown",
                context={
                    "attempt_id": attempt_id,
                    "outcome": "unknown",
                    "may_have_reached_dut": True,
                },
            ) from exc
