"""Byte-first audited UART send HTTP contract."""

import pytest
from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.workflows.uart_send import UartSendError
from dutchmate_service.app import create_app


def test_uart_send_returns_exact_bytes_and_audit_references():
    runtime = FakeRuntime(connected_status())
    response = TestClient(create_app(runtime)).post(
        "/dut/uart/send",
        json={"text": "go", "line_ending": "crlf"},
    )
    assert response.status_code == 200
    assert runtime.uart_send_requests == [{"data_b64": None, "text": "go", "line_ending": "crlf"}]
    body = response.json()
    assert body["data_b64"] == "Z28NCg=="
    assert body["accepted_bytes"] == 4
    assert body["audit_status"] == "recorded"
    assert body["attempt_evidence_seq"] < body["result_evidence_seq"]


@pytest.mark.parametrize(
    "payload",
    [
        {"cmd": "go"},
        {"text": "go"},
        {"data_b64": "eA==", "force": True},
        {"text": "go", "line_ending": "none", "append_newline": False},
        {"data_b64": "!"},
        {"text": "x" * 1024, "line_ending": "lf"},
    ],
)
def test_invalid_or_retired_fields_do_not_reach_runtime(payload):
    runtime = FakeRuntime(connected_status())
    response = TestClient(create_app(runtime)).post("/dut/uart/send", json=payload)
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert runtime.uart_send_requests == []


def test_failed_send_preserves_audit_context():
    class Failed(FakeRuntime):
        def send_uart(self, **kwargs):
            raise UartSendError(
                error="timeout",
                detail="UART transmission failed",
                context={
                    "attempt_id": "attempt01",
                    "bytes_accepted": None,
                    "may_have_reached_dut": True,
                },
            )

    response = TestClient(create_app(Failed(connected_status()))).post(
        "/dut/uart/send", json={"data_b64": "eA=="}
    )
    assert response.status_code == 502
    assert response.json()["context"]["attempt_id"] == "attempt01"
