"""Compatibility adapters from the Enhanced v1 wire protocol to normalized events."""

from __future__ import annotations

from typing import Protocol

from dutchmate_core.backends.contracts import (
    BackendEvent,
    BackendInputError,
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.device_connection.errors import ProtocolError
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.device_connection.transport import TransportTimeoutError


class EnhancedMessageSource(Protocol):
    """Synchronous source of parsed Enhanced wire-protocol messages."""

    def read_message(self) -> DeviceMessage:
        """Read the next parsed message or raise on transport timeout."""


class EnhancedCaptureEventSource:
    """Interim synchronous adapter for the existing Enhanced serial transport."""

    def __init__(
        self,
        source: EnhancedMessageSource,
        *,
        segment_id: int,
        source_origin_us: int,
    ) -> None:
        self._source = source
        self._segment_id = segment_id
        self._source_origin_us = source_origin_us

    def read_event(self) -> BackendEvent | None:
        """Read and normalize one wire message, returning ``None`` for inactivity."""

        try:
            message = self._source.read_message()
        except TransportTimeoutError:
            return None
        except ProtocolError as exc:
            raise BackendInputError(str(exc)) from exc

        return normalize_enhanced_message(
            message,
            segment_id=self._segment_id,
            source_origin_us=self._source_origin_us,
        )


class EnhancedNdjsonEventStream:
    """Parse Enhanced NDJSON chunks and expose only normalized evidence events."""

    def __init__(
        self,
        *,
        segment_id: int = 0,
        source_origin_us: int = 0,
        parser: NdjsonStreamParser | None = None,
    ) -> None:
        self._segment_id = segment_id
        self._source_origin_us = source_origin_us
        self._parser = parser or NdjsonStreamParser()

    @property
    def pending_bytes(self) -> bytes:
        """Return an incomplete Enhanced NDJSON frame buffered by the parser."""

        return self._parser.pending_bytes

    def feed(self, chunk: bytes) -> list[BackendEvent]:
        """Parse a chunk and normalize its UART and buffer-telemetry messages."""

        try:
            messages = self._parser.feed(chunk)
        except ProtocolError as exc:
            raise BackendInputError(str(exc)) from exc

        events: list[BackendEvent] = []
        for message in messages:
            event = normalize_enhanced_message(
                message,
                segment_id=self._segment_id,
                source_origin_us=self._source_origin_us,
            )
            if event is not None:
                events.append(event)
        return events


def normalize_enhanced_message(
    message: DeviceMessage,
    *,
    segment_id: int,
    source_origin_us: int,
) -> BackendEvent | None:
    """Translate one parsed Enhanced message into the shared event model."""

    if isinstance(message, UartMessage):
        return UartReceiveEvent(
            segment_id=segment_id,
            timestamp_us=_relative_timestamp(message.timestamp_us, source_origin_us),
            channel=message.channel,
            data=message.data,
        )
    if isinstance(message, BufferOverflowMessage):
        return BufferOverflowEvent(
            segment_id=segment_id,
            timestamp_us=_relative_timestamp(message.timestamp_us, source_origin_us),
            channel=message.channel,
            dropped_bytes=message.dropped_bytes,
        )
    if isinstance(message, BufferStatusMessage):
        return BufferStatusEvent(
            segment_id=segment_id,
            timestamp_us=_relative_timestamp(message.timestamp_us, source_origin_us),
            size_bytes=message.uart_rx_size_bytes,
            used_bytes=message.uart_rx_used_bytes,
            high_water_bytes=message.uart_rx_high_water_bytes,
            dropped_bytes_total=message.dropped_bytes_total,
            overflow_events=message.overflow_events,
        )
    return None


def _relative_timestamp(timestamp_us: int, source_origin_us: int) -> int:
    if source_origin_us < 0:
        raise ValueError("Enhanced source origin must be non-negative")
    if timestamp_us < source_origin_us:
        raise BackendInputError("Enhanced event timestamp precedes its segment origin")
    return timestamp_us - source_origin_us
