"""Transport protocols for host-to-device command exchange."""

from __future__ import annotations

from typing import Literal, Protocol, TypeAlias

from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import HostCommandFrameTooLargeError
from dutchmate_core.device_connection.parser import DeviceMessage

TransportWriteErrorCode: TypeAlias = Literal["hardware_fault", "timeout"]


class CommandTransport(Protocol):
    """Transport capable of sending one host command and returning its response."""

    def request(self, command: bytes) -> DeviceMessage:
        """Send one encoded command and return one parsed device response."""


class AsyncCommandTransport(Protocol):
    """Asynchronous one-at-a-time host command exchange."""

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        """Send one complete command and return its parsed response."""


def validate_host_command_frame(command: bytes) -> None:
    """Validate the complete encoded host frame before serial dispatch."""

    if not isinstance(command, bytes):
        raise TypeError("serial commands must be bytes")
    if len(command) > MAX_HOST_FRAME_BYTES:
        raise HostCommandFrameTooLargeError(
            actual_frame_bytes=len(command),
            max_frame_bytes=MAX_HOST_FRAME_BYTES,
        )
    if not command.endswith(b"\n"):
        raise ValueError("serial commands must be newline-terminated NDJSON")


class TransportError(RuntimeError):
    """Raised when host-to-device transport cannot complete an operation."""


class TransportWriteError(TransportError):
    """Raised when a host command frame cannot be written completely."""

    def __init__(
        self,
        detail: str,
        *,
        frame_bytes_accepted: int,
        error: TransportWriteErrorCode,
    ) -> None:
        super().__init__(detail)
        self.frame_bytes_accepted = frame_bytes_accepted
        self.error = error


class TransportTimeoutError(TransportError):
    """Raised when the Debug Helper does not provide a complete message in time."""
