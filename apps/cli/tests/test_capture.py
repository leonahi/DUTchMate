from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.capture import format_capture_result
from dutchmate_cli.client import ServiceApiError


def test_format_capture_result_renders_session_summary() -> None:
    assert (
        format_capture_result(
            {
                "session_id": "20260729T100000Z-capture01",
                "backend_mode": "basic",
                "integrity": {"loss_status": "not_observable"},
                "timestamp_provenance": [
                    {
                        "segment_id": 0,
                        "timestamp": {
                            "source": "host",
                            "clock": "monotonic",
                            "observation_point": "host_serial_read",
                            "event_granularity": "serial_read_chunk",
                        },
                    }
                ],
                "segments": 2,
                "overflow": True,
                "interrupted": False,
                "resumed": False,
                "truncated": True,
            }
        )
        == "Capture complete: 20260729T100000Z-capture01 "
        "(backend=basic, loss=not_observable, "
        "timestamp=host/monotonic:host_serial_read/serial_read_chunk, "
        "first_error=none, segments=2, "
        "overflow=yes, interrupted=no, resumed=no, truncated=yes)"
    )


def test_format_capture_result_identifies_first_error_location() -> None:
    output = format_capture_result(
        {
            "session_id": "session-error",
            "first_error": {
                "pattern": "HardFault",
                "segment_id": 2,
                "ingestion_index": 19,
            },
        }
    )

    assert "first_error=HardFault@segment:2/event:19" in output


def test_capture_command_passes_duration_to_service(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_capture_uart(
        *,
        duration_s: float,
        service_url: str,
    ) -> dict[str, object]:
        assert duration_s == 2.5
        assert service_url == "http://127.0.0.1:2040"
        return {
            "session_id": "20260729T100000Z-capture01",
            "segments": 1,
            "overflow": False,
            "interrupted": False,
            "resumed": False,
            "truncated": False,
        }

    monkeypatch.setattr(main, "capture_uart", fake_capture_uart)
    monkeypatch.setattr(main, "format_capture_result", lambda _payload: "Capture complete")

    result = CliRunner().invoke(main.app, ["capture", "--seconds", "2.5"])

    assert result.exit_code == 0
    assert result.output == "Capture complete\n"


def test_capture_command_reports_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_capture_uart(
        *,
        duration_s: float,
        service_url: str,
    ) -> dict[str, object]:
        raise ServiceApiError("capture is already active")

    monkeypatch.setattr(main, "capture_uart", fake_capture_uart)

    result = CliRunner().invoke(main.app, ["capture", "--seconds", "1"])

    assert result.exit_code == 1
    assert "Error: capture is already active" in result.output


@pytest.mark.parametrize("seconds", ["0", "-1", "301", "inf", "nan"])
def test_capture_command_rejects_invalid_duration(seconds: str) -> None:
    result = CliRunner().invoke(main.app, ["capture", "--seconds", seconds])

    assert result.exit_code == 2
    assert "positive finite" in result.output
