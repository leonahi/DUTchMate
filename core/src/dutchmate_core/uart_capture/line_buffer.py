"""Line buffering for decoded DUT UART bytes."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UartLine:
    """One complete UART log line."""

    raw: bytes
    text: str


class UartLineBuffer:
    """Buffer raw UART bytes until complete newline-terminated lines are available."""

    def __init__(self) -> None:
        self._pending = b""

    @property
    def pending_bytes(self) -> bytes:
        """Raw UART bytes not yet terminated by a newline."""

        return self._pending

    def feed(self, data: bytes) -> list[UartLine]:
        """Consume UART bytes and return complete lines.

        Returned line `raw` values include the newline delimiter. `text` is a
        lossy UTF-8 display view derived from the raw line bytes.
        """

        if not isinstance(data, bytes):
            raise TypeError("UART line buffer data must be bytes")
        if not data:
            return []

        self._pending += data
        parts = self._pending.split(b"\n")
        self._pending = parts.pop()

        lines: list[UartLine] = []
        for part in parts:
            raw = part + b"\n"
            lines.append(UartLine(raw=raw, text=raw.decode("utf-8", errors="replace")))

        return lines

    def flush(self) -> UartLine | None:
        """Return the trailing partial line, if any, and clear the buffer."""

        if not self._pending:
            return None

        raw = self._pending
        self._pending = b""
        return UartLine(raw=raw, text=raw.decode("utf-8", errors="replace"))
