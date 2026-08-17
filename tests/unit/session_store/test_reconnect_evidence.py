import json
from dataclasses import replace
from pathlib import Path

import pytest
from session_store_support import (
    enhanced_snapshot,
    evidence_bytes,
    fixed_clock,
    fixed_id,
    read_jsonl,
)

from dutchmate_core.backends import BackendSnapshot, SegmentContext
from dutchmate_core.session_store.metadata import METADATA_MAX_BYTES
from dutchmate_core.session_store.store import (
    DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
    EvidenceQuotaExceeded,
    SessionHandle,
    SessionStore,
)


def _snapshot_for_segment(
    segment_id: int,
    *,
    source_origin_us: int | None = None,
) -> BackendSnapshot:
    snapshot = enhanced_snapshot()
    assert snapshot.segment is not None
    timestamp = replace(
        snapshot.segment.timestamp,
        source_origin_us=(
            source_origin_us if source_origin_us is not None else 1_000 + segment_id
        ),
    )
    return replace(
        snapshot,
        segment=SegmentContext(segment_id=segment_id, timestamp=timestamp),
    )


def _create_active_session(
    root: Path,
    *,
    evidence_budget_bytes: int = DEFAULT_SESSION_EVIDENCE_BUDGET_BYTES,
) -> tuple[SessionStore, SessionHandle]:
    store = SessionStore(
        root=root,
        clock=fixed_clock,
        id_factory=fixed_id,
        evidence_budget_bytes=evidence_budget_bytes,
    )
    handle = store.create_session(
        command="capture --seconds 5",
        backend_snapshot=_snapshot_for_segment(0),
        workflow="capture",
        duration_s=5.0,
        reconnect_timeout_s=5.0,
    )
    return store, handle


def test_disconnect_and_resume_append_segment_lifecycle_evidence(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)

    assert store.record_backend_disconnect(handle, segment_id=0) == 1
    assert (
        store.resume_session(
            handle,
            backend_snapshot=_snapshot_for_segment(1, source_origin_us=9_000),
        )
        == 1
    )

    metadata = store.load_metadata(handle.session_id)
    assert metadata["interrupted"] is True
    assert metadata["resumed"] is True
    segments = metadata["segments"]
    assert isinstance(segments, list)
    assert segments[0]["ended_at"] == "2026-07-14T12:30:45Z"  # type: ignore[index]
    assert segments[0]["end_reason"] == "usb_disconnect"  # type: ignore[index]
    assert segments[1]["segment_id"] == 1  # type: ignore[index]
    assert segments[1]["started_at"] == "2026-07-14T12:30:45Z"  # type: ignore[index]
    assert segments[1]["timestamp"]["source_origin_us"] == 9_000  # type: ignore[index]
    assert read_jsonl(handle.paths.hardware_events) == [
        {
            "type": "usb_disconnect",
            "host_timestamp": "2026-07-14T12:30:45Z",
            "segment_id": 0,
        },
        {
            "type": "usb_reconnect",
            "host_timestamp": "2026-07-14T12:30:45Z",
            "segment_id": 1,
        },
        {
            "type": "timestamp_discontinuity",
            "host_timestamp": "2026-07-14T12:30:45Z",
            "from_segment_id": 0,
            "to_segment_id": 1,
        },
    ]
    summary = store.summarize_session(handle.session_id)
    assert summary.interrupted is True
    assert summary.resumed is True
    assert summary.segment_count == 2
    assert summary.segment_contexts[-1] == _snapshot_for_segment(
        1,
        source_origin_us=9_000,
    ).segment


def test_terminalization_preserves_closed_disconnect_segment_reason(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    store.record_backend_disconnect(handle, segment_id=0)

    store.fail_session(
        handle,
        end_reason="reconnect_timeout",
        error_code="service_unavailable",
        detail="Backend did not reconnect before the reconnect deadline",
    )

    metadata = store.load_metadata(handle.session_id)
    assert metadata["end_reason"] == "reconnect_timeout"
    assert metadata["segments"][0]["end_reason"] == "usb_disconnect"  # type: ignore[index]


def test_disconnect_quota_rejection_keeps_summary_without_detailed_event(
    tmp_path: Path,
) -> None:
    reference_store, reference_handle = _create_active_session(tmp_path / "reference")
    reference_store.record_backend_disconnect(reference_handle, segment_id=0)
    rejected_budget = evidence_bytes(reference_handle) - 1
    store, handle = _create_active_session(
        tmp_path / "rejected",
        evidence_budget_bytes=rejected_budget,
    )

    with pytest.raises(EvidenceQuotaExceeded):
        store.record_backend_disconnect(handle, segment_id=0)

    summary = store.summarize_session(handle.session_id)
    metadata = store.load_metadata(handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.interrupted is True
    assert summary.resumed is False
    assert metadata["segments"][0]["end_reason"] == "usb_disconnect"  # type: ignore[index]
    assert read_jsonl(handle.paths.hardware_events) == []


def test_reconnect_quota_rejection_does_not_publish_new_segment(tmp_path: Path) -> None:
    reference_store, reference_handle = _create_active_session(tmp_path / "reference")
    reference_store.record_backend_disconnect(reference_handle, segment_id=0)
    reference_store.resume_session(
        reference_handle,
        backend_snapshot=_snapshot_for_segment(1),
    )
    rejected_budget = evidence_bytes(reference_handle) - 1
    store, handle = _create_active_session(
        tmp_path / "rejected",
        evidence_budget_bytes=rejected_budget,
    )
    store.record_backend_disconnect(handle, segment_id=0)

    with pytest.raises(EvidenceQuotaExceeded):
        store.resume_session(handle, backend_snapshot=_snapshot_for_segment(1))

    summary = store.summarize_session(handle.session_id)
    assert summary.state == "completed"
    assert summary.end_reason == "size_limit"
    assert summary.interrupted is True
    assert summary.resumed is False
    assert summary.segment_count == 1
    assert [event["type"] for event in read_jsonl(handle.paths.hardware_events)] == [
        "usb_disconnect"
    ]


@pytest.mark.parametrize(
    "invalid_snapshot",
    ["segment", "port", "identity", "provenance"],
)
def test_resume_rejects_incompatible_backend_without_writing(
    tmp_path: Path,
    invalid_snapshot: str,
) -> None:
    store, handle = _create_active_session(tmp_path)
    store.record_backend_disconnect(handle, segment_id=0)
    snapshot = _snapshot_for_segment(1)
    if invalid_snapshot == "segment":
        snapshot = _snapshot_for_segment(2)
    elif invalid_snapshot == "port":
        snapshot = replace(snapshot, info=replace(snapshot.info, port="/dev/ttyACM1"))
    elif invalid_snapshot == "identity":
        snapshot = replace(snapshot, info=replace(snapshot.info, firmware="0.2.0"))
    else:
        snapshot = replace(snapshot, segment=None)
    before_metadata = handle.paths.metadata.read_bytes()
    before_events = handle.paths.hardware_events.read_bytes()

    with pytest.raises(ValueError):
        store.resume_session(handle, backend_snapshot=snapshot)

    assert handle.paths.metadata.read_bytes() == before_metadata
    assert handle.paths.hardware_events.read_bytes() == before_events


def test_resume_rejects_noncontiguous_stored_segments(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    store.record_backend_disconnect(handle, segment_id=0)
    metadata = store.load_metadata(handle.session_id)
    metadata["segments"][0]["segment_id"] = 7  # type: ignore[index]
    handle.paths.metadata.write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )
    before_events = handle.paths.hardware_events.read_bytes()

    with pytest.raises(ValueError, match="contiguous from zero"):
        store.resume_session(handle, backend_snapshot=_snapshot_for_segment(1))

    assert handle.paths.hardware_events.read_bytes() == before_events


def test_session_never_appends_a_thirty_third_segment(tmp_path: Path) -> None:
    store, handle = _create_active_session(tmp_path)
    for segment_id in range(1, 32):
        assert store.record_backend_disconnect(handle, segment_id=segment_id - 1) == segment_id
        assert (
            store.resume_session(
                handle,
                backend_snapshot=_snapshot_for_segment(segment_id),
            )
            == segment_id
        )
    assert store.record_backend_disconnect(handle, segment_id=31) == 32
    before_events = handle.paths.hardware_events.read_bytes()

    with pytest.raises(ValueError, match="maximum 32 segments"):
        store.resume_session(handle, backend_snapshot=_snapshot_for_segment(32))

    metadata = store.load_metadata(handle.session_id)
    assert len(metadata["segments"]) == 32  # type: ignore[arg-type]
    assert len(handle.paths.metadata.read_bytes()) <= METADATA_MAX_BYTES
    assert handle.paths.hardware_events.read_bytes() == before_events


def test_thirty_two_maximum_length_segment_identities_fit_terminal_metadata(
    tmp_path: Path,
) -> None:
    initial = _snapshot_for_segment(0)
    maximum_info = replace(
        initial.info,
        port="p" * 4096,
        device="d" * 64,
        firmware="f" * 64,
    )
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="c" * 256,
        backend_snapshot=replace(initial, info=maximum_info),
        workflow="capture",
        duration_s=300.0,
        reconnect_timeout_s=60.0,
    )
    for segment_id in range(1, 32):
        store.record_backend_disconnect(handle, segment_id=segment_id - 1)
        snapshot = _snapshot_for_segment(segment_id)
        store.resume_session(
            handle,
            backend_snapshot=replace(snapshot, info=maximum_info),
        )

    store.fail_session(
        handle,
        end_reason="backend_input_error",
        error_code="persistence_fault",
        detail="x" * 1024,
    )

    metadata = store.load_metadata(handle.session_id)
    assert len(metadata["segments"]) == 32  # type: ignore[arg-type]
    assert len(handle.paths.metadata.read_bytes()) <= METADATA_MAX_BYTES
