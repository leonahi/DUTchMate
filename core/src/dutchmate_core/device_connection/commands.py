"""Host-to-device protocol command encoding."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TypeAlias

from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.validation import (
    VALID_GPIO_CONTROL_CHANNELS as VALID_GPIO_CONTROL_CHANNELS,
)
from dutchmate_core.validation import (
    VALID_GPIO_LEVELS as VALID_GPIO_LEVELS,
)
from dutchmate_core.validation import (
    VALID_GPIO_MODES as VALID_GPIO_MODES,
)
from dutchmate_core.validation import (
    WELL_KNOWN_GPIO_ROLES as WELL_KNOWN_GPIO_ROLES,
)
from dutchmate_core.validation import (
    BootMode,
    GpioControlChannel,
    GpioControlMode,
    GpioLevel,
    prepare_uart_send_payload,
    validate_boot_mode,
    validate_gpio_channel,
    validate_gpio_mode_configuration,
    validate_gpio_role,
    validate_reset_pulse,
)

GpioRole: TypeAlias = str
GpioMode: TypeAlias = GpioControlMode


@dataclass(frozen=True, slots=True)
class ConfigureGpioModeCommand:
    """Configure a DUT control role on a physical control channel."""

    channel: GpioControlChannel
    role: GpioRole
    mode: GpioMode
    active_level: GpioLevel
    idle_level: GpioLevel | None = None

    def to_payload(self) -> dict[str, str]:
        payload = {
            "cmd": "configure_gpio_mode",
            "channel": self.channel,
            "role": self.role,
            "mode": self.mode,
            "active_level": self.active_level,
        }
        if self.idle_level is not None:
            payload["idle_level"] = self.idle_level
        return payload

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class ResetCommand:
    """Pulse the configured DUT reset line."""

    pulse_ms: int = 100

    def to_payload(self) -> dict[str, int | str]:
        return {
            "cmd": "reset",
            "pulse_ms": self.pulse_ms,
        }

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class BootModeCommand:
    """Set the configured DUT BOOT/control pin behavior."""

    mode: BootMode

    def to_payload(self) -> dict[str, str]:
        return {
            "cmd": "set_boot_mode",
            "mode": self.mode,
        }

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class UartSendCommand:
    """Send raw bytes to the DUT UART RX line."""

    data: bytes

    def to_payload(self) -> dict[str, str]:
        return {
            "cmd": "uart_send",
            "data_b64": base64.b64encode(self.data).decode("ascii"),
        }

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


def configure_gpio_mode_command(
    *,
    channel: str,
    role: str,
    mode: str,
    active_level: str,
    idle_level: str | None = None,
) -> ConfigureGpioModeCommand:
    """Build a validated `configure_gpio_mode` command."""

    try:
        channel_name = validate_gpio_channel(channel)
        role_name = validate_gpio_role(role)
        mode_name, active_level_name, idle_level_name = validate_gpio_mode_configuration(
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc

    return ConfigureGpioModeCommand(
        channel=channel_name,
        role=role_name,
        mode=mode_name,
        active_level=active_level_name,
        idle_level=idle_level_name,
    )


def boot_mode_command(mode: str) -> BootModeCommand:
    """Build a validated `set_boot_mode` command."""

    try:
        mode_name = validate_boot_mode(mode)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc
    return BootModeCommand(mode=mode_name)


def reset_command(pulse_ms: int = 100) -> ResetCommand:
    """Build a validated `reset` command."""

    try:
        pulse_ms_value = validate_reset_pulse(pulse_ms)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc
    return ResetCommand(pulse_ms=pulse_ms_value)


def uart_send_command(data: bytes) -> UartSendCommand:
    """Build a validated `uart_send` command from raw bytes."""

    if not isinstance(data, bytes):
        raise ProtocolValidationError("UART send data must be bytes")
    if not data:
        raise ProtocolValidationError("UART send data must not be empty")
    if len(data) > 1024:
        raise ProtocolValidationError("UART send data must not exceed 1024 bytes")

    return UartSendCommand(data=data)


def uart_send_text_command(text: str, *, append_newline: bool = True) -> UartSendCommand:
    """Build a `uart_send` command from UTF-8 text."""

    try:
        data = prepare_uart_send_payload(text, append_newline=append_newline)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc
    return uart_send_command(data)


def _encode_payload(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n").encode("utf-8")
