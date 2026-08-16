"""Compatibility adapters from the Enhanced v1 wire protocol to normalized events."""

from __future__ import annotations

from typing import Protocol, cast

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BufferOverflowEvent,
    BufferStatusEvent,
    DeviceControl,
    DeviceControlError,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.device_connection.commands import (
    boot_mode_command,
    configure_gpio_mode_command,
    reset_command,
)
from dutchmate_core.device_connection.errors import ProtocolError
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.device_connection.transport import CommandTransport, TransportTimeoutError


class EnhancedMessageSource(Protocol):
    """Synchronous source of parsed Enhanced wire-protocol messages."""

    def read_message(self) -> DeviceMessage:
        """Read the next parsed message or raise on transport timeout."""


class EnhancedDeviceControl(DeviceControl):
    """Translate semantic control operations to Enhanced protocol commands."""

    def __init__(self, transport: CommandTransport) -> None:
        self._transport = transport

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        role: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        command = configure_gpio_mode_command(
            channel=channel,
            role=role,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        return self._request_success(
            command.to_ndjson(),
            operation="GPIO mode configuration",
        )

    def reset_dut(self, *, pulse_ms: int) -> int | None:
        return self._request_success(
            reset_command(pulse_ms).to_ndjson(),
            operation="reset",
        )

    def set_boot_mode(self, *, mode: str) -> int | None:
        return self._request_success(
            boot_mode_command(mode).to_ndjson(),
            operation="set_boot_mode",
        )

    def _request_success(self, command: bytes, *, operation: str) -> int | None:
        response = self._transport.request(command)
        if isinstance(response, CommandSuccessMessage):
            return response.timestamp_us
        if isinstance(response, CommandErrorMessage):
            raise DeviceControlError(error=response.error, detail=response.detail)
        raise DeviceControlError(
            error="unexpected_response",
            detail=f"Expected command response for {operation}, got {type(response).__name__}",
        )


class EnhancedCaptureEventSource:
    """Interim synchronous adapter for the existing Enhanced serial transport."""

    def __init__(
        self,
        source: EnhancedMessageSource,
        *,
        segment_id: int,
        source_origin_us: int | None,
    ) -> None:
        self._source = source
        self._segment_id = segment_id
        self._source_origin_us = source_origin_us
        self._segment = (
            _enhanced_segment_context(segment_id, source_origin_us)
            if source_origin_us is not None
            else None
        )

    @property
    def segment(self) -> SegmentContext | None:
        """Return device-timer provenance for this compatibility source."""

        return self._segment

    def read_event(self) -> BackendEvent | None:
        """Read and normalize one wire message, returning ``None`` for inactivity."""

        try:
            message = self._source.read_message()
        except TransportTimeoutError:
            return None
        except ProtocolError as exc:
            raise BackendInputError(str(exc)) from exc

        if self._source_origin_us is None:
            timestamp_us = _message_timestamp_us(message)
            if timestamp_us is None:
                return None
            self._source_origin_us = timestamp_us
            self._segment = _enhanced_segment_context(
                self._segment_id,
                timestamp_us,
            )

        return normalize_enhanced_message(
            message,
            segment_id=self._segment_id,
            source_origin_us=self._source_origin_us,
        )


def normalize_enhanced_hello(hello: HelloMessage, *, port: str) -> BackendInfo:
    """Translate one Enhanced hello message into backend-neutral identity."""

    capabilities = frozenset(
        cast(BackendCapability, "uart_receive" if value == "uart_capture" else value)
        for value in hello.capabilities
    )
    return BackendInfo(
        mode="enhanced",
        port=port,
        device=hello.device,
        firmware=hello.firmware,
        capabilities=capabilities,
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


def _enhanced_segment_context(
    segment_id: int,
    source_origin_us: int,
) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2040_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=source_origin_us,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )


def _message_timestamp_us(message: DeviceMessage) -> int | None:
    if isinstance(message, (UartMessage, BufferOverflowMessage, BufferStatusMessage)):
        return message.timestamp_us
    return None
