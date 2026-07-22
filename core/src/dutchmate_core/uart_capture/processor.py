"""UART capture processing from protocol messages to log lines and matches."""

from dataclasses import dataclass

from dutchmate_core.device_connection.messages import UartMessage
from dutchmate_core.log_processing.patterns import PatternDetector, PatternMatch
from dutchmate_core.uart_capture.line_buffer import UartLine, UartLineBuffer


@dataclass(frozen=True, slots=True)
class UartCaptureResult:
    """Completed UART lines and pattern matches produced from one processing step."""

    channel: int
    timestamp_us: int | None
    lines: tuple[UartLine, ...]
    matches: tuple[PatternMatch, ...]


class UartCaptureProcessor:
    """Convert captured UART byte messages into complete lines and pattern matches."""

    def __init__(self, pattern_detector: PatternDetector | None = None) -> None:
        self._pattern_detector = pattern_detector or PatternDetector()
        self._line_buffers: dict[int, UartLineBuffer] = {}

    def process_message(self, message: UartMessage) -> UartCaptureResult:
        """Process one UART protocol message."""

        if not isinstance(message, UartMessage):
            raise TypeError("UART capture processor input must be a UartMessage")

        buffer = self._line_buffer_for_channel(message.channel)
        lines = tuple(buffer.feed(message.data))
        matches = tuple(self._pattern_detector.scan_lines(lines))

        return UartCaptureResult(
            channel=message.channel,
            timestamp_us=message.timestamp_us,
            lines=lines,
            matches=matches,
        )

    def pending_bytes(self, channel: int) -> bytes:
        """Raw bytes buffered for a channel while waiting for a line terminator."""

        buffer = self._line_buffers.get(channel)
        if buffer is None:
            return b""
        return buffer.pending_bytes

    def flush_channel(self, channel: int) -> UartCaptureResult | None:
        """Flush a channel's trailing partial line, if any."""

        buffer = self._line_buffers.get(channel)
        if buffer is None:
            return None

        line = buffer.flush()
        if line is None:
            return None

        lines = (line,)
        matches = tuple(self._pattern_detector.scan_lines(lines))
        return UartCaptureResult(
            channel=channel,
            timestamp_us=None,
            lines=lines,
            matches=matches,
        )

    def _line_buffer_for_channel(self, channel: int) -> UartLineBuffer:
        buffer = self._line_buffers.get(channel)
        if buffer is None:
            buffer = UartLineBuffer()
            self._line_buffers[channel] = buffer
        return buffer
