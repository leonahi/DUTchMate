"""CLI formatting for the thin capture Monitor alias."""

from collections.abc import Mapping

from dutchmate_cli.monitor import format_monitor_result


def format_capture_result(payload: Mapping[str, object]) -> str:
    return format_monitor_result(payload).replace("Monitor", "Capture", 1)
