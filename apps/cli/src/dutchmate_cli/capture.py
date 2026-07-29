"""Terminal formatting for UART capture commands."""

from __future__ import annotations

from collections.abc import Mapping


def format_capture_result(payload: Mapping[str, object]) -> str:
    """Format a completed capture session summary."""

    session_id = _display(payload.get("session_id"))
    segments = _display(payload.get("segments"))
    flags = ", ".join(
        (
            f"segments={segments}",
            f"overflow={_flag(payload.get('overflow'))}",
            f"interrupted={_flag(payload.get('interrupted'))}",
            f"resumed={_flag(payload.get('resumed'))}",
            f"truncated={_flag(payload.get('truncated'))}",
        )
    )
    return f"Capture complete: {session_id} ({flags})"


def _display(value: object) -> str:
    if value is None or value == "":
        return "unknown"
    return str(value)


def _flag(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
