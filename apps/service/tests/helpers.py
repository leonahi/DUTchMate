from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.modes import GpioControlChannelState, GpioModeRegistry
from dutchmate_core.runtime import DeviceCoreStatus
from dutchmate_core.session_store.models import (
    RecentLogs,
    SessionComparison,
    SessionComparisonError,
    SessionQueryError,
)
from dutchmate_core.session_store.store import SessionDetail, SessionListPage
from dutchmate_core.workflows.device_actions import DeviceActionResult
from dutchmate_core.workflows.uart_send import UartSendResult


class FakeRuntime:
    def __init__(self, status: DeviceCoreStatus) -> None:
        self._status = status
        self.gpio_mode_requests: list[dict[str, object]] = []
        self.reset_requests: list[int] = []
        self.boot_mode_requests: list[str] = []
        self.capture_requests: list[float] = []
        self.uart_send_requests: list[dict[str, object]] = []
        self.hardware_configs: list[HardwareGpioConfig] = []

    def status(self) -> DeviceCoreStatus:
        return self._status

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
        self.gpio_mode_requests.append(
            {
                "role": role,
                "channel": channel,
                "dut_signal": dut_signal,
                "mode": mode,
                "active_level": active_level,
                "idle_level": idle_level,
            }
        )
        return GpioControlChannelState(
            channel="CTRL0",
            state="configured",
            role=role,
            dut_signal=dut_signal,
            mode="open_drain",
            active_level="low",
            source="runtime",
            device_timestamp_us=182334400,
        )

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        self.reset_requests.append(pulse_ms)
        return DeviceActionResult(
            action="reset",
            pulse_ms=pulse_ms,
            performed_at="2026-08-21T10:00:00Z",
            device_timestamp_us=182334500,
        )

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        self.boot_mode_requests.append(mode)
        return DeviceActionResult(
            action="set_boot_mode",
            mode=mode,
            performed_at="2026-08-21T10:00:00Z",
            device_timestamp_us=182334600,
        )


    def send_uart(self, *, data_b64=None, text=None, line_ending=None) -> UartSendResult:
        from dutchmate_core.validation import prepare_uart_tx_payload

        payload = prepare_uart_tx_payload(data_b64=data_b64, text=text, line_ending=line_ending)
        self.uart_send_requests.append(
            {"data_b64": data_b64, "text": text, "line_ending": line_ending}
        )
        return UartSendResult(
            performed_at="2026-07-29T10:00:01Z",
            device_timestamp_us=182334700,
            attempt_id="attempt01",
            data_b64=payload.data_b64,
            transformation=payload.transformation(),
            accepted_bytes=len(payload.data),
            status="success",
            audit_status="recorded",
            attempt_session_id="session-one",
            attempt_evidence_seq=1,
            result_session_id="session-one",
            result_evidence_seq=2,
        )

    def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        del limit, cursor
        return SessionListPage(items=(), next_cursor=None)

    def get_session(self, session_id: str) -> SessionDetail:
        raise SessionQueryError(
            error="not_found",
            operation="get_session",
            session_id=session_id,
            detail=f"Session '{session_id}' was not found",
        )

    def compare_session(self, session_id: str) -> SessionComparison:
        raise SessionComparisonError(
            error="not_found",
            session_id=session_id,
            reason="baseline_not_designated",
            detail="No project baseline is designated",
        )

    def recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = 300,
    ) -> RecentLogs:
        del lines
        raise SessionQueryError(
            error="not_found",
            operation="get_logs",
            session_id=session_id,
            detail="No native active or terminal session is available",
        )

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[str, GpioControlChannelState]:
        self.hardware_configs.append(config)
        return {}


def connected_status() -> DeviceCoreStatus:
    registry = GpioModeRegistry()
    return DeviceCoreStatus(
        connected=True,
        port="/dev/ttyACM0",
        firmware="0.1.0",
        device="dutchmate-rp2350",
        capabilities=("gpio_control",),
        active_session_id=None,
        control_channels=registry.snapshot(),
        backend_mode="enhanced",
        backend_capabilities=("gpio_control", "uart_receive", "uart_send"),
        capability_policy=_tx_policy(),
        timestamp_provenance=_enhanced_segment(),
        integrity=_enhanced_integrity(),
        connection_state="connected",
    )


def disconnected_status() -> DeviceCoreStatus:
    registry = GpioModeRegistry()
    return DeviceCoreStatus(
        connected=False,
        port="/dev/ttyACM0",
        firmware=None,
        device=None,
        capabilities=(),
        active_session_id=None,
        control_channels=registry.snapshot(),
        backend_mode="enhanced",
        backend_capabilities=(),
        capability_policy=_tx_policy(),
        integrity=None,
        connection_state="disconnected",
    )


def _tx_policy() -> BackendCapabilityPolicy:
    return BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))


def _enhanced_integrity() -> UartIntegrity:
    return UartIntegrity(
        loss_status="none_reported",
        observation_scope="debug_helper_rx_buffer",
        dropped_bytes=0,
    )


def _enhanced_timestamp() -> SegmentTimestamp:
    return SegmentTimestamp(
        source="device",
        clock="rp2350_timer",
        unit="us",
        origin="segment_start",
        source_origin_us=100,
        observation_point="debug_helper_uart_receive",
        event_granularity="uart_event",
    )


def _enhanced_segment() -> SegmentContext:
    return SegmentContext(segment_id=0, timestamp=_enhanced_timestamp())
