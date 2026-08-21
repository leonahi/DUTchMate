from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.wait import format_wait_pattern


def test_format_wait_pattern_prints_match_excerpt_and_provenance() -> None:
    output = format_wait_pattern(
        {
            "matched": True,
            "pattern": "READY",
            "session_id": "20260821T120000Z-wait",
            "segment_id": 1,
            "channel": 0,
            "timestamp_us": 20,
            "match_start_byte": 2,
            "match_end_byte": 7,
            "match_excerpt": {"text": "xxREADY\n"},
        }
    )

    assert "Matched: READY" in output
    assert "Session: 20260821T120000Z-wait" in output
    assert "segment 1, channel 0, timestamp 20 us" in output
    assert "Match bytes: [2, 7)" in output
    assert "Excerpt: xxREADY" in output


def test_format_wait_pattern_prints_no_match_as_successful_outcome() -> None:
    assert format_wait_pattern(
        {"matched": False, "session_id": "20260821T120000Z-wait"}
    ) == "No match\nSession: 20260821T120000Z-wait"


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
