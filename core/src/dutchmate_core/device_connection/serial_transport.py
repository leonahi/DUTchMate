"""Synchronous serial transport for Debug Helper command exchange."""

from __future__ import annotations

import importlib
from collections import deque
from collections.abc import Callable
from threading import RLock
from typing import Protocol, cast

from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import (
    FrameTooLargeError,
    HostCommandFrameTooLargeError,
)
from dutchmate_core.device_connection.messages import CommandErrorMessage, CommandSuccessMessage
from dutchmate_core.device_connection.parser import DeviceMessage, parse_device_message
from dutchmate_core.device_connection.stream import MAX_DEVICE_FRAME_BYTES
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
    TransportWriteErrorCode,
)

DEFAULT_BAUDRATE = 115200
DEFAULT_TIMEOUT_SECONDS = 1.0


class SerialPort(Protocol):
    """Small pyserial-compatible surface used by the command transport."""

    def write(self, data: bytes) -> int:
        """Write bytes to the serial port."""

    def flush(self) -> None:
        """Flush pending output bytes."""

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        """Read bytes until a delimiter or timeout."""

    def close(self) -> None:
        """Close the serial port."""


SerialFactory = Callable[..., SerialPort]


class SerialCommandTransport:
    """Send NDJSON commands and read command responses from a serial port."""

    def __init__(self, serial_port: SerialPort) -> None:
        self._serial_port = serial_port
        self._pending_messages: deque[DeviceMessage] = deque()
        self._io_lock = RLock()

    def request(self, command: bytes) -> DeviceMessage:
        """Send one encoded command and return the matching command response."""

        if not isinstance(command, bytes):
            raise TypeError("serial commands must be bytes")
        if len(command) > MAX_HOST_FRAME_BYTES:
            raise HostCommandFrameTooLargeError(
                actual_frame_bytes=len(command),
                max_frame_bytes=MAX_HOST_FRAME_BYTES,
            )
        if not command.endswith(b"\n"):
            raise ValueError("serial commands must be newline-terminated NDJSON")

        with self._io_lock:
            accepted = 0
            while accepted < len(command):
                remaining = len(command) - accepted
                try:
                    written = self._serial_port.write(command[accepted:])
                except Exception as exc:
                    raise TransportWriteError(
                        "Enhanced serial command write failed",
                        frame_bytes_accepted=accepted,
                        error=_classify_serial_write_error(exc),
                    ) from exc
                if (
                    isinstance(written, bool)
                    or not isinstance(written, int)
                    or written <= 0
                    or written > remaining
                ):
                    raise TransportWriteError(
                        "Enhanced serial command write made invalid progress",
                        frame_bytes_accepted=accepted,
                        error=(
                            "timeout"
                            if written == 0 and not isinstance(written, bool)
                            else "hardware_fault"
                        ),
                    )
                accepted += written
            try:
                self._serial_port.flush()
            except Exception as exc:
                raise TransportWriteError(
                    "Enhanced serial command flush failed",
                    frame_bytes_accepted=accepted,
                    error=_classify_serial_write_error(exc),
                ) from exc

            while True:
                message = self._read_serial_message()
                if isinstance(message, CommandSuccessMessage | CommandErrorMessage):
                    return message
                self._pending_messages.append(message)

    def read_message(self) -> DeviceMessage:
        """Return the oldest queued or newly read Debug Helper message."""

        with self._io_lock:
            if self._pending_messages:
                return self._pending_messages.popleft()
            return self._read_serial_message()

    def drain_pending_messages(self) -> tuple[DeviceMessage, ...]:
        """Return and clear messages queued during command requests."""

        with self._io_lock:
            messages = tuple(self._pending_messages)
            self._pending_messages.clear()
            return messages

    def _read_serial_message(self) -> DeviceMessage:
        line = self._serial_port.read_until(b"\n", size=MAX_DEVICE_FRAME_BYTES)
        if not line:
            raise TransportTimeoutError("Timed out waiting for Debug Helper message")
        if len(line) >= MAX_DEVICE_FRAME_BYTES and not line.endswith(b"\n"):
            raise FrameTooLargeError(
                observed_frame_bytes=len(line),
                max_frame_bytes=MAX_DEVICE_FRAME_BYTES,
            )
        if len(line) > MAX_DEVICE_FRAME_BYTES:
            raise FrameTooLargeError(
                observed_frame_bytes=len(line),
                max_frame_bytes=MAX_DEVICE_FRAME_BYTES,
            )
        if not line.endswith(b"\n"):
            raise TransportTimeoutError("Timed out waiting for complete Debug Helper message")
        return parse_device_message(line)

    def close(self) -> None:
        """Close the underlying serial port."""

        self._serial_port.close()


def open_serial_command_transport(
    *,
    port: str,
    baudrate: int = DEFAULT_BAUDRATE,
    timeout_s: float = DEFAULT_TIMEOUT_SECONDS,
    serial_factory: SerialFactory | None = None,
) -> SerialCommandTransport:
    """Open a pyserial-backed command transport."""

    factory = serial_factory or _pyserial_factory()
    serial_port = factory(port=port, baudrate=baudrate, timeout=timeout_s)
    return SerialCommandTransport(serial_port)


def _pyserial_factory() -> SerialFactory:
    serial_module = importlib.import_module("serial")
    return cast(SerialFactory, serial_module.Serial)


def _classify_serial_write_error(exc: Exception) -> TransportWriteErrorCode:
    if isinstance(exc, TimeoutError) or type(exc).__name__ == "SerialTimeoutException":
        return "timeout"
    return "hardware_fault"
