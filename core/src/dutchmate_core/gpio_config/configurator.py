"""GPIO mode configuration workflow."""

from __future__ import annotations

from dutchmate_core.backends.contracts import DeviceControl, DeviceControlError
from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRequestSource,
)
from dutchmate_core.validation import InputValidationError, validate_gpio_configuration


class GpioConfigurator:
    """Configure GPIO modes through firmware and update accepted host state."""

    def __init__(
        self,
        *,
        registry: GpioModeRegistry,
        control: DeviceControl,
    ) -> None:
        self._registry = registry
        self._control = control

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
            raise InputValidationError(str(exc)) from exc
        try:
            timestamp_us = self._control.configure_gpio_mode(
                channel=request.channel,
                role=request.role,
                mode=request.mode,
                active_level=request.active_level,
                idle_level=request.idle_level,
            )
        except DeviceControlError as exc:
            if exc.error == "unexpected_response":
                raise GpioConfigurationError(exc.detail) from exc
            return self._registry.reject_mode(
                role=request.role,
                channel=request.channel,
                dut_signal=request.dut_signal,
                mode=request.mode,
                active_level=request.active_level,
                idle_level=request.idle_level,
                source=source,
                error=exc.error,
                detail=exc.detail,
            )
        return self._registry.accept_mode(
            role=request.role,
            channel=request.channel,
            dut_signal=request.dut_signal,
            mode=request.mode,
            active_level=request.active_level,
            idle_level=request.idle_level,
            source=source,
            device_timestamp_us=timestamp_us,
        )
