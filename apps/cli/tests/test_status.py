from __future__ import annotations

import httpx
import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceApiError, ServiceUnavailableError, fetch_status
from dutchmate_cli.status import format_status


def test_fetch_status_returns_status_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/status"
        return httpx.Response(200, json={"connected": False, "control_channels": {}})

    payload = fetch_status(transport=httpx.MockTransport(handler))

    assert payload == {"connected": False, "control_channels": {}}


def test_fetch_status_maps_connection_failure_to_service_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ServiceUnavailableError) as error:
        fetch_status(transport=httpx.MockTransport(handler))

    assert "Run 'dutchmate start' first" in str(error.value)


def test_fetch_status_includes_service_error_detail() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "runtime failed"})

    with pytest.raises(ServiceApiError) as error:
        fetch_status(transport=httpx.MockTransport(handler))

    assert str(error.value) == "Device Core Service returned HTTP 500: runtime failed"


def test_format_status_renders_channel_first_state() -> None:
    payload: dict[str, object] = {
        "connected": True,
        "port": "/dev/ttyACM0",
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "capabilities": ["gpio_control", "uart_capture"],
        "active_session_id": None,
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
            "Device: connected (dutchmate-rp2040, firmware 0.1.0)",
            "Port: /dev/ttyACM0",
            "Active session: none",
            "Capabilities: gpio_control, uart_capture",
            "Control channels:",
            "  CTRL0: reset -> RESET_N (mode=open_drain, active=low, idle=high, source=config)",
            "  CTRL1: unconfigured",
            "  CTRL2: unconfigured",
            "  CTRL3: unconfigured",
        ]
    )


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
