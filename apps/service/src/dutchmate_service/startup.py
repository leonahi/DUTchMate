"""Device Core Service startup configuration helpers."""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import suppress
from pathlib import Path
from typing import Final, NoReturn, Protocol

from dutchmate_core.backends.basic import (
    BasicBackendConnection,
    BasicBackendEventSource,
    open_basic_backend_connection,
)
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.serial_transport import SerialCommandTransport
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
from dutchmate_service.backend_reconnect import (
    ReplaceableDeviceControl,
    ReplaceableUartSender,
    backend_snapshot,
    build_basic_capture_reconnect,
    build_enhanced_capture_reconnect,
    read_enhanced_hello,
)
from dutchmate_service.continuous_ingestion import ContinuousIngestionCoordinator
from dutchmate_service.enhanced_async import open_enhanced_async_host

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
    session_max_count: int | None = None,
    backend_settings: BackendSettings | None = None,
    monotonic_clock: Callable[[], float] | None = None,
    sleep: Callable[[float], None] | None = None,
) -> DeviceCoreRuntime:
    """Build the service runtime for one explicitly selected backend."""

    session_store = SessionStore(
        root=session_root,
        evidence_budget_bytes=session_evidence_budget_bytes,
        max_count=session_max_count,
    )
    session_store.recover_stale_sessions()
    reconnect_clock = monotonic_clock or time.monotonic
    reconnect_sleep = sleep or time.sleep

    if backend_settings is None:
        return DeviceCoreRuntime(
            device_control=_UnavailableDeviceControl(),
            session_store=session_store,
            capture_clock=monotonic_clock,
        )

    if backend_settings.mode == "basic":
        connection = open_basic_backend_connection(backend_settings)
        basic_source = BasicBackendEventSource(connection, segment_id=0)
        initial_snapshot = basic_source.snapshot
        coordinator = ContinuousIngestionCoordinator(
            basic_source,
            backend_snapshot=initial_snapshot,
        )
        reconnect = None
        try:
            sender = ReplaceableUartSender(connection)
            control = ReplaceableDeviceControl(_UnavailableDeviceControl(connection))
            reconnect = build_basic_capture_reconnect(
                settings=backend_settings,
                source_owner=coordinator,
                expected_snapshot=initial_snapshot,
                open_connection=open_basic_backend_connection,
                sender=sender,
                monotonic_clock=reconnect_clock,
                sleep=reconnect_sleep,
            )
            runtime = DeviceCoreRuntime(
                device_control=control,
                uart_sender=sender,
                message_source=coordinator,
                session_store=session_store,
                capture_clock=monotonic_clock,
                port=connection.info.port,
                backend_mode="basic",
                tx_policy_enabled=backend_settings.tx_enabled,
                reconnect_timeout_s=backend_settings.reconnect_timeout_s,
                backend_reconnect=reconnect,
            )
            runtime.record_backend_connection(initial_snapshot.info)
            reconnect.start()
        except BaseException:
            if reconnect is not None:
                with suppress(BaseException):
                    reconnect.close()
            with suppress(BaseException):
                coordinator.close()
            raise
        return runtime

    serial_port = backend_settings.serial_port
    if serial_port is None:
        return DeviceCoreRuntime(
            device_control=_UnavailableDeviceControl(),
            session_store=session_store,
            backend_mode="enhanced",
            capture_clock=monotonic_clock,
        )

    enhanced_host = open_enhanced_async_host(
        port=serial_port,
        baudrate=backend_settings.baudrate,
        segment_id=0,
    )
    initial_snapshot = backend_snapshot(
        info=enhanced_host.info,
        segment=enhanced_host.segment,
        tx_enabled=backend_settings.tx_enabled,
    )
    coordinator = ContinuousIngestionCoordinator(
        enhanced_host,
        backend_snapshot=initial_snapshot,
    )
    reconnect = None
    try:
        control = ReplaceableDeviceControl(enhanced_host)
        sender = ReplaceableUartSender(enhanced_host)
        reconnect = build_enhanced_capture_reconnect(
            settings=backend_settings,
            source_owner=coordinator,
            expected_info=initial_snapshot.info,
            expected_snapshot=initial_snapshot,
            control=control,
            sender=sender,
            open_host=open_enhanced_async_host,
            monotonic_clock=reconnect_clock,
            sleep=reconnect_sleep,
        )
        runtime = DeviceCoreRuntime(
            device_control=control,
            uart_sender=sender,
            message_source=coordinator,
            session_store=session_store,
            capture_clock=monotonic_clock,
            port=serial_port,
            backend_mode="enhanced",
            tx_policy_enabled=backend_settings.tx_enabled,
            reconnect_timeout_s=backend_settings.reconnect_timeout_s,
            backend_reconnect=reconnect,
        )
        runtime.record_backend_connection(initial_snapshot.info)
        reconnect.start()
    except BaseException:
        if reconnect is not None:
            with suppress(BaseException):
                reconnect.close()
        with suppress(BaseException):
            coordinator.close()
        raise
    return runtime


def read_startup_hello(transport: SerialCommandTransport) -> HelloMessage:
    """Read and validate the initial Debug Helper hello message."""

    return read_enhanced_hello(transport)


class _UnavailableDeviceControl:
    def __init__(self, resource: BasicBackendConnection | None = None) -> None:
        self._resource = resource

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        self._raise_unavailable()

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        self._raise_unavailable()

    def set_control_state(self, *, channel: str, state: ControlState) -> int | None:
        self._raise_unavailable()

    def _raise_unavailable(self) -> NoReturn:
        if self._resource is not None:
            raise DeviceCoreRuntimeError("Basic backend does not support Debug Helper commands")
        raise DeviceCoreRuntimeError("Serial transport is not configured")
