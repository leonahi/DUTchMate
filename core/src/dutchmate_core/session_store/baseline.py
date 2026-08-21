"""Authoritative project-wide baseline pointer operations."""

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.models import (
    BaselineError,
    BaselineMutationResult,
    BaselinePointer,
    NativeSessionDetail,
    SessionDetail,
    SessionPersistenceError,
    SessionQueryError,
)
from dutchmate_core.session_store.retrieval import get_session_detail as _get_session_detail

BaselineOperation = Literal["read_baseline", "mark_baseline", "clear_baseline"]
BASELINE_SCHEMA_VERSION = 1
BASELINE_FILENAME = "baseline.json"


def read_baseline_pointer(
    root: Path,
    *,
    operation: BaselineOperation = "read_baseline",
) -> BaselinePointer | None:
    """Read and validate the pointer and its eligible native target."""

    pointer_path = root / BASELINE_FILENAME
    if not pointer_path.exists():
        return None
    if pointer_path.is_symlink() or not pointer_path.is_file():
        raise _persistence_fault(
            operation=operation,
            detail="baseline pointer is not a regular file",
        )
    try:
        raw_pointer = _persistence.read_json_object(pointer_path)
        if raw_pointer.get("schema_version") != BASELINE_SCHEMA_VERSION:
            raise ValueError("baseline pointer schema_version must be 1")
        session_id = raw_pointer.get("session_id")
        marked_at = raw_pointer.get("marked_at")
        if not isinstance(session_id, str):
            raise ValueError("baseline pointer session_id must be a string")
        session_id = _metadata._validate_session_id(session_id)
        if not isinstance(marked_at, str):
            raise ValueError("baseline pointer marked_at must be a string")
        _validate_rfc3339_utc(marked_at, field="marked_at")
    except (SessionPersistenceError, ValueError) as exc:
        raise _persistence_fault(operation=operation, detail=str(exc)) from exc

    detail = _target_detail(
        root,
        session_id,
        operation=operation,
        pointer_target=True,
    )
    if not isinstance(detail, NativeSessionDetail):
        raise _persistence_fault(
            operation=operation,
            session_id=session_id,
            detail="baseline pointer target is not a native session",
        )
    reason = _ineligibility_reason(detail)
    if reason is not None:
        raise _persistence_fault(
            operation=operation,
            session_id=session_id,
            detail=f"baseline pointer target is not eligible: {reason}",
        )
    return BaselinePointer(session_id=session_id, marked_at=marked_at)


def mark_baseline(
    root: Path,
    session_id: str,
    *,
    clock: Callable[[], datetime],
) -> BaselineMutationResult:
    """Durably designate one eligible native completed session."""

    session_name = _metadata._validate_session_id(session_id)
    detail = _target_detail(
        root,
        session_name,
        operation="mark_baseline",
        pointer_target=False,
    )
    if not isinstance(detail, NativeSessionDetail):
        raise BaselineError(
            error="unsupported_session_schema",
            operation="mark_baseline",
            session_id=session_name,
            detected_schema_version=detail.summary.schema_version,
            detail="Only native schema-v1 sessions can be marked as baseline",
        )
    reason = _ineligibility_reason(detail)
    if reason is not None:
        raise BaselineError(
            error="invalid_session_state",
            operation="mark_baseline",
            session_id=session_name,
            reason=reason,
            detail=f"Session cannot be marked as baseline: {reason}",
        )

    current = read_baseline_pointer(root, operation="mark_baseline")
    if current is not None and current.session_id == session_name:
        return BaselineMutationResult(
            session_id=session_name,
            previous_session_id=session_name,
            changed=False,
            marked_at=current.marked_at,
            integrity=detail.summary.integrity,
        )

    marked_at = _metadata._format_utc_timestamp(clock())
    try:
        _persistence.write_json(
            root / BASELINE_FILENAME,
            {
                "schema_version": BASELINE_SCHEMA_VERSION,
                "session_id": session_name,
                "marked_at": marked_at,
            },
        )
    except SessionPersistenceError as exc:
        raise _persistence_fault(
            operation="mark_baseline",
            session_id=session_name,
            detail=str(exc),
        ) from exc
    return BaselineMutationResult(
        session_id=session_name,
        previous_session_id=current.session_id if current is not None else None,
        changed=True,
        marked_at=marked_at,
        integrity=detail.summary.integrity,
    )


def clear_baseline(root: Path, session_id: str) -> BaselineMutationResult:
    """Clear the pointer only when it currently names the requested session."""

    session_name = _metadata._validate_session_id(session_id)
    _target_detail(
        root,
        session_name,
        operation="clear_baseline",
        pointer_target=False,
    )
    current = read_baseline_pointer(root, operation="clear_baseline")
    if current is None or current.session_id != session_name:
        return BaselineMutationResult(
            session_id=session_name,
            previous_session_id=current.session_id if current is not None else None,
            changed=False,
            marked_at=current.marked_at if current is not None else None,
        )

    try:
        _persistence.remove_durable_file(root / BASELINE_FILENAME)
    except SessionPersistenceError as exc:
        raise _persistence_fault(
            operation="clear_baseline",
            session_id=session_name,
            detail=str(exc),
        ) from exc
    return BaselineMutationResult(
        session_id=session_name,
        previous_session_id=session_name,
        changed=True,
        marked_at=current.marked_at,
    )


def _target_detail(
    root: Path,
    session_id: str,
    *,
    operation: BaselineOperation,
    pointer_target: bool,
) -> SessionDetail:
    try:
        return _get_session_detail(root, session_id)
    except SessionQueryError as exc:
        if pointer_target:
            raise _persistence_fault(
                operation=operation,
                session_id=session_id,
                detail=f"baseline pointer target is invalid: {exc}",
            ) from exc
        raise BaselineError(
            error=exc.error,
            operation=operation,
            session_id=session_id,
            detected_schema_version=exc.detected_schema_version,
            detail=str(exc),
        ) from exc


def _ineligibility_reason(detail: NativeSessionDetail) -> str | None:
    summary = detail.summary
    if summary.state != "completed":
        return "state_not_completed"
    if summary.workflow not in {"capture", "boot_test"}:
        return "workflow_not_baseline_eligible"
    if summary.truncated:
        return "truncated"
    if summary.interrupted:
        return "interrupted"
    if summary.integrity.loss_status == "loss_reported":
        return "loss_reported"
    return None


def _validate_rfc3339_utc(value: str, *, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != timezone.utc.utcoffset(parsed):
        raise ValueError(f"{field} must be an RFC 3339 UTC timestamp")
    return parsed.astimezone(timezone.utc)


def _persistence_fault(
    *,
    operation: BaselineOperation,
    detail: str,
    session_id: str | None = None,
) -> BaselineError:
    return BaselineError(
        error="persistence_fault",
        operation=operation,
        session_id=session_id,
        detail=detail,
    )
