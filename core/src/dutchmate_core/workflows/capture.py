"""Capture workflow coordination for parsed device messages."""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TypeAlias, TypeGuard, cast

from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.log_processing.patterns import PatternMatch
from dutchmate_core.session_store.store import SessionHandle, SessionStore, SessionSummary
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor

CaptureMessage: TypeAlias = UartMessage | BufferOverflowMessage | BufferStatusMessage


@dataclass(frozen=True, slots=True)
class CaptureRecordResult:
    """Result of recording one parsed device message into a capture session."""

    session_id: str
    message_type: str
    lines: tuple[UartLine, ...] = ()
    matches: tuple[PatternMatch, ...] = ()


class CaptureRecorder:
    """Route parsed capture messages into UART processing and session storage."""

    def __init__(
        self,
        *,
        session_store: SessionStore,
        session_handle: SessionHandle,
        uart_processor: UartCaptureProcessor | None = None,
        segment_id: int = 0,
        timestamp_epoch: int = 0,
    ) -> None:
        self._session_store = session_store
        self._session_handle = session_handle
        self._uart_processor = uart_processor or UartCaptureProcessor()
        self._segment_id = segment_id
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

    def record_message(self, message: CaptureMessage) -> CaptureRecordResult:
        """Record one parsed device message into the session."""

        if isinstance(message, UartMessage):
            result = self._uart_processor.process_message(message)
            self._session_store.append_uart_capture(
                self._session_handle,
                message=message,
                result=result,
                segment_id=self._segment_id,
                timestamp_epoch=self._timestamp_epoch,
            )
            return CaptureRecordResult(
                session_id=self.session_id,
                message_type="uart",
                lines=result.lines,
                matches=result.matches,
            )

        if isinstance(message, BufferOverflowMessage):
            self._session_store.append_buffer_overflow(
                self._session_handle,
                message=message,
                segment_id=self._segment_id,
                timestamp_epoch=self._timestamp_epoch,
            )
            return CaptureRecordResult(
                session_id=self.session_id,
                message_type="buffer_overflow",
            )

        if isinstance(message, BufferStatusMessage):
            self._session_store.append_buffer_status(
                self._session_handle,
                message=message,
                segment_id=self._segment_id,
                timestamp_epoch=self._timestamp_epoch,
            )
            return CaptureRecordResult(
                session_id=self.session_id,
                message_type="buffer_status",
            )

        raise TypeError("capture recorder input must be a supported capture message")


class CaptureStreamRecorder:
    """Parse NDJSON byte chunks and record supported capture messages."""

    def __init__(
        self,
        *,
        recorder: CaptureRecorder,
        stream_parser: NdjsonStreamParser | None = None,
    ) -> None:
        self._recorder = recorder
        self._stream_parser = stream_parser or NdjsonStreamParser()

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
    ) -> "CaptureStreamRecorder":
        """Create a capture session and return a byte-stream recorder for it."""

        return cls(
            recorder=CaptureRecorder.start(
                session_store=session_store,
                command=command,
                firmware=firmware,
                device=device,
                baseline=baseline,
                uart_processor=uart_processor,
            )
        )

    @property
    def recorder(self) -> CaptureRecorder:
        """Typed-message recorder used by this stream recorder."""

        return self._recorder

    @property
    def session_handle(self) -> SessionHandle:
        """Handle for the session this recorder writes to."""

        return self._recorder.session_handle

    @property
    def session_id(self) -> str:
        """Session identifier this recorder writes to."""

        return self._recorder.session_id

    @property
    def pending_bytes(self) -> bytes:
        """NDJSON bytes buffered while waiting for a line terminator."""

        return cast(bytes, self._stream_parser.pending_bytes)

    def feed(self, chunk: bytes) -> list[CaptureRecordResult]:
        """Consume serial bytes and record supported complete capture messages."""

        results: list[CaptureRecordResult] = []
        for message in self._stream_parser.feed(chunk):
            if _is_capture_message(message):
                results.append(self._recorder.record_message(message))
        return results


def _is_capture_message(message: DeviceMessage) -> TypeGuard[CaptureMessage]:
    return isinstance(message, UartMessage | BufferOverflowMessage | BufferStatusMessage)


def run_mock_capture(
    *,
    chunks: Iterable[bytes],
    session_store: SessionStore,
    command: str,
    firmware: str | None = None,
    device: str | None = None,
    baseline: bool = False,
    uart_processor: UartCaptureProcessor | None = None,
) -> SessionSummary:
    """Record a finite mocked NDJSON capture stream and return its summary."""

    recorder = CaptureStreamRecorder.start(
        session_store=session_store,
        command=command,
        firmware=firmware,
        device=device,
        baseline=baseline,
        uart_processor=uart_processor,
    )
    for chunk in chunks:
        recorder.feed(chunk)

    return session_store.summarize_session(recorder.session_id)
