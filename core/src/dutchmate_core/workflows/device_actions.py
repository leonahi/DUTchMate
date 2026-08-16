"""Hardware action workflows guarded by GPIO configuration state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Literal, TypeAlias

from dutchmate_core.backends.contracts import DeviceControl, DeviceControlError
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.gpio_config.modes import GpioModeRegistry
from dutchmate_core.validation import validate_boot_mode, validate_reset_pulse

DeviceActionName: TypeAlias = Literal["reset", "set_boot_mode"]


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
        control: DeviceControl,
    ) -> None:
        self._registry = registry
        self._control = control

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the DUT reset role after confirming reset GPIO configuration."""

        try:
            pulse_ms_value = validate_reset_pulse(pulse_ms)
        except ValueError as exc:
            raise ProtocolValidationError(str(exc)) from exc
        self._registry.require_role_configured("reset")
        return self._run_action(
            action="reset",
            operation=lambda: self._control.reset_dut(pulse_ms=pulse_ms_value),
        )

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set DUT boot mode after confirming boot GPIO configuration."""

        try:
            mode_name = validate_boot_mode(mode)
        except ValueError as exc:
            raise ProtocolValidationError(str(exc)) from exc
        self._registry.require_role_configured("boot")
        return self._run_action(
            action="set_boot_mode",
            operation=lambda: self._control.set_boot_mode(mode=mode_name),
        )

    def _run_action(
        self,
        *,
        action: DeviceActionName,
        operation: Callable[[], int | None],
    ) -> DeviceActionResult:
        try:
            timestamp_us = operation()
        except DeviceControlError as exc:
            raise DeviceActionError(error=exc.error, detail=exc.detail) from exc
        return DeviceActionResult(action=action, timestamp_us=timestamp_us)
