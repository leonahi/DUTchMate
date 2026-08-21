from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceApiError
from dutchmate_cli.dut import format_boot_mode_result, format_reset_result


def test_format_reset_result_renders_accepted_action() -> None:
    assert (
        format_reset_result(
            {
                "ok": True,
                "pulse_ms": 250,
                "performed_at": "2026-08-21T10:00:00Z",
                "device_timestamp_us": 182334500,
            }
        )
        == "Reset command accepted (pulse_ms=250, performed_at=2026-08-21T10:00:00Z, "
        "device_timestamp_us=182334500)"
    )


def test_format_boot_mode_result_renders_accepted_action() -> None:
    assert (
        format_boot_mode_result(
            {
                "ok": True,
                "mode": "bootloader",
                "performed_at": "2026-08-21T10:00:00Z",
                "device_timestamp_us": 182334600,
            }
        )
        == "Boot mode set to bootloader (performed_at=2026-08-21T10:00:00Z, "
        "device_timestamp_us=182334600)"
    )


def test_dut_reset_command_pulses_reset_role(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_reset_dut(*, pulse_ms: int, service_url: str) -> dict[str, object]:
        assert pulse_ms == 250
        assert service_url == "http://127.0.0.1:2040"
        return {
            "ok": True,
            "pulse_ms": pulse_ms,
            "performed_at": "2026-08-21T10:00:00Z",
            "device_timestamp_us": 182334500,
        }

    monkeypatch.setattr(main, "reset_dut", fake_reset_dut)
    monkeypatch.setattr(main, "format_reset_result", lambda _payload: "Reset accepted")

    result = CliRunner().invoke(main.app, ["dut", "reset", "--pulse-ms", "250"])

    assert result.exit_code == 0
    assert result.output == "Reset accepted\n"


def test_dut_reset_command_reports_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_reset_dut(*, pulse_ms: int, service_url: str) -> dict[str, object]:
        raise ServiceApiError("GPIO role 'reset' is not configured")

    monkeypatch.setattr(main, "reset_dut", fake_reset_dut)

    result = CliRunner().invoke(main.app, ["dut", "reset"])

    assert result.exit_code == 1
    assert "Error: GPIO role 'reset' is not configured" in result.output


def test_dut_boot_mode_command_sets_boot_mode(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_set_boot_mode(*, mode: str, service_url: str) -> dict[str, object]:
        assert mode == "bootloader"
        assert service_url == "http://127.0.0.1:2040"
        return {
            "ok": True,
            "mode": mode,
            "performed_at": "2026-08-21T10:00:00Z",
            "device_timestamp_us": 182334600,
        }

    monkeypatch.setattr(main, "set_boot_mode", fake_set_boot_mode)
    monkeypatch.setattr(
        main,
        "format_boot_mode_result",
        lambda payload: f"Boot mode set to {payload['mode']}",
    )

    result = CliRunner().invoke(main.app, ["dut", "boot-mode", "bootloader"])

    assert result.exit_code == 0
    assert result.output == "Boot mode set to bootloader\n"


def test_dut_boot_mode_command_reports_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_set_boot_mode(*, mode: str, service_url: str) -> dict[str, object]:
        raise ServiceApiError("Request validation failed")

    monkeypatch.setattr(main, "set_boot_mode", fake_set_boot_mode)

    result = CliRunner().invoke(main.app, ["dut", "boot-mode", "factory"])

    assert result.exit_code == 1
    assert "Error: Request validation failed" in result.output
