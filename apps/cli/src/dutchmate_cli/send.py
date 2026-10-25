"""CLI formatting for UART-send outcomes."""

from collections.abc import Mapping


def format_uart_send(payload: Mapping[str, object]) -> str:
    """Format a complete audited UART send."""

    lines = [
        "UART command sent",
        f"Performed: {_display(payload.get('performed_at'))}",
    ]
    device_timestamp = payload.get("device_timestamp_us")
    if device_timestamp is not None:
        lines.append(f"Device timestamp: {device_timestamp} us")
    lines.extend(
        [
            f"Bytes accepted: {_display(payload.get('accepted_bytes'))}",
            f"Attempt: {_display(payload.get('attempt_id'))}",
            f"Audit: {_display(payload.get('audit_status'))}",
            f"Exact bytes (base64): {_display(payload.get('data_b64'))}",
        ]
    )
    return "\n".join(lines)


def _display(value: object) -> str:
    return "none" if value is None or value == "" else str(value)
