import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.store import FirstError, MatchExcerpt, SessionSummary
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app
from dutchmate_service.schemas import capture_summary_payload


def test_capture_summary_serializes_bounded_first_error_evidence() -> None:
    summary = SessionSummary(
        session_id="20260729T100000Z-capture-error",
        started_at="2026-07-29T10:00:00Z",
        command="capture --seconds 1",
        truncated=False,
        interrupted=False,
        resumed=False,
        overflow=False,
        baseline=False,
        firmware=None,
        device=None,
        segment_count=1,
        first_error=FirstError(
            pattern="ERROR",
            detected_pattern_index=3,
            segment_id=0,
            timestamp_us=10,
            channel=1,
            ingestion_index=2,
            line_index_in_event=0,
            line_start_ingestion_index=1,
            line_start_event_offset=4,
            line_end_ingestion_index=2,
            line_end_event_offset=6,
            total_line_bytes=12,
            match_start_byte=2,
            match_end_byte=7,
            match_excerpt=MatchExcerpt(
                start_byte=0,
                end_byte=12,
                text="x ERROR log\n",
                raw_b64="eCBFUlJPUiBsb2cK",
                excerpt_truncated=False,
            ),
        ),
    )

    payload = capture_summary_payload(summary)

    assert payload["first_error"] == {
        "pattern": "ERROR",
        "detected_pattern_index": 3,
        "segment_id": 0,
        "timestamp_us": 10,
        "channel": 1,
        "ingestion_index": 2,
        "line_index_in_event": 0,
        "line_start_ingestion_index": 1,
        "line_start_event_offset": 4,
        "line_end_ingestion_index": 2,
        "line_end_event_offset": 6,
        "total_line_bytes": 12,
        "match_start_byte": 2,
        "match_end_byte": 7,
        "match_excerpt": {
            "start_byte": 0,
            "end_byte": 12,
            "text": "x ERROR log\n",
            "raw_b64": "eCBFUlJPUiBsb2cK",
            "excerpt_truncated": False,
        },
    }


def test_capture_passes_duration_to_runtime_and_returns_summary() -> None:
    runtime = FakeRuntime(connected_status())
    app = create_app(runtime)

    response = TestClient(app).post("/dut/capture", json={"duration_s": 2.5})

    assert response.status_code == 200
    assert runtime.capture_requests == [2.5]
    assert response.json() == {
        "ok": True,
        "session_id": "20260729T100000Z-capture01",
        "backend_mode": "enhanced",
        "backend_identity": {
            "port": "/dev/ttyACM0",
            "firmware": "0.1.0",
            "device": "dutchmate-rp2040",
        },
        "backend_capabilities": ["gpio_control", "uart_receive", "uart_send"],
        "capabilities": ["gpio_control", "uart_receive"],
        "capability_policy": {
            "uart_send": {
                "tx_policy_enabled": False,
                "source": "hardware.uart.tx_enabled",
            }
        },
        "timestamp_provenance": [
            {
                "segment_id": 0,
                "timestamp": {
                    "source": "device",
                    "clock": "rp2040_timer",
                    "unit": "us",
                    "origin": "segment_start",
                    "source_origin_us": 100,
                    "observation_point": "debug_helper_uart_receive",
                    "event_granularity": "uart_event",
                },
            }
        ],
        "integrity": {
            "loss_status": "none_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 0,
        },
        "first_error": None,
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
        "backend_mode": None,
        "backend_identity": {
            "port": None,
            "firmware": "0.1.0",
            "device": "dutchmate-rp2040",
        },
        "backend_capabilities": [],
        "capabilities": [],
        "capability_policy": None,
        "timestamp_provenance": [],
        "integrity": None,
        "first_error": None,
        "truncated": True,
        "interrupted": True,
        "resumed": True,
        "overflow": True,
        "segments": 2,
    }


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
    }
    assert runtime.capture_requests == []


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
