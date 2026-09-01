import pytest

from dutchmate_core.backends import DeviceControlError
from dutchmate_core.backends.contracts import ControlState
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.gpio_config.configurator import GpioConfigurator
from dutchmate_core.gpio_config.modes import GpioConfigurationError, GpioModeRegistry
from dutchmate_core.validation import InputValidationError


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
        self.calls.append(
            (
                "configure_gpio_mode",
                {
                    "channel": channel,
                    "mode": mode,
                    "active_level": active_level,
                    "idle_level": idle_level,
                },
            )
        )
        return self._timestamp()

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        raise AssertionError(f"unexpected pulse: {channel=} {pulse_ms=}")

    def set_control_state(self, *, channel: str, state: ControlState) -> int | None:
        raise AssertionError(f"unexpected state change: {channel=} {state=}")

    def _timestamp(self) -> int | None:
        if isinstance(self.response, CommandSuccessMessage):
            return self.response.timestamp_us
        if isinstance(self.response, CommandErrorMessage):
            raise DeviceControlError(
                error=self.response.error,
                detail=self.response.detail,
            )
        raise DeviceControlError(
            error="unexpected_response",
            detail=(
                "Expected command response for GPIO mode configuration, "
                f"got {type(self.response).__name__}"
            ),
        )


def test_configure_mode_sends_command_and_accepts_success() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage(timestamp_us=182334400))
    configurator = GpioConfigurator(registry=registry, control=control)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert control.calls == [
        (
            "configure_gpio_mode",
            {
                "channel": "CTRL0",
                "mode": "open_drain",
                "active_level": "low",
                "idle_level": None,
            },
        )
    ]
    assert state.state == "configured"
    assert state.role == "reset"
    assert state.channel == "CTRL0"
    assert state.dut_signal == "RESET_N"
    assert state.mode == "open_drain"
    assert state.active_level == "low"
    assert state.source == "runtime"
    assert state.device_timestamp_us == 182334400
    assert registry.get("CTRL0") == state


def test_configure_mode_accepts_boot_role_with_idle_level() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    state = configurator.configure_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="config",
    )

    assert control.calls == [
        (
            "configure_gpio_mode",
            {
                "channel": "CTRL1",
                "mode": "push_pull",
                "active_level": "high",
                "idle_level": "low",
            },
        )
    ]
    assert state.state == "configured"
    assert state.role == "boot"
    assert state.channel == "CTRL1"
    assert state.dut_signal == "BOOT0"
    assert state.mode == "push_pull"
    assert state.active_level == "high"
    assert state.idle_level == "low"
    assert state.source == "config"
    assert state.device_timestamp_us is None


def test_configure_mode_records_firmware_rejection() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(
        CommandErrorMessage(
            error="invalid_argument",
            detail="push_pull is not supported for reset",
        )
    )
    configurator = GpioConfigurator(registry=registry, control=control)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
    )

    assert control.calls == [
        (
            "configure_gpio_mode",
            {
                "channel": "CTRL0",
                "mode": "push_pull",
                "active_level": "low",
                "idle_level": "high",
            },
        )
    ]
    assert state.state == "rejected"
    assert state.last_rejected is not None
    assert state.last_rejected.error == "invalid_argument"
    assert state.last_rejected.detail == "push_pull is not supported for reset"
    assert state.last_rejected.channel == "CTRL0"
    assert state.last_rejected.dut_signal == "RESET_N"
    assert registry.get("CTRL0") == state


def test_configure_mode_rejection_preserves_previous_accepted_mode() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
    )
    control = FakeDeviceControl(
        CommandErrorMessage(
            error="invalid_argument",
            detail="push_pull is not supported for reset",
        )
    )
    configurator = GpioConfigurator(registry=registry, control=control)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        idle_level="high",
        source="runtime",
    )

    assert state.state == "configured"
    assert state.channel == "CTRL0"
    assert state.dut_signal == "RESET_N"
    assert state.mode == "open_drain"
    assert state.source == "config"
    assert state.last_rejected is not None
    assert state.last_rejected.mode == "push_pull"


def test_invalid_channel_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="GPIO control channel"):
        configurator.configure_mode(
            role="reset",
            channel="GPIO0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert control.calls == []
    assert registry.get("CTRL0").state == "unconfigured"
    assert registry.get("CTRL1").state == "unconfigured"


def test_custom_role_is_recorded_but_not_sent() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    state = configurator.configure_mode(
        role="power_en",
        channel="CTRL2",
        dut_signal="PMIC_EN",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="runtime",
    )

    assert control.calls == [
        (
            "configure_gpio_mode",
            {
                "channel": "CTRL2",
                "mode": "push_pull",
                "active_level": "high",
                "idle_level": "low",
            },
        )
    ]
    assert state.state == "configured"
    assert state.role == "power_en"
    assert registry.get("CTRL2") == state


def test_empty_role_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="GPIO role"):
        configurator.configure_mode(
            role=" ",
            channel="CTRL0",
            dut_signal="PMIC_EN",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert control.calls == []
    assert registry.get("CTRL0").state == "unconfigured"
    assert registry.get("CTRL1").state == "unconfigured"


def test_invalid_dut_signal_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="dut_signal"):
        configurator.configure_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET\x00N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert control.calls == []


def test_invalid_mode_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, control=control)

    with pytest.raises(InputValidationError, match="GPIO mode"):
        configurator.configure_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="floating",
            active_level="low",
            source="runtime",
        )

    assert control.calls == []
    assert registry.get("CTRL0").state == "unconfigured"


def test_unexpected_response_does_not_update_registry() -> None:
    registry = GpioModeRegistry()
    control = FakeDeviceControl(
        HelloMessage(
            firmware="0.1.0",
            device="debug-helper",
            capabilities=("uart_receive", "gpio_control"),
        )
    )
    configurator = GpioConfigurator(registry=registry, control=control)

    with pytest.raises(GpioConfigurationError, match="Expected command response"):
        configurator.configure_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert control.calls == [
        (
            "configure_gpio_mode",
            {
                "channel": "CTRL0",
                "mode": "open_drain",
                "active_level": "low",
                "idle_level": None,
            },
        )
    ]
    assert registry.get("CTRL0").state == "unconfigured"
