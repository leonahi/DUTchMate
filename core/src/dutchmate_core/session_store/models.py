"""Public session-store data models and lifecycle errors."""

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dutchmate_core.backends.contracts import (
    BackendCapabilityPolicy,
    BackendMode,
    SegmentContext,
    UartIntegrity,
)
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES

SessionState = Literal["active", "completed", "failed", "abandoned"]
SessionWorkflow = Literal["capture", "boot_test", "wait_pattern"]


@dataclass(frozen=True, slots=True)
class SessionPaths:
    """Filesystem paths for the required Phase 1 session files."""

    root: Path
    metadata: Path
    uart_raw: Path
    uart_events: Path
    hardware_events: Path
    detected_patterns: Path
    terminal_reserve: Path


@dataclass(frozen=True, slots=True)
class SessionHandle:
    """Reference to a created debug session."""

    session_id: str
    paths: SessionPaths


@dataclass(frozen=True, slots=True)
class SessionRecoveryDiagnostic:
    """One non-fatal startup-recovery observation for a stored session."""

    session_id: str
    code: str
    detail: str


@dataclass(frozen=True, slots=True)
class SessionRecoveryResult:
    """Sessions abandoned at startup plus non-fatal compatibility diagnostics."""

    recovered_session_ids: tuple[str, ...] = ()
    diagnostics: tuple[SessionRecoveryDiagnostic, ...] = ()


class SessionRecoveryError(RuntimeError):
    """Raised when stale native session metadata cannot be safely replaced."""


class EvidenceQuotaExceeded(RuntimeError):
    """Raised after an evidence unit is rejected and its session is terminalized."""

    def __init__(self, truncation: dict[str, object]) -> None:
        self.truncation = truncation.copy()
        super().__init__("session evidence budget would be exceeded")


@dataclass(frozen=True, slots=True)
class MatchExcerpt:
    """Bounded exact-byte evidence surrounding one detected pattern."""

    start_byte: int
    end_byte: int
    text: str
    raw_b64: str
    excerpt_truncated: bool


@dataclass(frozen=True, slots=True)
class FirstError:
    """Reference-bearing view of the first stored failure-pattern match."""

    pattern: str
    detected_pattern_index: int
    segment_id: int
    timestamp_us: int
    channel: int
    ingestion_index: int
    line_index_in_event: int
    line_start_ingestion_index: int
    line_start_event_offset: int
    line_end_ingestion_index: int
    line_end_event_offset: int
    total_line_bytes: int
    match_start_byte: int
    match_end_byte: int
    match_excerpt: MatchExcerpt


@dataclass(frozen=True, slots=True)
class LineProcessing:
    """Bounded derived-line processing status for one session."""

    status: Literal["complete", "limit_exceeded"] = "complete"
    max_line_bytes: int = MAX_UART_LINE_BYTES
    oversized_line_count: int = 0

    def __post_init__(self) -> None:
        if self.max_line_bytes != MAX_UART_LINE_BYTES:
            raise ValueError("line-processing max_line_bytes must be 65536")
        if (
            isinstance(self.oversized_line_count, bool)
            or not isinstance(self.oversized_line_count, int)
            or self.oversized_line_count < 0
        ):
            raise ValueError("oversized-line count must be a non-negative integer")
        if (self.status == "complete") != (self.oversized_line_count == 0):
            raise ValueError("line-processing status/count must agree")


@dataclass(frozen=True, slots=True)
class SessionSummary:
    """Compact summary of a debug session for workflow/API responses."""

    session_id: str
    started_at: str
    command: str
    truncated: bool
    interrupted: bool
    resumed: bool
    overflow: bool
    baseline: bool
    firmware: str | None
    device: str | None
    segment_count: int
    backend_mode: BackendMode | None = None
    port: str | None = None
    backend_capabilities: tuple[str, ...] = ()
    capabilities: tuple[str, ...] = ()
    capability_policy: BackendCapabilityPolicy | None = None
    integrity: UartIntegrity | None = None
    segment_contexts: tuple[SegmentContext, ...] = ()
    first_error: FirstError | None = None
    line_processing: LineProcessing = LineProcessing()
    schema_version: int = 0
    state: SessionState | None = None
    workflow: SessionWorkflow | None = None
    duration_s: float | None = None
    reconnect_timeout_s: float | None = None
    ended_at: str | None = None
    end_reason: str | None = None
    error: dict[str, object] | None = None
    truncation: dict[str, object] | None = None
