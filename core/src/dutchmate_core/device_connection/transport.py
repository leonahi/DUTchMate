"""Transport protocols for host-to-device command exchange."""

from __future__ import annotations

from typing import Protocol

from dutchmate_core.device_connection.parser import DeviceMessage


class CommandTransport(Protocol):
    """Transport capable of sending one host command and returning its response."""

    def request(self, command: bytes) -> DeviceMessage:
        """Send one encoded command and return one parsed device response."""
