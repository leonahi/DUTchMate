"""Count-based retention policy for filesystem-backed debug sessions."""

from datetime import datetime, timezone
from pathlib import Path

import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.baseline import read_baseline_pointer
from dutchmate_core.session_store.models import (
    BaselineError,
    NativeSessionDetail,
    SessionPersistenceError,
    SessionQueryError,
    SessionRetentionStatus,
    V2SessionDetail,
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
    try:
        pointer = read_baseline_pointer(root)
    except BaselineError as exc:
        return _fault(
            max_count=max_count,
            session_count=len(session_roots),
            detail=str(exc),
        )
    baseline_session_id = pointer.session_id if pointer is not None else None

    protected: set[str] = set()
    eligible: list[tuple[datetime, str, Path]] = []
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
            if schema_version not in {1, 2}:
                return _fault(
                    max_count=max_count,
                    session_count=len(session_roots),
                    detail=(
                        f"session {session_id} uses unsupported schema version {schema_version}"
                    ),
                    diagnostic="unsupported_session_schema",
                )

            if schema_version == 2:
                _protect_active_operation_ranges(metadata, protected)
                if metadata.get("state") == "active":
                    _protect_pending_attempt_origins(metadata, protected)

            detail = _get_session_detail(root, session_id)
            if not isinstance(detail, (NativeSessionDetail, V2SessionDetail)):
                raise ValueError(f"session {session_id} native detail is unavailable")
            summary = detail.summary
            if summary.session_id != session_id:
                raise ValueError(
                    f"session {session_id} metadata ID does not match its directory"
                )
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

    eligible = [item for item in eligible if item[1] not in protected]
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


def _protect_active_operation_ranges(
    metadata: dict[str, object],
    protected: set[str],
) -> None:
    active = metadata.get("active_operations")
    if not isinstance(active, dict):
        raise ValueError("v2 active_operations must be an object")
    for operation in active.values():
        if not isinstance(operation, dict):
            raise ValueError("v2 active operation metadata is malformed")
        ranges = operation.get("ranges")
        if not isinstance(ranges, list) or not ranges:
            raise ValueError("v2 active operation ranges are malformed")
        for evidence_range in ranges:
            if not isinstance(evidence_range, dict):
                raise ValueError("v2 active operation range is malformed")
            session_id = evidence_range.get("session_id")
            if not isinstance(session_id, str):
                raise ValueError("v2 active operation range session ID is invalid")
            protected.add(_metadata._validate_session_id(session_id))


def _protect_pending_attempt_origins(
    metadata: dict[str, object],
    protected: set[str],
) -> None:
    pending = metadata.get("pending_attempts")
    if not isinstance(pending, dict):
        raise ValueError("v2 pending_attempts must be an object")
    for attempt in pending.values():
        if not isinstance(attempt, dict):
            raise ValueError("v2 pending attempt metadata is malformed")
        session_id = attempt.get("session_id")
        if not isinstance(session_id, str):
            raise ValueError("v2 pending attempt session ID is invalid")
        protected.add(_metadata._validate_session_id(session_id))


def _parse_rfc3339_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must be an RFC 3339 UTC timestamp")
    return parsed.astimezone(timezone.utc)


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
