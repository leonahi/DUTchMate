from __future__ import annotations

import asyncio
import hashlib
import json
from contextlib import suppress
from dataclasses import asdict, replace
from pathlib import Path

import pytest
from test_evidence_package import _append_lines, _native_session

from dutchmate_core.backends import UartIntegrity
from dutchmate_debug_agent.analysis_request import AnalysisRequest, build_analysis_request
from dutchmate_debug_agent.provider_boundary import (
    AnalysisUnavailable,
    ProviderSelection,
    prepare_analysis,
    submit_analysis,
)
from dutchmate_debug_agent.report_schema import validate_report_response


def _request(tmp_path: Path) -> AnalysisRequest:
    store, handle = _native_session(tmp_path)
    _append_lines(store, handle, ["BOOT\n", "ERROR boot\n"])
    store.complete_session(handle)
    context = {
        "schema_version": 1,
        "objective": "Explain the boot failure",
        "session_ids": [handle.session_id],
        "build": {
            "commit": "0123456789abcdef",
            "build_id": "debug-1",
            "board": "pico2",
            "configuration": "debug",
        },
        "excerpts": [
            {
                "kind": "source",
                "path": "src/boot.c",
                "commit": "0123456789abcdef",
                "start_line": 80,
                "end_line": 80,
                "text": "boot();\n",
            }
        ],
    }
    return build_analysis_request(store, [handle.session_id], context)


def _response(session_id: str) -> dict[str, object]:
    return {
        "schema_version": 1,
        "observations": [
            {
                "text": "The boot line reports an error.",
                "references": [{"kind": "uart", "session_id": session_id, "ordinal": 1}],
            }
        ],
        "inferences": [
            {
                "text": "Initialization may stop before READY.",
                "basis": [{"kind": "first_error", "session_id": session_id}],
                "uncertainty": "The capture does not show later execution.",
            }
        ],
        "unknowns": ["The regulator state was not captured."],
        "recommended_next_evidence": [
            {
                "action": "Capture regulator enable during boot.",
                "bounds": "One boot cycle; stop after 10 seconds.",
            }
        ],
        "recommended_source_areas": [{"path": "src/boot.c", "symbol": "boot"}],
        "first_meaningful_failure": {
            "text": "The error line is the first visible failure.",
            "references": [{"kind": "first_error", "session_id": session_id}],
        },
    }


def test_report_validates_citations_and_preserves_native_first_error(tmp_path: Path) -> None:
    request = _request(tmp_path)
    session_id = request.session_ids[0]
    original = request.session_evidence[0].facts.first_error
    report = validate_report_response(
        request,
        _response(session_id),
        provider_id="local",
        model_id="fixture",
        remote=False,
        request_digest="a" * 64,
    )

    assert report.first_meaningful_failure is not None
    assert original is not None
    assert report.metadata.first_errors[0].detected_pattern_index == original.detected_pattern_index
    assert report.metadata.first_errors[0].ingestion_index == original.ingestion_index
    assert report.metadata.request_schema_version == 1
    assert report.metadata.context_schema_version == 1
    assert report.metadata.source_commits == ("0123456789abcdef",)
    assert report.metadata.request_digest == "a" * 64
    assert report.recommended_next_evidence[0].bounds == "One boot cycle; stop after 10 seconds."
    assert request.session_evidence[0].facts.first_error == original
    json.dumps(asdict(report))


def test_report_first_error_metadata_does_not_copy_captured_text(tmp_path: Path) -> None:
    request = _request(tmp_path)
    evidence = request.session_evidence[0]
    original = evidence.facts.first_error
    assert original is not None
    sensitive = replace(
        original,
        match_excerpt=replace(
            original.match_excerpt,
            text="password=supersecret",
            raw_b64="cGFzc3dvcmQ=",
        ),
    )
    request = replace(
        request,
        session_evidence=(replace(evidence, facts=replace(evidence.facts, first_error=sensitive)),),
    )
    report = validate_report_response(
        request,
        _response(request.session_ids[0]),
        provider_id="local",
        model_id="fixture",
        remote=False,
        request_digest="a" * 64,
    )
    rendered = json.dumps(asdict(report))
    assert "supersecret" not in rendered
    assert "cGFzc3dvcmQ" not in rendered


@pytest.mark.parametrize(
    "change",
    [
        {
            "observations": [
                {
                    "text": "False line",
                    "references": [
                        {"kind": "uart", "session_id": "wrong", "ordinal": 1},
                    ],
                }
            ]
        },
        {
            "observations": [
                {
                    "text": "Unselected line",
                    "references": [
                        {"kind": "uart", "session_id": "evidence", "ordinal": 999},
                    ],
                }
            ]
        },
        {
            "inferences": [
                {
                    "text": "Certain",
                    "basis": [
                        {"kind": "first_error", "session_id": "evidence"},
                    ],
                    "uncertainty": "",
                }
            ]
        },
        {"first_error": {"pattern": "overwritten"}},
        {"source_patch": "--- old\n+++ new"},
        {"recommended_next_evidence": [{"action": "Capture indefinitely"}]},
    ],
)
def test_report_rejects_unsupported_claims_or_fields(
    tmp_path: Path,
    change: dict[str, object],
) -> None:
    request = _request(tmp_path)
    raw = _response(request.session_ids[0])
    raw.update(change)
    with pytest.raises(ValueError):
        validate_report_response(
            request,
            raw,
            provider_id="local",
            model_id="fixture",
            remote=False,
            request_digest="a" * 64,
        )


def test_report_rejects_source_reference_outside_selected_excerpt(tmp_path: Path) -> None:
    request = _request(tmp_path)
    raw = _response(request.session_ids[0])
    raw["observations"] = [
        {
            "text": "Unseen source line",
            "references": [
                {
                    "kind": "source",
                    "path": "src/boot.c",
                    "commit": "0123456789abcdef",
                    "start_line": 81,
                    "end_line": 81,
                }
            ],
        }
    ]
    with pytest.raises(ValueError, match="source"):
        validate_report_response(
            request,
            raw,
            provider_id="local",
            model_id="fixture",
            remote=False,
            request_digest="a" * 64,
        )


def test_report_accepts_selected_source_line_reference(tmp_path: Path) -> None:
    request = _request(tmp_path)
    raw = _response(request.session_ids[0])
    raw["observations"] = [
        {
            "text": "The selected source calls boot.",
            "references": [
                {
                    "kind": "source",
                    "path": "src/boot.c",
                    "commit": "0123456789abcdef",
                    "start_line": 80,
                    "end_line": 80,
                }
            ],
        }
    ]
    report = validate_report_response(
        request,
        raw,
        provider_id="local",
        model_id="fixture",
        remote=False,
        request_digest="a" * 64,
    )
    assert report.observations[0].references[0].path == "src/boot.c"


def test_report_derived_warnings_preserve_integrity_and_timing(tmp_path: Path) -> None:
    request = _request(tmp_path)
    evidence = request.session_evidence[0]
    facts = replace(
        evidence.facts,
        integrity=UartIntegrity(
            loss_status="not_observable",
            observation_scope=None,
            dropped_bytes=None,
        ),
        segments=({"segment_id": 0, "timestamp": {"source": "host"}},),
    )
    request = replace(request, session_evidence=(replace(evidence, facts=facts),))
    report = validate_report_response(
        request,
        _response(request.session_ids[0]),
        provider_id="local",
        model_id="fixture",
        remote=False,
        request_digest="a" * 64,
    )
    assert {warning.code for warning in report.metadata.provenance_warnings} >= {
        "uart_loss_not_observable",
        "host_timestamp",
    }


class FixtureAdapter:
    def __init__(self, *, provider_id: str, remote: bool, response: object) -> None:
        self.provider_id = provider_id
        self.remote = remote
        self.response = response
        self.calls: list[tuple[bytes, str]] = []

    async def analyze(self, payload: bytes, *, model_id: str) -> object:
        self.calls.append((payload, model_id))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


def test_disabled_default_and_remote_opt_in_block_adapter_calls(tmp_path: Path) -> None:
    request = _request(tmp_path)
    adapter = FixtureAdapter(
        provider_id="remote",
        remote=True,
        response=_response(request.session_ids[0]),
    )
    with pytest.raises(AnalysisUnavailable, match="disabled"):
        prepare_analysis(request, ProviderSelection(), {"remote": adapter})
    with pytest.raises(AnalysisUnavailable, match="opt-in"):
        prepare_analysis(
            request,
            ProviderSelection(provider_id="remote", model_id="fixture"),
            {"remote": adapter},
        )
    assert adapter.calls == []


def test_preparation_rejects_oversized_serialized_request(tmp_path: Path) -> None:
    request = _request(tmp_path)
    evidence = request.session_evidence[0]
    oversized_line = replace(evidence.uart_excerpts[0], text="x" * (4 * 1024 * 1024))
    request = replace(
        request,
        session_evidence=(replace(evidence, uart_excerpts=(oversized_line,)),),
    )
    adapter = FixtureAdapter(provider_id="local", remote=False, response={})
    with pytest.raises(AnalysisUnavailable, match="request byte limit"):
        prepare_analysis(
            request,
            ProviderSelection(provider_id="local", model_id="fixture"),
            {"local": adapter},
        )
    assert adapter.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("remote", [False, True])
async def test_prepared_manifest_precedes_exact_local_or_remote_submission(
    tmp_path: Path,
    remote: bool,
) -> None:
    request = _request(tmp_path)
    adapter = FixtureAdapter(
        provider_id="selected",
        remote=remote,
        response=_response(request.session_ids[0]),
    )
    prepared = prepare_analysis(
        request,
        ProviderSelection(
            provider_id="selected",
            model_id="fixture",
            remote_processing_opt_in=remote,
        ),
        {"selected": adapter},
    )
    assert adapter.calls == []
    assert prepared.manifest.session_ids == request.session_ids
    assert prepared.manifest.source_paths == ("src/boot.c",)
    assert prepared.manifest.provider_id == "selected"
    assert prepared.manifest.model_id == "fixture"
    assert prepared.manifest.remote is remote
    assert prepared.manifest.total_text_bytes == len(prepared.payload)
    assert prepared.manifest.request_digest == hashlib.sha256(prepared.payload).hexdigest()
    assert b"boot();" in prepared.payload

    report = await submit_analysis(prepared)
    assert len(adapter.calls) == 1
    assert adapter.calls[0] == (prepared.payload, "fixture")
    assert report.metadata.remote is remote
    assert report.metadata.provider_id == "selected"


@pytest.mark.asyncio
async def test_invalid_or_failed_provider_never_falls_back_or_modifies_evidence(
    tmp_path: Path,
) -> None:
    request = _request(tmp_path)
    original = request.session_evidence[0].facts.first_error
    selected = FixtureAdapter(provider_id="selected", remote=False, response={"oops": True})
    fallback = FixtureAdapter(
        provider_id="fallback",
        remote=False,
        response=_response(request.session_ids[0]),
    )
    prepared = prepare_analysis(
        request,
        ProviderSelection(provider_id="selected", model_id="fixture"),
        {"selected": selected, "fallback": fallback},
    )
    with pytest.raises(AnalysisUnavailable, match="invalid response"):
        await submit_analysis(prepared)
    assert fallback.calls == []
    assert request.session_evidence[0].facts.first_error == original

    selected.response = RuntimeError("password=supersecret")
    with pytest.raises(AnalysisUnavailable) as raised:
        await submit_analysis(prepared)
    assert "supersecret" not in str(raised.value)
    assert fallback.calls == []


@pytest.mark.asyncio
async def test_provider_timeout_fails_only_the_analysis(tmp_path: Path) -> None:
    request = _request(tmp_path)

    class SlowAdapter(FixtureAdapter):
        async def analyze(self, payload: bytes, *, model_id: str) -> object:
            self.calls.append((payload, model_id))
            await asyncio.Event().wait()
            return {}

    adapter = SlowAdapter(provider_id="slow", remote=False, response={})
    prepared = prepare_analysis(
        request,
        ProviderSelection(provider_id="slow", model_id="fixture", timeout_s=0.01),
        {"slow": adapter},
    )
    with pytest.raises(AnalysisUnavailable, match="timed out"):
        await submit_analysis(prepared)
    assert request.session_evidence[0].facts.first_error is not None


def test_adapter_credential_is_absent_from_manifest_and_payload(tmp_path: Path) -> None:
    request = _request(tmp_path)
    adapter = FixtureAdapter(provider_id="local", remote=False, response={})
    adapter.credential = "password=supersecret"
    prepared = prepare_analysis(
        request,
        ProviderSelection(provider_id="local", model_id="fixture"),
        {"local": adapter},
    )
    assert "supersecret" not in json.dumps(asdict(prepared.manifest))
    assert b"supersecret" not in prepared.payload


def test_prepared_manifest_limits_cannot_be_changed_after_review(tmp_path: Path) -> None:
    request = _request(tmp_path)
    adapter = FixtureAdapter(provider_id="local", remote=False, response={})
    prepared = prepare_analysis(
        request,
        ProviderSelection(provider_id="local", model_id="fixture"),
        {"local": adapter},
    )
    with suppress(TypeError):
        prepared.manifest.applied_limits["coding_context"]["excerpts"] = 999
    assert asdict(prepared.manifest)["applied_limits"]["coding_context"]["excerpts"] == 8
