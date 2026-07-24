"""Service response serialization helpers."""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from dutchmate_core.gpio_config.modes import GpioControlChannelState
from dutchmate_core.runtime import DeviceCoreStatus
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

    channel: Literal["CTRL0", "CTRL1", "CTRL2", "CTRL3"]
    role: str = Field(min_length=1)
    dut_signal: str = Field(min_length=1)
    mode: Literal["open_drain", "push_pull"]
    active_level: Literal["low", "high"]
    idle_level: Literal["low", "high"] | None = None

    @field_validator("role", "dut_signal")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("must be a non-empty string")
        return stripped


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


def device_action_payload(result: DeviceActionResult) -> dict[str, object]:
    """Serialize a successful hardware action response."""

    return {
        "ok": True,
        "timestamp_us": result.timestamp_us,
    }
