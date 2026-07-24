"""Local Device Core Service process lifecycle helpers."""

from __future__ import annotations

import os
import signal
import subprocess
import time
from collections.abc import Callable, Sequence
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import Final, Protocol

from dutchmate_cli.client import ServiceClientError, fetch_status
from dutchmate_cli.config import DEFAULT_DAEMON_HOST, DEFAULT_DAEMON_PORT, DEFAULT_SESSION_PATH

DEFAULT_HOST: Final = DEFAULT_DAEMON_HOST
DEFAULT_PORT: Final = DEFAULT_DAEMON_PORT
DEFAULT_SESSION_ROOT: Final = DEFAULT_SESSION_PATH
DEFAULT_PID_FILE: Final = Path(".dutchmate/dutchmate-service.pid")
DEFAULT_LOG_FILE: Final = Path(".dutchmate/dutchmate-service.log")
DEFAULT_START_TIMEOUT_SECONDS: Final = 5.0


class LifecycleError(RuntimeError):
    """Raised when the CLI cannot start or stop the local service process."""


class StartedProcess(Protocol):
    pid: int

    def poll(self) -> int | None:
        """Return the process exit code, or None while still running."""


@dataclass(frozen=True, slots=True)
class ServiceStartResult:
    """Result of a Device Core Service start attempt."""

    pid: int
    url: str
    pid_file: Path
    log_file: Path
    ready: bool


@dataclass(frozen=True, slots=True)
class ServiceStopResult:
    """Result of a Device Core Service stop attempt."""

    pid: int
    pid_file: Path


def start_service(
    *,
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    session_root: Path = DEFAULT_SESSION_ROOT,
    pid_file: Path = DEFAULT_PID_FILE,
    log_file: Path = DEFAULT_LOG_FILE,
    command: Sequence[str] | None = None,
    wait_timeout_s: float = DEFAULT_START_TIMEOUT_SECONDS,
    health_check: Callable[[str], bool] | None = None,
    is_running: Callable[[int], bool] | None = None,
) -> ServiceStartResult:
    """Start the Device Core Service as a background process."""

    service_url = f"http://{host}:{port}"
    running_check = is_running or is_process_running
    existing_pid = _read_pid_file(pid_file)
    if existing_pid is not None and running_check(existing_pid):
        raise LifecycleError(f"Device Core Service is already running (pid {existing_pid}).")

    if (health_check or _service_responds)(service_url):
        raise LifecycleError(f"Device Core Service is already running at {service_url}.")

    pid_file.parent.mkdir(parents=True, exist_ok=True)
    log_file.parent.mkdir(parents=True, exist_ok=True)
    service_command = list(
        command
        or (
            "dutchmate-service",
            "--host",
            host,
            "--port",
            str(port),
            "--session-root",
            str(session_root),
        )
    )

    with log_file.open("ab") as log:
        process: StartedProcess = subprocess.Popen(
            service_command,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )

    pid_file.write_text(f"{process.pid}\n", encoding="utf-8")
    ready = _wait_until_ready(
        process=process,
        service_url=service_url,
        wait_timeout_s=wait_timeout_s,
        health_check=health_check or _service_responds,
    )
    if process.poll() is not None and not ready:
        _unlink_if_exists(pid_file)
        raise LifecycleError(f"Device Core Service exited during startup. Check {log_file}.")

    return ServiceStartResult(
        pid=process.pid,
        url=service_url,
        pid_file=pid_file,
        log_file=log_file,
        ready=ready,
    )


def stop_service(
    *,
    pid_file: Path = DEFAULT_PID_FILE,
    is_running: Callable[[int], bool] | None = None,
    kill: Callable[[int, int], None] = os.kill,
) -> ServiceStopResult:
    """Stop the background Device Core Service process recorded in the PID file."""

    running_check = is_running or is_process_running
    pid = _read_pid_file(pid_file)
    if pid is None:
        raise LifecycleError("Device Core Service is not running.")

    if not running_check(pid):
        _unlink_if_exists(pid_file)
        raise LifecycleError("Device Core Service is not running.")

    kill(pid, signal.SIGTERM)
    _unlink_if_exists(pid_file)
    return ServiceStopResult(pid=pid, pid_file=pid_file)


def is_process_running(pid: int) -> bool:
    """Return whether a process ID currently exists."""

    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _service_responds(service_url: str) -> bool:
    try:
        fetch_status(service_url=service_url)
    except ServiceClientError:
        return False
    return True


def _wait_until_ready(
    *,
    process: StartedProcess,
    service_url: str,
    wait_timeout_s: float,
    health_check: Callable[[str], bool],
) -> bool:
    deadline = time.monotonic() + wait_timeout_s
    while time.monotonic() < deadline:
        if health_check(service_url):
            return True
        if process.poll() is not None:
            return False
        time.sleep(0.1)
    return health_check(service_url)


def _read_pid_file(pid_file: Path) -> int | None:
    try:
        raw_pid = pid_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None

    try:
        return int(raw_pid)
    except ValueError as exc:
        raise LifecycleError(f"Invalid Device Core Service PID file: {pid_file}") from exc


def _unlink_if_exists(path: Path) -> None:
    with suppress(FileNotFoundError):
        path.unlink()
