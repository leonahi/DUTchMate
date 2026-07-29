from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.store import SessionSummary
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app


def test_capture_passes_duration_to_runtime_and_returns_summary() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/capture", json={"duration_s": 2.5})

    assert response.status_code == 200
    assert runtime.capture_requests == [2.5]
    assert response.json() == {
        "ok": True,
        "session_id": "20260729T100000Z-capture01",
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "segments": 1,
    }


def test_capture_serializes_incomplete_evidence_flags() -> None:
    class IncompleteCaptureRuntime(FakeRuntime):
        def capture_uart(self, *, duration_s: float) -> SessionSummary:
            return SessionSummary(
                session_id="20260729T100000Z-capture02",
                started_at="2026-07-29T10:00:00Z",
                command="capture --seconds 5",
                truncated=True,
                interrupted=True,
                resumed=True,
                overflow=True,
                baseline=False,
                firmware="0.1.0",
                device="dutchmate-rp2040",
                segment_count=2,
            )

    app = create_app(IncompleteCaptureRuntime(connected_status()))

    response = TestClient(app).post("/dut/capture", json={"duration_s": 5})

    assert response.status_code == 200
    assert response.json() == {
        "ok": True,
        "session_id": "20260729T100000Z-capture02",
        "truncated": True,
        "interrupted": True,
        "resumed": True,
        "overflow": True,
        "segments": 2,
    }


def test_capture_rejects_invalid_duration() -> None:
    app = create_app(FakeRuntime(connected_status()))

    response = TestClient(app).post("/dut/capture", json={"duration_s": 0})

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "Request validation failed",
    }


def test_capture_active_uses_conflict_error_contract() -> None:
    class ActiveCaptureRuntime(FakeRuntime):
        def capture_uart(self, *, duration_s: float) -> SessionSummary:
            raise DeviceActionError(
                error="capture_active",
                detail="capture is already active",
            )

    app = create_app(ActiveCaptureRuntime(connected_status()))

    response = TestClient(app).post("/dut/capture", json={"duration_s": 1})

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "capture_active",
        "detail": "capture is already active",
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
    }
