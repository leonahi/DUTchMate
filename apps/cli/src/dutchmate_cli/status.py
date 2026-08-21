"""Terminal formatting for Device Core Service status."""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Final, cast

CONTROL_CHANNEL_ORDER: Final = ("CTRL0", "CTRL1", "CTRL2", "CTRL3")


def format_status(payload: Mapping[str, object]) -> str:
    """Format the service status payload for human-readable CLI output."""

    lines = [
        "Service: running",
        f"Backend: {_display(payload.get('backend_mode'))}",
        f"Workflow: {_format_workflow(payload.get('active_workflow'))}",
        f"Session: {_display(payload.get('active_session_id'))}",
        f"Connection: {_format_connection(payload)}",
        f"Device: {_format_device(payload)}",
        f"Port: {_display(payload.get('port'))}",
        f"Backend capabilities: {_format_capabilities(payload.get('backend_capabilities'))}",
        f"Capabilities: {_format_capabilities(payload.get('capabilities'))}",
        f"UART TX policy: {_format_tx_policy(payload.get('capability_policy'))}",
        f"Timestamp provenance: {_format_timestamp(payload.get('timestamp_provenance'))}",
        f"UART loss: {_format_integrity(payload.get('integrity'))}",
        f"Retention: {_format_retention(payload.get('retention'))}",
        "Control channels:",
    ]
    lines.extend(_format_control_channels(payload.get("control_channels")))
    return "\n".join(lines)


def _format_workflow(value: object) -> str:
    if not isinstance(value, str) or not value:
        return "none"
    return f"{value.replace('_', '-')} (active)"


def _format_connection(payload: Mapping[str, object]) -> str:
    value = payload.get("connection_state")
    state = (
        value
        if isinstance(value, str) and value in {"connected", "disconnected", "reconnecting"}
        else None
    )
    if state is None:
        state = "connected" if payload.get("connected") is True else "disconnected"
    if state != "reconnecting":
        return state

    remaining = payload.get("reconnect_remaining_s")
    if (
        isinstance(remaining, int | float)
        and not isinstance(remaining, bool)
        and math.isfinite(remaining)
        and remaining >= 0
    ):
        return f"reconnecting ({remaining:.1f}s remaining)"
    return "reconnecting"


def _format_device(payload: Mapping[str, object]) -> str:
    if payload.get("connected") is not True:
        return "disconnected"

    if payload.get("backend_mode") == "basic":
        return "connected (generic UART adapter)"

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


def _format_tx_policy(value: object) -> str:
    policy = _as_mapping(value)
    uart_send = _as_mapping(policy.get("uart_send")) if policy is not None else None
    if uart_send is None:
        return "unknown"
    enabled = uart_send.get("tx_policy_enabled")
    state = "enabled" if enabled is True else "disabled" if enabled is False else "unknown"
    return f"{state} ({_display(uart_send.get('source'))})"


def _format_timestamp(value: object) -> str:
    context = _as_mapping(value)
    if context is None:
        return "none"
    timestamp = _as_mapping(context.get("timestamp"))
    if timestamp is None:
        return "none"
    return (
        f"segment {_display(context.get('segment_id'))}: "
        f"{_display(timestamp.get('source'))}/{_display(timestamp.get('clock'))}, "
        f"{_display(timestamp.get('observation_point'))}/"
        f"{_display(timestamp.get('event_granularity'))}"
    )


def _format_integrity(value: object) -> str:
    integrity = _as_mapping(value)
    if integrity is None:
        return "unknown"
    loss_status = _display(integrity.get("loss_status"))
    scope = integrity.get("observation_scope")
    dropped = integrity.get("dropped_bytes")
    if scope is None and dropped is None:
        return loss_status
    return f"{loss_status} (scope={_display(scope)}, dropped_bytes={_display(dropped)})"


def _format_retention(value: object) -> str:
    retention = _as_mapping(value)
    if retention is None:
        return "unknown"
    if retention.get("enabled") is not True:
        return "disabled"
    diagnostic = retention.get("diagnostic")
    count = _display(retention.get("session_count"))
    maximum = _display(retention.get("max_count"))
    if isinstance(diagnostic, str) and diagnostic:
        return f"{diagnostic} ({count}/{maximum} sessions)"
    return f"healthy ({count}/{maximum} sessions)"


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
