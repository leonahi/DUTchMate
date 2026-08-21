"""FastAPI application factory for the Device Core Service."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated, Protocol

from fastapi import FastAPI, Query

from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import (
    DeviceCoreStatus,
)
from dutchmate_core.session_store.store import (
    DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    BaselineMutationResult,
    RecentLogs,
    SessionComparison,
    SessionDetail,
    SessionListPage,
    SessionSummary,
    WaitPatternResult,
)
from dutchmate_core.workflows.device_actions import DeviceActionResult
from dutchmate_core.workflows.uart_send import UartSendResult
from dutchmate_service.errors import register_error_handlers
from dutchmate_service.schemas import (
    BootModeRequest,
    BootTestRequest,
    CaptureRequest,
    GpioModeRequest,
    ResetRequest,
    UartSendRequest,
    WaitPatternRequest,
    baseline_mutation_payload,
    capture_summary_payload,
    device_action_payload,
    gpio_mode_payload,
    recent_logs_payload,
    session_comparison_payload,
    session_detail_payload,
    session_list_payload,
    status_payload,
    uart_send_payload,
    wait_pattern_payload,
)
from dutchmate_service.startup import apply_startup_hardware_config, build_startup_runtime


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

    def capture_uart(self, *, duration_s: float) -> SessionSummary:
        """Capture UART and telemetry messages into a session."""

    def run_boot_test(self, *, duration_s: float) -> SessionSummary:
        """Reset the DUT and capture boot evidence into a session."""

    def wait_pattern(self, *, pattern: str, timeout_s: float) -> WaitPatternResult:
        """Wait for one literal in new UART evidence."""

    def send_uart(
        self,
        *,
        cmd: str,
        append_newline: bool = True,
        force: bool = False,
    ) -> UartSendResult:
        """Send one validated text command to the DUT UART."""

    def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        """Return one bounded newest-first session page."""

    def get_session(self, session_id: str) -> SessionDetail:
        """Return bounded schema-aware detail for one session."""

    def recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = 300,
    ) -> RecentLogs:
        """Return bounded recent UART replay for one selected session."""

    def mark_baseline(self, session_id: str) -> BaselineMutationResult:
        """Designate one eligible session as the project baseline."""

    def clear_baseline(self, session_id: str) -> BaselineMutationResult:
        """Clear the baseline only when it names the requested session."""

    def compare_session(self, session_id: str) -> SessionComparison:
        """Compare one terminal session with the designated baseline."""

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[str, GpioControlChannelState]:
        """Apply startup hardware control mappings."""


def create_app(
    runtime: RuntimeProvider | None = None,
    *,
    session_root: Path | str = Path(".dutchmate/sessions"),
    session_evidence_budget_bytes: int = DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    session_max_count: int | None = None,
    hardware_config: HardwareGpioConfig | None = None,
    backend_settings: BackendSettings | None = None,
) -> FastAPI:
    """Create the Device Core Service application."""

    app = FastAPI(title="DUTchMate Device Core Service")
    register_error_handlers(app)
    runtime_provider = runtime or build_startup_runtime(
        session_root=session_root,
        session_evidence_budget_bytes=session_evidence_budget_bytes,
        session_max_count=session_max_count,
        backend_settings=backend_settings,
    )
    if hardware_config is not None:
        apply_startup_hardware_config(runtime_provider, hardware_config)

    @app.get("/status")
    def get_status() -> dict[str, object]:
        return status_payload(runtime_provider.status())

    @app.get("/sessions")
    def list_sessions(
        limit: Annotated[int, Query(ge=1, le=100)] = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        page = runtime_provider.list_sessions(limit=limit, cursor=cursor)
        return session_list_payload(page)

    @app.get("/sessions/{session_id}")
    def get_session(session_id: str) -> dict[str, object]:
        return session_detail_payload(runtime_provider.get_session(session_id))

    @app.post("/sessions/{session_id}/baseline")
    def mark_baseline(session_id: str) -> dict[str, object]:
        return baseline_mutation_payload(runtime_provider.mark_baseline(session_id))

    @app.delete("/sessions/{session_id}/baseline")
    def clear_baseline(session_id: str) -> dict[str, object]:
        return baseline_mutation_payload(runtime_provider.clear_baseline(session_id))

    @app.get("/sessions/{session_id}/compare")
    def compare_session(session_id: str) -> dict[str, object]:
        return session_comparison_payload(runtime_provider.compare_session(session_id))

    @app.get("/dut/logs")
    def get_recent_logs(
        session_id: str | None = None,
        lines: Annotated[int, Query(ge=1, le=1000)] = 300,
    ) -> dict[str, object]:
        return recent_logs_payload(
            runtime_provider.recent_logs(session_id=session_id, lines=lines)
        )

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

    @app.post("/dut/capture")
    def capture_uart(request: CaptureRequest) -> dict[str, object]:
        summary = runtime_provider.capture_uart(duration_s=request.duration_s)
        return capture_summary_payload(summary)

    @app.post("/dut/boot-test")
    def run_boot_test(request: BootTestRequest) -> dict[str, object]:
        summary = runtime_provider.run_boot_test(duration_s=request.duration_s)
        return capture_summary_payload(summary)

    @app.post("/dut/wait-pattern")
    def wait_pattern(request: WaitPatternRequest) -> dict[str, object]:
        return wait_pattern_payload(
            runtime_provider.wait_pattern(
                pattern=request.pattern,
                timeout_s=request.timeout_s,
            )
        )

    @app.post("/dut/uart/send")
    def send_uart(request: UartSendRequest) -> dict[str, object]:
        return uart_send_payload(
            runtime_provider.send_uart(
                cmd=request.cmd,
                append_newline=request.append_newline,
                force=request.force,
            )
        )

    return app
