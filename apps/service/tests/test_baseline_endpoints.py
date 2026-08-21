from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from helpers import (
    FakeRuntime,
    _enhanced_integrity,
    _enhanced_segment,
    _tx_policy,
    disconnected_status,
)

from dutchmate_core.backends import BackendInfo, BackendSnapshot, UartReceiveEvent
from dutchmate_core.session_store.models import (
    BaselineMutationResult,
    SessionComparison,
    SessionDetail,
    SessionHandle,
    SessionListPage,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_service.app import create_app


class BaselineRuntime(FakeRuntime):
    def __init__(self, store: SessionStore) -> None:
        super().__init__(disconnected_status())
        self.store = store

    def mark_baseline(self, session_id: str) -> BaselineMutationResult:
        return self.store.mark_baseline(session_id)

    def clear_baseline(self, session_id: str) -> BaselineMutationResult:
        return self.store.clear_baseline(session_id)

    def compare_session(self, session_id: str) -> SessionComparison:
        return self.store.compare_session(session_id)

    def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        return self.store.list_session_page(limit=limit, cursor=cursor)

    def get_session(self, session_id: str) -> SessionDetail:
        return self.store.get_session_detail(session_id)


def _store(root: Path) -> SessionStore:
    start = datetime(2026, 8, 21, 22, 0, tzinfo=timezone.utc)
    moments = iter(start + timedelta(seconds=index) for index in range(10))
    suffixes = iter(("aaaa1111", "bbbb2222", "legacy1"))
    return SessionStore(
        root=root,
        clock=lambda: next(moments),
        id_factory=lambda: next(suffixes),
    )


def _capture(store: SessionStore) -> SessionHandle:
    info = BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="dutchmate-rp2040",
        firmware="0.1.0",
        capabilities=frozenset({"gpio_control", "uart_receive", "uart_send"}),
    )
    return store.create_session(
        command="capture --seconds 1",
        backend_snapshot=BackendSnapshot(
            info=info,
            capabilities=frozenset({"gpio_control", "uart_receive"}),
            capability_policy=_tx_policy(),
            segment=_enhanced_segment(),
            integrity=_enhanced_integrity(),
        ),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )


def test_mark_and_clear_baseline_endpoints_work_while_disconnected(tmp_path: Path) -> None:
    store = _store(tmp_path)
    first = _capture(store)
    store.complete_session(first)
    second = _capture(store)
    store.complete_session(second)
    client = TestClient(create_app(BaselineRuntime(store)))

    marked = client.post(f"/sessions/{first.session_id}/baseline")
    listed = client.get("/sessions")
    detailed = client.get(f"/sessions/{first.session_id}")
    wrong_clear = client.delete(f"/sessions/{second.session_id}/baseline")
    cleared = client.delete(f"/sessions/{first.session_id}/baseline")

    assert marked.status_code == 200
    assert marked.json()["changed"] is True
    assert marked.json()["previous_session_id"] is None
    assert marked.json()["integrity"]["loss_status"] == "none_reported"
    assert listed.json()["items"][1]["baseline"] is True
    assert detailed.json()["baseline"] is True
    assert wrong_clear.status_code == 200
    assert wrong_clear.json()["changed"] is False
    assert cleared.status_code == 200
    assert cleared.json()["changed"] is True


def test_baseline_endpoint_maps_state_schema_and_pointer_faults(tmp_path: Path) -> None:
    store = _store(tmp_path)
    active = _capture(store)
    legacy = store.create_session(command="capture")
    client = TestClient(create_app(BaselineRuntime(store)))

    state_error = client.post(f"/sessions/{active.session_id}/baseline")
    schema_error = client.post(f"/sessions/{legacy.session_id}/baseline")

    assert state_error.status_code == 409
    assert state_error.json()["error"] == "invalid_session_state"
    assert state_error.json()["context"] == {
        "operation": "mark_baseline",
        "session_id": active.session_id,
        "reason": "state_not_completed",
    }
    assert schema_error.status_code == 409
    assert schema_error.json()["error"] == "unsupported_session_schema"
    assert schema_error.json()["context"]["detected_schema_version"] == 0

    (tmp_path / "baseline.json").write_text("not JSON", encoding="utf-8")
    pointer_error = client.delete(f"/sessions/{active.session_id}/baseline")
    assert pointer_error.status_code == 500
    assert pointer_error.json()["error"] == "persistence_fault"


def test_compare_endpoint_returns_bounded_deltas_and_maps_preconditions(
    tmp_path: Path,
) -> None:
    store = _store(tmp_path)
    baseline = _capture(store)
    _append_line(store, baseline, b"BOOT_OK\n", timestamp_us=100)
    store.complete_session(baseline)
    subject = _capture(store)
    _append_line(store, subject, b"ERROR\n", timestamp_us=150)
    store.complete_session(subject)
    active = _capture(store)
    store.mark_baseline(baseline.session_id)
    client = TestClient(create_app(BaselineRuntime(store)))

    compared = client.get(f"/sessions/{subject.session_id}/compare")
    active_error = client.get(f"/sessions/{active.session_id}/compare")
    client.delete(f"/sessions/{baseline.session_id}/baseline")
    missing_error = client.get(f"/sessions/{subject.session_id}/compare")

    assert compared.status_code == 200
    assert compared.json()["baseline_session_id"] == baseline.session_id
    assert compared.json()["session_id"] == subject.session_id
    assert compared.json()["line_window_limit"] == 300
    assert {item["type"]: item["delta"] for item in compared.json()["pattern_counts"]} == {
        "failure": 1,
        "success": -1,
    }
    assert compared.json()["timing_comparable"] is True
    assert active_error.status_code == 409
    assert active_error.json()["context"]["reason"] == "state_not_terminal"
    assert missing_error.status_code == 404
    assert missing_error.json()["context"] == {
        "operation": "compare_session",
        "session_id": subject.session_id,
        "reason": "baseline_not_designated",
    }


def _append_line(
    store: SessionStore,
    handle: SessionHandle,
    data: bytes,
    *,
    timestamp_us: int,
) -> None:
    event = UartReceiveEvent(
        segment_id=0,
        timestamp_us=timestamp_us,
        channel=0,
        data=data,
    )
    store.append_uart_capture(
        handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )
