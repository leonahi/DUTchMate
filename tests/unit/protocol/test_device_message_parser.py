import json

import pytest

from dutchmate_core.device_connection.errors import (
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


def test_parse_valid_hello_message() -> None:
    message = parse_device_message(
        json.dumps(
            {
                "type": "hello",
                "v": 1,
                "firmware": "0.1.0",
                "device": "dutchmate-rp2040",
                "capabilities": ["uart_capture", "gpio_control", "uart_send"],
            }
        )
    )

    assert message == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control", "uart_send"),
    )


def test_parse_hello_from_bytes() -> None:
    message = parse_device_message(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[]}'
    )

    assert message == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=(),
    )


def test_rejects_malformed_json() -> None:
    with pytest.raises(MalformedMessageError):
        parse_device_message('{"type":"hello"')


def test_rejects_non_object_json() -> None:
    with pytest.raises(MalformedMessageError):
        parse_device_message("[]")


def test_rejects_protocol_version_mismatch() -> None:
    with pytest.raises(ProtocolVersionError):
        parse_device_message(
            '{"type":"hello","v":2,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[]}'
        )


def test_rejects_boolean_protocol_version() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":true,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[]}'
        )


def test_rejects_unknown_capability() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":["unknown"]}'
        )


def test_rejects_duplicate_capability() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":["uart_capture","uart_capture"]}'
        )


def test_rejects_unexpected_hello_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message(
            '{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[],"extra":true}'
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


def test_rejects_negative_command_success_timestamp() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":true,"timestamp_us":-1}')


def test_rejects_unexpected_command_success_field() -> None:
    with pytest.raises(ProtocolValidationError):
        parse_device_message('{"ok":true,"timestamp_us":1,"extra":true}')


def test_parse_command_error_message() -> None:
    message = parse_device_message(
        '{"ok":false,"error":"not_configured","detail":"configure_gpio_mode not called for reset pin"}'
    )

    assert message == CommandErrorMessage(
        error="not_configured",
        detail="configure_gpio_mode not called for reset pin",
    )


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
