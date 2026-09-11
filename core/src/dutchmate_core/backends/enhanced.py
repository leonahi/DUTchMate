"""Enhanced v1 protocol adapters and normalized event translation."""

from __future__ import annotations

from typing import cast

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendUartSendResult,
    BackendWriteError,
    BufferOverflowEvent,
    BufferStatusEvent,
    ControlState,
    DeviceControlError,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.device_connection.commands import (
    configure_gpio_mode_command,
    pulse_control_command,
    set_control_state_command,
    uart_send_command,
)
from dutchmate_core.device_connection.errors import (
    HostCommandFrameTooLargeError,
    ProtocolError,
)
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
from dutchmate_core.device_connection.transport import (
    AsyncCommandTransport,
    TransportTimeoutError,
    TransportWriteError,
)

DEFAULT_ENHANCED_COMMAND_TIMEOUT_S = 1.0
_ENHANCED_PULSE_COMPLETION_MARGIN_S = 0.5


class AsyncEnhancedDeviceControl:
    """Translate semantic control operations through an async Enhanced transport."""

    def __init__(
        self,
        transport: AsyncCommandTransport,
        *,
        timeout_s: float = DEFAULT_ENHANCED_COMMAND_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._timeout_s = timeout_s

    async def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        command = configure_gpio_mode_command(
            channel=channel,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        return await self._request_success(
            command.to_ndjson(),
            operation="configure_gpio_mode",
            response_label="GPIO mode configuration",
        )

    async def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        command = pulse_control_command(channel=channel, pulse_ms=pulse_ms)
        timeout_s = max(
            self._timeout_s,
            pulse_ms / 1000.0 + _ENHANCED_PULSE_COMPLETION_MARGIN_S,
        )
        return await self._request_success(
            command.to_ndjson(),
            operation="reset",
            timeout_s=timeout_s,
        )

    async def set_control_state(
        self,
        *,
        channel: str,
        state: ControlState,
    ) -> int | None:
        command = set_control_state_command(channel=channel, state=state)
        return await self._request_success(
            command.to_ndjson(),
            operation="set_boot_mode",
        )

    async def _request_success(
        self,
        command: bytes,
        *,
        operation: str,
        response_label: str | None = None,
        timeout_s: float | None = None,
    ) -> int | None:
        label = response_label or operation
        try:
            response = await self._transport.request(
                command,
                self._timeout_s if timeout_s is None else timeout_s,
            )
        except TransportWriteError as exc:
            raise DeviceControlError(error=exc.error, detail=str(exc)) from exc
        except TransportTimeoutError as exc:
            raise DeviceControlError(
                error="timeout",
                detail=f"Timed out waiting for {label} response",
            ) from exc
        except HostCommandFrameTooLargeError:
            raise
        except ProtocolError as exc:
            raise backend_input_error_from_protocol(exc, operation=operation) from exc
        return _control_success_timestamp(response, label=label)


class AsyncEnhancedUartSender:
    """Translate complete UART payloads through an async Enhanced transport."""

    def __init__(
        self,
        transport: AsyncCommandTransport,
        *,
        timeout_s: float = DEFAULT_ENHANCED_COMMAND_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._timeout_s = timeout_s

    async def send_uart(self, data: bytes) -> BackendUartSendResult:
        command = uart_send_command(data)
        try:
            response = await self._transport.request(
                command.to_ndjson(),
                self._timeout_s,
            )
        except TransportWriteError as exc:
            raise BackendWriteError(
                str(exc),
                bytes_accepted=None,
                error=exc.error,
            ) from exc
        except TransportTimeoutError as exc:
            raise BackendWriteError(
                "Enhanced UART send timed out",
                bytes_accepted=None,
                error="timeout",
            ) from exc
        except HostCommandFrameTooLargeError:
            raise
        except ProtocolError as exc:
            raise backend_input_error_from_protocol(exc, operation="uart_send") from exc
        except BackendInputError:
            raise
        except Exception as exc:
            raise BackendWriteError(
                "Enhanced UART send transport failed",
                bytes_accepted=None,
            ) from exc
        return _uart_send_result(response, expected_bytes=len(data))


def _control_success_timestamp(
    response: DeviceMessage,
    *,
    label: str,
) -> int | None:
    if isinstance(response, CommandSuccessMessage):
        return response.timestamp_us
    if isinstance(response, CommandErrorMessage):
        raise DeviceControlError(error=response.error, detail=response.detail)
    raise DeviceControlError(
        error="unexpected_response",
        detail=f"Expected command response for {label}, got {type(response).__name__}",
    )


def _uart_send_result(
    response: DeviceMessage,
    *,
    expected_bytes: int,
) -> BackendUartSendResult:
    if isinstance(response, CommandErrorMessage):
        raise BackendWriteError(
            response.detail,
            bytes_accepted=None,
            error=response.error,
        )
    if not isinstance(response, CommandSuccessMessage):
        raise BackendWriteError(
            "Enhanced UART send received an unexpected response",
            bytes_accepted=None,
        )
    if response.bytes_accepted != expected_bytes:
        raise BackendWriteError(
            "Enhanced UART send acknowledgement did not accept the complete payload",
            bytes_accepted=response.bytes_accepted,
        )
    if response.timestamp_us is None:
        raise BackendWriteError(
            "Enhanced UART send acknowledgement omitted timestamp_us",
            bytes_accepted=response.bytes_accepted,
        )
    return BackendUartSendResult(
        bytes_accepted=response.bytes_accepted,
        device_timestamp_us=response.timestamp_us,
    )


def normalize_enhanced_hello(hello: HelloMessage, *, port: str) -> BackendInfo:
    """Translate one Enhanced hello message into backend-neutral identity."""

    capabilities = frozenset(
        cast(BackendCapability, value) for value in hello.capabilities
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
            raise backend_input_error_from_protocol(exc) from exc

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
        raise BackendInputError(
            "Enhanced event timestamp precedes its segment origin",
            backend_mode="enhanced",
        )
    return timestamp_us - source_origin_us


def backend_input_error_from_protocol(
    exc: ProtocolError,
    *,
    operation: str | None = None,
) -> BackendInputError:
    """Preserve bounded Enhanced protocol classification across the adapter."""

    detail = {
        "frame_too_large": "Enhanced protocol frame exceeds the device-to-host size limit",
        "invalid_utf8": "Enhanced protocol frame is not valid UTF-8",
        "invalid_json": "Enhanced protocol frame is not valid JSON",
        "invalid_message": (
            "Enhanced protocol message does not match the expected schema"
        ),
    }[exc.input_error]
    return BackendInputError(
        detail,
        input_error=exc.input_error,
        operation=operation,
        backend_mode="enhanced",
        observed_frame_bytes=exc.observed_frame_bytes,
        max_frame_bytes=exc.max_frame_bytes,
    )


def enhanced_segment_context(
    segment_id: int,
    source_origin_us: int,
) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=source_origin_us,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )


def enhanced_message_timestamp_us(message: DeviceMessage) -> int | None:
    if isinstance(message, (UartMessage, BufferOverflowMessage, BufferStatusMessage)):
        return message.timestamp_us
    return None
