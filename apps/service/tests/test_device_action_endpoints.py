from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.workflows.device_actions import DeviceActionResult
from dutchmate_service.app import create_app


def test_reset_uses_default_pulse_and_returns_timestamp() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/reset")

    assert response.status_code == 200
    assert runtime.reset_requests == [100]
    assert response.json() == {
        "ok": True,
        "timestamp_us": 182334500,
    }


def test_reset_passes_explicit_pulse_to_runtime() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/reset", json={"pulse_ms": 250})

    assert response.status_code == 200
    assert runtime.reset_requests == [250]


def test_reset_not_configured_uses_service_error_contract() -> None:
    class UnconfiguredResetRuntime(FakeRuntime):
        def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
            raise GpioConfigurationError("GPIO role 'reset' is not configured")

    app = create_app(UnconfiguredResetRuntime(connected_status()))

    response = TestClient(app).post("/dut/reset", json={"pulse_ms": 100})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "not_configured",
        "detail": "GPIO role 'reset' is not configured",
        "detail_truncated": False,
    }


def test_reset_validation_error_uses_service_error_contract() -> None:
    app = create_app(FakeRuntime(connected_status()))

    response = TestClient(app).post("/dut/reset", json={"pulse_ms": 0})

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
        "detail_truncated": False,
    }


def test_boot_mode_passes_mode_to_runtime_and_returns_timestamp() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/boot-mode", json={"mode": "bootloader"})

    assert response.status_code == 200
    assert runtime.boot_mode_requests == ["bootloader"]
    assert response.json() == {
        "ok": True,
        "timestamp_us": 182334600,
    }


def test_boot_mode_accepts_normal_mode() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/boot-mode", json={"mode": "normal"})

    assert response.status_code == 200
    assert runtime.boot_mode_requests == ["normal"]


def test_boot_mode_not_configured_uses_service_error_contract() -> None:
    class UnconfiguredBootRuntime(FakeRuntime):
        def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
            raise GpioConfigurationError("GPIO role 'boot' is not configured")

    app = create_app(UnconfiguredBootRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-mode", json={"mode": "bootloader"})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "not_configured",
        "detail": "GPIO role 'boot' is not configured",
        "detail_truncated": False,
    }


def test_boot_mode_validation_error_uses_service_error_contract() -> None:
    app = create_app(FakeRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-mode", json={"mode": "factory"})

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
        "detail_truncated": False,
    }
