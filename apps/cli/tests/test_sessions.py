from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceApiError
from dutchmate_cli.sessions import format_session_detail, format_session_list


def test_format_session_list_discriminates_native_and_legacy_items() -> None:
    output = format_session_list(
        {
            "items": [
                {
                    "session_id": "20260820T120000Z-native",
                    "schema_version": 1,
                    "compatibility": "native",
                    "state": "completed",
                    "workflow": "capture",
                    "backend_mode": "enhanced",
                    "baseline": False,
                    "segment_count": 2,
                    "integrity": {"loss_status": "none_reported"},
                },
                {
                    "session_id": "20260820T115900Z-legacy",
                    "schema_version": 0,
                    "compatibility": "legacy_read_only",
                    "command": "capture",
                },
            ],
            "next_cursor": "opaque-next",
        }
    )

    assert "20260820T120000Z-native [v1 native] completed/capture" in output
    assert "backend=enhanced baseline=no segments=2 loss=none_reported" in output
    assert "20260820T115900Z-legacy [v0 legacy_read_only]" in output
    assert "migration=required" in output
    assert output.endswith("Next cursor: opaque-next")


def test_format_session_detail_marks_legacy_read_only_and_lists_artifacts() -> None:
    output = format_session_detail(
        {
            "session_id": "20260820T115900Z-legacy",
            "schema_version": 0,
            "compatibility": "legacy_read_only",
            "started_at": "2026-08-20T11:59:00Z",
            "command": "capture",
            "firmware": "0.0.1",
            "device": "old-helper",
            "artifact_manifest": [
                {"name": "metadata.json", "bytes": 500, "records": None}
            ],
        }
    )

    assert "Schema: v0 (legacy_read_only)" in output
    assert "Access: read-only; migration required and unavailable" in output
    assert "metadata.json: 500 bytes" in output


def test_sessions_command_forwards_page_and_prints_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_list_debug_sessions(
        *,
        limit: int,
        cursor: str | None,
        service_url: str,
    ) -> dict[str, object]:
        assert (limit, cursor) == (10, "current")
        assert service_url == "http://127.0.0.1:2040"
        return {"items": [], "next_cursor": None}

    monkeypatch.setattr(main, "list_debug_sessions", fake_list_debug_sessions)
    monkeypatch.setattr(main, "format_session_list", lambda _payload: "Sessions: none")

    result = CliRunner().invoke(
        main.app,
        ["sessions", "--limit", "10", "--cursor", "current"],
    )

    assert result.exit_code == 0
    assert result.output == "Sessions: none\n"


def test_session_command_forwards_id_and_prints_detail(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_get_debug_session(
        session_id: str,
        *,
        service_url: str,
    ) -> dict[str, object]:
        assert session_id == "20260820T120000Z-native"
        assert service_url == "http://127.0.0.1:2040"
        return {"session_id": session_id}

    monkeypatch.setattr(main, "get_debug_session", fake_get_debug_session)
    monkeypatch.setattr(main, "format_session_detail", lambda _payload: "Session detail")

    result = CliRunner().invoke(main.app, ["session", "20260820T120000Z-native"])

    assert result.exit_code == 0
    assert result.output == "Session detail\n"


def test_session_command_reports_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_get_debug_session(
        session_id: str,
        *,
        service_url: str,
    ) -> dict[str, object]:
        raise ServiceApiError("session was not found")

    monkeypatch.setattr(main, "get_debug_session", fake_get_debug_session)

    result = CliRunner().invoke(main.app, ["session", "20260820T120000Z-missing"])

    assert result.exit_code == 1
    assert "Error: session was not found" in result.output
