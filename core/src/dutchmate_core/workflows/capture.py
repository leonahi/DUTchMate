"""Backend-independent capture workflow coordination."""

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from dutchmate_core.backends.contracts import (
    BackendEvent,
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.log_processing.patterns import PatternMatch
from dutchmate_core.session_store.store import SessionHandle, SessionStore, SessionSummary
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


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
        _validate_capture_duration(duration_s)
        self._transport = transport
        self._duration_s = duration_s
        self._clock = monotonic_clock or time.monotonic

    def run(self, recorder: "CaptureRecorder") -> None:
        """Record supported messages until the host-monotonic deadline."""

        deadline = self._clock() + self._duration_s
        while self._clock() < deadline:
            event = self._transport.read_event()

            if self._clock() >= deadline:
                break
            if event is not None:
                recorder.record_event(event)


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
        timestamp_epoch: int = 0,
    ) -> None:
        self._session_store = session_store
        self._session_handle = session_handle
        self._uart_processor = uart_processor or UartCaptureProcessor()
        self._timestamp_epoch = timestamp_epoch

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
    ) -> "CaptureRecorder":
        """Create a capture session and return a recorder for it."""

        session_handle = session_store.create_session(
            command=command,
            firmware=firmware,
            device=device,
            baseline=baseline,
        )
        return cls(
            session_store=session_store,
            session_handle=session_handle,
            uart_processor=uart_processor,
        )

    @property
    def session_handle(self) -> SessionHandle:
        """Handle for the session this recorder writes to."""

        return self._session_handle

    @property
    def session_id(self) -> str:
        """Session identifier this recorder writes to."""

        return self._session_handle.session_id

    def record_event(self, event: BackendEvent) -> CaptureRecordResult:
        """Record one normalized backend event into the session."""

        if isinstance(event, UartReceiveEvent):
            result = self._uart_processor.process_event(event)
            self._session_store.append_uart_capture(
                self._session_handle,
                event=event,
                result=result,
                timestamp_epoch=self._timestamp_epoch,
            )
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
) -> SessionSummary:
    """Record transport messages until the host-side capture deadline."""

    runner = TransportCaptureRunner(
        transport=transport,
        duration_s=duration_s,
        monotonic_clock=monotonic_clock,
    )
    recorder = CaptureRecorder.start(
        session_store=session_store,
        command=command,
        firmware=firmware,
        device=device,
        baseline=baseline,
        uart_processor=uart_processor,
    )
    runner.run(recorder)
    return session_store.summarize_session(recorder.session_id)


def _validate_capture_duration(duration_s: float) -> None:
    if (
        isinstance(duration_s, bool)
        or not isinstance(duration_s, int | float)
        or not math.isfinite(duration_s)
        or duration_s <= 0
    ):
        raise ValueError("capture duration must be a positive finite number")
