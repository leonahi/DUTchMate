from pathlib import Path

import pytest

from dutchmate_core.device_connection.messages import (
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.gpio_config.config import parse_hardware_gpio_config
from dutchmate_core.runtime import (
    DeviceCoreRuntime,
    DeviceCoreRuntimeError,
    DeviceCoreStatus,
)
from dutchmate_core.workflows.device_actions import DeviceActionResult


class FakeTransport:
    def __init__(self, responses: list[DeviceMessage] | None = None) -> None:
        self.responses = responses or []
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> DeviceMessage:
        self.requests.append(command)
        if not self.responses:
            raise AssertionError("fake transport has no queued response")
        return self.responses.pop(0)


def hello() -> HelloMessage:
    return HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control", "uart_send"),
    )


def test_initial_status_is_disconnected_with_unconfigured_gpio(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        session_root=tmp_path,
        port="/dev/ttyACM0",
    )

    status = runtime.status()

    assert status == DeviceCoreStatus(
        connected=False,
        port="/dev/ttyACM0",
        firmware=None,
        device=None,
        capabilities=(),
        active_session_id=None,
        control_channels=status.control_channels,
    )
    assert status.control_channels["CTRL0"].state == "unconfigured"
    assert status.control_channels["CTRL3"].state == "unconfigured"
    assert runtime.session_store.root == tmp_path


def test_record_hello_updates_connection_status(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(transport=FakeTransport(), session_root=tmp_path)

    status = runtime.record_hello(hello(), port="/dev/tty.usbmodem2040")

    assert status.connected is True
    assert status.port == "/dev/tty.usbmodem2040"
    assert status.firmware == "0.1.0"
    assert status.device == "dutchmate-rp2040"
    assert status.capabilities == ("uart_capture", "gpio_control", "uart_send")


def test_apply_hardware_config_requires_connection(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(transport=FakeTransport(), session_root=tmp_path)
    config = parse_hardware_gpio_config({})

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.apply_hardware_config(config)


def test_apply_hardware_config_sends_configured_modes(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            CommandSuccessMessage(timestamp_us=100),
            CommandSuccessMessage(timestamp_us=200),
        ]
    )
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello())
    config = parse_hardware_gpio_config(
        {
            "hardware": {
                "control": {
                    "reset": {
                        "channel": "CTRL0",
                        "dut_signal": "RESET_N",
                        "mode": "open_drain",
                        "active_level": "low",
                    },
                    "boot": {
                        "channel": "CTRL1",
                        "dut_signal": "BOOT0",
                        "mode": "push_pull",
                        "active_level": "high",
                        "idle_level": "low",
                    },
                }
            }
        }
    )

    states = runtime.apply_hardware_config(config)

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"configure_gpio_mode","channel":"CTRL1","role":"boot",'
        b'"mode":"push_pull","active_level":"high","idle_level":"low"}\n',
    ]
    assert states["reset"].state == "configured"
    assert states["reset"].channel == "CTRL0"
    assert states["reset"].source == "config"
    assert states["reset"].device_timestamp_us == 100
    assert states["boot"].state == "configured"
    assert states["boot"].channel == "CTRL1"
    assert states["boot"].source == "config"
    assert states["boot"].device_timestamp_us == 200
    assert runtime.status().control_channels["CTRL0"] == states["reset"]


def test_reset_uses_shared_gpio_state_and_transport(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            CommandSuccessMessage(timestamp_us=100),
            CommandSuccessMessage(timestamp_us=300),
        ]
    )
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello())
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
    )

    result = runtime.reset_dut(pulse_ms=250)

    assert result == DeviceActionResult(action="reset", timestamp_us=300)
    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"reset","pulse_ms":250}\n',
    ]


def test_disconnect_clears_connection_metadata_but_keeps_gpio_state(tmp_path: Path) -> None:
    transport = FakeTransport([CommandSuccessMessage(timestamp_us=100)])
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello(), port="/dev/ttyACM0")
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
    )

    status = runtime.disconnect()

    assert status.connected is False
    assert status.port == "/dev/ttyACM0"
    assert status.firmware is None
    assert status.control_channels["CTRL0"].state == "configured"
