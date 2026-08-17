"""Byte-level filesystem persistence for debug sessions."""

import json
import os
from contextlib import suppress
from pathlib import Path
from typing import cast
from uuid import uuid4

from dutchmate_core.session_store.models import (
    SessionHandle,
    SessionPaths,
    SessionPersistenceError,
)


def session_paths(root: Path) -> SessionPaths:
    return SessionPaths(
        root=root,
        metadata=root / "metadata.json",
        uart_raw=root / "uart_raw.log",
        uart_events=root / "uart_events.jsonl",
        hardware_events=root / "hardware_events.jsonl",
        detected_patterns=root / "detected_patterns.json",
        terminal_reserve=root / ".terminal-reserve",
    )


def write_json(path: Path, value: object) -> None:
    write_serialized(path, serialize_json(value))


def create_directory(path: Path) -> None:
    """Create a session directory and durably publish its parent entry."""

    try:
        path.mkdir(parents=True, exist_ok=False)
        _fsync_directory(path.parent)
    except FileExistsError:
        raise
    except OSError as exc:
        raise _error("create directory", path, exc) from exc


def remove_file(path: Path, *, missing_ok: bool = False) -> None:
    """Remove one session file without hiding filesystem failures."""

    try:
        path.unlink(missing_ok=missing_ok)
    except OSError as exc:
        raise _error("remove", path, exc) from exc


def refresh_storage_accounting(
    metadata: dict[str, object],
    paths: SessionPaths,
) -> None:
    raw_storage = metadata.get("storage")
    if raw_storage is None:
        return
    if not isinstance(raw_storage, dict):
        raise ValueError("session metadata 'storage' must be a JSON object")
    storage = cast(dict[str, object], raw_storage)
    storage["evidence_bytes_written"] = evidence_file_bytes(paths)


def evidence_file_bytes(paths: SessionPaths) -> int:
    try:
        return sum(
            path.stat().st_size
            for path in (
                paths.uart_raw,
                paths.uart_events,
                paths.hardware_events,
                paths.detected_patterns,
            )
        )
    except OSError as exc:
        raise _error("account evidence", paths.root, exc) from exc


def read_json_object(path: Path) -> dict[str, object]:
    try:
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except OSError as exc:
        raise _error("read", path, exc) from exc
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return cast(dict[str, object], loaded)


def read_json_list(path: Path) -> list[object]:
    try:
        with path.open("r", encoding="utf-8") as file:
            loaded = json.load(file)
    except OSError as exc:
        raise _error("read", path, exc) from exc
    if not isinstance(loaded, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return cast(list[object], loaded)


def require_session_appendable(handle: SessionHandle) -> None:
    metadata = read_json_object(handle.paths.metadata)
    schema_version = metadata.get("schema_version", 0)
    if schema_version == 1 and metadata.get("state") != "active":
        raise ValueError("native session evidence can only append while active")


def append_bytes(path: Path, data: bytes) -> None:
    append_serialized(path, data)


def serialize_json(value: object) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def serialize_jsonl(value: dict[str, object]) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")


def write_serialized(path: Path, data: bytes) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    descriptor: int | None = None
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o666)
        _write_all(descriptor, data)
        _sync_fd(descriptor)
        synced_descriptor = descriptor
        descriptor = None
        os.close(synced_descriptor)
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except OSError as exc:
        raise _error("write", path, exc) from exc
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)
        with suppress(OSError):
            temporary.unlink(missing_ok=True)


def append_serialized(path: Path, data: bytes) -> None:
    descriptor: int | None = None
    original_size: int | None = None
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o666)
        original_size = os.fstat(descriptor).st_size
        _write_all(descriptor, data)
        _sync_fd(descriptor)
        synced_descriptor = descriptor
        descriptor = None
        os.close(synced_descriptor)
    except OSError as exc:
        if descriptor is not None and original_size is not None:
            try:
                os.ftruncate(descriptor, original_size)
                _sync_fd(descriptor)
            except OSError:
                pass
        raise _error("append", path, exc) from exc
    finally:
        if descriptor is not None:
            with suppress(OSError):
                os.close(descriptor)


def _write_all(descriptor: int, data: bytes) -> None:
    view = memoryview(data)
    written = 0
    while written < len(view):
        count = _write_chunk(descriptor, view[written:])
        if count <= 0:
            raise OSError("write returned zero bytes")
        written += count


def _write_chunk(descriptor: int, data: memoryview) -> int:
    return os.write(descriptor, data)


def _sync_fd(descriptor: int) -> None:
    os.fsync(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        _sync_fd(descriptor)
    finally:
        os.close(descriptor)


def _error(operation: str, path: Path, exc: OSError) -> SessionPersistenceError:
    detail = exc.strerror or str(exc) or type(exc).__name__
    return SessionPersistenceError(operation=operation, path=path, detail=detail)
