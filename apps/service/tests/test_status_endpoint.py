from fastapi.testclient import TestClient
from helpers import FakeRuntime, disconnected_status

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
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
        "connection_state": "disconnected",
        "backend_mode": "enhanced",
        "port": "/dev/ttyACM0",
        "firmware": None,
        "device": None,
        "backend_identity": {
            "port": "/dev/ttyACM0",
            "firmware": None,
            "device": None,
        },
        "backend_capabilities": [],
        "capabilities": [],
        "capability_policy": {
            "uart_send": {
                "tx_policy_enabled": False,
                "source": "hardware.uart.tx_enabled",
            }
        },
        "timestamp_provenance": None,
        "integrity": None,
        "active_session_id": None,
        "active_workflow": None,
        "reconnect_remaining_s": None,
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
                backend_mode="enhanced",
                backend_capabilities=("gpio_control", "uart_receive"),
                capability_policy=BackendCapabilityPolicy(
                    uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
                ),
                timestamp_provenance=SegmentContext(
                    segment_id=0,
                    timestamp=SegmentTimestamp(
                        source="device",
                        clock="rp2040_timer",
                        unit="us",
                        origin="segment_start",
                        source_origin_us=100,
                        observation_point="debug_helper_uart_receive",
                        event_granularity="uart_event",
                    ),
                ),
                integrity=UartIntegrity(
                    loss_status="none_reported",
                    observation_scope="debug_helper_rx_buffer",
                    dropped_bytes=0,
                ),
                connection_state="connected",
                active_workflow="capture",
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
    assert payload["backend_mode"] == "enhanced"
    assert payload["backend_capabilities"] == ["gpio_control", "uart_receive"]
    assert payload["capability_policy"]["uart_send"]["tx_policy_enabled"] is False
    assert payload["timestamp_provenance"]["segment_id"] == 0
    assert payload["timestamp_provenance"]["timestamp"]["clock"] == "rp2040_timer"
    assert payload["integrity"]["loss_status"] == "none_reported"
    assert payload["active_session_id"] == "20260724T100000Z-abc12345"
    assert payload["connection_state"] == "connected"
    assert payload["active_workflow"] == "capture"
    assert payload["reconnect_remaining_s"] is None
    assert payload["control_channels"]["CTRL0"]["state"] == "configured"
    assert payload["control_channels"]["CTRL0"]["role"] == "reset"
    assert payload["control_channels"]["CTRL0"]["dut_signal"] == "RESET_N"
    assert payload["control_channels"]["CTRL0"]["mode"] == "open_drain"
    assert payload["control_channels"]["CTRL0"]["source"] == "config"
    assert payload["control_channels"]["CTRL0"]["device_timestamp_us"] == 123
