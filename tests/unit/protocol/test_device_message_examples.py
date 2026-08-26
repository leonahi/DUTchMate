from pathlib import Path

from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import parse_device_message

EXAMPLES_DIR = Path(__file__).parents[3] / "hardware" / "protocol" / "v1" / "examples"


def parse_example(filename: str):
    return parse_device_message((EXAMPLES_DIR / filename).read_text())


def test_parse_hello_example() -> None:
    assert parse_example("hello.json") == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_receive", "gpio_control", "uart_send"),
    )


def test_parse_uart_event_example() -> None:
    assert parse_example("uart_event.json") == UartMessage(
        channel=0,
        timestamp_us=182341200,
        data=b"BOOT_OK\n",
        text="BOOT_OK\n",
    )


def test_parse_buffer_overflow_example() -> None:
    assert parse_example("buffer_overflow.json") == BufferOverflowMessage(
        channel=0,
        timestamp_us=182350000,
        dropped_bytes=512,
    )


def test_parse_buffer_status_example() -> None:
    assert parse_example("buffer_status.json") == BufferStatusMessage(
        timestamp_us=182360000,
        uart_rx_size_bytes=32768,
        uart_rx_used_bytes=4096,
        uart_rx_high_water_bytes=18432,
        dropped_bytes_total=512,
        overflow_events=1,
    )


def test_parse_success_response_example() -> None:
    assert parse_example("success_response.json") == CommandSuccessMessage(
        timestamp_us=182334400,
    )


def test_parse_error_response_example() -> None:
    assert parse_example("error_response.json") == CommandErrorMessage(
        error="not_configured",
        detail="CTRL0 is not configured",
    )
