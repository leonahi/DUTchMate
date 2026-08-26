"""Hardware action workflows guarded by GPIO configuration state."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal, TypeAlias

from dutchmate_core.backends.contracts import ControlState, DeviceControl, DeviceControlError
from dutchmate_core.gpio_config.modes import GpioModeRegistry
from dutchmate_core.validation import (
    InputValidationError,
    validate_boot_mode,
    validate_reset_pulse,
)

DeviceActionName: TypeAlias = Literal["reset", "set_boot_mode"]


class DeviceActionError(RuntimeError):
    """Raised when firmware rejects a hardware action command."""

    def __init__(
        self,
        *,
        error: str,
        detail: str,
        context: dict[str, object] | None = None,
    ) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail
        self.context = context.copy() if context is not None else None


@dataclass(frozen=True, slots=True)
class DeviceActionResult:
    """Successful hardware action result."""

    action: DeviceActionName
    performed_at: str
    device_timestamp_us: int | None = None
    pulse_ms: int | None = None
    mode: Literal["normal", "bootloader"] | None = None

    def __post_init__(self) -> None:
        if self.action == "reset":
            if self.pulse_ms is None or self.mode is not None:
                raise ValueError("reset results require pulse_ms and omit mode")
            return
        if self.mode is None or self.pulse_ms is not None:
            raise ValueError("boot-mode results require mode and omit pulse_ms")


class DeviceActionRunner:
    """Run reset/boot commands only when required GPIO roles are configured."""

    def __init__(
        self,
        *,
        registry: GpioModeRegistry,
        control: DeviceControl,
        wall_clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._registry = registry
        self._control = control
        self._wall_clock = wall_clock or (lambda: datetime.now(timezone.utc))

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the DUT reset role after confirming reset GPIO configuration."""

        try:
            pulse_ms_value = validate_reset_pulse(pulse_ms)
        except ValueError as exc:
            raise InputValidationError(str(exc)) from exc
        control = self._registry.require_role_configured("reset", operation="reset")
        device_timestamp_us = self._run_action(
            operation=lambda: self._control.pulse_control(
                channel=control.channel,
                pulse_ms=pulse_ms_value,
            ),
        )
        return DeviceActionResult(
            action="reset",
            pulse_ms=pulse_ms_value,
            performed_at=_format_utc(self._wall_clock()),
            device_timestamp_us=device_timestamp_us,
        )

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set DUT boot mode after confirming boot GPIO configuration."""

        try:
            mode_name = validate_boot_mode(mode)
        except ValueError as exc:
            raise InputValidationError(str(exc)) from exc
        control = self._registry.require_role_configured("boot", operation="set_boot_mode")
        state: ControlState = "active" if mode_name == "bootloader" else "idle"
        device_timestamp_us = self._run_action(
            operation=lambda: self._control.set_control_state(
                channel=control.channel,
                state=state,
            ),
        )
        return DeviceActionResult(
            action="set_boot_mode",
            mode=mode_name,
            performed_at=_format_utc(self._wall_clock()),
            device_timestamp_us=device_timestamp_us,
        )

    def _run_action(
        self,
        *,
        operation: Callable[[], int | None],
    ) -> int | None:
        try:
            return operation()
        except DeviceControlError as exc:
            raise DeviceActionError(error=exc.error, detail=exc.detail) from exc


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
