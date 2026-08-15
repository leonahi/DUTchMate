"""Backend selection and serial-setting contracts shared by CLI and service."""

from __future__ import annotations

import importlib
import math
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

from dutchmate_core.backends.contracts import BackendMode
from dutchmate_core.validation import validate_serial_port

DEFAULT_BASIC_BAUDRATE: Final = 115200
ENHANCED_BAUDRATE: Final = 460800
DEFAULT_RECONNECT_TIMEOUT_S: Final = 5.0


class BackendConfigError(ValueError):
    """Raised when backend selection or UART settings are invalid."""


@dataclass(frozen=True, slots=True)
class UartConfig:
    """Configured UART values before backend-specific defaults are resolved."""

    baudrate: int | None = None
    data_bits: int = 8
    parity: str = "none"
    stop_bits: int = 1
    tx_enabled: bool = False


@dataclass(frozen=True, slots=True)
class BackendConfig:
    """Optional project backend selection loaded from TOML."""

    mode: BackendMode | None = None
    serial_port: str | None = None
    reconnect_timeout_s: float = DEFAULT_RECONNECT_TIMEOUT_S
    uart: UartConfig = UartConfig()


@dataclass(frozen=True, slots=True)
class BackendSettings:
    """Complete validated settings for one selected backend."""

    mode: BackendMode
    serial_port: str | None
    reconnect_timeout_s: float
    baudrate: int
    data_bits: int
    parity: str
    stop_bits: int
    tx_enabled: bool


def load_backend_config(path: Path | str) -> BackendConfig:
    """Load backend/UART configuration from a TOML file."""

    with Path(path).open("rb") as file:
        raw_config = _toml_module().load(file)
    if not isinstance(raw_config, Mapping):
        raise BackendConfigError("configuration root must be a TOML table")
    return parse_backend_config(cast(Mapping[str, object], raw_config))


def parse_backend_config(raw_config: Mapping[str, object]) -> BackendConfig:
    """Parse optional `[backend]` and `[hardware.uart]` configuration."""

    backend = _optional_table(raw_config, "backend")
    _reject_extra_fields(
        backend,
        allowed={"mode", "serial_port", "reconnect_timeout_s"},
        context="[backend]",
    )

    raw_mode = backend.get("mode")
    mode = None if raw_mode is None else _validate_mode(raw_mode)
    raw_serial_port = backend.get("serial_port")
    serial_port = (
        None
        if raw_serial_port is None
        else _validate_port(raw_serial_port, field="[backend].serial_port")
    )
    reconnect_timeout_s = _finite_number(
        backend.get("reconnect_timeout_s", DEFAULT_RECONNECT_TIMEOUT_S),
        field="[backend].reconnect_timeout_s",
        minimum=0.1,
        maximum=60.0,
    )

    hardware = _optional_table(raw_config, "hardware")
    uart = _optional_table(hardware, "uart", context="[hardware.uart]")
    _reject_extra_fields(
        uart,
        allowed={"baudrate", "data_bits", "parity", "stop_bits", "tx_enabled"},
        context="[hardware.uart]",
    )
    uart_config = UartConfig(
        baudrate=_optional_baudrate(uart.get("baudrate")),
        data_bits=_fixed_integer(
            uart.get("data_bits", 8),
            field="[hardware.uart].data_bits",
            expected=8,
        ),
        parity=_fixed_string(
            uart.get("parity", "none"),
            field="[hardware.uart].parity",
            expected="none",
        ),
        stop_bits=_fixed_integer(
            uart.get("stop_bits", 1),
            field="[hardware.uart].stop_bits",
            expected=1,
        ),
        tx_enabled=_boolean(uart.get("tx_enabled", False), field="[hardware.uart].tx_enabled"),
    )
    return BackendConfig(
        mode=mode,
        serial_port=serial_port,
        reconnect_timeout_s=reconnect_timeout_s,
        uart=uart_config,
    )


def resolve_backend_mode(config: BackendConfig, override: str | None = None) -> BackendMode:
    """Resolve the required backend mode with CLI precedence."""

    raw_mode = override if override is not None else config.mode
    if raw_mode is None:
        raise BackendConfigError(
            "Backend mode is required; pass --backend or set [backend].mode"
        )
    return _validate_mode(raw_mode)


def resolve_backend_settings(
    config: BackendConfig,
    *,
    mode: str | None = None,
    serial_port: str | None = None,
    baudrate: int | None = None,
    reconnect_timeout_s: float | None = None,
    data_bits: int | None = None,
    parity: str | None = None,
    stop_bits: int | None = None,
    tx_enabled: bool | None = None,
) -> BackendSettings:
    """Apply explicit overrides and backend-specific defaults."""

    resolved_mode = resolve_backend_mode(config, mode)
    raw_port = serial_port if serial_port is not None else config.serial_port
    resolved_port = (
        None if raw_port is None else _validate_port(raw_port, field="serial port")
    )
    if resolved_mode == "basic" and resolved_port is None:
        raise BackendConfigError(
            "Basic backend requires --serial-port or [backend].serial_port"
        )

    configured_baudrate = baudrate if baudrate is not None else config.uart.baudrate
    if configured_baudrate is None:
        resolved_baudrate = (
            DEFAULT_BASIC_BAUDRATE if resolved_mode == "basic" else ENHANCED_BAUDRATE
        )
    else:
        resolved_baudrate = _baudrate(configured_baudrate, field="UART baudrate")
    if resolved_mode == "enhanced" and resolved_baudrate != ENHANCED_BAUDRATE:
        raise BackendConfigError(
            f"Enhanced backend baudrate is fixed at {ENHANCED_BAUDRATE}"
        )

    resolved_reconnect_timeout_s = (
        config.reconnect_timeout_s
        if reconnect_timeout_s is None
        else _finite_number(
            reconnect_timeout_s,
            field="reconnect timeout",
            minimum=0.1,
            maximum=60.0,
        )
    )
    resolved_data_bits = (
        config.uart.data_bits
        if data_bits is None
        else _fixed_integer(data_bits, field="UART data_bits", expected=8)
    )
    resolved_parity = (
        config.uart.parity
        if parity is None
        else _fixed_string(parity, field="UART parity", expected="none")
    )
    resolved_stop_bits = (
        config.uart.stop_bits
        if stop_bits is None
        else _fixed_integer(stop_bits, field="UART stop_bits", expected=1)
    )
    resolved_tx_enabled = (
        config.uart.tx_enabled
        if tx_enabled is None
        else _boolean(tx_enabled, field="UART tx_enabled")
    )

    return BackendSettings(
        mode=resolved_mode,
        serial_port=resolved_port,
        reconnect_timeout_s=resolved_reconnect_timeout_s,
        baudrate=resolved_baudrate,
        data_bits=resolved_data_bits,
        parity=resolved_parity,
        stop_bits=resolved_stop_bits,
        tx_enabled=resolved_tx_enabled,
    )


def _optional_table(
    raw_config: Mapping[str, object],
    key: str,
    *,
    context: str | None = None,
) -> Mapping[str, object]:
    value = raw_config.get(key, {})
    if not isinstance(value, Mapping):
        raise BackendConfigError(f"{context or f'[{key}]'} must be a TOML table")
    return cast(Mapping[str, object], value)


def _reject_extra_fields(
    values: Mapping[str, object],
    *,
    allowed: set[str],
    context: str,
) -> None:
    extra = set(values) - allowed
    if extra:
        names = ", ".join(sorted(extra))
        raise BackendConfigError(f"Unexpected {context} field(s): {names}")


def _validate_mode(value: object) -> BackendMode:
    if not isinstance(value, str) or value not in {"basic", "enhanced"}:
        raise BackendConfigError("backend mode must be 'basic' or 'enhanced'")
    return cast(BackendMode, value)


def _validate_port(value: object, *, field: str) -> str:
    try:
        return validate_serial_port(value)
    except ValueError as exc:
        raise BackendConfigError(f"{field}: {exc}") from exc


def _optional_baudrate(value: object) -> int | None:
    if value is None:
        return None
    return _baudrate(value, field="[hardware.uart].baudrate")


def _baudrate(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise BackendConfigError(f"{field} must be a positive integer")
    return value


def _fixed_integer(value: object, *, field: str, expected: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value != expected:
        raise BackendConfigError(f"{field} must be {expected}")
    return value


def _fixed_string(value: object, *, field: str, expected: str) -> str:
    if value != expected:
        raise BackendConfigError(f"{field} must be '{expected}'")
    return expected


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise BackendConfigError(f"{field} must be a boolean")
    return value


def _finite_number(
    value: object,
    *,
    field: str,
    minimum: float,
    maximum: float,
) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < minimum
        or value > maximum
    ):
        raise BackendConfigError(
            f"{field} must be a finite number between {minimum:g} and {maximum:g}"
        )
    return float(value)


def _toml_module() -> Any:
    try:
        return importlib.import_module("tomllib")
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only.
        return importlib.import_module("tomli")
