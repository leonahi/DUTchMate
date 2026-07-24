"""Terminal formatting for GPIO control commands."""

from __future__ import annotations

from collections.abc import Mapping


def format_gpio_mode_result(payload: Mapping[str, object]) -> str:
    """Format a successful GPIO mode configuration response."""

    channel = _display(payload.get("channel"))
    role = _display(payload.get("role"))
    dut_signal = _display(payload.get("dut_signal"))
    mode = _display(payload.get("mode"))
    active_level = _display(payload.get("active_level"))
    idle_level = payload.get("idle_level")
    source = _display(payload.get("source"))

    details = [
        f"mode={mode}",
        f"active={active_level}",
    ]
    if idle_level is not None:
        details.append(f"idle={_display(idle_level)}")
    details.append(f"source={source}")

    return f"Configured {channel}: {role} -> {dut_signal} ({', '.join(details)})"


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)
