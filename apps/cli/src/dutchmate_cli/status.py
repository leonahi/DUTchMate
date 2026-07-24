"""Terminal formatting for Device Core Service status."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

CONTROL_CHANNEL_ORDER: Final = ("CTRL0", "CTRL1", "CTRL2", "CTRL3")


def format_status(payload: Mapping[str, object]) -> str:
    """Format the service status payload for human-readable CLI output."""

    lines = [
        "Service: running",
        f"Device: {_format_device(payload)}",
        f"Port: {_display(payload.get('port'))}",
        f"Active session: {_display(payload.get('active_session_id'))}",
        f"Capabilities: {_format_capabilities(payload.get('capabilities'))}",
        "Control channels:",
    ]
    lines.extend(_format_control_channels(payload.get("control_channels")))
    return "\n".join(lines)


def _format_device(payload: Mapping[str, object]) -> str:
    if payload.get("connected") is not True:
        return "disconnected"

    device = _display(payload.get("device"))
    firmware = _display(payload.get("firmware"))
    return f"connected ({device}, firmware {firmware})"


def _format_capabilities(value: object) -> str:
    if not isinstance(value, (list, tuple)):
        return "none"

    capabilities = [item for item in value if isinstance(item, str) and item]
    if not capabilities:
        return "none"
    return ", ".join(capabilities)


def _format_control_channels(value: object) -> list[str]:
    channels = _as_mapping(value)
    if channels is None:
        return ["  none"]

    lines: list[str] = []
    for channel in CONTROL_CHANNEL_ORDER:
        state = _as_mapping(channels.get(channel))
        if state is None:
            lines.append(f"  {channel}: unknown")
            continue
        lines.append(_format_control_channel(channel, state))
    return lines


def _format_control_channel(channel: str, state: Mapping[str, object]) -> str:
    state_name = _display(state.get("state"))
    if state_name == "configured":
        parts = [
            f"  {channel}: {_display(state.get('role'))} -> {_display(state.get('dut_signal'))}",
            f"mode={_display(state.get('mode'))}",
            f"active={_display(state.get('active_level'))}",
        ]
        idle_level = state.get("idle_level")
        if idle_level is not None:
            parts.append(f"idle={_display(idle_level)}")
        parts.append(f"source={_display(state.get('source'))}")
        return f"{parts[0]} ({', '.join(parts[1:])})"

    if state_name == "rejected":
        rejection = _as_mapping(state.get("last_rejected"))
        detail = _display(rejection.get("detail") if rejection is not None else None)
        role = _display(state.get("role"))
        return f"  {channel}: rejected role={role} detail={detail}"

    return f"  {channel}: {state_name}"


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return None


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)
