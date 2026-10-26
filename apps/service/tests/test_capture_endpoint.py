import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.store import (
    SessionSummary,
)
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app


@pytest.mark.parametrize("duration_s", [0, 300.1, True, "1"])
def test_capture_rejects_invalid_duration(duration_s: object) -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/capture", json={"duration_s": duration_s})

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
        "detail_truncated": False,
    }
    assert runtime.capture_requests == []


def test_operation_active_uses_conflict_error_contract() -> None:
    class ActiveCaptureRuntime(FakeRuntime):
        def capture_uart(self, *, duration_s: float) -> SessionSummary:
            raise DeviceActionError(
                error="operation_active",
                detail="an exclusive operation is active",
            )

    app = create_app(ActiveCaptureRuntime(connected_status()))

    response = TestClient(app).post("/dut/capture", json={"duration_s": 1})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "operation_active",
        "detail": "an exclusive operation is active",
        "detail_truncated": False,
    }


def test_capture_disconnected_uses_service_unavailable_contract() -> None:
    class DisconnectedCaptureRuntime(FakeRuntime):
        def capture_uart(self, *, duration_s: float) -> SessionSummary:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    app = create_app(DisconnectedCaptureRuntime(connected_status()))

    response = TestClient(app).post("/dut/capture", json={"duration_s": 1})

    assert response.status_code == 503
    assert response.json() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Debug Helper is not connected",
        "detail_truncated": False,
    }
