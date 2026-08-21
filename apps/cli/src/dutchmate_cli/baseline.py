"""Terminal formatting for project baseline mutations."""

from collections.abc import Mapping
from typing import cast


def format_baseline_mutation(
    payload: Mapping[str, object],
    *,
    action: str,
) -> str:
    """Format one mark or clear result without inferring evidence quality."""

    changed = payload.get("changed") is True
    lines = [
        f"Baseline {action}: {'changed' if changed else 'unchanged'}",
        f"Session: {_display(payload.get('session_id'))}",
        f"Previous session: {_display(payload.get('previous_session_id'))}",
        f"Marked at: {_display(payload.get('marked_at'))}",
    ]
    integrity = _as_mapping(payload.get("integrity"))
    if integrity is not None:
        lines.append(f"Integrity: {_display(integrity.get('loss_status'))}")
        if integrity.get("loss_status") == "not_observable":
            lines.append("Warning: UART loss was not observable for this session.")
    return "\n".join(lines)


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return None


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)
