"""Normalized source, health, and reconnect boundaries used by continuous recording.

Names remain stable for backend/service consumers; finite capture execution and
schema-v1 recording have been retired from the runtime.
"""

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

from dutchmate_core.backends.contracts import BackendEvent, BackendSnapshot, UartIntegrity
from dutchmate_core.dut_vio import DutVioObservation


class CaptureEventSource(Protocol):
    """Blocking source of normalized events for the continuous recorder."""

    def read_event(self) -> BackendEvent | None:
        """Return the next normalized event, or ``None`` after read inactivity."""


@runtime_checkable
class BufferedCaptureEventSource(CaptureEventSource, Protocol):
    """Optional polling boundary for opportunistic durable admission batches."""

    def read_event_nowait(self) -> BackendEvent | None:
        """Take an already queued event without waiting for additional input."""


@runtime_checkable
class BackendObservationInitializer(Protocol):
    """Optional per-source setup after desired controls have been acknowledged."""

    def initialize_observation(self) -> bool:
        """Return False only for an explicit, nonterminal setup rejection."""


@dataclass(frozen=True, slots=True)
class CaptureSourceHealth:
    """Immutable current-source connection, integrity, and replacement projection."""

    connected: bool
    integrity: UartIntegrity | None
    backend_snapshot: BackendSnapshot | None = None
    connection_generation: int = 0
    dut_vio_observation: DutVioObservation | None = None
    dut_vio_setup_rejected: bool = False

    def __post_init__(self) -> None:
        if self.connection_generation < 0:
            raise ValueError("source connection generation must be non-negative")


@runtime_checkable
class CaptureSourceMonitor(Protocol):
    """Optional current-source health observation boundary."""

    def capture_source_health(self) -> CaptureSourceHealth:
        """Return one immutable current-source health snapshot."""


@dataclass(frozen=True, slots=True)
class ReconnectedCaptureSource:
    """A validated replacement source and its immutable backend snapshot."""

    source: CaptureEventSource
    backend_snapshot: BackendSnapshot


class ReconnectLifecycle(Protocol):
    """Shutdown boundary for the service-owned continuous reconnect supervisor."""

    def close(self) -> None:
        """Stop reopen attempts and wait for candidate cleanup."""
