"""Bounded native session facts for eventual Debug Agent context assembly."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Literal

from dutchmate_core.backends.contracts import (
    BackendCapabilityPolicy,
    BackendMode,
    UartIntegrity,
)
from dutchmate_core.session_store.models import (
    CommandedBootMode,
    EvidenceTypeCount,
    FirstError,
    LegacySessionDetail,
    LineProcessing,
    SessionQueryError,
    SessionState,
    SessionWorkflow,
)
from dutchmate_core.session_store.store import SessionStore


@dataclass(frozen=True, slots=True)
class SessionFacts:
    """Native bounded session facts; UART and event excerpts are separate slices."""

    session_id: str
    schema_version: Literal[1]
    command: str
    duration_s: float | None
    started_at: str
    ended_at: str | None
    state: SessionState
    workflow: SessionWorkflow
    end_reason: str | None
    error: dict[str, object] | None
    backend_mode: BackendMode
    backend_identity: dict[str, object]
    backend_capabilities: tuple[str, ...]
    capabilities: tuple[str, ...]
    capability_policy: BackendCapabilityPolicy
    commanded_boot_mode: CommandedBootMode | None
    segments: tuple[dict[str, object], ...]
    reconnect_timeout_s: float
    integrity: UartIntegrity
    line_processing: LineProcessing
    truncated: bool
    truncation: dict[str, object] | None
    interrupted: bool
    resumed: bool
    storage: dict[str, object]
    first_error: FirstError | None
    pattern_counts: tuple[EvidenceTypeCount, ...]
    hardware_event_counts: tuple[EvidenceTypeCount, ...]
    unresolved_uart_tx_attempts: int
    baseline: bool


def load_session_facts(store: SessionStore, session_id: str) -> SessionFacts:
    """Load facts through the validated, schema-aware session-store query."""

    detail = store.get_session_detail(session_id)
    if isinstance(detail, LegacySessionDetail):
        raise SessionQueryError(
            error="unsupported_session_schema",
            operation="get_session",
            detail="Debug Agent evidence requires native session schema version 1",
            session_id=detail.summary.session_id,
            detected_schema_version=0,
        )

    summary = detail.summary
    return SessionFacts(
        session_id=summary.session_id,
        schema_version=summary.schema_version,
        command=detail.command,
        duration_s=detail.duration_s,
        started_at=summary.started_at,
        ended_at=summary.ended_at,
        state=summary.state,
        workflow=summary.workflow,
        end_reason=summary.end_reason,
        error=deepcopy(detail.error),
        backend_mode=summary.backend_mode,
        backend_identity=deepcopy(detail.backend_identity),
        backend_capabilities=detail.backend_capabilities,
        capabilities=detail.capabilities,
        capability_policy=detail.capability_policy,
        commanded_boot_mode=detail.commanded_boot_mode,
        segments=deepcopy(detail.segments),
        reconnect_timeout_s=detail.reconnect_timeout_s,
        integrity=summary.integrity,
        line_processing=summary.line_processing,
        truncated=summary.truncated,
        truncation=deepcopy(summary.truncation),
        interrupted=summary.interrupted,
        resumed=summary.resumed,
        storage=deepcopy(detail.storage),
        first_error=detail.first_error,
        pattern_counts=detail.pattern_counts,
        hardware_event_counts=detail.hardware_event_counts,
        unresolved_uart_tx_attempts=detail.unresolved_uart_tx_attempts,
        baseline=summary.baseline,
    )
