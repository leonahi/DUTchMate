from datetime import datetime, timezone

import pytest

from dutchmate_core.backends import DeviceControlError
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.gpio_config.modes import GpioConfigurationError, GpioModeRegistry
from dutchmate_core.validation import InputValidationError
from dutchmate_core.workflows.device_actions import (
    DeviceActionError,
    DeviceActionResult,
    DeviceActionRunner,
)


class FakeDeviceControl:
    def __init__(self, response: object) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, object]]] = []

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        raise AssertionError(
            f"unexpected configuration: {channel=} {mode=} {active_level=} {idle_level=}"
        )

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        self.calls.append(("pulse_control", {"channel": channel, "pulse_ms": pulse_ms}))
        return self._timestamp("reset")

    def set_control_state(self, *, channel: str, state: ControlState) -> int | None:
        self.calls.append(("set_control_state", {"channel": channel, "state": state}))
        return self._timestamp("set_boot_mode")

    def _timestamp(self, operation: str) -> int | None:
        if isinstance(self.response, CommandSuccessMessage):
            return self.response.timestamp_us
        if isinstance(self.response, CommandErrorMessage):
            raise DeviceControlError(
                error=self.response.error,
                detail=self.response.detail,
            )
        if isinstance(self.response, DeviceControlError):
            raise self.response
        raise DeviceControlError(
            error="unexpected_response",
            detail=(
                f"Expected command response for {operation}, "
                f"got {type(self.response).__name__}"
            ),
        )


def test_reset_requires_configured_reset_role() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    runner = DeviceActionRunner(
        registry=registry,
        control=control,
        wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(GpioConfigurationError, match="not configured"):
        runner.reset_dut()

    assert control.calls == []


def test_reset_sends_command_after_reset_role_is_configured() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )
    control = FakeDeviceControl(CommandSuccessMessage(timestamp_us=182334400))
    runner = DeviceActionRunner(
        registry=registry,
        control=control,
        wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )

    result = runner.reset_dut(pulse_ms=250)

    assert result == DeviceActionResult(
        action="reset",
        pulse_ms=250,
        performed_at="2026-08-21T10:00:00Z",
        device_timestamp_us=182334400,
    )
    assert control.calls == [
        ("pulse_control", {"channel": "CTRL0", "pulse_ms": 250})
    ]


def test_reset_rejected_state_uses_rejection_detail() -> None:
    registry = GpioModeRegistry()
    registry.reject_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
        error="invalid_argument",
        detail="push_pull is not supported for reset",
    )
    control = FakeDeviceControl(CommandSuccessMessage())
    runner = DeviceActionRunner(
        registry=registry,
        control=control,
        wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )

    with pytest.raises(GpioConfigurationError, match="push_pull is not supported") as exc_info:
        runner.reset_dut()

    assert exc_info.value.operation == "reset"
    assert exc_info.value.required_role == "reset"
    assert exc_info.value.role_state == "rejected"
    assert control.calls == []


def test_reset_validates_pulse_before_configuration_check() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="pulse_ms"):
        runner.reset_dut(pulse_ms=0)

    assert control.calls == []


def test_boot_mode_requires_configured_boot_role() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=control)

    with pytest.raises(GpioConfigurationError, match="not configured") as exc_info:
        runner.set_boot_mode(mode="bootloader")

    assert exc_info.value.operation == "set_boot_mode"
    assert exc_info.value.required_role == "boot"
    assert exc_info.value.role_state == "unconfigured"
    assert control.calls == []


def test_boot_mode_sends_command_after_boot_role_is_configured() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )
    control = FakeDeviceControl(CommandSuccessMessage(timestamp_us=99))
    runner = DeviceActionRunner(
        registry=registry,
        control=control,
        wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )

    result = runner.set_boot_mode(mode="bootloader")

    assert result == DeviceActionResult(
        action="set_boot_mode",
        mode="bootloader",
        performed_at="2026-08-21T10:00:00Z",
        device_timestamp_us=99,
    )
    assert control.calls == [
        ("set_control_state", {"channel": "CTRL1", "state": "active"})
    ]


def test_normal_boot_mode_restores_configured_boot_channel_idle_state() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="boot",
        channel="CTRL3",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="runtime",
    )
    control = FakeDeviceControl(CommandSuccessMessage(timestamp_us=100))
    runner = DeviceActionRunner(
        registry=registry,
        control=control,
        wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )

    result = runner.set_boot_mode(mode="normal")

    assert result.mode == "normal"
    assert control.calls == [
        ("set_control_state", {"channel": "CTRL3", "state": "idle"})
    ]


def test_boot_mode_validates_mode_before_configuration_check() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="Boot mode"):
        runner.set_boot_mode(mode="factory")

    assert control.calls == []


@pytest.mark.parametrize(
    "result",
    [
        {
            "action": "reset",
            "performed_at": "2026-08-21T10:00:00Z",
            "mode": "normal",
        },
        {
            "action": "set_boot_mode",
            "performed_at": "2026-08-21T10:00:00Z",
            "pulse_ms": 100,
        },
    ],
)
def test_action_result_rejects_mismatched_accepted_fields(result: dict[str, object]) -> None:
    with pytest.raises(ValueError, match="results require"):
        DeviceActionResult(**result)  # type: ignore[arg-type]


def test_command_error_response_raises_device_action_error() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )
    control = FakeDeviceControl(
        CommandErrorMessage(
            error="hardware_fault",
            detail="reset driver failed",
        )
    )
    runner = DeviceActionRunner(registry=registry, control=control)

    with pytest.raises(DeviceActionError, match="reset driver failed") as exc_info:
        runner.reset_dut()

    assert exc_info.value.error == "hardware_fault"
    assert exc_info.value.detail == "reset driver failed"
    assert control.calls == [
        ("pulse_control", {"channel": "CTRL0", "pulse_ms": 100})
    ]


def test_unexpected_response_raises_device_action_error() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )
    control = FakeDeviceControl(
        HelloMessage(
            firmware="0.1.0",
            device="debug-helper",
            capabilities=("uart_receive", "gpio_control"),
        )
    )
    runner = DeviceActionRunner(registry=registry, control=control)

    with pytest.raises(DeviceActionError, match="Expected command response"):
        runner.reset_dut()

    assert control.calls == [
        ("pulse_control", {"channel": "CTRL0", "pulse_ms": 100})
    ]


def test_transport_timeout_raises_typed_device_action_error() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )
    runner = DeviceActionRunner(
        registry=registry,
        control=FakeDeviceControl(
            DeviceControlError(error="timeout", detail="Timed out waiting for reset response")
        ),
    )

    with pytest.raises(DeviceActionError, match="Timed out") as exc_info:
        runner.reset_dut()

    assert exc_info.value.error == "timeout"
