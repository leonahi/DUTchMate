"""Disabled-by-default provider selection and inspectable submission boundary."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
from collections.abc import Mapping
from copy import deepcopy
from dataclasses import asdict, dataclass, replace
from typing import Protocol

from dutchmate_debug_agent.analysis_request import AnalysisRequest
from dutchmate_debug_agent.coding_context import CodingContextLimits, _text
from dutchmate_debug_agent.evidence_package import EvidenceLimits
from dutchmate_debug_agent.report_schema import DebugReport, validate_report_response

_REQUEST_BYTES = 4 * 1024 * 1024


class AnalysisUnavailable(Exception):
    """Analysis-only failure; never a capture or storage failure."""


class ProviderAdapter(Protocol):
    provider_id: str
    remote: bool

    async def analyze(self, payload: bytes, *, model_id: str) -> object: ...


@dataclass(frozen=True, slots=True)
class ProviderSelection:
    provider_id: str = "disabled"
    model_id: str | None = None
    remote_processing_opt_in: bool = False
    timeout_s: float = 60.0


@dataclass(frozen=True, slots=True)
class SessionTruncation:
    session_id: str
    context_truncated: bool
    omitted_uart_lines: int
    omitted_hardware_events: int


@dataclass(frozen=True, slots=True)
class AppliedLimits:
    coding_context: CodingContextLimits
    session_evidence: tuple[EvidenceLimits, ...]
    request_bytes: int


@dataclass(frozen=True, slots=True)
class AnalysisManifest:
    session_ids: tuple[str, ...]
    source_paths: tuple[str, ...]
    applied_limits: AppliedLimits
    context_truncated: bool
    session_truncation: tuple[SessionTruncation, ...]
    total_text_bytes: int
    provider_id: str
    model_id: str
    remote: bool
    provider_timeout_s: float
    request_digest: str
    manifest_digest: str


@dataclass(frozen=True, slots=True)
class PreparedAnalysis:
    manifest: AnalysisManifest
    payload: bytes
    _request: AnalysisRequest
    _adapter: ProviderAdapter


def prepare_analysis(
    request: AnalysisRequest,
    selection: ProviderSelection,
    adapters: Mapping[str, ProviderAdapter],
) -> PreparedAnalysis:
    """Freeze the exact request and expose a manifest before any provider call."""

    if not isinstance(selection, ProviderSelection) or selection.provider_id == "disabled":
        raise AnalysisUnavailable("AI analysis is disabled")
    if not isinstance(selection.remote_processing_opt_in, bool):
        raise AnalysisUnavailable("remote-processing opt-in must be explicit")
    if (
        isinstance(selection.timeout_s, bool)
        or not isinstance(selection.timeout_s, int | float)
        or not 0 < selection.timeout_s <= 300
    ):
        raise AnalysisUnavailable("provider timeout must be within 0..300 seconds")
    try:
        provider_id = _text(selection.provider_id, field="provider_id", maximum=256)
        model_id = _text(selection.model_id, field="model_id", maximum=256)
    except ValueError:
        raise AnalysisUnavailable("provider selection is invalid") from None
    adapter = adapters.get(provider_id)
    if (
        adapter is None
        or adapter.provider_id != provider_id
        or not isinstance(adapter.remote, bool)
    ):
        raise AnalysisUnavailable("selected provider is not registered")
    if adapter.remote and not selection.remote_processing_opt_in:
        raise AnalysisUnavailable("remote processing requires explicit opt-in")
    snapshot = deepcopy(request)
    try:
        payload = json.dumps(
            asdict(snapshot),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, UnicodeError):
        raise AnalysisUnavailable("analysis request cannot be serialized") from None
    if len(payload) > _REQUEST_BYTES:
        raise AnalysisUnavailable("analysis request byte limit exceeded")
    context = snapshot.coding_context
    manifest = AnalysisManifest(
        session_ids=snapshot.session_ids,
        source_paths=context.source_paths if context is not None else (),
        applied_limits=AppliedLimits(
            coding_context=snapshot.coding_context_limits,
            session_evidence=tuple(part.limits for part in snapshot.session_evidence),
            request_bytes=_REQUEST_BYTES,
        ),
        context_truncated=snapshot.context_truncated,
        session_truncation=tuple(
            SessionTruncation(
                session_id=part.facts.session_id,
                context_truncated=part.context_truncated,
                omitted_uart_lines=part.omitted_uart_lines,
                omitted_hardware_events=part.omitted_hardware_events,
            )
            for part in snapshot.session_evidence
        ),
        total_text_bytes=len(payload),
        provider_id=provider_id,
        model_id=model_id,
        remote=adapter.remote,
        provider_timeout_s=float(selection.timeout_s),
        request_digest=hashlib.sha256(payload).hexdigest(),
        manifest_digest="",
    )
    review_fields = asdict(manifest)
    del review_fields["manifest_digest"]
    manifest = replace(
        manifest,
        manifest_digest=hashlib.sha256(
            json.dumps(review_fields, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest(),
    )
    return PreparedAnalysis(
        manifest=manifest,
        payload=payload,
        _request=snapshot,
        _adapter=adapter,
    )


async def submit_analysis(prepared: PreparedAnalysis) -> DebugReport:
    """Submit only the prepared payload to its fixed provider, then validate output."""

    try:
        raw = await asyncio.wait_for(
            prepared._adapter.analyze(
                prepared.payload,
                model_id=prepared.manifest.model_id,
            ),
            timeout=prepared.manifest.provider_timeout_s,
        )
    except (TimeoutError, asyncio.TimeoutError):
        raise AnalysisUnavailable("selected provider timed out") from None
    except Exception:
        raise AnalysisUnavailable("selected provider is unavailable") from None
    try:
        return validate_report_response(
            prepared._request,
            raw,
            provider_id=prepared.manifest.provider_id,
            model_id=prepared.manifest.model_id,
            remote=prepared.manifest.remote,
            request_digest=prepared.manifest.request_digest,
        )
    except ValueError:
        raise AnalysisUnavailable("selected provider returned an invalid response") from None


async def submit_approved_analysis(
    prepared: PreparedAnalysis,
    *,
    approved_digest: str,
) -> DebugReport:
    """Submit only when the caller approved this exact prepared request."""

    if not isinstance(approved_digest, str) or not hmac.compare_digest(
        approved_digest, prepared.manifest.manifest_digest
    ):
        raise AnalysisUnavailable("manifest digest mismatch")
    return await submit_analysis(prepared)
