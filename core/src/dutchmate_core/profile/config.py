"""Load and resolve one file-backed DUT Profile."""

from __future__ import annotations

import importlib
import math
import unicodedata
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Final, Literal, cast

from dutchmate_core.backends.contracts import BackendMode
from dutchmate_core.backends.settings import (
    DEFAULT_BASIC_BAUDRATE,
    DEFAULT_RECONNECT_TIMEOUT_S,
    ENHANCED_BAUDRATE,
)
from dutchmate_core.gpio_config.config import GpioConfigError, parse_hardware_gpio_config
from dutchmate_core.profile.models import (
    ConnectionTopology,
    ControlLineOpenBehavior,
    DefaultLineEnding,
    DutProfile,
    DutProfileConfig,
    EffectiveUartSettings,
    SerialSelector,
    UartProfileConfig,
)
from dutchmate_core.validation import validate_serial_port

MAX_PROFILE_NAME_BYTES: Final = 128
MAX_PROFILE_PROJECTION_BYTES: Final = 65536


class DutProfileError(ValueError):
    """Raised when a DUT Profile is invalid."""


def load_dut_profile_config(path: Path | str) -> DutProfileConfig:
    """Load unresolved DUT Profile configuration from TOML."""

    with Path(path).open("rb") as file:
        raw_config = _toml_module().load(file)
    if not isinstance(raw_config, Mapping):
        raise DutProfileError("configuration root must be a TOML table")
    return parse_dut_profile_config(cast(Mapping[str, object], raw_config))


def parse_dut_profile_config(raw_config: Mapping[str, object]) -> DutProfileConfig:
    """Parse profile/backend/UART/GPIO tables without selecting CLI overrides."""

    if not isinstance(raw_config, Mapping):
        raise DutProfileError("configuration root must be a TOML table")

    profile = _optional_table(raw_config, "profile")
    _reject_extra_fields(profile, allowed={"name"}, context="[profile]")

    backend = _optional_table(raw_config, "backend")
    _reject_extra_fields(
        backend,
        allowed={"mode", "serial_port", "reconnect_timeout_s", "topology"},
        context="[backend]",
    )

    hardware = _optional_table(raw_config, "hardware")
    uart = _optional_table(hardware, "uart", context="[hardware.uart]")
    _reject_extra_fields(
        uart,
        allowed={
            "baudrate",
            "data_bits",
            "parity",
            "stop_bits",
            "rtscts",
            "xonxoff",
            "tx_enabled",
            "default_line_ending",
            "control_lines",
        },
        context="[hardware.uart]",
    )
    control_lines = _optional_table(
        uart,
        "control_lines",
        context="[hardware.uart.control_lines]",
    )
    _reject_extra_fields(
        control_lines,
        allowed={"dtr_on_open", "rts_on_open"},
        context="[hardware.uart.control_lines]",
    )

    try:
        gpio = parse_hardware_gpio_config(cast(dict[str, Any], raw_config))
    except GpioConfigError as exc:
        raise DutProfileError(str(exc)) from exc

    return DutProfileConfig(
        name=profile.get("name"),
        mode=backend.get("mode"),
        serial_port=backend.get("serial_port"),
        reconnect_timeout_s=backend.get(
            "reconnect_timeout_s",
            DEFAULT_RECONNECT_TIMEOUT_S,
        ),
        topology=backend.get("topology", "external_uart"),
        uart=UartProfileConfig(
            baudrate=uart.get("baudrate"),
            data_bits=uart.get("data_bits", 8),
            parity=uart.get("parity", "none"),
            stop_bits=uart.get("stop_bits", 1),
            rtscts=uart.get("rtscts", False),
            xonxoff=uart.get("xonxoff", False),
            tx_enabled=uart.get("tx_enabled", False),
            default_line_ending=uart.get("default_line_ending", "none"),
            dtr_on_open=control_lines.get("dtr_on_open", "driver_default"),
            rts_on_open=control_lines.get("rts_on_open", "driver_default"),
        ),
        hardware=gpio,
    )


def resolve_profile_mode(config: DutProfileConfig, override: object | None = None) -> BackendMode:
    """Resolve the required backend mode with explicit override precedence."""

    raw_mode = override if override is not None else config.mode
    if raw_mode is None:
        raise DutProfileError("Backend mode is required; pass --backend or set [backend].mode")
    if not isinstance(raw_mode, str) or raw_mode not in {"basic", "enhanced"}:
        raise DutProfileError("backend mode must be 'basic' or 'enhanced'")
    return cast(BackendMode, raw_mode)


def resolve_dut_profile(
    config: DutProfileConfig,
    *,
    name: object | None = None,
    mode: object | None = None,
    serial_port: object | None = None,
    topology: object | None = None,
    baudrate: object | None = None,
    reconnect_timeout_s: object | None = None,
    data_bits: object | None = None,
    parity: object | None = None,
    stop_bits: object | None = None,
    rtscts: object | None = None,
    xonxoff: object | None = None,
    tx_enabled: object | None = None,
    default_line_ending: object | None = None,
    dtr_on_open: object | None = None,
    rts_on_open: object | None = None,
) -> DutProfile:
    """Apply overrides and validate one complete immutable effective profile."""

    resolved_mode = resolve_profile_mode(config, mode)
    resolved_name = _optional_name(config.name if name is None else name)
    resolved_topology = _topology(config.topology if topology is None else topology)
    raw_port = serial_port if serial_port is not None else config.serial_port
    resolved_port = None if raw_port is None else _serial_port(raw_port)
    if resolved_mode == "basic" and resolved_port is None:
        raise DutProfileError("Basic backend requires --serial-port or [backend].serial_port")
    if resolved_topology == "native_usb_console" and resolved_port is None:
        raise DutProfileError(
            "native_usb_console requires an exact serial path until a safe unique identity "
            "selector is configured"
        )

    resolved_reconnect_timeout = _finite_number(
        config.reconnect_timeout_s if reconnect_timeout_s is None else reconnect_timeout_s,
        field="reconnect timeout",
        minimum=0.1,
        maximum=60.0,
    )
    configured_baudrate = config.uart.baudrate if baudrate is None else baudrate
    if configured_baudrate is None:
        resolved_baudrate = (
            DEFAULT_BASIC_BAUDRATE if resolved_mode == "basic" else ENHANCED_BAUDRATE
        )
    else:
        resolved_baudrate = _positive_integer(configured_baudrate, field="UART baudrate")
    if resolved_mode == "enhanced" and resolved_baudrate != ENHANCED_BAUDRATE:
        raise DutProfileError(f"Enhanced backend baudrate is fixed at {ENHANCED_BAUDRATE}")

    resolved_data_bits = _fixed_integer(
        config.uart.data_bits if data_bits is None else data_bits,
        field="hardware.uart.data_bits",
        expected=8,
    )
    resolved_parity = _fixed_string(
        config.uart.parity if parity is None else parity,
        field="hardware.uart.parity",
        expected="none",
    )
    resolved_stop_bits = _fixed_integer(
        config.uart.stop_bits if stop_bits is None else stop_bits,
        field="hardware.uart.stop_bits",
        expected=1,
    )
    resolved_rtscts = _boolean(
        config.uart.rtscts if rtscts is None else rtscts,
        field="hardware.uart.rtscts",
    )
    resolved_xonxoff = _boolean(
        config.uart.xonxoff if xonxoff is None else xonxoff,
        field="hardware.uart.xonxoff",
    )
    resolved_tx_enabled = _boolean(
        config.uart.tx_enabled if tx_enabled is None else tx_enabled,
        field="hardware.uart.tx_enabled",
    )
    resolved_default_line_ending = _line_ending(
        config.uart.default_line_ending
        if default_line_ending is None
        else default_line_ending
    )
    resolved_dtr_on_open = _control_line_behavior(
        config.uart.dtr_on_open if dtr_on_open is None else dtr_on_open,
        field="hardware.uart.control_lines.dtr_on_open",
    )
    resolved_rts_on_open = _control_line_behavior(
        config.uart.rts_on_open if rts_on_open is None else rts_on_open,
        field="hardware.uart.control_lines.rts_on_open",
    )
    if resolved_rtscts and resolved_rts_on_open != "driver_default":
        raise DutProfileError("RTS application state conflicts with hardware.uart.rtscts")
    if resolved_rtscts:
        raise DutProfileError("hardware.uart.rtscts must be false in Phase 1")
    if resolved_xonxoff:
        raise DutProfileError("hardware.uart.xonxoff must be false in Phase 1")

    selector = SerialSelector(
        strategy="exact_path" if resolved_port is not None else "enhanced_discovery",
        exact_path=resolved_port,
    )
    controls = tuple(
        config.hardware.controls[role] for role in sorted(config.hardware.controls)
    )
    profile = DutProfile(
        name=resolved_name,
        backend_mode=resolved_mode,
        selector=selector,
        current_serial_port=resolved_port,
        reconnect_timeout_s=resolved_reconnect_timeout,
        topology=resolved_topology,
        uart=EffectiveUartSettings(
            baudrate=resolved_baudrate,
            data_bits=resolved_data_bits,
            parity=cast(Literal["none"], resolved_parity),
            stop_bits=cast(Literal[1], resolved_stop_bits),
            rtscts=resolved_rtscts,
            xonxoff=resolved_xonxoff,
            tx_enabled=resolved_tx_enabled,
            default_line_ending=resolved_default_line_ending,
            dtr_on_open=resolved_dtr_on_open,
            rts_on_open=resolved_rts_on_open,
        ),
        dut_io_voltage=config.hardware.dut_io_voltage,
        controls=controls,
    )
    if len(profile.canonical_json) > MAX_PROFILE_PROJECTION_BYTES:
        raise DutProfileError(
            f"effective DUT Profile exceeds {MAX_PROFILE_PROJECTION_BYTES} bytes"
        )
    return profile


def _optional_table(
    raw_config: Mapping[str, object],
    key: str,
    *,
    context: str | None = None,
) -> Mapping[str, object]:
    value = raw_config.get(key, {})
    if not isinstance(value, Mapping):
        raise DutProfileError(f"{context or f'[{key}]'} must be a TOML table")
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
        raise DutProfileError(f"Unexpected {context} field(s): {names}")


def _optional_name(value: object | None) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DutProfileError("profile.name must be a string")
    encoded = value.encode("utf-8")
    if (
        not encoded
        or len(encoded) > MAX_PROFILE_NAME_BYTES
        or value[0].isspace()
        or value[-1].isspace()
        or any(unicodedata.category(character) == "Cc" for character in value)
    ):
        raise DutProfileError(
            f"profile.name must be 1..{MAX_PROFILE_NAME_BYTES} UTF-8 bytes with no "
            "edge whitespace or control characters"
        )
    return value


def _topology(value: object) -> ConnectionTopology:
    if value not in {"external_uart", "native_usb_console"}:
        raise DutProfileError(
            "backend topology must be 'external_uart' or 'native_usb_console'"
        )
    return value


def _serial_port(value: object) -> str:
    try:
        return validate_serial_port(value)
    except ValueError as exc:
        raise DutProfileError(f"serial port: {exc}") from exc


def _positive_integer(value: object, *, field: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise DutProfileError(f"{field} must be a positive integer")
    return value


def _fixed_integer(value: object, *, field: str, expected: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value != expected:
        raise DutProfileError(f"{field} must be {expected}")
    return value


def _fixed_string(value: object, *, field: str, expected: str) -> str:
    if value != expected:
        raise DutProfileError(f"{field} must be '{expected}'")
    return expected


def _boolean(value: object, *, field: str) -> bool:
    if not isinstance(value, bool):
        raise DutProfileError(f"{field} must be a boolean")
    return value


def _line_ending(value: object) -> DefaultLineEnding:
    if value not in {"none", "lf", "cr", "crlf"}:
        raise DutProfileError("hardware.uart.default_line_ending is invalid")
    return value


def _control_line_behavior(value: object, *, field: str) -> ControlLineOpenBehavior:
    if value not in {"driver_default", "asserted", "deasserted"}:
        raise DutProfileError(
            f"{field} must be 'driver_default', 'asserted', or 'deasserted'"
        )
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
        raise DutProfileError(
            f"{field} must be a finite number between {minimum:g} and {maximum:g}"
        )
    return float(value)


def _toml_module() -> Any:
    try:
        return importlib.import_module("tomllib")
    except ModuleNotFoundError:  # pragma: no cover - Python 3.10 only.
        return importlib.import_module("tomli")
