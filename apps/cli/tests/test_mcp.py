from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from typer.testing import CliRunner

import dutchmate_cli.mcp as mcp_module
from dutchmate_cli import main
from dutchmate_cli.mcp import McpLaunchError, McpLogLevel, launch_mcp


def test_mcp_command_launches_stdio_server_with_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str | None, McpLogLevel]] = []

    monkeypatch.setattr(
        main,
        "launch_mcp",
        lambda *, service_url, log_level: calls.append((service_url, log_level)),
    )

    result = CliRunner().invoke(main.app, ["mcp"])

    assert result.exit_code == 0
    assert result.output == ""
    assert calls == [(None, McpLogLevel.INFO)]


def test_mcp_command_resolves_service_environment_and_explicit_override(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str | None, McpLogLevel]] = []
    monkeypatch.setattr(
        main,
        "launch_mcp",
        lambda *, service_url, log_level: calls.append((service_url, log_level)),
    )
    runner = CliRunner()

    environment_result = runner.invoke(
        main.app,
        ["mcp", "--log-level", "debug"],
        env={"DUTCHMATE_SERVICE_URL": "http://127.0.0.1:3040"},
    )
    override_result = runner.invoke(
        main.app,
        ["mcp", "--service-url", "http://127.0.0.1:4040", "--log-level", "warning"],
        env={"DUTCHMATE_SERVICE_URL": "http://127.0.0.1:3040"},
    )

    assert environment_result.exit_code == 0
    assert override_result.exit_code == 0
    assert calls == [
        ("http://127.0.0.1:3040", McpLogLevel.DEBUG),
        ("http://127.0.0.1:4040", McpLogLevel.WARNING),
    ]


def test_mcp_command_rejects_unknown_log_level_before_launch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "launch_mcp",
        lambda **_kwargs: pytest.fail("invalid arguments must not launch MCP"),
    )

    result = CliRunner().invoke(main.app, ["mcp", "--log-level", "verbose"])

    assert result.exit_code == 2
    assert "Invalid value for '--log-level'" in result.output


def test_launcher_replaces_the_cli_process_with_mcp_executable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    command: list[str] = []

    class ProcessReplaced(RuntimeError):
        pass

    def fake_execvp(executable: str, arguments: list[str]) -> None:
        assert executable == "dutchmate-mcp"
        command.extend(arguments)
        raise ProcessReplaced

    monkeypatch.setattr(mcp_module, "_sibling_mcp_executable", lambda: None)
    monkeypatch.setattr(os, "execvp", fake_execvp)

    with pytest.raises(ProcessReplaced):
        launch_mcp(
            service_url="http://127.0.0.1:3040",
            log_level=McpLogLevel.ERROR,
        )

    assert command == [
        "dutchmate-mcp",
        "--service-url",
        "http://127.0.0.1:3040",
        "--log-level",
        "error",
    ]


def test_launcher_reports_missing_mcp_executable(monkeypatch: pytest.MonkeyPatch) -> None:
    def missing_executable(executable: str, arguments: list[str]) -> None:
        raise FileNotFoundError(executable)

    monkeypatch.setattr(mcp_module, "_sibling_mcp_executable", lambda: None)
    monkeypatch.setattr(os, "execvp", missing_executable)

    with pytest.raises(McpLaunchError, match="dutchmate-mcp executable is not installed"):
        launch_mcp(service_url=None, log_level=McpLogLevel.INFO)


def test_absolute_cli_launches_sibling_mcp_executable_without_venv_on_path() -> None:
    cli_executable = Path(sys.executable).with_name("dutchmate")
    environment = dict(os.environ)
    environment["PATH"] = "/usr/bin:/bin"

    completed = subprocess.run(
        [str(cli_executable), "mcp"],
        input="",
        text=True,
        capture_output=True,
        env=environment,
        timeout=5,
        check=False,
    )

    assert completed.returncode == 0
    assert completed.stdout == ""
