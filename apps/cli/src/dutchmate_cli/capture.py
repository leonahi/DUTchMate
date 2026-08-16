"""Terminal formatting for UART capture commands."""

from __future__ import annotations

from collections.abc import Mapping


def format_capture_result(payload: Mapping[str, object]) -> str:
    """Format a completed capture session summary."""

    return _format_capture_summary("Capture complete", payload)


def format_boot_test_result(payload: Mapping[str, object]) -> str:
    """Format a completed boot-test session summary."""

    return _format_capture_summary("Boot test complete", payload)


def _format_capture_summary(label: str, payload: Mapping[str, object]) -> str:
    session_id = _display(payload.get("session_id"))
    segments = _display(payload.get("segments"))
    flags = ", ".join(
        (
            f"backend={_display(payload.get('backend_mode'))}",
            f"loss={_loss_status(payload.get('integrity'))}",
            f"timestamp={_timestamp_source(payload.get('timestamp_provenance'))}",
            f"first_error={_first_error(payload.get('first_error'))}",
            f"lines={_line_processing(payload.get('line_processing'))}",
            f"segments={segments}",
            f"overflow={_flag(payload.get('overflow'))}",
            f"interrupted={_flag(payload.get('interrupted'))}",
            f"resumed={_flag(payload.get('resumed'))}",
            f"truncated={_flag(payload.get('truncated'))}",
        )
    )
    return f"{label}: {session_id} ({flags})"


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


def _loss_status(value: object) -> str:
    if not isinstance(value, Mapping):
        return "unknown"
    return _display(value.get("loss_status"))


def _timestamp_source(value: object) -> str:
    if not isinstance(value, list) or not value:
        return "unknown"
    context = value[0]
    if not isinstance(context, Mapping):
        return "unknown"
    timestamp = context.get("timestamp")
    if not isinstance(timestamp, Mapping):
        return "unknown"
    return (
        f"{_display(timestamp.get('source'))}/{_display(timestamp.get('clock'))}:"
        f"{_display(timestamp.get('observation_point'))}/"
        f"{_display(timestamp.get('event_granularity'))}"
    )


def _first_error(value: object) -> str:
    if value is None:
        return "none"
    if not isinstance(value, Mapping):
        return "unknown"
    pattern = _display(value.get("pattern"))
    segment_id = _display(value.get("segment_id"))
    ingestion_index = _display(value.get("ingestion_index"))
    return f"{pattern}@segment:{segment_id}/event:{ingestion_index}"


def _line_processing(value: object) -> str:
    if not isinstance(value, Mapping):
        return "unknown"
    status = _display(value.get("status"))
    oversized = _display(value.get("oversized_line_count"))
    return f"{status}/oversized:{oversized}"
