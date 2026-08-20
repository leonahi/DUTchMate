from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from helpers import FakeRuntime, _enhanced_segment, disconnected_status

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.models import (
    EvidenceTypeCount,
    FirstErrorReference,
    LegacySessionListItem,
    LineProcessing,
    NativeSessionDetail,
    NativeSessionListItem,
    RecentLogLine,
    RecentLogs,
    SessionArtifact,
    SessionDetail,
    SessionListPage,
    SessionQueryError,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_service.app import create_app
from dutchmate_service.schemas import recent_logs_payload


class SessionRuntime(FakeRuntime):
    def __init__(
        self,
        *,
        page: SessionListPage | None = None,
        detail: SessionDetail | None = None,
        store: SessionStore | None = None,
    ) -> None:
        super().__init__(disconnected_status())
        self.page = page
        self.detail = detail
        self.store = store
        self.list_requests: list[tuple[int, str | None]] = []
        self.detail_requests: list[str] = []
        self.log_requests: list[tuple[str | None, int]] = []

    def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        self.list_requests.append((limit, cursor))
        if self.store is not None:
            return self.store.list_session_page(limit=limit, cursor=cursor)
        assert self.page is not None
        return self.page

    def get_session(self, session_id: str) -> SessionDetail:
        self.detail_requests.append(session_id)
        if self.store is not None:
            return self.store.get_session_detail(session_id)
        assert self.detail is not None
        return self.detail

    def recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = 300,
    ) -> RecentLogs:
        self.log_requests.append((session_id, lines))
        assert self.store is not None
        return self.store.replay_recent_logs(session_id=session_id, lines=lines)


def test_list_sessions_endpoint_serializes_discriminated_page() -> None:
    native = _native_item()
    legacy = LegacySessionListItem(
        session_id="20260820T115900Z-legacy",
        started_at="2026-08-20T11:59:00Z",
        command="capture",
        firmware="0.0.1",
        device="old-helper",
    )
    runtime = SessionRuntime(
        page=SessionListPage(items=(native, legacy), next_cursor="next-page")
    )

    response = TestClient(create_app(runtime)).get(
        "/sessions",
        params={"limit": 2, "cursor": "current-page"},
    )

    assert response.status_code == 200
    assert runtime.list_requests == [(2, "current-page")]
    payload = response.json()
    assert payload["next_cursor"] == "next-page"
    assert payload["items"][0]["schema_version"] == 1
    assert payload["items"][0]["compatibility"] == "native"
    assert payload["items"][0]["segment_count"] == 1
    assert payload["items"][0]["integrity"]["loss_status"] == "none_reported"
    assert payload["items"][0]["first_error"] == {
        "pattern": "ERROR",
        "detected_pattern_index": 3,
        "segment_id": 0,
        "timestamp_us": 10,
        "channel": 0,
        "ingestion_index": 4,
        "line_index_in_event": 0,
    }
    assert "match_excerpt" not in payload["items"][0]["first_error"]
    assert payload["items"][1] == {
        "session_id": "20260820T115900Z-legacy",
        "started_at": "2026-08-20T11:59:00Z",
        "command": "capture",
        "firmware": "0.0.1",
        "device": "old-helper",
        "schema_version": 0,
        "compatibility": "legacy_read_only",
        "migration_required": True,
        "migration_available": False,
    }


def test_get_session_endpoint_serializes_bounded_native_detail() -> None:
    runtime = SessionRuntime(detail=_native_detail())

    response = TestClient(create_app(runtime)).get(
        "/sessions/20260820T120000Z-native"
    )

    assert response.status_code == 200
    assert runtime.detail_requests == ["20260820T120000Z-native"]
    payload = response.json()
    assert payload["schema_version"] == 1
    assert payload["compatibility"] == "native"
    assert payload["segments"][0]["segment_id"] == 0
    assert payload["pattern_counts"] == {"failure": 1}
    assert payload["hardware_event_counts"] == {"buffer_status": 2}
    assert payload["unresolved_uart_tx_attempts"] == 0
    assert payload["artifact_manifest"][1] == {
        "name": "uart_raw.log",
        "bytes": 12,
        "records": None,
    }
    assert "uart_events" not in payload
    assert "detected_patterns" not in payload


def test_session_endpoints_use_validation_and_query_error_contracts(tmp_path: Path) -> None:
    runtime = SessionRuntime(store=SessionStore(root=tmp_path))
    client = TestClient(create_app(runtime))

    invalid_limit = client.get("/sessions", params={"limit": 101})
    assert invalid_limit.status_code == 400
    assert invalid_limit.json()["error"] == "invalid_argument"
    assert invalid_limit.json()["detail_truncated"] is False

    invalid_cursor = client.get("/sessions", params={"cursor": "not-base64"})
    assert invalid_cursor.status_code == 400
    assert invalid_cursor.json()["error"] == "invalid_argument"

    missing = client.get("/sessions/20260820T120000Z-missing")
    assert missing.status_code == 404
    assert missing.json()["error"] == "not_found"
    assert missing.json()["context"] == {
        "operation": "get_session",
        "session_id": "20260820T120000Z-missing",
    }


def test_unsupported_session_schema_returns_exact_context() -> None:
    class UnsupportedRuntime(SessionRuntime):
        def get_session(self, session_id: str) -> SessionDetail:
            raise SessionQueryError(
                error="unsupported_session_schema",
                operation="get_session",
                session_id=session_id,
                detected_schema_version=7,
                detail="unsupported session schema",
            )

    response = TestClient(create_app(UnsupportedRuntime())).get(
        "/sessions/20260820T120000Z-unknown"
    )

    assert response.status_code == 409
    assert response.json()["context"] == {
        "operation": "get_session",
        "session_id": "20260820T120000Z-unknown",
        "detected_schema_version": 7,
        "supported_schema_versions": [1],
    }


def test_default_service_composition_queries_sessions_while_disconnected(tmp_path: Path) -> None:
    handle = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "legacy",
    ).create_session(command="capture", firmware="0.0.1", device="old-helper")
    client = TestClient(create_app(session_root=tmp_path))

    page = client.get("/sessions")
    detail = client.get(f"/sessions/{handle.session_id}")

    assert page.status_code == 200
    assert page.json()["items"][0]["session_id"] == handle.session_id
    assert page.json()["items"][0]["compatibility"] == "legacy_read_only"
    assert detail.status_code == 200
    assert detail.json()["session_id"] == handle.session_id
    assert detail.json()["artifact_manifest"][0]["name"] == "metadata.json"


def test_recent_logs_endpoint_replays_native_uart_and_validates_limit(tmp_path: Path) -> None:
    store = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 8, 20, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "logs",
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=BackendSnapshot(
            info=BackendInfo(
                mode="enhanced",
                port="/dev/ttyACM0",
                device="dutchmate-rp2040",
                firmware="0.1.0",
                capabilities=frozenset(
                    {"uart_receive", "gpio_control", "device_timestamp"}
                ),
            ),
            capabilities=frozenset(
                {"uart_receive", "gpio_control", "device_timestamp"}
            ),
            capability_policy=BackendCapabilityPolicy(
                uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
            ),
            segment=_enhanced_segment(),
            integrity=UartIntegrity(
                loss_status="none_reported",
                observation_scope="debug_helper_rx_buffer",
                dropped_bytes=0,
            ),
        ),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=10, data=b"hello\n")
    store.append_uart_capture(
        handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )
    store.complete_session(handle)
    runtime = SessionRuntime(store=store)
    client = TestClient(create_app(runtime))

    response = client.get(
        "/dut/logs",
        params={"session_id": handle.session_id, "lines": 7},
    )
    invalid = client.get("/dut/logs", params={"lines": 1001})
    composed = TestClient(create_app(session_root=tmp_path)).get("/dut/logs")

    assert response.status_code == 200
    assert runtime.log_requests == [(handle.session_id, 7)]
    assert response.json()["complete_lines"][0]["line_text"] == "hello\n"
    assert response.json()["complete_lines"][0]["line_raw_b64"] == "aGVsbG8K"
    assert response.json()["response_truncated"] is False
    assert invalid.status_code == 400
    assert invalid.json()["error"] == "invalid_argument"
    assert composed.status_code == 200
    assert composed.json()["session_selection"] == "latest_terminal"
    assert composed.json()["session_id"] == handle.session_id


def test_recent_logs_payload_removes_oldest_whole_records_to_fit_body_cap() -> None:
    records = tuple(
        RecentLogLine(
            segment_id=0,
            channel=0,
            timestamp_us=index,
            ingestion_index=index,
            line_index_in_event=0,
            line_raw_b64="eA==" * 16000,
            line_text="x" * 64000,
        )
        for index in range(5)
    )
    payload = recent_logs_payload(
        RecentLogs(
            session_selection="explicit",
            session_id="20260821T120000Z-large",
            active=False,
            snapshot_event_count=5,
            complete_lines=records,
            partial_lines=(),
            oversized_lines=(),
            integrity=UartIntegrity(
                loss_status="none_reported",
                observation_scope="debug_helper_rx_buffer",
                dropped_bytes=0,
            ),
            line_processing=LineProcessing(),
            reconnect_timeout_s=5.0,
            interrupted=False,
            resumed=False,
            storage={"evidence_bytes_written": 1},
            truncated=False,
            truncation=None,
            timestamp_provenance=(),
        )
    )

    body = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8")
    assert len(body) <= 262144
    assert payload["response_truncated"] is True
    omitted = payload["omitted_complete_lines"]
    assert isinstance(omitted, int) and omitted >= 1
    assert [record["ingestion_index"] for record in payload["complete_lines"]] == list(
        range(omitted, 5)
    )
    assert all(len(record["line_text"]) == 64000 for record in payload["complete_lines"])


def _native_item() -> NativeSessionListItem:
    return NativeSessionListItem(
        session_id="20260820T120000Z-native",
        started_at="2026-08-20T12:00:00Z",
        state="completed",
        workflow="capture",
        ended_at="2026-08-20T12:00:01Z",
        end_reason="duration_elapsed",
        backend_mode="enhanced",
        baseline=False,
        truncated=False,
        truncation=None,
        interrupted=False,
        resumed=False,
        segment_count=1,
        integrity=UartIntegrity(
            loss_status="none_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=0,
        ),
        line_processing=LineProcessing(),
        first_error=FirstErrorReference(
            pattern="ERROR",
            detected_pattern_index=3,
            segment_id=0,
            timestamp_us=10,
            channel=0,
            ingestion_index=4,
            line_index_in_event=0,
        ),
    )


def _native_detail() -> NativeSessionDetail:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
    )
    return NativeSessionDetail(
        summary=_native_item(),
        command="capture --seconds 1",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
        error=None,
        backend_identity={
            "port": "/dev/ttyACM0",
            "device": "dutchmate-rp2040",
            "firmware": "0.1.0",
        },
        backend_capabilities=("uart_receive",),
        capabilities=("uart_receive",),
        capability_policy=policy,
        commanded_boot_mode=None,
        storage={
            "evidence_budget_bytes": 52428800,
            "evidence_bytes_written": 15,
            "metadata_max_bytes": 262144,
        },
        segments=({"segment_id": 0},),
        first_error=None,
        pattern_counts=(EvidenceTypeCount(type="failure", count=1),),
        hardware_event_counts=(EvidenceTypeCount(type="buffer_status", count=2),),
        unresolved_uart_tx_attempts=0,
        artifacts=(
            SessionArtifact(name="metadata.json", bytes=1000, records=1),
            SessionArtifact(name="uart_raw.log", bytes=12, records=None),
        ),
    )
