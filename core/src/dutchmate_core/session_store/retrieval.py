"""Bounded schema-aware session list and detail projections."""

from __future__ import annotations

import base64
import binascii
import json
import time
import unicodedata
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Final, Literal, cast

import dutchmate_core.session_store.evidence as _evidence
import dutchmate_core.session_store.metadata as _metadata
import dutchmate_core.session_store.persistence as _persistence
from dutchmate_core.session_store.models import (
    EvidenceTypeCount,
    FirstError,
    FirstErrorReference,
    LegacySessionDetail,
    LegacySessionListItem,
    NativeSessionDetail,
    NativeSessionListItem,
    SessionArtifact,
    SessionDetail,
    SessionListItem,
    SessionListPage,
    SessionPaths,
    SessionPersistenceError,
    SessionQueryError,
    SessionSummary,
)
from dutchmate_core.validation import InputValidationError, validate_serial_port

QueryOperation = Literal["list_sessions", "get_session", "get_logs"]

DEFAULT_SESSION_PAGE_LIMIT: Final = 50
MAX_SESSION_PAGE_LIMIT: Final = 100
_CURSOR_VERSION: Final = 1
_MAX_CURSOR_BYTES: Final = 1024
_SNAPSHOT_ATTEMPTS: Final = 20
_TRANSACTION_MARKER: Final = ".evidence-transaction.json"
_ARTIFACT_NAMES: Final = (
    "metadata.json",
    "uart_raw.log",
    "uart_events.jsonl",
    "hardware_events.jsonl",
    "detected_patterns.json",
)
_FAILURE_PATTERNS: Final = frozenset({"ERROR", "ASSERT", "PANIC", "HardFault"})
_SUCCESS_PATTERNS: Final = frozenset({"BOOT_OK"})
_HARDWARE_EVENT_TYPES: Final = frozenset(
    {
        "buffer_overflow",
        "buffer_status",
        "control_action",
        "line_limit_exceeded",
        "timestamp_discontinuity",
        "uart_tx_attempt",
        "uart_tx_result",
        "usb_disconnect",
        "usb_reconnect",
    }
)
_END_REASONS: Final = frozenset(
    {
        "backend_error",
        "backend_input_error",
        "duration_elapsed",
        "internal_error",
        "pattern_matched",
        "persistence_error",
        "reconnect_limit",
        "reconnect_timeout",
        "service_restart",
        "size_limit",
        "timeout",
        "user_stop",
    }
)
_TRUNCATION_KEYS: Final = frozenset(
    {
        "reason",
        "rejected_unit_type",
        "rejected_unit_evidence_bytes",
        "projected_evidence_bytes",
        "rejected_uart_payload_bytes",
        "segment_id",
        "channel",
        "timestamp_us",
        "occurred_at",
    }
)


def list_session_page(
    root: Path,
    *,
    limit: int = DEFAULT_SESSION_PAGE_LIMIT,
    cursor: str | None = None,
    baseline_session_id: str | None = None,
) -> SessionListPage:
    """Return one stable newest-first page across native and legacy sessions."""

    _validate_page_limit(limit)
    boundary = _decode_cursor(cursor)
    if not root.exists():
        return SessionListPage(items=(), next_cursor=None)

    items: list[SessionListItem] = []
    try:
        roots = tuple(root.iterdir())
    except OSError as exc:
        raise _query_fault(
            operation="list_sessions",
            session_id=None,
            detail=f"Unable to enumerate session storage: {_os_detail(exc)}",
        ) from exc

    for session_root in roots:
        if session_root.is_symlink() or not session_root.is_dir():
            continue
        paths = _persistence.session_paths(session_root)
        if not paths.metadata.is_file():
            continue
        item = _list_item(
            paths,
            operation="list_sessions",
            baseline_session_id=baseline_session_id,
        )
        if boundary is None or _item_key(item) < boundary:
            items.append(item)

    items.sort(key=_item_key, reverse=True)
    page_items = items[:limit]
    next_cursor = (
        _encode_cursor(_item_key(page_items[-1])) if len(items) > limit and page_items else None
    )
    return SessionListPage(items=tuple(page_items), next_cursor=next_cursor)


def get_session_detail(
    root: Path,
    session_id: str,
    *,
    baseline_session_id: str | None = None,
) -> SessionDetail:
    """Return bounded native detail or a legacy read-only compatibility view."""

    session_name = _metadata._validate_session_id(session_id)
    session_root = root / session_name
    if session_root.is_symlink() or not session_root.exists():
        raise SessionQueryError(
            error="not_found",
            operation="get_session",
            session_id=session_name,
            detail=f"Session '{session_name}' was not found",
        )
    if not session_root.is_dir():
        raise _query_fault(
            operation="get_session",
            session_id=session_name,
            detail="Session path is not a directory",
        )
    paths = _persistence.session_paths(session_root)
    if not paths.metadata.exists():
        raise _query_fault(
            operation="get_session",
            session_id=session_name,
            detail="Session metadata is missing",
        )

    metadata = _read_metadata(paths, operation="get_session")
    schema_version = _schema_version(
        metadata,
        operation="get_session",
        session_id=session_name,
    )
    if schema_version == 0:
        summary = _legacy_item(metadata, session_name, operation="get_session")
        return LegacySessionDetail(
            summary=summary,
            artifacts=_legacy_artifacts(paths, operation="get_session"),
        )
    if schema_version != 1:
        raise _unsupported_schema(
            operation="get_session",
            session_id=session_name,
            detected=schema_version,
        )
    return _native_detail(
        paths,
        metadata,
        baseline_session_id=baseline_session_id,
    )


def _list_item(
    paths: SessionPaths,
    *,
    operation: QueryOperation,
    baseline_session_id: str | None,
) -> SessionListItem:
    metadata = _read_metadata(paths, operation=operation)
    session_id = paths.root.name
    schema_version = _schema_version(
        metadata,
        operation=operation,
        session_id=session_id,
    )
    if schema_version == 0:
        return _legacy_item(metadata, session_id, operation=operation)
    if schema_version != 1:
        raise _unsupported_schema(
            operation=operation,
            session_id=session_id,
            detected=schema_version,
        )
    summary, _patterns = _stable_native_summary(paths, metadata, operation=operation)
    return _native_item(summary, baseline_session_id=baseline_session_id)


def _native_detail(
    paths: SessionPaths,
    initial_metadata: dict[str, object],
    *,
    baseline_session_id: str | None,
) -> NativeSessionDetail:
    operation: Literal["get_session"] = "get_session"
    metadata = initial_metadata
    for _attempt in range(_SNAPSHOT_ATTEMPTS):
        if _transaction_active(paths):
            time.sleep(0.001)
            metadata = _read_metadata(paths, operation=operation)
            continue
        try:
            _artifact_size(paths.detected_patterns)
            patterns = _persistence.read_json_list(paths.detected_patterns)
            summary = _validated_summary(metadata, patterns, paths, operation=operation)
            _validate_wait_reference(summary, patterns)
            uart_records = _count_jsonl(paths.uart_events)
            hardware_records, hardware_counts, unresolved = _hardware_summary(
                paths.hardware_events
            )
            artifacts = _native_artifacts(
                paths,
                uart_records=uart_records,
                hardware_records=hardware_records,
                pattern_records=len(patterns),
            )
            metadata_after = _read_metadata(paths, operation=operation)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            SessionPersistenceError,
            ValueError,
        ) as exc:
            raise _query_fault(
                operation=operation,
                session_id=paths.root.name,
                detail=f"Session evidence is invalid: {_exception_detail(exc)}",
            ) from exc
        if not _transaction_active(paths) and metadata_after == metadata:
            try:
                return _build_native_detail(
                    metadata=metadata,
                    summary=summary,
                    patterns=patterns,
                    hardware_counts=hardware_counts,
                    unresolved_uart_tx_attempts=unresolved,
                    artifacts=artifacts,
                    baseline_session_id=baseline_session_id,
                )
            except ValueError as exc:
                raise _query_fault(
                    operation=operation,
                    session_id=paths.root.name,
                    detail=f"Session metadata is invalid: {exc}",
                ) from exc
        metadata = metadata_after
        time.sleep(0.001)
    raise _query_fault(
        operation=operation,
        session_id=paths.root.name,
        detail="Session changed continuously while creating a stable detail snapshot",
    )


def _stable_native_summary(
    paths: SessionPaths,
    initial_metadata: dict[str, object],
    *,
    operation: QueryOperation,
) -> tuple[SessionSummary, list[object]]:
    metadata = initial_metadata
    for _attempt in range(_SNAPSHOT_ATTEMPTS):
        if _transaction_active(paths):
            time.sleep(0.001)
            metadata = _read_metadata(paths, operation=operation)
            continue
        try:
            _artifact_size(paths.detected_patterns)
            patterns = _persistence.read_json_list(paths.detected_patterns)
            summary = _validated_summary(metadata, patterns, paths, operation=operation)
            _validate_wait_reference(summary, patterns)
            metadata_after = _read_metadata(paths, operation=operation)
        except (
            OSError,
            UnicodeError,
            json.JSONDecodeError,
            SessionPersistenceError,
            ValueError,
        ) as exc:
            raise _query_fault(
                operation=operation,
                session_id=paths.root.name,
                detail=f"Session metadata is invalid: {_exception_detail(exc)}",
            ) from exc
        if not _transaction_active(paths) and metadata_after == metadata:
            return summary, patterns
        metadata = metadata_after
        time.sleep(0.001)
    raise _query_fault(
        operation=operation,
        session_id=paths.root.name,
        detail="Session changed continuously while creating a stable list snapshot",
    )


def _validated_summary(
    metadata: dict[str, object],
    patterns: list[object],
    paths: SessionPaths,
    *,
    operation: QueryOperation,
) -> SessionSummary:
    try:
        summary = _metadata._summary_from_metadata(metadata, detected_patterns=patterns)
        if summary.session_id != paths.root.name:
            raise ValueError("session metadata ID does not match its directory")
        if summary.schema_version != 1:
            raise ValueError("native session projection requires schema version 1")
        _validate_timestamp(summary.started_at, "started_at")
        if summary.ended_at is not None:
            _validate_timestamp(summary.ended_at, "ended_at")
        if summary.end_reason is not None and summary.end_reason not in _END_REASONS:
            raise ValueError("native session end_reason is invalid")
        if summary.backend_mode is None or summary.state is None or summary.workflow is None:
            raise ValueError("native session lifecycle/backend facts are incomplete")
        if summary.integrity is None or summary.capability_policy is None:
            raise ValueError("native session integrity/capability policy is required")
        _metadata._validate_session_command(summary.command)
        if summary.port is None:
            raise ValueError("native session backend port is required")
        validate_serial_port(summary.port)
        if summary.backend_mode == "basic":
            if summary.device is not None or summary.firmware is not None:
                raise ValueError("native Basic identity must omit device and firmware")
        else:
            _required_native_identity(summary.device, "device")
            _required_native_identity(summary.firmware, "firmware")
        identity = _required_object(metadata, "backend_identity")
        if set(identity) != {"port", "device", "firmware"}:
            raise ValueError("native backend_identity fields are invalid")
        _metadata._contiguous_native_segments(metadata)
        _validate_error(summary.error)
        _bounded_truncation(summary.truncation)
        return summary
    except ValueError as exc:
        raise _query_fault(
            operation=operation,
            session_id=paths.root.name,
            detail=f"Session metadata is invalid: {exc}",
        ) from exc


def _native_item(
    summary: SessionSummary,
    *,
    baseline_session_id: str | None,
) -> NativeSessionListItem:
    if (
        summary.state is None
        or summary.workflow is None
        or summary.backend_mode is None
        or summary.integrity is None
    ):
        raise ValueError("native summary is missing required fields")
    return NativeSessionListItem(
        session_id=summary.session_id,
        started_at=summary.started_at,
        state=summary.state,
        workflow=summary.workflow,
        ended_at=summary.ended_at,
        end_reason=summary.end_reason,
        backend_mode=summary.backend_mode,
        baseline=summary.session_id == baseline_session_id,
        truncated=summary.truncated,
        truncation=_bounded_truncation(summary.truncation),
        interrupted=summary.interrupted,
        resumed=summary.resumed,
        segment_count=summary.segment_count,
        integrity=summary.integrity,
        line_processing=summary.line_processing,
        first_error=_first_error_reference(summary.first_error),
    )


def _validate_wait_reference(
    summary: SessionSummary,
    patterns: list[object],
) -> None:
    if summary.workflow != "wait_pattern" or summary.detected_pattern_index is None:
        return
    detected = _evidence.detected_pattern_at(
        patterns,
        summary.detected_pattern_index,
    )
    if detected.pattern != summary.wait_pattern:
        raise ValueError("wait-pattern metadata does not reference its requested pattern")


def _build_native_detail(
    *,
    metadata: dict[str, object],
    summary: SessionSummary,
    patterns: list[object],
    hardware_counts: Counter[str],
    unresolved_uart_tx_attempts: int,
    artifacts: tuple[SessionArtifact, ...],
    baseline_session_id: str | None,
) -> NativeSessionDetail:
    backend_identity = _required_object(metadata, "backend_identity")
    storage = _required_object(metadata, "storage")
    policy = summary.capability_policy
    if policy is None or summary.reconnect_timeout_s is None:
        raise ValueError("native session detail is missing required policy")
    commanded_boot_mode = metadata.get("commanded_boot_mode")
    if commanded_boot_mode not in {None, "normal", "bootloader"}:
        raise ValueError("native commanded_boot_mode is invalid")
    segments = _metadata._contiguous_native_segments(metadata)
    _validate_storage(storage, artifacts)
    return NativeSessionDetail(
        summary=_native_item(summary, baseline_session_id=baseline_session_id),
        command=summary.command,
        duration_s=summary.duration_s,
        reconnect_timeout_s=summary.reconnect_timeout_s,
        error=summary.error,
        backend_identity=backend_identity.copy(),
        backend_capabilities=summary.backend_capabilities,
        capabilities=summary.capabilities,
        capability_policy=policy,
        commanded_boot_mode=commanded_boot_mode,
        storage=storage.copy(),
        segments=tuple(segment.copy() for segment in segments),
        first_error=summary.first_error,
        pattern_counts=_pattern_counts(patterns),
        hardware_event_counts=_counter_projection(hardware_counts),
        unresolved_uart_tx_attempts=unresolved_uart_tx_attempts,
        artifacts=artifacts,
        wait_pattern=summary.wait_pattern,
        match_mode=summary.match_mode,
        case_sensitive=summary.case_sensitive,
        timeout_s=summary.timeout_s,
        matched=summary.matched,
        detected_pattern_index=summary.detected_pattern_index,
    )


def _legacy_item(
    metadata: dict[str, object],
    directory_session_id: str,
    *,
    operation: QueryOperation,
) -> LegacySessionListItem:
    try:
        session_id = _required_string(metadata, "session_id")
        if session_id != directory_session_id:
            raise ValueError("session metadata ID does not match its directory")
        _metadata._validate_session_id(session_id)
        started_at = _required_string(metadata, "started_at")
        _validate_timestamp(started_at, "started_at")
        command = _required_string(metadata, "command")
        _metadata._validate_session_command(command)
        firmware = _legacy_identity(metadata.get("firmware"), "firmware")
        device = _legacy_identity(metadata.get("device"), "device")
        return LegacySessionListItem(
            session_id=session_id,
            started_at=started_at,
            command=command,
            firmware=firmware,
            device=device,
        )
    except ValueError as exc:
        raise _query_fault(
            operation=operation,
            session_id=directory_session_id,
            detail=f"Legacy session metadata is invalid: {exc}",
        ) from exc


def _read_metadata(
    paths: SessionPaths,
    *,
    operation: QueryOperation,
) -> dict[str, object]:
    if paths.metadata.is_symlink() or not paths.metadata.is_file():
        raise _query_fault(
            operation=operation,
            session_id=paths.root.name,
            detail="Session metadata is missing or invalid",
        )
    try:
        return _persistence.read_json_object(paths.metadata)
    except (
        OSError,
        UnicodeError,
        json.JSONDecodeError,
        SessionPersistenceError,
        ValueError,
    ) as exc:
        raise _query_fault(
            operation=operation,
            session_id=paths.root.name,
            detail=f"Unable to read session metadata: {_exception_detail(exc)}",
        ) from exc


def _schema_version(
    metadata: dict[str, object],
    *,
    operation: QueryOperation,
    session_id: str,
) -> int:
    value = metadata.get("schema_version", 0)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise _query_fault(
            operation=operation,
            session_id=session_id,
            detail="Session schema_version is malformed",
        )
    return value


def _native_artifacts(
    paths: SessionPaths,
    *,
    uart_records: int,
    hardware_records: int,
    pattern_records: int,
) -> tuple[SessionArtifact, ...]:
    return (
        SessionArtifact("metadata.json", _artifact_size(paths.metadata), 1),
        SessionArtifact("uart_raw.log", _artifact_size(paths.uart_raw), None),
        SessionArtifact("uart_events.jsonl", _artifact_size(paths.uart_events), uart_records),
        SessionArtifact(
            "hardware_events.jsonl",
            _artifact_size(paths.hardware_events),
            hardware_records,
        ),
        SessionArtifact(
            "detected_patterns.json",
            _artifact_size(paths.detected_patterns),
            pattern_records,
        ),
    )


def _legacy_artifacts(
    paths: SessionPaths,
    *,
    operation: Literal["get_session"],
) -> tuple[SessionArtifact, ...]:
    try:
        path_by_name = {
            "metadata.json": paths.metadata,
            "uart_raw.log": paths.uart_raw,
            "uart_events.jsonl": paths.uart_events,
            "hardware_events.jsonl": paths.hardware_events,
            "detected_patterns.json": paths.detected_patterns,
        }
        return tuple(
            SessionArtifact(name=name, bytes=_artifact_size(path_by_name[name]), records=None)
            for name in _ARTIFACT_NAMES
        )
    except (OSError, SessionPersistenceError, ValueError) as exc:
        raise _query_fault(
            operation=operation,
            session_id=paths.root.name,
            detail=f"Legacy session artifact is invalid: {_exception_detail(exc)}",
        ) from exc


def _count_jsonl(path: Path) -> int:
    count = 0
    for _record in _iter_jsonl_objects(path):
        count += 1
    return count


def _hardware_summary(path: Path) -> tuple[int, Counter[str], int]:
    counts: Counter[str] = Counter()
    pending_attempts: set[str] = set()
    total = 0
    for record in _iter_jsonl_objects(path):
        event_type = record.get("type")
        if not isinstance(event_type, str) or event_type not in _HARDWARE_EVENT_TYPES:
            raise ValueError("hardware event type is invalid")
        counts[event_type] += 1
        total += 1
        if event_type == "uart_tx_attempt":
            attempt_id = _required_string(record, "attempt_id")
            if attempt_id in pending_attempts:
                raise ValueError("duplicate unresolved UART TX attempt ID")
            pending_attempts.add(attempt_id)
        elif event_type == "uart_tx_result":
            attempt_id = _required_string(record, "attempt_id")
            if attempt_id not in pending_attempts:
                raise ValueError("UART TX result has no preceding unresolved attempt")
            pending_attempts.remove(attempt_id)
    return total, counts, len(pending_attempts)


def _iter_jsonl_objects(path: Path) -> Iterator[dict[str, object]]:
    _artifact_size(path)
    try:
        with path.open("rb") as file:
            for raw_line in file:
                if not raw_line.endswith(b"\n"):
                    raise ValueError(f"{path.name} contains an incomplete record")
                if raw_line == b"\n":
                    raise ValueError(f"{path.name} contains an empty record")
                value = json.loads(raw_line.decode("utf-8"))
                if not isinstance(value, dict):
                    raise ValueError(f"{path.name} records must be JSON objects")
                yield cast(dict[str, object], value)
    except OSError as exc:
        raise SessionPersistenceError(
            operation="read",
            path=path,
            detail=_os_detail(exc),
        ) from exc


def _pattern_counts(patterns: list[object]) -> tuple[EvidenceTypeCount, ...]:
    counts: Counter[str] = Counter()
    for raw_pattern in patterns:
        if not isinstance(raw_pattern, dict):
            raise ValueError("detected patterns must contain JSON objects")
        pattern = raw_pattern.get("pattern")
        if not isinstance(pattern, str) or not pattern:
            raise ValueError("detected pattern name must be a non-empty string")
        classification = (
            "failure"
            if pattern in _FAILURE_PATTERNS
            else "success"
            if pattern in _SUCCESS_PATTERNS
            else "other"
        )
        counts[classification] += 1
    return _counter_projection(counts)


def _counter_projection(counts: Counter[str]) -> tuple[EvidenceTypeCount, ...]:
    return tuple(
        EvidenceTypeCount(type=name, count=count)
        for name, count in sorted(counts.items())
    )


def _first_error_reference(error: FirstError | None) -> FirstErrorReference | None:
    if error is None:
        return None
    return FirstErrorReference(
        pattern=error.pattern,
        detected_pattern_index=error.detected_pattern_index,
        segment_id=error.segment_id,
        timestamp_us=error.timestamp_us,
        channel=error.channel,
        ingestion_index=error.ingestion_index,
        line_index_in_event=error.line_index_in_event,
    )


def _validate_page_limit(limit: object) -> None:
    if (
        isinstance(limit, bool)
        or not isinstance(limit, int)
        or not 1 <= limit <= MAX_SESSION_PAGE_LIMIT
    ):
        raise InputValidationError(
            f"session limit must be an integer from 1 to {MAX_SESSION_PAGE_LIMIT}"
        )


def _encode_cursor(boundary: tuple[str, str]) -> str:
    payload = json.dumps(
        {"v": _CURSOR_VERSION, "started_at": boundary[0], "session_id": boundary[1]},
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).rstrip(b"=").decode("ascii")


def _decode_cursor(cursor: str | None) -> tuple[str, str] | None:
    if cursor is None:
        return None
    if not isinstance(cursor, str) or not cursor:
        raise InputValidationError("session cursor must be a non-empty string")
    try:
        encoded = cursor.encode("ascii")
    except UnicodeEncodeError as exc:
        raise InputValidationError("session cursor must be URL-safe ASCII") from exc
    if len(encoded) > _MAX_CURSOR_BYTES:
        raise InputValidationError("session cursor is too large")
    padding = b"=" * (-len(encoded) % 4)
    try:
        decoded = base64.b64decode(encoded + padding, altchars=b"-_", validate=True)
        value = json.loads(decoded.decode("utf-8"))
    except (binascii.Error, UnicodeError, json.JSONDecodeError) as exc:
        raise InputValidationError("session cursor is invalid") from exc
    if not isinstance(value, dict) or set(value) != {"v", "started_at", "session_id"}:
        raise InputValidationError("session cursor payload is invalid")
    if value.get("v") != _CURSOR_VERSION:
        raise InputValidationError("session cursor version is unsupported")
    started_at = value.get("started_at")
    session_id = value.get("session_id")
    if not isinstance(started_at, str) or not isinstance(session_id, str):
        raise InputValidationError("session cursor boundary is invalid")
    try:
        _validate_timestamp(started_at, "cursor started_at")
        _metadata._validate_session_id(session_id)
    except ValueError as exc:
        raise InputValidationError("session cursor boundary is invalid") from exc
    return started_at, session_id


def _item_key(item: SessionListItem) -> tuple[str, str]:
    return item.started_at, item.session_id


def _required_string(value: dict[str, object], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"'{key}' must be a non-empty string")
    return result


def _required_object(value: dict[str, object], key: str) -> dict[str, object]:
    result = value.get(key)
    if not isinstance(result, dict):
        raise ValueError(f"'{key}' must be a JSON object")
    return cast(dict[str, object], result)


def _legacy_identity(value: object, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"legacy {field} must be null or a string")
    encoded = value.encode("utf-8")
    if not 1 <= len(encoded) <= 64:
        raise ValueError(f"legacy {field} must encode to 1..64 UTF-8 bytes")
    if value[0].isspace() or value[-1].isspace():
        raise ValueError(f"legacy {field} must not have edge whitespace")
    if any(unicodedata.category(character) == "Cc" for character in value):
        raise ValueError(f"legacy {field} must not contain control characters")
    return value


def _required_native_identity(value: str | None, field: str) -> str:
    result = _legacy_identity(value, field)
    if result is None:
        raise ValueError(f"native Enhanced {field} is required")
    return result


def _validate_storage(
    storage: dict[str, object],
    artifacts: tuple[SessionArtifact, ...],
) -> None:
    budget = storage.get("evidence_budget_bytes")
    written = storage.get("evidence_bytes_written")
    metadata_max = storage.get("metadata_max_bytes")
    if isinstance(budget, bool) or not isinstance(budget, int) or budget <= 0:
        raise ValueError("native evidence budget is invalid")
    if isinstance(written, bool) or not isinstance(written, int) or written < 0:
        raise ValueError("native evidence byte accounting is invalid")
    if metadata_max != _metadata.METADATA_MAX_BYTES:
        raise ValueError("native metadata byte limit is invalid")
    evidence_bytes = sum(
        artifact.bytes for artifact in artifacts if artifact.name != "metadata.json"
    )
    if written != evidence_bytes:
        raise ValueError("native evidence byte accounting does not match artifacts")


def _validate_error(error: dict[str, object] | None) -> None:
    if error is None:
        return
    if set(error) != {"code", "detail", "detail_truncated"}:
        raise ValueError("native session error fields are invalid")
    code = error.get("code")
    detail = error.get("detail")
    truncated = error.get("detail_truncated")
    if not isinstance(code, str) or not 1 <= len(code.encode("utf-8")) <= 64:
        raise ValueError("native session error code is invalid")
    if not isinstance(detail, str) or not 1 <= len(detail.encode("utf-8")) <= 1024:
        raise ValueError("native session error detail is invalid")
    if not isinstance(truncated, bool):
        raise ValueError("native session error truncation flag is invalid")
    if any(unicodedata.category(character) == "Cc" for character in detail):
        raise ValueError("native session error detail contains control characters")


def _bounded_truncation(value: dict[str, object] | None) -> dict[str, object] | None:
    if value is None:
        return None
    if set(value) != _TRUNCATION_KEYS:
        raise ValueError("native session truncation fields are invalid")
    if value.get("reason") != "size_limit":
        raise ValueError("native session truncation reason is invalid")
    if value.get("rejected_unit_type") not in {
        "uart_receive",
        "hardware_event",
        "session_event",
        "uart_tx_attempt",
    }:
        raise ValueError("native session rejected unit type is invalid")
    for field in ("rejected_unit_evidence_bytes", "projected_evidence_bytes"):
        _optional_non_negative_int(value.get(field), field, required=True)
    for field in (
        "rejected_uart_payload_bytes",
        "segment_id",
        "channel",
        "timestamp_us",
    ):
        _optional_non_negative_int(value.get(field), field, required=False)
    occurred_at = value.get("occurred_at")
    if not isinstance(occurred_at, str):
        raise ValueError("native session truncation occurred_at is invalid")
    _validate_timestamp(occurred_at, "truncation occurred_at")
    return value.copy()


def _optional_non_negative_int(value: object, field: str, *, required: bool) -> None:
    if value is None and not required:
        return
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"native session truncation {field} is invalid")


def _validate_timestamp(value: str, field: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"session {field} must be an RFC 3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"session {field} must include a UTC offset")


def _artifact_size(path: Path) -> int:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f"required artifact {path.name} is missing or invalid")
    try:
        return path.stat().st_size
    except OSError as exc:
        raise SessionPersistenceError(
            operation="stat",
            path=path,
            detail=_os_detail(exc),
        ) from exc


def _transaction_active(paths: SessionPaths) -> bool:
    return paths.root.joinpath(_TRANSACTION_MARKER).exists()


def _unsupported_schema(
    *,
    operation: QueryOperation,
    session_id: str,
    detected: int,
) -> SessionQueryError:
    return SessionQueryError(
        error="unsupported_session_schema",
        operation=operation,
        session_id=session_id,
        detected_schema_version=detected,
        detail=f"Session '{session_id}' uses unsupported schema version {detected}",
    )


def _query_fault(
    *,
    operation: QueryOperation,
    session_id: str | None,
    detail: str,
) -> SessionQueryError:
    return SessionQueryError(
        error="persistence_fault",
        operation=operation,
        session_id=session_id,
        detail=detail,
    )


def _exception_detail(exc: BaseException) -> str:
    return str(exc) or type(exc).__name__


def _os_detail(exc: OSError) -> str:
    return exc.strerror or str(exc) or type(exc).__name__
