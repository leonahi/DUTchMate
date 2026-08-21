from datetime import datetime, timezone
from pathlib import Path

import pytest
from runtime_test_support import FakeTransport, enhanced_info

from dutchmate_core.backends.enhanced import EnhancedDeviceControl
from dutchmate_core.device_connection.messages import CommandSuccessMessage
from dutchmate_core.gpio_config.config import parse_hardware_gpio_config
from dutchmate_core.runtime import DeviceCoreRuntime, DeviceCoreRuntimeError, DeviceCoreStatus
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.device_actions import DeviceActionResult


def test_initial_status_is_disconnected_with_unconfigured_gpio(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        session_store=SessionStore(root=tmp_path),
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


def test_record_backend_connection_updates_status(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        session_store=SessionStore(root=tmp_path),
    )

    status = runtime.record_backend_connection(enhanced_info(port="/dev/tty.usbmodem2040"))

    assert status.connected is True
    assert status.port == "/dev/tty.usbmodem2040"
    assert status.firmware == "0.1.0"
    assert status.device == "dutchmate-rp2040"
    assert status.backend_mode == "enhanced"
    assert status.backend_capabilities == ("gpio_control", "uart_receive", "uart_send")
    assert status.capabilities == ("gpio_control", "uart_receive")
    assert status.capability_policy is not None
    assert status.capability_policy.uart_send.tx_policy_enabled is False
    assert status.integrity is not None
    assert status.integrity.loss_status == "none_reported"


def test_tx_policy_cannot_manufacture_unreported_backend_capability(
    tmp_path: Path,
) -> None:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        session_store=SessionStore(root=tmp_path),
        tx_policy_enabled=True,
    )
    info = enhanced_info(capabilities=frozenset({"gpio_control", "uart_receive"}))

    status = runtime.record_backend_connection(info)

    assert status.backend_capabilities == ("gpio_control", "uart_receive")
    assert status.capabilities == ("gpio_control", "uart_receive")
    assert status.capability_policy is not None
    assert status.capability_policy.uart_send.tx_policy_enabled is True


def test_apply_hardware_config_requires_connection(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        session_store=SessionStore(root=tmp_path),
    )
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
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))
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
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport),
        session_store=SessionStore(root=tmp_path),
        action_wall_clock=lambda: datetime(2026, 8, 21, 10, tzinfo=timezone.utc),
    )
    runtime.record_backend_connection(enhanced_info())
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
    )

    result = runtime.reset_dut(pulse_ms=250)

    assert result == DeviceActionResult(
        action="reset",
        pulse_ms=250,
        performed_at="2026-08-21T10:00:00Z",
        device_timestamp_us=300,
    )
    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"reset","pulse_ms":250}\n',
    ]


def test_disconnect_clears_connection_metadata_but_keeps_gpio_state(tmp_path: Path) -> None:
    transport = FakeTransport([CommandSuccessMessage(timestamp_us=100)])
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(transport), session_store=SessionStore(root=tmp_path)
    )
    runtime.record_backend_connection(enhanced_info(port="/dev/ttyACM0"))
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
    assert status.integrity is None
    assert status.control_channels["CTRL0"].state == "configured"
