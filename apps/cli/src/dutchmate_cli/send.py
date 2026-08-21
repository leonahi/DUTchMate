"""CLI formatting for UART-send outcomes."""

from collections.abc import Mapping


def format_uart_send(payload: Mapping[str, object]) -> str:
    """Format a complete standalone or forced in-session UART send."""

    lines = [
        "UART command sent",
        f"Performed: {_display(payload.get('performed_at'))}",
    ]
    device_timestamp = payload.get("device_timestamp_us")
    if device_timestamp is not None:
        lines.append(f"Device timestamp: {device_timestamp} us")
    attempt_id = payload.get("attempt_id")
    if attempt_id is not None:
        lines.extend(
            [
                f"Attempt: {_display(attempt_id)}",
                (
                    "Perturbation logged: yes"
                    if payload.get("perturbation_logged") is True
                    else "Perturbation logged: no"
                ),
            ]
        )
    return "\n".join(lines)


def _display(value: object) -> str:
    return "none" if value is None or value == "" else str(value)
