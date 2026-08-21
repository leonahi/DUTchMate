"""CLI formatting for finite literal wait-pattern outcomes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast


def format_wait_pattern(payload: Mapping[str, object]) -> str:
    """Format a matched or ordinary unmatched wait outcome."""

    session_id = _display(payload.get("session_id"))
    if payload.get("matched") is not True:
        return f"No match\nSession: {session_id}"

    excerpt = _mapping(payload.get("match_excerpt"))
    excerpt_text = _display(excerpt.get("text") if excerpt is not None else None)
    return "\n".join(
        [
            f"Matched: {_display(payload.get('pattern'))}",
            f"Session: {session_id}",
            (
                f"Location: segment {_display(payload.get('segment_id'))}, "
                f"channel {_display(payload.get('channel'))}, "
                f"timestamp {_display(payload.get('timestamp_us'))} us"
            ),
            (
                f"Match bytes: [{_display(payload.get('match_start_byte'))}, "
                f"{_display(payload.get('match_end_byte'))})"
            ),
            f"Excerpt: {excerpt_text}",
        ]
    )


def _mapping(value: object) -> Mapping[str, object] | None:
    return cast(Mapping[str, object], value) if isinstance(value, Mapping) else None


def _display(value: object) -> str:
    return "none" if value is None or value == "" else str(value)
