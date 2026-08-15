from __future__ import annotations

import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.devices import DeviceSelectionError, format_devices, resolve_start_serial_port
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
        "  /dev/ttyACM0 [enhanced_candidate]: DUTchMate Debug Helper "
        "(vid:pid=2E8A:000A, manufacturer=DUTchMate, product=Debug Helper, serial=ABC123)"
    )


def test_format_devices_labels_unverified_generic_port() -> None:
    output = format_devices(
        [
            SerialPortCandidate(
                device="/dev/ttyUSB0",
                description="Generic USB Serial",
                hwid="USB VID:PID=1234:5678",
            )
        ]
    )

    assert output == "Serial ports:\n  /dev/ttyUSB0 [generic]: Generic USB Serial"


def test_resolve_start_serial_port_uses_explicit_port() -> None:
    assert resolve_start_serial_port("/dev/ttyACM9", []) == "/dev/ttyACM9"


def test_resolve_start_serial_port_returns_none_without_candidates() -> None:
    assert resolve_start_serial_port(None, []) is None


def test_resolve_start_serial_port_auto_selects_single_candidate() -> None:
    assert (
        resolve_start_serial_port(
            None,
            [
                SerialPortCandidate(
                    device="/dev/ttyACM0",
                    description="DUTchMate Debug Helper",
                    hwid="USB VID:PID=2E8A:000A",
                )
            ],
        )
        == "/dev/ttyACM0"
    )


def test_resolve_start_serial_port_rejects_multiple_candidates() -> None:
    candidates = [
        SerialPortCandidate(
            device="/dev/ttyACM0",
            description="DUTchMate Debug Helper",
            hwid="USB VID:PID=2E8A:000A",
        ),
        SerialPortCandidate(
            device="/dev/ttyACM1",
            description="DUTchMate Debug Helper",
            hwid="USB VID:PID=2E8A:000A",
        ),
    ]

    with pytest.raises(DeviceSelectionError) as error:
        resolve_start_serial_port(None, candidates)

    assert str(error.value) == (
        "Multiple DUTchMate serial devices found: /dev/ttyACM0, /dev/ttyACM1. "
        "Run 'dutchmate devices' and pass --serial-port."
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
