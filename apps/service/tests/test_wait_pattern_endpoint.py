from dataclasses import replace

import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.session_store.models import (
    FirstError,
    MatchExcerpt,
    WaitPatternResult,
)
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app


class WaitRuntime(FakeRuntime):
    def __init__(self, *, matched: bool = True) -> None:
        super().__init__(connected_status())
        self.matched = matched
        self.wait_requests: list[tuple[str, float]] = []

    def wait_pattern(self, *, pattern: str, timeout_s: float) -> WaitPatternResult:
        self.wait_requests.append((pattern, timeout_s))
        summary = replace(
            self.capture_uart(duration_s=timeout_s),
            workflow="wait_pattern",
            duration_s=None,
            end_reason="pattern_matched" if self.matched else "timeout",
            wait_pattern=pattern,
            match_mode="literal",
            case_sensitive=True,
            timeout_s=timeout_s,
            matched=self.matched,
            detected_pattern_index=0 if self.matched else None,
        )
        return WaitPatternResult(
            summary=summary,
            pattern=pattern,
            matched=self.matched,
            match=_match(pattern) if self.matched else None,
        )


def test_wait_pattern_endpoint_serializes_authoritative_match_reference() -> None:
    runtime = WaitRuntime()
    response = TestClient(create_app(runtime)).post(
        "/dut/wait-pattern",
        json={"pattern": "READY.*", "timeout_s": 2.5},
    )

    assert response.status_code == 200
    assert runtime.wait_requests == [("READY.*", 2.5)]
    payload = response.json()
    assert payload["ok"] is True
    assert payload["matched"] is True
    assert payload["pattern"] == "READY.*"
    assert payload["end_reason"] == "pattern_matched"
    assert payload["detected_pattern_index"] == 0
    assert payload["segment_id"] == 0
    assert payload["timestamp_us"] == 20
    assert payload["match_start_byte"] == 2
    assert payload["match_end_byte"] == 9
    assert payload["match_excerpt"]["raw_b64"] == "eHhSRUFEWS4qCg=="


def test_wait_pattern_timeout_is_successful_with_null_match_fields() -> None:
    response = TestClient(create_app(WaitRuntime(matched=False))).post(
        "/dut/wait-pattern",
        json={"pattern": "READY", "timeout_s": 1},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["matched"] is False
    assert payload["end_reason"] == "timeout"
    for field in (
        "match_excerpt",
        "detected_pattern_index",
        "channel",
        "segment_id",
        "timestamp_us",
    ):
        assert payload[field] is None


@pytest.mark.parametrize(
    "body",
    [
        {"pattern": "", "timeout_s": 1},
        {"pattern": "bad\npattern", "timeout_s": 1},
        {"pattern": "x" * 257, "timeout_s": 1},
        {"pattern": "READY", "timeout_s": True},
        {"pattern": "READY", "timeout_s": 301},
    ],
)
def test_wait_pattern_endpoint_rejects_invalid_input_before_runtime(
    body: dict[str, object],
) -> None:
    runtime = WaitRuntime()
    response = TestClient(create_app(runtime)).post("/dut/wait-pattern", json=body)

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert runtime.wait_requests == []


def test_wait_pattern_endpoint_preserves_capture_active_error() -> None:
    class BusyRuntime(WaitRuntime):
        def wait_pattern(self, *, pattern: str, timeout_s: float) -> WaitPatternResult:
            raise DeviceActionError(error="capture_active", detail="capture is already active")

    response = TestClient(create_app(BusyRuntime())).post(
        "/dut/wait-pattern",
        json={"pattern": "READY", "timeout_s": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "capture_active"


def test_wait_pattern_endpoint_returns_structured_capability_error() -> None:
    class IncapableRuntime(WaitRuntime):
        def wait_pattern(self, *, pattern: str, timeout_s: float) -> WaitPatternResult:
            raise DeviceActionError(
                error="unsupported_capability",
                detail="UART receive is unavailable",
                context={
                    "operation": "wait_pattern",
                    "backend_mode": "enhanced",
                    "required_capabilities": ["uart_receive"],
                    "available_capabilities": [],
                    "backend_capabilities": [],
                    "disabled_by_policy": [],
                },
            )

    response = TestClient(create_app(IncapableRuntime())).post(
        "/dut/wait-pattern",
        json={"pattern": "READY", "timeout_s": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "unsupported_capability"
    assert response.json()["context"]["required_capabilities"] == ["uart_receive"]


def _match(pattern: str) -> FirstError:
    return FirstError(
        pattern=pattern,
        detected_pattern_index=0,
        segment_id=0,
        timestamp_us=20,
        channel=0,
        ingestion_index=1,
        line_index_in_event=0,
        line_start_ingestion_index=1,
        line_start_event_offset=0,
        line_end_ingestion_index=1,
        line_end_event_offset=10,
        total_line_bytes=10,
        match_start_byte=2,
        match_end_byte=9,
        match_excerpt=MatchExcerpt(
            start_byte=0,
            end_byte=10,
            text="xxREADY.*\n",
            raw_b64="eHhSRUFEWS4qCg==",
            excerpt_truncated=False,
        ),
    )
