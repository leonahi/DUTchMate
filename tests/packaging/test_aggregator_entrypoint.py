"""Behavior of the public aggregator command surface."""

from __future__ import annotations

from typer.testing import CliRunner

from dutchmate import entrypoints


def test_v0_1_public_aggregator_does_not_expose_debug_agent() -> None:
    debug_result = CliRunner().invoke(entrypoints.app, ["debug", "--help"])

    assert debug_result.exit_code == 2
    assert "No such command 'debug'" in debug_result.stderr
