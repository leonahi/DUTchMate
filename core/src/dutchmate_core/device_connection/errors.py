"""Protocol parsing errors."""


class ProtocolError(ValueError):
    """Base class for host-device protocol errors."""


class MalformedMessageError(ProtocolError):
    """Raised when a serial line is not valid JSON or not a JSON object."""


class ProtocolValidationError(ProtocolError):
    """Raised when a JSON object does not match the v1 protocol contract."""


class ProtocolVersionError(ProtocolValidationError):
    """Raised when a device speaks an unsupported protocol version."""


class UnsupportedMessageTypeError(ProtocolValidationError):
    """Raised when a valid JSON object has a message type we do not parse yet."""
