"""Line buffering for decoded DUT UART bytes."""

from dataclasses import dataclass, field


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


class UartLineBuffer:
    """Buffer raw UART bytes until complete newline-terminated lines are available."""

    def __init__(self) -> None:
        self._pending = b""
        self._pending_start_ingestion_index: int | None = None
        self._pending_start_event_offset: int | None = None
        self._pending_end_ingestion_index: int | None = None
        self._pending_end_event_offset: int | None = None
        self._pending_line_index_in_event: int | None = None

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

        if not isinstance(data, bytes):
            raise TypeError("UART line buffer data must be bytes")
        if not data:
            return []

        lines: list[UartLine] = []
        event_offset = 0
        line_index_in_event = 0
        while True:
            newline_offset = data.find(b"\n", event_offset)
            if newline_offset < 0:
                break

            end_event_offset = newline_offset + 1
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

        trailing = data[event_offset:]
        if trailing:
            if not self._pending:
                self._pending_start_ingestion_index = ingestion_index
                self._pending_start_event_offset = event_offset
            self._pending += trailing
            self._pending_end_ingestion_index = ingestion_index
            self._pending_end_event_offset = len(data)
            self._pending_line_index_in_event = line_index_in_event

        return lines

    def flush(self) -> UartLine | None:
        """Return the trailing partial line, if any, and clear the buffer."""

        if not self._pending:
            return None

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
        return line

    def _clear_pending(self) -> None:
        self._pending = b""
        self._pending_start_ingestion_index = None
        self._pending_start_event_offset = None
        self._pending_end_ingestion_index = None
        self._pending_end_event_offset = None
        self._pending_line_index_in_event = None
