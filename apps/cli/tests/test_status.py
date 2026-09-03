from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceUnavailableError
from dutchmate_cli.config import CliConfig, DaemonConfig
from dutchmate_cli.status import format_status


def test_format_status_renders_channel_first_state() -> None:
    payload: dict[str, object] = {
        "connected": True,
        "connection_state": "connected",
        "backend_mode": "enhanced",
        "port": "/dev/ttyACM0",
        "firmware": "0.1.0",
        "device": "dutchmate-rp2350",
        "backend_capabilities": ["gpio_control", "uart_receive", "uart_send"],
        "capabilities": ["gpio_control", "uart_receive"],
        "capability_policy": {
            "uart_send": {
                "tx_policy_enabled": False,
                "source": "hardware.uart.tx_enabled",
            }
        },
        "timestamp_provenance": {
            "segment_id": 0,
            "timestamp": {
                "source": "device",
                "clock": "rp2350_timer",
                "observation_point": "debug_helper_uart_receive",
                "event_granularity": "uart_event",
            },
        },
        "integrity": {
            "loss_status": "none_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 0,
        },
        "active_session_id": None,
        "active_workflow": None,
        "commanded_boot_mode": "bootloader",
        "reconnect_remaining_s": None,
        "retention": {
            "enabled": True,
            "max_count": 25,
            "session_count": 3,
            "diagnostic": None,
        },
        "control_channels": {
            "CTRL0": {
                "channel": "CTRL0",
                "state": "configured",
                "role": "reset",
                "dut_signal": "RESET_N",
                "mode": "open_drain",
                "active_level": "low",
                "idle_level": "high",
                "source": "config",
            },
            "CTRL1": {"channel": "CTRL1", "state": "unconfigured"},
            "CTRL2": {"channel": "CTRL2", "state": "unconfigured"},
            "CTRL3": {"channel": "CTRL3", "state": "unconfigured"},
        },
    }

    assert format_status(payload) == "\n".join(
        [
            "Service: running",
            "Backend: enhanced",
            "Workflow: none",
            "Session: none",
            "Commanded boot mode: bootloader",
            "Connection: connected",
            "Device: connected (dutchmate-rp2350, firmware 0.1.0)",
            "Port: /dev/ttyACM0",
            "Backend capabilities: gpio_control, uart_receive, uart_send",
            "Capabilities: gpio_control, uart_receive",
            "UART TX policy: disabled (hardware.uart.tx_enabled)",
            "Timestamp provenance: segment 0: device/rp2350_timer, "
            "debug_helper_uart_receive/uart_event",
            "UART loss: none_reported (scope=debug_helper_rx_buffer, dropped_bytes=0)",
            "Retention: healthy (3/25 sessions)",
            "Control channels:",
            "  CTRL0: reset -> RESET_N (mode=open_drain, active=low, idle=high, source=config)",
            "  CTRL1: unconfigured",
            "  CTRL2: unconfigured",
            "  CTRL3: unconfigured",
        ]
    )


def test_format_status_renders_basic_loss_limit_and_tx_policy() -> None:
    output = format_status(
        {
            "connected": True,
            "backend_mode": "basic",
            "port": "/dev/ttyUSB0",
            "backend_capabilities": ["uart_receive", "uart_send"],
            "capabilities": ["uart_receive"],
            "capability_policy": {
                "uart_send": {
                    "tx_policy_enabled": False,
                    "source": "hardware.uart.tx_enabled",
                }
            },
            "timestamp_provenance": {
                "segment_id": 0,
                "timestamp": {
                    "source": "host",
                    "clock": "monotonic",
                    "observation_point": "host_serial_read",
                    "event_granularity": "serial_read_chunk",
                },
            },
            "integrity": {
                "loss_status": "not_observable",
                "observation_scope": None,
                "dropped_bytes": None,
            },
            "active_session_id": None,
            "control_channels": {},
        }
    )

    assert "Backend: basic" in output
    assert "Device: connected (generic UART adapter)" in output
    assert "Backend capabilities: uart_receive, uart_send" in output
    assert "Capabilities: uart_receive" in output
    assert "UART TX policy: disabled (hardware.uart.tx_enabled)" in output
    assert (
        "Timestamp provenance: segment 0: host/monotonic, "
        "host_serial_read/serial_read_chunk" in output
    )
    assert "UART loss: not_observable" in output


def test_format_status_renders_active_reconnect_window() -> None:
    output = format_status(
        {
            "connected": False,
            "connection_state": "reconnecting",
            "backend_mode": "enhanced",
            "active_workflow": "boot_test",
            "active_session_id": "20260820T120000Z-a1b2c3d4",
            "reconnect_remaining_s": 2.14,
        }
    )

    assert "Workflow: boot-test (active)" in output
    assert "Session: 20260820T120000Z-a1b2c3d4" in output
    assert "Connection: reconnecting (2.1s remaining)" in output


def test_format_status_renders_retention_diagnostic() -> None:
    output = format_status(
        {
            "retention": {
                "enabled": True,
                "max_count": 1,
                "session_count": 3,
                "diagnostic": "retention_blocked",
            }
        }
    )

    assert "Retention: retention_blocked (3/1 sessions)" in output


@pytest.mark.parametrize("remaining", [None, True, -0.1, float("inf"), "2.1"])
def test_format_status_omits_invalid_reconnect_remaining_time(remaining: object) -> None:
    output = format_status(
        {
            "connected": False,
            "connection_state": "reconnecting",
            "reconnect_remaining_s": remaining,
        }
    )

    assert "Connection: reconnecting\n" in output


def test_status_command_prints_service_status(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_status(*, service_url: str) -> dict[str, object]:
        assert service_url == "http://127.0.0.1:2040"
        return {"connected": False}

    monkeypatch.setattr(main, "fetch_status", fake_fetch_status)
    monkeypatch.setattr(main, "format_status", lambda _payload: "Service: running")

    result = CliRunner().invoke(main.app, ["status"])

    assert result.exit_code == 0
    assert result.output == "Service: running\n"


def test_status_command_reports_service_unavailable(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_status(*, service_url: str) -> dict[str, object]:
        raise ServiceUnavailableError("Device Core Service is not running.")

    monkeypatch.setattr(main, "fetch_status", fake_fetch_status)

    result = CliRunner().invoke(main.app, ["status"])

    assert result.exit_code == 1
    assert "Error: Device Core Service is not running." in result.output


def test_status_command_uses_config_service_url(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_fetch_status(*, service_url: str) -> dict[str, object]:
        assert service_url == "http://localhost:2041"
        return {"connected": False}

    monkeypatch.setattr(
        main,
        "load_cli_config",
        lambda: CliConfig(daemon=DaemonConfig(host="localhost", port=2041)),
    )
    monkeypatch.setattr(main, "fetch_status", fake_fetch_status)
    monkeypatch.setattr(main, "format_status", lambda _payload: "Service: running")

    result = CliRunner().invoke(main.app, ["status"])

    assert result.exit_code == 0
    assert result.output == "Service: running\n"
