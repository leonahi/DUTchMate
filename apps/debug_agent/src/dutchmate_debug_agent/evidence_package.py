"""Deterministic, bounded excerpts from one validated native session."""

from __future__ import annotations

import binascii
import json
from dataclasses import dataclass

from dutchmate_core.session_store.store import SessionStore
from dutchmate_debug_agent.evidence_source import _evidence_fault, _read_stable_artifacts
from dutchmate_debug_agent.hardware_excerpts import (
    _EVENT_STRING_BYTES,
    _HARDWARE_EVENTS,
    HardwareEventExcerpt,
    UartTxOutcome,
    _HardwareSelector,
)
from dutchmate_debug_agent.session_facts import SessionFacts, _project_native_detail
from dutchmate_debug_agent.uart_excerpts import (
    _PATTERN_REFS_PER_LINE,
    _UART_LINES,
    _UART_TEXT_BYTES,
    UartExcerpt,
    _pattern_references,
    _UartSelector,
)


@dataclass(frozen=True, slots=True)
class EvidenceLimits:
    uart_lines: int = _UART_LINES
    uart_text_bytes: int = _UART_TEXT_BYTES
    hardware_events: int = _HARDWARE_EVENTS
    event_string_bytes: int = _EVENT_STRING_BYTES
    pattern_references_per_line: int = _PATTERN_REFS_PER_LINE


@dataclass(frozen=True, slots=True)
class SessionEvidence:
    facts: SessionFacts
    uart_excerpts: tuple[UartExcerpt, ...]
    hardware_excerpts: tuple[HardwareEventExcerpt, ...]
    tx_outcomes: tuple[UartTxOutcome, ...]
    successful_uart_tx_attempts: int
    limits: EvidenceLimits
    uart_text_bytes: int
    omitted_uart_lines: int
    omitted_hardware_events: int
    unresolved_first_error_line: bool
    context_truncated: bool


def build_session_evidence(store: SessionStore, session_id: str) -> SessionEvidence:
    """Assemble bounded, priority-selected evidence without changing stored facts."""

    detail, artifacts = _read_stable_artifacts(store, session_id)
    facts = _project_native_detail(detail)
    try:
        patterns = _pattern_references(artifacts["detected_patterns.json"])
        uart = _UartSelector(facts, patterns)
        uart.read(artifacts["uart_events.jsonl"])
        uart_excerpts, uart_bytes = uart.select()
        hardware = _HardwareSelector(facts.session_id)
        hardware.read(artifacts["hardware_events.jsonl"])
        hardware_excerpts, outcomes = hardware.select()
        if hardware.count != sum(item.count for item in facts.hardware_event_counts):
            raise ValueError("hardware event count changed during evidence selection")
        if hardware.unmatched_count != facts.unresolved_uart_tx_attempts:
            raise ValueError("unmatched UART TX count changed during evidence selection")
        if uart.oversized_count != facts.line_processing.oversized_line_count:
            raise ValueError("oversized UART line count disagrees with session metadata")
    except (UnicodeError, ValueError, json.JSONDecodeError, binascii.Error) as exc:
        raise _evidence_fault(session_id, str(exc)) from exc

    omitted_uart = uart.count - len(uart_excerpts)
    omitted_hardware = hardware.count - len(hardware_excerpts)
    unresolved_error = facts.first_error is not None and not uart.first_error_found
    trimmed_fields = any(event.truncated_fields for event in hardware_excerpts)
    trimmed_patterns = any(line.omitted_pattern_indexes for line in uart_excerpts)
    trimmed_outcomes = any(outcome.error_truncated for outcome in outcomes)
    return SessionEvidence(
        facts=facts,
        uart_excerpts=uart_excerpts,
        hardware_excerpts=hardware_excerpts,
        tx_outcomes=outcomes,
        successful_uart_tx_attempts=hardware.successful_count,
        limits=EvidenceLimits(),
        uart_text_bytes=uart_bytes,
        omitted_uart_lines=omitted_uart,
        omitted_hardware_events=omitted_hardware,
        unresolved_first_error_line=unresolved_error,
        context_truncated=bool(
            omitted_uart
            or omitted_hardware
            or unresolved_error
            or trimmed_fields
            or trimmed_patterns
            or trimmed_outcomes
        ),
    )
