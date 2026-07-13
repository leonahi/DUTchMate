"""Host-to-device protocol command encoding."""

from __future__ import annotations

import base64
import json
from dataclasses import dataclass
from typing import Literal

from dutchmate_core.device_connection.errors import ProtocolValidationError

GpioPin = Literal["reset", "boot"]
GpioMode = Literal["open_drain", "push_pull"]
BootMode = Literal["normal", "bootloader"]

VALID_GPIO_PINS = frozenset({"reset", "boot"})
VALID_GPIO_MODES = frozenset({"open_drain", "push_pull"})
VALID_BOOT_MODES = frozenset({"normal", "bootloader"})


@dataclass(frozen=True, slots=True)
class ConfigureGpioModeCommand:
    """Configure a DUT control pin drive mode before hardware actions."""

    pin: GpioPin
    mode: GpioMode

    def to_payload(self) -> dict[str, str]:
        return {
            "cmd": "configure_gpio_mode",
            "pin": self.pin,
            "mode": self.mode,
        }

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


def configure_gpio_mode_command(pin: str, mode: str) -> ConfigureGpioModeCommand:
    """Build a validated `configure_gpio_mode` command."""

    if pin not in VALID_GPIO_PINS:
        raise ProtocolValidationError("GPIO pin must be 'reset' or 'boot'")
    if mode not in VALID_GPIO_MODES:
        raise ProtocolValidationError("GPIO mode must be 'open_drain' or 'push_pull'")

    return ConfigureGpioModeCommand(pin=pin, mode=mode)  # type: ignore[arg-type]


def boot_mode_command(mode: str) -> BootModeCommand:
    """Build a validated `set_boot_mode` command."""

    if mode not in VALID_BOOT_MODES:
        raise ProtocolValidationError("Boot mode must be 'normal' or 'bootloader'")

    return BootModeCommand(mode=mode)  # type: ignore[arg-type]


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


def _encode_payload(payload: dict[str, object]) -> bytes:
    return (json.dumps(payload, separators=(",", ":"), sort_keys=False) + "\n").encode("utf-8")


def _is_int(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)
