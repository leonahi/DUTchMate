import json
from pathlib import Path

import pytest

from dutchmate_core.device_connection.commands import (
    BootModeCommand,
    ConfigureGpioModeCommand,
    ResetCommand,
    UartSendCommand,
    boot_mode_command,
    configure_gpio_mode_command,
    reset_command,
    uart_send_command,
    uart_send_text_command,
)
from dutchmate_core.device_connection.errors import ProtocolValidationError

EXAMPLES_DIR = Path(__file__).parents[3] / "hardware" / "protocol" / "v1" / "examples"


def test_build_configure_gpio_mode_command() -> None:
    command = configure_gpio_mode_command("reset", "open_drain")

    assert command == ConfigureGpioModeCommand(pin="reset", mode="open_drain")
    assert command.to_payload() == {
        "cmd": "configure_gpio_mode",
        "pin": "reset",
        "mode": "open_drain",
    }


def test_encode_configure_gpio_mode_command_as_ndjson() -> None:
    command = configure_gpio_mode_command("reset", "open_drain")

    assert command.to_ndjson() == b'{"cmd":"configure_gpio_mode","pin":"reset","mode":"open_drain"}\n'


def test_configure_gpio_mode_matches_canonical_example() -> None:
    command = configure_gpio_mode_command("reset", "open_drain")
    example_payload = json.loads((EXAMPLES_DIR / "configure_gpio_mode.json").read_text())

    assert command.to_payload() == example_payload


def test_rejects_unknown_gpio_pin() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command("power", "open_drain")


def test_rejects_unknown_gpio_mode() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command("reset", "floating")


def test_build_reset_command() -> None:
    command = reset_command()

    assert command == ResetCommand(pulse_ms=100)
    assert command.to_payload() == {
        "cmd": "reset",
        "pulse_ms": 100,
    }


def test_encode_reset_command_as_ndjson() -> None:
    command = reset_command(250)

    assert command.to_ndjson() == b'{"cmd":"reset","pulse_ms":250}\n'


def test_reset_command_matches_canonical_example() -> None:
    command = reset_command()
    example_payload = json.loads((EXAMPLES_DIR / "reset.json").read_text())

    assert command.to_payload() == example_payload


def test_rejects_zero_reset_pulse() -> None:
    with pytest.raises(ProtocolValidationError):
        reset_command(0)


def test_rejects_reset_pulse_above_limit() -> None:
    with pytest.raises(ProtocolValidationError):
        reset_command(10001)


def test_rejects_boolean_reset_pulse() -> None:
    with pytest.raises(ProtocolValidationError):
        reset_command(True)


def test_build_boot_mode_command() -> None:
    command = boot_mode_command("bootloader")

    assert command == BootModeCommand(mode="bootloader")
    assert command.to_payload() == {
        "cmd": "set_boot_mode",
        "mode": "bootloader",
    }


def test_encode_boot_mode_command_as_ndjson() -> None:
    command = boot_mode_command("normal")

    assert command.to_ndjson() == b'{"cmd":"set_boot_mode","mode":"normal"}\n'


def test_boot_mode_command_matches_canonical_example() -> None:
    command = boot_mode_command("bootloader")
    example_payload = json.loads((EXAMPLES_DIR / "set_boot_mode.json").read_text())

    assert command.to_payload() == example_payload


def test_rejects_unknown_boot_mode() -> None:
    with pytest.raises(ProtocolValidationError):
        boot_mode_command("dfu")


def test_build_uart_send_command_from_bytes() -> None:
    command = uart_send_command(b"reboot\n")

    assert command == UartSendCommand(data=b"reboot\n")
    assert command.to_payload() == {
        "cmd": "uart_send",
        "data_b64": "cmVib290Cg==",
    }


def test_build_uart_send_text_command_appends_newline() -> None:
    command = uart_send_text_command("reboot")

    assert command == UartSendCommand(data=b"reboot\n")


def test_build_uart_send_text_command_can_preserve_text_without_newline() -> None:
    command = uart_send_text_command("reboot", append_newline=False)

    assert command == UartSendCommand(data=b"reboot")


def test_encode_uart_send_command_as_ndjson() -> None:
    command = uart_send_command(b"reboot\n")

    assert command.to_ndjson() == b'{"cmd":"uart_send","data_b64":"cmVib290Cg=="}\n'


def test_uart_send_command_matches_canonical_example() -> None:
    command = uart_send_command(b"reboot\n")
    example_payload = json.loads((EXAMPLES_DIR / "uart_send.json").read_text())

    assert command.to_payload() == example_payload


def test_rejects_empty_uart_send_bytes() -> None:
    with pytest.raises(ProtocolValidationError):
        uart_send_command(b"")


def test_rejects_non_bytes_uart_send_data() -> None:
    with pytest.raises(ProtocolValidationError):
        uart_send_command("reboot")  # type: ignore[arg-type]
