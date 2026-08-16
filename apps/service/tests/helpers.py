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
from dutchmate_core.session_store.store import SessionSummary
from dutchmate_core.workflows.device_actions import DeviceActionResult


class FakeRuntime:
    def __init__(self, status: DeviceCoreStatus) -> None:
        self._status = status
        self.gpio_mode_requests: list[dict[str, object]] = []
        self.reset_requests: list[int] = []
        self.boot_mode_requests: list[str] = []
        self.capture_requests: list[float] = []
        self.boot_test_requests: list[float] = []
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
        return DeviceActionResult(action="reset", timestamp_us=182334500)

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        self.boot_mode_requests.append(mode)
        return DeviceActionResult(action="set_boot_mode", timestamp_us=182334600)

    def capture_uart(self, *, duration_s: float) -> SessionSummary:
        self.capture_requests.append(duration_s)
        return SessionSummary(
            session_id="20260729T100000Z-capture01",
            started_at="2026-07-29T10:00:00Z",
            command=f"capture --seconds {duration_s:g}",
            truncated=False,
            interrupted=False,
            resumed=False,
            overflow=False,
            baseline=False,
            firmware="0.1.0",
            device="dutchmate-rp2040",
            segment_count=1,
            backend_mode="enhanced",
            port="/dev/ttyACM0",
            backend_capabilities=("gpio_control", "uart_receive", "uart_send"),
            capabilities=("gpio_control", "uart_receive"),
            capability_policy=_tx_policy(),
            integrity=_enhanced_integrity(),
            segment_contexts=(_enhanced_segment(),),
            schema_version=1,
            state="completed",
            workflow="capture",
            duration_s=duration_s,
            reconnect_timeout_s=5.0,
            ended_at="2026-07-29T10:00:03Z",
            end_reason="duration_elapsed",
        )

    def run_boot_test(self, *, duration_s: float) -> SessionSummary:
        self.boot_test_requests.append(duration_s)
        return SessionSummary(
            session_id="20260729T100000Z-boot01",
            started_at="2026-07-29T10:00:00Z",
            command=f"boot-test --seconds {duration_s:g}",
            truncated=False,
            interrupted=False,
            resumed=False,
            overflow=False,
            baseline=False,
            firmware="0.1.0",
            device="dutchmate-rp2040",
            segment_count=1,
            backend_mode="enhanced",
            port="/dev/ttyACM0",
            backend_capabilities=("gpio_control", "uart_receive", "uart_send"),
            capabilities=("gpio_control", "uart_receive"),
            capability_policy=_tx_policy(),
            integrity=_enhanced_integrity(),
            segment_contexts=(_enhanced_segment(),),
            schema_version=1,
            state="completed",
            workflow="boot_test",
            duration_s=duration_s,
            reconnect_timeout_s=5.0,
            ended_at="2026-07-29T10:00:03Z",
            end_reason="duration_elapsed",
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
        device="dutchmate-rp2040",
        capabilities=("gpio_control",),
        active_session_id=None,
        control_channels=registry.snapshot(),
        backend_mode="enhanced",
        backend_capabilities=("gpio_control", "uart_receive", "uart_send"),
        capability_policy=_tx_policy(),
        timestamp_provenance=_enhanced_segment(),
        integrity=_enhanced_integrity(),
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
        clock="rp2040_timer",
        unit="us",
        origin="segment_start",
        source_origin_us=100,
        observation_point="debug_helper_uart_receive",
        event_granularity="uart_event",
    )


def _enhanced_segment() -> SegmentContext:
    return SegmentContext(segment_id=0, timestamp=_enhanced_timestamp())
