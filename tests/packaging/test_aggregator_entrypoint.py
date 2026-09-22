"""Behavior of the public aggregator command surface."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from typer.testing import CliRunner

from dutchmate import entrypoints


def test_debug_forwards_arguments_to_the_optional_python_api(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def debug_main(arguments: list[str] | None = None) -> int:
        assert arguments is not None
        print("debug arguments:", " ".join(arguments))
        return 7

    monkeypatch.setattr(
        entrypoints,
        "import_module",
        lambda name: SimpleNamespace(main=debug_main),
        raising=False,
    )

    result = CliRunner().invoke(
        entrypoints.app,
        ["debug", "preview", "--session-id", "session-1"],
    )

    assert result.exit_code == 7
    assert result.stdout == "debug arguments: preview --session-id session-1\n"


def test_debug_reports_how_to_install_the_missing_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    missing = ModuleNotFoundError("No module named 'dutchmate_debug_agent'")
    missing.name = "dutchmate_debug_agent"

    def fail_import(name: str) -> object:
        raise missing

    monkeypatch.setattr(entrypoints, "import_module", fail_import, raising=False)

    result = CliRunner().invoke(entrypoints.app, ["debug", "--help"])

    assert result.exit_code == 1
    assert "Debug Agent is not installed" in result.stderr
    assert 'uv tool install "dutchmate[debug-agent]"' in result.stderr


def test_debug_does_not_mask_an_import_failure_inside_the_installed_extra(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    internal_failure = ModuleNotFoundError("No module named 'provider_dependency'")
    internal_failure.name = "provider_dependency"

    def fail_import(name: str) -> object:
        raise internal_failure

    monkeypatch.setattr(entrypoints, "import_module", fail_import, raising=False)

    result = CliRunner().invoke(entrypoints.app, ["debug", "preview"])

    assert result.exit_code == 1
    assert result.exception is internal_failure
    assert "Debug Agent is not installed" not in result.stderr
