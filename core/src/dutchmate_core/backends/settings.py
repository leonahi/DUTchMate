"""Physical backend settings projected from an effective DUT Profile."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

from dutchmate_core.backends.contracts import BackendMode

DEFAULT_BASIC_BAUDRATE: Final = 115200
ENHANCED_BAUDRATE: Final = 460800
DEFAULT_RECONNECT_TIMEOUT_S: Final = 5.0


@dataclass(frozen=True, slots=True)
class BackendSettings:
    """Complete settings consumed by one physical backend adapter."""

    mode: BackendMode
    serial_port: str | None
    reconnect_timeout_s: float
    baudrate: int
    data_bits: int
    parity: str
    stop_bits: int
    tx_enabled: bool
    rtscts: bool = False
    xonxoff: bool = False
