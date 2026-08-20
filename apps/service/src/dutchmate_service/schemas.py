"""Service response serialization helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import DeviceCoreStatus
from dutchmate_core.session_store.models import (
    LegacySessionDetail,
    LegacySessionListItem,
    NativeSessionListItem,
    SessionDetail,
    SessionListItem,
    SessionListPage,
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
)
from dutchmate_core.workflows.device_actions import DeviceActionResult


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
        }
    )
    return payload


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
