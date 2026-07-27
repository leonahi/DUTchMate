from dataclasses import dataclass

from dutchmate_core.device_connection.discovery import (
    SerialPortCandidate,
    list_dutchmate_candidates,
    list_serial_ports,
)


@dataclass(frozen=True, slots=True)
class FakePort:
    device: str
    description: str
    hwid: str
    vid: int | None = None
    pid: int | None = None
    serial_number: str | None = None
    manufacturer: str | None = None
    product: str | None = None
    interface: str | None = None
    location: str | None = None


def test_list_serial_ports_normalizes_port_metadata() -> None:
    ports = list_serial_ports(
        comports_provider=lambda: [
            FakePort(
                device="/dev/ttyACM0",
                description="USB Serial",
                hwid="USB VID:PID=2E8A:000A",
                vid=0x2E8A,
                pid=0x000A,
                serial_number="ABC123",
                manufacturer="DUTchMate",
                product="Debug Helper",
                interface="CDC",
                location="1-1",
            )
        ]
    )

    assert ports == [
        SerialPortCandidate(
            device="/dev/ttyACM0",
            description="USB Serial",
            hwid="USB VID:PID=2E8A:000A",
            vid=0x2E8A,
            pid=0x000A,
            serial_number="ABC123",
            manufacturer="DUTchMate",
            product="Debug Helper",
            interface="CDC",
            location="1-1",
            is_dutchmate_hint=True,
        )
    ]


def test_list_dutchmate_candidates_filters_by_text_hint() -> None:
    candidates = list_dutchmate_candidates(
        comports_provider=lambda: [
            FakePort(
                device="/dev/ttyACM0",
                description="DUTchMate Debug Helper",
                hwid="USB VID:PID=2E8A:000A",
            ),
            FakePort(
                device="/dev/ttyUSB0",
                description="Generic USB Serial",
                hwid="USB VID:PID=1234:5678",
            ),
        ]
    )

    assert [candidate.device for candidate in candidates] == ["/dev/ttyACM0"]


def test_list_serial_ports_preserves_non_dutchmate_ports() -> None:
    ports = list_serial_ports(
        comports_provider=lambda: [
            FakePort(
                device="/dev/ttyUSB0",
                description="Generic USB Serial",
                hwid="USB VID:PID=1234:5678",
            )
        ]
    )

    assert ports[0].is_dutchmate_hint is False
