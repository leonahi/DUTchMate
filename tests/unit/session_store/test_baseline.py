import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot

import dutchmate_core.session_store.baseline as baseline_policy
from dutchmate_core.backends import BackendInfo, UartIntegrity
from dutchmate_core.session_store.models import (
    BaselineError,
    NativeSessionDetail,
    NativeSessionListItem,
    SessionPersistenceError,
)
from dutchmate_core.session_store.store import SessionHandle, SessionStore


def _store(
    root: Path,
    *,
    moments: list[datetime],
    suffixes: list[str],
    max_count: int | None = None,
) -> SessionStore:
    moment_iter = iter(moments)
    suffix_iter = iter(suffixes)
    return SessionStore(
        root=root,
        max_count=max_count,
        clock=lambda: next(moment_iter),
        id_factory=lambda: next(suffix_iter),
    )


def _create_capture(Session_store: SessionStore) -> SessionHandle:
    return Session_store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )


def test_mark_is_atomic_idempotent_and_authoritative_for_queries(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 15, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(3)],
        suffixes=["aaaa1111"],
    )
    handle = _create_capture(store)
    store.complete_session(handle)

    marked = store.mark_baseline(handle.session_id)
    repeated = store.mark_baseline(handle.session_id)

    assert marked.session_id == handle.session_id
    assert marked.previous_session_id is None
    assert marked.changed is True
    assert marked.marked_at == "2026-08-21T15:00:02Z"
    assert marked.integrity == enhanced_snapshot().integrity
    assert repeated.previous_session_id == handle.session_id
    assert repeated.changed is False
    assert repeated.marked_at == marked.marked_at
    assert json.loads((tmp_path / "baseline.json").read_text(encoding="utf-8")) == {
        "schema_version": 1,
        "session_id": handle.session_id,
        "marked_at": marked.marked_at,
    }
    list_item = store.list_session_page().items[0]
    assert isinstance(list_item, NativeSessionListItem)
    assert list_item.baseline is True
    detail = store.get_session_detail(handle.session_id)
    assert isinstance(detail, NativeSessionDetail)
    assert detail.summary.baseline is True
    assert store.summarize_session(handle.session_id).baseline is True
    assert store.load_metadata(handle.session_id).get("baseline") is None


def test_replacement_and_named_clear_are_idempotent(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 16, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(6)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = _create_capture(store)
    store.complete_session(first)
    second = _create_capture(store)
    store.complete_session(second)
    first_mark = store.mark_baseline(first.session_id)

    replacement = store.mark_baseline(second.session_id)
    wrong_clear = store.clear_baseline(first.session_id)
    cleared = store.clear_baseline(second.session_id)
    repeated_clear = store.clear_baseline(second.session_id)

    assert replacement.previous_session_id == first.session_id
    assert replacement.changed is True
    assert replacement.marked_at != first_mark.marked_at
    assert wrong_clear.changed is False
    assert wrong_clear.previous_session_id == second.session_id
    assert cleared.changed is True
    assert cleared.previous_session_id == second.session_id
    assert repeated_clear.changed is False
    assert not (tmp_path / "baseline.json").exists()


def test_basic_not_observable_session_is_baseline_eligible(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 17, 0, tzinfo=timezone.utc)
    snapshot = enhanced_snapshot()
    basic_snapshot = replace(
        snapshot,
        info=BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        integrity=UartIntegrity(
            loss_status="not_observable",
            observation_scope=None,
            dropped_bytes=None,
        ),
    )
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(3)],
        suffixes=["aaaa1111"],
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=basic_snapshot,
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    store.complete_session(handle)

    result = store.mark_baseline(handle.session_id)

    assert result.changed is True
    assert result.integrity is not None
    assert result.integrity.loss_status == "not_observable"


def test_ineligibility_reasons_use_deterministic_order(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 18, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(2)],
        suffixes=["aaaa1111"],
    )
    handle = _create_capture(store)
    store.complete_session(handle)
    detail = store.get_session_detail(handle.session_id)
    assert isinstance(detail, NativeSessionDetail)
    loss = UartIntegrity(
        loss_status="loss_reported",
        observation_scope="debug_helper_rx_buffer",
        dropped_bytes=1,
    )

    states = (
        (replace(detail.summary, state="failed", workflow="wait_pattern", truncated=True,
                 interrupted=True, integrity=loss), "state_not_completed"),
        (replace(detail.summary, workflow="wait_pattern", truncated=True,
                 interrupted=True, integrity=loss), "workflow_not_baseline_eligible"),
        (replace(detail.summary, truncated=True, interrupted=True, integrity=loss), "truncated"),
        (replace(detail.summary, interrupted=True, integrity=loss), "interrupted"),
        (replace(detail.summary, integrity=loss), "loss_reported"),
    )
    for summary, expected in states:
        candidate = replace(detail, summary=summary)
        assert baseline_policy._ineligibility_reason(candidate) == expected


def test_failed_replacement_preserves_existing_pointer(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 19, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(4)],
        suffixes=["aaaa1111", "legacy1"],
    )
    baseline = _create_capture(store)
    store.complete_session(baseline)
    legacy = store.create_session(command="capture")
    store.mark_baseline(baseline.session_id)
    before = (tmp_path / "baseline.json").read_bytes()

    with pytest.raises(BaselineError) as error:
        store.mark_baseline(legacy.session_id)

    assert error.value.error == "unsupported_session_schema"
    assert error.value.detected_schema_version == 0
    assert (tmp_path / "baseline.json").read_bytes() == before


def test_atomic_write_failure_preserves_existing_pointer(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    start = datetime(2026, 8, 21, 19, 30, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(6)],
        suffixes=["aaaa1111", "bbbb2222"],
    )
    first = _create_capture(store)
    store.complete_session(first)
    second = _create_capture(store)
    store.complete_session(second)
    store.mark_baseline(first.session_id)
    pointer = tmp_path / "baseline.json"
    before = pointer.read_bytes()

    def fail_write(path: Path, value: object) -> None:
        raise SessionPersistenceError(
            operation="write",
            path=path,
            detail="injected failure",
        )

    monkeypatch.setattr(baseline_policy._persistence, "write_json", fail_write)
    with pytest.raises(BaselineError) as error:
        store.mark_baseline(second.session_id)

    assert error.value.error == "persistence_fault"
    assert pointer.read_bytes() == before


def test_dangling_or_corrupt_pointer_fails_reads_and_mutations(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 20, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(3)],
        suffixes=["aaaa1111"],
    )
    candidate = _create_capture(store)
    store.complete_session(candidate)
    pointer = tmp_path / "baseline.json"
    pointer.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "session_id": "20260821T200500Z-missing1",
                "marked_at": "2026-08-21T20:05:00Z",
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(BaselineError, match="pointer target") as read_error:
        store.list_session_page()
    with pytest.raises(BaselineError) as mutation_error:
        store.mark_baseline(candidate.session_id)
    assert read_error.value.error == "persistence_fault"
    assert mutation_error.value.error == "persistence_fault"

    pointer.write_text("not JSON", encoding="utf-8")
    with pytest.raises(BaselineError) as corrupt_error:
        store.clear_baseline(candidate.session_id)
    assert corrupt_error.value.error == "persistence_fault"


def test_replacement_releases_old_baseline_for_retention(tmp_path: Path) -> None:
    start = datetime(2026, 8, 21, 21, 0, tzinfo=timezone.utc)
    store = _store(
        tmp_path,
        moments=[start + timedelta(seconds=index) for index in range(6)],
        suffixes=["aaaa1111", "bbbb2222"],
        max_count=1,
    )
    old = _create_capture(store)
    store.complete_session(old)
    store.mark_baseline(old.session_id)
    replacement = _create_capture(store)
    store.complete_session(replacement)

    result = store.mark_baseline(replacement.session_id)

    assert result.previous_session_id == old.session_id
    assert not old.paths.root.exists()
    assert replacement.paths.root.exists()
