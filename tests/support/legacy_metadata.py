"""Frozen pre-v2 fixture construction from Stage 7 (9a228fcc).

Test-only: never imported by a distribution. Production SessionStore has no
legacy creation/append API. These builders preserve compatibility test inputs;
the inherited production queries are the read-only boundary under test.
"""

from typing import cast

import dutchmate_core.session_store.metadata as _shared
from dutchmate_core.backends.contracts import (
    BackendSnapshot,
)
from dutchmate_core.session_store.metadata import (
    MAX_SESSION_SEGMENTS,
    METADATA_MAX_BYTES,
    _backend_segment_json,
    _capability_policy_json,
    _contiguous_native_segments,
    _integrity_json,
    _line_processing_json,
    _optional_object,
    _require_positive_number,
)
from dutchmate_core.session_store.models import (
    CommandedBootMode,
    LineProcessing,
    SessionWorkflow,
)
from dutchmate_core.validation import (
    validate_wait_pattern,
    validate_wait_timeout,
)


def _validate_native_lifecycle_inputs(
    *,
    workflow: SessionWorkflow | None,
    duration_s: float | None,
    reconnect_timeout_s: float | None,
    commanded_boot_mode: CommandedBootMode | None,
    backend_snapshot: BackendSnapshot | None,
    wait_pattern: str | None,
    timeout_s: float | None,
) -> None:
    if commanded_boot_mode not in {None, "normal", "bootloader"}:
        raise ValueError("commanded_boot_mode must be normal, bootloader, or null")
    if workflow is None:
        if any(
            value is not None
            for value in (
                duration_s,
                reconnect_timeout_s,
                commanded_boot_mode,
                wait_pattern,
                timeout_s,
            )
        ):
            raise ValueError("native lifecycle values require a workflow")
        return
    if backend_snapshot is None:
        raise ValueError("native sessions require a backend snapshot")
    if workflow in {"capture", "boot_test"}:
        _require_positive_number(duration_s, "duration_s")
        if wait_pattern is not None or timeout_s is not None:
            raise ValueError("capture/boot-test sessions cannot contain wait inputs")
    elif duration_s is not None:
        raise ValueError("wait-pattern duration_s must be null")
    else:
        validate_wait_pattern(wait_pattern)
        validate_wait_timeout(timeout_s)
    _require_positive_number(reconnect_timeout_s, "reconnect_timeout_s")


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
    commanded_boot_mode: CommandedBootMode | None,
    wait_pattern: str | None,
    timeout_s: float | None,
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
            "commanded_boot_mode": commanded_boot_mode,
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
        if workflow == "wait_pattern":
            metadata.update(
                {
                    "pattern": wait_pattern,
                    "match_mode": "literal",
                    "case_sensitive": True,
                    "timeout_s": timeout_s,
                    "matched": None,
                    "detected_pattern_index": None,
                }
            )
    return metadata


def _record_backend_disconnect(
    metadata: dict[str, object],
    *,
    segment_id: int,
    ended_at: str,
) -> int:
    if metadata.get("schema_version") != 1 or metadata.get("state") != "active":
        raise ValueError("backend disconnect requires an active native session")
    if isinstance(segment_id, bool) or not isinstance(segment_id, int) or segment_id < 0:
        raise ValueError("backend disconnect segment ID must be a non-negative integer")
    segments = _contiguous_native_segments(metadata)
    current = segments[-1]
    if not isinstance(current, dict) or current.get("segment_id") != segment_id:
        raise ValueError("backend disconnect must close the current segment")
    if current.get("ended_at") is not None or current.get("end_reason") is not None:
        raise ValueError("current session segment is already closed")
    current["ended_at"] = ended_at
    current["end_reason"] = "usb_disconnect"
    metadata["interrupted"] = True
    return len(segments)


def _append_resumed_backend_segment(
    metadata: dict[str, object],
    *,
    snapshot: BackendSnapshot,
    started_at: str,
) -> int:
    if metadata.get("schema_version") != 1 or metadata.get("state") != "active":
        raise ValueError("session resume requires an active native session")
    if snapshot.segment is None:
        raise ValueError("session resume requires timestamp provenance")
    segments = _contiguous_native_segments(metadata)
    if len(segments) >= MAX_SESSION_SEGMENTS:
        raise ValueError("session already contains the maximum 32 segments")
    previous = segments[-1]
    previous_id = len(segments) - 1
    if (
        not isinstance(previous, dict)
        or previous.get("segment_id") != previous_id
        or previous.get("end_reason") != "usb_disconnect"
        or previous.get("ended_at") is None
    ):
        raise ValueError("session resume requires a closed disconnected segment")
    resumed_segment_id = snapshot.segment.segment_id
    if (
        isinstance(resumed_segment_id, bool)
        or not isinstance(resumed_segment_id, int)
        or resumed_segment_id != len(segments)
    ):
        raise ValueError("resumed segment ID must be the next contiguous ID")
    if snapshot.info.mode != metadata.get("backend_mode"):
        raise ValueError("resumed backend mode must match the session")
    identity = _optional_object(metadata.get("backend_identity"), "backend_identity")
    if identity is None or snapshot.info.port != identity.get("port"):
        raise ValueError("resumed backend port must match the session")
    if snapshot.info.mode == "enhanced" and (
        snapshot.info.device != identity.get("device")
        or snapshot.info.firmware != identity.get("firmware")
    ):
        raise ValueError("resumed Enhanced identity must match the session")
    if snapshot.info.mode == "basic" and (
        snapshot.info.device is not None or snapshot.info.firmware is not None
    ):
        raise ValueError("resumed Basic identity must omit device and firmware")
    segments.append(_backend_segment_json(snapshot, started_at=started_at))
    metadata["resumed"] = True
    return resumed_segment_id


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


def __getattr__(name):
    return getattr(_shared, name)
