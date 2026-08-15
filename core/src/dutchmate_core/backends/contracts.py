"""Backend-neutral identity, timing, event, and receive-source contracts."""

from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

BackendMode: TypeAlias = Literal["basic", "enhanced"]
BackendCapability: TypeAlias = Literal[
    "uart_receive",
    "uart_send",
    "gpio_control",
    "gpio_events",
    "device_timestamp",
    "overflow_telemetry",
    "power_sense",
    "msgpack",
]


@dataclass(frozen=True, slots=True)
class BackendInfo:
    """Identity and physical capabilities reported by one selected backend."""

    mode: BackendMode
    port: str
    device: str | None
    firmware: str | None
    capabilities: frozenset[BackendCapability]


@dataclass(frozen=True, slots=True)
class SegmentTimestamp:
    """Immutable timestamp provenance for one continuous connection segment."""

    source: Literal["host", "device"]
    clock: Literal["monotonic", "rp2040_timer"]
    unit: Literal["us"]
    origin: Literal["segment_start"]
    source_origin_us: int
    observation_point: str
    event_granularity: str


@dataclass(frozen=True, slots=True)
class SegmentContext:
    """Session-local connection segment and its timestamp provenance."""

    segment_id: int
    timestamp: SegmentTimestamp


@dataclass(frozen=True, slots=True)
class UartReceiveEvent:
    """Raw UART bytes observed by a backend within one connection segment."""

    segment_id: int
    timestamp_us: int
    channel: int
    data: bytes


@dataclass(frozen=True, slots=True)
class BufferOverflowEvent:
    """Observed Enhanced-backend UART receive-buffer loss."""

    segment_id: int
    timestamp_us: int
    channel: int
    dropped_bytes: int


@dataclass(frozen=True, slots=True)
class BufferStatusEvent:
    """Enhanced-backend UART receive-buffer telemetry."""

    segment_id: int
    timestamp_us: int
    size_bytes: int
    used_bytes: int
    high_water_bytes: int
    dropped_bytes_total: int
    overflow_events: int


BackendEvent: TypeAlias = UartReceiveEvent | BufferOverflowEvent | BufferStatusEvent


class BackendDisconnectedError(RuntimeError):
    """Raised when the selected backend connection is lost."""


class BackendInputError(RuntimeError):
    """Raised when a backend emits malformed or otherwise invalid input."""


class BackendCapabilityError(RuntimeError):
    """Raised when an operation is disabled or unsupported by the backend."""


class BackendWriteError(RuntimeError):
    """Raised when a backend cannot accept a complete UART payload."""

    def __init__(self, message: str, *, bytes_accepted: int | None) -> None:
        super().__init__(message)
        self.bytes_accepted = bytes_accepted


class BackendEventSource(Protocol):
    """Asynchronous FIFO source of normalized events from one backend connection."""

    @property
    def info(self) -> BackendInfo:
        """Return immutable identity and physical capability information."""

    @property
    def segment_id(self) -> int:
        """Return the session-local segment ID assigned to this source."""

    @property
    def segment(self) -> SegmentContext | None:
        """Return timestamp provenance once the source origin is established."""

    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
        """Return the next FIFO event, or ``None`` for an ordinary read timeout."""
