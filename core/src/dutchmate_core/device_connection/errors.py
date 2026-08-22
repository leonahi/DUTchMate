"""Typed failures at Enhanced wire-protocol input boundaries."""

from typing import Literal, TypeAlias

ProtocolInputError: TypeAlias = Literal[
    "frame_too_large",
    "invalid_utf8",
    "invalid_json",
    "invalid_message",
]


class ProtocolError(ValueError):
    """Base class for host-device protocol errors."""

    input_error: ProtocolInputError = "invalid_message"
    observed_frame_bytes: int | None = None
    max_frame_bytes: int | None = None


class FrameTooLargeError(ProtocolError):
    """Raised before decoding when a device-to-host frame exceeds its bound."""

    input_error: ProtocolInputError = "frame_too_large"

    def __init__(self, *, observed_frame_bytes: int, max_frame_bytes: int) -> None:
        super().__init__(
            "Enhanced protocol frame exceeds the device-to-host size limit"
        )
        self.observed_frame_bytes = observed_frame_bytes
        self.max_frame_bytes = max_frame_bytes


class MalformedMessageError(ProtocolError):
    """Raised when a UTF-8 protocol frame is not valid JSON."""

    input_error: ProtocolInputError = "invalid_json"


class InvalidUtf8Error(MalformedMessageError):
    """Raised when a bounded frame body is not valid UTF-8."""

    input_error: ProtocolInputError = "invalid_utf8"


class ProtocolValidationError(ProtocolError):
    """Raised when a JSON object does not match the v1 protocol contract."""

    input_error: ProtocolInputError = "invalid_message"


class ProtocolVersionError(ProtocolValidationError):
    """Raised when a device speaks an unsupported protocol version."""


class UnsupportedMessageTypeError(ProtocolValidationError):
    """Raised when a valid JSON object has a message type we do not parse yet."""
