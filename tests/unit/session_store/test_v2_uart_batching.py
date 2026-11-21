from __future__ import annotations

import base64
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot, fixed_clock, read_jsonl

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def _store(tmp_path: Path):  # type: ignore[no-untyped-def]
    store = SessionStore(root=tmp_path, clock=fixed_clock)
    profile = resolve_dut_profile(
        DutProfileConfig(), mode="enhanced", serial_port="/dev/ttyACM0"
    )
    return store, store.create_v2_session(profile=profile, backend_snapshot=enhanced_snapshot())


def _results(events):  # type: ignore[no-untyped-def]
    processor = UartCaptureProcessor()
    return [processor.process_event(event) for event in events]


def test_uart_group_preserves_each_timestamp_and_exact_raw_offset(tmp_path: Path) -> None:
    # Catches event coalescing, wrong offsets or non-atomic sequence publication.
    store, handle = _store(tmp_path)
    events = [UartReceiveEvent(0, 10, 0, b"REA"), UartReceiveEvent(0, 11, 0, b"DY\n")]
    admission = store.try_append_v2_uart_receive_batch(
        handle, events=events, capture_results=_results(events)
    )

    assert admission is not None
    assert (admission.evidence_seq, admission.next_evidence_seq) == (0, 2)
    records = read_jsonl(handle.paths.uart_events)
    assert [(r["evidence_seq"], r["timestamp_us"]) for r in records] == [(0, 10), (1, 11)]
    assert [(r["raw_offset_start"], r["raw_offset_end"]) for r in records] == [(0, 3), (3, 6)]
    assert [base64.b64decode(r["data_b64"]) for r in records] == [b"REA", b"DY\n"]
    assert handle.paths.uart_raw.read_bytes() == b"READY\n"
    metadata = store.load_metadata(handle.session_id)
    assert metadata["next_evidence_seq"] == 2
    assert metadata["segments"][0]["last_timestamp_us"] == 11


def test_group_that_cannot_fit_does_not_write_a_prefix(tmp_path: Path) -> None:
    # Group fallback must leave original per-event rollover decisions untouched.
    store, handle = _store(tmp_path)
    events = [UartReceiveEvent(0, 10, 0, b"a"), UartReceiveEvent(0, 11, 0, b"b")]
    metadata = store.load_metadata(handle.session_id)
    metadata["storage"]["evidence_bytes_written"] = metadata["storage"]["evidence_budget_bytes"]
    persistence.write_json(handle.paths.metadata, metadata)
    before = {p.name: p.read_bytes() for p in handle.paths.root.iterdir() if p.is_file()}

    assert store.try_append_v2_uart_receive_batch(
        handle, events=events, capture_results=_results(events)
    ) is None

    assert before == {p.name: p.read_bytes() for p in handle.paths.root.iterdir() if p.is_file()}


def test_pattern_projection_uses_existing_single_unit_path(tmp_path: Path) -> None:
    store, handle = _store(tmp_path)
    events = [UartReceiveEvent(0, 10, 0, b"READY\n"), UartReceiveEvent(0, 11, 0, b"HardFault\n")]

    assert store.try_append_v2_uart_receive_batch(
        handle, events=events, capture_results=_results(events)
    ) is None
    assert handle.paths.uart_raw.read_bytes() == b""
    assert store.load_metadata(handle.session_id)["next_evidence_seq"] == 0


@pytest.mark.parametrize("failure_file", ["uart_events.jsonl", "metadata.json"])
def test_failed_group_rolls_back_all_raw_and_primary_records(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure_file: str
) -> None:
    store, handle = _store(tmp_path)
    events = [UartReceiveEvent(0, 10, 0, b"one\n"), UartReceiveEvent(0, 11, 0, b"two\n")]
    operation = "write_serialized" if failure_file == "metadata.json" else "append_serialized"
    original = getattr(persistence, operation)
    failed = False

    def fail_once(path: Path, data: bytes) -> None:
        nonlocal failed
        if path.name == failure_file and not failed:
            failed = True
            raise SessionPersistenceError(operation="injected", path=path, detail="disk failure")
        original(path, data)

    monkeypatch.setattr(
        persistence, operation, fail_once,
    )
    with pytest.raises(SessionPersistenceError, match="disk failure"):
        store.try_append_v2_uart_receive_batch(
            handle, events=events, capture_results=_results(events)
        )

    assert handle.paths.uart_raw.read_bytes() == b""
    assert handle.paths.uart_events.read_bytes() == b""
    metadata = store.load_metadata(handle.session_id)
    assert metadata["next_evidence_seq"] == 0
    assert metadata["state"] == "failed"
    assert metadata["evidence_quality"]["local_recording"] == "persistence_fault"


def test_group_rejects_mismatched_processor_results_before_writing(tmp_path: Path) -> None:
    store, handle = _store(tmp_path)
    events = [UartReceiveEvent(0, 10, 0, b"a"), UartReceiveEvent(0, 11, 0, b"b")]
    with pytest.raises(ValueError):
        store.try_append_v2_uart_receive_batch(
            handle, events=events, capture_results=_results(events[:1])
        )
    assert handle.paths.uart_raw.read_bytes() == b""
