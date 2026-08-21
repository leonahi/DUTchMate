"""Service response serialization helpers."""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Final, Literal, cast

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import DeviceCoreStatus
from dutchmate_core.session_store.models import (
    LegacySessionDetail,
    LegacySessionListItem,
    NativeSessionListItem,
    RecentLogs,
    SessionDetail,
    SessionListItem,
    SessionListPage,
    WaitPatternResult,
)
from dutchmate_core.session_store.store import SessionSummary
from dutchmate_core.validation import (
    MAX_CAPTURE_DURATION_S,
    GpioControlChannel,
    GpioControlMode,
    GpioLevel,
    validate_capture_duration,
    validate_gpio_configuration,
    validate_gpio_identifier,
    validate_wait_pattern,
    validate_wait_timeout,
)
from dutchmate_core.workflows.device_actions import DeviceActionResult
from dutchmate_core.workflows.uart_send import UartSendResult


def status_payload(status: DeviceCoreStatus) -> dict[str, object]:
    """Serialize a Device Core status snapshot for the HTTP API."""

    return {
        "connected": status.connected,
        "connection_state": status.connection_state,
        "backend_mode": status.backend_mode,
        "port": status.port,
        "firmware": status.firmware,
        "device": status.device,
        "backend_identity": {
            "port": status.port,
            "firmware": status.firmware,
            "device": status.device,
        },
        "backend_capabilities": list(status.backend_capabilities),
        "capabilities": list(status.capabilities),
        "capability_policy": (
            asdict(status.capability_policy) if status.capability_policy is not None else None
        ),
        "timestamp_provenance": (
            asdict(status.timestamp_provenance) if status.timestamp_provenance is not None else None
        ),
        "integrity": asdict(status.integrity) if status.integrity is not None else None,
        "active_session_id": status.active_session_id,
        "active_workflow": status.active_workflow,
        "reconnect_remaining_s": status.reconnect_remaining_s,
        "retention": asdict(status.retention),
        "control_channels": {
            channel: asdict(channel_status)
            for channel, channel_status in status.control_channels.items()
        },
    }


class GpioModeRequest(BaseModel):
    """Request body for configuring a control channel mode."""

    channel: GpioControlChannel
    role: str
    dut_signal: str
    mode: GpioControlMode
    active_level: GpioLevel
    idle_level: GpioLevel | None = None

    @field_validator("role", "dut_signal")
    @classmethod
    def validate_required_identifier(cls, value: str, info: ValidationInfo) -> str:
        return validate_gpio_identifier(value, field=info.field_name or "identifier")

    @model_validator(mode="after")
    def validate_electrical_configuration(self) -> GpioModeRequest:
        validate_gpio_configuration(
            channel=self.channel,
            role=self.role,
            dut_signal=self.dut_signal,
            mode=self.mode,
            active_level=self.active_level,
            idle_level=self.idle_level,
        )
        return self


def gpio_mode_payload(state: GpioControlChannelState) -> dict[str, object]:
    """Serialize a configured GPIO mode response."""

    return {
        "ok": True,
        "channel": state.channel,
        "role": state.role,
        "dut_signal": state.dut_signal,
        "mode": state.mode,
        "active_level": state.active_level,
        "idle_level": state.idle_level,
        "source": state.source,
        "timestamp_us": state.device_timestamp_us,
    }


class ResetRequest(BaseModel):
    """Request body for pulsing the configured reset role."""

    pulse_ms: int = Field(default=100, ge=1, le=10000)


class BootModeRequest(BaseModel):
    """Request body for setting the configured boot/control role."""

    mode: Literal["normal", "bootloader"]


class _TimedCaptureRequest(BaseModel):
    duration_s: float = Field(gt=0, le=MAX_CAPTURE_DURATION_S, allow_inf_nan=False)

    @field_validator("duration_s", mode="before")
    @classmethod
    def validate_duration(cls, value: object) -> float:
        return validate_capture_duration(value)


class CaptureRequest(_TimedCaptureRequest):
    """Request body for a finite UART capture."""


class BootTestRequest(_TimedCaptureRequest):
    """Request body for a reset-triggered boot capture."""


class WaitPatternRequest(BaseModel):
    """Request body for a finite new-evidence-only literal wait."""

    pattern: str
    timeout_s: float

    @field_validator("pattern", mode="before")
    @classmethod
    def validate_pattern(cls, value: object) -> str:
        return validate_wait_pattern(value)

    @field_validator("timeout_s", mode="before")
    @classmethod
    def validate_timeout(cls, value: object) -> float:
        return validate_wait_timeout(value)


class UartSendRequest(BaseModel):
    """Public text-only UART-send request."""

    cmd: str
    append_newline: bool = True
    force: bool = False

    @field_validator("append_newline", "force", mode="before")
    @classmethod
    def validate_boolean(cls, value: object, info: ValidationInfo) -> bool:
        if not isinstance(value, bool):
            raise ValueError(f"{info.field_name} must be a boolean")
        return value


def capture_summary_payload(summary: SessionSummary) -> dict[str, object]:
    """Serialize a completed capture session summary."""

    return {
        "ok": True,
        "session_id": summary.session_id,
        "schema_version": summary.schema_version,
        "state": summary.state,
        "workflow": summary.workflow,
        "duration_s": summary.duration_s,
        "reconnect_timeout_s": summary.reconnect_timeout_s,
        "ended_at": summary.ended_at,
        "end_reason": summary.end_reason,
        "error": summary.error,
        "truncation": summary.truncation,
        "backend_mode": summary.backend_mode,
        "backend_identity": {
            "port": summary.port,
            "firmware": summary.firmware,
            "device": summary.device,
        },
        "backend_capabilities": list(summary.backend_capabilities),
        "capabilities": list(summary.capabilities),
        "capability_policy": (
            asdict(summary.capability_policy) if summary.capability_policy is not None else None
        ),
        "timestamp_provenance": [asdict(segment) for segment in summary.segment_contexts],
        "integrity": asdict(summary.integrity) if summary.integrity is not None else None,
        "first_error": (asdict(summary.first_error) if summary.first_error is not None else None),
        "line_processing": asdict(summary.line_processing),
        "truncated": summary.truncated,
        "interrupted": summary.interrupted,
        "resumed": summary.resumed,
        "overflow": summary.overflow,
        "segments": summary.segment_count,
    }


def wait_pattern_payload(result: WaitPatternResult) -> dict[str, object]:
    """Serialize one successful matched or unmatched wait-pattern outcome."""

    payload = capture_summary_payload(result.summary)
    match = result.match
    payload.update(
        {
            "matched": result.matched,
            "pattern": result.pattern,
            "match_mode": result.summary.match_mode,
            "case_sensitive": result.summary.case_sensitive,
            "timeout_s": result.summary.timeout_s,
            "match_excerpt": (
                asdict(match.match_excerpt) if match is not None else None
            ),
            "detected_pattern_index": (
                match.detected_pattern_index if match is not None else None
            ),
            "channel": match.channel if match is not None else None,
            "segment_id": match.segment_id if match is not None else None,
            "timestamp_us": match.timestamp_us if match is not None else None,
            "ingestion_index": match.ingestion_index if match is not None else None,
            "line_index_in_event": match.line_index_in_event if match is not None else None,
            "match_start_byte": match.match_start_byte if match is not None else None,
            "match_end_byte": match.match_end_byte if match is not None else None,
            "total_line_bytes": match.total_line_bytes if match is not None else None,
            "line_start_ingestion_index": (
                match.line_start_ingestion_index if match is not None else None
            ),
            "line_start_event_offset": (
                match.line_start_event_offset if match is not None else None
            ),
            "line_end_ingestion_index": (
                match.line_end_ingestion_index if match is not None else None
            ),
            "line_end_event_offset": (
                match.line_end_event_offset if match is not None else None
            ),
        }
    )
    return payload


def uart_send_payload(result: UartSendResult) -> dict[str, object]:
    """Serialize one successful complete UART send."""

    return {
        "ok": True,
        "performed_at": result.performed_at,
        "device_timestamp_us": result.device_timestamp_us,
        "attempt_id": result.attempt_id,
        "perturbation_logged": result.perturbation_logged,
    }


def session_list_payload(page: SessionListPage) -> dict[str, object]:
    """Serialize one bounded stable session page."""

    return {
        "items": [_session_list_item_payload(item) for item in page.items],
        "next_cursor": page.next_cursor,
    }


def session_detail_payload(detail: SessionDetail) -> dict[str, object]:
    """Serialize bounded native or legacy session detail."""

    if isinstance(detail, LegacySessionDetail):
        payload = _session_list_item_payload(detail.summary)
        payload["artifact_manifest"] = [asdict(artifact) for artifact in detail.artifacts]
        return payload

    payload = _session_list_item_payload(detail.summary)
    payload.update(
        {
            "command": detail.command,
            "duration_s": detail.duration_s,
            "reconnect_timeout_s": detail.reconnect_timeout_s,
            "error": detail.error,
            "backend_identity": detail.backend_identity,
            "backend_capabilities": list(detail.backend_capabilities),
            "capabilities": list(detail.capabilities),
            "capability_policy": asdict(detail.capability_policy),
            "commanded_boot_mode": detail.commanded_boot_mode,
            "storage": detail.storage,
            "segments": list(detail.segments),
            "first_error": asdict(detail.first_error) if detail.first_error is not None else None,
            "pattern_counts": {
                count.type: count.count for count in detail.pattern_counts
            },
            "hardware_event_counts": {
                count.type: count.count for count in detail.hardware_event_counts
            },
            "unresolved_uart_tx_attempts": detail.unresolved_uart_tx_attempts,
            "artifact_manifest": [asdict(artifact) for artifact in detail.artifacts],
            "pattern": detail.wait_pattern,
            "match_mode": detail.match_mode,
            "case_sensitive": detail.case_sensitive,
            "timeout_s": detail.timeout_s,
            "matched": detail.matched,
            "detected_pattern_index": detail.detected_pattern_index,
        }
    )
    return payload


MAX_RECENT_LOG_RESPONSE_BYTES: Final = 262144


def recent_logs_payload(logs: RecentLogs) -> dict[str, object]:
    """Serialize recent logs and remove oldest whole records to fit the body cap."""

    payload: dict[str, object] = {
        "session_selection": logs.session_selection,
        "session_id": logs.session_id,
        "schema_version": logs.schema_version,
        "active": logs.active,
        "snapshot_event_count": logs.snapshot_event_count,
        "complete_lines": [asdict(line) for line in logs.complete_lines],
        "partial_lines": [asdict(line) for line in logs.partial_lines],
        "oversized_lines": [asdict(line) for line in logs.oversized_lines],
        "integrity": asdict(logs.integrity),
        "line_processing": asdict(logs.line_processing),
        "reconnect_timeout_s": logs.reconnect_timeout_s,
        "interrupted": logs.interrupted,
        "resumed": logs.resumed,
        "storage": logs.storage,
        "truncated": logs.truncated,
        "truncation": logs.truncation,
        "timestamp_provenance": list(logs.timestamp_provenance),
        "response_truncated": False,
        "omitted_complete_lines": logs.omitted_complete_lines,
        "omitted_partial_lines": logs.omitted_partial_lines,
        "omitted_oversized_lines": logs.omitted_oversized_lines,
    }
    while _compact_json_size(payload) > MAX_RECENT_LOG_RESPONSE_BYTES:
        category = _oldest_log_category(payload)
        if category is None:
            raise ValueError("recent-log metadata exceeds the response byte limit")
        records = cast(list[object], payload[category])
        records.pop(0)
        omission_key = {
            "complete_lines": "omitted_complete_lines",
            "partial_lines": "omitted_partial_lines",
            "oversized_lines": "omitted_oversized_lines",
        }[category]
        payload[omission_key] = cast(int, payload[omission_key]) + 1
    payload["response_truncated"] = any(
        cast(int, payload[key]) > 0
        for key in (
            "omitted_complete_lines",
            "omitted_partial_lines",
            "omitted_oversized_lines",
        )
    )
    return payload


def _oldest_log_category(payload: dict[str, object]) -> str | None:
    candidates: list[tuple[tuple[int, int], str]] = []
    for category in ("complete_lines", "partial_lines", "oversized_lines"):
        records = cast(list[object], payload[category])
        if not records:
            continue
        record = cast(dict[str, object], records[0])
        candidates.append(
            (
                (
                    cast(int, record["ingestion_index"]),
                    cast(int, record["line_index_in_event"]),
                ),
                category,
            )
        )
    return min(candidates)[1] if candidates else None


def _compact_json_size(payload: dict[str, object]) -> int:
    return len(
        json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            separators=(",", ":"),
        ).encode("utf-8")
    )


def _session_list_item_payload(item: SessionListItem) -> dict[str, object]:
    if isinstance(item, LegacySessionListItem):
        return asdict(item)
    return _native_session_list_item_payload(item)


def _native_session_list_item_payload(item: NativeSessionListItem) -> dict[str, object]:
    return {
        "session_id": item.session_id,
        "schema_version": item.schema_version,
        "compatibility": item.compatibility,
        "started_at": item.started_at,
        "state": item.state,
        "workflow": item.workflow,
        "ended_at": item.ended_at,
        "end_reason": item.end_reason,
        "backend_mode": item.backend_mode,
        "baseline": item.baseline,
        "truncated": item.truncated,
        "truncation": item.truncation,
        "interrupted": item.interrupted,
        "resumed": item.resumed,
        "segment_count": item.segment_count,
        "integrity": asdict(item.integrity),
        "line_processing": asdict(item.line_processing),
        "first_error": asdict(item.first_error) if item.first_error is not None else None,
    }


def device_action_payload(result: DeviceActionResult) -> dict[str, object]:
    """Serialize a successful hardware action response."""

    return {
        "ok": True,
        "timestamp_us": result.timestamp_us,
    }
