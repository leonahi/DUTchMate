"""Shared validation for public Device Core input contracts."""

from __future__ import annotations

import math
import unicodedata
from dataclasses import dataclass
from typing import Final, Literal, TypeAlias, cast

GpioControlChannel: TypeAlias = Literal["CTRL0", "CTRL1", "CTRL2", "CTRL3"]
GpioRoleName: TypeAlias = str
GpioControlMode: TypeAlias = Literal["open_drain", "push_pull"]
GpioLevel: TypeAlias = Literal["low", "high"]
GpioModeRequestSource: TypeAlias = Literal["config", "runtime"]

ALL_CONTROL_CHANNELS: Final[tuple[GpioControlChannel, ...]] = (
    "CTRL0",
    "CTRL1",
    "CTRL2",
    "CTRL3",
)
VALID_GPIO_CONTROL_CHANNELS: Final = frozenset(ALL_CONTROL_CHANNELS)
VALID_GPIO_MODES: Final = frozenset({"open_drain", "push_pull"})
VALID_GPIO_LEVELS: Final = frozenset({"low", "high"})
WELL_KNOWN_GPIO_ROLES: Final = frozenset({"reset", "boot", "power_enable", "wake"})

MAX_GPIO_IDENTIFIER_BYTES: Final = 64
MAX_CAPTURE_DURATION_S: Final = 300.0

IdentifierValidationReason: TypeAlias = Literal[
    "invalid_type",
    "invalid_length",
    "edge_whitespace",
    "control_character",
]


class GpioIdentifierValidationError(ValueError):
    """Raised when a GPIO role or DUT signal violates the exact identifier contract."""

    def __init__(
        self,
        *,
        field: str,
        reason: IdentifierValidationReason,
        actual_bytes: int | None = None,
    ) -> None:
        self.field = field
        self.reason = reason
        self.max_bytes = MAX_GPIO_IDENTIFIER_BYTES
        self.actual_bytes = actual_bytes
        super().__init__(self._detail())

    def _detail(self) -> str:
        field_name = f"GPIO {self.field}"
        if self.reason == "invalid_type":
            return f"{field_name} must be a string"
        if self.reason == "invalid_length":
            return f"{field_name} must encode to 1..{self.max_bytes} UTF-8 bytes"
        if self.reason == "edge_whitespace":
            return f"{field_name} must not have leading or trailing Unicode whitespace"
        return f"{field_name} must not contain Unicode control characters"


@dataclass(frozen=True, slots=True)
class ValidatedGpioConfiguration:
    """A GPIO request after lexical and electrical validation."""

    channel: GpioControlChannel
    role: GpioRoleName
    dut_signal: str
    mode: GpioControlMode
    active_level: GpioLevel
    idle_level: GpioLevel | None


def validate_capture_duration(duration_s: object) -> float:
    """Return a valid Phase 1 capture duration in seconds."""

    if (
        isinstance(duration_s, bool)
        or not isinstance(duration_s, int | float)
        or not math.isfinite(duration_s)
        or duration_s <= 0
        or duration_s > MAX_CAPTURE_DURATION_S
    ):
        raise ValueError(
            "duration must be a positive finite number no greater than "
            f"{MAX_CAPTURE_DURATION_S:g} seconds"
        )
    return float(duration_s)


def validate_gpio_identifier(value: object, *, field: str) -> str:
    """Validate and return an exact 1..64-byte GPIO role or signal identifier."""

    if not isinstance(value, str):
        raise GpioIdentifierValidationError(field=field, reason="invalid_type")

    try:
        actual_bytes = len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise GpioIdentifierValidationError(
            field=field,
            reason="control_character",
        ) from exc

    if not 1 <= actual_bytes <= MAX_GPIO_IDENTIFIER_BYTES:
        raise GpioIdentifierValidationError(
            field=field,
            reason="invalid_length",
            actual_bytes=actual_bytes,
        )
    if _is_unicode_whitespace(value[0]) or _is_unicode_whitespace(value[-1]):
        raise GpioIdentifierValidationError(
            field=field,
            reason="edge_whitespace",
            actual_bytes=actual_bytes,
        )
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise GpioIdentifierValidationError(
            field=field,
            reason="control_character",
            actual_bytes=actual_bytes,
        )
    return value


def validate_gpio_role(role: object) -> GpioRoleName:
    """Validate and preserve an exact GPIO role identifier."""

    return validate_gpio_identifier(role, field="role")


def validate_gpio_dut_signal(dut_signal: object) -> str:
    """Validate and preserve an exact DUT schematic signal identifier."""

    return validate_gpio_identifier(dut_signal, field="dut_signal")


def validate_gpio_channel(channel: object) -> GpioControlChannel:
    """Return a known physical GPIO control channel."""

    if not isinstance(channel, str) or channel not in VALID_GPIO_CONTROL_CHANNELS:
        raise ValueError("GPIO control channel must be 'CTRL0', 'CTRL1', 'CTRL2', or 'CTRL3'")
    return channel


def validate_gpio_mode(mode: object) -> GpioControlMode:
    """Return a supported GPIO electrical mode."""

    if not isinstance(mode, str) or mode not in VALID_GPIO_MODES:
        raise ValueError("GPIO mode must be 'open_drain' or 'push_pull'")
    return cast(GpioControlMode, mode)


def validate_gpio_level(level: object, *, field: str) -> GpioLevel:
    """Return a supported GPIO logic level."""

    if not isinstance(level, str) or level not in VALID_GPIO_LEVELS:
        raise ValueError(f"GPIO {field} must be 'low' or 'high'")
    return cast(GpioLevel, level)


def validate_gpio_mode_configuration(
    *,
    mode: object,
    active_level: object,
    idle_level: object,
) -> tuple[GpioControlMode, GpioLevel, GpioLevel | None]:
    """Validate the complete Phase 1 GPIO electrical-mode matrix."""

    mode_name = validate_gpio_mode(mode)
    active_level_name = validate_gpio_level(active_level, field="active_level")
    idle_level_name = (
        None
        if idle_level is None
        else validate_gpio_level(idle_level, field="idle_level")
    )

    if mode_name == "open_drain":
        if active_level_name != "low":
            raise ValueError("GPIO open_drain active_level must be 'low'")
        if idle_level_name is not None:
            raise ValueError("GPIO open_drain idle_level must be omitted")
    else:
        if idle_level_name is None:
            raise ValueError("GPIO push_pull idle_level is required")
        if idle_level_name == active_level_name:
            raise ValueError("GPIO push_pull idle_level must be opposite active_level")

    return mode_name, active_level_name, idle_level_name


def validate_gpio_configuration(
    *,
    channel: object,
    role: object,
    dut_signal: object,
    mode: object,
    active_level: object,
    idle_level: object = None,
) -> ValidatedGpioConfiguration:
    """Validate a complete GPIO mapping in the canonical field order."""

    channel_name = validate_gpio_channel(channel)
    role_name = validate_gpio_role(role)
    dut_signal_name = validate_gpio_dut_signal(dut_signal)
    mode_name, active_level_name, idle_level_name = validate_gpio_mode_configuration(
        mode=mode,
        active_level=active_level,
        idle_level=idle_level,
    )
    return ValidatedGpioConfiguration(
        channel=channel_name,
        role=role_name,
        dut_signal=dut_signal_name,
        mode=mode_name,
        active_level=active_level_name,
        idle_level=idle_level_name,
    )


def validate_gpio_source(source: object) -> GpioModeRequestSource:
    """Return a known GPIO request source."""

    if not isinstance(source, str) or source not in {"config", "runtime"}:
        raise ValueError("GPIO mode source must be 'config' or 'runtime'")
    return cast(GpioModeRequestSource, source)


def _is_unicode_whitespace(character: str) -> bool:
    codepoint = ord(character)
    return (
        0x0009 <= codepoint <= 0x000D
        or codepoint in {0x0020, 0x0085, 0x00A0, 0x1680, 0x2028, 0x2029, 0x202F, 0x205F, 0x3000}
        or 0x2000 <= codepoint <= 0x200A
    )
