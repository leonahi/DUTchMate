"""Priority selection of hardware events and UART TX outcome anomalies."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Final, Literal

from dutchmate_debug_agent.evidence_source import _integer, _jsonl_objects

_HARDWARE_EVENTS: Final = 100
_EVENT_STRING_BYTES: Final = 512
_BOOT_EDGE_LINES: Final = 20
_IMPORTANT_EVENTS: Final = frozenset(
    {
        "buffer_overflow",
        "line_limit_exceeded",
        "usb_disconnect",
        "usb_reconnect",
        "timestamp_discontinuity",
        "control_action",
    }
)
_EVENT_FIELDS: Final = frozenset(
    {
        "type",
        "segment_id",
        "timestamp_us",
        "channel",
        "dropped_bytes",
        "uart_rx_size_bytes",
        "uart_rx_used_bytes",
        "uart_rx_high_water_bytes",
        "dropped_bytes_total",
        "overflow_events",
        "host_timestamp",
        "from_segment_id",
        "to_segment_id",
        "action",
        "performed_at",
        "pulse_ms",
        "device_timestamp_us",
        "attempt_id",
        "attempted_at",
        "payload_bytes",
        "forced",
        "completed_at",
        "outcome",
        "error",
        "bytes_accepted",
        "ingestion_index",
        "line_index_in_event",
        "line_start_ingestion_index",
        "line_start_event_offset",
        "line_end_ingestion_index",
        "line_end_event_offset",
        "total_line_bytes",
        "terminated",
    }
)


@dataclass(frozen=True, slots=True)
class HardwareEventExcerpt:
    session_id: str
    event_index: int
    type: str
    record: dict[str, object]
    truncated_fields: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class UartTxOutcome:
    attempt_id: str
    status: Literal["failed", "unknown"]
    attempt_event_index: int
    result_event_index: int | None
    payload_bytes: int
    bytes_accepted: int | None
    partial_acceptance: bool
    error: str | None
    error_truncated: bool


def _limited_string(value: str) -> tuple[str, bool]:
    encoded = value.encode("utf-8")
    if len(encoded) <= _EVENT_STRING_BYTES:
        return value, False
    return encoded[:_EVENT_STRING_BYTES].decode("utf-8", errors="ignore"), True


def _hardware_excerpt(
    session_id: str, index: int, record: dict[str, object]
) -> HardwareEventExcerpt:
    event_type = record.get("type")
    if not isinstance(event_type, str):
        raise ValueError("hardware event type is invalid")
    projected: dict[str, object] = {}
    truncated: list[str] = []
    for field, value in record.items():
        if field not in _EVENT_FIELDS:
            continue
        if isinstance(value, str):
            projected[field], was_truncated = _limited_string(value)
            if was_truncated:
                truncated.append(field)
        elif value is None or isinstance(value, bool | int):
            projected[field] = value
    return HardwareEventExcerpt(
        session_id=session_id,
        event_index=index,
        type=event_type,
        record=projected,
        truncated_fields=tuple(truncated),
    )


class _HardwareSelector:
    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.count = 0
        self.unmatched_count = 0
        self.successful_count = 0
        self._outcomes: list[UartTxOutcome] = []
        self._critical: list[HardwareEventExcerpt] = []
        self._important: list[HardwareEventExcerpt] = []
        self._start: list[HardwareEventExcerpt] = []
        self._end = deque[HardwareEventExcerpt](maxlen=_BOOT_EDGE_LINES)
        self._recent = deque[HardwareEventExcerpt](maxlen=_HARDWARE_EVENTS)

    def read(self, data: bytes) -> None:
        pending: dict[str, tuple[HardwareEventExcerpt, int]] = {}
        for index, record in enumerate(_jsonl_objects(data)):
            excerpt = _hardware_excerpt(self.session_id, index, record)
            self.count += 1
            if len(self._start) < _BOOT_EDGE_LINES:
                self._start.append(excerpt)
            self._end.append(excerpt)
            self._recent.append(excerpt)
            if excerpt.type in _IMPORTANT_EVENTS and len(self._important) < _HARDWARE_EVENTS:
                self._important.append(excerpt)
            if excerpt.type == "uart_tx_attempt":
                attempt_id = _required_string(record, "attempt_id")
                if attempt_id in pending:
                    raise ValueError("duplicate unresolved UART TX attempt ID")
                pending[attempt_id] = (
                    excerpt,
                    _integer(record.get("payload_bytes"), "payload_bytes"),
                )
            elif excerpt.type == "uart_tx_result":
                attempt_id = _required_string(record, "attempt_id")
                if attempt_id not in pending:
                    raise ValueError("UART TX result has no preceding attempt")
                attempt, payload_bytes = pending.pop(attempt_id)
                outcome = record.get("outcome")
                if outcome not in {"success", "failed"}:
                    raise ValueError("UART TX outcome is invalid")
                accepted = record.get("bytes_accepted")
                if accepted is not None:
                    accepted = _integer(accepted, "bytes_accepted")
                    if accepted > payload_bytes:
                        raise ValueError("UART TX accepted bytes exceed attempted payload")
                if outcome == "success":
                    if accepted != payload_bytes:
                        raise ValueError("successful UART TX result lacks full acceptance")
                    self.successful_count += 1
                if outcome == "failed":
                    error = record.get("error")
                    if not isinstance(error, str) or not error:
                        raise ValueError("failed UART TX result needs an error")
                    limited_error, error_trimmed = _limited_string(error)
                    self._outcomes.append(
                        UartTxOutcome(
                            attempt_id=attempt_id,
                            status="failed",
                            attempt_event_index=attempt.event_index,
                            result_event_index=index,
                            payload_bytes=payload_bytes,
                            bytes_accepted=accepted,
                            partial_acceptance=accepted is not None and accepted < payload_bytes,
                            error=limited_error,
                            error_truncated=error_trimmed,
                        )
                    )
                    if len(self._critical) < _HARDWARE_EVENTS:
                        self._critical.extend((excerpt, attempt))
        for attempt_id, (attempt, payload_bytes) in pending.items():
            self._outcomes.append(
                UartTxOutcome(
                    attempt_id=attempt_id,
                    status="unknown",
                    attempt_event_index=attempt.event_index,
                    result_event_index=None,
                    payload_bytes=payload_bytes,
                    bytes_accepted=None,
                    partial_acceptance=False,
                    error=None,
                    error_truncated=False,
                )
            )
            if len(self._critical) < _HARDWARE_EVENTS:
                self._critical.append(attempt)
        self.unmatched_count = len(pending)

    def select(
        self,
    ) -> tuple[tuple[HardwareEventExcerpt, ...], tuple[UartTxOutcome, ...]]:
        selected: dict[int, HardwareEventExcerpt] = {}
        for excerpt in (*self._critical, *self._important, *self._start, *self._end, *self._recent):
            if len(selected) >= _HARDWARE_EVENTS:
                break
            selected[excerpt.event_index] = excerpt
        excerpts = tuple(selected[index] for index in sorted(selected))
        outcomes = tuple(sorted(self._outcomes, key=lambda item: item.attempt_event_index))
        return excerpts, outcomes


def _required_string(record: dict[str, object], field: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value:
        raise ValueError(f"hardware event {field} must be non-empty text")
    return value
