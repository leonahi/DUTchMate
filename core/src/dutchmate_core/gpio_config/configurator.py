"""GPIO mode configuration workflow."""

from __future__ import annotations

from typing import TypeAlias

from dutchmate_core.device_connection.commands import configure_gpio_mode_command
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.device_connection.messages import CommandErrorMessage, CommandSuccessMessage
from dutchmate_core.device_connection.transport import CommandTransport
from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRequestSource,
)
from dutchmate_core.validation import validate_gpio_configuration

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
    ) -> GpioControlChannelState:
        """Send `configure_gpio_mode` and record the firmware result."""

        try:
            request = validate_gpio_configuration(
                channel=channel,
                role=role,
                dut_signal=dut_signal,
                mode=mode,
                active_level=active_level,
                idle_level=idle_level,
            )
        except ValueError as exc:
            raise ProtocolValidationError(str(exc)) from exc
        command = configure_gpio_mode_command(
            channel=request.channel,
            role=request.role,
            mode=request.mode,
            active_level=request.active_level,
            idle_level=request.idle_level,
        )
        response = self._transport.request(command.to_ndjson())

        if isinstance(response, CommandSuccessMessage):
            return self._registry.accept_mode(
                role=request.role,
                channel=request.channel,
                dut_signal=request.dut_signal,
                mode=request.mode,
                active_level=request.active_level,
                idle_level=request.idle_level,
                source=source,
                device_timestamp_us=response.timestamp_us,
            )

        if isinstance(response, CommandErrorMessage):
            return self._registry.reject_mode(
                role=request.role,
                channel=request.channel,
                dut_signal=request.dut_signal,
                mode=request.mode,
                active_level=request.active_level,
                idle_level=request.idle_level,
                source=source,
                error=response.error,
                detail=response.detail,
            )

        message_name = type(response).__name__
        raise GpioConfigurationError(
            f"Expected command response for GPIO mode configuration, got {message_name}"
        )
