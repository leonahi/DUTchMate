"""Validate provider observations while deriving report provenance from native evidence."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass

from dutchmate_debug_agent.analysis_request import AnalysisRequest
from dutchmate_debug_agent.coding_context import CodingContextLimits, _path, _text

_REPORT_BYTES = 128 * 1024
_REPORT_ENTRIES = 50
_REFERENCES = 8
_TEXT_BYTES = 4096
_DIGEST = re.compile(r"[0-9a-f]{64}\Z")


@dataclass(frozen=True, slots=True)
class EvidenceReference:
    kind: str
    session_id: str | None = None
    ordinal: int | None = None
    event_index: int | None = None
    attempt_id: str | None = None
    path: str | None = None
    commit: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    base_commit: str | None = None
    head_commit: str | None = None
    hunk_index: int | None = None


@dataclass(frozen=True, slots=True)
class ReportStatement:
    text: str
    references: tuple[EvidenceReference, ...]


@dataclass(frozen=True, slots=True)
class ReportInference:
    text: str
    basis: tuple[EvidenceReference, ...]
    uncertainty: str


@dataclass(frozen=True, slots=True)
class RecommendedSourceArea:
    path: str | None
    symbol: str | None


@dataclass(frozen=True, slots=True)
class RecommendedEvidence:
    action: str
    bounds: str


@dataclass(frozen=True, slots=True)
class ProvenanceWarning:
    session_id: str
    code: str


@dataclass(frozen=True, slots=True)
class StoredFirstError:
    session_id: str
    detected_pattern_index: int | None
    segment_id: int | None
    ingestion_index: int | None
    line_index_in_event: int | None


@dataclass(frozen=True, slots=True)
class ReportMetadata:
    request_schema_version: int
    context_schema_version: int | None
    session_ids: tuple[str, ...]
    effective_limits: dict[str, object]
    context_truncated: bool
    source_commits: tuple[str, ...]
    provider_id: str
    model_id: str
    remote: bool
    request_digest: str
    first_errors: tuple[StoredFirstError, ...]
    provenance_warnings: tuple[ProvenanceWarning, ...]


@dataclass(frozen=True, slots=True)
class DebugReport:
    schema_version: int
    observations: tuple[ReportStatement, ...]
    inferences: tuple[ReportInference, ...]
    unknowns: tuple[str, ...]
    recommended_next_evidence: tuple[RecommendedEvidence, ...]
    recommended_source_areas: tuple[RecommendedSourceArea, ...]
    first_meaningful_failure: ReportStatement | None
    metadata: ReportMetadata


def _object(
    raw: object,
    *,
    field: str,
    required: set[str],
    optional: set[str] | frozenset[str] = frozenset(),
) -> dict[str, object]:
    if not isinstance(raw, dict) or not all(isinstance(key, str) for key in raw):
        raise ValueError(f"{field} must be an object")
    difference = (required - raw.keys()) | (raw.keys() - required - optional)
    if difference:
        raise ValueError(f"{field} has missing or unexpected fields: {sorted(difference)}")
    return raw


def _entries(
    raw: object, *, field: str, maximum: int = _REPORT_ENTRIES, required: bool = False
) -> list[object]:
    if not isinstance(raw, list) or len(raw) > maximum or (required and not raw):
        raise ValueError(f"{field} must contain {int(required)}..{maximum} entries")
    return raw


def _integer(raw: object, *, field: str) -> int:
    if not isinstance(raw, int) or isinstance(raw, bool) or raw < 0:
        raise ValueError(f"{field} must be a nonnegative integer")
    return raw


def _reference(raw: object, request: AnalysisRequest) -> EvidenceReference:
    item = _object(
        raw,
        field="reference",
        required={"kind"},
        optional={
            "session_id",
            "ordinal",
            "event_index",
            "attempt_id",
            "path",
            "commit",
            "start_line",
            "end_line",
            "base_commit",
            "head_commit",
            "hunk_index",
        },
    )
    kind = item["kind"]
    keys = {
        "session": {"kind", "session_id"},
        "first_error": {"kind", "session_id"},
        "uart": {"kind", "session_id", "ordinal"},
        "hardware": {"kind", "session_id", "event_index"},
        "tx_outcome": {"kind", "session_id", "attempt_id"},
        "source": {"kind", "path", "commit", "start_line", "end_line"},
        "diff": {"kind", "path", "base_commit", "head_commit", "hunk_index"},
    }
    if not isinstance(kind, str) or kind not in keys or set(item) != keys[kind]:
        raise ValueError("reference has invalid kind or coordinates")
    if kind in {"session", "first_error", "uart", "hardware", "tx_outcome"}:
        session_id = item["session_id"]
        if not isinstance(session_id, str):
            raise ValueError("reference session_id is invalid")
        evidence = next(
            (part for part in request.session_evidence if part.facts.session_id == session_id),
            None,
        )
        if evidence is None:
            raise ValueError("reference cites an unselected session")
        if kind == "first_error" and evidence.facts.first_error is None:
            raise ValueError("reference cites a missing first_error")
        if kind == "uart":
            ordinal = _integer(item["ordinal"], field="ordinal")
            if not any(line.ordinal == ordinal for line in evidence.uart_excerpts):
                raise ValueError("reference cites an unselected UART line")
            return EvidenceReference(kind="uart", session_id=session_id, ordinal=ordinal)
        if kind == "hardware":
            index = _integer(item["event_index"], field="event_index")
            if not any(event.event_index == index for event in evidence.hardware_excerpts):
                raise ValueError("reference cites an unselected hardware event")
            return EvidenceReference(kind="hardware", session_id=session_id, event_index=index)
        if kind == "tx_outcome":
            attempt_id = _text(item["attempt_id"], field="attempt_id", maximum=256)
            if not any(outcome.attempt_id == attempt_id for outcome in evidence.tx_outcomes):
                raise ValueError("reference cites an unselected UART TX outcome")
            return EvidenceReference(
                kind="tx_outcome", session_id=session_id, attempt_id=attempt_id
            )
        return EvidenceReference(kind=kind, session_id=session_id)
    context = request.coding_context
    if context is None:
        raise ValueError("source reference requires selected Coding Agent context")
    path = _path(item["path"], field="reference.path", limits=CodingContextLimits())
    if kind == "source":
        commit = _text(item["commit"], field="reference.commit", maximum=64)
        start = _integer(item["start_line"], field="start_line")
        end = _integer(item["end_line"], field="end_line")
        if (
            start == 0
            or end < start
            or not any(
                excerpt.kind in {"source", "configuration"}
                and excerpt.path == path
                and excerpt.commit == commit
                and excerpt.start_line is not None
                and excerpt.end_line is not None
                and excerpt.start_line <= start <= end <= excerpt.end_line
                for excerpt in context.excerpts
            )
        ):
            raise ValueError("source reference lies outside selected excerpt")
        return EvidenceReference(
            kind="source",
            path=path,
            commit=commit,
            start_line=start,
            end_line=end,
        )
    base = _text(item["base_commit"], field="base_commit", maximum=64)
    head = _text(item["head_commit"], field="head_commit", maximum=64)
    index = _integer(item["hunk_index"], field="hunk_index")
    if not any(
        excerpt.kind == "diff"
        and excerpt.path == path
        and excerpt.base_commit == base
        and excerpt.head_commit == head
        and index < len(excerpt.hunks)
        for excerpt in context.excerpts
    ):
        raise ValueError("diff reference lies outside selected excerpt")
    return EvidenceReference(
        kind="diff",
        path=path,
        base_commit=base,
        head_commit=head,
        hunk_index=index,
    )


def _references(raw: object, request: AnalysisRequest) -> tuple[EvidenceReference, ...]:
    return tuple(
        _reference(entry, request)
        for entry in _entries(raw, field="references", maximum=_REFERENCES, required=True)
    )


def _statement(raw: object, request: AnalysisRequest) -> ReportStatement:
    item = _object(raw, field="statement", required={"text", "references"})
    return ReportStatement(
        text=_text(item["text"], field="statement.text", maximum=_TEXT_BYTES),
        references=_references(item["references"], request),
    )


def _inference(raw: object, request: AnalysisRequest) -> ReportInference:
    item = _object(raw, field="inference", required={"text", "basis", "uncertainty"})
    return ReportInference(
        text=_text(item["text"], field="inference.text", maximum=_TEXT_BYTES),
        basis=_references(item["basis"], request),
        uncertainty=_text(item["uncertainty"], field="inference.uncertainty", maximum=_TEXT_BYTES),
    )


def _source_area(raw: object) -> RecommendedSourceArea:
    item = _object(raw, field="source area", required=set(), optional={"path", "symbol"})
    if not item:
        raise ValueError("source area needs a path or symbol")
    return RecommendedSourceArea(
        path=_path(item["path"], field="source area.path", limits=CodingContextLimits())
        if "path" in item
        else None,
        symbol=_text(item["symbol"], field="source area.symbol", maximum=256)
        if "symbol" in item
        else None,
    )


def _recommended_evidence(raw: object) -> RecommendedEvidence:
    item = _object(raw, field="recommended_next_evidence", required={"action", "bounds"})
    return RecommendedEvidence(
        action=_text(item["action"], field="next_evidence.action", maximum=_TEXT_BYTES),
        bounds=_text(item["bounds"], field="next_evidence.bounds", maximum=_TEXT_BYTES),
    )


def _warnings(request: AnalysisRequest) -> tuple[ProvenanceWarning, ...]:
    warnings: list[ProvenanceWarning] = []
    for part in request.session_evidence:
        session_id = part.facts.session_id
        loss = part.facts.integrity.loss_status
        if loss != "none_reported":
            code = "uart_loss_not_observable" if loss == "not_observable" else "uart_loss_reported"
            warnings.append(ProvenanceWarning(session_id, code))
        if part.facts.truncated or part.context_truncated:
            warnings.append(ProvenanceWarning(session_id, "evidence_truncated"))
        if part.facts.interrupted:
            warnings.append(ProvenanceWarning(session_id, "capture_interrupted"))
        if len(part.facts.segments) > 1:
            warnings.append(ProvenanceWarning(session_id, "cross_segment_timing"))
        if any(_has_host_timestamp(segment) for segment in part.facts.segments):
            warnings.append(ProvenanceWarning(session_id, "host_timestamp"))
        if part.baseline_context is not None and part.baseline_context.timing_comparable is False:
            warnings.append(ProvenanceWarning(session_id, "baseline_timing_incomparable"))
    return tuple(warnings)


def _has_host_timestamp(segment: dict[str, object]) -> bool:
    timestamp = segment.get("timestamp")
    return isinstance(timestamp, dict) and timestamp.get("source") == "host"


def validate_report_response(
    request: AnalysisRequest,
    raw: object,
    *,
    provider_id: str,
    model_id: str,
    remote: bool,
    request_digest: str,
) -> DebugReport:
    """Validate model output and attach metadata derived only from the request."""

    try:
        encoded = json.dumps(raw, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError) as exc:
        raise ValueError("report response must be JSON-compatible") from exc
    if len(encoded) > _REPORT_BYTES:
        raise ValueError("report response exceeds byte limit")
    item = _object(
        raw,
        field="report",
        required={
            "schema_version",
            "observations",
            "inferences",
            "unknowns",
            "recommended_next_evidence",
            "recommended_source_areas",
        },
        optional={"first_meaningful_failure"},
    )
    if type(item["schema_version"]) is not int or item["schema_version"] != 1:
        raise ValueError("unsupported report schema_version")
    if not isinstance(remote, bool) or not _DIGEST.fullmatch(request_digest):
        raise ValueError("report provider metadata is invalid")
    provider_id = _text(provider_id, field="provider_id", maximum=256)
    model_id = _text(model_id, field="model_id", maximum=256)
    observations = tuple(
        _statement(entry, request) for entry in _entries(item["observations"], field="observations")
    )
    inferences = tuple(
        _inference(entry, request) for entry in _entries(item["inferences"], field="inferences")
    )
    unknowns = tuple(
        _text(entry, field="unknowns", maximum=_TEXT_BYTES)
        for entry in _entries(item["unknowns"], field="unknowns")
    )
    next_evidence = tuple(
        _recommended_evidence(entry)
        for entry in _entries(item["recommended_next_evidence"], field="recommended_next_evidence")
    )
    source_areas = tuple(
        _source_area(entry)
        for entry in _entries(item["recommended_source_areas"], field="recommended_source_areas")
    )
    advisory_raw = item.get("first_meaningful_failure")
    advisory = _statement(advisory_raw, request) if advisory_raw is not None else None
    if advisory is not None and all(ref.kind == "session" for ref in advisory.references):
        raise ValueError("first_meaningful_failure requires a specific evidence citation")
    context = request.coding_context
    commits = (
        tuple(
            dict.fromkeys(
                [
                    *([context.build.commit] if context.build is not None else []),
                    *(excerpt.commit or excerpt.head_commit for excerpt in context.excerpts),
                ]
            )
        )
        if context is not None
        else ()
    )
    metadata = ReportMetadata(
        request_schema_version=request.schema_version,
        context_schema_version=context.schema_version if context is not None else None,
        session_ids=request.session_ids,
        effective_limits={
            "coding_context": asdict(request.coding_context_limits),
            "session_evidence": [asdict(part.limits) for part in request.session_evidence],
            "report_bytes": _REPORT_BYTES,
            "report_entries_per_field": _REPORT_ENTRIES,
            "references_per_statement": _REFERENCES,
            "report_text_bytes": _TEXT_BYTES,
        },
        context_truncated=request.context_truncated,
        source_commits=tuple(commit for commit in commits if commit is not None),
        provider_id=provider_id,
        model_id=model_id,
        remote=remote,
        request_digest=request_digest,
        first_errors=tuple(
            StoredFirstError(
                session_id=part.facts.session_id,
                detected_pattern_index=part.facts.first_error.detected_pattern_index
                if part.facts.first_error is not None
                else None,
                segment_id=part.facts.first_error.segment_id
                if part.facts.first_error is not None
                else None,
                ingestion_index=part.facts.first_error.ingestion_index
                if part.facts.first_error is not None
                else None,
                line_index_in_event=part.facts.first_error.line_index_in_event
                if part.facts.first_error is not None
                else None,
            )
            for part in request.session_evidence
        ),
        provenance_warnings=_warnings(request),
    )
    return DebugReport(
        schema_version=1,
        observations=observations,
        inferences=inferences,
        unknowns=unknowns,
        recommended_next_evidence=next_evidence,
        recommended_source_areas=source_areas,
        first_meaningful_failure=advisory,
        metadata=metadata,
    )
