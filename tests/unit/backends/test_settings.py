from pathlib import Path

import pytest

from dutchmate_core.backends.settings import (
    BackendConfig,
    BackendConfigError,
    BackendSettings,
    UartConfig,
    load_backend_config,
    parse_backend_config,
    resolve_backend_mode,
    resolve_backend_settings,
)


def test_parse_backend_and_uart_config() -> None:
    config = parse_backend_config(
        {
            "backend": {
                "mode": "basic",
                "serial_port": "/dev/ttyUSB0",
                "reconnect_timeout_s": 2.5,
            },
            "hardware": {
                "uart": {
                    "baudrate": 921600,
                    "data_bits": 8,
                    "parity": "none",
                    "stop_bits": 1,
                    "tx_enabled": True,
                }
            },
        }
    )

    assert config == BackendConfig(
        mode="basic",
        serial_port="/dev/ttyUSB0",
        reconnect_timeout_s=2.5,
        uart=UartConfig(baudrate=921600, tx_enabled=True),
    )


def test_load_backend_config_reads_shared_project_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
[backend]
mode = "enhanced"

[hardware.uart]
baudrate = 460800
""",
        encoding="utf-8",
    )

    assert load_backend_config(path).mode == "enhanced"


def test_resolve_basic_defaults() -> None:
    settings = resolve_backend_settings(
        BackendConfig(mode="basic", serial_port="/dev/ttyUSB0")
    )

    assert settings == BackendSettings(
        mode="basic",
        serial_port="/dev/ttyUSB0",
        reconnect_timeout_s=5.0,
        baudrate=115200,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=False,
    )


def test_resolve_enhanced_defaults_and_allows_disconnected_selection() -> None:
    settings = resolve_backend_settings(BackendConfig(mode="enhanced"))

    assert settings.mode == "enhanced"
    assert settings.serial_port is None
    assert settings.baudrate == 460800


def test_explicit_values_override_backend_config() -> None:
    settings = resolve_backend_settings(
        BackendConfig(
            mode="enhanced",
            serial_port="/dev/ttyACM0",
            uart=UartConfig(baudrate=460800),
        ),
        mode="basic",
        serial_port="/dev/ttyUSB9",
        baudrate=230400,
        reconnect_timeout_s=1.5,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=True,
    )

    assert settings.mode == "basic"
    assert settings.serial_port == "/dev/ttyUSB9"
    assert settings.baudrate == 230400
    assert settings.reconnect_timeout_s == 1.5
    assert settings.tx_enabled is True


def test_backend_mode_is_required_without_cli_or_config_value() -> None:
    with pytest.raises(BackendConfigError, match="Backend mode is required"):
        resolve_backend_mode(BackendConfig())


def test_basic_backend_requires_explicit_or_configured_port() -> None:
    with pytest.raises(BackendConfigError, match="Basic backend requires"):
        resolve_backend_settings(BackendConfig(mode="basic"))


@pytest.mark.parametrize("baudrate", [115200, 230400])
def test_enhanced_backend_rejects_non_protocol_baudrate(baudrate: int) -> None:
    with pytest.raises(BackendConfigError, match="fixed at 460800"):
        resolve_backend_settings(BackendConfig(mode="enhanced"), baudrate=baudrate)


@pytest.mark.parametrize(
    "raw_config",
    [
        {"backend": {"mode": "auto"}},
        {"backend": {"mode": "hybrid"}},
        {"backend": {"serial_port": " /dev/ttyUSB0"}},
        {"backend": {"serial_port": "/dev/tty\x00USB0"}},
        {"backend": {"serial_port": "/" * 4097}},
        {"backend": {"reconnect_timeout_s": True}},
        {"backend": {"reconnect_timeout_s": 0.09}},
        {"backend": {"reconnect_timeout_s": 60.1}},
        {"hardware": {"uart": {"baudrate": True}}},
        {"hardware": {"uart": {"data_bits": 7}}},
        {"hardware": {"uart": {"parity": "even"}}},
        {"hardware": {"uart": {"stop_bits": 2}}},
        {"hardware": {"uart": {"tx_enabled": 1}}},
    ],
)
def test_rejects_invalid_backend_or_uart_config(
    raw_config: dict[str, object],
) -> None:
    with pytest.raises(BackendConfigError):
        parse_backend_config(raw_config)
