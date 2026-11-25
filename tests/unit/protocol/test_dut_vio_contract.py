import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.device_connection.parser import parse_device_message

PROTOCOL = Path(__file__).parents[3] / "hardware/protocol/v1"


def device_validator():
    errors = json.loads((PROTOCOL / "errors.schema.json").read_text())
    registry = Registry().with_resource(errors["$id"], Resource.from_contents(errors))
    return Draft202012Validator(
        json.loads((PROTOCOL / "device_to_host.schema.json").read_text()), registry=registry
    )


def payload(**changes):
    return {
        "type": "dut_vio",
        "timestamp_us": 123,
        "status": "ok",
        "adc_raw": 2048,
        "voltage_mv": 3300,
        "adc_reference_mv": 3300,
        "reference_source": "nominal",
        **changes,
    }


@pytest.mark.parametrize(
    "changes",
    [
        {},
        {"adc_raw": 0, "voltage_mv": 0},
        {"status": "adc_error", "adc_raw": None, "voltage_mv": None},
        {"status": "saturated", "adc_raw": 4095, "voltage_mv": None},
    ],
)
def test_vio_wire_is_accepted_by_parser_and_schema(changes):
    frame = payload(**changes)
    assert device_validator().is_valid(frame)
    message = parse_device_message(json.dumps(frame))
    assert message.timestamp_us == 123
    assert message.sample.status == frame["status"]
    assert message.sample.voltage_mv == frame["voltage_mv"]


@pytest.mark.parametrize(
    "changes",
    [
        {"timestamp_us": True},
        {"timestamp_us": -1},
        {"adc_raw": True},
        {"voltage_mv": None},
        {"adc_reference_mv": 2499},
        {"adc_reference_mv": 3601},
        {"reference_source": "guessed"},
        {"extra": 1},
        {"status": "adc_error", "adc_raw": 0, "voltage_mv": None},
        {"status": "saturated", "adc_raw": 4094, "voltage_mv": None},
    ],
)
def test_vio_wire_rejects_bad_types_and_shapes(changes):
    frame = payload(**changes)
    assert not device_validator().is_valid(frame)
    with pytest.raises(ProtocolValidationError):
        parse_device_message(json.dumps(frame))


def test_vio_parser_rejects_inconsistent_voltage_and_missing_fields():
    with pytest.raises(ProtocolValidationError):
        parse_device_message(json.dumps(payload(voltage_mv=3301)))
    for key in payload():
        if key == "type":
            continue
        frame = payload()
        del frame[key]
        with pytest.raises(ProtocolValidationError):
            parse_device_message(json.dumps(frame))


@pytest.mark.parametrize("enabled", [True, False])
def test_power_sense_command_is_strict_and_uses_existing_response_shape(enabled):
    from dutchmate_core.device_connection.commands import ConfigurePowerSenseCommand

    wire = ConfigurePowerSenseCommand(enabled).to_ndjson()
    assert wire.endswith(b"\n")
    assert json.loads(wire) == {"cmd": "configure_power_sense", "enabled": enabled}
    schema = Draft202012Validator(json.loads((PROTOCOL / "host_to_device.schema.json").read_text()))
    assert schema.is_valid(json.loads(wire))
    assert not schema.is_valid({"cmd": "configure_power_sense", "enabled": 1})
    assert not schema.is_valid({"cmd": "configure_power_sense", "enabled": enabled, "interval": 1})
    with pytest.raises(ValueError):
        ConfigurePowerSenseCommand(1)
