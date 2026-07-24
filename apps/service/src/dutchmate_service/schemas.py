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
        "control_channels": {
            channel: asdict(channel_status)
            for channel, channel_status in status.control_channels.items()
        },
    }
