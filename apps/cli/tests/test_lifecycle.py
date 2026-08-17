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
from dutchmate_core.backends.settings import BackendConfig, BackendSettings
from dutchmate_core.device_connection.discovery import SerialPortCandidate


class FakeProcess:
    pid = 4242

    def poll(self) -> int | None:
        return None


def enhanced_settings(serial_port: str | None = None) -> BackendSettings:
    return BackendSettings(
        mode="enhanced",
        serial_port=serial_port,
        reconnect_timeout_s=5.0,
        baudrate=460800,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=False,
    )


def basic_settings(serial_port: str = "/dev/ttyUSB0", baudrate: int = 115200) -> BackendSettings:
    return BackendSettings(
        mode="basic",
        serial_port=serial_port,
        reconnect_timeout_s=5.0,
        baudrate=baudrate,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=False,
    )


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
        backend_settings=enhanced_settings(),
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
            "--session-max-size-mb",
            "50",
            "--config",
            ".dutchmate/config.toml",
            "--backend",
            "enhanced",
            "--baudrate",
            "460800",
            "--data-bits",
            "8",
            "--parity",
            "none",
            "--stop-bits",
            "1",
            "--reconnect-timeout-s",
            "5.0",
            "--no-tx-enabled",
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


def test_start_service_passes_serial_port_to_background_process(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    calls: list[list[str]] = []

    def fake_popen(command: list[str], **_kwargs: object) -> FakeProcess:
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr("dutchmate_cli.lifecycle.subprocess.Popen", fake_popen)
    health_checks = iter((False, True))

    start_service(
        backend_settings=enhanced_settings("/dev/ttyACM0"),
        host="127.0.0.1",
        port=2041,
        pid_file=tmp_path / "service.pid",
        log_file=tmp_path / "service.log",
        wait_timeout_s=0,
        health_check=lambda _url: next(health_checks),
        is_running=lambda _pid: False,
    )

    assert calls[0][-2:] == ["--serial-port", "/dev/ttyACM0"]


def test_start_service_rejects_existing_running_pid(tmp_path: Path) -> None:
    pid_file = tmp_path / "service.pid"
    pid_file.write_text("4242\n", encoding="utf-8")

    with pytest.raises(LifecycleError) as error:
        start_service(
            backend_settings=enhanced_settings(),
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
    def fake_start_service(
        *,
        host: str,
        port: int,
        session_root: Path,
        session_max_size_mb: int,
        backend_settings: BackendSettings,
    ) -> ServiceStartResult:
        assert host == "127.0.0.1"
        assert port == 2040
        assert session_root == Path(".dutchmate/sessions")
        assert session_max_size_mb == 50
        assert backend_settings == enhanced_settings()
        return ServiceStartResult(
            pid=4242,
            url="http://127.0.0.1:2040",
            pid_file=Path(".dutchmate/dutchmate-service.pid"),
            log_file=Path(".dutchmate/dutchmate-service.log"),
            ready=True,
        )

    monkeypatch.setattr(main, "start_service", fake_start_service)
    monkeypatch.setattr(main, "list_dutchmate_candidates", lambda: [])

    result = CliRunner().invoke(main.app, ["start", "--backend", "enhanced"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service started (pid 4242, http://127.0.0.1:2040)\n"


def test_start_command_requires_explicit_or_configured_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(main, "load_cli_config", lambda: CliConfig())

    result = CliRunner().invoke(main.app, ["start"])

    assert result.exit_code == 1
    assert "Backend mode is required" in result.output


def test_start_command_resolves_basic_without_enhanced_discovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unexpected_discovery() -> list[SerialPortCandidate]:
        raise AssertionError("Basic must not use Enhanced discovery")

    def fake_start_service(
        *,
        host: str,
        port: int,
        session_root: Path,
        session_max_size_mb: int,
        backend_settings: BackendSettings,
    ) -> ServiceStartResult:
        assert session_max_size_mb == 50
        assert backend_settings == basic_settings(baudrate=230400)
        return ServiceStartResult(
            pid=4242,
            url="http://127.0.0.1:2040",
            pid_file=Path(".dutchmate/dutchmate-service.pid"),
            log_file=Path(".dutchmate/dutchmate-service.log"),
            ready=True,
        )

    monkeypatch.setattr(main, "load_cli_config", lambda: CliConfig())
    monkeypatch.setattr(main, "start_service", fake_start_service)
    monkeypatch.setattr(main, "list_dutchmate_candidates", unexpected_discovery)

    result = CliRunner().invoke(
        main.app,
        [
            "start",
            "--backend",
            "basic",
            "--serial-port",
            "/dev/ttyUSB0",
            "--baudrate",
            "230400",
        ],
    )

    assert result.exit_code == 0


def test_start_command_reports_lifecycle_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_start_service(
        *,
        host: str,
        port: int,
        session_root: Path,
        session_max_size_mb: int,
        backend_settings: BackendSettings,
    ) -> ServiceStartResult:
        assert session_max_size_mb == 50
        raise LifecycleError("Device Core Service is already running (pid 4242).")

    monkeypatch.setattr(main, "start_service", fake_start_service)
    monkeypatch.setattr(main, "list_dutchmate_candidates", lambda: [])

    result = CliRunner().invoke(main.app, ["start", "--backend", "enhanced"])

    assert result.exit_code == 1
    assert "Error: Device Core Service is already running (pid 4242)." in result.output


def test_start_command_uses_config_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_start_service(
        *,
        host: str,
        port: int,
        session_root: Path,
        session_max_size_mb: int,
        backend_settings: BackendSettings,
    ) -> ServiceStartResult:
        assert host == "localhost"
        assert port == 2041
        assert session_root == Path(".dutchmate/custom-sessions")
        assert session_max_size_mb == 10
        assert backend_settings == enhanced_settings()
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
            sessions=SessionsConfig(
                path=Path(".dutchmate/custom-sessions"),
                max_size_mb=10,
            ),
            backend=BackendConfig(mode="enhanced"),
        ),
    )
    monkeypatch.setattr(main, "start_service", fake_start_service)
    monkeypatch.setattr(main, "list_dutchmate_candidates", lambda: [])

    result = CliRunner().invoke(main.app, ["start"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service started (pid 4242, http://localhost:2041)\n"


def test_start_command_auto_selects_single_dutchmate_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_start_service(
        *,
        host: str,
        port: int,
        session_root: Path,
        session_max_size_mb: int,
        backend_settings: BackendSettings,
    ) -> ServiceStartResult:
        assert session_max_size_mb == 50
        assert backend_settings == enhanced_settings("/dev/ttyACM0")
        return ServiceStartResult(
            pid=4242,
            url="http://127.0.0.1:2040",
            pid_file=Path(".dutchmate/dutchmate-service.pid"),
            log_file=Path(".dutchmate/dutchmate-service.log"),
            ready=True,
        )

    monkeypatch.setattr(main, "start_service", fake_start_service)
    monkeypatch.setattr(
        main,
        "list_dutchmate_candidates",
        lambda: [
            SerialPortCandidate(
                device="/dev/ttyACM0",
                description="DUTchMate Debug Helper",
                hwid="USB VID:PID=2E8A:000A",
            )
        ],
    )

    result = CliRunner().invoke(main.app, ["start", "--backend", "enhanced"])

    assert result.exit_code == 0


def test_start_command_rejects_multiple_dutchmate_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        main,
        "list_dutchmate_candidates",
        lambda: [
            SerialPortCandidate(
                device="/dev/ttyACM0",
                description="DUTchMate Debug Helper",
                hwid="USB VID:PID=2E8A:000A",
            ),
            SerialPortCandidate(
                device="/dev/ttyACM1",
                description="DUTchMate Debug Helper",
                hwid="USB VID:PID=2E8A:000A",
            ),
        ],
    )

    result = CliRunner().invoke(main.app, ["start", "--backend", "enhanced"])

    assert result.exit_code == 1
    assert "Error: Multiple DUTchMate serial devices found" in result.output


def test_stop_command_reports_stopped_service(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        main,
        "stop_service",
        lambda: ServiceStopResult(pid=4242, pid_file=Path(".dutchmate/dutchmate-service.pid")),
    )

    result = CliRunner().invoke(main.app, ["stop"])

    assert result.exit_code == 0
    assert result.output == "Device Core Service stopped (pid 4242)\n"
