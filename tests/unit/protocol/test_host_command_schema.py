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
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "role": "reset",
            "mode": "open_drain",
            "active_level": "low",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "role": "boot",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "low",
        },
    ],
)
def test_gpio_schema_accepts_safe_electrical_combinations(payload: dict[str, object]) -> None:
    assert _validator().is_valid(payload)


@pytest.mark.parametrize(
    "payload",
    [
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "role": "reset",
            "mode": "open_drain",
            "active_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL0",
            "role": "reset",
            "mode": "open_drain",
            "active_level": "low",
            "idle_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "role": "boot",
            "mode": "push_pull",
            "active_level": "high",
        },
        {
            "cmd": "configure_gpio_mode",
            "channel": "CTRL1",
            "role": "boot",
            "mode": "push_pull",
            "active_level": "high",
            "idle_level": "high",
        },
    ],
)
def test_gpio_schema_rejects_unsafe_electrical_combinations(payload: dict[str, object]) -> None:
    assert not _validator().is_valid(payload)
