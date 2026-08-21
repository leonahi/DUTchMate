from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.baseline import format_baseline_mutation
from dutchmate_cli.client import ServiceApiError


def test_format_mark_surfaces_change_replacement_time_and_integrity() -> None:
    output = format_baseline_mutation(
        {
            "session_id": "20260821T120000Z-newbase1",
            "previous_session_id": "20260820T120000Z-oldbase1",
            "changed": True,
            "marked_at": "2026-08-21T12:00:00Z",
            "integrity": {
                "loss_status": "not_observable",
                "observation_scope": None,
                "dropped_bytes": None,
            },
        },
        action="mark",
    )

    assert "Baseline mark: changed" in output
    assert "Previous session: 20260820T120000Z-oldbase1" in output
    assert "Marked at: 2026-08-21T12:00:00Z" in output
    assert "Integrity: not_observable" in output
    assert "Warning: UART loss was not observable" in output


@pytest.mark.parametrize(
    ("command", "client_name", "action"),
    [
        ("mark-baseline", "mark_session_baseline", "mark"),
        ("clear-baseline", "clear_session_baseline", "clear"),
    ],
)
def test_baseline_commands_forward_named_session(
    monkeypatch: pytest.MonkeyPatch,
    command: str,
    client_name: str,
    action: str,
) -> None:
    def fake_mutation(
        session_id: str,
        *,
        service_url: str,
    ) -> dict[str, object]:
        assert session_id == "20260821T120000Z-abc12345"
        assert service_url == "http://127.0.0.1:2040"
        return {"session_id": session_id, "changed": False}

    monkeypatch.setattr(main, client_name, fake_mutation)
    monkeypatch.setattr(
        main,
        "format_baseline_mutation",
        lambda _payload, *, action: f"baseline {action}",
    )

    result = CliRunner().invoke(
        main.app,
        [command, "20260821T120000Z-abc12345"],
    )

    assert result.exit_code == 0
    assert result.output == f"baseline {action}\n"


def test_mark_baseline_command_surfaces_eligibility_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_mark(session_id: str, *, service_url: str) -> dict[str, object]:
        raise ServiceApiError(
            "Device Core Service returned HTTP 409 [invalid_session_state]: "
            "Session cannot be marked as baseline: truncated"
        )

    monkeypatch.setattr(main, "mark_session_baseline", fail_mark)

    result = CliRunner().invoke(
        main.app,
        ["mark-baseline", "20260821T120000Z-abc12345"],
    )

    assert result.exit_code == 1
    assert "invalid_session_state" in result.output
    assert "truncated" in result.output
