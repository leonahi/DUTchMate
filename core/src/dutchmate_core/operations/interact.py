"""Interact's TX facts alongside the common bounded observation result."""

from dataclasses import dataclass

from dutchmate_core.operations.monitor import MonitorResult
from dutchmate_core.workflows.uart_send import UartSendResult


@dataclass(frozen=True, slots=True)
class InteractResult(MonitorResult):
    """One bounded interaction, including an exact payload and known TX result."""

    data_b64: str
    transformation: dict[str, object]
    tx: UartSendResult | None
    tx_error: dict[str, object] | None
