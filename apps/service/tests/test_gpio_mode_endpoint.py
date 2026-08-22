import pytest
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
        "device_timestamp_us": 182334400,
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
        "detail_truncated": False,
    }


def test_configure_gpio_mode_validation_error_uses_service_error_contract() -> None:
    app = create_app(FakeRuntime(connected_status()))

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "GPIO0",
            "role": "reset",
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
        "detail_truncated": False,
    }


@pytest.mark.parametrize(
    ("overrides", "detail", "context"),
    [
        (
            {"role": 42},
            "GPIO role must be a string",
            {
                "field": "role",
                "reason": "invalid_type",
                "max_bytes": 64,
            },
        ),
        (
            {"role": "x" * 65},
            "GPIO role must encode to 1..64 UTF-8 bytes",
            {
                "field": "role",
                "reason": "invalid_length",
                "max_bytes": 64,
                "actual_bytes": 65,
            },
        ),
        (
            {"role": " reset"},
            "GPIO role must not have leading or trailing Unicode whitespace",
            {
                "field": "role",
                "reason": "edge_whitespace",
                "max_bytes": 64,
                "actual_bytes": 6,
            },
        ),
        (
            {"dut_signal": "RESET\x00N"},
            "GPIO dut_signal must not contain Unicode control characters",
            {
                "field": "dut_signal",
                "reason": "control_character",
                "max_bytes": 64,
                "actual_bytes": 7,
            },
        ),
    ],
)
def test_configure_gpio_mode_preserves_identifier_validation_context(
    overrides: dict[str, object],
    detail: str,
    context: dict[str, object],
) -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)
    request = {
        "channel": "CTRL0",
        "role": "reset",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
        **overrides,
    }

    response = TestClient(app).post("/gpio/mode", json=request)

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": detail,
        "detail_truncated": False,
        "context": context,
    }
    assert runtime.gpio_mode_requests == []


@pytest.mark.parametrize(
    "overrides",
    [
        {"role": " reset"},
        {"dut_signal": "RESET\x00N"},
        {"mode": "open_drain", "active_level": "high"},
        {"mode": "open_drain", "active_level": "low", "idle_level": "high"},
        {"mode": "push_pull", "active_level": "high"},
        {"mode": "push_pull", "active_level": "high", "idle_level": "high"},
    ],
)
def test_configure_gpio_mode_rejects_exact_contract_violations(
    overrides: dict[str, object],
) -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)
    request = {
        "channel": "CTRL0",
        "role": "reset",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
        **overrides,
    }

    response = TestClient(app).post("/gpio/mode", json=request)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert runtime.gpio_mode_requests == []


def test_configure_gpio_mode_preserves_exact_unicode_identifiers() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post(
        "/gpio/mode",
        json={
            "channel": "CTRL0",
            "role": "Re\u0301set",
            "dut_signal": "RÉSET_N",
            "mode": "open_drain",
            "active_level": "low",
        },
    )

    assert response.status_code == 200
    assert runtime.gpio_mode_requests[0]["role"] == "Re\u0301set"
    assert runtime.gpio_mode_requests[0]["dut_signal"] == "RÉSET_N"
    assert response.json()["role"] == "Re\u0301set"
    assert response.json()["dut_signal"] == "RÉSET_N"
