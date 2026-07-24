"""Service-facing Device Core runtime composition."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TypeAlias

from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.transport import CommandTransport
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.configurator import GpioConfigurator
from dutchmate_core.gpio_config.modes import (
    GpioControlChannel,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRequestSource,
    GpioRoleName,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.device_actions import (
    DeviceActionResult,
    DeviceActionRunner,
)

DeviceCoreTransport: TypeAlias = CommandTransport


class DeviceCoreRuntimeError(RuntimeError):
    """Raised when the runtime cannot perform the requested operation."""


@dataclass(frozen=True, slots=True)
class DeviceCoreStatus:
    """Current service-facing Device Core state."""

    connected: bool
    port: str | None
    firmware: str | None
    device: str | None
    capabilities: tuple[str, ...]
    active_session_id: str | None
    control_channels: dict[GpioControlChannel, GpioControlChannelState]


class DeviceCoreRuntime:
    """Compose Phase 1 core services behind one service-facing object."""

    def __init__(
        self,
        *,
        transport: DeviceCoreTransport,
        session_store: SessionStore | None = None,
        session_root: Path | str = Path(".dutchmate/sessions"),
        gpio_registry: GpioModeRegistry | None = None,
        port: str | None = None,
    ) -> None:
        self._transport = transport
        self._session_store = session_store or SessionStore(root=session_root)
        self._gpio_registry = gpio_registry or GpioModeRegistry()
        self._gpio_configurator = GpioConfigurator(
            registry=self._gpio_registry,
            transport=self._transport,
        )
        self._action_runner = DeviceActionRunner(
            registry=self._gpio_registry,
            transport=self._transport,
        )
        self._port = port
        self._hello: HelloMessage | None = None
        self._active_session_id: str | None = None

    @property
    def session_store(self) -> SessionStore:
        """Filesystem-backed session store used by this runtime."""

        return self._session_store

    @property
    def gpio_registry(self) -> GpioModeRegistry:
        """GPIO role configuration state used by this runtime."""

        return self._gpio_registry

    def record_hello(self, hello: HelloMessage, *, port: str | None = None) -> DeviceCoreStatus:
        """Record a validated Debug Helper hello message."""

        self._hello = hello
        if port is not None:
            self._port = port
        return self.status()

    def disconnect(self) -> DeviceCoreStatus:
        """Mark the Debug Helper connection as disconnected."""

        self._hello = None
        return self.status()

    def status(self) -> DeviceCoreStatus:
        """Return the current service-facing status snapshot."""

        return DeviceCoreStatus(
            connected=self._hello is not None,
            port=self._port,
            firmware=self._hello.firmware if self._hello is not None else None,
            device=self._hello.device if self._hello is not None else None,
            capabilities=self._hello.capabilities if self._hello is not None else (),
            active_session_id=self._active_session_id,
            control_channels=self._gpio_registry.snapshot(),
        )

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[GpioRoleName, GpioControlChannelState]:
        """Apply configured GPIO modes after a Debug Helper hello is available."""

        self._require_connected()
        applied: dict[GpioRoleName, GpioControlChannelState] = {}
        for mapping in config.controls.values():
            applied[mapping.role] = self.configure_gpio_mode(
                role=mapping.role,
                channel=mapping.channel,
                dut_signal=mapping.dut_signal,
                mode=mapping.mode,
                active_level=mapping.active_level,
                idle_level=mapping.idle_level,
                source="config",
            )
        return applied

    def configure_gpio_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        source: GpioModeRequestSource = "runtime",
        idle_level: str | None = None,
    ) -> GpioControlChannelState:
        """Configure one GPIO role through firmware and update runtime state."""

        self._require_connected()
        if source not in {"config", "runtime"}:
            raise DeviceCoreRuntimeError("GPIO configuration source must be 'config' or 'runtime'")
        return self._gpio_configurator.configure_mode(
            role=role,
            channel=channel,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
            source=source,
        )

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the configured DUT reset role."""

        self._require_connected()
        return self._action_runner.reset_dut(pulse_ms=pulse_ms)

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set the configured DUT boot/control role."""

        self._require_connected()
        return self._action_runner.set_boot_mode(mode=mode)

    def _require_connected(self) -> None:
        if self._hello is None:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")
