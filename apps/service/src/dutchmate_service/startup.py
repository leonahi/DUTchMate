"""Device Core Service startup configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Final, Protocol

from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.serial_transport import (
    SerialCommandTransport,
    open_serial_command_transport,
)
from dutchmate_core.gpio_config.config import (
    HardwareGpioConfig,
    load_hardware_gpio_config,
    parse_hardware_gpio_config,
)
from dutchmate_core.gpio_config.modes import GpioControlChannelState, GpioRoleName
from dutchmate_core.runtime import DeviceCoreRuntime, DeviceCoreRuntimeError, DeviceCoreStatus

DEFAULT_CONFIG_PATH: Final = Path(".dutchmate/config.toml")


class StartupConfigRuntime(Protocol):
    """Runtime surface needed to apply startup hardware configuration."""

    def status(self) -> DeviceCoreStatus:
        """Return current runtime status."""

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[GpioRoleName, GpioControlChannelState]:
        """Apply configured hardware control mappings."""


def load_startup_hardware_config(path: Path = DEFAULT_CONFIG_PATH) -> HardwareGpioConfig:
    """Load startup hardware configuration, treating a missing file as empty config."""

    try:
        return load_hardware_gpio_config(path)
    except FileNotFoundError:
        return parse_hardware_gpio_config({})


def apply_startup_hardware_config(
    runtime: StartupConfigRuntime,
    config: HardwareGpioConfig,
) -> bool:
    """Apply startup GPIO mappings if a Debug Helper is already connected."""

    if not config.controls:
        return False
    if not runtime.status().connected:
        return False

    runtime.apply_hardware_config(config)
    return True


def build_startup_runtime(
    *,
    session_root: Path | str,
    serial_port: str | None = None,
) -> DeviceCoreRuntime:
    """Build the service runtime and connect to the Debug Helper when requested."""

    if serial_port is None:
        return DeviceCoreRuntime(transport=_UnavailableTransport(), session_root=session_root)

    transport = open_serial_command_transport(port=serial_port)
    runtime = DeviceCoreRuntime(
        transport=transport,
        message_source=transport,
        session_root=session_root,
        port=serial_port,
    )
    hello = read_startup_hello(transport)
    runtime.record_hello(hello, port=serial_port)
    return runtime


def read_startup_hello(transport: SerialCommandTransport) -> HelloMessage:
    """Read and validate the initial Debug Helper hello message."""

    message = transport.read_message()
    if not isinstance(message, HelloMessage):
        message_name = type(message).__name__
        raise RuntimeError(f"Expected Debug Helper hello message, got {message_name}")
    return message


class _UnavailableTransport:
    def request(self, command: bytes) -> DeviceMessage:
        raise DeviceCoreRuntimeError("Serial transport is not implemented yet")
