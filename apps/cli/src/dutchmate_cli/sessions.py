"""Terminal formatting for bounded session list and detail responses."""

from __future__ import annotations

from collections.abc import Mapping
from typing import cast


def format_session_list(payload: Mapping[str, object]) -> str:
    """Format one bounded newest-first session page."""

    raw_items = payload.get("items")
    if not isinstance(raw_items, list) or not raw_items:
        lines = ["Sessions: none"]
    else:
        lines = ["Sessions:"]
        for raw_item in raw_items:
            item = _as_mapping(raw_item)
            lines.append(f"  {_format_list_item(item)}" if item is not None else "  invalid")
    cursor = payload.get("next_cursor")
    if isinstance(cursor, str) and cursor:
        lines.append(f"Next cursor: {cursor}")
    return "\n".join(lines)


def format_session_detail(payload: Mapping[str, object]) -> str:
    """Format bounded native or legacy session detail."""

    compatibility = _display(payload.get("compatibility"))
    lines = [
        f"Session: {_display(payload.get('session_id'))}",
        f"Schema: v{_display(payload.get('schema_version'))} ({compatibility})",
        f"Started: {_display(payload.get('started_at'))}",
    ]
    if compatibility == "legacy_read_only":
        lines.extend(
            [
                "Access: read-only; migration required and unavailable",
                f"Command: {_display(payload.get('command'))}",
                f"Firmware: {_display(payload.get('firmware'))}",
                f"Device: {_display(payload.get('device'))}",
            ]
        )
    else:
        lines.extend(
            [
                f"Workflow: {_display(payload.get('workflow'))}",
                f"State: {_display(payload.get('state'))}",
                f"End reason: {_display(payload.get('end_reason'))}",
                f"Backend: {_display(payload.get('backend_mode'))}",
                f"Segments: {_display(payload.get('segment_count'))}",
                f"Integrity: {_nested_display(payload.get('integrity'), 'loss_status')}",
                f"First error: {_format_first_error(payload.get('first_error'))}",
                f"Truncated: {_yes_no(payload.get('truncated'))}",
                f"Interrupted: {_yes_no(payload.get('interrupted'))}",
                f"Resumed: {_yes_no(payload.get('resumed'))}",
            ]
        )
    lines.append("Artifacts:")
    lines.extend(_format_artifacts(payload.get("artifact_manifest")))
    return "\n".join(lines)


def _format_list_item(item: Mapping[str, object] | None) -> str:
    if item is None:
        return "invalid"
    session_id = _display(item.get("session_id"))
    schema_version = _display(item.get("schema_version"))
    compatibility = _display(item.get("compatibility"))
    if compatibility == "legacy_read_only":
        return (
            f"{session_id} [v{schema_version} {compatibility}] "
            f"command={_display(item.get('command'))} migration=required"
        )
    return (
        f"{session_id} [v{schema_version} {compatibility}] "
        f"{_display(item.get('state'))}/{_display(item.get('workflow'))} "
        f"backend={_display(item.get('backend_mode'))} "
        f"segments={_display(item.get('segment_count'))} "
        f"loss={_nested_display(item.get('integrity'), 'loss_status')}"
    )


def _format_artifacts(value: object) -> list[str]:
    if not isinstance(value, list) or not value:
        return ["  none"]
    lines: list[str] = []
    for raw_artifact in value:
        artifact = _as_mapping(raw_artifact)
        if artifact is None:
            lines.append("  invalid")
            continue
        record_count = artifact.get("records")
        records = "" if record_count is None else f", records={_display(record_count)}"
        lines.append(
            f"  {_display(artifact.get('name'))}: "
            f"{_display(artifact.get('bytes'))} bytes{records}"
        )
    return lines


def _format_first_error(value: object) -> str:
    error = _as_mapping(value)
    if error is None:
        return "none"
    return (
        f"{_display(error.get('pattern'))} at segment "
        f"{_display(error.get('segment_id'))}, event "
        f"{_display(error.get('ingestion_index'))}"
    )


def _nested_display(value: object, key: str) -> str:
    mapping = _as_mapping(value)
    return _display(mapping.get(key) if mapping is not None else None)


def _as_mapping(value: object) -> Mapping[str, object] | None:
    if isinstance(value, Mapping):
        return cast(Mapping[str, object], value)
    return None


def _display(value: object) -> str:
    if value is None or value == "":
        return "none"
    return str(value)


def _yes_no(value: object) -> str:
    if value is True:
        return "yes"
    if value is False:
        return "no"
    return "unknown"
