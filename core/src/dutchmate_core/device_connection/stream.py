"""NDJSON stream parsing for serial byte chunks."""

from dutchmate_core.device_connection.parser import DeviceMessage, parse_device_message


class NdjsonStreamParser:
    """Buffer serial chunks and parse complete newline-terminated messages."""

    def __init__(self) -> None:
        self._buffer = b""

    @property
    def pending_bytes(self) -> bytes:
        """Bytes buffered because they do not yet end in a newline."""

        return self._buffer

    def feed(self, chunk: bytes) -> list[DeviceMessage]:
        """Consume a serial byte chunk and return parsed complete messages."""

        if not isinstance(chunk, bytes):
            raise TypeError("NDJSON stream chunks must be bytes")
        if not chunk:
            return []

        self._buffer += chunk
        lines = self._buffer.split(b"\n")
        self._buffer = lines.pop()

        messages: list[DeviceMessage] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            messages.append(parse_device_message(line))

        return messages
