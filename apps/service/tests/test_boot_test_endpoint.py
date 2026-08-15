import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.store import SessionSummary
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app


def test_boot_test_passes_duration_to_runtime_and_returns_summary() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": 2.5})

    assert response.status_code == 200
    assert runtime.boot_test_requests == [2.5]
    assert response.json() == {
        "ok": True,
        "session_id": "20260729T100000Z-boot01",
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "segments": 1,
    }


def test_boot_test_serializes_incomplete_evidence_flags() -> None:
    class IncompleteBootTestRuntime(FakeRuntime):
        def run_boot_test(self, *, duration_s: float) -> SessionSummary:
            return SessionSummary(
                session_id="20260729T100000Z-boot02",
                started_at="2026-07-29T10:00:00Z",
                command="boot-test --seconds 5",
                truncated=True,
                interrupted=True,
                resumed=True,
                overflow=True,
                baseline=False,
                firmware="0.1.0",
                device="dutchmate-rp2040",
                segment_count=2,
            )

    app = create_app(IncompleteBootTestRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": 5})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session_id": "20260729T100000Z-boot02",
        "truncated": True,
        "interrupted": True,
        "resumed": True,
        "overflow": True,
        "segments": 2,
    }


@pytest.mark.parametrize("duration_s", [0, 300.1, True, "1"])
def test_boot_test_rejects_invalid_duration(duration_s: object) -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": duration_s})

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
    }
    assert runtime.boot_test_requests == []


def test_boot_test_requires_configured_reset_role() -> None:
    class UnconfiguredBootTestRuntime(FakeRuntime):
        def run_boot_test(self, *, duration_s: float) -> SessionSummary:
            raise GpioConfigurationError("GPIO role 'reset' is not configured")

    app = create_app(UnconfiguredBootTestRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": 1})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "not_configured",
        "detail": "GPIO role 'reset' is not configured",
    }


def test_boot_test_active_uses_conflict_error_contract() -> None:
    class ActiveBootTestRuntime(FakeRuntime):
        def run_boot_test(self, *, duration_s: float) -> SessionSummary:
            raise DeviceActionError(
                error="capture_active",
                detail="capture is already active",
            )

    app = create_app(ActiveBootTestRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": 1})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "capture_active",
        "detail": "capture is already active",
    }


def test_boot_test_disconnected_uses_service_unavailable_contract() -> None:
    class DisconnectedBootTestRuntime(FakeRuntime):
        def run_boot_test(self, *, duration_s: float) -> SessionSummary:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    app = create_app(DisconnectedBootTestRuntime(connected_status()))

    response = TestClient(app).post("/dut/boot-test", json={"duration_s": 1})

    assert response.status_code == 503
    assert response.json() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Debug Helper is not connected",
    }
