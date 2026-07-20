"""Host-to-device protocol command encoding."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, cast

from dutchmate_core.device_connection.errors import ProtocolValidationError

GpioControlChannel = Literal["CTRL0", "CTRL1", "CTRL2", "CTRL3"]
GpioRole = Literal["reset", "boot"]
GpioMode = Literal["open_drain", "push_pull"]
GpioLevel = Literal["low", "high"]
BootMode = Literal["normal", "bootloader"]

VALID_GPIO_CONTROL_CHANNELS = frozenset({"CTRL0", "CTRL1", "CTRL2", "CTRL3"})
VALID_GPIO_ROLES = frozenset({"reset", "boot"})
VALID_GPIO_MODES = frozenset({"open_drain", "push_pull"})
VALID_GPIO_LEVELS = frozenset({"low", "high"})
VALID_BOOT_MODES = frozenset({"normal", "bootloader"})


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

    if channel not in VALID_GPIO_CONTROL_CHANNELS:
        raise ProtocolValidationError(
            "GPIO control channel must be 'CTRL0', 'CTRL1', 'CTRL2', or 'CTRL3'"
        )
    if role not in VALID_GPIO_ROLES:
        raise ProtocolValidationError("GPIO role must be 'reset' or 'boot'")
    if mode not in VALID_GPIO_MODES:
        raise ProtocolValidationError("GPIO mode must be 'open_drain' or 'push_pull'")
    if active_level not in VALID_GPIO_LEVELS:
        raise ProtocolValidationError("GPIO active_level must be 'low' or 'high'")
    if idle_level is not None and idle_level not in VALID_GPIO_LEVELS:
        raise ProtocolValidationError("GPIO idle_level must be 'low' or 'high'")

    return ConfigureGpioModeCommand(
        channel=cast(GpioControlChannel, channel),
        role=cast(GpioRole, role),
        mode=cast(GpioMode, mode),
        active_level=cast(GpioLevel, active_level),
        idle_level=cast(GpioLevel, idle_level) if idle_level is not None else None,
    )


def boot_mode_command(mode: str) -> BootModeCommand:
    """Build a validated `set_boot_mode` command."""

    if mode not in VALID_BOOT_MODES:
        raise ProtocolValidationError("Boot mode must be 'normal' or 'bootloader'")

    return BootModeCommand(mode=cast(BootMode, mode))


def reset_command(pulse_ms: int = 100) -> ResetCommand:
    """Build a validated `reset` command."""

    if not _is_int(pulse_ms) or pulse_ms < 1 or pulse_ms > 10000:
        raise ProtocolValidationError("Reset pulse_ms must be an integer between 1 and 10000")

    return ResetCommand(pulse_ms=pulse_ms)


def uart_send_command(data: bytes) -> UartSendCommand:
    """Build a validated `uart_send` command from raw bytes."""

    if not isinstance(data, bytes):
        raise ProtocolValidationError("UART send data must be bytes")
    if not data:
        raise ProtocolValidationError("UART send data must not be empty")

    return UartSendCommand(data=data)


def uart_send_text_command(text: str, *, append_newline: bool = True) -> UartSendCommand:
    """Build a `uart_send` command from UTF-8 text."""

    if not isinstance(text, str):
        raise ProtocolValidationError("UART send text must be a string")

    data = text.encode("utf-8")
    if append_newline and not data.endswith(b"\n"):
        data += b"\n"

    return uart_send_command(data)


def _encode_payload(payload: Mapping[str, object]) -> bytes:
    return (json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n").encode("utf-8")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
