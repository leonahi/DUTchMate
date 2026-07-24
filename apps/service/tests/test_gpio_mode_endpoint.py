from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status, disconnected_status

from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_service.app import create_app


def test_configure_gpio_mode_calls_runtime_and_returns_accepted_mode() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 200
    assert runtime.gpio_mode_requests == [
        {
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
            "idle_level": None,
        }
    ]
    assert response.json() == {
        "ok": True,
        "channel": "CTRL0",
        "role": "reset",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
        "idle_level": None,
        "source": "runtime",
        "timestamp_us": 182334400,
    }


def test_configure_gpio_mode_passes_idle_level_for_push_pull_mapping() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL2",
            "role": "power_en",
            "dut_signal": "REG_EN",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        },
    )

    assert response.status_code == 200
    assert runtime.gpio_mode_requests == [
        {
            "channel": "CTRL2",
            "role": "power_en",
            "dut_signal": "REG_EN",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        }
    ]


def test_configure_gpio_mode_runtime_error_uses_service_error_contract() -> None:
    class DisconnectedRuntime(FakeRuntime):
        def configure_gpio_mode(
            self,
            *,
            role: str,
            channel: str,
            dut_signal: str,
            mode: str,
            active_level: str,
            idle_level: str | None = None,
        ) -> GpioControlChannelState:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    app = create_app(DisconnectedRuntime(disconnected_status()))

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL0",
            "role": "reset",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 503
    assert response.json() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Debug Helper is not connected",
    }


def test_configure_gpio_mode_validation_error_uses_service_error_contract() -> None:
    app = create_app(FakeRuntime(connected_status()))

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "GPIO0",
            "role": " ",
            "dut_signal": "RESET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
    }
