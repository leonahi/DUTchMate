import json
from pathlib import Path

import pytest

from dutchmate_core.device_connection.commands import (
    ConfigureGpioModeCommand,
    PulseControlCommand,
    SetControlStateCommand,
    UartSendCommand,
    configure_gpio_mode_command,
    pulse_control_command,
    set_control_state_command,
    uart_send_command,
    uart_send_text_command,
)
from dutchmate_core.device_connection.errors import ProtocolValidationError

EXAMPLES_DIR = Path(__file__).parents[3] / "hardware" / "protocol" / "v1" / "examples"


def test_build_configure_gpio_mode_command() -> None:
    command = configure_gpio_mode_command(
        channel="CTRL0",
        mode="open_drain",
        active_level="low",
    )

    assert command == ConfigureGpioModeCommand(
        channel="CTRL0",
        mode="open_drain",
        active_level="low",
    )
    assert command.to_payload() == {
        "cmd": "configure_gpio_mode",
        "channel": "CTRL0",
        "mode": "open_drain",
        "active_level": "low",
    }


def test_build_configure_gpio_mode_command_with_idle_level() -> None:
    command = configure_gpio_mode_command(
        channel="CTRL1",
        mode="push_pull",
        active_level="high",
        idle_level="low",
    )

    assert command.to_payload() == {
        "cmd": "configure_gpio_mode",
        "channel": "CTRL1",
        "mode": "push_pull",
        "active_level": "high",
        "idle_level": "low",
    }


def test_encode_configure_gpio_mode_command_as_ndjson() -> None:
    command = configure_gpio_mode_command(
        channel="CTRL0",
        mode="open_drain",
        active_level="low",
    )

    assert command.to_ndjson() == (
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0",'
        b'"mode":"open_drain","active_level":"low"}\n'
    )


def test_configure_gpio_mode_matches_canonical_example() -> None:
    command = configure_gpio_mode_command(
        channel="CTRL0",
        mode="open_drain",
        active_level="low",
    )
    example_payload = json.loads((EXAMPLES_DIR / "configure_gpio_mode.json").read_text())

    assert command.to_payload() == example_payload


def test_rejects_unknown_gpio_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command(
            channel="GPIO0",
            mode="open_drain",
            active_level="low",
        )


def test_rejects_unknown_gpio_mode() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command(
            channel="CTRL0",
            mode="floating",
            active_level="low",
        )


def test_rejects_unknown_gpio_active_level() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command(
            channel="CTRL0",
            mode="open_drain",
            active_level="asserted",
        )


def test_rejects_unknown_gpio_idle_level() -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command(
            channel="CTRL0",
            mode="open_drain",
            active_level="low",
            idle_level="released",
        )


@pytest.mark.parametrize(
    ("mode", "active_level", "idle_level"),
    [
        ("open_drain", "high", None),
        ("open_drain", "low", "high"),
        ("push_pull", "high", None),
        ("push_pull", "high", "high"),
    ],
)
def test_rejects_unsafe_gpio_electrical_combinations(
    mode: str,
    active_level: str,
    idle_level: str | None,
) -> None:
    with pytest.raises(ProtocolValidationError):
        configure_gpio_mode_command(
            channel="CTRL0",
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )


def test_build_pulse_control_command() -> None:
    command = pulse_control_command(channel="CTRL0")

    assert command == PulseControlCommand(channel="CTRL0", pulse_ms=100)
    assert command.to_payload() == {
        "cmd": "pulse_control",
        "channel": "CTRL0",
        "pulse_ms": 100,
    }


def test_encode_pulse_control_command_as_ndjson() -> None:
    command = pulse_control_command(channel="CTRL2", pulse_ms=250)

    assert command.to_ndjson() == (
        b'{"cmd":"pulse_control","channel":"CTRL2","pulse_ms":250}\n'
    )


def test_pulse_control_command_matches_canonical_example() -> None:
    command = pulse_control_command(channel="CTRL0")
    example_payload = json.loads((EXAMPLES_DIR / "pulse_control.json").read_text())

    assert command.to_payload() == example_payload


def test_pulse_control_rejects_unknown_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        pulse_control_command(channel="GPIO0")


def test_pulse_control_rejects_zero_pulse() -> None:
    with pytest.raises(ProtocolValidationError):
        pulse_control_command(channel="CTRL0", pulse_ms=0)


def test_pulse_control_rejects_pulse_above_limit() -> None:
    with pytest.raises(ProtocolValidationError):
        pulse_control_command(channel="CTRL0", pulse_ms=10001)


def test_pulse_control_rejects_boolean_pulse() -> None:
    with pytest.raises(ProtocolValidationError):
        pulse_control_command(channel="CTRL0", pulse_ms=True)


def test_build_set_control_state_command() -> None:
    command = set_control_state_command(channel="CTRL1", state="active")

    assert command == SetControlStateCommand(channel="CTRL1", state="active")
    assert command.to_payload() == {
        "cmd": "set_control_state",
        "channel": "CTRL1",
        "state": "active",
    }


def test_encode_set_control_state_command_as_ndjson() -> None:
    command = set_control_state_command(channel="CTRL3", state="idle")

    assert command.to_ndjson() == (
        b'{"cmd":"set_control_state","channel":"CTRL3","state":"idle"}\n'
    )


def test_set_control_state_command_matches_canonical_example() -> None:
    command = set_control_state_command(channel="CTRL1", state="active")
    example_payload = json.loads((EXAMPLES_DIR / "set_control_state.json").read_text())

    assert command.to_payload() == example_payload


def test_set_control_state_rejects_unknown_channel() -> None:
    with pytest.raises(ProtocolValidationError):
        set_control_state_command(channel="GPIO0", state="active")


def test_set_control_state_rejects_unknown_state() -> None:
    with pytest.raises(ProtocolValidationError):
        set_control_state_command(channel="CTRL1", state="bootloader")


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


def test_rejects_oversized_uart_send_bytes() -> None:
    with pytest.raises(ProtocolValidationError, match="1024"):
        uart_send_command(b"x" * 1025)


def test_uart_send_text_preserves_existing_crlf_and_completes_trailing_cr() -> None:
    assert uart_send_text_command("go\r\n").data == b"go\r\n"
    assert uart_send_text_command("go\r").data == b"go\r\n"
