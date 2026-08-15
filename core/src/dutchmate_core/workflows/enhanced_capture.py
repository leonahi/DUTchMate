"""Enhanced NDJSON compatibility helpers built on the shared capture recorder."""

from collections.abc import Iterable

from dutchmate_core.backends.enhanced import EnhancedNdjsonEventStream
from dutchmate_core.session_store.store import SessionHandle, SessionStore, SessionSummary
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_core.workflows.capture import CaptureRecorder, CaptureRecordResult


class CaptureStreamRecorder:
    """Adapt Enhanced NDJSON fixture chunks before shared event recording."""

    def __init__(
        self,
        *,
        recorder: CaptureRecorder,
        event_stream: EnhancedNdjsonEventStream | None = None,
    ) -> None:
        self._recorder = recorder
        self._event_stream = event_stream or EnhancedNdjsonEventStream()

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
        """Create a capture session and an Enhanced byte-stream recorder."""

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
        """Return the shared normalized-event recorder."""

        return self._recorder

    @property
    def session_handle(self) -> SessionHandle:
        """Return the session handle receiving normalized evidence."""

        return self._recorder.session_handle

    @property
    def session_id(self) -> str:
        """Return the session identifier receiving normalized evidence."""

        return self._recorder.session_id

    @property
    def pending_bytes(self) -> bytes:
        """Return Enhanced NDJSON bytes awaiting a line terminator."""

        return self._event_stream.pending_bytes

    def feed(self, chunk: bytes) -> list[CaptureRecordResult]:
        """Normalize and record supported complete Enhanced messages."""

        return [
            self._recorder.record_event(event)
            for event in self._event_stream.feed(chunk)
        ]


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
    """Record a finite mocked Enhanced NDJSON stream and return its summary."""

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
