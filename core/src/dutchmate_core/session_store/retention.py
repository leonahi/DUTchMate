"""Count-based retention policy for filesystem-backed debug sessions."""

from datetime import datetime, timezone
from pathlib import Path

import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.models import (
    NativeSessionDetail,
    NativeSessionListItem,
    SessionPersistenceError,
    SessionQueryError,
    SessionRetentionStatus,
)
from dutchmate_core.session_store.retrieval import get_session_detail as _get_session_detail


def apply_session_retention(
    root: Path,
    *,
    max_count: int,
    held_session_ids: frozenset[str] = frozenset(),
) -> SessionRetentionStatus:
    """Delete oldest eligible terminal sessions up to one configured limit."""

    if not root.exists():
        return SessionRetentionStatus(enabled=True, max_count=max_count)

    session_roots = tuple(
        sorted(
            (
                path
                for path in root.iterdir()
                if not path.is_symlink()
                and path.is_dir()
                and _persistence.session_paths(path).metadata.is_file()
            ),
            key=lambda path: path.name,
        )
    )
    baseline_session_id, pointer_fault = _baseline_session_id(root)
    if pointer_fault is not None:
        return _fault(
            max_count=max_count,
            session_count=len(session_roots),
            detail=pointer_fault,
        )

    protected: set[str] = set()
    eligible: list[tuple[datetime, str, Path]] = []
    native_summaries: dict[str, NativeSessionListItem] = {}
    try:
        for session_root in session_roots:
            session_id = _metadata._validate_session_id(session_root.name)
            metadata = _persistence.read_json_object(
                _persistence.session_paths(session_root).metadata
            )
            schema_version = metadata.get("schema_version", 0)
            if isinstance(schema_version, bool) or not isinstance(schema_version, int):
                raise ValueError(f"session {session_id} schema_version is malformed")
            if schema_version == 0:
                protected.add(session_id)
                continue
            if schema_version != 1:
                return _fault(
                    max_count=max_count,
                    session_count=len(session_roots),
                    detail=(
                        f"session {session_id} uses unsupported schema version {schema_version}"
                    ),
                    diagnostic="unsupported_session_schema",
                )

            detail = _get_session_detail(root, session_id)
            if not isinstance(detail, NativeSessionDetail):
                raise ValueError(f"session {session_id} native detail is unavailable")
            summary = detail.summary
            if summary.session_id != session_id:
                raise ValueError(
                    f"session {session_id} metadata ID does not match its directory"
                )
            native_summaries[session_id] = summary
            started_at = _parse_rfc3339_utc(summary.started_at, field="started_at")
            if (
                summary.state == "active"
                or session_id == baseline_session_id
                or session_id in held_session_ids
            ):
                protected.add(session_id)
            else:
                eligible.append((started_at, session_id, session_root))
    except (OSError, SessionPersistenceError, SessionQueryError, ValueError) as exc:
        return _fault(
            max_count=max_count,
            session_count=len(session_roots),
            detail=str(exc),
        )

    if baseline_session_id is not None:
        baseline_summary = native_summaries.get(baseline_session_id)
        if baseline_summary is None or not _is_valid_baseline_summary(baseline_summary):
            return _fault(
                max_count=max_count,
                session_count=len(session_roots),
                detail="baseline pointer does not name an eligible native session",
            )

    eligible.sort(key=lambda item: (item[0], item[1]))
    delete_count = max(0, len(session_roots) - max_count)
    deleted: list[str] = []
    for _started_at, session_id, session_root in eligible[:delete_count]:
        try:
            _persistence.remove_session_directory(session_root)
        except SessionPersistenceError as exc:
            return _fault(
                max_count=max_count,
                session_count=len(session_roots) - len(deleted),
                detail=str(exc),
                protected_session_ids=tuple(sorted(protected)),
                deleted_session_ids=tuple(deleted),
            )
        deleted.append(session_id)

    remaining_count = len(session_roots) - len(deleted)
    blocked = remaining_count > max_count
    return SessionRetentionStatus(
        enabled=True,
        max_count=max_count,
        session_count=remaining_count,
        protected_session_ids=tuple(sorted(protected)),
        deleted_session_ids=tuple(deleted),
        diagnostic="retention_blocked" if blocked else None,
        detail=(
            "protected sessions prevent enforcement of the configured count limit"
            if blocked
            else None
        ),
    )


def _baseline_session_id(root: Path) -> tuple[str | None, str | None]:
    pointer_path = root / "baseline.json"
    if not pointer_path.exists():
        return None, None
    if pointer_path.is_symlink() or not pointer_path.is_file():
        return None, "baseline pointer is not a regular file"
    try:
        pointer = _persistence.read_json_object(pointer_path)
        if pointer.get("schema_version") != 1:
            raise ValueError("baseline pointer schema_version must be 1")
        session_id = pointer.get("session_id")
        marked_at = pointer.get("marked_at")
        if not isinstance(session_id, str):
            raise ValueError("baseline pointer session_id must be a string")
        _metadata._validate_session_id(session_id)
        if not isinstance(marked_at, str):
            raise ValueError("baseline pointer marked_at must be a string")
        _parse_rfc3339_utc(marked_at, field="marked_at")
    except (OSError, SessionPersistenceError, ValueError) as exc:
        return None, str(exc)
    return session_id, None


def _parse_rfc3339_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must be an RFC 3339 UTC timestamp")
    return parsed.astimezone(timezone.utc)


def _is_valid_baseline_summary(summary: NativeSessionListItem) -> bool:
    return (
        summary.schema_version == 1
        and summary.state == "completed"
        and summary.workflow in {"capture", "boot_test"}
        and not summary.truncated
        and not summary.interrupted
        and summary.integrity.loss_status != "loss_reported"
    )


def _fault(
    *,
    max_count: int,
    session_count: int,
    detail: str,
    diagnostic: str = "persistence_fault",
    protected_session_ids: tuple[str, ...] = (),
    deleted_session_ids: tuple[str, ...] = (),
) -> SessionRetentionStatus:
    return SessionRetentionStatus(
        enabled=True,
        max_count=max_count,
        session_count=session_count,
        protected_session_ids=protected_session_ids,
        deleted_session_ids=deleted_session_ids,
        diagnostic=diagnostic,
        detail=detail,
    )
