from fastapi.testclient import TestClient
from helpers import FakeRuntime, connected_status

from dutchmate_core.validation import prepare_uart_send_payload
from dutchmate_core.workflows.uart_send import UartSendError
from dutchmate_service.app import create_app


def test_uart_send_endpoint_uses_defaults_and_serializes_completion() -> None:
    runtime = FakeRuntime(connected_status())

    response = TestClient(create_app(runtime)).post(
        "/dut/uart/send",
        json={"cmd": "reboot"},
    )

    assert response.status_code == 200
    assert runtime.uart_send_requests == [
        {"cmd": "reboot", "append_newline": True, "force": False}
    ]
    assert response.json() == {
        "ok": True,
        "performed_at": "2026-07-29T10:00:01Z",
        "device_timestamp_us": 182334700,
        "attempt_id": None,
        "perturbation_logged": False,
    }


def test_uart_send_endpoint_forwards_no_newline_and_force() -> None:
    runtime = FakeRuntime(connected_status())

    response = TestClient(create_app(runtime)).post(
        "/dut/uart/send",
        json={"cmd": "go", "append_newline": False, "force": True},
    )

    assert response.status_code == 200
    assert runtime.uart_send_requests[-1] == {
        "cmd": "go",
        "append_newline": False,
        "force": True,
    }
    assert response.json()["attempt_id"] == "attempt01"
    assert response.json()["perturbation_logged"] is True


def test_uart_send_endpoint_rejects_non_boolean_flags_before_runtime() -> None:
    runtime = FakeRuntime(connected_status())

    response = TestClient(create_app(runtime)).post(
        "/dut/uart/send",
        json={"cmd": "go", "force": "true"},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert runtime.uart_send_requests == []


def test_uart_send_endpoint_preserves_final_payload_size_context() -> None:
    class ValidatingRuntime(FakeRuntime):
        def send_uart(
            self,
            *,
            cmd: str,
            append_newline: bool = True,
            force: bool = False,
        ) -> object:
            del force
            prepare_uart_send_payload(cmd, append_newline=append_newline)
            raise AssertionError("oversized payload unexpectedly validated")

    response = TestClient(create_app(ValidatingRuntime(connected_status()))).post(
        "/dut/uart/send",
        json={"cmd": "x" * 1024},
    )

    assert response.status_code == 400
    assert response.json()["error"] == "invalid_argument"
    assert response.json()["context"] == {
        "actual_bytes": 1025,
        "max_bytes": 1024,
    }


def test_uart_send_endpoint_preserves_forced_failure_audit_context() -> None:
    class FailingRuntime(FakeRuntime):
        def send_uart(
            self,
            *,
            cmd: str,
            append_newline: bool = True,
            force: bool = False,
        ) -> object:
            del cmd, append_newline, force
            raise UartSendError(
                error="timeout",
                detail="UART send timed out",
                context={
                    "attempt_id": "attempt01",
                    "bytes_accepted": None,
                    "may_have_reached_dut": True,
                },
            )

    response = TestClient(create_app(FailingRuntime(connected_status()))).post(
        "/dut/uart/send",
        json={"cmd": "go", "force": True},
    )

    assert response.status_code == 502
    assert response.json()["error"] == "timeout"
    assert response.json()["context"] == {
        "attempt_id": "attempt01",
        "bytes_accepted": None,
        "may_have_reached_dut": True,
    }
