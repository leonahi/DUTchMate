"""Parser for v1 device-to-host protocol messages."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from dutchmate_core.device_connection.errors import (
    MalformedMessageError,
    ProtocolValidationError,
    ProtocolVersionError,
    UnsupportedMessageTypeError,
)
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    KNOWN_CAPABILITIES,
    PROTOCOL_VERSION,
    HelloMessage,
    UartMessage,
)

DeviceMessage = HelloMessage | UartMessage | BufferOverflowMessage | BufferStatusMessage

_HELLO_KEYS = {"type", "v", "firmware", "device", "capabilities"}
_UART_KEYS = {"type", "channel", "timestamp_us", "data_b64"}
_BUFFER_OVERFLOW_KEYS = {"type", "channel", "timestamp_us", "dropped_bytes"}
_BUFFER_STATUS_KEYS = {
    "type",
    "timestamp_us",
    "uart_rx_size_bytes",
    "uart_rx_used_bytes",
    "uart_rx_high_water_bytes",
    "dropped_bytes_total",
    "overflow_events",
}


def parse_device_message(line: str | bytes) -> DeviceMessage:
    """Parse one NDJSON device-to-host protocol line.

    This parser currently supports the `hello` handshake, `uart` events,
    `buffer_overflow` events, and `buffer_status` events. Other v1 message
    shapes will be added in later slices.
    """

    payload = _load_json_object(line)
    message_type = payload.get("type")

    if message_type == "hello":
        return _parse_hello(payload)
    if message_type == "uart":
        return _parse_uart(payload)
    if message_type == "buffer_overflow":
        return _parse_buffer_overflow(payload)
    if message_type == "buffer_status":
        return _parse_buffer_status(payload)

    if isinstance(message_type, str):
        raise UnsupportedMessageTypeError(f"Unsupported device message type: {message_type}")

    raise ProtocolValidationError("Device message must include a string 'type' field")


def _load_json_object(line: str | bytes) -> dict[str, Any]:
    if isinstance(line, bytes):
        try:
            line = line.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MalformedMessageError("Protocol line is not valid UTF-8") from exc

    try:
        payload = json.loads(line)
    except json.JSONDecodeError as exc:
        raise MalformedMessageError("Protocol line is not valid JSON") from exc

    if not isinstance(payload, dict):
        raise MalformedMessageError("Protocol line must decode to a JSON object")

    return payload


def _parse_hello(payload: dict[str, Any]) -> HelloMessage:
    extra_keys = set(payload) - _HELLO_KEYS
    if extra_keys:
        names = ", ".join(sorted(extra_keys))
        raise ProtocolValidationError(f"Unexpected hello field(s): {names}")

    missing_keys = _HELLO_KEYS - set(payload)
    if missing_keys:
        names = ", ".join(sorted(missing_keys))
        raise ProtocolValidationError(f"Missing hello field(s): {names}")

    version = payload["v"]
    if not isinstance(version, int):
        raise ProtocolValidationError("Hello protocol version 'v' must be an integer")
    if version != PROTOCOL_VERSION:
        raise ProtocolVersionError(f"Unsupported protocol version: {version}")

    firmware = payload["firmware"]
    if not isinstance(firmware, str) or not firmware:
        raise ProtocolValidationError("Hello 'firmware' must be a non-empty string")

    device = payload["device"]
    if not isinstance(device, str) or not device:
        raise ProtocolValidationError("Hello 'device' must be a non-empty string")

    capabilities = payload["capabilities"]
    if not isinstance(capabilities, list):
        raise ProtocolValidationError("Hello 'capabilities' must be an array")

    parsed_capabilities: list[str] = []
    seen_capabilities: set[str] = set()
    for capability in capabilities:
        if not isinstance(capability, str):
            raise ProtocolValidationError("Hello capabilities must be strings")
        if capability not in KNOWN_CAPABILITIES:
            raise ProtocolValidationError(f"Unknown hello capability: {capability}")
        if capability in seen_capabilities:
            raise ProtocolValidationError(f"Duplicate hello capability: {capability}")
        seen_capabilities.add(capability)
        parsed_capabilities.append(capability)

    return HelloMessage(
        firmware=firmware,
        device=device,
        capabilities=tuple(parsed_capabilities),
        protocol_version=version,
    )


def _parse_uart(payload: dict[str, Any]) -> UartMessage:
    extra_keys = set(payload) - _UART_KEYS
    if extra_keys:
        names = ", ".join(sorted(extra_keys))
        raise ProtocolValidationError(f"Unexpected uart field(s): {names}")

    missing_keys = _UART_KEYS - set(payload)
    if missing_keys:
        names = ", ".join(sorted(missing_keys))
        raise ProtocolValidationError(f"Missing uart field(s): {names}")

    channel = payload["channel"]
    if not isinstance(channel, int) or channel < 0:
        raise ProtocolValidationError("UART 'channel' must be a non-negative integer")

    timestamp_us = payload["timestamp_us"]
    if not isinstance(timestamp_us, int) or timestamp_us < 0:
        raise ProtocolValidationError("UART 'timestamp_us' must be a non-negative integer")

    data_b64 = payload["data_b64"]
    if not isinstance(data_b64, str):
        raise ProtocolValidationError("UART 'data_b64' must be a base64 string")

    try:
        data = base64.b64decode(data_b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ProtocolValidationError("UART 'data_b64' is not valid base64") from exc

    return UartMessage(
        channel=channel,
        timestamp_us=timestamp_us,
        data=data,
        text=data.decode("utf-8", errors="replace"),
    )


def _parse_buffer_overflow(payload: dict[str, Any]) -> BufferOverflowMessage:
    extra_keys = set(payload) - _BUFFER_OVERFLOW_KEYS
    if extra_keys:
        names = ", ".join(sorted(extra_keys))
        raise ProtocolValidationError(f"Unexpected buffer_overflow field(s): {names}")

    missing_keys = _BUFFER_OVERFLOW_KEYS - set(payload)
    if missing_keys:
        names = ", ".join(sorted(missing_keys))
        raise ProtocolValidationError(f"Missing buffer_overflow field(s): {names}")

    channel = payload["channel"]
    if not isinstance(channel, int) or channel < 0:
        raise ProtocolValidationError("Buffer overflow 'channel' must be a non-negative integer")

    timestamp_us = payload["timestamp_us"]
    if not isinstance(timestamp_us, int) or timestamp_us < 0:
        raise ProtocolValidationError(
            "Buffer overflow 'timestamp_us' must be a non-negative integer"
        )

    dropped_bytes = payload["dropped_bytes"]
    if not isinstance(dropped_bytes, int) or dropped_bytes < 1:
        raise ProtocolValidationError("Buffer overflow 'dropped_bytes' must be a positive integer")

    return BufferOverflowMessage(
        channel=channel,
        timestamp_us=timestamp_us,
        dropped_bytes=dropped_bytes,
    )


def _parse_buffer_status(payload: dict[str, Any]) -> BufferStatusMessage:
    extra_keys = set(payload) - _BUFFER_STATUS_KEYS
    if extra_keys:
        names = ", ".join(sorted(extra_keys))
        raise ProtocolValidationError(f"Unexpected buffer_status field(s): {names}")

    missing_keys = _BUFFER_STATUS_KEYS - set(payload)
    if missing_keys:
        names = ", ".join(sorted(missing_keys))
        raise ProtocolValidationError(f"Missing buffer_status field(s): {names}")

    timestamp_us = _required_non_negative_int(payload, "timestamp_us", "Buffer status")
    uart_rx_size_bytes = _required_positive_int(
        payload, "uart_rx_size_bytes", "Buffer status"
    )
    uart_rx_used_bytes = _required_non_negative_int(
        payload, "uart_rx_used_bytes", "Buffer status"
    )
    uart_rx_high_water_bytes = _required_non_negative_int(
        payload, "uart_rx_high_water_bytes", "Buffer status"
    )
    dropped_bytes_total = _required_non_negative_int(
        payload, "dropped_bytes_total", "Buffer status"
    )
    overflow_events = _required_non_negative_int(payload, "overflow_events", "Buffer status")

    if uart_rx_used_bytes > uart_rx_size_bytes:
        raise ProtocolValidationError(
            "Buffer status 'uart_rx_used_bytes' cannot exceed 'uart_rx_size_bytes'"
        )
    if uart_rx_high_water_bytes > uart_rx_size_bytes:
        raise ProtocolValidationError(
            "Buffer status 'uart_rx_high_water_bytes' cannot exceed 'uart_rx_size_bytes'"
        )

    return BufferStatusMessage(
        timestamp_us=timestamp_us,
        uart_rx_size_bytes=uart_rx_size_bytes,
        uart_rx_used_bytes=uart_rx_used_bytes,
        uart_rx_high_water_bytes=uart_rx_high_water_bytes,
        dropped_bytes_total=dropped_bytes_total,
        overflow_events=overflow_events,
    )


def _required_non_negative_int(
    payload: dict[str, Any], field_name: str, message_name: str
) -> int:
    value = payload[field_name]
    if not isinstance(value, int) or value < 0:
        raise ProtocolValidationError(
            f"{message_name} '{field_name}' must be a non-negative integer"
        )
    return value


def _required_positive_int(payload: dict[str, Any], field_name: str, message_name: str) -> int:
    value = payload[field_name]
    if not isinstance(value, int) or value < 1:
        raise ProtocolValidationError(f"{message_name} '{field_name}' must be a positive integer")
    return value
