"""Host-to-device protocol command encoding."""

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias

from dutchmate_core.device_connection.errors import (
    HostCommandFrameTooLargeError,
    ProtocolValidationError,
)
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
    GpioControlChannel,
    GpioControlMode,
    GpioLevel,
    prepare_uart_send_payload,
    validate_gpio_channel,
    validate_gpio_mode_configuration,
    validate_reset_pulse,
)

GpioMode: TypeAlias = GpioControlMode
ControlState: TypeAlias = Literal["active", "idle"]
MAX_HOST_FRAME_BYTES: Final = 2048


@dataclass(frozen=True, slots=True)
class ConfigureGpioModeCommand:
    """Configure the electrical behavior of a physical control channel."""

    channel: GpioControlChannel
    mode: GpioMode
    active_level: GpioLevel
    idle_level: GpioLevel | None = None

    def to_payload(self) -> dict[str, str]:
        payload = {
            "cmd": "configure_gpio_mode",
            "channel": self.channel,
            "mode": self.mode,
            "active_level": self.active_level,
        }
        if self.idle_level is not None:
            payload["idle_level"] = self.idle_level
        return payload

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class PulseControlCommand:
    """Pulse one configured physical control channel."""

    channel: GpioControlChannel
    pulse_ms: int = 100

    def to_payload(self) -> dict[str, int | str]:
        return {
            "cmd": "pulse_control",
            "channel": self.channel,
            "pulse_ms": self.pulse_ms,
        }

    def to_ndjson(self) -> bytes:
        return _encode_payload(self.to_payload())


@dataclass(frozen=True, slots=True)
class SetControlStateCommand:
    """Apply the active or idle behavior of one configured control channel."""

    channel: GpioControlChannel
    state: ControlState

    def to_payload(self) -> dict[str, str]:
        return {
            "cmd": "set_control_state",
            "channel": self.channel,
            "state": self.state,
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
    mode: str,
    active_level: str,
    idle_level: str | None = None,
) -> ConfigureGpioModeCommand:
    """Build a validated `configure_gpio_mode` command."""

    try:
        channel_name = validate_gpio_channel(channel)
        mode_name, active_level_name, idle_level_name = validate_gpio_mode_configuration(
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc

    return ConfigureGpioModeCommand(
        channel=channel_name,
        mode=mode_name,
        active_level=active_level_name,
        idle_level=idle_level_name,
    )


def pulse_control_command(
    *,
    channel: str,
    pulse_ms: int = 100,
) -> PulseControlCommand:
    """Build a validated `pulse_control` command."""

    try:
        channel_name = validate_gpio_channel(channel)
        pulse_ms_value = validate_reset_pulse(pulse_ms)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc
    return PulseControlCommand(channel=channel_name, pulse_ms=pulse_ms_value)


def set_control_state_command(
    *,
    channel: str,
    state: str,
) -> SetControlStateCommand:
    """Build a validated `set_control_state` command."""

    try:
        channel_name = validate_gpio_channel(channel)
    except ValueError as exc:
        raise ProtocolValidationError(str(exc)) from exc
    if state == "active":
        state_name: ControlState = "active"
    elif state == "idle":
        state_name = "idle"
    else:
        raise ProtocolValidationError("Control state must be 'active' or 'idle'")
    return SetControlStateCommand(
        channel=channel_name,
        state=state_name,
    )


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
    frame = (
        json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=False,
        )
        + "\n"
    ).encode("utf-8")
    if len(frame) > MAX_HOST_FRAME_BYTES:
        raise HostCommandFrameTooLargeError(
            actual_frame_bytes=len(frame),
            max_frame_bytes=MAX_HOST_FRAME_BYTES,
        )
    return frame
