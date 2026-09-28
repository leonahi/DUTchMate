"""CLI formatting for bounded Monitor results."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def format_monitor_result(payload: Mapping[str, object]) -> str:
    """Format one terminal Monitor result with its durable evidence ranges."""

    outcome = _display(payload.get("outcome"))
    operation_id = _display(payload.get("operation_id"))
    ranges = _format_ranges(payload.get("evidence_ranges"))
    lines = [f"Monitor {outcome}", f"Operation: {operation_id}", f"Evidence: {ranges}"]
    matched = payload.get("matched_condition")
    if isinstance(matched, Mapping):
        condition = matched.get("condition")
        if isinstance(condition, Mapping):
            lines.append(f"Matched: {_display(condition.get('pattern'))}")
        excerpt = matched.get("excerpt")
        if isinstance(excerpt, Mapping):
            lines.append(f"Excerpt: {_display(excerpt.get('text'))}")
    return "\n".join(lines)


def _format_ranges(value: object) -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return "none"
    rendered: list[str] = []
    for item in value:
        if not isinstance(item, Mapping):
            continue
        rendered.append(
            f"{_display(item.get('session_id'))}:"
            f"{_display(item.get('start_evidence_seq'))}.."
            f"{_display(item.get('end_evidence_seq_exclusive'))}"
        )
    return ", ".join(rendered) or "none"


def _display(value: object) -> str:
    return "none" if value is None or value == "" else str(value)
