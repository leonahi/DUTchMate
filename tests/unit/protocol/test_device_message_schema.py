import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError
from referencing import Registry, Resource

SCHEMA_PATH = (
    Path(__file__).parents[3] / "hardware" / "protocol" / "v1" / "device_to_host.schema.json"
)
ERRORS_SCHEMA_PATH = SCHEMA_PATH.with_name("errors.schema.json")
EXAMPLES_PATH = SCHEMA_PATH.parent / "examples"


def _validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    errors_schema = json.loads(ERRORS_SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    registry = Registry().with_resource(
        errors_schema["$id"],
        Resource.from_contents(errors_schema),
    )
    return Draft202012Validator(schema, registry=registry)


@pytest.mark.parametrize(
    "example_path",
    [
        path
        for path in sorted(EXAMPLES_PATH.glob("*.json"))
        if "cmd" not in json.loads(path.read_text(encoding="utf-8"))
    ],
    ids=lambda path: path.name,
)
def test_every_checked_in_device_message_example_matches_the_schema(
    example_path: Path,
) -> None:
    _validator().validate(json.loads(example_path.read_text(encoding="utf-8")))


def _hello(capability: str) -> dict[str, object]:
    return {
        "type": "hello",
        "v": 1,
        "firmware": "0.1.0",
        "device": "dutchmate-rp2350",
        "capabilities": [capability],
    }


@pytest.mark.parametrize(
    "capability",
    ["uart_receive", "device_timestamp", "overflow_telemetry"],
)
def test_schema_accepts_phase1_enhanced_capability(capability: str) -> None:
    _validator().validate(_hello(capability))


def test_schema_rejects_legacy_uart_capture_capability() -> None:
    with pytest.raises(ValidationError):
        _validator().validate(_hello("uart_capture"))
