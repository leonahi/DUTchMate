import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.session_store.store import SessionStore


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
