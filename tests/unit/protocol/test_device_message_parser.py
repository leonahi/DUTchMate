import base64
import json

import pytest

from dutchmate_core.device_connection.errors import (
    InvalidUtf8Error,
    MalformedMessageError,
    ProtocolValidationError,
    ProtocolVersionError,
    UnsupportedMessageTypeError,
)
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import parse_device_message


def _hello_line(**overrides: object) -> str:
    payload: dict[str, object] = {
        "type": "hello",
        "v": 1,
        "firmware": "0.1.0",
        "device": "dutchmate-rp2350",
        "capabilities": [],
    }
    payload.update(overrides)
    return json.dumps(payload)


def _command_error_line(detail: object) -> str:
    return json.dumps({"ok": False, "error": "timeout", "detail": detail})


def _uart_line(data: bytes) -> str:
    return json.dumps(
        {
            "type": "uart",
            "channel": 0,
            "timestamp_us": 1,
            "data_b64": base64.b64encode(data).decode("ascii"),
        }
    )


def test_parse_valid_hello_message() -> None:
    message = parse_device_message(
        json.dumps(
            {
                "type": "hello",
                "v": 1,
                "firmware": "0.1.0",
                "device": "dutchmate-rp2350",
                "capabilities": ["uart_receive", "gpio_control", "uart_send"],
            }
        )
    )

    assert message == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2350",
        capabilities=("uart_receive", "gpio_control", "uart_send"),
    )


def test_parse_hello_from_bytes() -> None:
    message = parse_device_message(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":[]}'
    )

    assert message == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2350",
        capabilities=(),
    )


@pytest.mark.parametrize("capability", ["device_timestamp", "overflow_telemetry"])
def test_parse_hello_accepts_phase1_telemetry_capabilities(capability: str) -> None:
    message = parse_device_message(_hello_line(capabilities=[capability]))

    assert message == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2350",
        capabilities=(capability,),
    )


@pytest.mark.parametrize("field", ["firmware", "device"])
@pytest.mark.parametrize("value", ["x", "a" * 64, "é" * 32, "e\u0301"])
def test_hello_identity_accepts_and_preserves_exact_utf8_value(
    field: str,
    value: str,
) -> None:
    message = parse_device_message(_hello_line(**{field: value}))

    assert getattr(message, field) == value


@pytest.mark.parametrize("field", ["firmware", "device"])
def test_hello_identity_rejects_empty_value(field: str) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: ""}))


@pytest.mark.parametrize("field", ["firmware", "device"])
@pytest.mark.parametrize("value", [None, 7, [], {}])
def test_hello_identity_rejects_non_string_value(
    field: str,
    value: object,
) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: value}))


@pytest.mark.parametrize("field", ["firmware", "device"])
def test_hello_identity_rejects_unpaired_surrogate(field: str) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: "\ud800"}))


@pytest.mark.parametrize("field", ["firmware", "device"])
@pytest.mark.parametrize("value", ["a" * 65, "é" * 33])
def test_hello_identity_rejects_values_above_64_utf8_bytes(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: value}))


@pytest.mark.parametrize("field", ["firmware", "device"])
@pytest.mark.parametrize("value", [" value", "value\u00a0", "\u2003value"])
def test_hello_identity_rejects_unicode_edge_whitespace(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: value}))


@pytest.mark.parametrize("field", ["firmware", "device"])
@pytest.mark.parametrize("value", ["val\x00ue", "value\x7f", "val\u0080ue"])
def test_hello_identity_rejects_unicode_control_characters(
    field: str,
    value: str,
) -> None:
    with pytest.raises(ProtocolValidationError, match=field):
        parse_device_message(_hello_line(**{field: value}))


def test_rejects_malformed_json() -> None:
    with pytest.raises(MalformedMessageError) as raised:
        parse_device_message('{"type":"hello"')

    assert raised.value.input_error == "invalid_json"


def test_rejects_invalid_utf8_with_distinct_classification() -> None:
    with pytest.raises(InvalidUtf8Error) as raised:
        parse_device_message(b"\xff")

    assert raised.value.input_error == "invalid_utf8"


def test_rejects_non_object_json() -> None:
    with pytest.raises(ProtocolValidationError) as raised:
        parse_device_message("[]")

    assert raised.value.input_error == "invalid_message"


def test_rejects_protocol_version_mismatch() -> None:
    with pytest.raises(ProtocolVersionError):
        parse_device_message(
            '{"type":"hello","v":2,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":[]}'
        )


def test_rejects_boolean_protocol_version() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":true,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":[]}'
        )


def test_rejects_unknown_capability() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":["unknown"]}'
        )


def test_rejects_legacy_uart_capture_capability() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":["uart_capture"]}'
        )


def test_rejects_duplicate_capability() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":["uart_receive","uart_receive"]}'
        )


def test_rejects_unexpected_hello_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2350","capabilities":[],"extra":true}'
        )


def test_parse_uart_message() -> None:
    message = parse_device_message(
        '{"type":"uart","channel":0,"timestamp_us":182341200,"data_b64":"Qk9PVF9PSwo="}'
    )

    assert message == UartMessage(
        channel=0,
        timestamp_us=182341200,
        data=b"BOOT_OK\n",
        text="BOOT_OK\n",
    )


def test_parse_uart_message_with_lossy_utf8_text() -> None:
    message = parse_device_message(
        '{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"//5PSwo="}'
    )

    assert message == UartMessage(
        channel=0,
        timestamp_us=1,
        data=b"\xff\xfeOK\n",
        text="\ufffd\ufffdOK\n",
    )


@pytest.mark.parametrize(
    "data",
    [pytest.param(b"x", id="one-byte"), pytest.param(b"x" * 32768, id="max-bytes")],
)
def test_uart_payload_accepts_and_preserves_exact_decoded_bytes(data: bytes) -> None:
    message = parse_device_message(_uart_line(data))

    assert message.data == data


@pytest.mark.parametrize(
    "data",
    [pytest.param(b"", id="empty"), pytest.param(b"x" * 32769, id="over-max")],
)
def test_uart_payload_rejects_decoded_size_outside_1_to_32768_bytes(data: bytes) -> None:
    with pytest.raises(ProtocolValidationError, match="1..32768"):
        parse_device_message(_uart_line(data))


def test_rejects_invalid_uart_base64() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"not base64"}')


def test_rejects_negative_uart_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"type":"uart","channel":-1,"timestamp_us":1,"data_b64":"WA=="}')


def test_rejects_boolean_uart_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"type":"uart","channel":true,"timestamp_us":1,"data_b64":"WA=="}')


def test_rejects_negative_uart_timestamp() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"type":"uart","channel":0,"timestamp_us":-1,"data_b64":"WA=="}')


def test_rejects_unexpected_uart_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA==","extra":true}'
        )


def test_parse_buffer_overflow_message() -> None:
    message = parse_device_message(
        '{"type":"buffer_overflow","channel":0,"timestamp_us":182350000,"dropped_bytes":512}'
    )

    assert message == BufferOverflowMessage(
        channel=0,
        timestamp_us=182350000,
        dropped_bytes=512,
    )


def test_rejects_zero_dropped_bytes_for_buffer_overflow() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_overflow","channel":0,"timestamp_us":1,"dropped_bytes":0}'
        )


def test_rejects_negative_buffer_overflow_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_overflow","channel":-1,"timestamp_us":1,"dropped_bytes":512}'
        )


def test_rejects_negative_buffer_overflow_timestamp() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_overflow","channel":0,"timestamp_us":-1,"dropped_bytes":512}'
        )


def test_rejects_unexpected_buffer_overflow_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_overflow","channel":0,"timestamp_us":1,"dropped_bytes":512,"extra":true}'
        )


def test_parse_buffer_status_message() -> None:
    message = parse_device_message(
        json.dumps(
            {
                "type": "buffer_status",
                "timestamp_us": 182360000,
                "uart_rx_size_bytes": 32768,
                "uart_rx_used_bytes": 4096,
                "uart_rx_high_water_bytes": 18432,
                "dropped_bytes_total": 512,
                "overflow_events": 1,
            }
        )
    )

    assert message == BufferStatusMessage(
        timestamp_us=182360000,
        uart_rx_size_bytes=32768,
        uart_rx_used_bytes=4096,
        uart_rx_high_water_bytes=18432,
        dropped_bytes_total=512,
        overflow_events=1,
    )


def test_rejects_zero_buffer_status_size() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_status","timestamp_us":1,"uart_rx_size_bytes":0,"uart_rx_used_bytes":0,"uart_rx_high_water_bytes":0,"dropped_bytes_total":0,"overflow_events":0}'
        )


def test_rejects_buffer_status_used_bytes_above_size() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_status","timestamp_us":1,"uart_rx_size_bytes":10,"uart_rx_used_bytes":11,"uart_rx_high_water_bytes":10,"dropped_bytes_total":0,"overflow_events":0}'
        )


def test_rejects_buffer_status_high_water_above_size() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_status","timestamp_us":1,"uart_rx_size_bytes":10,"uart_rx_used_bytes":5,"uart_rx_high_water_bytes":11,"dropped_bytes_total":0,"overflow_events":0}'
        )


def test_rejects_unexpected_buffer_status_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"buffer_status","timestamp_us":1,"uart_rx_size_bytes":10,"uart_rx_used_bytes":5,"uart_rx_high_water_bytes":5,"dropped_bytes_total":0,"overflow_events":0,"extra":true}'
        )


def test_parse_command_success_message() -> None:
    message = parse_device_message('{"ok":true,"timestamp_us":182334400}')

    assert message == CommandSuccessMessage(timestamp_us=182334400)


def test_parse_command_success_without_timestamp() -> None:
    message = parse_device_message('{"ok":true}')

    assert message == CommandSuccessMessage()


def test_parse_uart_send_success_acceptance_count() -> None:
    message = parse_device_message(
        '{"ok":true,"timestamp_us":182334400,"bytes_accepted":7}'
    )

    assert message == CommandSuccessMessage(
        timestamp_us=182334400,
        bytes_accepted=7,
    )


def test_rejects_negative_command_success_acceptance_count() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":true,"bytes_accepted":-1}')


def test_rejects_oversized_command_success_acceptance_count() -> None:
    with pytest.raises(ProtocolValidationError, match="1024"):
        parse_device_message('{"ok":true,"bytes_accepted":1025}')


def test_rejects_negative_command_success_timestamp() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":true,"timestamp_us":-1}')


def test_rejects_unexpected_command_success_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":true,"timestamp_us":1,"extra":true}')


def test_parse_command_error_message() -> None:
    message = parse_device_message(
        '{"ok":false,"error":"not_configured","detail":"reset role is not configured"}'
    )

    assert message == CommandErrorMessage(
        error="not_configured",
        detail="reset role is not configured",
    )


@pytest.mark.parametrize(
    "detail",
    ["x", "a" * 256, "é" * 128, " ", "\u00a0detail\u00a0", "e\u0301"],
)
def test_command_error_detail_accepts_and_preserves_exact_utf8_value(detail: str) -> None:
    message = parse_device_message(_command_error_line(detail))

    assert message == CommandErrorMessage(error="timeout", detail=detail)


@pytest.mark.parametrize("detail", ["a" * 257, "é" * 128 + "a"])
def test_command_error_detail_rejects_values_above_256_utf8_bytes(detail: str) -> None:
    with pytest.raises(ProtocolValidationError, match="detail"):
        parse_device_message(_command_error_line(detail))


@pytest.mark.parametrize("detail", ["det\x00ail", "detail\x7f", "det\u0080ail"])
def test_command_error_detail_rejects_unicode_control_characters(detail: str) -> None:
    with pytest.raises(ProtocolValidationError, match="detail"):
        parse_device_message(_command_error_line(detail))


@pytest.mark.parametrize("detail", [None, 7, [], {}])
def test_command_error_detail_rejects_non_string_value(detail: object) -> None:
    with pytest.raises(ProtocolValidationError, match="detail"):
        parse_device_message(_command_error_line(detail))


def test_command_error_detail_rejects_unpaired_surrogate() -> None:
    with pytest.raises(ProtocolValidationError, match="detail"):
        parse_device_message(_command_error_line("\ud800"))


def test_rejects_unknown_command_error_code() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":false,"error":"unknown","detail":"nope"}')


def test_rejects_empty_command_error_detail() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":false,"error":"timeout","detail":""}')


def test_rejects_unexpected_command_error_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":false,"error":"timeout","detail":"timed out","extra":true}')


def test_rejects_non_boolean_command_response_ok() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":"true"}')


def test_rejects_unsupported_message_type_for_now() -> None:
    with pytest.raises(UnsupportedMessageTypeError):
        parse_device_message('{"type":"not_real"}')
