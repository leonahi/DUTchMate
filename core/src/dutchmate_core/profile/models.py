"""Immutable DUT Profile configuration and provenance models."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Literal

from dutchmate_core.backends.contracts import BackendMode
from dutchmate_core.gpio_config.config import HardwareControlMapping, HardwareGpioConfig

if TYPE_CHECKING:
    from dutchmate_core.backends.settings import BackendSettings

ConnectionTopology = Literal["external_uart", "native_usb_console"]
SerialSelectorStrategy = Literal["exact_path", "enhanced_discovery", "usb_identity"]
ControlLineOpenBehavior = Literal["driver_default", "asserted", "deasserted"]
DefaultLineEnding = Literal["none", "lf", "cr", "crlf"]


@dataclass(frozen=True, slots=True)
class UartProfileConfig:
    """Unresolved UART values loaded from project configuration."""

    baudrate: object | None = None
    data_bits: object = 8
    parity: object = "none"
    stop_bits: object = 1
    rtscts: object = False
    xonxoff: object = False
    tx_enabled: object = False
    default_line_ending: object = "none"
    dtr_on_open: object = "driver_default"
    rts_on_open: object = "driver_default"


@dataclass(frozen=True, slots=True)
class DutProfileConfig:
    """Unresolved file-backed DUT Profile before overrides and defaults."""

    name: object | None = None
    mode: object | None = None
    serial_port: object | None = None
    reconnect_timeout_s: object = 5.0
    topology: object = "external_uart"
    usb_vid: object = None
    usb_pid: object = None
    usb_serial_number: object = None
    uart: UartProfileConfig = UartProfileConfig()
    hardware: HardwareGpioConfig = field(
        default_factory=lambda: HardwareGpioConfig(dut_io_voltage=None, controls={})
    )


@dataclass(frozen=True, slots=True)
class SerialSelector:
    """Immutable initial serial-device matching strategy."""

    strategy: SerialSelectorStrategy
    exact_path: str | None
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None


@dataclass(frozen=True, slots=True)
class EffectiveUartSettings:
    """Validated effective UART policy and provenance values."""

    baudrate: int
    data_bits: int
    parity: Literal["none"]
    stop_bits: Literal[1]
    rtscts: bool
    xonxoff: bool
    tx_enabled: bool
    default_line_ending: DefaultLineEnding
    dtr_on_open: ControlLineOpenBehavior
    rts_on_open: ControlLineOpenBehavior


@dataclass(frozen=True, slots=True)
class DutProfile:
    """Complete immutable DUT configuration used by one service runtime."""

    name: str | None
    backend_mode: BackendMode
    selector: SerialSelector
    current_serial_port: str | None
    reconnect_timeout_s: float
    topology: ConnectionTopology
    uart: EffectiveUartSettings
    dut_io_voltage: float | None
    controls: tuple[HardwareControlMapping, ...]

    @property
    def backend_settings(self) -> BackendSettings:
        """Project the profile onto the physical backend adapter settings."""

        from dutchmate_core.backends.settings import BackendSettings

        return BackendSettings(
            mode=self.backend_mode,
            serial_port=self.current_serial_port,
            reconnect_timeout_s=self.reconnect_timeout_s,
            baudrate=self.uart.baudrate,
            data_bits=self.uart.data_bits,
            parity=self.uart.parity,
            stop_bits=self.uart.stop_bits,
            tx_enabled=self.uart.tx_enabled,
            rtscts=self.uart.rtscts,
            xonxoff=self.uart.xonxoff,
            dtr_on_open=self.uart.dtr_on_open,
            rts_on_open=self.uart.rts_on_open,
            topology=self.topology,
            usb_vid=self.selector.vid,
            usb_pid=self.selector.pid,
            usb_serial_number=self.selector.serial_number,
        )

    @property
    def hardware_gpio_config(self) -> HardwareGpioConfig:
        """Return the validated GPIO configuration represented by this profile."""

        return HardwareGpioConfig(
            dut_io_voltage=self.dut_io_voltage,
            controls={mapping.role: mapping for mapping in self.controls},
        )

    def projection(self) -> dict[str, object]:
        """Return the bounded canonicalizable effective profile projection."""

        controls: list[dict[str, object]] = [
            {
                "role": mapping.role,
                "channel": mapping.channel,
                "dut_signal": mapping.dut_signal,
                "mode": mapping.mode,
                "active_level": mapping.active_level,
                "idle_level": mapping.idle_level,
            }
            for mapping in self.controls
        ]
        return {
            "name": self.name,
            "backend": {
                "mode": self.backend_mode,
                "topology": self.topology,
                "selector": {
                    "strategy": self.selector.strategy,
                    "exact_path": self.selector.exact_path,
                    **(
                        {
                            "vid": self.selector.vid,
                            "pid": self.selector.pid,
                            "serial_number": self.selector.serial_number,
                        }
                        if self.selector.strategy == "usb_identity"
                        else {}
                    ),
                },
                "current_serial_port": self.current_serial_port,
                "reconnect_timeout_s": self.reconnect_timeout_s,
            },
            "hardware": {
                "dut_io_voltage": self.dut_io_voltage,
                "uart": {
                    "baudrate": self.uart.baudrate,
                    "data_bits": self.uart.data_bits,
                    "parity": self.uart.parity,
                    "stop_bits": self.uart.stop_bits,
                    "rtscts": self.uart.rtscts,
                    "xonxoff": self.uart.xonxoff,
                    "tx_enabled": self.uart.tx_enabled,
                    "default_line_ending": self.uart.default_line_ending,
                    "control_lines": {
                        "dtr_on_open": self.uart.dtr_on_open,
                        "rts_on_open": self.uart.rts_on_open,
                    },
                },
                "control": controls,
            },
        }

    @property
    def canonical_json(self) -> bytes:
        """Return deterministic compact UTF-8 bytes for digesting and persistence."""

        return json.dumps(
            self.projection(),
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")

    @property
    def digest_sha256(self) -> str:
        """Return the stable SHA-256 digest of the canonical projection."""

        return hashlib.sha256(self.canonical_json).hexdigest()
