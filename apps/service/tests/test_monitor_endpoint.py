"""Bounded Monitor HTTP contract tests."""

from threading import Event

from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.backends import SegmentContext, SegmentTimestamp, UartIntegrity
from dutchmate_core.operations import (
    EvidenceCursor,
    EvidenceRange,
    MonitorCondition,
    MonitorResult,
    MonitorTimestampProvenance,
)
from dutchmate_service.app import create_app


class MonitorRuntime(FakeRuntime):
    def __init__(self) -> None:
        super().__init__(connected_status())
        self.monitor_requests: list[dict[str, object]] = []

    def monitor(
        self,
        *,
        duration_s: object | None = None,
        conditions: tuple[MonitorCondition, ...] | None = None,
        timeout_s: object | None = None,
        cancellation: Event | None = None,
    ) -> MonitorResult:
        self.monitor_requests.append(
            {
                "duration_s": duration_s,
                "conditions": conditions,
                "timeout_s": timeout_s,
                "has_cancellation": cancellation is not None,
            }
        )
        mode = "duration" if duration_s is not None else "conditions"
        outcome = "elapsed" if mode == "duration" else "timeout"
        return MonitorResult(
            operation_id="monitor-http",
            outcome=outcome,
            mode=mode,
            duration_s=float(duration_s) if duration_s is not None else None,
            conditions=conditions or (),
            timeout_s=float(timeout_s) if timeout_s is not None else None,
            start_cursor=EvidenceCursor("session-one", 4),
            end_cursor=EvidenceCursor("session-one", 6),
            evidence_ranges=(EvidenceRange("session-one", 3, 6),),
            match=None,
            line_processing_limited=False,
            integrity=UartIntegrity(
                "none_reported",
                "debug_helper_rx_buffer",
                0,
            ),
            timestamp_provenance=(
                MonitorTimestampProvenance(
                    session_id="session-one",
                    segment=SegmentContext(
                        segment_id=0,
                        timestamp=SegmentTimestamp(
                            source="device",
                            clock="rp2350_timer",
                            unit="us",
                            origin="segment_start",
                            source_origin_us=100,
                            observation_point="debug_helper_uart_receive",
                            event_granularity="uart_event",
                        ),
                    ),
                ),
            ),
        )


class MonitorAliasRuntime(MonitorRuntime):
    def capture_uart(self, *, duration_s: float) -> MonitorResult:
        return self.monitor(duration_s=duration_s)

    def wait_pattern(self, *, pattern: str, timeout_s: float) -> MonitorResult:
        return self.monitor(
            conditions=(MonitorCondition(pattern=pattern),),
            timeout_s=timeout_s,
        )


def test_duration_monitor_returns_http_success_operation_result() -> None:
    runtime = MonitorRuntime()

    response = TestClient(create_app(runtime)).post(
        "/dut/monitor",
        json={"duration_s": 0.25},
    )

    assert response.status_code == 200
    assert runtime.monitor_requests == [
        {
            "duration_s": 0.25,
            "conditions": None,
            "timeout_s": None,
            "has_cancellation": True,
        }
    ]
    assert response.json() == {
        "ok": True,
        "operation_id": "monitor-http",
        "outcome": "elapsed",
        "mode": "duration",
        "duration_s": 0.25,
        "conditions": [],
        "timeout_s": None,
        "start_cursor": {
            "session_id": "session-one",
            "next_evidence_seq": 4,
        },
        "end_cursor": {
            "session_id": "session-one",
            "next_evidence_seq": 6,
        },
        "evidence_ranges": [
            {
                "session_id": "session-one",
                "start_evidence_seq": 3,
                "end_evidence_seq_exclusive": 6,
            }
        ],
        "matched_condition": None,
        "line_processing_limited": False,
        "integrity": {
            "loss_status": "none_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 0,
        },
        "timestamp_provenance": [
            {
                "session_id": "session-one",
                "segment": {
                    "segment_id": 0,
                    "timestamp": {
                        "source": "device",
                        "clock": "rp2350_timer",
                        "unit": "us",
                        "origin": "segment_start",
                        "source_origin_us": 100,
                        "observation_point": "debug_helper_uart_receive",
                        "event_granularity": "uart_event",
                    },
                },
            },
        ],
    }


def test_condition_timeout_is_http_200_and_preserves_condition_order() -> None:
    runtime = MonitorRuntime()

    response = TestClient(create_app(runtime)).post(
        "/dut/monitor",
        json={
            "conditions": [
                {"pattern": "READY", "name": "ready"},
                {"pattern": "ERROR"},
            ],
            "timeout_s": 3,
        },
    )

    assert response.status_code == 200
    assert response.json()["outcome"] == "timeout"
    assert runtime.monitor_requests[0]["conditions"] == (
        MonitorCondition(pattern="READY", name="ready"),
        MonitorCondition(pattern="ERROR"),
    )


def test_invalid_monitor_mode_is_rejected_before_runtime_call() -> None:
    runtime = MonitorRuntime()

    response = TestClient(create_app(runtime)).post(
        "/dut/monitor",
        json={
            "duration_s": 1,
            "conditions": [{"pattern": "READY"}],
            "timeout_s": 1,
        },
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert runtime.monitor_requests == []


def test_legacy_capture_and_wait_endpoints_serialize_monitor_alias_results() -> None:
    runtime = MonitorAliasRuntime()
    client = TestClient(create_app(runtime))

    capture = client.post("/dut/capture", json={"duration_s": 0.25})
    wait = client.post(
        "/dut/wait-pattern",
        json={"pattern": "READY", "timeout_s": 3},
    )

    assert capture.status_code == 200
    assert capture.json()["operation_id"] == "monitor-http"
    assert capture.json()["outcome"] == "elapsed"
    assert wait.status_code == 200
    assert wait.json()["operation_id"] == "monitor-http"
    assert wait.json()["outcome"] == "timeout"
