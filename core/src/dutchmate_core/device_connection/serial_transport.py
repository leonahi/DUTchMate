"""Exact serial-frame writes shared by Enhanced transport adapters."""

from __future__ import annotations

from typing import Protocol

from dutchmate_core.device_connection.transport import (
    TransportWriteError,
    TransportWriteErrorCode,
    validate_host_command_frame,
)

DEFAULT_BAUDRATE = 115200


class SerialFrameSink(Protocol):
    """Pyserial-compatible surface for exact host frame writes."""

    def write(self, data: bytes) -> int:
        """Return the number of bytes accepted from data."""

    def flush(self) -> None:
        """Wait until accepted output is flushed."""


def write_serial_frame(serial_port: SerialFrameSink, frame: bytes) -> None:
    """Write and flush one complete frame with exact accepted-byte errors."""

    validate_host_command_frame(frame)
    accepted = 0
    while accepted < len(frame):
        remaining = len(frame) - accepted
        try:
            written = serial_port.write(frame[accepted:])
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
        serial_port.flush()
    except Exception as exc:
        raise TransportWriteError(
            "Enhanced serial command flush failed",
            frame_bytes_accepted=accepted,
            error=_classify_serial_write_error(exc),
        ) from exc


def _classify_serial_write_error(exc: Exception) -> TransportWriteErrorCode:
    if isinstance(exc, TimeoutError) or type(exc).__name__ == "SerialTimeoutException":
        return "timeout"
    return "hardware_fault"
