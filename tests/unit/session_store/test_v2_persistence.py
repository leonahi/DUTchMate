from __future__ import annotations

import base64
import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot, fixed_clock, read_jsonl

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.backends import (
    BackendSnapshot,
    BufferOverflowEvent,
    UartIntegrity,
    UartReceiveEvent,
)
from dutchmate_core.operations import EvidenceCursor, EvidenceRange
from dutchmate_core.profile import DutProfile, DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.metadata import (
    MAX_V2_JSONL_RECORD_BYTES,
    METADATA_MAX_BYTES,
    MIN_V2_EVIDENCE_BUDGET_BYTES,
)
from dutchmate_core.session_store.models import (
    SessionHandle,
    SessionPersistenceError,
    V2EvidenceAdmission,
    V2SessionDetail,
)
from dutchmate_core.session_store.store import SessionStore


def _profile() -> DutProfile:
    return resolve_dut_profile(
        DutProfileConfig(),
        mode="enhanced",
        serial_port="/dev/ttyACM0",
    )


def _failure_pattern() -> dict[str, object]:
    return {
        "pattern": "ERROR",
        "segment_id": 0,
        "timestamp_us": 101,
        "channel": 0,
        "ingestion_index": 0,
        "line_index_in_event": 0,
        "line_start_ingestion_index": 0,
        "line_start_event_offset": 0,
        "line_end_ingestion_index": 0,
        "line_end_event_offset": 13,
        "total_line_bytes": 13,
        "match_start_byte": 0,
        "match_end_byte": 5,
        "match_excerpt": {
            "start_byte": 0,
            "end_byte": 13,
            "text": "ERROR failed\n",
            "raw_b64": base64.b64encode(b"ERROR failed\n").decode("ascii"),
            "excerpt_truncated": False,
        },
    }


def _enhanced_snapshot_at(segment_id: int) -> BackendSnapshot:
    snapshot = enhanced_snapshot()
    assert snapshot.segment is not None
    return replace(snapshot, segment=replace(snapshot.segment, segment_id=segment_id))


def _append_until_rollover(
    store: SessionStore,
    handle: SessionHandle,
    event: UartReceiveEvent,
) -> V2EvidenceAdmission:
    current = handle
    for _attempt in range(100):
        admission = store.append_v2_uart_receive(current, event=event)
        if admission.rolled_over:
            return admission
        current = admission.handle
    pytest.fail("v2 UART evidence did not roll over within its bounded test budget")


def _fill_v2_budget(store: SessionStore, handle: SessionHandle) -> None:
    while True:
        metadata = store.load_metadata(handle.session_id)
        storage = metadata["storage"]
        assert isinstance(storage, dict)
        written = storage["evidence_bytes_written"]
        budget = storage["evidence_budget_bytes"]
        assert isinstance(written, int)
        assert isinstance(budget, int)
        remaining = budget - written
        if remaining == 0:
            return
        sequence = metadata["next_evidence_seq"]
        assert isinstance(sequence, int)
        segment_id = metadata["segments"][-1]["segment_id"]  # type: ignore[index]
        empty_record = {
            "evidence_seq": sequence,
            "type": "reconnect_started",
            "recorded_at": "2026-07-14T12:30:45Z",
            "segment_id": segment_id,
            "detail": {"padding": ""},
        }
        overhead = len(
            (json.dumps(empty_record, separators=(",", ":")) + "\n").encode("utf-8")
        )
        target_size = min(65000, remaining)
        assert target_size >= overhead
        store.append_v2_connection_event(
            handle,
            event_type="reconnect_started",
            segment_id=segment_id,
            detail={"padding": "x" * (target_size - overhead)},
        )


def test_v2_creation_publishes_required_artifacts_and_terminal_reserve(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")

    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    assert {path.name for path in handle.paths.root.iterdir()} == {
        ".terminal-reserve",
        "connection_events.jsonl",
        "detected_patterns.json",
        "hardware_events.jsonl",
        "metadata.json",
        "operation_events.jsonl",
        "uart_events.jsonl",
        "uart_raw.log",
    }
    assert handle.paths.terminal_reserve.stat().st_size == METADATA_MAX_BYTES
    metadata = store.load_metadata(handle.session_id)
    assert metadata["schema_version"] == 2
    assert metadata["state"] == "active"
    assert metadata["profile_digest_sha256"] == _profile().digest_sha256
    assert metadata["effective_profile"] == _profile().projection()
    assert metadata["storage"] == {
        "evidence_budget_bytes": 52428800,
        "evidence_bytes_written": 3,
        "metadata_max_bytes": METADATA_MAX_BYTES,
    }
    assert metadata["next_evidence_seq"] == 0
    assert len(json.dumps(metadata, separators=(",", ":")).encode("utf-8")) < METADATA_MAX_BYTES


def test_v2_creation_rejects_budget_below_maximum_primary_unit_bound(
    tmp_path: Path,
) -> None:
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: "abc12345",
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES - 1,
    )

    with pytest.raises(ValueError, match="schema-v2 evidence budget"):
        store.create_v2_session(
            profile=_profile(),
            backend_snapshot=enhanced_snapshot(),
        )

    assert list(tmp_path.iterdir()) == []


def test_v2_rejects_oversized_primary_jsonl_record_before_mutation(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    metadata_before = handle.paths.metadata.read_bytes()

    with pytest.raises(ValueError, match="primary JSONL record"):
        store.append_v2_connection_event(
            handle,
            event_type="reconnect_started",
            segment_id=0,
            detail={"padding": "x" * MAX_V2_JSONL_RECORD_BYTES},
        )

    assert handle.paths.connection_events.read_bytes() == b""
    assert handle.paths.metadata.read_bytes() == metadata_before


def test_v2_rejects_more_than_twelve_patterns_for_one_uart_unit(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    metadata_before = handle.paths.metadata.read_bytes()

    with pytest.raises(ValueError, match="at most 12 detected patterns"):
        store.append_v2_uart_receive(
            handle,
            event=UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=101,
                data=b"ERROR failed\n",
            ),
            detected_patterns=[_failure_pattern() for _index in range(13)],
        )

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    assert handle.paths.detected_patterns.read_bytes() == b"[]\n"
    assert handle.paths.metadata.read_bytes() == metadata_before


def test_v2_exact_budget_is_admitted_and_next_whole_unit_rolls_over(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    _fill_v2_budget(store, handle)

    assert store.load_metadata(handle.session_id)["storage"][  # type: ignore[index]
        "evidence_bytes_written"
    ] == MIN_V2_EVIDENCE_BUDGET_BYTES

    rolled = store.append_v2_connection_event(
        handle,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "test"},
    )

    assert rolled.rolled_over is True
    assert rolled.handle.session_id != handle.session_id
    assert store.load_metadata(handle.session_id)["end_reason"] == "rollover_size"


def test_v2_creation_failure_never_publishes_partial_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real_write = persistence.write_serialized

    def fail_operation_artifact(path: Path, data: bytes) -> None:
        if path.name == "operation_events.jsonl":
            raise SessionPersistenceError(
                operation="write",
                path=path,
                detail="disk full",
            )
        real_write(path, data)

    monkeypatch.setattr(persistence, "write_serialized", fail_operation_artifact)
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")

    with pytest.raises(SessionPersistenceError, match="disk full"):
        store.create_v2_session(
            profile=_profile(),
            backend_snapshot=enhanced_snapshot(),
        )

    assert list(tmp_path.iterdir()) == []


def test_v2_terminal_metadata_stays_within_cap_and_consumes_reserve(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    store.fail_session(
        handle,
        end_reason="backend_input_error",
        error_code="backend_input_error",
        detail="x" * (METADATA_MAX_BYTES * 2),
    )

    metadata_bytes = handle.paths.metadata.read_bytes()
    metadata = json.loads(metadata_bytes)
    assert len(metadata_bytes) <= METADATA_MAX_BYTES
    assert metadata["state"] == "failed"
    assert metadata["error"]["detail_truncated"] is True
    assert not handle.paths.terminal_reserve.exists()


def test_v2_uart_rx_assigns_contiguous_sequence_and_exact_raw_offsets(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    first = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=101, data=b"\xffA")
    second = UartReceiveEvent(segment_id=0, channel=1, timestamp_us=102, data=b"B\n")

    first_admission = store.append_v2_uart_receive(handle, event=first)
    second_admission = store.append_v2_uart_receive(handle, event=second)

    assert first_admission.handle == handle
    assert first_admission.evidence_seq == 0
    assert second_admission.evidence_seq == 1
    assert handle.paths.uart_raw.read_bytes() == b"\xffAB\n"
    records = read_jsonl(handle.paths.uart_events)
    assert [record["evidence_seq"] for record in records] == [0, 1]
    assert [(record["raw_offset_start"], record["raw_offset_end"]) for record in records] == [
        (0, 2),
        (2, 4),
    ]
    raw = handle.paths.uart_raw.read_bytes()
    for record in records:
        start = record["raw_offset_start"]
        end = record["raw_offset_end"]
        data_b64 = record["data_b64"]
        assert isinstance(start, int)
        assert isinstance(end, int)
        assert isinstance(data_b64, str)
        assert base64.b64decode(data_b64) == raw[start:end]
    assert store.load_metadata(handle.session_id)["next_evidence_seq"] == 2


def test_v2_uart_rx_atomically_persists_derived_pattern_and_first_error(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    admission = store.append_v2_uart_receive(
        handle,
        event=UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=101,
            data=b"ERROR failed\n",
        ),
        detected_patterns=[_failure_pattern()],
    )

    assert admission.evidence_seq == 0
    assert store.load_metadata(handle.session_id)["next_evidence_seq"] == 1
    patterns = json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8"))
    assert patterns[0]["source_evidence_seq"] == 0
    page = store.list_session_page()
    summary = page.items[0]
    assert summary.schema_version == 2
    assert summary.first_error is not None
    assert summary.first_error.pattern == "ERROR"
    assert summary.first_error.source_evidence_seq == 0
    detail = store.get_session_detail(handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.first_error is not None
    assert detail.first_error.match_excerpt.text == "ERROR failed\n"


def test_v2_uart_transaction_failure_rolls_back_and_faults_session(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    real_append = persistence.append_serialized

    def fail_uart_event(path: Path, data: bytes) -> None:
        if path == handle.paths.uart_events:
            raise SessionPersistenceError(
                operation="append",
                path=path,
                detail="disk full",
            )
        real_append(path, data)

    monkeypatch.setattr(persistence, "append_serialized", fail_uart_event)

    with pytest.raises(SessionPersistenceError, match="disk full"):
        store.append_v2_uart_receive(
            handle,
            event=UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=101,
                data=b"ERROR failed\n",
            ),
            detected_patterns=[_failure_pattern()],
        )

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    assert handle.paths.detected_patterns.read_bytes() == b"[]\n"
    metadata = store.load_metadata(handle.session_id)
    assert metadata["state"] == "failed"
    assert metadata["end_reason"] == "persistence_error"
    quality = metadata["evidence_quality"]
    assert isinstance(quality, dict)
    assert quality["local_recording"] == "persistence_fault"
    assert metadata["active_operations"] == {}
    assert metadata["interrupted_operations"]["monitor-1"]["ranges"][-1][  # type: ignore[index]
        "end_evidence_seq_exclusive"
    ] == 1
    assert [record["type"] for record in read_jsonl(handle.paths.operation_events)] == [
        "operation_started"
    ]
    assert not handle.paths.terminal_reserve.exists()


def test_v2_size_rollover_admits_next_whole_uart_unit_in_linked_successor(
    tmp_path: Path,
) -> None:
    payload = bytes(range(256)) * 128
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=101, data=payload)
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path / "rollover",
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    first_handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    rolled = _append_until_rollover(store, first_handle, event)

    assert rolled.handle.session_id != first_handle.session_id
    assert rolled.rolled_over is True
    assert rolled.evidence_seq == 1
    assert rolled.handle.paths.uart_raw.read_bytes() == payload
    predecessor = store.load_metadata(first_handle.session_id)
    successor = store.load_metadata(rolled.handle.session_id)
    assert predecessor["state"] == "completed"
    assert predecessor["end_reason"] == "rollover_size"
    assert predecessor["successor_session_id"] == rolled.handle.session_id
    assert successor["predecessor_session_id"] == first_handle.session_id


def test_recovery_abandons_stale_active_v2_without_inventing_events(tmp_path: Path) -> None:
    creating = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = creating.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    creating.start_v2_operation(
        handle,
        operation_id="monitor-before-restart",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    creating.append_v2_uart_tx_attempt(
        handle,
        attempt_id="tx-before-restart",
        data=b"x",
        operation_id=None,
        transformation={"source": "bytes", "line_ending": "none"},
    )
    creating.append_v2_control_attempt(
        handle,
        attempt_id="control-before-restart",
        role="reset",
        provider="CTRL0",
        parameters={"pulse_ms": 10},
        operation_id=None,
    )

    recovering = SessionStore(root=tmp_path, clock=fixed_clock)
    result = recovering.recover_stale_sessions()

    assert result.recovered_session_ids == (handle.session_id,)
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["state"] == "abandoned"
    assert metadata["end_reason"] == "service_restart"
    assert metadata["active_operations"] == {}
    assert metadata["interrupted_operations"]["monitor-before-restart"]["ranges"][-1][  # type: ignore[index]
        "end_evidence_seq_exclusive"
    ] == 3
    assert metadata["operation_summary"] == {
        "started": 1,
        "completed": 0,
        "failed": 0,
        "active": 0,
    }
    assert read_jsonl(handle.paths.connection_events) == []
    assert not handle.paths.terminal_reserve.exists()
    detail = recovering.get_session_detail(handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.unresolved_uart_tx_attempts == 1
    assert detail.unresolved_control_attempts == 1


@pytest.mark.parametrize("terminal_state", ["completed", "failed", "abandoned"])
def test_v2_terminalization_closes_and_relinquishes_active_operations_without_results(
    tmp_path: Path,
    terminal_state: str,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )

    if terminal_state == "completed":
        store.complete_session(handle, end_reason="service_shutdown")
    elif terminal_state == "failed":
        store.fail_session(
            handle,
            end_reason="backend_input_error",
            error_code="backend_input_error",
            detail="reader failed",
        )
    else:
        store.abandon_session(handle)

    metadata = store.load_metadata(handle.session_id)
    assert metadata["state"] == terminal_state
    assert metadata["active_operations"] == {}
    assert metadata["operation_summary"] == {
        "started": 1,
        "completed": 0,
        "failed": 0,
        "active": 0,
    }
    assert metadata["interrupted_operations"] == {
        "monitor-1": {
            "operation_type": "monitor",
            "ranges": [
                {
                    "session_id": handle.session_id,
                    "start_evidence_seq": 0,
                    "end_evidence_seq_exclusive": 1,
                }
            ],
        }
    }
    assert [record["type"] for record in read_jsonl(handle.paths.operation_events)] == [
        "operation_started"
    ]


def test_v2_primary_records_share_one_sequence_and_detail_reports_unresolved_attempts(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    store.append_v2_uart_tx_attempt(
        handle,
        attempt_id="tx-1",
        data=b"status\r\n",
        operation_id=None,
        transformation={"source": "text", "line_ending": "crlf"},
    )
    store.append_v2_control_attempt(
        handle,
        attempt_id="control-1",
        role="reset",
        provider="CTRL0",
        parameters={"pulse_ms": 10},
        operation_id=None,
    )
    store.append_v2_connection_event(
        handle,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "usb_disconnect"},
    )
    store.complete_v2_operation(
        handle,
        operation_id="monitor-1",
        outcome="elapsed",
    )

    records = [
        *read_jsonl(handle.paths.operation_events),
        *read_jsonl(handle.paths.hardware_events),
        *read_jsonl(handle.paths.connection_events),
    ]

    def evidence_sequence(record: dict[str, object]) -> int:
        value = record["evidence_seq"]
        assert isinstance(value, int)
        return value

    records.sort(key=evidence_sequence)
    assert [record["evidence_seq"] for record in records] == list(range(5))
    assert [record["type"] for record in records] == [
        "operation_started",
        "uart_tx_attempt",
        "control_attempt",
        "reconnect_started",
        "operation_terminal",
    ]
    terminal = records[-1]
    assert terminal["evidence_ranges"] == [
        {
            "session_id": handle.session_id,
            "start_evidence_seq": 0,
            "end_evidence_seq_exclusive": 5,
        }
    ]
    detail = store.get_session_detail(handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.unresolved_uart_tx_attempts == 1
    assert detail.unresolved_control_attempts == 1
    assert detail.operation_counts == {
        "started": 1,
        "completed": 1,
        "failed": 0,
        "active": 0,
    }
    assert detail.action_counts == {"control_attempt": 1, "uart_tx_attempt": 1}


def test_v2_list_and_detail_use_the_same_operation_state_counts(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    store.complete_v2_operation(handle, operation_id="monitor-1", outcome="elapsed")

    listed = store.list_session_page().items[0]
    detail = store.get_session_detail(handle.session_id)

    assert isinstance(detail, V2SessionDetail)
    expected = {"started": 1, "completed": 1, "failed": 0, "active": 0}
    assert listed.operation_counts == expected  # type: ignore[union-attr]
    assert detail.operation_counts == expected
    assert detail.summary.operation_counts == expected


def test_v2_rolls_over_before_publishing_segment_33(tmp_path: Path) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
    )
    snapshot = enhanced_snapshot()
    handle = store.create_v2_session(profile=_profile(), backend_snapshot=snapshot)

    for segment_id in range(1, 32):
        assert snapshot.segment is not None
        snapshot = replace(
            snapshot,
            segment=replace(snapshot.segment, segment_id=segment_id),
        )
        handle = store.append_v2_segment(handle, backend_snapshot=snapshot)

    assert len(store.load_metadata(handle.session_id)["segments"]) == 32  # type: ignore[arg-type]
    assert snapshot.segment is not None
    next_snapshot = replace(
        snapshot,
        segment=replace(snapshot.segment, segment_id=32),
    )

    successor = store.append_v2_segment(handle, backend_snapshot=next_snapshot)

    assert successor.session_id != handle.session_id
    predecessor_metadata = store.load_metadata(handle.session_id)
    successor_metadata = store.load_metadata(successor.session_id)
    assert predecessor_metadata["state"] == "completed"
    assert predecessor_metadata["end_reason"] == "rollover_segments"
    assert predecessor_metadata["successor_session_id"] == successor.session_id
    assert successor_metadata["predecessor_session_id"] == handle.session_id
    successor_segments = successor_metadata["segments"]
    assert isinstance(successor_segments, list)
    assert [segment["segment_id"] for segment in successor_segments] == [0]


def test_v2_operation_crossing_size_rollover_keeps_id_and_multiple_ranges(
    tmp_path: Path,
) -> None:
    payload = bytes(range(256)) * 128
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=101, data=payload)
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path / "rollover",
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    second = _append_until_rollover(store, handle, event)
    predecessor_active_metadata = store.load_metadata(handle.session_id)
    successor_active_metadata = store.load_metadata(second.handle.session_id)
    assert predecessor_active_metadata["active_operations"] == {}
    assert predecessor_active_metadata["operation_summary"]["active"] == 0  # type: ignore[index]
    assert "monitor-1" in successor_active_metadata["active_operations"]  # type: ignore[operator]
    assert successor_active_metadata["operation_summary"]["active"] == 1  # type: ignore[index]
    terminal = store.complete_v2_operation(
        second.handle,
        operation_id="monitor-1",
        outcome="elapsed",
    )

    assert second.rolled_over is True
    assert second.evidence_seq == 2
    successor_records = read_jsonl(second.handle.paths.operation_events)
    assert successor_records[0]["type"] == "operation_continued"
    assert successor_records[0]["operation_id"] == "monitor-1"
    rollover_records = read_jsonl(second.handle.paths.connection_events)
    assert rollover_records[0] == {
        "evidence_seq": 0,
        "type": "rollover_succeeded",
        "recorded_at": "2026-07-14T12:30:45Z",
        "segment_id": 0,
        "detail": {
            "predecessor_session_id": handle.session_id,
            "reason": "rollover_size",
        },
    }
    terminal_record = read_jsonl(terminal.handle.paths.operation_events)[-1]
    predecessor_next_sequence = store.load_metadata(handle.session_id)[
        "next_evidence_seq"
    ]
    assert terminal_record["evidence_ranges"] == [
        {
            "session_id": handle.session_id,
            "start_evidence_seq": 0,
            "end_evidence_seq_exclusive": predecessor_next_sequence,
        },
        {
            "session_id": second.handle.session_id,
            "start_evidence_seq": 1,
            "end_evidence_seq_exclusive": 4,
        },
    ]
    predecessor_metadata = store.load_metadata(handle.session_id)
    successor_metadata = store.load_metadata(second.handle.session_id)
    assert predecessor_metadata["active_operations"] == {}
    assert predecessor_metadata["operation_summary"]["active"] == 0  # type: ignore[index]
    assert successor_metadata["active_operations"] == {}
    assert successor_metadata["operation_summary"]["active"] == 0  # type: ignore[index]
    with pytest.raises(ValueError, match="already been used"):
        store.start_v2_operation(
            terminal.handle,
            operation_id="monitor-1",
            operation_type="monitor",
            parameters={"duration_s": 1.0},
        )


def test_v2_operation_start_rebuilds_cursor_when_start_record_rolls_over(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    _fill_v2_budget(store, predecessor)

    admission = store.start_v2_operation(
        predecessor,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )

    assert admission.rolled_over is True
    record = read_jsonl(admission.handle.paths.operation_events)[0]
    assert record["start_cursor"] == {
        "session_id": admission.handle.session_id,
        "next_evidence_seq": admission.evidence_seq + 1,
    }
    active = store.load_metadata(admission.handle.session_id)["active_operations"]
    assert active["monitor-1"]["ranges"][0] == {  # type: ignore[index]
        "session_id": admission.handle.session_id,
        "start_evidence_seq": admission.evidence_seq,
        "end_evidence_seq_exclusive": None,
    }


def test_v2_operation_terminal_rebuilds_cursor_and_ranges_when_it_rolls_over(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        predecessor,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    _fill_v2_budget(store, predecessor)

    admission = store.complete_v2_operation(
        predecessor,
        operation_id="monitor-1",
        outcome="elapsed",
    )

    assert admission.rolled_over is True
    record = read_jsonl(admission.handle.paths.operation_events)[-1]
    assert record["end_cursor"] == {
        "session_id": admission.handle.session_id,
        "next_evidence_seq": admission.evidence_seq + 1,
    }
    assert record["evidence_ranges"][-1] == {
        "session_id": admission.handle.session_id,
        "start_evidence_seq": 1,
        "end_evidence_seq_exclusive": admission.evidence_seq + 1,
    }


def test_v2_monitor_reader_starts_at_durable_uart_offset_and_avoids_store_lock(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.append_v2_uart_receive(
        handle,
        event=UartReceiveEvent(0, 1, 0, b"history\n"),
    )
    started = store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    start = EvidenceCursor(started.handle.session_id, started.evidence_seq + 1)
    reader = store.open_v2_monitor_evidence_reader(
        start=start,
        operation_id="monitor-1",
    )
    admitted = store.append_v2_uart_receive(
        started.handle,
        event=UartReceiveEvent(0, 2, 0, b"new\n"),
    )
    end = EvidenceCursor(admitted.handle.session_id, admitted.evidence_seq + 1)

    store._store_lock.acquire()  # noqa: SLF001
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            evidence = executor.submit(reader.read_to, end).result(timeout=0.5)
    finally:
        store._store_lock.release()  # noqa: SLF001

    assert [(item.evidence_seq, item.data) for item in evidence] == [
        (admitted.evidence_seq, b"new\n")
    ]
    reader.close()


def test_v2_monitor_integrity_uses_only_exact_half_open_evidence_ranges(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.append_v2_buffer_overflow(
        handle,
        event=BufferOverflowEvent(0, 1, 0, 3),
    )
    started = store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    store.append_v2_buffer_overflow(
        started.handle,
        event=BufferOverflowEvent(0, 2, 0, 7),
    )
    terminal = store.complete_v2_operation(
        started.handle,
        operation_id="monitor-1",
        outcome="elapsed",
    )
    store.append_v2_buffer_overflow(
        terminal.handle,
        event=BufferOverflowEvent(0, 3, 0, 11),
    )
    terminal_record = store.load_v2_operation_terminal(
        session_id=terminal.handle.session_id,
        operation_id="monitor-1",
    )
    raw_ranges = terminal_record["evidence_ranges"]
    assert isinstance(raw_ranges, list)
    ranges = tuple(
        EvidenceRange(
            session_id=item["session_id"],
            start_evidence_seq=item["start_evidence_seq"],
            end_evidence_seq_exclusive=item["end_evidence_seq_exclusive"],
        )
        for item in raw_ranges
    )

    integrity, _provenance = store.summarize_v2_monitor_evidence(ranges)

    assert integrity == UartIntegrity(
        "loss_reported",
        "debug_helper_rx_buffer",
        7,
    )


@pytest.mark.parametrize("attempt_kind", ["uart_tx", "control"])
def test_v2_action_attempt_rebuilds_current_segment_when_it_rolls_over(
    tmp_path: Path,
    attempt_kind: str,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    snapshot = _enhanced_snapshot_at(1)
    predecessor = store.append_v2_segment(predecessor, backend_snapshot=snapshot)
    _fill_v2_budget(store, predecessor)

    if attempt_kind == "uart_tx":
        admission = store.append_v2_uart_tx_attempt(
            predecessor,
            attempt_id="attempt-1",
            data=b"x",
            operation_id=None,
            transformation={"source": "bytes", "line_ending": "none"},
        )
        record = read_jsonl(admission.handle.paths.operation_events)[0]
    else:
        admission = store.append_v2_control_attempt(
            predecessor,
            attempt_id="attempt-1",
            role="reset",
            provider="CTRL0",
            parameters={"pulse_ms": 10},
            operation_id=None,
        )
        record = read_jsonl(admission.handle.paths.hardware_events)[0]

    assert admission.rolled_over is True
    assert record["segment_id"] == 0


def test_v2_segment_and_connection_records_rebuild_segment_ids_after_rollover(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02", "third003"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    first = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    current = store.append_v2_segment(
        first,
        backend_snapshot=_enhanced_snapshot_at(1),
    )
    _fill_v2_budget(store, current)

    successor = store.append_v2_segment(
        current,
        backend_snapshot=_enhanced_snapshot_at(2),
    )

    assert successor.session_id != current.session_id
    assert [
        segment["segment_id"]
        for segment in store.load_metadata(successor.session_id)["segments"]  # type: ignore[union-attr]
    ] == [0, 1]
    assert read_jsonl(successor.paths.connection_events)[-1]["segment_id"] == 1

    _fill_v2_budget(store, successor)
    admission = store.append_v2_connection_event(
        successor,
        event_type="reconnect_started",
        segment_id=1,
        detail={"reason": "test"},
    )

    assert admission.rolled_over is True
    assert read_jsonl(admission.handle.paths.connection_events)[-1]["segment_id"] == 0


def test_v2_uart_and_patterns_rebuild_segment_and_offsets_after_rollover(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    predecessor = store.append_v2_segment(
        predecessor,
        backend_snapshot=_enhanced_snapshot_at(1),
    )
    _fill_v2_budget(store, predecessor)
    pattern = _failure_pattern()
    pattern["segment_id"] = 1

    admission = store.append_v2_uart_receive(
        predecessor,
        event=UartReceiveEvent(
            segment_id=1,
            channel=0,
            timestamp_us=101,
            data=b"ERROR failed\n",
        ),
        detected_patterns=[pattern],
    )

    assert admission.rolled_over is True
    record = read_jsonl(admission.handle.paths.uart_events)[0]
    assert record["segment_id"] == 0
    assert (record["raw_offset_start"], record["raw_offset_end"]) == (0, 13)
    patterns = json.loads(admission.handle.paths.detected_patterns.read_text(encoding="utf-8"))
    assert patterns[0]["segment_id"] == 0
    assert patterns[0]["source_evidence_seq"] == admission.evidence_seq


def test_v2_successor_creation_failure_marks_predecessor_persistence_fault(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payload = bytes(range(256)) * 128
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=101, data=payload)
    store = SessionStore(
        root=tmp_path / "fault",
        clock=fixed_clock,
        id_factory=lambda: "first001",
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    def fail_successor(**_kwargs: object) -> None:
        raise SessionPersistenceError(
            operation="create directory",
            path=tmp_path / "fault" / "successor",
            detail="disk full",
        )

    monkeypatch.setattr(store, "_create_v2_session_locked", fail_successor)

    with pytest.raises(SessionPersistenceError, match="disk full"):
        for _attempt in range(100):
            store.append_v2_uart_receive(handle, event=event)
        pytest.fail("v2 UART evidence did not reach successor creation")

    metadata = store.load_metadata(handle.session_id)
    assert metadata["state"] == "failed"
    assert metadata["end_reason"] == "persistence_error"
    assert metadata["error"]["code"] == "persistence_fault"  # type: ignore[index]
    assert metadata["evidence_quality"]["local_recording"] == "persistence_fault"  # type: ignore[index]


def test_v2_retention_deletes_terminal_session_but_protects_active_session(
    tmp_path: Path,
) -> None:
    suffixes = iter(("terminal", "active00"))
    creating = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
    )
    terminal = creating.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    creating.complete_session(terminal, end_reason="service_shutdown")
    active = creating.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    result = SessionStore(root=tmp_path, max_count=1).run_retention()

    assert result.diagnostic is None
    assert result.deleted_session_ids == (terminal.session_id,)
    assert result.protected_session_ids == (active.session_id,)
    assert not terminal.paths.root.exists()
    assert active.paths.root.exists()


def test_v2_completed_loss_free_session_can_be_baseline_and_is_retention_protected(
    tmp_path: Path,
) -> None:
    suffixes = iter(("baseline", "subject0"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
    )
    baseline = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.complete_session(baseline, end_reason="service_shutdown")
    marked = store.mark_baseline(baseline.session_id)
    subject = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.complete_session(subject, end_reason="service_shutdown")

    result = SessionStore(root=tmp_path, max_count=1).run_retention()

    assert marked.changed is True
    assert result.deleted_session_ids == (subject.session_id,)
    assert result.protected_session_ids == (baseline.session_id,)
    assert baseline.paths.root.exists()


def test_v2_retention_protects_rollover_sessions_referenced_by_active_operation(
    tmp_path: Path,
) -> None:
    payload = bytes(range(256)) * 128
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=101, data=payload)
    suffixes = iter(("first001", "second02"))
    creating = SessionStore(
        root=tmp_path / "sessions",
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    predecessor = creating.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    creating.start_v2_operation(
        predecessor,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    successor = _append_until_rollover(creating, predecessor, event).handle

    result = SessionStore(root=tmp_path / "sessions", max_count=1).run_retention()

    assert result.diagnostic == "retention_blocked"
    assert result.deleted_session_ids == ()
    assert result.protected_session_ids == tuple(
        sorted((predecessor.session_id, successor.session_id))
    )


def test_v2_rollover_runs_retention_after_predecessor_becomes_terminal(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
        max_count=1,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    _fill_v2_budget(store, predecessor)

    admission = store.append_v2_connection_event(
        predecessor,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "test"},
    )

    assert admission.rolled_over is True
    assert not predecessor.paths.root.exists()
    assert admission.handle.paths.root.exists()
    assert store.retention_status.deleted_session_ids == (predecessor.session_id,)


@pytest.mark.parametrize("attempt_kind", ["uart_tx", "control"])
def test_v2_attempt_result_crosses_rollover_and_retains_origin_until_resolved(
    tmp_path: Path,
    attempt_kind: str,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
        max_count=1,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    if attempt_kind == "uart_tx":
        attempt = store.append_v2_uart_tx_attempt(
            predecessor,
            attempt_id="attempt-1",
            data=b"x",
            operation_id=None,
            transformation={"source": "bytes", "line_ending": "none"},
        )
    else:
        attempt = store.append_v2_control_attempt(
            predecessor,
            attempt_id="attempt-1",
            role="reset",
            provider="CTRL0",
            parameters={"pulse_ms": 10},
            operation_id=None,
        )
    _fill_v2_budget(store, predecessor)
    rollover = store.append_v2_connection_event(
        predecessor,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "test"},
    )

    assert rollover.rolled_over is True
    assert predecessor.paths.root.exists()
    assert store.retention_status.diagnostic == "retention_blocked"
    assert predecessor.session_id in store.retention_status.protected_session_ids
    pending_detail = store.get_session_detail(rollover.handle.session_id)
    assert isinstance(pending_detail, V2SessionDetail)
    assert pending_detail.unresolved_uart_tx_attempts == (attempt_kind == "uart_tx")
    assert pending_detail.unresolved_control_attempts == (attempt_kind == "control")

    if attempt_kind == "uart_tx":
        result = store.append_v2_uart_tx_result(
            rollover.handle,
            attempt_id="attempt-1",
            status="accepted",
            accepted_bytes=1,
        )
        result_record = read_jsonl(result.handle.paths.operation_events)[-1]
    else:
        result = store.append_v2_control_result(
            rollover.handle,
            attempt_id="attempt-1",
            status="accepted",
        )
        result_record = read_jsonl(result.handle.paths.hardware_events)[-1]

    assert result_record["attempt_session_id"] == predecessor.session_id
    assert result_record["attempt_evidence_seq"] == attempt.evidence_seq
    assert not predecessor.paths.root.exists()
    assert store.retention_status.deleted_session_ids == (predecessor.session_id,)
    detail = store.get_session_detail(result.handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.unresolved_uart_tx_attempts == 0
    assert detail.unresolved_control_attempts == 0


@pytest.mark.parametrize("attempt_kind", ["uart_tx", "control"])
def test_v2_recovery_keeps_cross_rollover_attempt_unknown_after_crash(
    tmp_path: Path,
    attempt_kind: str,
) -> None:
    suffixes = iter(("first001", "second02"))
    creating = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
        max_count=1,
    )
    predecessor = creating.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    creating.start_v2_operation(
        predecessor,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    if attempt_kind == "uart_tx":
        attempt = creating.append_v2_uart_tx_attempt(
            predecessor,
            attempt_id="attempt-1",
            data=b"x",
            operation_id="monitor-1",
            transformation={"source": "bytes", "line_ending": "none"},
        )
        attempt_type = "uart_tx_attempt"
    else:
        attempt = creating.append_v2_control_attempt(
            predecessor,
            attempt_id="attempt-1",
            role="reset",
            provider="CTRL0",
            parameters={"pulse_ms": 10},
            operation_id="monitor-1",
        )
        attempt_type = "control_attempt"
    _fill_v2_budget(creating, predecessor)
    rollover = creating.append_v2_connection_event(
        predecessor,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "test"},
    )

    assert rollover.rolled_over is True
    assert predecessor.paths.root.exists()
    assert creating.retention_status.diagnostic == "retention_blocked"

    recovering = SessionStore(root=tmp_path, clock=fixed_clock, max_count=1)
    recovery = recovering.recover_stale_sessions()

    assert recovery.recovered_session_ids == (rollover.handle.session_id,)
    assert not predecessor.paths.root.exists()
    metadata = recovering.load_metadata(rollover.handle.session_id)
    assert metadata["state"] == "abandoned"
    assert metadata["active_operations"] == {}
    assert "monitor-1" in metadata["interrupted_operations"]  # type: ignore[operator]
    assert metadata["pending_attempts"] == {
        f"{attempt_type}:attempt-1": {
            "attempt_type": attempt_type,
            "attempt_id": "attempt-1",
            "session_id": predecessor.session_id,
            "evidence_seq": attempt.evidence_seq,
        }
    }
    assert recovering.retention_status.deleted_session_ids == (predecessor.session_id,)
    assert all(
        record["type"] != f"{attempt_type.removesuffix('_attempt')}_result"
        for record in (
            read_jsonl(rollover.handle.paths.operation_events)
            + read_jsonl(rollover.handle.paths.hardware_events)
        )
    )
    detail = recovering.get_session_detail(rollover.handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.unresolved_uart_tx_attempts == (attempt_kind == "uart_tx")
    assert detail.unresolved_control_attempts == (attempt_kind == "control")


def test_v2_operation_id_tracking_stays_bounded_across_rollover_and_retention(
    tmp_path: Path,
) -> None:
    suffixes = iter(("first001", "second02"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
        max_count=1,
    )
    predecessor = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    initial_metadata_bytes = predecessor.paths.metadata.stat().st_size
    for index in range(64):
        prefix = f"monitor-{index:03d}-"
        operation_id = prefix + ("x" * (128 - len(prefix)))
        store.start_v2_operation(
            predecessor,
            operation_id=operation_id,
            operation_type="monitor",
            parameters={"duration_s": 1.0},
        )
        store.complete_v2_operation(
            predecessor,
            operation_id=operation_id,
            outcome="elapsed",
        )

    predecessor_metadata = store.load_metadata(predecessor.session_id)
    assert "operation_ids" not in predecessor_metadata
    assert predecessor.paths.metadata.stat().st_size <= initial_metadata_bytes + 256
    _fill_v2_budget(store, predecessor)
    rollover = store.append_v2_connection_event(
        predecessor,
        event_type="reconnect_started",
        segment_id=0,
        detail={"reason": "test"},
    )

    assert not predecessor.paths.root.exists()
    successor_metadata = store.load_metadata(rollover.handle.session_id)
    assert "operation_ids" not in successor_metadata
    assert rollover.handle.paths.metadata.stat().st_size <= initial_metadata_bytes + 512
    fresh = store.start_v2_operation(
        rollover.handle,
        operation_id="monitor-after-rollover",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    assert fresh.handle == rollover.handle


@pytest.mark.parametrize("projection", ["list", "detail"])
def test_v2_retrieval_retries_until_metadata_and_evidence_form_one_snapshot(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    projection: str,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    real_read_json_list = persistence.read_json_list
    interleave = True

    def read_json_list(path: Path) -> list[object]:
        nonlocal interleave
        result = real_read_json_list(path)
        if interleave and path == handle.paths.detected_patterns:
            interleave = False
            store.append_v2_uart_receive(
                handle,
                event=UartReceiveEvent(
                    segment_id=0,
                    channel=0,
                    timestamp_us=101,
                    data=b"ERROR failed\n",
                ),
                detected_patterns=[_failure_pattern()],
            )
        return result

    monkeypatch.setattr(persistence, "read_json_list", read_json_list)

    if projection == "list":
        snapshot = store.list_session_page().items[0]
    else:
        detail = store.get_session_detail(handle.session_id)
        assert isinstance(detail, V2SessionDetail)
        snapshot = detail.summary
        assert detail.first_error is not None

    assert snapshot.first_error is not None
    assert snapshot.first_error.pattern == "ERROR"
    assert snapshot.storage == store.load_metadata(handle.session_id)["storage"]


def test_v2_recent_log_replay_uses_schema_v2_uart_records(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.append_v2_uart_receive(
        handle,
        event=UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=101,
            data=b"BOOT_OK\npartial",
        ),
    )

    replay = store.replay_recent_logs(
        session_id=handle.session_id,
        lines=10,
    )

    assert replay.schema_version == 2
    assert [line.line_text for line in replay.complete_lines] == ["BOOT_OK\n"]
    assert [line.line_text for line in replay.partial_lines] == ["partial"]
    assert replay.snapshot_event_count == 1


def test_v2_comparison_is_bounded_and_uses_durable_uart_evidence(tmp_path: Path) -> None:
    suffixes = iter(("baseline", "subject0"))
    store = SessionStore(
        root=tmp_path,
        clock=fixed_clock,
        id_factory=lambda: next(suffixes),
    )
    baseline = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.append_v2_uart_receive(
        baseline,
        event=UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=100,
            data=b"OLD\n",
        ),
    )
    store.complete_session(baseline, end_reason="service_shutdown")
    store.mark_baseline(baseline.session_id)
    subject = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.append_v2_uart_receive(
        subject,
        event=UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=105,
            data=b"NEW\n",
        ),
    )
    store.complete_session(subject, end_reason="service_shutdown")

    comparison = store.compare_session(subject.session_id)

    assert comparison.baseline.session_id == baseline.session_id
    assert comparison.subject.session_id == subject.session_id
    assert comparison.baseline.workflow is None
    assert comparison.subject.workflow is None
    assert comparison.timing_comparable is True
    assert {(change.text_excerpt, change.delta) for change in comparison.line_changes} == {
        ("OLD ", -1),
        ("NEW ", 1),
    }


def test_v2_attempt_results_require_preceding_attempt_and_resolve_visibility(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    with pytest.raises(ValueError, match="preceding unresolved UART TX attempt"):
        store.append_v2_uart_tx_result(
            handle,
            attempt_id="tx-1",
            status="accepted",
            accepted_bytes=1,
        )
    with pytest.raises(ValueError, match="preceding unresolved control attempt"):
        store.append_v2_control_result(
            handle,
            attempt_id="control-1",
            status="accepted",
        )

    store.append_v2_uart_tx_attempt(
        handle,
        attempt_id="tx-1",
        data=b"x",
        operation_id=None,
        transformation={"source": "bytes", "line_ending": "none"},
    )
    store.append_v2_uart_tx_result(
        handle,
        attempt_id="tx-1",
        status="accepted",
        accepted_bytes=1,
    )
    store.append_v2_control_attempt(
        handle,
        attempt_id="control-1",
        role="reset",
        provider="CTRL0",
        parameters={"pulse_ms": 10},
        operation_id=None,
    )
    store.append_v2_control_result(
        handle,
        attempt_id="control-1",
        status="accepted",
    )

    detail = store.get_session_detail(handle.session_id)
    assert isinstance(detail, V2SessionDetail)
    assert detail.unresolved_uart_tx_attempts == 0
    assert detail.unresolved_control_attempts == 0


@pytest.mark.parametrize(
    "operation_id",
    [" monitor-1", "monitor-1 ", "monitor\x00-1"],
)
def test_v2_operation_identity_rejects_edge_whitespace_and_controls(
    tmp_path: Path,
    operation_id: str,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )

    with pytest.raises(ValueError, match="operation_id"):
        store.start_v2_operation(
            handle,
            operation_id=operation_id,
            operation_type="monitor",
            parameters={"duration_s": 1.0},
        )

    assert read_jsonl(handle.paths.operation_events) == []


def test_v2_operation_id_cannot_be_reused_or_referenced_when_inactive(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )
    store.complete_v2_operation(handle, operation_id="monitor-1", outcome="elapsed")

    with pytest.raises(ValueError, match="already been used"):
        store.start_v2_operation(
            handle,
            operation_id="monitor-1",
            operation_type="monitor",
            parameters={"duration_s": 1.0},
        )
    with pytest.raises(ValueError, match="active operation"):
        store.append_v2_uart_tx_attempt(
            handle,
            attempt_id="attempt-1",
            data=b"x",
            operation_id="monitor-1",
            transformation={"source": "bytes", "line_ending": "none"},
        )
    with pytest.raises(ValueError, match="active operation"):
        store.append_v2_control_attempt(
            handle,
            attempt_id="control-1",
            role="reset",
            provider="CTRL0",
            parameters={"pulse_ms": 10},
            operation_id="monitor-1",
        )


@pytest.mark.parametrize("outcome", ["success", "failed", " elapsed", "unknown"])
def test_v2_operation_terminal_rejects_outcomes_outside_phase1_vocabulary(
    tmp_path: Path,
    outcome: str,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )

    with pytest.raises(ValueError, match="outcome"):
        store.complete_v2_operation(
            handle,
            operation_id="monitor-1",
            outcome=outcome,
        )

    assert store.load_metadata(handle.session_id)["operation_summary"][  # type: ignore[index]
        "active"
    ] == 1


def test_v2_error_outcome_and_error_payload_must_agree(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=lambda: "abc12345")
    handle = store.create_v2_session(
        profile=_profile(),
        backend_snapshot=enhanced_snapshot(),
    )
    store.start_v2_operation(
        handle,
        operation_id="monitor-1",
        operation_type="monitor",
        parameters={"duration_s": 1.0},
    )

    with pytest.raises(ValueError, match="error outcome"):
        store.complete_v2_operation(
            handle,
            operation_id="monitor-1",
            outcome="error",
        )
    with pytest.raises(ValueError, match="only valid"):
        store.complete_v2_operation(
            handle,
            operation_id="monitor-1",
            outcome="elapsed",
            error={"code": "internal_error", "detail": "failed"},
        )

    admission = store.complete_v2_operation(
        handle,
        operation_id="monitor-1",
        outcome="error",
        error={"code": "internal_error", "detail": "failed"},
    )
    record = read_jsonl(admission.handle.paths.operation_events)[-1]
    assert record["error"] == {
        "code": "internal_error",
        "detail": "failed",
        "detail_truncated": False,
    }
    summary = store.load_metadata(handle.session_id)["operation_summary"]
    assert summary["failed"] == 1  # type: ignore[index]
    assert summary["completed"] == 0  # type: ignore[index]
