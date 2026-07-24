from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceApiError
from dutchmate_cli.gpio import format_gpio_mode_result


def test_format_gpio_mode_result_renders_accepted_mapping() -> None:
    assert (
        format_gpio_mode_result(
            {
                "ok": True,
                "channel": "CTRL0",
                "role": "reset",
                "dut_signal": "RESET_N",
                "mode": "open_drain",
                "active_level": "low",
                "idle_level": None,
                "source": "runtime",
            }
        )
        == "Configured CTRL0: reset -> RESET_N (mode=open_drain, active=low, source=runtime)"
    )


def test_gpio_mode_command_configures_channel(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_configure_gpio_mode(
        *,
        channel: str,
        role: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
        service_url: str,
    ) -> dict[str, object]:
        assert channel == "CTRL0"
        assert role == "reset"
        assert dut_signal == "RESET_N"
        assert mode == "open_drain"
        assert active_level == "low"
        assert idle_level is None
        assert service_url == "http://127.0.0.1:2040"
        return {"channel": "CTRL0"}

    monkeypatch.setattr(main, "configure_gpio_mode", fake_configure_gpio_mode)
    monkeypatch.setattr(main, "format_gpio_mode_result", lambda _payload: "Configured CTRL0")

    result = CliRunner().invoke(
        main.app,
        [
            "gpio",
            "mode",
            "CTRL0",
            "reset",
            "RESET_N",
            "--mode",
            "open_drain",
            "--active-level",
            "low",
        ],
    )

    assert result.exit_code == 0
    assert result.output == "Configured CTRL0\n"


def test_gpio_mode_command_reports_service_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_configure_gpio_mode(
        *,
        channel: str,
        role: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
        service_url: str,
    ) -> dict[str, object]:
        raise ServiceApiError("Request validation failed")

    monkeypatch.setattr(main, "configure_gpio_mode", fake_configure_gpio_mode)

    result = CliRunner().invoke(
        main.app,
        [
            "gpio",
            "mode",
            "GPIO0",
            "reset",
            "RESET_N",
            "--mode",
            "open_drain",
            "--active-level",
            "low",
        ],
    )

    assert result.exit_code == 1
    assert "Error: Request validation failed" in result.output
