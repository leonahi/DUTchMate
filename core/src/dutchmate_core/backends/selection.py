"""Profile-defined physical selection at the backend/discovery boundary."""

from collections.abc import Sequence
from dataclasses import replace

from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.device_connection.discovery import SerialPortCandidate, list_serial_ports
from dutchmate_core.validation import validate_serial_port


def select_backend_settings(
    settings: BackendSettings,
    *,
    candidates: Sequence[SerialPortCandidate] | None = None,
) -> BackendSettings:
    if settings.topology != "native_usb_console" or settings.usb_serial_number is None:
        return settings
    ports = list_serial_ports() if candidates is None else candidates
    matches = [
        port
        for port in ports
        if (
            port.vid == settings.usb_vid
            and port.pid == settings.usb_pid
            and port.serial_number == settings.usb_serial_number
        )
    ]
    if len(matches) != 1:
        reason = "ambiguous_device" if len(matches) > 1 else "device_not_found"
        raise ConnectionLifecycleError(
            "service_unavailable", "USB identity selection failed", reason=reason
        )
    return replace(settings, serial_port=validate_serial_port(matches[0].device))
