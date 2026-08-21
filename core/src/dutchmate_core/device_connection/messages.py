"""Typed protocol messages received from the Debug Helper."""

from dataclasses import dataclass

PROTOCOL_VERSION = 1

KNOWN_CAPABILITIES = frozenset(
    {
        "uart_capture",
        "gpio_control",
        "uart_send",
        "gpio_events",
        "power_sense",
        "msgpack",
    }
)

KNOWN_ERROR_CODES = frozenset(
    {
        "invalid_command",
        "invalid_argument",
        "not_configured",
        "capture_active",
        "hardware_fault",
        "timeout",
    }
)


@dataclass(frozen=True, slots=True)
class HelloMessage:
    """Debug Helper hello handshake."""

    firmware: str
    device: str
    capabilities: tuple[str, ...]
    protocol_version: int = PROTOCOL_VERSION


@dataclass(frozen=True, slots=True)
class UartMessage:
    """UART bytes captured by the Debug Helper."""

    channel: int
    timestamp_us: int
    data: bytes
    text: str


@dataclass(frozen=True, slots=True)
class BufferOverflowMessage:
    """UART/event ring buffer overflow reported by the Debug Helper."""

    channel: int
    timestamp_us: int
    dropped_bytes: int


@dataclass(frozen=True, slots=True)
class BufferStatusMessage:
    """Firmware-side UART ring buffer telemetry."""

    timestamp_us: int
    uart_rx_size_bytes: int
    uart_rx_used_bytes: int
    uart_rx_high_water_bytes: int
    dropped_bytes_total: int
    overflow_events: int


@dataclass(frozen=True, slots=True)
class CommandSuccessMessage:
    """Successful command response from the Debug Helper."""

    timestamp_us: int | None = None
    bytes_accepted: int | None = None


@dataclass(frozen=True, slots=True)
class CommandErrorMessage:
    """Rejected or failed command response from the Debug Helper."""

    error: str
    detail: str
