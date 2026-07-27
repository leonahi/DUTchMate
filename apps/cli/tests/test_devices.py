from __future__ import annotations

from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.devices import format_devices
from dutchmate_core.device_connection.discovery import SerialPortCandidate


def test_format_devices_reports_no_ports() -> None:
    assert format_devices([]) == "No serial ports found."


def test_format_devices_renders_serial_metadata() -> None:
    output = format_devices(
        [
            SerialPortCandidate(
                device="/dev/ttyACM0",
                description="DUTchMate Debug Helper",
                hwid="USB VID:PID=2E8A:000A",
                vid=0x2E8A,
                pid=0x000A,
                manufacturer="DUTchMate",
                product="Debug Helper",
                serial_number="ABC123",
                is_dutchmate_hint=True,
            )
        ]
    )

    assert output == (
        "Serial ports:\n"
        "  /dev/ttyACM0 dutchmate_hint: DUTchMate Debug Helper "
        "(vid:pid=2E8A:000A, manufacturer=DUTchMate, product=Debug Helper, serial=ABC123)"
    )


def test_devices_command_lists_dutchmate_candidates(monkeypatch) -> None:
    candidate = SerialPortCandidate(
        device="/dev/ttyACM0",
        description="DUTchMate Debug Helper",
        hwid="USB VID:PID=2E8A:000A",
        is_dutchmate_hint=True,
    )
    monkeypatch.setattr(main, "list_dutchmate_candidates", lambda: [candidate])
    monkeypatch.setattr(main, "format_devices", lambda candidates: f"{len(candidates)} device")

    result = CliRunner().invoke(main.app, ["devices"])

    assert result.exit_code == 0
    assert result.output == "1 device\n"


def test_devices_command_can_list_all_serial_ports(monkeypatch) -> None:
    monkeypatch.setattr(
        main,
        "list_serial_ports",
        lambda: [
            SerialPortCandidate(
                device="/dev/ttyUSB0",
                description="Generic USB Serial",
                hwid="USB VID:PID=1234:5678",
            )
        ],
    )
    monkeypatch.setattr(main, "format_devices", lambda candidates: f"{len(candidates)} port")

    result = CliRunner().invoke(main.app, ["devices", "--all"])

    assert result.exit_code == 0
    assert result.output == "1 port\n"
