from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main


def test_wait_command_forwards_literal_timeout_and_prints_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_wait_for_pattern(
        *,
        pattern: str,
        timeout_s: float,
        service_url: str,
    ) -> dict[str, object]:
        assert pattern == "READY.*"
        assert timeout_s == 2.5
        assert service_url == "http://127.0.0.1:2040"
        return {"matched": False, "session_id": "wait-1"}

    monkeypatch.setattr(main, "wait_for_pattern", fake_wait_for_pattern)
    monkeypatch.setattr(main, "format_wait_pattern", lambda _payload: "No match")

    result = CliRunner().invoke(
        main.app,
        ["wait", "READY.*", "--timeout", "2.5"],
    )

    assert result.exit_code == 0
    assert result.output == "No match\n"
