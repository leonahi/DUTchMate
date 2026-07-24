from __future__ import annotations

import signal
from pathlib import Path

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.config import CliConfig, DaemonConfig, SessionsConfig
from dutchmate_cli.lifecycle import (
    LifecycleError,
    ServiceStartResult,
    ServiceStopResult,
    start_service,
    stop_service,
)


class FakeProcess:
    pid = 4242

    def poll(self) -> int | None:
        return None


def test_start_service_spawns_background_process_and_writes_pid(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_popen(command: list[str], **_kwargs: object) -> FakeProcess:
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr("dutchmate_cli.lifecycle.subprocess.Popen", fake_popen)
    pid_file = tmp_path / "service.pid"
    log_file = tmp_path / "service.log"
    health_checks = iter((False, True))

    result = start_service(
        host="127.0.0.1",
        port=2041,
        pid_file=pid_file,
        log_file=log_file,
        wait_timeout_s=0,
        health_check=lambda _url: next(health_checks),
        is_running=lambda _pid: False,
    )

    assert calls == [
        [
            "dutchmate-service",
            "--host",
            "127.0.0.1",
            "--port",
            "2041",
            "--session-root",
            ".dutchmate/sessions",
        ]
    ]
    assert pid_file.read_text(encoding="utf-8") == "4242\n"
    assert result == ServiceStartResult(
        pid=4242,
        url="http://127.0.0.1:2041",
        pid_file=pid_file,
        log_file=log_file,
        ready=True,
    )


def test_start_service_rejects_existing_running_pid(tmp_path: Path) -> None:
    pid_file = tmp_path / "service.pid"
    pid_file.write_text("4242\n", encoding="utf-8")

    with pytest.raises(LifecycleError) as error:
        start_service(
            pid_file=pid_file,
            log_file=tmp_path / "service.log",
            is_running=lambda _pid: True,
        )

    assert str(error.value) == "Device Core Service is already running (pid 4242)."


def test_stop_service_sends_sigterm_and_removes_pid_file(tmp_path: Path) -> None:
    pid_file = tmp_path / "service.pid"
    pid_file.write_text("4242\n", encoding="utf-8")
    killed: list[tuple[int, int]] = []

    result = stop_service(
        pid_file=pid_file,
        is_running=lambda _pid: True,
        kill=lambda pid, sig: killed.append((pid, sig)),
    )

    assert result == ServiceStopResult(pid=4242, pid_file=pid_file)
    assert killed == [(4242, signal.SIGTERM)]
    assert not pid_file.exists()


def test_stop_service_reports_missing_pid_file(tmp_path: Path) -> None:
    with pytest.raises(LifecycleError) as error:
        stop_service(pid_file=tmp_path / "missing.pid")

    assert str(error.value) == "Device Core Service is not running."


def test_start_command_reports_started_service(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_start_service(*, host: str, port: int, session_root: Path) -> ServiceStartResult:
        assert host == "127.0.0.1"
        assert port == 2040
        assert session_root == Path(".dutchmate/sessions")
        return ServiceStartResult(
            pid=4242,
            url="http://127.0.0.1:2040",
            pid_file=Path(".dutchmate/dutchmate-service.pid"),
            log_file=Path(".dutchmate/dutchmate-service.log"),
            ready=True,
        )

    monkeypatch.setattr(main, "start_service", fake_start_service)

    result = CliRunner().invoke(main.app, ["start"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service started (pid 4242, http://127.0.0.1:2040)\n"


def test_start_command_reports_lifecycle_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_start_service(*, host: str, port: int, session_root: Path) -> ServiceStartResult:
        raise LifecycleError("Device Core Service is already running (pid 4242).")

    monkeypatch.setattr(main, "start_service", fake_start_service)

    result = CliRunner().invoke(main.app, ["start"])

    assert result.exit_code == 1
    assert "Error: Device Core Service is already running (pid 4242)." in result.output


def test_start_command_uses_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_start_service(*, host: str, port: int, session_root: Path) -> ServiceStartResult:
        assert host == "localhost"
        assert port == 2041
        assert session_root == Path(".dutchmate/custom-sessions")
        return ServiceStartResult(
            pid=4242,
            url="http://localhost:2041",
            pid_file=Path(".dutchmate/dutchmate-service.pid"),
            log_file=Path(".dutchmate/dutchmate-service.log"),
            ready=True,
        )

    monkeypatch.setattr(
        main,
        "load_cli_config",
        lambda: CliConfig(
            daemon=DaemonConfig(host="localhost", port=2041),
            sessions=SessionsConfig(path=Path(".dutchmate/custom-sessions")),
        ),
    )
    monkeypatch.setattr(main, "start_service", fake_start_service)

    result = CliRunner().invoke(main.app, ["start"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service started (pid 4242, http://localhost:2041)\n"


def test_stop_command_reports_stopped_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        main,
        "stop_service",
        lambda: ServiceStopResult(pid=4242, pid_file=Path(".dutchmate/dutchmate-service.pid")),
    )

    result = CliRunner().invoke(main.app, ["stop"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service stopped (pid 4242)\n"
