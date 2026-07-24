from pathlib import Path

import pytest

from dutchmate_core.gpio_config.config import (
    GpioConfigError,
    HardwareControlMapping,
    HardwareGpioConfig,
    load_hardware_gpio_config,
    parse_hardware_gpio_config,
)


def test_parse_valid_hardware_control_mapping() -> None:
    config = parse_hardware_gpio_config(
        {
            "hardware": {
                "dut_io_voltage": 3.3,
                "control": {
                    "reset": {
                        "channel": "CTRL0",
                        "dut_signal": "RESET_N",
                        "mode": "open_drain",
                        "active_level": "low",
                    }
                },
            }
        }
    )

    assert config == HardwareGpioConfig(
        dut_io_voltage=3.3,
        controls={
            "reset": HardwareControlMapping(
                role="reset",
                channel="CTRL0",
                dut_signal="RESET_N",
                mode="open_drain",
                active_level="low",
            )
        },
    )


def test_parse_valid_boot_mapping_with_idle_level() -> None:
    config = parse_hardware_gpio_config(
        {
            "hardware": {
                "control": {
                    "boot": {
                        "channel": "CTRL1",
                        "dut_signal": "BOOT0",
                        "mode": "push_pull",
                        "active_level": "high",
                        "idle_level": "low",
                    }
                }
            }
        }
    )

    assert config.require_control("boot") == HardwareControlMapping(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
    )


def test_parse_empty_config_leaves_all_controls_unconfigured() -> None:
    config = parse_hardware_gpio_config({})

    assert config.dut_io_voltage is None
    assert config.controls == {}


def test_require_control_rejects_missing_role_mapping() -> None:
    config = parse_hardware_gpio_config({})

    with pytest.raises(GpioConfigError, match="hardware.control.reset is not configured"):
        config.require_control("reset")


def test_load_hardware_gpio_config_reads_toml_file(tmp_path: Path) -> None:
    config_path = tmp_path / "config.toml"
    config_path.write_text(
        """
[hardware]
dut_io_voltage = 1.8

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"
""",
        encoding="utf-8",
    )

    config = load_hardware_gpio_config(config_path)

    assert config.dut_io_voltage == 1.8
    assert config.require_control("reset").channel == "CTRL0"


def test_rejects_non_table_hardware_section() -> None:
    with pytest.raises(GpioConfigError, match=r"\[hardware\] must be a TOML table"):
        parse_hardware_gpio_config({"hardware": "bad"})


def test_rejects_non_table_control_section() -> None:
    with pytest.raises(GpioConfigError, match=r"\[hardware.control\] must be a TOML table"):
        parse_hardware_gpio_config({"hardware": {"control": "bad"}})


def test_rejects_non_table_control_mapping() -> None:
    with pytest.raises(GpioConfigError, match=r"\[hardware.control.reset\] must be a TOML table"):
        parse_hardware_gpio_config({"hardware": {"control": {"reset": "bad"}}})


def test_parse_custom_role_mapping() -> None:
    config = parse_hardware_gpio_config(
        {
            "hardware": {
                "control": {
                    "wake": {
                        "channel": "CTRL2",
                        "dut_signal": "WAKE_N",
                        "mode": "push_pull",
                        "active_level": "low",
                    }
                }
            }
        }
    )

    assert config.require_control("wake") == HardwareControlMapping(
        role="wake",
        channel="CTRL2",
        dut_signal="WAKE_N",
        mode="push_pull",
        active_level="low",
    )


def test_rejects_empty_role() -> None:
    with pytest.raises(GpioConfigError, match="GPIO role"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "": {
                            "channel": "CTRL2",
                            "dut_signal": "WAKE_N",
                            "mode": "push_pull",
                            "active_level": "low",
                        }
                    }
                }
            }
        )


def test_rejects_unknown_channel() -> None:
    with pytest.raises(GpioConfigError, match="GPIO control channel"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "reset": {
                            "channel": "GPIO0",
                            "dut_signal": "RESET_N",
                            "mode": "open_drain",
                            "active_level": "low",
                        }
                    }
                }
            }
        )


def test_rejects_duplicate_channel_assignments() -> None:
    with pytest.raises(GpioConfigError, match="assigned to both"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RESET_N",
                            "mode": "open_drain",
                            "active_level": "low",
                        },
                        "boot": {
                            "channel": "CTRL0",
                            "dut_signal": "BOOT0",
                            "mode": "push_pull",
                            "active_level": "high",
                        },
                    }
                }
            }
        )


@pytest.mark.parametrize("field_name", ["channel", "dut_signal", "mode", "active_level"])
def test_rejects_missing_required_control_fields(field_name: str) -> None:
    raw_mapping = {
        "channel": "CTRL0",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
    }
    del raw_mapping[field_name]

    with pytest.raises(GpioConfigError, match=f"hardware.control.reset.{field_name} is required"):
        parse_hardware_gpio_config({"hardware": {"control": {"reset": raw_mapping}}})


def test_rejects_empty_dut_signal() -> None:
    with pytest.raises(GpioConfigError, match="dut_signal must be a non-empty string"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": " ",
                            "mode": "open_drain",
                            "active_level": "low",
                        }
                    }
                }
            }
        )


def test_rejects_unknown_mode() -> None:
    with pytest.raises(GpioConfigError, match="GPIO mode"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RESET_N",
                            "mode": "floating",
                            "active_level": "low",
                        }
                    }
                }
            }
        )


@pytest.mark.parametrize("field_name", ["active_level", "idle_level"])
def test_rejects_unknown_level(field_name: str) -> None:
    raw_mapping = {
        "channel": "CTRL0",
        "dut_signal": "RESET_N",
        "mode": "open_drain",
        "active_level": "low",
    }
    raw_mapping[field_name] = "middle"

    with pytest.raises(GpioConfigError, match=f"GPIO {field_name}"):
        parse_hardware_gpio_config({"hardware": {"control": {"reset": raw_mapping}}})


@pytest.mark.parametrize("dut_io_voltage", [True, "3.3"])
def test_rejects_non_numeric_dut_io_voltage(dut_io_voltage: object) -> None:
    with pytest.raises(GpioConfigError, match="dut_io_voltage must be a number"):
        parse_hardware_gpio_config({"hardware": {"dut_io_voltage": dut_io_voltage}})


@pytest.mark.parametrize("dut_io_voltage", [1.7, 5.1])
def test_rejects_out_of_range_dut_io_voltage(dut_io_voltage: float) -> None:
    with pytest.raises(GpioConfigError, match="between 1.8 and 5.0"):
        parse_hardware_gpio_config({"hardware": {"dut_io_voltage": dut_io_voltage}})


def test_rejects_unexpected_control_field() -> None:
    with pytest.raises(GpioConfigError, match="Unexpected hardware.control.reset field"):
        parse_hardware_gpio_config(
            {
                "hardware": {
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RESET_N",
                            "mode": "open_drain",
                            "active_level": "low",
                            "pull": "up",
                        }
                    }
                }
            }
        )
