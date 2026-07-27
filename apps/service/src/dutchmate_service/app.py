"""FastAPI application factory for the Device Core Service."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from fastapi import FastAPI

from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import (
    DeviceCoreRuntime,
    DeviceCoreRuntimeError,
    DeviceCoreStatus,
)
from dutchmate_core.workflows.device_actions import DeviceActionResult
from dutchmate_service.errors import register_error_handlers
from dutchmate_service.schemas import (
    BootModeRequest,
    GpioModeRequest,
    ResetRequest,
    device_action_payload,
    gpio_mode_payload,
    status_payload,
)
from dutchmate_service.startup import apply_startup_hardware_config


class RuntimeProvider(Protocol):
    """Runtime surface needed by the current service API."""

    def status(self) -> DeviceCoreStatus:
        """Return the current Device Core status."""

    def configure_gpio_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        idle_level: str | None = None,
    ) -> GpioControlChannelState:
        """Configure a control channel GPIO mode."""

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the configured DUT reset role."""

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set the configured DUT boot/control role."""

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[str, GpioControlChannelState]:
        """Apply startup hardware control mappings."""


def create_app(
    runtime: RuntimeProvider | None = None,
    *,
    session_root: Path | str = Path(".dutchmate/sessions"),
    hardware_config: HardwareGpioConfig | None = None,
) -> FastAPI:
    """Create the Device Core Service application."""

    app = FastAPI(title="DUTchMate Device Core Service")
    register_error_handlers(app)
    runtime_provider = runtime or DeviceCoreRuntime(
        transport=_UnavailableTransport(),
        session_root=session_root,
    )
    if hardware_config is not None:
        apply_startup_hardware_config(runtime_provider, hardware_config)

    @app.get("/status")
    def get_status() -> dict[str, object]:
        return status_payload(runtime_provider.status())

    @app.post("/gpio/mode")
    def configure_gpio_mode(request: GpioModeRequest) -> dict[str, object]:
        state = runtime_provider.configure_gpio_mode(
            role=request.role,
            channel=request.channel,
            dut_signal=request.dut_signal,
            mode=request.mode,
            active_level=request.active_level,
            idle_level=request.idle_level,
        )
        return gpio_mode_payload(state)

    @app.post("/dut/reset")
    def reset_dut(request: ResetRequest | None = None) -> dict[str, object]:
        if request is None:
            request = ResetRequest()
        return device_action_payload(runtime_provider.reset_dut(pulse_ms=request.pulse_ms))

    @app.post("/dut/boot-mode")
    def set_boot_mode(request: BootModeRequest) -> dict[str, object]:
        return device_action_payload(runtime_provider.set_boot_mode(mode=request.mode))

    return app


class _UnavailableTransport:
    def request(self, command: bytes) -> DeviceMessage:
        raise DeviceCoreRuntimeError("Serial transport is not implemented yet")
