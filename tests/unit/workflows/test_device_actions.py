import pytest

from dutchmate_core.backends.enhanced import EnhancedDeviceControl
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


class FakeTransport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> object:
        self.requests.append(command)
        return self.response


def test_reset_requires_configured_reset_role() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(GpioConfigurationError, match="not configured"):
        runner.reset_dut()

    assert transport.requests == []


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
    transport = FakeTransport(CommandSuccessMessage(timestamp_us=182334400))
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    result = runner.reset_dut(pulse_ms=250)

    assert result == DeviceActionResult(action="reset", timestamp_us=182334400)
    assert transport.requests == [b'{"cmd":"reset","pulse_ms":250}\n']


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
    transport = FakeTransport(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(GpioConfigurationError, match="push_pull is not supported"):
        runner.reset_dut()

    assert transport.requests == []


def test_reset_validates_pulse_before_configuration_check() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(InputValidationError, match="pulse_ms"):
        runner.reset_dut(pulse_ms=0)

    assert transport.requests == []


def test_boot_mode_requires_configured_boot_role() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(GpioConfigurationError, match="not configured"):
        runner.set_boot_mode(mode="bootloader")

    assert transport.requests == []


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
    transport = FakeTransport(CommandSuccessMessage(timestamp_us=99))
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    result = runner.set_boot_mode(mode="bootloader")

    assert result == DeviceActionResult(action="set_boot_mode", timestamp_us=99)
    assert transport.requests == [b'{"cmd":"set_boot_mode","mode":"bootloader"}\n']


def test_boot_mode_validates_mode_before_configuration_check() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(InputValidationError, match="Boot mode"):
        runner.set_boot_mode(mode="factory")

    assert transport.requests == []


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
    transport = FakeTransport(
        CommandErrorMessage(
            error="hardware_fault",
            detail="reset driver failed",
        )
    )
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(DeviceActionError, match="reset driver failed") as exc_info:
        runner.reset_dut()

    assert exc_info.value.error == "hardware_fault"
    assert exc_info.value.detail == "reset driver failed"
    assert transport.requests == [b'{"cmd":"reset","pulse_ms":100}\n']


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
    transport = FakeTransport(
        HelloMessage(
            firmware="0.1.0",
            device="debug-helper",
            capabilities=("uart_capture", "gpio_control"),
        )
    )
    runner = DeviceActionRunner(registry=registry, control=EnhancedDeviceControl(transport))

    with pytest.raises(DeviceActionError, match="Expected command response"):
        runner.reset_dut()

    assert transport.requests == [b'{"cmd":"reset","pulse_ms":100}\n']
