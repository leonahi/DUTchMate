from dutchmate_core.gpio_config.modes import GpioControlChannelState, GpioModeRegistry
from dutchmate_core.runtime import DeviceCoreStatus
from dutchmate_core.workflows.device_actions import DeviceActionResult


class FakeRuntime:
    def __init__(self, status: DeviceCoreStatus) -> None:
        self._status = status
        self.gpio_mode_requests: list[dict[str, object]] = []
        self.reset_requests: list[int] = []
        self.boot_mode_requests: list[str] = []

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
    )
