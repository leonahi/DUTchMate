import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Event, Thread

import pytest
from session_store_support import enhanced_snapshot

import dutchmate_core.session_store.store as store_module
from dutchmate_core.session_store.store import SessionHandle, SessionStore


def _native_store(
    root: Path,
    *,
    max_count: int | None,
    moments: list[datetime],
    suffixes: list[str],
) -> SessionStore:
    moment_iter = iter(moments)
    suffix_iter = iter(suffixes)
    return SessionStore(
        root=root,
        max_count=max_count,
        clock=lambda: next(moment_iter),
        id_factory=lambda: next(suffix_iter),
    )


def _create_capture(store: SessionStore) -> SessionHandle:
    return store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )


def test_terminal_transition_removes_oldest_eligible_session(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)
    store = _native_store(
        tmp_path,
        max_count=2,
        moments=[start + timedelta(seconds=index) for index in range(6)],
        suffixes=["aaaa1111", "bbbb2222", "cccc3333"],
    )
    first = _create_capture(store)
    store.complete_session(first)
    second = _create_capture(store)
    store.complete_session(second)
    third = _create_capture(store)
    store.complete_session(third)

    assert not first.paths.root.exists()
    assert second.paths.root.exists()
    assert third.paths.root.exists()
    assert store.retention_status.deleted_session_ids == (first.session_id,)
    assert store.retention_status.session_count == 2
    assert store.retention_status.diagnostic is None


def test_startup_recovery_runs_retention_after_recovery(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 10, 30, tzinfo=timezone.utc)
    creating_store = _native_store(
        tmp_path,
        max_count=None,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = _create_capture(creating_store)
    creating_store.complete_session(first)
    second = _create_capture(creating_store)
    creating_store.complete_session(second)

    store = SessionStore(root=tmp_path, max_count=1)
    store.recover_stale_sessions()

    assert not first.paths.root.exists()
    assert second.paths.root.exists()
    assert store.retention_status.deleted_session_ids == (first.session_id,)


def test_legacy_sessions_count_toward_limit_but_remain_protected(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 10, 45, tzinfo=timezone.utc)
    store = _native_store(
        tmp_path,
        max_count=1,
        moments=[start, start + timedelta(seconds=1)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = store.create_session(command="capture")
    second = store.create_session(command="capture")

    status = store.run_retention()

    assert first.paths.root.exists()
    assert second.paths.root.exists()
    assert status.diagnostic == "retention_blocked"
    assert status.protected_session_ids == tuple(sorted((first.session_id, second.session_id)))


def test_retention_reports_blocked_when_active_sessions_exceed_limit(
    tmp_path: Path,
) -> None:
    start = datetime(2026, 8, 21, 11, 0, tzinfo=timezone.utc)
    store = _native_store(
        tmp_path,
        max_count=1,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "bbbb2222", "cccc3333"],
    )
    first_active = _create_capture(store)
    second_active = _create_capture(store)
    terminal = _create_capture(store)
    store.complete_session(terminal)

    assert first_active.paths.root.exists()
    assert second_active.paths.root.exists()
    assert terminal.paths.root.exists()
    assert store.retention_status.diagnostic == "retention_blocked"
    assert store.retention_status.protected_session_ids == tuple(
        sorted((first_active.session_id, second_active.session_id, terminal.session_id))
    )
    assert store.retention_status.session_count == 3


def test_retention_protects_valid_baseline_pointer(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc)
    creating_store = _native_store(
        tmp_path,
        max_count=None,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    baseline = _create_capture(creating_store)
    creating_store.complete_session(baseline)
    other = _create_capture(creating_store)
    creating_store.complete_session(other)
    (tmp_path / "baseline.json").write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session_id": baseline.session_id,
                "marked_at": "2026-08-21T12:05:00Z",
            }
        ),
        encoding="utf-8",
    )

    status = SessionStore(root=tmp_path, max_count=1).run_retention()

    assert baseline.paths.root.exists()
    assert not other.paths.root.exists()
    assert status.protected_session_ids == (baseline.session_id,)
    assert status.deleted_session_ids == (other.session_id,)


def test_corrupt_pointer_and_unknown_schema_suspend_retention(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 13, 0, tzinfo=timezone.utc)
    creating_store = _native_store(
        tmp_path,
        max_count=None,
        moments=[start, start + timedelta(seconds=1)],
        suffixes=["aaaa1111"],
    )
    native = _create_capture(creating_store)
    creating_store.complete_session(native)
    unknown = tmp_path / "20260821T130200Z-bbbb2222"
    unknown.mkdir()
    (unknown / "metadata.json").write_text(
        json.dumps({"schema_version": 7}),
        encoding="utf-8",
    )

    status = SessionStore(root=tmp_path, max_count=1).run_retention()

    assert status.diagnostic == "unsupported_session_schema"
    assert native.paths.root.exists()
    assert unknown.exists()

    unknown.rename(tmp_path / "unknown-evidence")
    (tmp_path / "baseline.json").write_text("not JSON", encoding="utf-8")
    status = SessionStore(root=tmp_path, max_count=1).run_retention()
    assert status.diagnostic == "persistence_fault"
    assert native.paths.root.exists()


def test_corrupt_session_evidence_suspends_retention(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 13, 30, tzinfo=timezone.utc)
    creating_store = _native_store(
        tmp_path,
        max_count=None,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = _create_capture(creating_store)
    creating_store.complete_session(first)
    second = _create_capture(creating_store)
    creating_store.complete_session(second)
    first.paths.detected_patterns.write_text("not JSON", encoding="utf-8")

    status = SessionStore(root=tmp_path, max_count=1).run_retention()

    assert status.diagnostic == "persistence_fault"
    assert first.paths.root.exists()
    assert second.paths.root.exists()


def test_reader_holds_store_lock_until_its_snapshot_is_complete(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    start = datetime(2026, 8, 21, 14, 0, tzinfo=timezone.utc)
    creating_store = _native_store(
        tmp_path,
        max_count=None,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = _create_capture(creating_store)
    creating_store.complete_session(first)
    second = _create_capture(creating_store)
    creating_store.complete_session(second)
    store = SessionStore(root=tmp_path, max_count=1)
    reader_started = Event()
    release_reader = Event()
    retention_finished = Event()
    original_get = store_module._get_session_detail

    def held_get(root: Path, session_id: str) -> object:
        reader_started.set()
        assert release_reader.wait(timeout=1)
        return original_get(root, session_id)

    monkeypatch.setattr(store_module, "_get_session_detail", held_get)
    reader = Thread(target=store.get_session_detail, args=(first.session_id,))
    retention = Thread(
        target=lambda: (store.run_retention(), retention_finished.set()),
    )
    reader.start()
    assert reader_started.wait(timeout=1)
    retention.start()
    assert not retention_finished.wait(timeout=0.05)
    assert first.paths.root.exists()

    release_reader.set()
    reader.join(timeout=1)
    retention.join(timeout=1)
    assert retention_finished.is_set()
    assert not first.paths.root.exists()
