from fastapi.testclient import TestClient
from helpers import FakeRuntime, disconnected_status

from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.gpio_config.modes import GpioModeRegistry
from dutchmate_core.runtime import DeviceCoreStatus
from dutchmate_service.app import create_app


def test_status_returns_disconnected_runtime_state() -> None:
    app = create_app(FakeRuntime(disconnected_status()))

    response = TestClient(app).get("/status")

    assert response.status_code == 200
    assert response.json() == {
        "connected": False,
        "port": "/dev/ttyACM0",
        "firmware": None,
        "device": None,
        "capabilities": [],
        "active_session_id": None,
        "control_channels": {
            "CTRL0": {
                "channel": "CTRL0",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL1": {
                "channel": "CTRL1",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL2": {
                "channel": "CTRL2",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
            "CTRL3": {
                "channel": "CTRL3",
                "state": "unconfigured",
                "role": None,
                "dut_signal": None,
                "mode": None,
                "active_level": None,
                "idle_level": None,
                "source": None,
                "configured_at": None,
                "device_timestamp_us": None,
                "last_rejected": None,
            },
        },
    }


def test_status_returns_connected_gpio_mapping_state() -> None:
    registry = GpioModeRegistry()
    registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="config",
        device_timestamp_us=123,
    )
    hello = HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control"),
    )
    app = create_app(
        FakeRuntime(
            DeviceCoreStatus(
                connected=True,
                port="/dev/ttyACM0",
                firmware=hello.firmware,
                device=hello.device,
                capabilities=hello.capabilities,
                active_session_id="20260724T100000Z-abc12345",
                control_channels=registry.snapshot(),
            )
        )
    )

    response = TestClient(app).get("/status")

    assert response.status_code == 200
    payload = response.json()
    assert payload["connected"] is True
    assert payload["firmware"] == "0.1.0"
    assert payload["device"] == "dutchmate-rp2040"
    assert payload["capabilities"] == ["uart_capture", "gpio_control"]
    assert payload["active_session_id"] == "20260724T100000Z-abc12345"
    assert payload["control_channels"]["CTRL0"]["state"] == "configured"
    assert payload["control_channels"]["CTRL0"]["role"] == "reset"
    assert payload["control_channels"]["CTRL0"]["dut_signal"] == "RESET_N"
    assert payload["control_channels"]["CTRL0"]["mode"] == "open_drain"
    assert payload["control_channels"]["CTRL0"]["source"] == "config"
    assert payload["control_channels"]["CTRL0"]["device_timestamp_us"] == 123
