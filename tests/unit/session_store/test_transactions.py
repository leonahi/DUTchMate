from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot, fixed_clock, fixed_id

import dutchmate_core.session_store.persistence as persistence
import dutchmate_core.session_store.transactions as transactions
from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.session_store.models import SessionHandle, SessionPersistenceError
from dutchmate_core.session_store.store import SessionRecoveryError, SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def _create_active_session(root: Path) -> tuple[SessionStore, SessionHandle]:
    store = SessionStore(root=root, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    return store, handle


def _transaction_artifacts(root: Path) -> list[Path]:
    return sorted(root.glob(".evidence-transaction*"))


def test_uart_unit_rolls_back_every_file_when_metadata_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store, handle = _create_active_session(tmp_path)
    before = {
        path.name: path.read_bytes()
        for path in (
            handle.paths.metadata,
            handle.paths.uart_raw,
            handle.paths.uart_events,
            handle.paths.hardware_events,
            handle.paths.detected_patterns,
        )
    }
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=100,
        data=b"ERROR\n",
    )
    result = UartCaptureProcessor().process_event(event)
    real_write = persistence.write_serialized

    def fail_metadata(path: Path, data: bytes) -> None:
        if path == handle.paths.metadata:
            raise SessionPersistenceError(
                operation="write",
                path=path,
                detail="simulated metadata failure",
            )
        real_write(path, data)

    monkeypatch.setattr(persistence, "write_serialized", fail_metadata)

    with pytest.raises(SessionPersistenceError, match="simulated metadata failure"):
        store.append_uart_capture(handle, event=event, result=result)

    assert {
        path.name: path.read_bytes()
        for path in (
            handle.paths.metadata,
            handle.paths.uart_raw,
            handle.paths.uart_events,
            handle.paths.hardware_events,
            handle.paths.detected_patterns,
        )
    } == before
    assert _transaction_artifacts(handle.paths.root) == []


def test_startup_rolls_back_prepared_interrupted_transaction(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    before_raw = handle.paths.uart_raw.read_bytes()
    before_events = handle.paths.uart_events.read_bytes()
    before_patterns = handle.paths.detected_patterns.read_bytes()
    transaction = transactions.begin_evidence_transaction(
        handle.paths,
        append_paths=[handle.paths.uart_raw, handle.paths.uart_events],
        replace_detected_patterns=True,
    )
    persistence.append_bytes(handle.paths.uart_raw, b"partial")
    persistence.append_serialized(handle.paths.uart_events, b'{"partial":true}\n')
    persistence.write_serialized(
        handle.paths.detected_patterns,
        b'[{"pattern":"ERROR"}]\n',
    )
    assert transaction is not None

    result = SessionStore(root=tmp_path, clock=fixed_clock).recover_stale_sessions()

    assert result.recovered_session_ids == (handle.session_id,)
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "evidence_transaction_rolled_back"
    ]
    assert handle.paths.uart_raw.read_bytes() == before_raw
    assert handle.paths.uart_events.read_bytes() == before_events
    assert handle.paths.detected_patterns.read_bytes() == before_patterns
    assert _transaction_artifacts(handle.paths.root) == []
    assert store.summarize_session(handle.session_id).state == "abandoned"


def test_startup_keeps_unit_when_expected_metadata_was_written(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    event_bytes = b'{"type":"buffer_status"}\n'
    transaction = transactions.begin_evidence_transaction(
        handle.paths,
        append_paths=[handle.paths.hardware_events],
    )
    persistence.append_serialized(handle.paths.hardware_events, event_bytes)
    metadata = persistence.read_json_object(handle.paths.metadata)
    metadata["overflow"] = True
    persistence.refresh_storage_accounting(metadata, handle.paths)
    serialized_metadata = persistence.serialize_json(metadata)
    transaction.prepare_metadata(serialized_metadata)
    persistence.write_serialized(handle.paths.metadata, serialized_metadata)

    result = SessionStore(root=tmp_path, clock=fixed_clock).recover_stale_sessions()

    assert result.recovered_session_ids == (handle.session_id,)
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "evidence_transaction_committed"
    ]
    assert handle.paths.hardware_events.read_bytes() == event_bytes
    assert _transaction_artifacts(handle.paths.root) == []
    summary = store.summarize_session(handle.session_id)
    assert summary.state == "abandoned"
    assert summary.overflow is True


def test_malformed_transaction_blocks_lifecycle_mutation(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    marker = handle.paths.root / ".evidence-transaction.json"
    persistence.write_json(marker, {"schema_version": 99})

    with pytest.raises(SessionRecoveryError, match="failed to recover evidence transaction"):
        SessionStore(root=tmp_path, clock=fixed_clock).recover_stale_sessions()

    assert store.summarize_session(handle.session_id).state == "active"
    assert marker.exists()
