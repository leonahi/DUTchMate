"""Session metadata construction, validation, and projection."""

import math
import unicodedata
from datetime import datetime, timezone
from typing import cast
from uuid import uuid4

from dutchmate_core.backends.contracts import (
    BackendCapabilityPolicy,
    BackendMode,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.evidence import first_error as _first_error
from dutchmate_core.session_store.models import (
    LineProcessing,
    SessionState,
    SessionSummary,
    SessionWorkflow,
)
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES

METADATA_MAX_BYTES = 262144


def _validate_session_id(session_id: str) -> str:
    if (
        not isinstance(session_id, str)
        or not session_id
        or session_id.strip() != session_id
        or session_id in {".", ".."}
        or "/" in session_id
        or "\\" in session_id
    ):
        raise ValueError("session ID must be a non-empty path-safe name")
    return session_id


def _validate_session_limit(limit: int | None) -> None:
    if limit is not None and (isinstance(limit, bool) or not isinstance(limit, int) or limit <= 0):
        raise ValueError("session limit must be a positive integer")


def _validate_session_command(command: str) -> None:
    if not isinstance(command, str) or not command:
        raise ValueError("session command must not be empty")
    if len(command.encode("utf-8")) > 256:
        raise ValueError("session command must contain at most 256 UTF-8 bytes")
    if any(unicodedata.category(character) == "Cc" for character in command):
        raise ValueError("session command must not contain control characters")


def _validate_native_lifecycle_inputs(
    *,
    workflow: SessionWorkflow | None,
    duration_s: float | None,
    reconnect_timeout_s: float | None,
    backend_snapshot: BackendSnapshot | None,
) -> None:
    if workflow is None:
        if duration_s is not None or reconnect_timeout_s is not None:
            raise ValueError("native lifecycle values require a workflow")
        return
    if backend_snapshot is None:
        raise ValueError("native sessions require a backend snapshot")
    if workflow in {"capture", "boot_test"}:
        _require_positive_number(duration_s, "duration_s")
    elif duration_s is not None:
        raise ValueError("wait-pattern duration_s must be null")
    _require_positive_number(reconnect_timeout_s, "reconnect_timeout_s")


def _require_positive_number(value: object, field: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(float(value))
        or float(value) <= 0
    ):
        raise ValueError(f"native session {field} must be a positive finite number")
    return float(value)


def _initial_metadata(
    *,
    session_id: str,
    started_at: str,
    command: str,
    firmware: str | None,
    device: str | None,
    baseline: bool,
    backend_snapshot: BackendSnapshot | None,
    workflow: SessionWorkflow | None,
    duration_s: float | None,
    reconnect_timeout_s: float | None,
    evidence_budget_bytes: int,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "session_id": session_id,
        "started_at": started_at,
        "command": command,
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "baseline": baseline,
        "firmware": firmware,
        "device": device,
        "line_processing": _line_processing_json(LineProcessing()),
        "segments": [
            {
                "segment_id": 0,
                "started_at": started_at,
                "ended_at": None,
                "end_reason": None,
                "hello": None,
                "first_device_timestamp_us": None,
                "last_device_timestamp_us": None,
                "timestamp_epoch": 0,
            }
        ],
    }
    if backend_snapshot is None:
        return metadata

    metadata.update(
        {
            "backend_mode": backend_snapshot.info.mode,
            "backend_identity": {
                "port": backend_snapshot.info.port,
                "device": backend_snapshot.info.device,
                "firmware": backend_snapshot.info.firmware,
            },
            "backend_capabilities": sorted(backend_snapshot.info.capabilities),
            "capabilities": sorted(backend_snapshot.capabilities),
            "capability_policy": _capability_policy_json(backend_snapshot.capability_policy),
            "integrity": _integrity_json(backend_snapshot.integrity),
            "segments": [
                _backend_segment_json(
                    backend_snapshot,
                    started_at=started_at,
                )
            ],
        }
    )
    if workflow is not None:
        metadata = {
            "schema_version": 1,
            "session_id": session_id,
            "started_at": started_at,
            "state": "active",
            "workflow": workflow,
            "duration_s": duration_s,
            "reconnect_timeout_s": reconnect_timeout_s,
            "ended_at": None,
            "end_reason": None,
            "error": None,
            "command": command,
            "backend_mode": backend_snapshot.info.mode,
            "backend_identity": {
                "port": backend_snapshot.info.port,
                "device": backend_snapshot.info.device,
                "firmware": backend_snapshot.info.firmware,
            },
            "backend_capabilities": sorted(backend_snapshot.info.capabilities),
            "capabilities": sorted(backend_snapshot.capabilities),
            "capability_policy": _capability_policy_json(backend_snapshot.capability_policy),
            "commanded_boot_mode": None,
            "integrity": _integrity_json(backend_snapshot.integrity),
            "line_processing": _line_processing_json(LineProcessing()),
            "storage": {
                "evidence_budget_bytes": evidence_budget_bytes,
                "evidence_bytes_written": 3,
                "metadata_max_bytes": METADATA_MAX_BYTES,
            },
            "truncated": False,
            "truncation": None,
            "interrupted": False,
            "resumed": False,
            "overflow": False,
            "segments": [_backend_segment_json(backend_snapshot, started_at=started_at)],
        }
    return metadata


def _summary_from_metadata(
    metadata: dict[str, object],
    *,
    detected_patterns: list[object],
) -> SessionSummary:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

    schema_version = metadata.get("schema_version", 0)
    if isinstance(schema_version, bool) or not isinstance(schema_version, int):
        raise ValueError("session metadata schema_version must be an integer")
    if schema_version not in {0, 1}:
        raise ValueError(f"unsupported session schema version: {schema_version}")
    native = schema_version == 1
    backend_mode = _optional_backend_mode(metadata.get("backend_mode"))
    backend_identity = _optional_object(metadata.get("backend_identity"), "backend_identity")
    state = _native_state(metadata.get("state")) if native else None
    workflow = _native_workflow(metadata.get("workflow")) if native else None
    duration_s = _optional_positive_number(metadata.get("duration_s")) if native else None
    reconnect_timeout_s = (
        _optional_positive_number(metadata.get("reconnect_timeout_s")) if native else None
    )
    ended_at = _optional_str(metadata, "ended_at") if native else None
    end_reason = _optional_str(metadata, "end_reason") if native else None
    error = _optional_object(metadata.get("error"), "error") if native else None
    if native:
        if backend_mode is None or backend_identity is None:
            raise ValueError("native session backend identity is required")
        if not 1 <= len(segments) <= 32:
            raise ValueError("native session must contain 1..32 segments")
        if workflow in {"capture", "boot_test"} and duration_s is None:
            raise ValueError("native capture-like session duration_s is required")
        if reconnect_timeout_s is None:
            raise ValueError("native session reconnect_timeout_s is required")
        _validate_native_lifecycle_metadata(
            state=state,
            ended_at=ended_at,
            end_reason=end_reason,
            error=error,
        )
    return SessionSummary(
        session_id=_required_str(metadata, "session_id"),
        started_at=_required_str(metadata, "started_at"),
        command=_required_str(metadata, "command"),
        truncated=_required_bool(metadata, "truncated"),
        interrupted=_required_bool(metadata, "interrupted"),
        resumed=_required_bool(metadata, "resumed"),
        overflow=_required_bool(metadata, "overflow"),
        baseline=False if native else _required_bool(metadata, "baseline"),
        firmware=(
            _optional_str(backend_identity, "firmware")
            if native and backend_identity is not None
            else _optional_str(metadata, "firmware")
        ),
        device=(
            _optional_str(backend_identity, "device")
            if native and backend_identity is not None
            else _optional_str(metadata, "device")
        ),
        segment_count=len(segments),
        backend_mode=backend_mode,
        port=(_optional_str(backend_identity, "port") if backend_identity is not None else None),
        backend_capabilities=_optional_string_tuple(metadata, "backend_capabilities"),
        capabilities=_optional_string_tuple(metadata, "capabilities"),
        capability_policy=_optional_capability_policy(metadata.get("capability_policy")),
        integrity=_optional_integrity(metadata.get("integrity")),
        segment_contexts=_segment_contexts(segments),
        first_error=_first_error(detected_patterns, segments),
        line_processing=_optional_line_processing(metadata.get("line_processing")),
        schema_version=schema_version,
        state=state,
        workflow=workflow,
        duration_s=duration_s,
        reconnect_timeout_s=reconnect_timeout_s,
        ended_at=ended_at,
        end_reason=end_reason,
        error=error,
        truncation=_optional_object(metadata.get("truncation"), "truncation") if native else None,
    )


def _backend_segment_json(
    snapshot: BackendSnapshot,
    *,
    started_at: str,
) -> dict[str, object]:
    segment_id = snapshot.segment.segment_id if snapshot.segment is not None else 0
    return {
        "segment_id": segment_id,
        "started_at": started_at,
        "ended_at": None,
        "end_reason": None,
        "backend": {
            "mode": snapshot.info.mode,
            "port": snapshot.info.port,
            "device": snapshot.info.device,
            "firmware": snapshot.info.firmware,
            "backend_capabilities": sorted(snapshot.info.capabilities),
            "capabilities": sorted(snapshot.capabilities),
            "capability_policy": _capability_policy_json(snapshot.capability_policy),
        },
        "timestamp": (
            _timestamp_json(snapshot.segment.timestamp) if snapshot.segment is not None else None
        ),
        "first_timestamp_us": None,
        "last_timestamp_us": None,
    }


def _capability_policy_json(policy: BackendCapabilityPolicy) -> dict[str, object]:
    return {
        "uart_send": {
            "tx_policy_enabled": policy.uart_send.tx_policy_enabled,
            "source": policy.uart_send.source,
        }
    }


def _integrity_json(integrity: UartIntegrity) -> dict[str, object]:
    return {
        "loss_status": integrity.loss_status,
        "observation_scope": integrity.observation_scope,
        "dropped_bytes": integrity.dropped_bytes,
    }


def _line_processing_json(line_processing: LineProcessing) -> dict[str, object]:
    return {
        "status": line_processing.status,
        "max_line_bytes": line_processing.max_line_bytes,
        "oversized_line_count": line_processing.oversized_line_count,
    }


def _timestamp_json(timestamp: SegmentTimestamp) -> dict[str, object]:
    return {
        "source": timestamp.source,
        "clock": timestamp.clock,
        "unit": timestamp.unit,
        "origin": timestamp.origin,
        "source_origin_us": timestamp.source_origin_us,
        "observation_point": timestamp.observation_point,
        "event_granularity": timestamp.event_granularity,
    }


def _required_str(metadata: dict[str, object], key: str) -> str:
    value = metadata.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"session metadata '{key}' must be a non-empty string")
    return value


def _optional_str(metadata: dict[str, object], key: str) -> str | None:
    value = metadata.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise ValueError(f"session metadata '{key}' must be null or a non-empty string")
    return value


def _optional_object(value: object, field: str) -> dict[str, object] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError(f"session metadata '{field}' must be a JSON object")
    return cast(dict[str, object], value)


def _optional_backend_mode(value: object) -> BackendMode | None:
    if value is None:
        return None
    if value not in {"basic", "enhanced"}:
        raise ValueError("session metadata 'backend_mode' must be basic or enhanced")
    return value


def _native_state(value: object) -> SessionState:
    if value not in {"active", "completed", "failed", "abandoned"}:
        raise ValueError("native session state is invalid")
    return value


def _native_workflow(value: object) -> SessionWorkflow:
    if value not in {"capture", "boot_test", "wait_pattern"}:
        raise ValueError("native session workflow is invalid")
    return value


def _validate_native_lifecycle_metadata(
    *,
    state: SessionState | None,
    ended_at: str | None,
    end_reason: str | None,
    error: dict[str, object] | None,
) -> None:
    if state == "active":
        if ended_at is not None or end_reason is not None or error is not None:
            raise ValueError("active session terminal fields must be null")
        return
    if ended_at is None or end_reason is None:
        raise ValueError("terminal session must contain ended_at and end_reason")
    if state == "failed":
        if error is None:
            raise ValueError("failed session must contain an error")
    elif error is not None:
        raise ValueError("completed or abandoned session error must be null")


def _optional_positive_number(value: object) -> float | None:
    if value is None:
        return None
    return _require_positive_number(value, "numeric lifecycle value")


def _optional_string_tuple(metadata: dict[str, object], key: str) -> tuple[str, ...]:
    value = metadata.get(key)
    if value is None:
        return ()
    if not isinstance(value, list) or any(not isinstance(item, str) or not item for item in value):
        raise ValueError(f"session metadata '{key}' must be an array of strings")
    return tuple(cast(list[str], value))


def _optional_capability_policy(value: object) -> BackendCapabilityPolicy | None:
    policy = _optional_object(value, "capability_policy")
    if policy is None:
        return None
    uart_send = _optional_object(policy.get("uart_send"), "capability_policy.uart_send")
    if uart_send is None:
        raise ValueError("session metadata capability policy must contain uart_send")
    enabled = uart_send.get("tx_policy_enabled")
    source = uart_send.get("source")
    if not isinstance(enabled, bool):
        raise ValueError("session metadata tx_policy_enabled must be a boolean")
    if source != "hardware.uart.tx_enabled":
        raise ValueError("session metadata UART-send policy source is invalid")
    return BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=enabled))


def _optional_integrity(value: object) -> UartIntegrity | None:
    integrity = _optional_object(value, "integrity")
    if integrity is None:
        return None
    loss_status = integrity.get("loss_status")
    if loss_status not in {"none_reported", "loss_reported", "not_observable"}:
        raise ValueError("session metadata integrity loss_status is invalid")
    observation_scope = integrity.get("observation_scope")
    if observation_scope not in {None, "debug_helper_rx_buffer"}:
        raise ValueError("session metadata integrity observation_scope is invalid")
    dropped_bytes = integrity.get("dropped_bytes")
    if dropped_bytes is not None and (
        isinstance(dropped_bytes, bool) or not isinstance(dropped_bytes, int) or dropped_bytes < 0
    ):
        raise ValueError("session metadata integrity dropped_bytes is invalid")
    return UartIntegrity(
        loss_status=loss_status,
        observation_scope=observation_scope,
        dropped_bytes=dropped_bytes,
    )


def _optional_line_processing(value: object) -> LineProcessing:
    if value is None:
        return LineProcessing()
    line_processing = _optional_object(value, "line_processing")
    if line_processing is None:
        return LineProcessing()
    status = line_processing.get("status")
    max_line_bytes = line_processing.get("max_line_bytes")
    oversized_line_count = line_processing.get("oversized_line_count")
    if status not in {"complete", "limit_exceeded"}:
        raise ValueError("session metadata line-processing status is invalid")
    if max_line_bytes != MAX_UART_LINE_BYTES:
        raise ValueError("session metadata max_line_bytes is invalid")
    if (
        isinstance(oversized_line_count, bool)
        or not isinstance(oversized_line_count, int)
        or oversized_line_count < 0
    ):
        raise ValueError("session metadata oversized_line_count is invalid")
    if (status == "complete") != (oversized_line_count == 0):
        raise ValueError("session metadata line-processing status/count disagree")
    return LineProcessing(
        status=status,
        max_line_bytes=max_line_bytes,
        oversized_line_count=oversized_line_count,
    )


def _segment_contexts(segments: list[object]) -> tuple[SegmentContext, ...]:
    contexts: list[SegmentContext] = []
    for raw_segment in segments:
        if not isinstance(raw_segment, dict):
            raise ValueError("session metadata segments must contain JSON objects")
        segment = cast(dict[str, object], raw_segment)
        segment_id = segment.get("segment_id")
        if isinstance(segment_id, bool) or not isinstance(segment_id, int) or segment_id < 0:
            raise ValueError("session metadata segment_id is invalid")
        timestamp = _optional_object(segment.get("timestamp"), "segments.timestamp")
        if timestamp is None:
            continue
        source = timestamp.get("source")
        clock = timestamp.get("clock")
        unit = timestamp.get("unit")
        origin = timestamp.get("origin")
        source_origin_us = timestamp.get("source_origin_us")
        observation_point = timestamp.get("observation_point")
        event_granularity = timestamp.get("event_granularity")
        if source not in {"host", "device"} or clock not in {
            "monotonic",
            "rp2040_timer",
        }:
            raise ValueError("session metadata timestamp source or clock is invalid")
        if unit != "us" or origin != "segment_start":
            raise ValueError("session metadata timestamp unit or origin is invalid")
        if (
            isinstance(source_origin_us, bool)
            or not isinstance(source_origin_us, int)
            or source_origin_us < 0
        ):
            raise ValueError("session metadata timestamp source_origin_us is invalid")
        if not isinstance(observation_point, str) or not observation_point:
            raise ValueError("session metadata timestamp observation_point is invalid")
        if not isinstance(event_granularity, str) or not event_granularity:
            raise ValueError("session metadata timestamp event_granularity is invalid")
        contexts.append(
            SegmentContext(
                segment_id=segment_id,
                timestamp=SegmentTimestamp(
                    source=source,
                    clock=clock,
                    unit="us",
                    origin="segment_start",
                    source_origin_us=source_origin_us,
                    observation_point=observation_point,
                    event_granularity=event_granularity,
                ),
            )
        )
    return tuple(contexts)


def _required_bool(metadata: dict[str, object], key: str) -> bool:
    value = metadata.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"session metadata '{key}' must be a boolean")
    return value



def _bounded_error(code: str, detail: str) -> dict[str, object]:
    if not isinstance(code, str) or not code:
        raise ValueError("session error code must be a non-empty string")
    if not isinstance(detail, str):
        raise TypeError("session error detail must be a string")
    cleaned = "".join(
        " "
        if character in {"\r", "\n", "\t"}
        else "\ufffd"
        if unicodedata.category(character) == "Cc"
        else character
        for character in detail
    )
    if not cleaned:
        cleaned = code.replace("_", " ")
    encoded = cleaned.encode("utf-8")
    truncated = len(encoded) > 1024
    if truncated:
        prefix = encoded[:1024]
        while True:
            try:
                cleaned = prefix.decode("utf-8")
                break
            except UnicodeDecodeError:
                prefix = prefix[:-1]
    return {
        "code": code,
        "detail": cleaned,
        "detail_truncated": truncated,
    }



def _record_line_processing(
    metadata: dict[str, object],
    *,
    newly_oversized_line_count: int,
) -> None:
    current = _optional_line_processing(metadata.get("line_processing"))
    count = current.oversized_line_count + newly_oversized_line_count
    metadata["line_processing"] = _line_processing_json(
        LineProcessing(
            status="limit_exceeded" if count else "complete",
            oversized_line_count=count,
        )
    )


def _record_metadata_segment_timestamp(
    metadata: dict[str, object],
    *,
    segment_id: int,
    timestamp_us: int,
) -> None:
    segment = _metadata_segment(metadata, segment_id)

    first_key = (
        "first_timestamp_us" if "first_timestamp_us" in segment else "first_device_timestamp_us"
    )
    last_key = "last_timestamp_us" if "last_timestamp_us" in segment else "last_device_timestamp_us"
    if segment[first_key] is None:
        segment[first_key] = timestamp_us
    segment[last_key] = timestamp_us


def _record_integrity_loss(
    metadata: dict[str, object],
    *,
    dropped_bytes: int,
    cumulative: bool,
) -> None:
    integrity = metadata.get("integrity")
    if not isinstance(integrity, dict):
        return
    typed_integrity = cast(dict[str, object], integrity)
    previous = typed_integrity.get("dropped_bytes")
    if cumulative:
        updated = (
            max(previous, dropped_bytes)
            if isinstance(previous, int) and not isinstance(previous, bool)
            else dropped_bytes
        )
    elif isinstance(previous, int) and not isinstance(previous, bool):
        updated = previous + dropped_bytes
    else:
        updated = None
    typed_integrity.update(
        {
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": updated,
        }
    )


def _metadata_segment(metadata: dict[str, object], segment_id: int) -> dict[str, object]:
    segments = metadata.get("segments")
    if not isinstance(segments, list):
        raise ValueError("session metadata segments must be a JSON array")

    for segment in segments:
        if not isinstance(segment, dict):
            raise ValueError("session metadata segments must contain JSON objects")
        typed_segment = cast(dict[str, object], segment)
        if typed_segment.get("segment_id") == segment_id:
            return typed_segment

    raise ValueError(f"session metadata has no segment {segment_id}")


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _random_suffix() -> str:
    return uuid4().hex[:8]


def _format_utc_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _format_session_id_timestamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
