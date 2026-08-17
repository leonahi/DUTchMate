"""Backend-independent UART receive processing to log lines and matches."""

import copy
from dataclasses import dataclass

from dutchmate_core.backends.contracts import UartReceiveEvent
from dutchmate_core.log_processing.patterns import PatternDetector, PatternMatch
from dutchmate_core.uart_capture.line_buffer import (
    OversizedUartLine,
    UartLine,
    UartLineBuffer,
)


@dataclass(frozen=True, slots=True)
class UartCaptureResult:
    """Completed UART lines and pattern matches produced from one processing step."""

    segment_id: int
    channel: int
    timestamp_us: int | None
    lines: tuple[UartLine, ...]
    matches: tuple[PatternMatch, ...]
    oversized_lines: tuple[OversizedUartLine, ...] = ()
    newly_oversized_line_count: int = 0


class UartCaptureProcessor:
    """Convert captured UART byte messages into complete lines and pattern matches."""

    def __init__(self, pattern_detector: PatternDetector | None = None) -> None:
        self._pattern_detector = pattern_detector or PatternDetector()
        self._line_buffers: dict[tuple[int, int], UartLineBuffer] = {}
        self._next_ingestion_index = 0

    def process_event(self, event: UartReceiveEvent) -> UartCaptureResult:
        """Process one normalized UART receive event."""

        if not isinstance(event, UartReceiveEvent):
            raise TypeError("UART capture processor input must be a UartReceiveEvent")

        ingestion_index = self._next_ingestion_index
        self._next_ingestion_index += 1
        buffer = self._line_buffer_for_channel(event.segment_id, event.channel)
        buffered = buffer.feed_result(
            event.data,
            ingestion_index=ingestion_index,
            timestamp_us=event.timestamp_us,
        )
        lines = buffered.lines
        matches = tuple(self._pattern_detector.scan_lines(lines))

        return UartCaptureResult(
            segment_id=event.segment_id,
            channel=event.channel,
            timestamp_us=event.timestamp_us,
            lines=lines,
            matches=matches,
            oversized_lines=buffered.oversized_lines,
            newly_oversized_line_count=buffered.newly_oversized_line_count,
        )

    def clone(self) -> "UartCaptureProcessor":
        """Return an independent candidate state for atomic evidence admission."""

        return copy.deepcopy(self)

    def pending_bytes(self, channel: int, *, segment_id: int = 0) -> bytes:
        """Return bytes awaiting a line terminator for one segment and channel."""

        buffer = self._line_buffers.get((segment_id, channel))
        if buffer is None:
            return b""
        return buffer.pending_bytes

    def flush_channel(self, channel: int, *, segment_id: int = 0) -> UartCaptureResult | None:
        """Flush one segment/channel's trailing partial line, if any."""

        buffer = self._line_buffers.get((segment_id, channel))
        if buffer is None:
            return None

        buffered = buffer.flush_result()
        if not buffered.lines and not buffered.oversized_lines:
            return None

        lines = buffered.lines
        matches = tuple(self._pattern_detector.scan_lines(lines))
        return UartCaptureResult(
            segment_id=segment_id,
            channel=channel,
            timestamp_us=None,
            lines=lines,
            matches=matches,
            oversized_lines=buffered.oversized_lines,
        )

    def flush_all(self) -> tuple[UartCaptureResult, ...]:
        """Finalize trailing derived state for every segment/channel."""

        results: list[UartCaptureResult] = []
        for segment_id in dict.fromkeys(key[0] for key in self._line_buffers):
            results.extend(self.flush_segment(segment_id))
        return tuple(results)

    def flush_segment(self, segment_id: int) -> tuple[UartCaptureResult, ...]:
        """Finalize and discard trailing derived state for one connection segment."""

        results: list[UartCaptureResult] = []
        channels = tuple(
            channel
            for buffered_segment_id, channel in self._line_buffers
            if buffered_segment_id == segment_id
        )
        for channel in channels:
            result = self.flush_channel(channel, segment_id=segment_id)
            if result is not None:
                results.append(result)
            self._line_buffers.pop((segment_id, channel), None)
        return tuple(results)

    def _line_buffer_for_channel(self, segment_id: int, channel: int) -> UartLineBuffer:
        key = (segment_id, channel)
        buffer = self._line_buffers.get(key)
        if buffer is None:
            buffer = UartLineBuffer()
            self._line_buffers[key] = buffer
        return buffer
