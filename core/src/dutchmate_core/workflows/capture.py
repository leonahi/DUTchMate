"""Backend-independent capture workflow coordination."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from dutchmate_core.backends.contracts import (
    BackendEvent,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartReceiveEvent,
)
from dutchmate_core.backends.settings import DEFAULT_RECONNECT_TIMEOUT_S
from dutchmate_core.log_processing.patterns import PatternMatch
from dutchmate_core.session_store.store import (
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionStore,
    SessionSummary,
    SessionWorkflow,
)
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_core.validation import validate_capture_duration


class CaptureEventSource(Protocol):
    """Interim blocking source of normalized backend events."""

    def read_event(self) -> BackendEvent | None:
        """Return the next normalized event, or ``None`` after read inactivity."""


class TransportCaptureRunner:
    """Record parsed transport messages for one finite capture duration."""

    def __init__(
        self,
        *,
        transport: CaptureEventSource,
        duration_s: float,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        validated_duration_s = validate_capture_duration(duration_s)
        self._transport = transport
        self._duration_s = validated_duration_s
        self._clock = monotonic_clock or time.monotonic

    def run(self, recorder: "CaptureRecorder") -> None:
        """Record supported messages until the host-monotonic deadline."""

        deadline = self._clock() + self._duration_s
        while self._clock() < deadline:
            event = self._transport.read_event()

            if self._clock() >= deadline:
                break
            if event is not None:
                segment = getattr(self._transport, "segment", None)
                if isinstance(segment, SegmentContext):
                    recorder.record_segment_context(segment)
                result = recorder.record_event(event)
                if result.event_type == "size_limit":
                    break


@dataclass(frozen=True, slots=True)
class CaptureRecordResult:
    """Result of recording one normalized event into a capture session."""

    session_id: str
    event_type: str
    lines: tuple[UartLine, ...] = ()
    matches: tuple[PatternMatch, ...] = ()


class CaptureRecorder:
    """Route normalized backend events into UART processing and session storage."""

    def __init__(
        self,
        *,
        session_store: SessionStore,
        session_handle: SessionHandle,
        uart_processor: UartCaptureProcessor | None = None,
        segment_context: SegmentContext | None = None,
        timestamp_epoch: int = 0,
    ) -> None:
        self._session_store = session_store
        self._session_handle = session_handle
        self._uart_processor = uart_processor or UartCaptureProcessor()
        self._segment_contexts = (
            {segment_context.segment_id: segment_context} if segment_context is not None else {}
        )
        self._timestamp_epoch = timestamp_epoch
        self._terminalized = False
        self._finalized = False

    @classmethod
    def start(
        cls,
        *,
        session_store: SessionStore,
        command: str,
        firmware: str | None = None,
        device: str | None = None,
        baseline: bool = False,
        uart_processor: UartCaptureProcessor | None = None,
        backend_snapshot: BackendSnapshot | None = None,
        workflow: SessionWorkflow | None = None,
        duration_s: float | None = None,
        reconnect_timeout_s: float | None = None,
    ) -> "CaptureRecorder":
        """Create a capture session and return a recorder for it."""

        session_handle = session_store.create_session(
            command=command,
            firmware=firmware,
            device=device,
            baseline=baseline,
            backend_snapshot=backend_snapshot,
            workflow=workflow,
            duration_s=duration_s,
            reconnect_timeout_s=reconnect_timeout_s,
        )
        return cls(
            session_store=session_store,
            session_handle=session_handle,
            uart_processor=uart_processor,
            segment_context=(backend_snapshot.segment if backend_snapshot is not None else None),
        )

    @property
    def session_handle(self) -> SessionHandle:
        """Handle for the session this recorder writes to."""

        return self._session_handle

    @property
    def session_id(self) -> str:
        """Session identifier this recorder writes to."""

        return self._session_handle.session_id

    @property
    def terminalized(self) -> bool:
        """Whether storage has already ended this recorder's native session."""

        return self._terminalized

    def record_event(self, event: BackendEvent) -> CaptureRecordResult:
        """Record one normalized backend event into the session."""

        if self._terminalized:
            raise ValueError("capture recorder session is already terminal")

        if isinstance(event, UartReceiveEvent):
            candidate_processor = self._uart_processor.clone()
            result = candidate_processor.process_event(event)
            try:
                self._session_store.append_uart_capture(
                    self._session_handle,
                    event=event,
                    result=result,
                    timestamp_epoch=self._timestamp_epoch,
                )
            except EvidenceQuotaExceeded:
                self._terminalized = True
                return CaptureRecordResult(
                    session_id=self.session_id,
                    event_type="size_limit",
                )
            self._uart_processor = candidate_processor
            return CaptureRecordResult(
                session_id=self.session_id,
                event_type="uart_receive",
                lines=result.lines,
                matches=result.matches,
            )

        if isinstance(event, BufferOverflowEvent):
            self._session_store.append_buffer_overflow(
                self._session_handle,
                event=event,
                timestamp_epoch=self._timestamp_epoch,
            )
            return CaptureRecordResult(
                session_id=self.session_id,
                event_type="buffer_overflow",
            )

        if isinstance(event, BufferStatusEvent):
            self._session_store.append_buffer_status(
                self._session_handle,
                event=event,
                timestamp_epoch=self._timestamp_epoch,
            )
            return CaptureRecordResult(
                session_id=self.session_id,
                event_type="buffer_status",
            )

        raise TypeError("capture recorder input must be a normalized backend event")

    def record_segment_context(self, context: SegmentContext) -> None:
        """Persist one immutable segment context before recording its events."""

        existing = self._segment_contexts.get(context.segment_id)
        if existing is not None:
            if existing != context:
                raise ValueError("capture segment timestamp provenance cannot change")
            return
        self._session_store.record_segment_context(self._session_handle, context)
        self._segment_contexts[context.segment_id] = context

    def finalize(self) -> None:
        """Finalize bounded derived state at the end of this capture segment."""

        if self._finalized or self._terminalized:
            return

        for result in self._uart_processor.flush_all():
            self._session_store.append_uart_processing_result(
                self._session_handle,
                result=result,
                timestamp_epoch=self._timestamp_epoch,
            )
        self._finalized = True


def run_transport_capture(
    *,
    transport: CaptureEventSource,
    duration_s: float,
    session_store: SessionStore,
    command: str,
    firmware: str | None = None,
    device: str | None = None,
    baseline: bool = False,
    uart_processor: UartCaptureProcessor | None = None,
    monotonic_clock: Callable[[], float] | None = None,
    reconnect_timeout_s: float = DEFAULT_RECONNECT_TIMEOUT_S,
) -> SessionSummary:
    """Record transport messages until the host-side capture deadline."""

    runner = TransportCaptureRunner(
        transport=transport,
        duration_s=duration_s,
        monotonic_clock=monotonic_clock,
    )
    source_snapshot = getattr(transport, "snapshot", None)
    recorder = CaptureRecorder.start(
        session_store=session_store,
        command=command,
        firmware=firmware,
        device=device,
        baseline=baseline,
        uart_processor=uart_processor,
        backend_snapshot=(
            source_snapshot if isinstance(source_snapshot, BackendSnapshot) else None
        ),
        workflow="capture" if isinstance(source_snapshot, BackendSnapshot) else None,
        duration_s=duration_s if isinstance(source_snapshot, BackendSnapshot) else None,
        reconnect_timeout_s=(
            reconnect_timeout_s if isinstance(source_snapshot, BackendSnapshot) else None
        ),
    )
    native_session = isinstance(source_snapshot, BackendSnapshot)
    try:
        runner.run(recorder)
    except Exception as exc:
        recorder.finalize()
        if native_session:
            session_store.fail_session(
                recorder.session_handle,
                end_reason="backend_error",
                error_code="internal_error",
                detail=str(exc),
            )
        raise
    recorder.finalize()
    if native_session and not recorder.terminalized:
        session_store.complete_session(recorder.session_handle)
    return session_store.summarize_session(recorder.session_id)
