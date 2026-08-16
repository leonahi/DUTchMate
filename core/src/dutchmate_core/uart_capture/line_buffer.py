"""Line buffering for decoded DUT UART bytes."""

from dataclasses import dataclass, field

MAX_UART_LINE_BYTES = 65536


@dataclass(frozen=True, slots=True)
class UartLine:
    """One complete UART log line."""

    raw: bytes
    text: str
    ingestion_index: int | None = field(default=None, compare=False)
    line_index_in_event: int | None = field(default=None, compare=False)
    start_ingestion_index: int | None = field(default=None, compare=False)
    start_event_offset: int | None = field(default=None, compare=False)
    end_ingestion_index: int | None = field(default=None, compare=False)
    end_event_offset: int | None = field(default=None, compare=False)


@dataclass(frozen=True, slots=True)
class OversizedUartLine:
    """Bounded descriptor for one physical line that exceeded the derived limit."""

    ingestion_index: int | None
    line_index_in_event: int | None
    start_ingestion_index: int | None
    start_event_offset: int | None
    end_ingestion_index: int | None
    end_event_offset: int | None
    total_bytes: int
    terminated: bool
    timestamp_us: int | None


@dataclass(frozen=True, slots=True)
class UartLineBufferResult:
    """Normal lines and bounded oversized-line facts produced by one input."""

    lines: tuple[UartLine, ...] = ()
    oversized_lines: tuple[OversizedUartLine, ...] = ()
    newly_oversized_line_count: int = 0


class UartLineBuffer:
    """Buffer raw UART bytes until complete newline-terminated lines are available."""

    def __init__(self) -> None:
        self._pending = b""
        self._pending_start_ingestion_index: int | None = None
        self._pending_start_event_offset: int | None = None
        self._pending_end_ingestion_index: int | None = None
        self._pending_end_event_offset: int | None = None
        self._pending_line_index_in_event: int | None = None
        self._oversized_total_bytes: int | None = None
        self._oversized_start_ingestion_index: int | None = None
        self._oversized_start_event_offset: int | None = None
        self._oversized_end_ingestion_index: int | None = None
        self._oversized_end_event_offset: int | None = None
        self._oversized_line_index_in_event: int | None = None
        self._oversized_timestamp_us: int | None = None

    @property
    def pending_bytes(self) -> bytes:
        """Raw UART bytes not yet terminated by a newline."""

        return self._pending

    def feed(
        self,
        data: bytes,
        *,
        ingestion_index: int | None = None,
    ) -> list[UartLine]:
        """Consume UART bytes and return complete lines.

        Returned line `raw` values include the newline delimiter. `text` is a
        lossy UTF-8 display view derived from the raw line bytes.
        """

        return list(self.feed_result(data, ingestion_index=ingestion_index).lines)

    def feed_result(
        self,
        data: bytes,
        *,
        ingestion_index: int | None = None,
        timestamp_us: int | None = None,
    ) -> UartLineBufferResult:
        """Consume bytes and return normal lines plus bounded overflow facts."""

        if not isinstance(data, bytes):
            raise TypeError("UART line buffer data must be bytes")
        if not data:
            return UartLineBufferResult()

        lines: list[UartLine] = []
        oversized_lines: list[OversizedUartLine] = []
        newly_oversized_line_count = 0
        event_offset = 0
        line_index_in_event = 0
        while event_offset < len(data):
            newline_offset = data.find(b"\n", event_offset)
            end_event_offset = newline_offset + 1 if newline_offset >= 0 else len(data)

            if self._oversized_total_bytes is not None:
                self._oversized_total_bytes += end_event_offset - event_offset
                self._oversized_end_ingestion_index = ingestion_index
                self._oversized_end_event_offset = end_event_offset
                self._oversized_line_index_in_event = line_index_in_event
                self._oversized_timestamp_us = timestamp_us
                if newline_offset < 0:
                    break
                oversized_lines.append(self._finish_oversized_line(terminated=True))
                event_offset = end_event_offset
                line_index_in_event += 1
                continue

            incoming_bytes = end_event_offset - event_offset
            total_bytes = len(self._pending) + incoming_bytes
            if total_bytes > MAX_UART_LINE_BYTES:
                if self._pending:
                    start_ingestion_index = self._pending_start_ingestion_index
                    start_event_offset = self._pending_start_event_offset
                else:
                    start_ingestion_index = ingestion_index
                    start_event_offset = event_offset
                self._clear_pending()
                self._oversized_total_bytes = total_bytes
                self._oversized_start_ingestion_index = start_ingestion_index
                self._oversized_start_event_offset = start_event_offset
                self._oversized_end_ingestion_index = ingestion_index
                self._oversized_end_event_offset = end_event_offset
                self._oversized_line_index_in_event = line_index_in_event
                self._oversized_timestamp_us = timestamp_us
                newly_oversized_line_count += 1
                if newline_offset < 0:
                    break
                oversized_lines.append(self._finish_oversized_line(terminated=True))
                event_offset = end_event_offset
                line_index_in_event += 1
                continue

            if newline_offset < 0:
                trailing = data[event_offset:]
                if not self._pending:
                    self._pending_start_ingestion_index = ingestion_index
                    self._pending_start_event_offset = event_offset
                self._pending += trailing
                self._pending_end_ingestion_index = ingestion_index
                self._pending_end_event_offset = len(data)
                self._pending_line_index_in_event = line_index_in_event
                break

            if self._pending:
                raw = self._pending + data[event_offset:end_event_offset]
                start_ingestion_index = self._pending_start_ingestion_index
                start_event_offset = self._pending_start_event_offset
            else:
                raw = data[event_offset:end_event_offset]
                start_ingestion_index = ingestion_index
                start_event_offset = event_offset
            lines.append(
                UartLine(
                    raw=raw,
                    text=raw.decode("utf-8", errors="replace"),
                    ingestion_index=ingestion_index,
                    line_index_in_event=line_index_in_event,
                    start_ingestion_index=start_ingestion_index,
                    start_event_offset=start_event_offset,
                    end_ingestion_index=ingestion_index,
                    end_event_offset=end_event_offset,
                )
            )
            self._clear_pending()
            event_offset = end_event_offset
            line_index_in_event += 1

        return UartLineBufferResult(
            lines=tuple(lines),
            oversized_lines=tuple(oversized_lines),
            newly_oversized_line_count=newly_oversized_line_count,
        )

    def flush(self) -> UartLine | None:
        """Return the trailing partial line, if any, and clear the buffer."""

        result = self.flush_result()
        return result.lines[0] if result.lines else None

    def flush_result(self) -> UartLineBufferResult:
        """Finalize trailing normal or oversized state at segment/session close."""

        if self._oversized_total_bytes is not None:
            return UartLineBufferResult(
                oversized_lines=(self._finish_oversized_line(terminated=False),)
            )

        if not self._pending:
            return UartLineBufferResult()

        raw = self._pending
        line = UartLine(
            raw=raw,
            text=raw.decode("utf-8", errors="replace"),
            ingestion_index=self._pending_end_ingestion_index,
            line_index_in_event=self._pending_line_index_in_event,
            start_ingestion_index=self._pending_start_ingestion_index,
            start_event_offset=self._pending_start_event_offset,
            end_ingestion_index=self._pending_end_ingestion_index,
            end_event_offset=self._pending_end_event_offset,
        )
        self._clear_pending()
        return UartLineBufferResult(lines=(line,))

    def _clear_pending(self) -> None:
        self._pending = b""
        self._pending_start_ingestion_index = None
        self._pending_start_event_offset = None
        self._pending_end_ingestion_index = None
        self._pending_end_event_offset = None
        self._pending_line_index_in_event = None

    def _finish_oversized_line(self, *, terminated: bool) -> OversizedUartLine:
        total_bytes = self._oversized_total_bytes
        if total_bytes is None:
            raise RuntimeError("no oversized UART line is active")
        line = OversizedUartLine(
            ingestion_index=self._oversized_end_ingestion_index,
            line_index_in_event=self._oversized_line_index_in_event,
            start_ingestion_index=self._oversized_start_ingestion_index,
            start_event_offset=self._oversized_start_event_offset,
            end_ingestion_index=self._oversized_end_ingestion_index,
            end_event_offset=self._oversized_end_event_offset,
            total_bytes=total_bytes,
            terminated=terminated,
            timestamp_us=self._oversized_timestamp_us,
        )
        self._oversized_total_bytes = None
        self._oversized_start_ingestion_index = None
        self._oversized_start_event_offset = None
        self._oversized_end_ingestion_index = None
        self._oversized_end_event_offset = None
        self._oversized_line_index_in_event = None
        self._oversized_timestamp_us = None
        return line
