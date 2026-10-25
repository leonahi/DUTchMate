"""Normalized connection ownership contract; no transport or delivery dependencies."""

from dataclasses import dataclass
from typing import Literal, Protocol

ConnectionState = Literal[
    "disconnected", "connecting", "connected", "reconnecting", "released", "reacquiring", "faulted"
]


class ConnectionLifecycleError(RuntimeError):
    def __init__(self, error: str, detail: str, *, reason: str | None = None) -> None:
        super().__init__(detail)
        self.error = error
        self.context: dict[str, object] = {"reason": reason} if reason else {}


@dataclass(frozen=True, slots=True)
class ConnectionBoundary:
    connection_state: ConnectionState
    session_id: str
    segment_id: int


class ConnectionOwner(Protocol):
    @property
    def failure(self) -> ConnectionLifecycleError | None: ...

    def release(self) -> None: ...
    def reacquire(self) -> None: ...
    def cancel_pending(self) -> None: ...
