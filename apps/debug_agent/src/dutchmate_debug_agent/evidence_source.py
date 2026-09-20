"""Validated, stable native-session evidence reads for the Debug Agent."""

from __future__ import annotations

import io
import json
from collections.abc import Iterator
from pathlib import Path
from typing import cast

from dutchmate_core.session_store.models import NativeSessionDetail, SessionQueryError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_debug_agent.session_facts import _require_native_detail

_SNAPSHOT_ATTEMPTS = 3


class _SnapshotChanged(Exception):
    pass


def _read_stable_artifacts(
    store: SessionStore, session_id: str
) -> tuple[NativeSessionDetail, dict[str, bytes]]:
    names = ("uart_events.jsonl", "hardware_events.jsonl", "detected_patterns.json")
    for _attempt in range(_SNAPSHOT_ATTEMPTS):
        detail = _require_native_detail(store, session_id)
        session_root = store.root / detail.summary.session_id
        if session_root.is_symlink() or not session_root.is_dir():
            raise _evidence_fault(session_id, "Session directory is missing or symbolic")
        sizes = {artifact.name: artifact.bytes for artifact in detail.artifacts}
        try:
            artifacts = {name: _read_artifact(session_root / name, sizes[name]) for name in names}
        except _SnapshotChanged:
            continue
        except (OSError, ValueError) as exc:
            raise _evidence_fault(session_id, str(exc)) from exc
        if _require_native_detail(store, session_id) == detail:
            return detail, artifacts
    raise _evidence_fault(session_id, "Session changed during evidence snapshot")


def _read_artifact(path: Path, expected_size: int) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"Required artifact {path.name} is missing or symbolic")
    if path.stat().st_size != expected_size:
        raise _SnapshotChanged
    data = path.read_bytes()
    if len(data) != expected_size or path.stat().st_size != expected_size:
        raise _SnapshotChanged
    return data


def _evidence_fault(session_id: str, detail: str) -> SessionQueryError:
    return SessionQueryError(
        error="persistence_fault",
        operation="get_session",
        session_id=session_id,
        detail=f"Unable to assemble session evidence: {detail}",
    )


def _jsonl_objects(data: bytes) -> Iterator[dict[str, object]]:
    for line in io.BytesIO(data):
        if line == b"\n" or not line.endswith(b"\n"):
            raise ValueError("JSONL artifact contains an empty or incomplete record")
        value = json.loads(line.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("JSONL artifact must contain objects")
        yield cast(dict[str, object], value)


def _integer(value: object, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value
