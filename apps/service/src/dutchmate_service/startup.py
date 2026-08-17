"""Device Core Service startup configuration helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Final, NoReturn, Protocol

from dutchmate_core.backends.basic import (
    BasicBackendConnection,
    BasicBackendEventSource,
    open_basic_backend_connection,
)
from dutchmate_core.backends.enhanced import (
    EnhancedCaptureEventSource,
    EnhancedDeviceControl,
    normalize_enhanced_hello,
)
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.device_connection.messages import HelloMessage
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
from dutchmate_core.session_store.store import (
    DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    SessionStore,
)

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
    status = runtime.status()
    if not status.connected or status.backend_mode == "basic":
        return False

    runtime.apply_hardware_config(config)
    return True


def build_startup_runtime(
    *,
    session_root: Path | str,
    session_evidence_budget_bytes: int = DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    backend_settings: BackendSettings | None = None,
) -> DeviceCoreRuntime:
    """Build the service runtime for one explicitly selected backend."""

    session_store = SessionStore(
        root=session_root,
        evidence_budget_bytes=session_evidence_budget_bytes,
    )
    session_store.recover_stale_sessions()

    if backend_settings is None:
        return DeviceCoreRuntime(
            device_control=_UnavailableDeviceControl(),
            session_store=session_store,
        )

    if backend_settings.mode == "basic":
        connection = open_basic_backend_connection(backend_settings)
        runtime = DeviceCoreRuntime(
            device_control=_UnavailableDeviceControl(connection),
            message_source=BasicBackendEventSource(connection, segment_id=0),
            session_store=session_store,
            port=connection.info.port,
            backend_mode="basic",
            tx_policy_enabled=backend_settings.tx_enabled,
            reconnect_timeout_s=backend_settings.reconnect_timeout_s,
        )
        runtime.record_backend_connection(connection.info)
        return runtime

    serial_port = backend_settings.serial_port
    if serial_port is None:
        return DeviceCoreRuntime(
            device_control=_UnavailableDeviceControl(),
            session_store=session_store,
            backend_mode="enhanced",
        )

    transport = open_serial_command_transport(
        port=serial_port,
        baudrate=backend_settings.baudrate,
    )
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        message_source=EnhancedCaptureEventSource(
            transport,
            segment_id=0,
            source_origin_us=None,
        ),
        session_store=session_store,
        port=serial_port,
        backend_mode="enhanced",
        tx_policy_enabled=backend_settings.tx_enabled,
        reconnect_timeout_s=backend_settings.reconnect_timeout_s,
    )
    hello = read_startup_hello(transport)
    runtime.record_backend_connection(normalize_enhanced_hello(hello, port=serial_port))
    return runtime


def read_startup_hello(transport: SerialCommandTransport) -> HelloMessage:
    """Read and validate the initial Debug Helper hello message."""

    message = transport.read_message()
    if not isinstance(message, HelloMessage):
        message_name = type(message).__name__
        raise RuntimeError(f"Expected Debug Helper hello message, got {message_name}")
    return message


class _UnavailableDeviceControl:
    def __init__(self, resource: BasicBackendConnection | None = None) -> None:
        self._resource = resource

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        role: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        self._raise_unavailable()

    def reset_dut(self, *, pulse_ms: int) -> int | None:
        self._raise_unavailable()

    def set_boot_mode(self, *, mode: str) -> int | None:
        self._raise_unavailable()

    def _raise_unavailable(self) -> NoReturn:
        if self._resource is not None:
            raise DeviceCoreRuntimeError("Basic backend does not support Debug Helper commands")
        raise DeviceCoreRuntimeError("Serial transport is not configured")
