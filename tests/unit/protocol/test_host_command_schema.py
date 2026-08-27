import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

SCHEMA_PATH = (
    Path(__file__).parents[3] / "hardware" / "protocol" / "v1" / "host_to_device.schema.json"
)


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


@pytest.mark.parametrize(
    "payload",
    [
        {"cmd": "pulse_control", "channel": "CTRL0", "pulse_ms": 100},
        {"cmd": "set_control_state", "channel": "CTRL1", "state": "active"},
        {"cmd": "set_control_state", "channel": "CTRL1", "state": "idle"},
    ],
)
def test_schema_accepts_generic_control_actions(payload: dict[str, object]) -> None:
    assert _validator().is_valid(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"cmd": "reset", "pulse_ms": 100},
        {"cmd": "set_boot_mode", "mode": "bootloader"},
    ],
)
def test_schema_rejects_legacy_role_specific_actions(payload: dict[str, object]) -> None:
    assert not _validator().is_valid(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "mode": "open_drain",
            "active_level": "low",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        },
    ],
)
def test_gpio_schema_accepts_safe_electrical_combinations(payload: dict[str, object]) -> None:
    assert _validator().is_valid(payload)


@pytest.mark.parametrize("field", ["role", "dut_signal"])
def test_gpio_schema_rejects_host_only_metadata(field: str) -> None:
    payload = {
        "cmd": "configure_gpio_mode",
        "channel": "CTRL0",
        "mode": "open_drain",
        "active_level": "low",
        field: "reset" if field == "role" else "RESET_N",
    }

    assert not _validator().is_valid(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "mode": "open_drain",
            "active_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "mode": "open_drain",
            "active_level": "low",
            "idle_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "mode": "push_pull",
            "active_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "high",
        },
    ],
)
def test_gpio_schema_rejects_unsafe_electrical_combinations(payload: dict[str, object]) -> None:
    assert not _validator().is_valid(payload)
