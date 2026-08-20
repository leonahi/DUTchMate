"""CLI formatting for bounded recent UART replay."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast


def format_recent_logs(payload: Mapping[str, object]) -> str:
    """Format replayed lines with CLI-only segment/channel separators."""

    lines = [
        f"Session: {_display(payload.get('session_id'))} "
        f"({_display(payload.get('session_selection'))})"
    ]
    records = _merged_records(payload)
    current_stream: tuple[object, object] | None = None
    for category, record in records:
        stream = record.get("segment_id"), record.get("channel")
        if stream != current_stream:
            lines.append(
                f"--- segment {_display(stream[0])}, channel {_display(stream[1])} ---"
            )
            current_stream = stream
        if category == "oversized_lines":
            lines.append(
                "[line omitted: "
                f"{_display(record.get('total_line_bytes'))} bytes exceeds processing limit; "
                f"terminated={_display(record.get('terminated'))}]"
            )
            continue
        text = _display_text(record.get("line_text"))
        marker = " [partial]" if category == "partial_lines" else ""
        lines.append(f"{text}{marker}")

    if not records:
        lines.append("No UART lines in the selected snapshot.")
    lines.extend(_warnings(payload))
    return "\n".join(lines)


def _merged_records(
    payload: Mapping[str, object],
) -> list[tuple[str, Mapping[str, object]]]:
    records: list[tuple[str, Mapping[str, object]]] = []
    for category in ("complete_lines", "partial_lines", "oversized_lines"):
        value = payload.get(category)
        if not isinstance(value, list):
            continue
        for raw_record in value:
            if isinstance(raw_record, Mapping):
                records.append((category, cast(Mapping[str, object], raw_record)))
    records.sort(
        key=lambda item: (
            _sort_int(item[1].get("ingestion_index")),
            _sort_int(item[1].get("line_index_in_event")),
        )
    )
    return records


def _warnings(payload: Mapping[str, object]) -> list[str]:
    warnings: list[str] = []
    integrity = payload.get("integrity")
    if isinstance(integrity, Mapping) and integrity.get("loss_status") != "none_reported":
        warnings.append(
            f"Warning: UART integrity is {_display(integrity.get('loss_status'))}."
        )
    if payload.get("truncated") is True:
        warnings.append("Warning: session evidence was truncated.")
    if payload.get("response_truncated") is True:
        warnings.append(
            "Warning: response omitted "
            f"{_display(payload.get('omitted_complete_lines'))} complete, "
            f"{_display(payload.get('omitted_partial_lines'))} partial, and "
            f"{_display(payload.get('omitted_oversized_lines'))} oversized lines."
        )
    return warnings


def _sort_int(value: object) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) else -1


def _display_text(value: object) -> str:
    if not isinstance(value, str):
        return "<invalid line>"
    return value[:-1] if value.endswith("\n") else value


def _display(value: object) -> str:
    return "none" if value is None or value == "" else str(value)
