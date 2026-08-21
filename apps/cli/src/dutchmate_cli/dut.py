"""Terminal formatting for DUT action commands."""

from __future__ import annotations

from collections.abc import Mapping


def format_reset_result(payload: Mapping[str, object]) -> str:
    """Format a successful DUT reset response."""

    return (
        "Reset command accepted "
        f"(pulse_ms={_display(payload.get('pulse_ms'))}, "
        f"performed_at={_display(payload.get('performed_at'))}, "
        f"device_timestamp_us={_display(payload.get('device_timestamp_us'))})"
    )


def format_boot_mode_result(payload: Mapping[str, object]) -> str:
    """Format a successful DUT boot-mode response."""

    return (
        f"Boot mode set to {_display(payload.get('mode'))} "
        f"(performed_at={_display(payload.get('performed_at'))}, "
        f"device_timestamp_us={_display(payload.get('device_timestamp_us'))})"
    )


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)
