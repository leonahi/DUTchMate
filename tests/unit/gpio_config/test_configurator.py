import pytest

from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.gpio_config.configurator import GpioConfigurator
from dutchmate_core.gpio_config.modes import GpioConfigurationError, GpioModeRegistry


class FakeTransport:
    def __init__(self, response: object) -> None:
        self.response = response
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> object:
        self.requests.append(command)
        return self.response


def test_configure_mode_sends_command_and_accepts_success() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage(timestamp_us=182334400))
    configurator = GpioConfigurator(registry=registry, transport=transport)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n'
    ]
    assert state.state == "configured"
    assert state.role == "reset"
    assert state.channel == "CTRL0"
    assert state.dut_signal == "RESET_N"
    assert state.mode == "open_drain"
    assert state.active_level == "low"
    assert state.source == "runtime"
    assert state.device_timestamp_us == 182334400
    assert registry.get("reset") == state


def test_configure_mode_accepts_boot_role_with_idle_level() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, transport=transport)

    state = configurator.configure_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        source="config",
    )

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL1","role":"boot",'
        b'"mode":"push_pull","active_level":"high","idle_level":"low"}\n'
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
    transport = FakeTransport(
        CommandErrorMessage(
            error="invalid_argument",
            detail="push_pull is not supported for reset",
        )
    )
    configurator = GpioConfigurator(registry=registry, transport=transport)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
        source="runtime",
    )

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"push_pull","active_level":"low"}\n'
    ]
    assert state.state == "rejected"
    assert state.last_rejected is not None
    assert state.last_rejected.error == "invalid_argument"
    assert state.last_rejected.detail == "push_pull is not supported for reset"
    assert state.last_rejected.channel == "CTRL0"
    assert state.last_rejected.dut_signal == "RESET_N"
    assert registry.get("reset") == state


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
    transport = FakeTransport(
        CommandErrorMessage(
            error="invalid_argument",
            detail="push_pull is not supported for reset",
        )
    )
    configurator = GpioConfigurator(registry=registry, transport=transport)

    state = configurator.configure_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="push_pull",
        active_level="low",
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
    transport = FakeTransport(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, transport=transport)

    with pytest.raises(ProtocolValidationError, match="GPIO control channel"):
        configurator.configure_mode(
            role="reset",
            channel="GPIO0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert transport.requests == []
    assert registry.get("reset").state == "unconfigured"
    assert registry.get("boot").state == "unconfigured"


def test_invalid_role_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, transport=transport)

    with pytest.raises(ProtocolValidationError, match="GPIO role"):
        configurator.configure_mode(
            role="power",
            channel="CTRL0",
            dut_signal="PMIC_EN",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert transport.requests == []
    assert registry.get("reset").state == "unconfigured"
    assert registry.get("boot").state == "unconfigured"


def test_invalid_mode_is_rejected_before_transport_request() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(CommandSuccessMessage())
    configurator = GpioConfigurator(registry=registry, transport=transport)

    with pytest.raises(ProtocolValidationError, match="GPIO mode"):
        configurator.configure_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="floating",
            active_level="low",
            source="runtime",
        )

    assert transport.requests == []
    assert registry.get("reset").state == "unconfigured"


def test_unexpected_response_does_not_update_registry() -> None:
    registry = GpioModeRegistry()
    transport = FakeTransport(
        HelloMessage(
            firmware="0.1.0",
            device="debug-helper",
            capabilities=("uart_capture", "gpio_control"),
        )
    )
    configurator = GpioConfigurator(registry=registry, transport=transport)

    with pytest.raises(GpioConfigurationError, match="Expected command response"):
        configurator.configure_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            source="runtime",
        )

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n'
    ]
    assert registry.get("reset").state == "unconfigured"
