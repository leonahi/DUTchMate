"""Versioned, bounded request assembled without provider calls."""

from __future__ import annotations

from dataclasses import dataclass

from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.validation import validate_session_id
from dutchmate_debug_agent.coding_context import (
    CodingContext,
    CodingContextLimits,
    validate_coding_context,
)
from dutchmate_debug_agent.evidence_package import SessionEvidence, build_session_evidence


@dataclass(frozen=True, slots=True)
class AnalysisRequest:
    schema_version: int
    session_ids: tuple[str, ...]
    session_evidence: tuple[SessionEvidence, ...]
    coding_context: CodingContext | None
    coding_context_limits: CodingContextLimits
    total_excerpt_text_bytes: int
    context_truncated: bool


def build_analysis_request(
    store: SessionStore,
    session_ids: list[str] | tuple[str, ...],
    coding_context: object | None = None,
) -> AnalysisRequest:
    """Combine native evidence with optional validated caller context."""

    limits = CodingContextLimits()
    if (
        not isinstance(session_ids, (list, tuple))
        or not 1 <= len(session_ids) <= limits.session_ids
    ):
        raise ValueError("session_ids must contain 1..8 entries")
    ids = tuple(validate_session_id(value) for value in session_ids)
    if len(set(ids)) != len(ids):
        raise ValueError("session_ids must be distinct")
    context = validate_coding_context(coding_context) if coding_context is not None else None
    if context is not None and context.session_ids != ids:
        raise ValueError("Coding Agent context session_ids must exactly match the request")
    evidence = tuple(build_session_evidence(store, session_id) for session_id in ids)
    return AnalysisRequest(
        schema_version=1,
        session_ids=ids,
        session_evidence=evidence,
        coding_context=context,
        coding_context_limits=limits,
        total_excerpt_text_bytes=sum(part.uart_text_bytes for part in evidence)
        + (context.excerpt_text_bytes if context is not None else 0),
        context_truncated=any(part.context_truncated for part in evidence),
    )
