"""Hardware action workflows guarded by GPIO configuration state."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

from dutchmate_core.device_connection.commands import boot_mode_command, reset_command
from dutchmate_core.device_connection.messages import CommandErrorMessage, CommandSuccessMessage
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.gpio_config.modes import GpioModeRegistry

DeviceActionName: TypeAlias = Literal["reset", "set_boot_mode"]


class DeviceCommandTransport(Protocol):
    """Transport capable of sending one host command and returning its response."""

    def request(self, command: bytes) -> DeviceMessage:
        """Send one encoded command and return one parsed device response."""


class DeviceActionError(RuntimeError):
    """Raised when firmware rejects a hardware action command."""

    def __init__(self, *, error: str, detail: str) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail


@dataclass(frozen=True, slots=True)
class DeviceActionResult:
    """Successful hardware action result."""

    action: DeviceActionName
    timestamp_us: int | None = None


class DeviceActionRunner:
    """Run reset/boot commands only when required GPIO roles are configured."""

    def __init__(
        self,
        *,
        registry: GpioModeRegistry,
        transport: DeviceCommandTransport,
    ) -> None:
        self._registry = registry
        self._transport = transport

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the DUT reset role after confirming reset GPIO configuration."""

        command = reset_command(pulse_ms)
        self._registry.require_configured("reset")
        response = self._transport.request(command.to_ndjson())
        return self._require_success(response, action="reset")

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set DUT boot mode after confirming boot GPIO configuration."""

        command = boot_mode_command(mode)
        self._registry.require_configured("boot")
        response = self._transport.request(command.to_ndjson())
        return self._require_success(response, action="set_boot_mode")

    def _require_success(
        self,
        response: DeviceMessage,
        *,
        action: DeviceActionName,
    ) -> DeviceActionResult:
        if isinstance(response, CommandSuccessMessage):
            return DeviceActionResult(action=action, timestamp_us=response.timestamp_us)

        if isinstance(response, CommandErrorMessage):
            raise DeviceActionError(error=response.error, detail=response.detail)

        message_name = type(response).__name__
        raise DeviceActionError(
            error="unexpected_response",
            detail=f"Expected command response for {action}, got {message_name}",
        )
