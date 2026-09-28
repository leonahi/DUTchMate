"""Core-owned continuous backend-to-session evidence recorder."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass, replace
from threading import Condition, Event, RLock, Thread
from typing import Literal, Protocol

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendEvent,
    BackendInputError,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartIntegrity,
    UartReceiveEvent,
)
from dutchmate_core.profile import DutProfile
from dutchmate_core.session_store.models import (
    SessionHandle,
    SessionPersistenceError,
    V2EvidenceAdmission,
)
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult
from dutchmate_core.workflows.capture import CaptureEventSource, CaptureSourceHealth


@dataclass(frozen=True, slots=True)
class DurableEvidenceTail:
    """Last durably published position in one active ownership session."""

    session_id: str
    next_evidence_seq: int


RecorderState = Literal[
    "connected",
    "reconnecting",
    "disconnected",
    "faulted",
    "closed",
]


class EvidenceRecorderStore(Protocol):
    """Schema-v2 persistence used by the authoritative recorder."""

    def create_v2_session(
        self,
        *,
        profile: DutProfile,
        backend_snapshot: BackendSnapshot,
    ) -> SessionHandle: ...

    def append_v2_uart_receive(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        detected_patterns: Sequence[dict[str, object]] = (),
        capture_result: UartCaptureResult | None = None,
        rollover_capture_result: UartCaptureResult | None = None,
    ) -> V2EvidenceAdmission: ...

    def v2_uart_receive_will_rollover(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        capture_result: UartCaptureResult,
    ) -> bool: ...

    def append_v2_line_boundary(
        self,
        handle: SessionHandle,
        *,
        results: Sequence[UartCaptureResult],
    ) -> tuple[V2EvidenceAdmission, ...]: ...

    def append_v2_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        session_dropped_bytes: int | None = None,
        rollover_session_dropped_bytes: int | None = None,
    ) -> V2EvidenceAdmission: ...

    def append_v2_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        session_dropped_bytes: int | None = None,
        reported_loss: bool | None = None,
        rollover_session_dropped_bytes: int | None = None,
        rollover_reported_loss: bool | None = None,
    ) -> V2EvidenceAdmission: ...

    def v2_telemetry_will_rollover(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent | BufferStatusEvent,
    ) -> bool: ...

    def append_v2_connection_event(
        self,
        handle: SessionHandle,
        *,
        event_type: str,
        segment_id: int | None,
        detail: dict[str, object],
    ) -> V2EvidenceAdmission: ...

    def append_v2_segment(
        self,
        handle: SessionHandle,
        *,
        backend_snapshot: BackendSnapshot,
    ) -> SessionHandle: ...

    def complete_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str = "duration_elapsed",
    ) -> None: ...

    def fail_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str,
        error_code: str,
        detail: str,
    ) -> None: ...

    def load_metadata(self, session_id: str) -> dict[str, object]: ...


class ContinuousEvidenceRecorder:
    """Persist every normalized backend event through one serialized path."""

    def __init__(
        self,
        *,
        source: CaptureEventSource,
        session_store: EvidenceRecorderStore,
        profile: DutProfile,
        backend_snapshot: BackendSnapshot,
        thread_factory: Callable[..., Thread] = Thread,
    ) -> None:
        source_segment = _source_segment(source)
        if backend_snapshot.segment is None or source_segment != backend_snapshot.segment:
            raise ValueError("recorder source segment must match its backend snapshot")
        self._condition = Condition(RLock())
        self._session_store = session_store
        self._profile = profile
        self._source: CaptureEventSource | None = source
        self._source_segment_id = source_segment.segment_id
        self._segment = source_segment
        self._stored_segment_id = 0
        self._connection_generation = 0
        self._health = CaptureSourceHealth(
            connected=True,
            integrity=backend_snapshot.integrity,
            backend_snapshot=backend_snapshot,
            connection_generation=0,
        )
        self._processor = UartCaptureProcessor()
        self._status_baseline: tuple[int, int] | None = None
        self._session_dropped_bytes = (
            backend_snapshot.integrity.dropped_bytes
            if backend_snapshot.integrity is not None
            and backend_snapshot.integrity.dropped_bytes is not None
            else 0
        )
        self._connection_start_dropped_bytes = self._session_dropped_bytes
        self._explicit_overflow_bytes = 0
        self._state: RecorderState = "connected"
        self._fault: BaseException | None = None
        self._replacement_allowed = False
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._close_error: BaseException | None = None
        self._source_close_complete = False

        handle = session_store.create_v2_session(
            profile=profile,
            backend_snapshot=backend_snapshot,
        )
        try:
            connected = session_store.append_v2_connection_event(
                handle,
                event_type="connected",
                segment_id=0,
                detail={"connection_generation": 0},
            )
        except BaseException:
            with suppress(BaseException):
                _close_source(source)
            raise
        self._handle = connected.handle
        self._tail = DurableEvidenceTail(
            session_id=connected.handle.session_id,
            next_evidence_seq=connected.evidence_seq + 1,
        )
        self._thread = thread_factory(
            target=self._ingest,
            name="dutchmate-evidence-recorder",
            daemon=False,
        )
        try:
            self._thread.start()
        except BaseException as exc:
            with suppress(BaseException):
                _close_source(source)
            with suppress(BaseException):
                session_store.fail_session(
                    self._handle,
                    end_reason="local_ingestion_overflow",
                    error_code="recorder_start_failed",
                    detail=str(exc),
                )
            raise

    @property
    def active_session_id(self) -> str:
        with self._condition:
            return self._handle.session_id

    @property
    def state(self) -> RecorderState:
        with self._condition:
            return self._state

    @property
    def fault(self) -> BaseException | None:
        with self._condition:
            return self._fault

    @property
    def segment(self) -> SegmentContext:
        with self._condition:
            return self._segment

    def capture_source_health(self) -> CaptureSourceHealth:
        """Return immutable connection/integrity state for runtime status."""

        with self._condition:
            return self._health

    def durable_tail(self) -> DurableEvidenceTail:
        """Return the latest position published after durable persistence."""

        with self._condition:
            return self._tail

    def wait_for_durable_tail(
        self,
        previous: DurableEvidenceTail,
        *,
        timeout_s: float,
    ) -> DurableEvidenceTail | None:
        """Wait for a different durable position without affecting ingestion."""

        with self._condition:
            changed = self._condition.wait_for(
                lambda: _tail_is_after(self._tail, previous)
                or self._fault is not None
                or self._closed,
                timeout=timeout_s,
            )
            return self._tail if changed and _tail_is_after(self._tail, previous) else None

    def wait_for_disconnect(self, *, timeout_s: float) -> bool:
        """Wait until the current source has durably entered reconnecting state."""

        with self._condition:
            return self._condition.wait_for(
                lambda: self._state in {"reconnecting", "faulted", "closed"},
                timeout=timeout_s,
            ) and self._state == "reconnecting"

    def wait_for_fault(self, *, timeout_s: float) -> bool:
        """Wait until authoritative recording has faulted."""

        with self._condition:
            return self._condition.wait_for(
                lambda: self._state in {"faulted", "closed"},
                timeout=timeout_s,
            ) and self._state == "faulted"

    def wait_for_idle_disconnect(self, timeout_s: float) -> bool:
        """Reconnect-owner compatibility: wait for a detached-ready disconnect."""

        return self.wait_for_disconnect(timeout_s=timeout_s)

    def close_current_source_for_reconnect(self, *, idle: bool = False) -> None:
        """Detach and close the disconnected source before replacement."""

        del idle
        with self._condition:
            if (
                self._state != "reconnecting"
                or not self._replacement_allowed
                or self._source is None
                or self._closing
            ):
                raise RuntimeError("evidence recorder cannot detach source for reconnect")
            source = self._source
            self._source = None
            self._replacement_allowed = False
            self._condition.notify_all()
        try:
            _close_source(source)
        except BaseException as exc:
            self._record_fatal(exc, end_reason="backend_input_error")
            raise
        with self._condition:
            if not self._closing and self._state == "reconnecting":
                self._replacement_allowed = True
            self._condition.notify_all()

    def replace_source(
        self,
        replacement: CaptureEventSource,
        *,
        backend_snapshot: BackendSnapshot | None = None,
    ) -> None:
        """Durably publish a replacement segment before resuming receive."""

        if backend_snapshot is None or backend_snapshot.segment is None:
            with suppress(BaseException):
                _close_source(replacement)
            raise ValueError("replacement backend snapshot requires segment provenance")
        physical_segment = _source_segment(replacement)
        if physical_segment != backend_snapshot.segment:
            with suppress(BaseException):
                _close_source(replacement)
            raise ValueError("replacement source segment must match its backend snapshot")
        with self._condition:
            if (
                self._state != "reconnecting"
                or not self._replacement_allowed
                or self._source is not None
                or self._closing
            ):
                with suppress(BaseException):
                    _close_source(replacement)
                raise RuntimeError("evidence recorder cannot accept replacement")
            handle = self._handle
            next_segment_id = self._stored_segment_id + 1
        normalized_segment = replace(physical_segment, segment_id=next_segment_id)
        normalized_snapshot = replace(backend_snapshot, segment=normalized_segment)
        try:
            handle = self._session_store.append_v2_segment(
                handle,
                backend_snapshot=normalized_snapshot,
            )
            metadata = self._session_store.load_metadata(handle.session_id)
            segments = metadata.get("segments")
            if not isinstance(segments, list) or not segments:
                raise ValueError("replacement session has no published segment")
            stored_segment_id = len(segments) - 1
            connected = self._session_store.append_v2_connection_event(
                handle,
                event_type="reconnect_succeeded",
                segment_id=stored_segment_id,
                detail={"connection_generation": self._connection_generation + 1},
            )
            metadata = self._session_store.load_metadata(connected.handle.session_id)
            segments = metadata.get("segments")
            if not isinstance(segments, list) or not segments:
                raise ValueError("replacement session has no published segment")
            stored_segment_id = len(segments) - 1
        except BaseException as exc:
            with suppress(BaseException):
                _close_source(replacement)
            self._record_fatal(exc, end_reason="persistence_error")
            raise
        with self._condition:
            if self._closing:
                reject = True
            else:
                reject = False
                rolled_over = connected.handle.session_id != self._handle.session_id
                self._connection_generation += 1
                self._handle = connected.handle
                self._source = replacement
                self._source_segment_id = physical_segment.segment_id
                self._stored_segment_id = stored_segment_id
                self._segment = replace(physical_segment, segment_id=stored_segment_id)
                self._processor = UartCaptureProcessor()
                self._status_baseline = None
                if rolled_over:
                    self._reset_integrity_after_rollover(
                        backend_snapshot.integrity,
                    )
                self._connection_start_dropped_bytes = self._session_dropped_bytes
                self._explicit_overflow_bytes = 0
                prior_integrity = self._health.integrity
                self._health = CaptureSourceHealth(
                    connected=True,
                    integrity=prior_integrity or backend_snapshot.integrity,
                    backend_snapshot=replace(
                        backend_snapshot,
                        segment=self._segment,
                    ),
                    connection_generation=self._connection_generation,
                )
                self._tail = DurableEvidenceTail(
                    connected.handle.session_id,
                    _next_sequence(connected),
                )
                self._state = "connected"
                self._replacement_allowed = False
                self._condition.notify_all()
        if reject:
            _close_source(replacement)
            raise RuntimeError("evidence recorder is closing")

    def reconnect_timed_out(self) -> None:
        """Record a bounded reconnect failure and terminalize ownership."""

        with self._condition:
            if self._closing or self._state != "reconnecting" or self._source is not None:
                return
            handle = self._handle
            segment_id = self._stored_segment_id
        try:
            failed = self._session_store.append_v2_connection_event(
                handle,
                event_type="reconnect_failed",
                segment_id=segment_id,
                detail={"error": "reconnect_timeout"},
            )
            self._session_store.fail_session(
                failed.handle,
                end_reason="reconnect_timeout",
                error_code="reconnect_timeout",
                detail="backend reconnect deadline expired",
            )
        except BaseException as exc:
            self._record_fatal(exc, end_reason="persistence_error")
            return
        with self._condition:
            self._handle = failed.handle
            self._tail = DurableEvidenceTail(
                failed.handle.session_id,
                _next_sequence(failed),
            )
            self._state = "disconnected"
            self._replacement_allowed = False
            self._health = replace(self._health, connected=False)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        """Reject obsolete finite-workflow ownership of the physical reader."""

        raise RuntimeError("bounded Monitor over durable evidence is not implemented yet")

    def close(self) -> None:
        """Stop receive, close the source, and terminalize active ownership."""

        with self._condition:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            if self._closing:
                first_closer = False
                source = None
            else:
                first_closer = True
                self._closing = True
                source = self._source
                self._source_close_complete = source is None
                self._condition.notify_all()
        if not first_closer:
            self._close_complete.wait()
            with self._condition:
                retained_error = self._close_error
            if retained_error is not None:
                raise retained_error
            return

        close_error: BaseException | None = None
        try:
            if source is not None:
                _close_source(source)
        except BaseException as exc:
            close_error = exc
        finally:
            with self._condition:
                self._source_close_complete = True
                self._condition.notify_all()
        try:
            self._thread.join()
        except BaseException as exc:
            if close_error is None:
                close_error = exc
        try:
            self._flush_line_state()
            metadata = self._session_store.load_metadata(self.active_session_id)
            if metadata.get("state") == "active":
                self._session_store.complete_session(
                    self._handle,
                    end_reason="service_shutdown",
                )
        except BaseException as exc:
            if close_error is None:
                close_error = exc
        finally:
            with self._condition:
                self._source = None
                self._state = "closed"
                self._closed = True
                self._health = replace(self._health, connected=False)
                self._close_error = close_error
                self._condition.notify_all()
            self._close_complete.set()
        if close_error is not None:
            raise close_error

    def _ingest(self) -> None:
        while True:
            with self._condition:
                while self._source is None and not self._closing and self._fault is None:
                    self._condition.wait()
                if self._fault is not None or (self._closing and self._source is None):
                    return
                source = self._source
                physical_segment_id = self._source_segment_id
                stored_segment_id = self._stored_segment_id
            if source is None:
                continue
            try:
                event = source.read_event()
            except BackendDisconnectedError as exc:
                if self._finish_shutdown_drain(source):
                    continue
                if self._closing:
                    return
                self._record_disconnect(source, exc)
                continue
            except BackendInputError as exc:
                if self._finish_shutdown_drain(source):
                    continue
                if self._closing:
                    return
                self._record_fatal(exc, end_reason="backend_input_error", source=source)
                return
            except Exception as exc:
                if self._finish_shutdown_drain(source):
                    continue
                if self._closing:
                    return
                self._record_fatal(exc, end_reason="backend_input_error", source=source)
                return
            if event is None:
                with self._condition:
                    if (
                        self._closing
                        and self._source_close_complete
                        and not bool(getattr(source, "has_pending_events", False))
                    ):
                        return
                continue
            if event.segment_id != physical_segment_id:
                self._record_fatal(
                    BackendInputError("backend event source changed its bound segment ID"),
                    end_reason="backend_input_error",
                    source=source,
                )
                return
            normalized = replace(event, segment_id=stored_segment_id)
            try:
                admission = self._record_event(normalized)
            except BaseException as exc:
                self._record_fatal(exc, end_reason="persistence_error", source=source)
                return
            self._publish_admission(admission)

    def _record_event(self, event: BackendEvent) -> V2EvidenceAdmission:
        if isinstance(event, UartReceiveEvent):
            candidate = self._processor.clone()
            result = candidate.process_event(event)
            if self._session_store.v2_uart_receive_will_rollover(
                self._handle,
                event=event,
                capture_result=result,
            ):
                self._flush_line_state()
                event = replace(event, segment_id=self._stored_segment_id)
                candidate = self._processor.clone()
                result = candidate.process_event(event)
            rollover_processor = UartCaptureProcessor()
            rollover_result = rollover_processor.process_event(
                replace(event, segment_id=0)
            )
            admission = self._session_store.append_v2_uart_receive(
                self._handle,
                event=event,
                capture_result=result,
                rollover_capture_result=rollover_result,
            )
            self._processor = rollover_processor if admission.rolled_over else candidate
            if admission.rolled_over:
                with self._condition:
                    self._reset_integrity_after_rollover()
            return admission
        if isinstance(event, BufferOverflowEvent):
            if self._session_store.v2_telemetry_will_rollover(
                self._handle,
                event=event,
            ):
                self._flush_line_state()
                event = replace(event, segment_id=self._stored_segment_id)
            projected_dropped = max(
                self._session_dropped_bytes,
                self._connection_start_dropped_bytes
                + self._explicit_overflow_bytes
                + event.dropped_bytes,
            )
            admission = self._session_store.append_v2_buffer_overflow(
                self._handle,
                event=event,
                session_dropped_bytes=projected_dropped,
                rollover_session_dropped_bytes=event.dropped_bytes,
            )
            if admission.rolled_over:
                self._processor = UartCaptureProcessor()
            with self._condition:
                if admission.rolled_over:
                    self._status_baseline = None
                    self._connection_start_dropped_bytes = 0
                    self._explicit_overflow_bytes = event.dropped_bytes
                    projected_dropped = event.dropped_bytes
                else:
                    self._explicit_overflow_bytes += event.dropped_bytes
                self._session_dropped_bytes = projected_dropped
                self._health = replace(
                    self._health,
                    integrity=UartIntegrity(
                        "loss_reported",
                        "debug_helper_rx_buffer",
                        projected_dropped,
                    ),
                )
            return admission
        if isinstance(event, BufferStatusEvent):
            if self._session_store.v2_telemetry_will_rollover(
                self._handle,
                event=event,
            ):
                self._flush_line_state()
                event = replace(event, segment_id=self._stored_segment_id)
            if self._status_baseline is None:
                self._status_baseline = (
                    event.dropped_bytes_total,
                    event.overflow_events,
                )
            baseline_dropped, baseline_overflows = self._status_baseline
            status_delta = max(0, event.dropped_bytes_total - baseline_dropped)
            connection_dropped = max(status_delta, self._explicit_overflow_bytes)
            projected_dropped = self._connection_start_dropped_bytes + connection_dropped
            prior_loss = (
                self._health.integrity is not None
                and self._health.integrity.loss_status == "loss_reported"
            )
            reported_loss = (
                prior_loss
                or connection_dropped > 0
                or event.overflow_events > baseline_overflows
            )
            admission = self._session_store.append_v2_buffer_status(
                self._handle,
                event=event,
                session_dropped_bytes=projected_dropped,
                reported_loss=reported_loss,
                rollover_session_dropped_bytes=0,
                rollover_reported_loss=False,
            )
            if admission.rolled_over:
                self._processor = UartCaptureProcessor()
            with self._condition:
                if admission.rolled_over:
                    self._status_baseline = (
                        event.dropped_bytes_total,
                        event.overflow_events,
                    )
                    self._connection_start_dropped_bytes = 0
                    self._explicit_overflow_bytes = 0
                    projected_dropped = 0
                    reported_loss = False
                self._session_dropped_bytes = projected_dropped
                self._health = replace(
                    self._health,
                    integrity=UartIntegrity(
                        "loss_reported" if reported_loss else "none_reported",
                        "debug_helper_rx_buffer",
                        projected_dropped,
                    ),
                )
            return admission
        raise TypeError("unsupported backend event")

    def _publish_admission(self, admission: V2EvidenceAdmission) -> None:
        with self._condition:
            self._handle = admission.handle
            if admission.rolled_over:
                self._stored_segment_id = 0
                self._segment = replace(self._segment, segment_id=0)
            self._tail = DurableEvidenceTail(
                admission.handle.session_id,
                _next_sequence(admission),
            )
            self._condition.notify_all()

    def _record_disconnect(
        self,
        source: CaptureEventSource,
        error: BackendDisconnectedError,
    ) -> None:
        with self._condition:
            if self._closing or source is not self._source:
                return
        try:
            self._flush_line_state()
            with self._condition:
                handle = self._handle
                segment_id = self._stored_segment_id
            admission = self._session_store.append_v2_connection_event(
                handle,
                event_type="unexpected_disconnect",
                segment_id=segment_id,
                detail={"error": str(error)},
            )
            self._publish_admission(admission)
            if admission.rolled_over:
                with self._condition:
                    self._reset_integrity_after_rollover()
            reconnect_started = self._session_store.append_v2_connection_event(
                admission.handle,
                event_type="reconnect_started",
                segment_id=self._stored_segment_id,
                detail={"timeout_s": self._profile.reconnect_timeout_s},
            )
        except BaseException as exc:
            self._record_fatal(exc, end_reason="persistence_error", source=source)
            return
        with self._condition:
            if self._closing or source is not self._source:
                return
            self._handle = reconnect_started.handle
            if reconnect_started.rolled_over:
                self._stored_segment_id = 0
                self._segment = replace(self._segment, segment_id=0)
                self._processor = UartCaptureProcessor()
                self._reset_integrity_after_rollover()
            self._tail = DurableEvidenceTail(
                reconnect_started.handle.session_id,
                _next_sequence(reconnect_started),
            )
            self._health = replace(self._health, connected=False)
            self._state = "reconnecting"
            self._replacement_allowed = True
            self._condition.notify_all()
            while source is self._source and not self._closing and self._fault is None:
                self._condition.wait()

    def _flush_line_state(self) -> None:
        results = self._processor.flush_all()
        self._processor = UartCaptureProcessor()
        if not results:
            return
        admissions = self._session_store.append_v2_line_boundary(
            self._handle,
            results=results,
        )
        for admission in admissions:
            self._publish_admission(admission)
            if admission.rolled_over:
                with self._condition:
                    self._reset_integrity_after_rollover()

    def _finish_shutdown_drain(self, source: CaptureEventSource) -> bool:
        with self._condition:
            if not self._closing:
                return False
            self._condition.wait_for(lambda: self._source_close_complete)
        return bool(getattr(source, "has_pending_events", False))

    def _record_fatal(
        self,
        error: BaseException,
        *,
        end_reason: str,
        source: CaptureEventSource | None = None,
    ) -> None:
        with self._condition:
            if self._fault is not None or self._closed:
                return
            current = self._source
            if source is not None and current is not source:
                return
            self._fault = error
            self._state = "faulted"
            self._source = None
            self._health = replace(self._health, connected=False)
            handle = self._handle
            self._condition.notify_all()
        if current is not None:
            with suppress(BaseException):
                _close_source(current)
        if isinstance(error, SessionPersistenceError):
            return
        try:
            metadata = self._session_store.load_metadata(handle.session_id)
            if metadata.get("state") == "active":
                self._session_store.fail_session(
                    handle,
                    end_reason=end_reason,
                    error_code=(
                        "backend_input_error"
                        if end_reason == "backend_input_error"
                        else "persistence_fault"
                    ),
                    detail=str(error),
                )
        except BaseException as terminal_error:
            with self._condition:
                if self._close_error is None:
                    self._close_error = terminal_error

    def _reset_integrity_after_rollover(
        self,
        integrity: UartIntegrity | None = None,
    ) -> None:
        if integrity is None and self._health.backend_snapshot is not None:
            integrity = self._health.backend_snapshot.integrity
        self._session_dropped_bytes = (
            integrity.dropped_bytes
            if integrity is not None and integrity.dropped_bytes is not None
            else 0
        )
        self._connection_start_dropped_bytes = self._session_dropped_bytes
        self._explicit_overflow_bytes = 0
        self._status_baseline = None
        self._health = replace(self._health, integrity=integrity)


def _source_segment(source: CaptureEventSource) -> SegmentContext:
    segment = getattr(source, "segment", None)
    if not isinstance(segment, SegmentContext):
        raise ValueError("evidence recorder source requires timestamp provenance")
    return segment


def _tail_is_after(current: DurableEvidenceTail, previous: DurableEvidenceTail) -> bool:
    return (
        current.session_id != previous.session_id
        or current.next_evidence_seq > previous.next_evidence_seq
    )


def _next_sequence(admission: V2EvidenceAdmission) -> int:
    return admission.next_evidence_seq or admission.evidence_seq + 1


def _close_source(source: CaptureEventSource) -> None:
    close = getattr(source, "close", None)
    if callable(close):
        close()
