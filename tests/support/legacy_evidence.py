"""Frozen pre-v2 fixture construction from Stage 7 (9a228fcc).

Test-only: never imported by a distribution. Production SessionStore has no
legacy creation/append API. These builders preserve compatibility test inputs;
the inherited production queries are the read-only boundary under test.
"""

from typing import Literal

import dutchmate_core.session_store.evidence as _shared
from dutchmate_core.backends import BufferOverflowEvent, BufferStatusEvent, UartReceiveEvent
from dutchmate_core.session_store.evidence import (
    _bytes_to_b64,
)


def control_action_event_json(
    *,
    action: Literal["reset"],
    segment_id: int,
    performed_at: str,
    pulse_ms: int,
    timestamp_us: int | None,
    device_timestamp_us: int | None,
) -> dict[str, object]:
    """Build one accepted normalized control-action record."""

    if action != "reset":
        raise ValueError("Phase 1 control-action evidence supports only reset")
    _non_negative_int(segment_id, "control action segment_id")
    if not isinstance(performed_at, str) or not performed_at:
        raise ValueError("control action performed_at must be a timestamp string")
    if isinstance(pulse_ms, bool) or not isinstance(pulse_ms, int) or not 1 <= pulse_ms <= 10000:
        raise ValueError("control action pulse_ms must be an integer from 1 through 10000")
    for field, value in (
        ("timestamp_us", timestamp_us),
        ("device_timestamp_us", device_timestamp_us),
    ):
        if value is not None:
            _non_negative_int(value, f"control action {field}")
    return {
        "type": "control_action",
        "action": action,
        "segment_id": segment_id,
        "performed_at": performed_at,
        "pulse_ms": pulse_ms,
        "timestamp_us": timestamp_us,
        "device_timestamp_us": device_timestamp_us,
    }


def uart_tx_attempt_event_json(
    *,
    attempt_id: str,
    segment_id: int,
    attempted_at: str,
    data: bytes,
) -> dict[str, object]:
    """Build one exact pre-dispatch forced-send perturbation record."""

    _validate_attempt_id(attempt_id)
    _non_negative_int(segment_id, "UART TX segment_id")
    if not isinstance(attempted_at, str) or not attempted_at:
        raise ValueError("UART TX attempted_at must be a timestamp string")
    if not isinstance(data, bytes) or not 1 <= len(data) <= 1024:
        raise ValueError("UART TX attempt data must contain 1..1024 bytes")
    return {
        "type": "uart_tx_attempt",
        "attempt_id": attempt_id,
        "segment_id": segment_id,
        "attempted_at": attempted_at,
        "data_b64": _bytes_to_b64(data),
        "payload_bytes": len(data),
        "forced": True,
    }


def uart_tx_result_event_json(
    *,
    attempt_id: str,
    segment_id: int,
    completed_at: str,
    outcome: Literal["success", "failed"],
    error: str | None,
    bytes_accepted: int | None,
    timestamp_us: int | None,
    device_timestamp_us: int | None,
) -> dict[str, object]:
    """Build one post-dispatch forced-send perturbation result record."""

    _validate_attempt_id(attempt_id)
    _non_negative_int(segment_id, "UART TX segment_id")
    if not isinstance(completed_at, str) or not completed_at:
        raise ValueError("UART TX completed_at must be a timestamp string")
    if outcome not in {"success", "failed"}:
        raise ValueError("UART TX outcome must be success or failed")
    if (outcome == "success") != (error is None):
        raise ValueError("UART TX result outcome and error must agree")
    if error is not None and (not isinstance(error, str) or not error):
        raise ValueError("UART TX result error must be non-empty or null")
    for field, value in (
        ("bytes_accepted", bytes_accepted),
        ("timestamp_us", timestamp_us),
        ("device_timestamp_us", device_timestamp_us),
    ):
        if value is not None:
            _non_negative_int(value, f"UART TX {field}")
    return {
        "type": "uart_tx_result",
        "attempt_id": attempt_id,
        "segment_id": segment_id,
        "completed_at": completed_at,
        "outcome": outcome,
        "error": error,
        "bytes_accepted": bytes_accepted,
        "timestamp_us": timestamp_us,
        "device_timestamp_us": device_timestamp_us,
    }


def __getattr__(name):
    return getattr(_shared, name)


def uart_event_json(event: UartReceiveEvent) -> dict[str, object]:
    return {
        "type": "uart",
        "segment_id": event.segment_id,
        "timestamp_us": event.timestamp_us,
        "channel": event.channel,
        "data_b64": _bytes_to_b64(event.data),
        "text": event.data.decode("utf-8", errors="replace"),
    }


def buffer_overflow_event_json(event: BufferOverflowEvent) -> dict[str, object]:
    return {
        "type": "buffer_overflow",
        "segment_id": event.segment_id,
        "timestamp_us": event.timestamp_us,
        "channel": event.channel,
        "dropped_bytes": event.dropped_bytes,
    }


def buffer_status_event_json(event: BufferStatusEvent) -> dict[str, object]:
    return {
        "type": "buffer_status",
        "segment_id": event.segment_id,
        "timestamp_us": event.timestamp_us,
        "uart_rx_size_bytes": event.size_bytes,
        "uart_rx_used_bytes": event.used_bytes,
        "uart_rx_high_water_bytes": event.high_water_bytes,
        "dropped_bytes_total": event.dropped_bytes_total,
        "overflow_events": event.overflow_events,
    }


def usb_disconnect_event_json(*, host_timestamp: str, segment_id: int) -> dict[str, object]:
    return {
        "type": "usb_disconnect",
        "host_timestamp": host_timestamp,
        "segment_id": segment_id,
    }


def usb_reconnect_event_json(*, host_timestamp: str, segment_id: int) -> dict[str, object]:
    return {
        "type": "usb_reconnect",
        "host_timestamp": host_timestamp,
        "segment_id": segment_id,
    }


def timestamp_discontinuity_event_json(
    *,
    host_timestamp: str,
    from_segment_id: int,
    to_segment_id: int,
) -> dict[str, object]:
    return {
        "type": "timestamp_discontinuity",
        "host_timestamp": host_timestamp,
        "from_segment_id": from_segment_id,
        "to_segment_id": to_segment_id,
    }


def _validate_attempt_id(attempt_id: object) -> str:
    if not isinstance(attempt_id, str) or not 1 <= len(attempt_id.encode("utf-8")) <= 64:
        raise ValueError("UART TX attempt_id must contain 1..64 UTF-8 bytes")
    return attempt_id


def _non_negative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")
    return value
