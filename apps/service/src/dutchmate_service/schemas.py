"""Service response serialization helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field, ValidationInfo, field_validator, model_validator

from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import DeviceCoreStatus
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
        "port": status.port,
        "firmware": status.firmware,
        "device": status.device,
        "capabilities": list(status.capabilities),
        "active_session_id": status.active_session_id,
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
        "truncated": summary.truncated,
        "interrupted": summary.interrupted,
        "resumed": summary.resumed,
        "overflow": summary.overflow,
        "segments": summary.segment_count,
    }


def device_action_payload(result: DeviceActionResult) -> dict[str, object]:
    """Serialize a successful hardware action response."""

    return {
        "ok": True,
        "timestamp_us": result.timestamp_us,
    }
