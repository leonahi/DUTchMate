"""Backend-independent capture workflow coordination."""

import time
from collections.abc import Callable
from dataclasses import dataclass
from functools import partial
from typing import Protocol

from dutchmate_core.backends.contracts import (
    BackendDisconnectedError,
    BackendEvent,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    UartReceiveEvent,
)
from dutchmate_core.backends.settings import DEFAULT_RECONNECT_TIMEOUT_S
from dutchmate_core.log_processing.patterns import PatternMatch
from dutchmate_core.session_store.models import (
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionPersistenceError,
    SessionSummary,
    SessionWorkflow,
)
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult
from dutchmate_core.validation import validate_capture_duration


class CaptureEventSource(Protocol):
    """Interim blocking source of normalized backend events."""

    def read_event(self) -> BackendEvent | None:
        """Return the next normalized event, or ``None`` after read inactivity."""


@dataclass(frozen=True, slots=True)
class ReconnectedCaptureSource:
    """A validated replacement source and its immutable backend snapshot."""

    source: CaptureEventSource
    backend_snapshot: BackendSnapshot


class CaptureReconnect(Protocol):
    """Backend-specific reopen operation used by a capture workflow."""

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        """Return a ready replacement before ``deadline``, or ``None``."""


class CaptureReconnectError(RuntimeError):
    """Raised when an interrupted capture cannot resume within policy."""

    error = "service_unavailable"

    def __init__(self, *, end_reason: str, detail: str) -> None:
        super().__init__(detail)
        self.end_reason = end_reason


class CaptureSessionStorage(Protocol):
    """Persistence operations required by the capture application service."""

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
        """Create one capture session."""

    def append_uart_capture(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        result: UartCaptureResult,
        timestamp_epoch: int = 0,
    ) -> None:
        """Persist one UART evidence unit."""

    def append_uart_processing_result(
        self,
        handle: SessionHandle,
        *,
        result: UartCaptureResult,
        timestamp_epoch: int = 0,
    ) -> None:
        """Persist derived UART records finalized at capture close."""

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Persist one buffer-overflow evidence unit."""

    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
        timestamp_epoch: int = 0,
    ) -> None:
        """Persist one buffer-status evidence unit."""

    def record_segment_context(self, handle: SessionHandle, context: SegmentContext) -> None:
        """Persist immutable timestamp provenance for a capture segment."""

    def record_backend_disconnect(
        self,
        handle: SessionHandle,
        *,
        segment_id: int,
    ) -> int:
        """Close the current segment and return the persisted segment count."""

    def resume_session(
        self,
        handle: SessionHandle,
        *,
        backend_snapshot: BackendSnapshot,
    ) -> int:
        """Append a validated reconnect segment and return its segment ID."""

    def complete_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str = "duration_elapsed",
    ) -> None:
        """Complete an active native session."""

    def fail_session(
        self,
        handle: SessionHandle,
        *,
        end_reason: str,
        error_code: str,
        detail: str,
    ) -> None:
        """Fail an active native session."""

    def summarize_session(self, session_id: str) -> SessionSummary:
        """Return the stored session summary."""


class TransportCaptureRunner:
    """Record parsed transport messages until one fixed workflow deadline."""

    def __init__(
        self,
        *,
        transport: CaptureEventSource,
        deadline: float,
        monotonic_clock: Callable[[], float] | None = None,
    ) -> None:
        self._transport = transport
        self._deadline = deadline
        self._clock = monotonic_clock or time.monotonic

    def run(self, recorder: "CaptureRecorder") -> None:
        """Record supported messages until the host-monotonic deadline."""

        while self._clock() < self._deadline:
            event = self._transport.read_event()

            if self._clock() >= self._deadline:
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
        session_store: CaptureSessionStorage,
        session_handle: SessionHandle,
        uart_processor: UartCaptureProcessor | None = None,
        segment_context: SegmentContext | None = None,
    ) -> None:
        self._session_store = session_store
        self._session_handle = session_handle
        self._uart_processor = uart_processor or UartCaptureProcessor()
        self._segment_contexts = (
            {segment_context.segment_id: segment_context} if segment_context is not None else {}
        )
        self._terminalized = False
        self._finalized = False

    @classmethod
    def start(
        cls,
        *,
        session_store: CaptureSessionStorage,
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
            if not self._record_with_quota(
                lambda: self._session_store.append_uart_capture(
                    self._session_handle,
                    event=event,
                    result=result,
                    timestamp_epoch=event.segment_id,
                )
            ):
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
            if not self._record_with_quota(
                lambda: self._session_store.append_buffer_overflow(
                    self._session_handle,
                    event=event,
                    timestamp_epoch=event.segment_id,
                )
            ):
                return CaptureRecordResult(
                    session_id=self.session_id,
                    event_type="size_limit",
                )
            return CaptureRecordResult(
                session_id=self.session_id,
                event_type="buffer_overflow",
            )

        if isinstance(event, BufferStatusEvent):
            if not self._record_with_quota(
                lambda: self._session_store.append_buffer_status(
                    self._session_handle,
                    event=event,
                    timestamp_epoch=event.segment_id,
                )
            ):
                return CaptureRecordResult(
                    session_id=self.session_id,
                    event_type="size_limit",
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
        """Finalize bounded derived state at the end of this capture."""

        if self._finalized or self._terminalized:
            return

        for result in self._uart_processor.flush_all():
            if not self._record_with_quota(
                partial(
                    self._session_store.append_uart_processing_result,
                    self._session_handle,
                    result=result,
                    timestamp_epoch=result.segment_id,
                )
            ):
                break
        self._finalized = True

    def finalize_segment(self, segment_id: int) -> None:
        """Finalize derived state without joining lines across a disconnect."""

        if self._terminalized or self._finalized:
            return
        for result in self._uart_processor.flush_segment(segment_id):
            if not self._record_with_quota(
                partial(
                    self._session_store.append_uart_processing_result,
                    self._session_handle,
                    result=result,
                    timestamp_epoch=result.segment_id,
                )
            ):
                break

    def record_backend_disconnect(self, segment_id: int) -> int | None:
        """Persist one disconnect, returning the segment count when admitted."""

        segment_count: int | None = None

        def record() -> None:
            nonlocal segment_count
            segment_count = self._session_store.record_backend_disconnect(
                self._session_handle,
                segment_id=segment_id,
            )

        if not self._record_with_quota(record):
            return None
        return segment_count

    def resume_session(self, backend_snapshot: BackendSnapshot) -> int | None:
        """Persist and activate one replacement segment when quota admits it."""

        context = backend_snapshot.segment
        if context is None:
            raise ValueError("reconnected backend snapshot requires segment provenance")
        segment_id: int | None = None

        def resume() -> None:
            nonlocal segment_id
            segment_id = self._session_store.resume_session(
                self._session_handle,
                backend_snapshot=backend_snapshot,
            )

        if not self._record_with_quota(resume):
            return None
        if context.segment_id != segment_id:
            raise ValueError("reconnected backend segment ID does not match persisted segment")
        self._segment_contexts[segment_id] = context
        return segment_id

    def _record_with_quota(self, operation: Callable[[], None]) -> bool:
        try:
            operation()
        except EvidenceQuotaExceeded:
            self._terminalized = True
            return False
        return True


class CaptureWorkflow:
    """Own the complete lifecycle of one finite capture session."""

    def __init__(self, *, session_store: CaptureSessionStorage) -> None:
        self._session_store = session_store

    def run(
        self,
        *,
        source: CaptureEventSource,
        duration_s: float,
        command: str,
        firmware: str | None = None,
        device: str | None = None,
        baseline: bool = False,
        uart_processor: UartCaptureProcessor | None = None,
        monotonic_clock: Callable[[], float] | None = None,
        reconnect_timeout_s: float = DEFAULT_RECONNECT_TIMEOUT_S,
        backend_snapshot: BackendSnapshot | None = None,
        workflow: SessionWorkflow = "capture",
        start_action: Callable[[], object] | None = None,
        on_session_started: Callable[[str], None] | None = None,
        reconnect: CaptureReconnect | None = None,
        on_backend_disconnected: Callable[[], None] | None = None,
    ) -> SessionSummary:
        """Create, record, terminalize, and summarize one capture session."""

        validated_duration_s = validate_capture_duration(duration_s)
        clock = monotonic_clock or time.monotonic
        source_snapshot = getattr(source, "snapshot", None)
        snapshot = (
            backend_snapshot
            if backend_snapshot is not None
            else source_snapshot
            if isinstance(source_snapshot, BackendSnapshot)
            else None
        )
        native_session = snapshot is not None
        recorder = CaptureRecorder.start(
            session_store=self._session_store,
            command=command,
            firmware=firmware,
            device=device,
            baseline=baseline,
            uart_processor=uart_processor,
            backend_snapshot=snapshot,
            workflow=workflow if native_session else None,
            duration_s=validated_duration_s if native_session else None,
            reconnect_timeout_s=reconnect_timeout_s if native_session else None,
        )
        try:
            if on_session_started is not None:
                on_session_started(recorder.session_id)
            if start_action is not None:
                start_action()
            workflow_deadline = clock() + validated_duration_s
            current_source = source
            current_segment_id = self._segment_id(current_source, snapshot)
            while True:
                runner = TransportCaptureRunner(
                    transport=current_source,
                    deadline=workflow_deadline,
                    monotonic_clock=clock,
                )
                try:
                    runner.run(recorder)
                    break
                except BackendDisconnectedError as disconnect_error:
                    if on_backend_disconnected is not None:
                        on_backend_disconnected()
                    if clock() >= workflow_deadline:
                        break
                    if not native_session or reconnect is None:
                        raise
                    reconnect_started_at = clock()
                    reconnect_deadline = reconnect_started_at + reconnect_timeout_s
                    recorder.finalize_segment(current_segment_id)
                    if recorder.terminalized:
                        break
                    segment_count = recorder.record_backend_disconnect(current_segment_id)
                    if segment_count is None:
                        break
                    now = clock()
                    if workflow_deadline <= reconnect_deadline and now >= workflow_deadline:
                        break
                    if segment_count >= 32:
                        raise CaptureReconnectError(
                            end_reason="reconnect_limit",
                            detail="Session reached the 32-segment reconnect limit",
                        ) from disconnect_error
                    if now >= reconnect_deadline:
                        raise self._reconnect_timeout_error() from disconnect_error
                    replacement = reconnect(
                        segment_id=segment_count,
                        deadline=min(workflow_deadline, reconnect_deadline),
                    )
                    now = clock()
                    if workflow_deadline <= reconnect_deadline and now >= workflow_deadline:
                        break
                    if replacement is None or now >= reconnect_deadline:
                        raise self._reconnect_timeout_error() from disconnect_error
                    replacement_segment = getattr(replacement.source, "segment", None)
                    if replacement_segment != replacement.backend_snapshot.segment:
                        raise ValueError(
                            "reconnected source segment must match its backend snapshot"
                        ) from disconnect_error
                    resumed_segment_id = recorder.resume_session(replacement.backend_snapshot)
                    if resumed_segment_id is None:
                        break
                    current_segment_id = resumed_segment_id
                    current_source = replacement.source
            recorder.finalize()
            if native_session and not recorder.terminalized:
                self._session_store.complete_session(recorder.session_handle)
        except Exception as exc:
            failure = exc
            if not isinstance(failure, SessionPersistenceError):
                try:
                    recorder.finalize()
                except SessionPersistenceError as finalize_error:
                    failure = finalize_error
            if recorder.terminalized:
                return self._session_store.summarize_session(recorder.session_id)
            terminalization_safe = (
                not isinstance(
                    failure,
                    SessionPersistenceError,
                )
                or failure.terminalization_safe
            )
            if native_session and terminalization_safe:
                self._session_store.fail_session(
                    recorder.session_handle,
                    end_reason=(
                        "persistence_error"
                        if isinstance(failure, SessionPersistenceError)
                        else getattr(failure, "end_reason", "backend_error")
                    ),
                    error_code=self._failure_code(failure),
                    detail=str(failure),
                )
            if failure is not exc:
                raise failure from exc
            raise
        return self._session_store.summarize_session(recorder.session_id)

    @staticmethod
    def _failure_code(exc: Exception) -> str:
        code = getattr(exc, "error", None)
        return code if isinstance(code, str) and code else "internal_error"

    @staticmethod
    def _segment_id(
        source: CaptureEventSource,
        snapshot: BackendSnapshot | None,
    ) -> int:
        if snapshot is not None and snapshot.segment is not None:
            return snapshot.segment.segment_id
        source_segment = getattr(source, "segment", None)
        return source_segment.segment_id if isinstance(source_segment, SegmentContext) else 0

    @staticmethod
    def _reconnect_timeout_error() -> CaptureReconnectError:
        return CaptureReconnectError(
            end_reason="reconnect_timeout",
            detail="Backend did not reconnect before the reconnect deadline",
        )
