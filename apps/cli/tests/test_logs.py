from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.logs import format_recent_logs


def test_format_recent_logs_merges_records_and_reports_warnings() -> None:
    output = format_recent_logs(
        {
            "session_id": "20260821T120000Z-logs",
            "session_selection": "latest_terminal",
            "complete_lines": [
                {
                    "segment_id": 0,
                    "channel": 0,
                    "ingestion_index": 0,
                    "line_index_in_event": 0,
                    "line_text": "booting\n",
                }
            ],
            "partial_lines": [
                {
                    "segment_id": 1,
                    "channel": 0,
                    "ingestion_index": 2,
                    "line_index_in_event": 1,
                    "line_text": "tail",
                }
            ],
            "oversized_lines": [
                {
                    "segment_id": 1,
                    "channel": 0,
                    "ingestion_index": 1,
                    "line_index_in_event": 0,
                    "total_line_bytes": 70000,
                    "terminated": True,
                }
            ],
            "integrity": {"loss_status": "loss_reported"},
            "truncated": True,
            "response_truncated": True,
            "omitted_complete_lines": 4,
            "omitted_partial_lines": 0,
            "omitted_oversized_lines": 1,
        }
    )

    assert "Session: 20260821T120000Z-logs (latest_terminal)" in output
    assert "--- segment 0, channel 0 ---\nbooting" in output
    assert "70000 bytes exceeds processing limit" in output
    assert "tail [partial]" in output
    assert "Warning: UART integrity is loss_reported." in output
    assert "response omitted 4 complete, 0 partial, and 1 oversized" in output


def test_logs_command_forwards_options_and_prints_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_fetch_recent_logs(
        *,
        session_id: str | None,
        lines: int,
        service_url: str,
    ) -> dict[str, object]:
        assert session_id == "20260821T120000Z-logs"
        assert lines == 25
        assert service_url == "http://127.0.0.1:2040"
        return {"session_id": session_id}

    monkeypatch.setattr(main, "fetch_recent_logs", fake_fetch_recent_logs)
    monkeypatch.setattr(main, "format_recent_logs", lambda _payload: "recent logs")

    result = CliRunner().invoke(
        main.app,
        ["logs", "--session", "20260821T120000Z-logs", "--last", "25"],
    )

    assert result.exit_code == 0
    assert result.output == "recent logs\n"
