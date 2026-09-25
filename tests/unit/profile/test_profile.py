from __future__ import annotations

from pathlib import Path

import pytest

from dutchmate_core.profile import (
    DutProfileConfig,
    DutProfileError,
    load_dut_profile_config,
    parse_dut_profile_config,
    resolve_dut_profile,
)


def test_resolve_basic_profile_uses_conservative_uart_defaults() -> None:
    profile = resolve_dut_profile(
        DutProfileConfig(),
        mode="basic",
        serial_port="/dev/ttyUSB0",
    )

    assert profile.name is None
    assert profile.backend_mode == "basic"
    assert profile.topology == "external_uart"
    assert profile.selector.strategy == "exact_path"
    assert profile.selector.exact_path == "/dev/ttyUSB0"
    assert profile.current_serial_port == "/dev/ttyUSB0"
    assert profile.reconnect_timeout_s == 5.0
    assert profile.uart.baudrate == 115200
    assert profile.uart.data_bits == 8
    assert profile.uart.parity == "none"
    assert profile.uart.stop_bits == 1
    assert profile.uart.rtscts is False
    assert profile.uart.xonxoff is False
    assert profile.uart.tx_enabled is False
    assert profile.uart.default_line_ending == "none"
    assert profile.uart.dtr_on_open == "driver_default"
    assert profile.uart.rts_on_open == "driver_default"
    assert profile.dut_io_voltage is None
    assert profile.controls == ()


def test_resolve_enhanced_profile_uses_fixed_uart_and_discovery_selector() -> None:
    profile = resolve_dut_profile(DutProfileConfig(), mode="enhanced")

    assert profile.backend_mode == "enhanced"
    assert profile.selector.strategy == "enhanced_discovery"
    assert profile.selector.exact_path is None
    assert profile.current_serial_port is None
    assert profile.uart.baudrate == 460800


def test_parse_profile_includes_topology_uart_and_sorted_gpio_projection() -> None:
    config = parse_dut_profile_config(
        {
            "profile": {"name": "fixture-dut"},
            "backend": {
                "mode": "basic",
                "serial_port": "/dev/ttyUSB0",
                "reconnect_timeout_s": 3.5,
                "topology": "native_usb_console",
            },
            "hardware": {
                "dut_io_voltage": 3.3,
                "uart": {
                    "baudrate": 230400,
                    "data_bits": 8,
                    "parity": "none",
                    "stop_bits": 1,
                    "rtscts": False,
                    "xonxoff": False,
                    "tx_enabled": True,
                    "default_line_ending": "crlf",
                    "control_lines": {
                        "dtr_on_open": "deasserted",
                        "rts_on_open": "asserted",
                    },
                },
                "control": {
                    "reset": {
                        "channel": "CTRL0",
                        "dut_signal": "RESET_N",
                        "mode": "open_drain",
                        "active_level": "low",
                    }
                },
            },
        }
    )

    profile = resolve_dut_profile(config)

    assert profile.name == "fixture-dut"
    assert profile.topology == "native_usb_console"
    assert profile.uart.baudrate == 230400
    assert profile.uart.tx_enabled is True
    assert profile.uart.default_line_ending == "crlf"
    assert profile.uart.dtr_on_open == "deasserted"
    assert profile.uart.rts_on_open == "asserted"
    assert profile.controls[0].role == "reset"
    assert profile.controls[0].channel == "CTRL0"
    assert profile.projection()["hardware"] == {
        "dut_io_voltage": 3.3,
        "uart": {
            "baudrate": 230400,
            "data_bits": 8,
            "parity": "none",
            "stop_bits": 1,
            "rtscts": False,
            "xonxoff": False,
            "tx_enabled": True,
            "default_line_ending": "crlf",
            "control_lines": {
                "dtr_on_open": "deasserted",
                "rts_on_open": "asserted",
            },
        },
        "control": [
            {
                "role": "reset",
                "channel": "CTRL0",
                "dut_signal": "RESET_N",
                "mode": "open_drain",
                "active_level": "low",
                "idle_level": None,
            }
        ],
    }


def test_profile_digest_is_canonical_and_changes_with_effective_values() -> None:
    first = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "profile": {"name": "fixture"},
                "backend": {"mode": "basic", "serial_port": "/dev/ttyUSB0"},
                "hardware": {"uart": {"tx_enabled": True, "baudrate": 230400}},
            }
        )
    )
    reordered = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "hardware": {"uart": {"baudrate": 230400, "tx_enabled": True}},
                "backend": {"serial_port": "/dev/ttyUSB0", "mode": "basic"},
                "profile": {"name": "fixture"},
            }
        )
    )
    changed = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "profile": {"name": "fixture"},
                "backend": {"mode": "basic", "serial_port": "/dev/ttyUSB0"},
                "hardware": {"uart": {"tx_enabled": False, "baudrate": 230400}},
            }
        )
    )

    assert len(first.digest_sha256) == 64
    assert first.canonical_json == reordered.canonical_json
    assert first.digest_sha256 == reordered.digest_sha256
    assert changed.digest_sha256 != first.digest_sha256


@pytest.mark.parametrize(
    ("raw_config", "message"),
    [
        ({"profile": {"name": " bad"}}, "profile.name"),
        ({"backend": {"topology": "wireless"}}, "topology"),
        ({"hardware": {"uart": {"data_bits": 7}}}, "data_bits"),
        ({"hardware": {"uart": {"parity": "even"}}}, "parity"),
        ({"hardware": {"uart": {"stop_bits": 2}}}, "stop_bits"),
        ({"hardware": {"uart": {"rtscts": True}}}, "rtscts"),
        ({"hardware": {"uart": {"xonxoff": True}}}, "xonxoff"),
        (
            {"hardware": {"uart": {"default_line_ending": "automatic"}}},
            "default_line_ending",
        ),
        (
            {"hardware": {"uart": {"control_lines": {"dtr_on_open": "pulse"}}}},
            "dtr_on_open",
        ),
    ],
)
def test_rejects_invalid_phase1_profile_values(
    raw_config: dict[str, object],
    message: str,
) -> None:
    config = parse_dut_profile_config(raw_config)

    with pytest.raises(DutProfileError, match=message):
        resolve_dut_profile(config, mode="basic", serial_port="/dev/ttyUSB0")


def test_rejects_rts_application_state_when_hardware_flow_control_owns_rts() -> None:
    config = parse_dut_profile_config(
        {
            "hardware": {
                "uart": {
                    "rtscts": True,
                    "control_lines": {"rts_on_open": "asserted"},
                }
            }
        }
    )

    with pytest.raises(DutProfileError, match="RTS.*rtscts"):
        resolve_dut_profile(config, mode="basic", serial_port="/dev/ttyUSB0")


def test_native_usb_discovery_requires_an_exact_path_until_safe_identity_exists() -> None:
    config = parse_dut_profile_config(
        {
            "backend": {
                "mode": "enhanced",
                "topology": "native_usb_console",
            }
        }
    )

    with pytest.raises(DutProfileError, match="native_usb_console.*exact serial path"):
        resolve_dut_profile(config)


def test_load_profile_reads_the_shared_project_toml(tmp_path: Path) -> None:
    path = tmp_path / "config.toml"
    path.write_text(
        """
[profile]
name = "fixture"

[backend]
mode = "enhanced"

[hardware]
dut_io_voltage = 3.3
""",
        encoding="utf-8",
    )

    config = load_dut_profile_config(path)

    assert config.name == "fixture"
    assert config.mode == "enhanced"
    assert config.hardware.dut_io_voltage == 3.3
