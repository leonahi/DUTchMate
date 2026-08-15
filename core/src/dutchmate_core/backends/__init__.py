"""Normalized Device Core backend contracts and adapters."""

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendDisconnectedError,
    BackendEvent,
    BackendEventSource,
    BackendInfo,
    BackendInputError,
    BackendMode,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)

__all__ = [
    "BackendCapability",
    "BackendDisconnectedError",
    "BackendEvent",
    "BackendEventSource",
    "BackendInfo",
    "BackendInputError",
    "BackendMode",
    "BufferOverflowEvent",
    "BufferStatusEvent",
    "SegmentContext",
    "SegmentTimestamp",
    "UartReceiveEvent",
]
