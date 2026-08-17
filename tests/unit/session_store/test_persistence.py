from pathlib import Path

import pytest

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.session_store.models import SessionPersistenceError


def test_atomic_write_retries_short_writes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    path = tmp_path / "metadata.json"
    expected = b'{"state":"active"}\n'
    real_write = persistence._write_chunk
    write_count = 0

    def short_write(descriptor: int, data: memoryview) -> int:
        nonlocal write_count
        write_count += 1
        return real_write(descriptor, data[:3])

    monkeypatch.setattr(persistence, "_write_chunk", short_write)

    persistence.write_serialized(path, expected)

    assert path.read_bytes() == expected
    assert write_count > 1
    assert list(tmp_path.glob(".*.tmp")) == []


def test_atomic_write_preserves_previous_document_when_sync_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "metadata.json"
    path.write_bytes(b'{"state":"active"}\n')
    real_sync = persistence._sync_fd
    sync_count = 0

    def fail_first_sync(descriptor: int) -> None:
        nonlocal sync_count
        sync_count += 1
        if sync_count == 1:
            raise OSError("simulated fsync failure")
        real_sync(descriptor)

    monkeypatch.setattr(persistence, "_sync_fd", fail_first_sync)

    with pytest.raises(SessionPersistenceError, match="write failed for metadata.json"):
        persistence.write_serialized(path, b'{"state":"completed"}\n')

    assert path.read_bytes() == b'{"state":"active"}\n'
    assert list(tmp_path.glob(".*.tmp")) == []


def test_append_rolls_back_partial_record_after_write_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    path = tmp_path / "uart_events.jsonl"
    existing = b'{"event":"existing"}\n'
    path.write_bytes(existing)
    real_write = persistence._write_chunk
    write_count = 0

    def partial_then_fail(descriptor: int, data: memoryview) -> int:
        nonlocal write_count
        write_count += 1
        if write_count == 1:
            return real_write(descriptor, data[:4])
        raise OSError("simulated write failure")

    monkeypatch.setattr(persistence, "_write_chunk", partial_then_fail)

    with pytest.raises(SessionPersistenceError, match="append failed for uart_events.jsonl"):
        persistence.append_serialized(path, b'{"event":"new"}\n')

    assert path.read_bytes() == existing


def test_atomic_write_syncs_parent_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    synced_directories: list[Path] = []
    real_sync_directory = persistence._fsync_directory

    def record_sync(path: Path) -> None:
        synced_directories.append(path)
        real_sync_directory(path)

    monkeypatch.setattr(persistence, "_fsync_directory", record_sync)

    persistence.write_serialized(tmp_path / "metadata.json", b"{}\n")

    assert synced_directories == [tmp_path]


def test_missing_json_document_raises_typed_persistence_fault(tmp_path: Path) -> None:
    with pytest.raises(SessionPersistenceError) as raised:
        persistence.read_json_object(tmp_path / "metadata.json")

    assert raised.value.error == "persistence_fault"
    assert raised.value.operation == "read"
    assert raised.value.path == tmp_path / "metadata.json"
