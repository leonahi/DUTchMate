import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot

from dutchmate_core.backends import BufferStatusEvent, UartReceiveEvent
from dutchmate_core.session_store.models import (
    LegacySessionDetail,
    LegacySessionListItem,
    NativeSessionDetail,
    NativeSessionListItem,
    SessionQueryError,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def test_list_sessions_returns_newest_first(tmp_path: Path) -> None:
    older = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "older",
    ).create_session(command="capture --seconds 5")
    newer = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 1, tzinfo=timezone.utc),
        id_factory=lambda: "newer",
    ).create_session(command="boot-test --seconds 5", baseline=True)

    sessions = SessionStore(root=tmp_path).list_sessions()

    assert [summary.session_id for summary in sessions] == [
        newer.session_id,
        older.session_id,
    ]
    assert sessions[0].command == "boot-test --seconds 5"
    assert sessions[0].baseline is True


def test_list_sessions_applies_positive_limit(tmp_path: Path) -> None:
    for second in range(3):
        SessionStore(
            root=tmp_path,
            clock=lambda second=second: datetime(
                2026,
                7,
                14,
                12,
                0,
                second,
                tzinfo=timezone.utc,
            ),
            id_factory=lambda second=second: f"session-{second}",
        ).create_session(command="capture")

    sessions = SessionStore(root=tmp_path).list_sessions(limit=2)

    assert [summary.started_at for summary in sessions] == [
        "2026-07-14T12:00:02Z",
        "2026-07-14T12:00:01Z",
    ]


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_list_sessions_rejects_invalid_limit(tmp_path: Path, limit: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        SessionStore(root=tmp_path).list_sessions(limit=limit)  # type: ignore[arg-type]


def test_list_sessions_returns_empty_for_missing_root(tmp_path: Path) -> None:
    assert SessionStore(root=tmp_path / "missing").list_sessions() == ()


def test_list_sessions_ignores_unrelated_files_and_directories(tmp_path: Path) -> None:
    tmp_path.joinpath("README.txt").write_text("not a session", encoding="utf-8")
    tmp_path.joinpath("incomplete-session").mkdir()

    assert SessionStore(root=tmp_path).list_sessions() == ()


def test_list_sessions_surfaces_invalid_session_metadata(tmp_path: Path) -> None:
    session_root = tmp_path / "20260714T120000Z-invalid"
    session_root.mkdir()
    session_root.joinpath("metadata.json").write_text(
        json.dumps({"session_id": session_root.name}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="segments"):
        SessionStore(root=tmp_path).list_sessions()


def test_list_sessions_rejects_metadata_id_mismatch(tmp_path: Path) -> None:
    session_root = tmp_path / "20260714T120000Z-directory"
    session_root.mkdir()
    metadata = {
        "session_id": "20260714T120000Z-other",
        "started_at": "2026-07-14T12:00:00Z",
        "command": "capture",
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "baseline": False,
        "firmware": None,
        "device": None,
        "segments": [],
    }
    session_root.joinpath("metadata.json").write_text(
        json.dumps(metadata),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="match its directory"):
        SessionStore(root=tmp_path).list_sessions()


def test_latest_session_returns_newest_or_none(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path / "missing")
    assert store.latest_session() is None

    older = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "older",
    ).create_session(command="capture")
    newer = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 1, tzinfo=timezone.utc),
        id_factory=lambda: "newer",
    ).create_session(command="capture")

    latest = SessionStore(root=tmp_path).latest_session()

    assert latest is not None
    assert latest.session_id == newer.session_id
    assert latest.session_id != older.session_id


@pytest.mark.parametrize("session_id", ["", " ", ".", "..", "../outside", r"..\outside"])
def test_load_metadata_rejects_unsafe_session_id(tmp_path: Path, session_id: str) -> None:
    with pytest.raises(ValueError, match="path-safe"):
        SessionStore(root=tmp_path).load_metadata(session_id)


def test_session_page_is_stable_when_newer_session_is_created_between_pages(
    tmp_path: Path,
) -> None:
    created = [
        _create_native_session(tmp_path, second=second, suffix=f"session-{second}")
        for second in range(3)
    ]
    store = SessionStore(root=tmp_path)

    first_page = store.list_session_page(limit=2)
    _create_native_session(tmp_path, second=4, suffix="created-later")
    second_page = store.list_session_page(limit=2, cursor=first_page.next_cursor)

    assert [item.session_id for item in first_page.items] == [
        created[2],
        created[1],
    ]
    assert first_page.next_cursor is not None
    assert [item.session_id for item in second_page.items] == [created[0]]
    assert second_page.next_cursor is None


def test_session_page_discriminates_native_and_legacy_without_inferred_facts(
    tmp_path: Path,
) -> None:
    native_id = _create_native_session(tmp_path, second=1, suffix="native")
    legacy = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "legacy",
    ).create_session(command="capture", firmware="old-fw", device="old-device")

    page = SessionStore(root=tmp_path).list_session_page()

    assert isinstance(page.items[0], NativeSessionListItem)
    assert page.items[0].session_id == native_id
    assert page.items[0].compatibility == "native"
    legacy_item = page.items[1]
    assert isinstance(legacy_item, LegacySessionListItem)
    assert legacy_item.session_id == legacy.session_id
    assert legacy_item.compatibility == "legacy_read_only"
    assert legacy_item.migration_required is True
    assert legacy_item.migration_available is False


@pytest.mark.parametrize("cursor", ["", "not-base64", "e30", "5L2g"])
def test_session_page_rejects_invalid_cursor(tmp_path: Path, cursor: str) -> None:
    with pytest.raises(ValueError, match="cursor"):
        SessionStore(root=tmp_path).list_session_page(cursor=cursor)


def test_native_session_detail_returns_counts_and_manifest_without_event_arrays(
    tmp_path: Path,
) -> None:
    store = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "native-detail",
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    uart_event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=10,
        data=b"ERROR failed\nBOOT_OK\n",
    )
    store.append_uart_capture(
        handle,
        event=uart_event,
        result=UartCaptureProcessor().process_event(uart_event),
    )
    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=0,
            timestamp_us=20,
            size_bytes=32768,
            used_bytes=10,
            high_water_bytes=20,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )
    store.complete_session(handle)

    detail = store.get_session_detail(handle.session_id)

    assert isinstance(detail, NativeSessionDetail)
    assert detail.summary.state == "completed"
    assert detail.summary.first_error is not None
    assert detail.summary.first_error.pattern == "ERROR"
    assert detail.first_error is not None
    assert detail.first_error.match_excerpt.text == "ERROR failed\n"
    assert {count.type: count.count for count in detail.pattern_counts} == {
        "failure": 1,
        "success": 1,
    }
    assert {count.type: count.count for count in detail.hardware_event_counts} == {
        "buffer_status": 1,
    }
    assert detail.unresolved_uart_tx_attempts == 0
    manifest = {artifact.name: artifact for artifact in detail.artifacts}
    assert manifest["uart_events.jsonl"].records == 1
    assert manifest["hardware_events.jsonl"].records == 1
    assert manifest["detected_patterns.json"].records == 2
    assert not hasattr(detail, "uart_events")


def test_legacy_session_detail_returns_only_identity_and_artifact_sizes(tmp_path: Path) -> None:
    store = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 7, 14, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "legacy-detail",
    )
    handle = store.create_session(command="capture", firmware="0.0.1", device="old-helper")

    detail = store.get_session_detail(handle.session_id)

    assert isinstance(detail, LegacySessionDetail)
    assert detail.summary.compatibility == "legacy_read_only"
    assert detail.summary.firmware == "0.0.1"
    assert {artifact.name for artifact in detail.artifacts} == {
        "metadata.json",
        "uart_raw.log",
        "uart_events.jsonl",
        "hardware_events.jsonl",
        "detected_patterns.json",
    }
    assert all(artifact.records is None for artifact in detail.artifacts)


def test_get_session_distinguishes_not_found_unsupported_and_corrupt(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path)
    with pytest.raises(SessionQueryError) as not_found:
        store.get_session_detail("20260714T120000Z-missing")
    assert not_found.value.error == "not_found"

    unknown = tmp_path / "20260714T120000Z-unknown"
    unknown.mkdir()
    unknown.joinpath("metadata.json").write_text(
        json.dumps({"schema_version": 7}),
        encoding="utf-8",
    )
    with pytest.raises(SessionQueryError) as unsupported:
        store.get_session_detail(unknown.name)
    assert unsupported.value.error == "unsupported_session_schema"
    assert unsupported.value.detected_schema_version == 7

    corrupt = tmp_path / "20260714T120000Z-corrupt"
    corrupt.mkdir()
    corrupt.joinpath("metadata.json").write_text("{", encoding="utf-8")
    with pytest.raises(SessionQueryError) as persistence_fault:
        store.get_session_detail(corrupt.name)
    assert persistence_fault.value.error == "persistence_fault"


def _create_native_session(root: Path, *, second: int, suffix: str) -> str:
    store = SessionStore(
        root=root,
        clock=lambda: datetime(2026, 7, 14, 12, 0, second, tzinfo=timezone.utc),
        id_factory=lambda: suffix,
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    store.complete_session(handle)
    return handle.session_id
