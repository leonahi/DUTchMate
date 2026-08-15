from __future__ import annotations

from pathlib import Path

import pytest

from dutchmate_cli.config import (
    CliConfig,
    CliConfigError,
    DaemonConfig,
    SessionsConfig,
    load_cli_config,
    parse_cli_config,
)
from dutchmate_core.backends.settings import BackendConfig, UartConfig


def test_parse_empty_cli_config_uses_defaults() -> None:
    config = parse_cli_config({})

    assert config == CliConfig()
    assert config.service_url == "http://127.0.0.1:2040"


def test_parse_daemon_and_sessions_config() -> None:
    config = parse_cli_config(
        {
            "daemon": {"host": "localhost", "port": 2041},
            "sessions": {
                "path": ".dutchmate/custom-sessions",
                "max_count": 25,
                "max_size_mb": 10,
            },
        }
    )

    assert config == CliConfig(
        daemon=DaemonConfig(host="localhost", port=2041),
        sessions=SessionsConfig(
            path=Path(".dutchmate/custom-sessions"),
            max_count=25,
            max_size_mb=10,
        ),
    )
    assert config.service_url == "http://localhost:2041"


def test_parse_backend_and_uart_config_for_startup() -> None:
    config = parse_cli_config(
        {
            "backend": {
                "mode": "basic",
                "serial_port": "/dev/ttyUSB0",
                "reconnect_timeout_s": 3.0,
            },
            "hardware": {
                "uart": {
                    "baudrate": 230400,
                    "tx_enabled": True,
                }
            },
        }
    )

    assert config.backend == BackendConfig(
        mode="basic",
        serial_port="/dev/ttyUSB0",
        reconnect_timeout_s=3.0,
        uart=UartConfig(baudrate=230400, tx_enabled=True),
    )


def test_load_cli_config_reads_toml_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[daemon]
port = 2041

[sessions]
path = ".dutchmate/custom-sessions"
""",
        encoding="utf-8",
    )

    config = load_cli_config(config_path)

    assert config.daemon.port == 2041
    assert config.sessions.path == Path(".dutchmate/custom-sessions")


def test_load_cli_config_returns_defaults_when_missing(tmp_path: Path) -> None:
    assert load_cli_config(tmp_path / "missing.toml") == CliConfig()


def test_rejects_non_table_daemon_config() -> None:
    with pytest.raises(CliConfigError, match=r"\[daemon\] must be a TOML table"):
        parse_cli_config({"daemon": "bad"})


def test_rejects_invalid_daemon_port() -> None:
    with pytest.raises(CliConfigError, match=r"\[daemon\]\.port must be between 1 and 65535"):
        parse_cli_config({"daemon": {"port": 70000}})


def test_rejects_boolean_session_limit() -> None:
    with pytest.raises(CliConfigError, match=r"\[sessions\]\.max_count must be an integer"):
        parse_cli_config({"sessions": {"max_count": True}})
