"""Load and validate hardware GPIO mapping configuration."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from dutchmate_core.device_connection.commands import (
    VALID_GPIO_CONTROL_CHANNELS,
    VALID_GPIO_LEVELS,
    VALID_GPIO_MODES,
    VALID_GPIO_ROLES,
)
from dutchmate_core.gpio_config.modes import (
    GpioControlChannel,
    GpioControlMode,
    GpioLevel,
    GpioRoleName,
)


class GpioConfigError(ValueError):
    """Raised when hardware GPIO configuration is invalid."""


@dataclass(frozen=True, slots=True)
class HardwareControlMapping:
    """Configured mapping from a DUTchMate control channel to a DUT role."""

    role: GpioRoleName
    channel: GpioControlChannel
    dut_signal: str
    mode: GpioControlMode
    active_level: GpioLevel
    idle_level: GpioLevel | None = None


@dataclass(frozen=True, slots=True)
class HardwareGpioConfig:
    """Validated hardware GPIO mappings from project configuration."""

    dut_io_voltage: float | None
    controls: dict[GpioRoleName, HardwareControlMapping]

    def require_control(self, role: str) -> HardwareControlMapping:
        """Return a required control mapping or raise a configuration error."""

        role_name = _validate_role_name(role)
        try:
            return self.controls[role_name]
        except KeyError as exc:
            raise GpioConfigError(f"hardware.control.{role} is not configured") from exc


def load_hardware_gpio_config(path: Path | str) -> HardwareGpioConfig:
    """Load hardware GPIO configuration from a TOML file."""

    with Path(path).open("rb") as file:
        data = _toml_module().load(file)
    return parse_hardware_gpio_config(cast(dict[str, Any], data))


def parse_hardware_gpio_config(data: dict[str, Any]) -> HardwareGpioConfig:
    """Parse and validate `[hardware.control.*]` configuration."""

    if not isinstance(data, dict):
        raise GpioConfigError("configuration root must be a TOML table")

    hardware = data.get("hardware", {})
    if hardware is None:
        hardware = {}
    if not isinstance(hardware, dict):
        raise GpioConfigError("[hardware] must be a TOML table")

    dut_io_voltage = _optional_voltage(hardware.get("dut_io_voltage"))
    control_table = hardware.get("control", {})
    if control_table is None:
        control_table = {}
    if not isinstance(control_table, dict):
        raise GpioConfigError("[hardware.control] must be a TOML table")

    controls: dict[GpioRoleName, HardwareControlMapping] = {}
    assigned_channels: dict[GpioControlChannel, GpioRoleName] = {}

    for role, raw_mapping in control_table.items():
        role_name = _validate_role_name(role)
        if not isinstance(raw_mapping, dict):
            raise GpioConfigError(f"[hardware.control.{role}] must be a TOML table")

        mapping = _parse_control_mapping(role=role_name, raw_mapping=raw_mapping)
        existing_role = assigned_channels.get(mapping.channel)
        if existing_role is not None:
            raise GpioConfigError(
                f"GPIO channel '{mapping.channel}' is assigned to both "
                f"'{existing_role}' and '{role_name}'"
            )

        assigned_channels[mapping.channel] = role_name
        controls[role_name] = mapping

    return HardwareGpioConfig(dut_io_voltage=dut_io_voltage, controls=controls)


def _parse_control_mapping(
    *,
    role: GpioRoleName,
    raw_mapping: dict[str, Any],
) -> HardwareControlMapping:
    allowed_keys = {
        "channel",
        "dut_signal",
        "mode",
        "active_level",
        "idle_level",
    }
    extra_keys = set(raw_mapping) - allowed_keys
    if extra_keys:
        names = ", ".join(sorted(extra_keys))
        raise GpioConfigError(f"Unexpected hardware.control.{role} field(s): {names}")

    channel = _required_string(raw_mapping, "channel", f"hardware.control.{role}")
    dut_signal = _required_string(raw_mapping, "dut_signal", f"hardware.control.{role}")
    mode = _required_string(raw_mapping, "mode", f"hardware.control.{role}")
    active_level = _required_string(raw_mapping, "active_level", f"hardware.control.{role}")
    idle_level = _optional_string(raw_mapping, "idle_level", f"hardware.control.{role}")

    channel_name = _validate_channel(channel)
    mode_name = _validate_mode(mode)
    active_level_name = _validate_level(active_level, "active_level")
    idle_level_name = _validate_optional_level(idle_level, "idle_level")

    return HardwareControlMapping(
        role=role,
        channel=channel_name,
        dut_signal=dut_signal,
        mode=mode_name,
        active_level=active_level_name,
        idle_level=idle_level_name,
    )


def _optional_voltage(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise GpioConfigError("hardware.dut_io_voltage must be a number")
    voltage = float(value)
    if voltage < 1.8 or voltage > 5.0:
        raise GpioConfigError("hardware.dut_io_voltage must be between 1.8 and 5.0")
    return voltage


def _required_string(raw_mapping: dict[str, Any], field_name: str, context: str) -> str:
    if field_name not in raw_mapping:
        raise GpioConfigError(f"{context}.{field_name} is required")
    value = raw_mapping[field_name]
    if not isinstance(value, str) or not value.strip():
        raise GpioConfigError(f"{context}.{field_name} must be a non-empty string")
    return value


def _optional_string(
    raw_mapping: dict[str, Any],
    field_name: str,
    context: str,
) -> str | None:
    if field_name not in raw_mapping:
        return None
    value = raw_mapping[field_name]
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise GpioConfigError(f"{context}.{field_name} must be a non-empty string")
    return value


def _validate_role_name(role: str) -> GpioRoleName:
    if role not in VALID_GPIO_ROLES:
        raise GpioConfigError("GPIO role must be 'reset' or 'boot'")
    return cast(GpioRoleName, role)


def _validate_channel(channel: str) -> GpioControlChannel:
    if channel not in VALID_GPIO_CONTROL_CHANNELS:
        raise GpioConfigError(
            "GPIO control channel must be 'CTRL0', 'CTRL1', 'CTRL2', or 'CTRL3'"
        )
    return cast(GpioControlChannel, channel)


def _validate_mode(mode: str) -> GpioControlMode:
    if mode not in VALID_GPIO_MODES:
        raise GpioConfigError("GPIO mode must be 'open_drain' or 'push_pull'")
    return cast(GpioControlMode, mode)


def _validate_level(level: str, field_name: str) -> GpioLevel:
    if level not in VALID_GPIO_LEVELS:
        raise GpioConfigError(f"GPIO {field_name} must be 'low' or 'high'")
    return cast(GpioLevel, level)


def _validate_optional_level(level: str | None, field_name: str) -> GpioLevel | None:
    if level is None:
        return None
    return _validate_level(level, field_name)


def _toml_module() -> Any:
    try:
        return importlib.import_module("tomllib")
    except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10.
        return importlib.import_module("tomli")
