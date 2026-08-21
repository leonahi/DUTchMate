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
LossStatus: TypeAlias = Literal["none_reported", "loss_reported", "not_observable"]


@dataclass(frozen=True, slots=True)
class UartSendCapabilityPolicy:
    """Software policy controlling whether backend UART transmission is usable."""

    tx_policy_enabled: bool
    source: Literal["hardware.uart.tx_enabled"] = "hardware.uart.tx_enabled"

    def __post_init__(self) -> None:
        if not isinstance(self.tx_policy_enabled, bool):
            raise ValueError("UART-send TX policy must be a boolean")
        if self.source != "hardware.uart.tx_enabled":
            raise ValueError("UART-send TX policy source is invalid")


@dataclass(frozen=True, slots=True)
class BackendCapabilityPolicy:
    """Host policy snapshot applied to backend-reported capabilities."""

    uart_send: UartSendCapabilityPolicy


@dataclass(frozen=True, slots=True)
class UartIntegrity:
    """What the selected backend can report about upstream UART loss."""

    loss_status: LossStatus
    observation_scope: Literal["debug_helper_rx_buffer"] | None
    dropped_bytes: int | None

    def __post_init__(self) -> None:
        if self.loss_status not in {
            "none_reported",
            "loss_reported",
            "not_observable",
        }:
            raise ValueError("UART integrity loss status is invalid")
        if self.dropped_bytes is not None and (
            isinstance(self.dropped_bytes, bool)
            or not isinstance(self.dropped_bytes, int)
            or self.dropped_bytes < 0
        ):
            raise ValueError("UART integrity dropped bytes must be non-negative or null")
        if self.loss_status == "not_observable":
            if self.observation_scope is not None or self.dropped_bytes is not None:
                raise ValueError("not-observable UART integrity cannot claim loss telemetry")
            return
        if self.observation_scope != "debug_helper_rx_buffer":
            raise ValueError("observable UART integrity requires the Debug Helper RX scope")
        if self.loss_status == "none_reported" and self.dropped_bytes != 0:
            raise ValueError("none-reported UART integrity requires zero dropped bytes")


@dataclass(frozen=True, slots=True)
class BackendSnapshot:
    """Backend identity, effective policy, timing, and integrity for one segment."""

    info: BackendInfo
    capabilities: frozenset[BackendCapability]
    capability_policy: BackendCapabilityPolicy
    segment: SegmentContext | None
    integrity: UartIntegrity

    def __post_init__(self) -> None:
        effective = apply_capability_policy(
            self.info.capabilities,
            self.capability_policy,
        )
        if self.capabilities != effective:
            raise ValueError("backend snapshot capabilities do not match applied policy")
        if self.info.mode == "basic" and self.integrity.loss_status != "not_observable":
            raise ValueError("Basic backend integrity must be not_observable")
        if self.info.mode == "enhanced" and self.integrity.loss_status == "not_observable":
            raise ValueError("Enhanced backend integrity must describe its RX buffer observer")


def apply_capability_policy(
    backend_capabilities: frozenset[BackendCapability],
    policy: BackendCapabilityPolicy,
) -> frozenset[BackendCapability]:
    """Filter backend support through the shared host capability policy."""

    capabilities = set(backend_capabilities)
    if not policy.uart_send.tx_policy_enabled:
        capabilities.discard("uart_send")
    return frozenset(capabilities)


def integrity_for_backend(mode: BackendMode) -> UartIntegrity:
    """Return the initial UART-loss observation state for a backend mode."""

    if mode == "basic":
        return UartIntegrity(
            loss_status="not_observable",
            observation_scope=None,
            dropped_bytes=None,
        )
    return UartIntegrity(
        loss_status="none_reported",
        observation_scope="debug_helper_rx_buffer",
        dropped_bytes=0,
    )


class BackendDisconnectedError(RuntimeError):
    """Raised when the selected backend connection is lost."""


class BackendInputError(RuntimeError):
    """Raised when a backend emits malformed or otherwise invalid input."""

    error = "backend_input_error"
    end_reason = "backend_input_error"


class BackendCapabilityError(RuntimeError):
    """Raised when an operation is disabled or unsupported by the backend."""


class BackendWriteError(RuntimeError):
    """Raised when a backend cannot accept a complete UART payload."""

    def __init__(
        self,
        message: str,
        *,
        bytes_accepted: int | None,
        error: str = "hardware_fault",
    ) -> None:
        super().__init__(message)
        self.bytes_accepted = bytes_accepted
        self.error = error


@dataclass(frozen=True, slots=True)
class BackendUartSendResult:
    """Complete backend acceptance of one UART payload."""

    bytes_accepted: int
    device_timestamp_us: int | None = None


class UartSender(Protocol):
    """Backend-neutral port for complete UART payload transmission."""

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        """Submit every payload byte or raise a backend write error."""


class DeviceControlError(RuntimeError):
    """Raised when a backend rejects or cannot complete a semantic control operation."""

    def __init__(self, *, error: str, detail: str) -> None:
        super().__init__(detail)
        self.error = error
        self.detail = detail


class DeviceControl(Protocol):
    """Backend-neutral semantic DUT and GPIO control operations."""

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        role: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        """Configure one physical control channel and return device time."""

    def reset_dut(self, *, pulse_ms: int) -> int | None:
        """Pulse the DUT reset line and return device time."""

    def set_boot_mode(self, *, mode: str) -> int | None:
        """Set DUT boot mode and return device time."""


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
