"""Serial port discovery helpers for DUTchMate Debug Helper candidates."""

from __future__ import annotations

import importlib
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Protocol, cast


class ListPortInfo(Protocol):
    """pyserial list-port metadata used by discovery."""

    device: str
    description: str
    hwid: str
    vid: int | None
    pid: int | None
    serial_number: str | None
    manufacturer: str | None
    product: str | None
    interface: str | None
    location: str | None


ComportsProvider = Callable[[], Iterable[ListPortInfo]]


@dataclass(frozen=True, slots=True)
class SerialPortCandidate:
    """One serial port that may be a DUTchMate Debug Helper."""

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
    is_dutchmate_hint: bool = False


def list_serial_ports(
    *,
    comports_provider: ComportsProvider | None = None,
) -> list[SerialPortCandidate]:
    """List available serial ports with normalized metadata."""

    provider = comports_provider or _pyserial_comports_provider()
    return [_candidate_from_port(port) for port in provider()]


def list_dutchmate_candidates(
    *,
    comports_provider: ComportsProvider | None = None,
) -> list[SerialPortCandidate]:
    """List serial ports whose metadata hints at a DUTchMate Debug Helper."""

    return [
        candidate
        for candidate in list_serial_ports(comports_provider=comports_provider)
        if candidate.is_dutchmate_hint
    ]


def _candidate_from_port(port: ListPortInfo) -> SerialPortCandidate:
    text_fields = (
        port.device,
        port.description,
        port.hwid,
        port.manufacturer,
        port.product,
        port.interface,
    )
    return SerialPortCandidate(
        device=port.device,
        description=port.description,
        hwid=port.hwid,
        vid=port.vid,
        pid=port.pid,
        serial_number=port.serial_number,
        manufacturer=port.manufacturer,
        product=port.product,
        interface=port.interface,
        location=port.location,
        is_dutchmate_hint=_has_dutchmate_text_hint(text_fields),
    )


def _has_dutchmate_text_hint(values: Iterable[str | None]) -> bool:
    return any("dutchmate" in value.lower() for value in values if value)


def _pyserial_comports_provider() -> ComportsProvider:
    list_ports_module = importlib.import_module("serial.tools.list_ports")
    return cast(ComportsProvider, list_ports_module.comports)
