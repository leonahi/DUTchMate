"""Backend-independent capture workflow coordination."""

import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from functools import partial
from threading import RLock
from types import TracebackType
from typing import Literal, Protocol, runtime_checkable

from dutchmate_core.backends.contracts import (
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
from dutchmate_core.backends.settings import DEFAULT_RECONNECT_TIMEOUT_S
from dutchmate_core.log_processing.patterns import PatternMatch
from dutchmate_core.session_store.models import (
    CommandedBootMode,
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionPersistenceError,
    SessionSummary,
    SessionWorkflow,
)
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult
from dutchmate_core.validation import validate_capture_duration
from dutchmate_core.workflows.device_actions import DeviceActionResult


class CaptureEventSource(Protocol):
    """Interim blocking source of normalized backend events."""

    def read_event(self) -> BackendEvent | None:
        """Return the next normalized event, or ``None`` after read inactivity."""


@dataclass(frozen=True, slots=True)
class CaptureSourceHealth:
    """Immutable current-source connection, integrity, and replacement projection."""

    connected: bool
    integrity: UartIntegrity | None
    backend_snapshot: BackendSnapshot | None = None
    connection_generation: int = 0

    def __post_init__(self) -> None:
        if self.connection_generation < 0:
            raise ValueError("source connection generation must be non-negative")


@runtime_checkable
class CaptureSourceMonitor(Protocol):
    """Optional current-source health observation boundary."""

    def capture_source_health(self) -> CaptureSourceHealth:
        """Return one immutable current-source health snapshot."""


@runtime_checkable
class CaptureWorkflowLifecycle(Protocol):
    """Optional fresh-cursor lifecycle implemented by continuous sources."""

    def begin_workflow(self) -> None:
        """Activate one new finite-workflow cursor."""

    def end_workflow(self) -> None:
        """Release the active cursor and discard its unread events."""


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

    def __init__(
        self,
        *,
        end_reason: str,
        detail: str,
        operation: SessionWorkflow | None = None,
        session_id: str | None = None,
        reconnect_timeout_s: float | None = None,
        segment_count: int | None = None,
        max_segments: int | None = None,
    ) -> None:
        super().__init__(detail)
        self.end_reason = end_reason
        self.operation = operation
        self.session_id = session_id
        self.reconnect_timeout_s = reconnect_timeout_s
        self.segment_count = segment_count
        self.max_segments = max_segments


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
        commanded_boot_mode: CommandedBootMode | None = None,
        wait_pattern: str | None = None,
        timeout_s: float | None = None,
    ) -> SessionHandle:
        """Create one capture session."""

    def append_uart_capture(
        self,
        handle: SessionHandle,
        *,
        event: UartReceiveEvent,
        result: UartCaptureResult,
    ) -> tuple[int, ...]:
        """Persist one UART evidence unit."""

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
        """Persist one accepted normalized control action."""

    def append_uart_processing_result(
        self,
        handle: SessionHandle,
        *,
        result: UartCaptureResult,
    ) -> None:
        """Persist derived UART records finalized at capture close."""

    def append_buffer_overflow(
        self,
        handle: SessionHandle,
        *,
        event: BufferOverflowEvent,
    ) -> None:
        """Persist one buffer-overflow evidence unit."""

    def append_buffer_status(
        self,
        handle: SessionHandle,
        *,
        event: BufferStatusEvent,
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

    def complete_wait_pattern(
        self,
        handle: SessionHandle,
        *,
        matched: bool,
        detected_pattern_index: int | None,
    ) -> None:
        """Complete an active wait-pattern session."""

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


class SessionMutationLock(Protocol):
    """Shared guard that serializes active-session evidence mutations."""

    def __enter__(self) -> object:
        """Acquire the mutation guard."""

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Release the mutation guard."""


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

    def run(
        self,
        recorder: "CaptureRecorder",
        *,
        requested_pattern: str | None = None,
        stop_requested: Callable[[], bool] | None = None,
    ) -> "CaptureRecordResult | None":
        """Record supported messages until the host-monotonic deadline."""

        while self._clock() < self._deadline and not (
            stop_requested is not None and stop_requested()
        ):
            event = self._transport.read_event()

            if self._clock() >= self._deadline or (
                stop_requested is not None and stop_requested()
            ):
                break
            if event is not None:
                segment = getattr(self._transport, "segment", None)
                if isinstance(segment, SegmentContext):
                    recorder.record_segment_context(segment)
                result = recorder.record_event(event)
                if result.event_type == "size_limit":
                    return None
                if requested_pattern is not None and any(
                    match.pattern == requested_pattern for match in result.matches
                ):
                    return result
        return None


@dataclass(frozen=True, slots=True)
class CaptureRecordResult:
    """Result of recording one normalized event into a capture session."""

    session_id: str
    event_type: str
    lines: tuple[UartLine, ...] = ()
    matches: tuple[PatternMatch, ...] = ()
    detected_pattern_indexes: tuple[int, ...] = ()


class CaptureRecorder:
    """Route normalized backend events into UART processing and session storage."""

    def __init__(
        self,
        *,
        session_store: CaptureSessionStorage,
        session_handle: SessionHandle,
        uart_processor: UartCaptureProcessor | None = None,
        segment_context: SegmentContext | None = None,
        mutation_lock: SessionMutationLock | None = None,
    ) -> None:
        self._session_store = session_store
        self._session_handle = session_handle
        self._uart_processor = uart_processor or UartCaptureProcessor()
        self._segment_contexts = (
            {segment_context.segment_id: segment_context} if segment_context is not None else {}
        )
        self._terminalized = False
        self._finalized = False
        self._mutation_lock = mutation_lock or RLock()

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
        commanded_boot_mode: CommandedBootMode | None = None,
        wait_pattern: str | None = None,
        timeout_s: float | None = None,
        mutation_lock: SessionMutationLock | None = None,
    ) -> "CaptureRecorder":
        """Create a capture session and return a recorder for it."""

        shared_lock = mutation_lock or RLock()
        with shared_lock:
            session_handle = session_store.create_session(
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
        return cls(
            session_store=session_store,
            session_handle=session_handle,
            uart_processor=uart_processor,
            segment_context=(backend_snapshot.segment if backend_snapshot is not None else None),
            mutation_lock=shared_lock,
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

    def mark_terminalized(self) -> None:
        """Observe terminalization performed by a coordinated external evidence writer."""

        self._terminalized = True

    def record_event(self, event: BackendEvent) -> CaptureRecordResult:
        """Record one normalized backend event into the session."""

        if self._terminalized:
            raise ValueError("capture recorder session is already terminal")

        if isinstance(event, UartReceiveEvent):
            candidate_processor = self._uart_processor.clone()
            result = candidate_processor.process_event(event)
            detected_pattern_indexes: tuple[int, ...] = ()

            def record_uart() -> None:
                nonlocal detected_pattern_indexes
                detected_pattern_indexes = self._session_store.append_uart_capture(
                    self._session_handle,
                    event=event,
                    result=result,
                )

            if not self._record_with_quota(record_uart):
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
                detected_pattern_indexes=detected_pattern_indexes,
            )

        if isinstance(event, BufferOverflowEvent):
            if not self._record_with_quota(
                lambda: self._session_store.append_buffer_overflow(
                    self._session_handle,
                    event=event,
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
        with self._mutation_lock:
            self._session_store.record_segment_context(self._session_handle, context)
        self._segment_contexts[context.segment_id] = context

    def record_control_action(self, result: DeviceActionResult) -> bool:
        """Persist one successful boot-test reset within its active segment."""

        pulse_ms = result.pulse_ms
        if result.action != "reset" or pulse_ms is None:
            raise ValueError("capture control evidence requires an accepted reset result")
        context = self._segment_contexts.get(0)
        if context is None:
            raise ValueError("capture control evidence requires initial segment provenance")
        timestamp_us = _normalized_control_timestamp(
            context,
            device_timestamp_us=result.device_timestamp_us,
        )
        return self._record_with_quota(
            lambda: self._session_store.append_control_action(
                self._session_handle,
                action="reset",
                segment_id=context.segment_id,
                performed_at=result.performed_at,
                pulse_ms=pulse_ms,
                timestamp_us=timestamp_us,
                device_timestamp_us=result.device_timestamp_us,
            )
        )

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
            with self._mutation_lock:
                operation()
        except EvidenceQuotaExceeded:
            self._terminalized = True
            return False
        return True


class CaptureWorkflow:
    """Own the complete lifecycle of one finite capture session."""

    def __init__(
        self,
        *,
        session_store: CaptureSessionStorage,
        mutation_lock: SessionMutationLock | None = None,
    ) -> None:
        self._session_store = session_store
        self.mutation_lock = mutation_lock or RLock()

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
        commanded_boot_mode: CommandedBootMode | None = None,
        start_action: Callable[[], DeviceActionResult] | None = None,
        on_session_started: Callable[[str], None] | None = None,
        on_session_handle_started: Callable[[SessionHandle], None] | None = None,
        reconnect: CaptureReconnect | None = None,
        on_backend_disconnected: Callable[[], None] | None = None,
        requested_pattern: str | None = None,
        discard_preexisting: bool = False,
        is_session_terminalized: Callable[[], bool] | None = None,
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
        if (workflow == "wait_pattern") != (requested_pattern is not None):
            raise ValueError("wait-pattern workflow requires exactly one requested pattern")
        if discard_preexisting:
            discard = getattr(source, "discard_pending_events", None)
            if callable(discard):
                discard()
        recorder = CaptureRecorder.start(
            session_store=self._session_store,
            command=command,
            firmware=firmware,
            device=device,
            baseline=baseline,
            uart_processor=uart_processor,
            backend_snapshot=snapshot,
            workflow=workflow if native_session else None,
            duration_s=(
                validated_duration_s
                if native_session and workflow in {"capture", "boot_test"}
                else None
            ),
            reconnect_timeout_s=reconnect_timeout_s if native_session else None,
            commanded_boot_mode=commanded_boot_mode if native_session else None,
            wait_pattern=requested_pattern if native_session else None,
            timeout_s=(
                validated_duration_s
                if native_session and workflow == "wait_pattern"
                else None
            ),
            mutation_lock=self.mutation_lock,
        )
        lifecycle = source if isinstance(source, CaptureWorkflowLifecycle) else None
        workflow_cursor_active = False
        matched_pattern_index: int | None = None
        try:
            if lifecycle is not None:
                lifecycle.begin_workflow()
                workflow_cursor_active = True
            if on_session_started is not None:
                on_session_started(recorder.session_id)
            if on_session_handle_started is not None:
                on_session_handle_started(recorder.session_handle)
            if start_action is not None and not recorder.record_control_action(start_action()):
                with self.mutation_lock:
                    return self._session_store.summarize_session(recorder.session_id)
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
                    record_result = runner.run(
                        recorder,
                        requested_pattern=requested_pattern,
                        stop_requested=is_session_terminalized,
                    )
                    if is_session_terminalized is not None and is_session_terminalized():
                        recorder.mark_terminalized()
                    if record_result is not None and requested_pattern is not None:
                        matched_pattern_index = self._requested_pattern_index(
                            record_result,
                            requested_pattern,
                        )
                    break
                except BackendInputError:
                    self._close_source(current_source)
                    raise
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
                            operation=workflow,
                            session_id=recorder.session_id,
                            segment_count=32,
                            max_segments=32,
                        ) from disconnect_error
                    if now >= reconnect_deadline:
                        raise self._reconnect_timeout_error(
                            operation=workflow,
                            session_id=recorder.session_id,
                            reconnect_timeout_s=reconnect_timeout_s,
                        ) from disconnect_error
                    replacement = reconnect(
                        segment_id=segment_count,
                        deadline=min(workflow_deadline, reconnect_deadline),
                    )
                    now = clock()
                    if workflow_deadline <= reconnect_deadline and now >= workflow_deadline:
                        break
                    if replacement is None or now >= reconnect_deadline:
                        raise self._reconnect_timeout_error(
                            operation=workflow,
                            session_id=recorder.session_id,
                            reconnect_timeout_s=reconnect_timeout_s,
                        ) from disconnect_error
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
                if workflow == "wait_pattern":
                    with self.mutation_lock:
                        self._session_store.complete_wait_pattern(
                            recorder.session_handle,
                            matched=matched_pattern_index is not None,
                            detected_pattern_index=matched_pattern_index,
                        )
                else:
                    with self.mutation_lock:
                        self._session_store.complete_session(recorder.session_handle)
        except Exception as exc:
            failure = (
                exc.with_context(
                    operation=workflow,
                    backend_mode=snapshot.info.mode,
                )
                if isinstance(exc, BackendInputError) and snapshot is not None
                else exc
            )
            if not isinstance(failure, SessionPersistenceError):
                try:
                    recorder.finalize()
                except SessionPersistenceError as finalize_error:
                    failure = finalize_error
            if recorder.terminalized:
                with self.mutation_lock:
                    return self._session_store.summarize_session(recorder.session_id)
            terminalization_safe = (
                not isinstance(
                    failure,
                    SessionPersistenceError,
                )
                or failure.terminalization_safe
            )
            if native_session and terminalization_safe:
                with self.mutation_lock:
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
        finally:
            if workflow_cursor_active:
                assert lifecycle is not None
                lifecycle.end_workflow()
        with self.mutation_lock:
            return self._session_store.summarize_session(recorder.session_id)

    @staticmethod
    def _requested_pattern_index(
        result: CaptureRecordResult,
        requested_pattern: str,
    ) -> int:
        if len(result.matches) != len(result.detected_pattern_indexes):
            raise ValueError("persisted detected-pattern indexes do not match scan results")
        for match, detected_index in zip(
            result.matches,
            result.detected_pattern_indexes,
            strict=True,
        ):
            if match.pattern == requested_pattern:
                return detected_index
        raise ValueError("requested pattern match has no persisted detected record")

    @staticmethod
    def _failure_code(exc: Exception) -> str:
        code = getattr(exc, "error", None)
        return code if isinstance(code, str) and code else "internal_error"

    @staticmethod
    def _close_source(source: CaptureEventSource) -> None:
        close = getattr(source, "close", None)
        if callable(close):
            with suppress(Exception):
                close()

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
    def _reconnect_timeout_error(
        *,
        operation: SessionWorkflow,
        session_id: str,
        reconnect_timeout_s: float,
    ) -> CaptureReconnectError:
        return CaptureReconnectError(
            end_reason="reconnect_timeout",
            detail="Backend did not reconnect before the reconnect deadline",
            operation=operation,
            session_id=session_id,
            reconnect_timeout_s=reconnect_timeout_s,
        )


def _normalized_control_timestamp(
    context: SegmentContext,
    *,
    device_timestamp_us: int | None,
) -> int | None:
    if context.timestamp.source == "host":
        if device_timestamp_us is not None:
            raise BackendInputError(
                "Host-timestamped control action returned a device timestamp"
            )
        return None
    if device_timestamp_us is None:
        return None
    if device_timestamp_us < context.timestamp.source_origin_us:
        raise BackendInputError(
            "Control-action device timestamp precedes the active segment origin"
        )
    return device_timestamp_us - context.timestamp.source_origin_us
