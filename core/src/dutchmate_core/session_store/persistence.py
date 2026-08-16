"""Byte-level filesystem persistence for debug sessions."""

import json
import os
from pathlib import Path
from typing import cast
from uuid import uuid4

from dutchmate_core.session_store.models import SessionHandle, SessionPaths


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


def write_json_atomic(path: Path, value: object) -> None:
    temporary = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        write_json(temporary, value)
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


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
    return sum(
        path.stat().st_size
        for path in (
            paths.uart_raw,
            paths.uart_events,
            paths.hardware_events,
            paths.detected_patterns,
        )
    )


def read_json_object(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return cast(dict[str, object], loaded)


def read_json_list(path: Path) -> list[object]:
    with path.open("r", encoding="utf-8") as file:
        loaded = json.load(file)
    if not isinstance(loaded, list):
        raise ValueError(f"{path.name} must contain a JSON array")
    return cast(list[object], loaded)


def require_session_appendable(handle: SessionHandle) -> None:
    metadata = read_json_object(handle.paths.metadata)
    schema_version = metadata.get("schema_version", 0)
    if schema_version == 1 and metadata.get("state") != "active":
        raise ValueError("native session evidence can only append while active")


def append_bytes(path: Path, data: bytes) -> None:
    with path.open("ab") as file:
        file.write(data)


def serialize_json(value: object) -> bytes:
    return (json.dumps(value, indent=2) + "\n").encode("utf-8")


def serialize_jsonl(value: dict[str, object]) -> bytes:
    return (json.dumps(value, separators=(",", ":")) + "\n").encode("utf-8")


def write_serialized(path: Path, data: bytes) -> None:
    with path.open("wb") as file:
        file.write(data)


def append_serialized(path: Path, data: bytes) -> None:
    with path.open("ab") as file:
        file.write(data)
