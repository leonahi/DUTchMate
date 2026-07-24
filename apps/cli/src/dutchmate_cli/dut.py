"""Terminal formatting for DUT action commands."""

from __future__ import annotations

from collections.abc import Mapping


def format_reset_result(payload: Mapping[str, object]) -> str:
    """Format a successful DUT reset response."""

    return f"Reset command accepted (timestamp_us={_display(payload.get('timestamp_us'))})"


def format_boot_mode_result(mode: str, payload: Mapping[str, object]) -> str:
    """Format a successful DUT boot-mode response."""

    return f"Boot mode set to {mode} (timestamp_us={_display(payload.get('timestamp_us'))})"


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)
