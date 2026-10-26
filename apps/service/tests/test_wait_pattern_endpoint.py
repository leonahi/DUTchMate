import pytest
from fastapi.testclient import TestClient
from test_monitor_endpoint import MonitorAliasRuntime

from dutchmate_core.operations import MonitorResult
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app


class WaitRuntime(MonitorAliasRuntime):
    def __init__(self):
        super().__init__()
        self.wait_requests = []

    def wait_pattern(self, *, pattern: str, timeout_s: float) -> MonitorResult:
        self.wait_requests.append((pattern, timeout_s))
        return super().wait_pattern(pattern=pattern, timeout_s=timeout_s)


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


def test_wait_pattern_endpoint_preserves_operation_active_error() -> None:
    class BusyRuntime(WaitRuntime):
        def wait_pattern(self, *, pattern: str, timeout_s: float) -> MonitorResult:
            raise DeviceActionError(
                error="operation_active", detail="an exclusive operation is active"
            )

    response = TestClient(create_app(BusyRuntime())).post(
        "/dut/wait-pattern",
        json={"pattern": "READY", "timeout_s": 1},
    )

    assert response.status_code == 409
    assert response.json()["error"] == "operation_active"


def test_wait_pattern_endpoint_returns_structured_capability_error() -> None:
    class IncapableRuntime(WaitRuntime):
        def wait_pattern(self, *, pattern: str, timeout_s: float) -> MonitorResult:
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
