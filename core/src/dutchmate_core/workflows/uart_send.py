"""Validated UART-send dispatch and forced-session perturbation recording."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, Protocol
from uuid import uuid4

from dutchmate_core.backends.contracts import (
    BackendUartSendResult,
    BackendWriteError,
    SegmentContext,
    UartSender,
)
from dutchmate_core.session_store.models import (
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionPersistenceError,
)
from dutchmate_core.workflows.capture import SessionMutationLock


class UartSendSessionStorage(Protocol):
    """Perturbation evidence operations required by UART send."""

    def append_uart_tx_attempt(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        segment_id: int,
        attempted_at: str,
        data: bytes,
    ) -> None:
        """Append an admitted pre-dispatch attempt."""

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
        """Append the matching post-dispatch result."""


@dataclass(frozen=True, slots=True)
class ActiveUartSendSession:
    """Published active-session identity and current timestamp segment."""

    handle: SessionHandle
    segment: SegmentContext


@dataclass(frozen=True, slots=True)
class UartSendResult:
    """Successful public UART-send result."""

    performed_at: str
    device_timestamp_us: int | None
    attempt_id: str | None
    perturbation_logged: bool


class UartSendError(RuntimeError):
    """Canonical UART-send failure with optional audit context."""

    def __init__(
        self,
        *,
        error: str,
        detail: str,
        context: dict[str, object] | None = None,
        session_terminalized: bool = False,
    ) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail
        self.context = context.copy() if context is not None else None
        self.session_terminalized = session_terminalized


class UartSendWorkflow:
    """Dispatch complete payloads and record forced in-session evidence."""

    def __init__(
        self,
        *,
        sender: UartSender,
        session_store: UartSendSessionStorage,
        mutation_lock: SessionMutationLock,
        wall_clock: Callable[[], datetime] | None = None,
        monotonic_ns: Callable[[], int] | None = None,
        attempt_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._sender = sender
        self._session_store = session_store
        self._mutation_lock = mutation_lock
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc))
        self._monotonic_ns = monotonic_ns or time.monotonic_ns
        self._attempt_id_factory = attempt_id_factory or (lambda: uuid4().hex)

    def run(
        self,
        payload: bytes,
        *,
        active_session: ActiveUartSendSession | None,
    ) -> UartSendResult:
        """Send one validated payload, optionally as a recorded perturbation."""

        attempt_id = self._attempt_id_factory() if active_session is not None else None
        with self._mutation_lock:
            if active_session is not None and attempt_id is not None:
                try:
                    self._session_store.append_uart_tx_attempt(
                        active_session.handle,
                        attempt_id=attempt_id,
                        segment_id=active_session.segment.segment_id,
                        attempted_at=_format_utc(self._wall_clock()),
                        data=payload,
                    )
                except EvidenceQuotaExceeded as exc:
                    raise UartSendError(
                        error="persistence_fault",
                        detail=(
                            "UART send was not dispatched because its attempt exceeded "
                            "the session evidence budget"
                        ),
                        session_terminalized=True,
                    ) from exc
                except SessionPersistenceError as exc:
                    raise UartSendError(
                        error="persistence_fault",
                        detail=(
                            "UART send was not dispatched because its attempt "
                            f"could not be stored: {exc}"
                        ),
                    ) from exc

            try:
                backend_result = self._sender.send_uart(payload)
                self._require_complete_acceptance(backend_result, len(payload))
                timestamp_us = (
                    self._normalized_completion_timestamp(
                        active_session.segment,
                        backend_result,
                    )
                    if active_session is not None
                    else None
                )
            except BackendWriteError as exc:
                self._record_failed_result(
                    active_session=active_session,
                    attempt_id=attempt_id,
                    error=exc.error,
                    bytes_accepted=exc.bytes_accepted,
                )
                context: dict[str, object] = {
                    "bytes_accepted": exc.bytes_accepted,
                    "may_have_reached_dut": True,
                }
                if attempt_id is not None:
                    context["attempt_id"] = attempt_id
                raise UartSendError(
                    error=exc.error,
                    detail=str(exc),
                    context=context,
                ) from exc

            completed_at = _format_utc(self._wall_clock())
            if active_session is not None and attempt_id is not None:
                self._append_result_or_raise_unknown(
                    active_session=active_session,
                    attempt_id=attempt_id,
                    completed_at=completed_at,
                    outcome="success",
                    error=None,
                    bytes_accepted=backend_result.bytes_accepted,
                    timestamp_us=timestamp_us,
                    device_timestamp_us=backend_result.device_timestamp_us,
                )
            return UartSendResult(
                performed_at=completed_at,
                device_timestamp_us=backend_result.device_timestamp_us,
                attempt_id=attempt_id,
                perturbation_logged=attempt_id is not None,
            )

    def _record_failed_result(
        self,
        *,
        active_session: ActiveUartSendSession | None,
        attempt_id: str | None,
        error: str,
        bytes_accepted: int | None,
    ) -> None:
        if active_session is None or attempt_id is None:
            return
        timestamp_us = (
            self._host_completion_timestamp(active_session.segment)
            if active_session.segment.timestamp.source == "host"
            else None
        )
        self._append_result_or_raise_unknown(
            active_session=active_session,
            attempt_id=attempt_id,
            completed_at=_format_utc(self._wall_clock()),
            outcome="failed",
            error=error,
            bytes_accepted=bytes_accepted,
            timestamp_us=timestamp_us,
            device_timestamp_us=None,
        )

    def _append_result_or_raise_unknown(
        self,
        *,
        active_session: ActiveUartSendSession,
        attempt_id: str,
        completed_at: str,
        outcome: Literal["success", "failed"],
        error: str | None,
        bytes_accepted: int | None,
        timestamp_us: int | None,
        device_timestamp_us: int | None,
    ) -> None:
        try:
            self._session_store.append_uart_tx_result(
                active_session.handle,
                attempt_id=attempt_id,
                segment_id=active_session.segment.segment_id,
                completed_at=completed_at,
                outcome=outcome,
                error=error,
                bytes_accepted=bytes_accepted,
                timestamp_us=timestamp_us,
                device_timestamp_us=device_timestamp_us,
            )
        except EvidenceQuotaExceeded as exc:
            raise UartSendError(
                error="persistence_fault",
                detail=(
                    "UART send completion exceeded its admitted reservation; "
                    "the durable attempt outcome is unknown"
                ),
                context={
                    "attempt_id": attempt_id,
                    "outcome": "unknown",
                    "may_have_reached_dut": True,
                },
                session_terminalized=True,
            ) from exc
        except SessionPersistenceError as exc:
            raise UartSendError(
                error="persistence_fault",
                detail=(
                    "UART send completion could not be stored; the durable attempt "
                    "outcome is unknown"
                ),
                context={
                    "attempt_id": attempt_id,
                    "outcome": "unknown",
                    "may_have_reached_dut": True,
                },
            ) from exc

    @staticmethod
    def _require_complete_acceptance(result: BackendUartSendResult, payload_bytes: int) -> None:
        if result.bytes_accepted != payload_bytes:
            raise BackendWriteError(
                "UART backend did not accept the complete payload",
                bytes_accepted=result.bytes_accepted,
            )

    def _normalized_completion_timestamp(
        self,
        segment: SegmentContext,
        result: BackendUartSendResult,
    ) -> int:
        if segment.timestamp.source == "host":
            if result.device_timestamp_us is not None:
                raise BackendWriteError(
                    "Host-timestamped UART backend returned a device timestamp",
                    bytes_accepted=result.bytes_accepted,
                )
            return self._host_completion_timestamp(segment)
        if result.device_timestamp_us is None:
            raise BackendWriteError(
                "Device-timestamped UART backend omitted its completion timestamp",
                bytes_accepted=result.bytes_accepted,
            )
        return _relative_timestamp(
            result.device_timestamp_us,
            segment.timestamp.source_origin_us,
        )

    def _host_completion_timestamp(self, segment: SegmentContext) -> int:
        return _relative_timestamp(
            self._monotonic_ns() // 1_000,
            segment.timestamp.source_origin_us,
        )


def _relative_timestamp(source_us: int, origin_us: int) -> int:
    if source_us < origin_us:
        raise BackendWriteError(
            "UART send completion timestamp precedes the active segment origin",
            bytes_accepted=None,
        )
    return source_us - origin_us


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
