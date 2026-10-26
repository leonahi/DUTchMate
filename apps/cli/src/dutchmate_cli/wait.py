"""CLI formatting for the thin wait Monitor alias."""

from collections.abc import Mapping

from dutchmate_cli.monitor import format_monitor_result


def format_wait_pattern(payload: Mapping[str, object]) -> str:
    return format_monitor_result(payload).replace("Monitor", "Wait", 1)
