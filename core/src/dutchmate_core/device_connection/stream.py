"""NDJSON stream parsing for serial byte chunks."""

from dutchmate_core.device_connection.errors import (
    FrameTooLargeError,
    ProtocolError,
    ProtocolValidationError,
)
from dutchmate_core.device_connection.parser import DeviceMessage, parse_device_message

MAX_DEVICE_FRAME_BYTES = 65536
MAX_PENDING_DEVICE_FRAME_BYTES = MAX_DEVICE_FRAME_BYTES - 1


class NdjsonStreamParser:
    """Buffer serial chunks and parse complete newline-terminated messages."""

    def __init__(self) -> None:
        self._buffer = b""
        self._terminal_error: ProtocolError | None = None

    @property
    def pending_bytes(self) -> bytes:
        """Bytes buffered because they do not yet end in a newline."""

        return self._buffer

    def feed(self, chunk: bytes) -> list[DeviceMessage]:
        """Consume a serial byte chunk and return parsed complete messages."""

        if self._terminal_error is not None:
            raise self._terminal_error
        if not isinstance(chunk, bytes):
            raise TypeError("NDJSON stream chunks must be bytes")
        if not chunk:
            return []

        self._buffer += chunk
        lines = self._buffer.split(b"\n")
        self._buffer = lines.pop()

        messages: list[DeviceMessage] = []
        for line in lines:
            try:
                observed_frame_bytes = len(line) + 1
                if observed_frame_bytes > MAX_DEVICE_FRAME_BYTES:
                    raise FrameTooLargeError(
                        observed_frame_bytes=observed_frame_bytes,
                        max_frame_bytes=MAX_DEVICE_FRAME_BYTES,
                    )
                messages.append(parse_device_message(_frame_body(line)))
            except ProtocolError as exc:
                self._buffer = b""
                self._terminal_error = exc
                if messages:
                    return messages
                raise

        if len(self._buffer) > MAX_PENDING_DEVICE_FRAME_BYTES:
            observed_frame_bytes = len(self._buffer)
            self._buffer = b""
            error = FrameTooLargeError(
                observed_frame_bytes=observed_frame_bytes,
                max_frame_bytes=MAX_DEVICE_FRAME_BYTES,
            )
            self._terminal_error = error
            if messages:
                return messages
            raise error

        return messages


def _frame_body(line: bytes) -> bytes:
    """Return one exact JSON object body after removing one optional CR."""

    if line.endswith(b"\r"):
        line = line[:-1]
    if (
        not line
        or b"\r" in line
        or not line.startswith(b"{")
        or not line.endswith(b"}")
    ):
        raise ProtocolValidationError(
            "Enhanced protocol frame must contain exactly one JSON object"
        )
    return line
