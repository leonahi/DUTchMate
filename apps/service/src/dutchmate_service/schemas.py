"""Service response serialization helpers."""

from __future__ import annotations

from dataclasses import asdict

from dutchmate_core.runtime import DeviceCoreStatus


def status_payload(status: DeviceCoreStatus) -> dict[str, object]:
    """Serialize a Device Core status snapshot for the HTTP API."""

    return {
        "connected": status.connected,
        "port": status.port,
        "firmware": status.firmware,
        "device": status.device,
        "capabilities": list(status.capabilities),
        "active_session_id": status.active_session_id,
        "gpio_modes": {
            role: asdict(role_status) for role, role_status in status.gpio_modes.items()
        },
    }
