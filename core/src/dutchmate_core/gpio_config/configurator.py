"""GPIO mode configuration workflow."""

from __future__ import annotations

from typing import TypeAlias

from dutchmate_core.device_connection.commands import configure_gpio_mode_command
from dutchmate_core.device_connection.messages import CommandErrorMessage, CommandSuccessMessage
from dutchmate_core.device_connection.transport import CommandTransport
from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioModeRegistry,
    GpioModeRequestSource,
    GpioRoleState,
)

GpioCommandTransport: TypeAlias = CommandTransport


class GpioConfigurator:
    """Configure GPIO modes through firmware and update accepted host state."""

    def __init__(
        self,
        *,
        registry: GpioModeRegistry,
        transport: GpioCommandTransport,
    ) -> None:
        self._registry = registry
        self._transport = transport

    def configure_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        source: GpioModeRequestSource,
        idle_level: str | None = None,
    ) -> GpioRoleState:
        """Send `configure_gpio_mode` and record the firmware result."""

        command = configure_gpio_mode_command(
            channel=channel,
            role=role,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        response = self._transport.request(command.to_ndjson())

        if isinstance(response, CommandSuccessMessage):
            return self._registry.accept_mode(
                role=role,
                channel=channel,
                dut_signal=dut_signal,
                mode=mode,
                active_level=active_level,
                idle_level=idle_level,
                source=source,
                device_timestamp_us=response.timestamp_us,
            )

        if isinstance(response, CommandErrorMessage):
            return self._registry.reject_mode(
                role=role,
                channel=channel,
                dut_signal=dut_signal,
                mode=mode,
                active_level=active_level,
                idle_level=idle_level,
                source=source,
                error=response.error,
                detail=response.detail,
            )

        message_name = type(response).__name__
        raise GpioConfigurationError(
            f"Expected command response for GPIO mode configuration, got {message_name}"
        )
