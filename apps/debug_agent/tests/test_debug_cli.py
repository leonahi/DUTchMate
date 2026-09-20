from __future__ import annotations

import json
from pathlib import Path

import pytest
from test_evidence_package import _append_lines, _native_session
from test_report_boundary import FixtureAdapter, _response

from dutchmate_debug_agent import cli


def _session(root: Path) -> str:
    store, handle = _native_session(root)
    _append_lines(store, handle, ["BOOT\n", "ERROR boot\n"])
    store.complete_session(handle)
    return handle.session_id


def _args(root: Path, session_id: str, action: str) -> list[str]:
    return [
        action,
        "--session-root",
        str(root),
        "--session-id",
        session_id,
        "--provider",
        "ollama",
        "--model",
        "fixture",
    ]


def test_cli_preview_exposes_manifest_without_provider_call(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = _session(tmp_path)
    status = cli.main(_args(tmp_path, session_id, "preview"))
    output = capsys.readouterr()
    manifest = json.loads(output.out)

    assert status == 0
    assert output.err == ""
    assert manifest["session_ids"] == [session_id]
    assert manifest["provider_id"] == "ollama"
    assert manifest["remote"] is False
    assert len(manifest["request_digest"]) == 64


def test_cli_analyze_requires_reviewed_digest_before_provider_call(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = _session(tmp_path)
    response = _response(session_id)
    response["recommended_source_areas"] = []
    adapter = FixtureAdapter(provider_id="ollama", remote=False, response=response)
    monkeypatch.setattr(cli, "OllamaAdapter", lambda **_: adapter)
    args = _args(tmp_path, session_id, "analyze")
    status = cli.main([*args, "--approved-digest", "0" * 64])
    output = capsys.readouterr()

    assert status == 2
    assert output.out == ""
    assert "manifest digest mismatch" in output.err
    assert adapter.calls == []

    assert cli.main(_args(tmp_path, session_id, "preview")) == 0
    digest = json.loads(capsys.readouterr().out)["manifest_digest"]
    assert cli.main([*args, "--approved-digest", digest]) == 0
    report = json.loads(capsys.readouterr().out)
    assert len(report["metadata"]["request_digest"]) == 64
    assert len(adapter.calls) == 1


def test_cli_changed_model_requires_new_manifest_review(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session_id = _session(tmp_path)
    response = _response(session_id)
    response["recommended_source_areas"] = []
    adapter = FixtureAdapter(provider_id="ollama", remote=False, response=response)
    monkeypatch.setattr(cli, "OllamaAdapter", lambda **_: adapter)
    args = _args(tmp_path, session_id, "preview")
    assert cli.main(args) == 0
    digest = json.loads(capsys.readouterr().out)["manifest_digest"]

    changed = _args(tmp_path, session_id, "analyze")
    changed[changed.index("fixture")] = "another-model"
    assert cli.main([*changed, "--approved-digest", digest]) == 2
    assert "manifest digest mismatch" in capsys.readouterr().err
    assert adapter.calls == []


@pytest.mark.parametrize(
    ("provider_response", "message"),
    [({}, "invalid response"), (TimeoutError(), "timed out")],
)
def test_cli_provider_failures_do_not_return_partial_reports(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    provider_response: object,
    message: str,
) -> None:
    session_id = _session(tmp_path)
    adapter = FixtureAdapter(provider_id="ollama", remote=False, response=provider_response)
    monkeypatch.setattr(cli, "OllamaAdapter", lambda **_: adapter)
    assert cli.main(_args(tmp_path, session_id, "preview")) == 0
    digest = json.loads(capsys.readouterr().out)["manifest_digest"]

    assert (
        cli.main(
            [
                *_args(tmp_path, session_id, "analyze"),
                "--approved-digest",
                digest,
            ]
        )
        == 2
    )
    output = capsys.readouterr()
    assert output.out == ""
    assert message in output.err
    assert len(adapter.calls) == 1


def test_cli_validates_explicit_context_file_without_reading_source(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = _session(tmp_path)
    context_path = tmp_path / "context.json"
    context_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "objective": "Explain boot failure",
                "session_ids": [session_id],
                "changed_files": [{"path": "src/nonexistent.c", "summary": "Changed boot path"}],
            }
        ),
        encoding="utf-8",
    )

    status = cli.main(
        [
            *_args(tmp_path, session_id, "preview"),
            "--context-file",
            str(context_path),
        ]
    )
    manifest = json.loads(capsys.readouterr().out)
    assert status == 0
    assert manifest["source_paths"] == ["src/nonexistent.c"]


def test_cli_stays_disabled_without_provider_selection(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    session_id = _session(tmp_path)
    status = cli.main(
        [
            "preview",
            "--session-root",
            str(tmp_path),
            "--session-id",
            session_id,
        ]
    )
    output = capsys.readouterr()
    assert status == 2
    assert output.out == ""
    assert "disabled" in output.err
