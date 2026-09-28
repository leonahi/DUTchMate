"""CLI command and formatting tests for bounded Monitor operations."""

from typer.testing import CliRunner

import dutchmate_cli.main as main
from dutchmate_cli.capture import format_capture_result
from dutchmate_cli.monitor import format_monitor_result
from dutchmate_cli.wait import format_wait_pattern


def test_format_monitor_timeout_as_normal_operation_result() -> None:
    output = format_monitor_result(
        {
            "operation_id": "monitor-1",
            "outcome": "timeout",
            "mode": "conditions",
            "conditions": [{"pattern": "READY", "name": "ready"}],
            "timeout_s": 3.0,
            "evidence_ranges": [
                {
                    "session_id": "session-one",
                    "start_evidence_seq": 4,
                    "end_evidence_seq_exclusive": 9,
                }
            ],
            "matched_condition": None,
        }
    )

    assert "Monitor timeout" in output
    assert "monitor-1" in output
    assert "session-one:4..9" in output


def test_legacy_cli_formatters_preserve_alias_names_for_monitor_results() -> None:
    payload = {
        "operation_id": "monitor-1",
        "outcome": "timeout",
        "evidence_ranges": [],
    }

    assert format_capture_result(payload).splitlines()[0] == "Capture timeout"
    assert format_wait_pattern(payload).splitlines()[0] == "Wait timeout"


def test_monitor_seconds_command_calls_duration_client(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    requests: list[dict[str, object]] = []

    def fake_monitor_uart(**kwargs: object) -> dict[str, object]:
        requests.append(kwargs)
        return {"operation_id": "monitor-1", "outcome": "elapsed"}

    monkeypatch.setattr(main, "monitor_uart", fake_monitor_uart)
    monkeypatch.setattr(main, "format_monitor_result", lambda _payload: "Monitor elapsed")

    result = CliRunner().invoke(main.app, ["monitor", "--seconds", "0.5"])

    assert result.exit_code == 0
    assert result.stdout.strip() == "Monitor elapsed"
    assert requests == [
        {
            "duration_s": 0.5,
            "until": None,
            "timeout_s": None,
            "service_url": "http://127.0.0.1:2040",
        }
    ]


def test_monitor_until_command_requires_timeout_before_http(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    called = False

    def fake_monitor_uart(**_kwargs: object) -> dict[str, object]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(main, "monitor_uart", fake_monitor_uart)

    result = CliRunner().invoke(main.app, ["monitor", "--until", "READY"])

    assert result.exit_code == 2
    assert "exactly one completion mode" in result.output
    assert called is False
