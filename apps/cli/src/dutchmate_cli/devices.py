"""Terminal formatting for serial device discovery."""

from __future__ import annotations

from collections.abc import Sequence

from dutchmate_core.device_connection.discovery import SerialPortCandidate


class DeviceSelectionError(RuntimeError):
    """Raised when the CLI cannot choose one Debug Helper serial port."""


def format_devices(candidates: Sequence[SerialPortCandidate]) -> str:
    """Format discovered serial ports for CLI output."""

    if not candidates:
        return "No serial ports found."

    lines = ["Serial ports:"]
    for candidate in candidates:
        hint = " dutchmate_hint" if candidate.is_dutchmate_hint else ""
        metadata = _format_metadata(candidate)
        lines.append(f"  {candidate.device}{hint}: {candidate.description}{metadata}")
    return "\n".join(lines)


def resolve_start_serial_port(
    explicit_serial_port: str | None,
    candidates: Sequence[SerialPortCandidate],
) -> str | None:
    """Resolve the serial port used by `dutchmate start`."""

    if explicit_serial_port is not None:
        return explicit_serial_port
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0].device

    devices = ", ".join(candidate.device for candidate in candidates)
    raise DeviceSelectionError(
        f"Multiple DUTchMate serial devices found: {devices}. "
        "Run 'dutchmate devices' and pass --serial-port."
    )


def _format_metadata(candidate: SerialPortCandidate) -> str:
    parts: list[str] = []
    if candidate.vid is not None and candidate.pid is not None:
        parts.append(f"vid:pid={candidate.vid:04X}:{candidate.pid:04X}")
    if candidate.manufacturer:
        parts.append(f"manufacturer={candidate.manufacturer}")
    if candidate.product:
        parts.append(f"product={candidate.product}")
    if candidate.serial_number:
        parts.append(f"serial={candidate.serial_number}")

    if not parts:
        return ""
    return f" ({', '.join(parts)})"
