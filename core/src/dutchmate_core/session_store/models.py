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
SessionCompatibility = Literal["native", "legacy_read_only"]


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


class SessionPersistenceError(RuntimeError):
    """Raised when durable session evidence cannot be read or written."""

    error = "persistence_fault"

    def __init__(
        self,
        *,
        operation: str,
        path: Path,
        detail: str,
        terminalization_safe: bool = True,
    ) -> None:
        self.operation = operation
        self.path = path
        self.terminalization_safe = terminalization_safe
        super().__init__(f"session persistence {operation} failed for {path.name}: {detail}")


class SessionQueryError(RuntimeError):
    """Raised when a bounded session query cannot produce a valid projection."""

    def __init__(
        self,
        *,
        error: Literal[
            "not_found",
            "persistence_fault",
            "unsupported_session_schema",
        ],
        operation: Literal["list_sessions", "get_session", "get_logs"],
        detail: str,
        session_id: str | None = None,
        detected_schema_version: int | None = None,
    ) -> None:
        self.error = error
        self.operation = operation
        self.session_id = session_id
        self.detected_schema_version = detected_schema_version
        super().__init__(detail)


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
    wait_pattern: str | None = None
    match_mode: Literal["literal"] | None = None
    case_sensitive: bool | None = None
    timeout_s: float | None = None
    matched: bool | None = None
    detected_pattern_index: int | None = None


@dataclass(frozen=True, slots=True)
class FirstErrorReference:
    """Compact first-error location used by bounded session list items."""

    pattern: str
    detected_pattern_index: int
    segment_id: int
    timestamp_us: int
    channel: int
    ingestion_index: int
    line_index_in_event: int


@dataclass(frozen=True, slots=True)
class NativeSessionListItem:
    """Bounded native lifecycle projection for one session list item."""

    session_id: str
    started_at: str
    state: SessionState
    workflow: SessionWorkflow
    ended_at: str | None
    end_reason: str | None
    backend_mode: BackendMode
    baseline: bool
    truncated: bool
    truncation: dict[str, object] | None
    interrupted: bool
    resumed: bool
    segment_count: int
    integrity: UartIntegrity
    line_processing: LineProcessing
    first_error: FirstErrorReference | None
    schema_version: Literal[1] = 1
    compatibility: Literal["native"] = "native"


@dataclass(frozen=True, slots=True)
class LegacySessionListItem:
    """Bounded read-only identity projection for one unversioned session."""

    session_id: str
    started_at: str
    command: str
    firmware: str | None
    device: str | None
    schema_version: Literal[0] = 0
    compatibility: Literal["legacy_read_only"] = "legacy_read_only"
    migration_required: Literal[True] = True
    migration_available: Literal[False] = False


SessionListItem = NativeSessionListItem | LegacySessionListItem


@dataclass(frozen=True, slots=True)
class SessionListPage:
    """One stable newest-first page of bounded session list items."""

    items: tuple[SessionListItem, ...]
    next_cursor: str | None


@dataclass(frozen=True, slots=True)
class SessionArtifact:
    """Logical size and optional record count for one session artifact."""

    name: str
    bytes: int
    records: int | None


@dataclass(frozen=True, slots=True)
class EvidenceTypeCount:
    """Bounded count for one detected-pattern or hardware-event type."""

    type: str
    count: int


@dataclass(frozen=True, slots=True)
class NativeSessionDetail:
    """Bounded native session detail without expanded evidence arrays."""

    summary: NativeSessionListItem
    command: str
    duration_s: float | None
    reconnect_timeout_s: float
    error: dict[str, object] | None
    backend_identity: dict[str, object]
    backend_capabilities: tuple[str, ...]
    capabilities: tuple[str, ...]
    capability_policy: BackendCapabilityPolicy
    commanded_boot_mode: Literal["normal", "bootloader"] | None
    storage: dict[str, object]
    segments: tuple[dict[str, object], ...]
    first_error: FirstError | None
    pattern_counts: tuple[EvidenceTypeCount, ...]
    hardware_event_counts: tuple[EvidenceTypeCount, ...]
    unresolved_uart_tx_attempts: int
    artifacts: tuple[SessionArtifact, ...]
    wait_pattern: str | None = None
    match_mode: Literal["literal"] | None = None
    case_sensitive: bool | None = None
    timeout_s: float | None = None
    matched: bool | None = None
    detected_pattern_index: int | None = None


@dataclass(frozen=True, slots=True)
class LegacySessionDetail:
    """Bounded legacy identity and artifact-size compatibility projection."""

    summary: LegacySessionListItem
    artifacts: tuple[SessionArtifact, ...]


SessionDetail = NativeSessionDetail | LegacySessionDetail


@dataclass(frozen=True, slots=True)
class WaitPatternResult:
    """Terminal wait-pattern session plus its authoritative requested match."""

    summary: SessionSummary
    pattern: str
    matched: bool
    match: FirstError | None


SessionSelection = Literal["explicit", "active", "latest_terminal"]


@dataclass(frozen=True, slots=True)
class RecentLogLine:
    """One bounded complete or trailing UART line from replayed evidence."""

    segment_id: int
    channel: int
    timestamp_us: int
    ingestion_index: int
    line_index_in_event: int
    line_raw_b64: str
    line_text: str
    partial: bool = False


@dataclass(frozen=True, slots=True)
class OversizedLogLine:
    """Location-only descriptor for a replayed physical line over the limit."""

    segment_id: int
    channel: int
    ingestion_index: int
    line_index_in_event: int
    line_start_ingestion_index: int
    line_start_event_offset: int
    line_end_ingestion_index: int
    line_end_event_offset: int
    total_line_bytes: int
    terminated: bool
    timestamp_us: int


@dataclass(frozen=True, slots=True)
class RecentLogs:
    """Bounded recent UART replay plus session evidence-quality context."""

    session_selection: SessionSelection
    session_id: str
    active: bool
    snapshot_event_count: int
    complete_lines: tuple[RecentLogLine, ...]
    partial_lines: tuple[RecentLogLine, ...]
    oversized_lines: tuple[OversizedLogLine, ...]
    integrity: UartIntegrity
    line_processing: LineProcessing
    reconnect_timeout_s: float
    interrupted: bool
    resumed: bool
    storage: dict[str, object]
    truncated: bool
    truncation: dict[str, object] | None
    timestamp_provenance: tuple[dict[str, object], ...]
    omitted_complete_lines: int = 0
    omitted_partial_lines: int = 0
    omitted_oversized_lines: int = 0
    schema_version: Literal[1] = 1
