"""CLI configuration loading for `.dutchmate/config.toml`."""

from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final, cast

DEFAULT_CONFIG_PATH: Final = Path(".dutchmate/config.toml")
DEFAULT_DAEMON_HOST: Final = "127.0.0.1"
DEFAULT_DAEMON_PORT: Final = 2040
DEFAULT_SESSION_PATH: Final = Path(".dutchmate/sessions")
DEFAULT_SESSION_MAX_COUNT: Final = 100
DEFAULT_SESSION_MAX_SIZE_MB: Final = 50


class CliConfigError(RuntimeError):
    """Raised when the CLI configuration file is invalid."""


@dataclass(frozen=True, slots=True)
class DaemonConfig:
    """Device Core Service daemon configuration."""

    host: str = DEFAULT_DAEMON_HOST
    port: int = DEFAULT_DAEMON_PORT


@dataclass(frozen=True, slots=True)
class SessionsConfig:
    """Debug session storage configuration."""

    path: Path = DEFAULT_SESSION_PATH
    max_count: int = DEFAULT_SESSION_MAX_COUNT
    max_size_mb: int = DEFAULT_SESSION_MAX_SIZE_MB


@dataclass(frozen=True, slots=True)
class CliConfig:
    """Merged CLI configuration."""

    daemon: DaemonConfig = DaemonConfig()
    sessions: SessionsConfig = SessionsConfig()

    @property
    def service_url(self) -> str:
        return f"http://{self.daemon.host}:{self.daemon.port}"


def load_cli_config(path: Path = DEFAULT_CONFIG_PATH) -> CliConfig:
    """Load CLI configuration from TOML, returning defaults when missing."""

    try:
        with path.open("rb") as file:
            raw_config = _toml_module().load(file)
    except FileNotFoundError:
        return CliConfig()

    if not isinstance(raw_config, Mapping):
        raise CliConfigError("CLI config must be a TOML table")
    return parse_cli_config(raw_config)


def parse_cli_config(raw_config: Mapping[str, object]) -> CliConfig:
    """Parse a raw TOML mapping into validated CLI configuration."""

    daemon = _parse_daemon_config(_optional_table(raw_config, "daemon"))
    sessions = _parse_sessions_config(_optional_table(raw_config, "sessions"))
    return CliConfig(daemon=daemon, sessions=sessions)


def _parse_daemon_config(raw_daemon: Mapping[str, object]) -> DaemonConfig:
    host = _optional_str(raw_daemon, "host", DEFAULT_DAEMON_HOST, "[daemon].host")
    port = _optional_port(raw_daemon, "port", DEFAULT_DAEMON_PORT, "[daemon].port")
    return DaemonConfig(host=host, port=port)


def _parse_sessions_config(raw_sessions: Mapping[str, object]) -> SessionsConfig:
    path = Path(_optional_str(raw_sessions, "path", str(DEFAULT_SESSION_PATH), "[sessions].path"))
    max_count = _optional_positive_int(
        raw_sessions,
        "max_count",
        DEFAULT_SESSION_MAX_COUNT,
        "[sessions].max_count",
    )
    max_size_mb = _optional_positive_int(
        raw_sessions,
        "max_size_mb",
        DEFAULT_SESSION_MAX_SIZE_MB,
        "[sessions].max_size_mb",
    )
    return SessionsConfig(path=path, max_count=max_count, max_size_mb=max_size_mb)


def _optional_table(raw_config: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = raw_config.get(key, {})
    if not isinstance(value, Mapping):
        raise CliConfigError(f"[{key}] must be a TOML table")
    return cast(Mapping[str, object], value)


def _optional_str(
    raw_config: Mapping[str, object],
    key: str,
    default: str,
    field_name: str,
) -> str:
    value = raw_config.get(key, default)
    if not isinstance(value, str):
        raise CliConfigError(f"{field_name} must be a string")
    stripped = value.strip()
    if not stripped:
        raise CliConfigError(f"{field_name} must not be empty")
    return stripped


def _optional_port(
    raw_config: Mapping[str, object],
    key: str,
    default: int,
    field_name: str,
) -> int:
    value = _optional_positive_int(raw_config, key, default, field_name)
    if value > 65535:
        raise CliConfigError(f"{field_name} must be between 1 and 65535")
    return value


def _optional_positive_int(
    raw_config: Mapping[str, object],
    key: str,
    default: int,
    field_name: str,
) -> int:
    value = raw_config.get(key, default)
    if not isinstance(value, int) or isinstance(value, bool):
        raise CliConfigError(f"{field_name} must be an integer")
    if value < 1:
        raise CliConfigError(f"{field_name} must be greater than zero")
    return value


def _toml_module() -> Any:
    try:
        return importlib.import_module("tomllib")
    except ModuleNotFoundError:  # pragma: no cover - exercised only on Python 3.10.
        return importlib.import_module("tomli")
