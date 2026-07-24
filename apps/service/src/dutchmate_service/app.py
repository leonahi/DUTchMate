"""FastAPI application factory for the Device Core Service."""

from __future__ import annotations

from typing import Protocol

from fastapi import FastAPI

from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.runtime import (
    DeviceCoreRuntime,
    DeviceCoreRuntimeError,
    DeviceCoreStatus,
)
from dutchmate_service.errors import register_error_handlers
from dutchmate_service.schemas import status_payload


class RuntimeStatusProvider(Protocol):
    """Runtime surface needed by the current service API."""

    def status(self) -> DeviceCoreStatus:
        """Return the current Device Core status."""


def create_app(runtime: RuntimeStatusProvider | None = None) -> FastAPI:
    """Create the Device Core Service application."""

    app = FastAPI(title="DUTchMate Device Core Service")
    register_error_handlers(app)
    runtime_provider = runtime or DeviceCoreRuntime(transport=_UnavailableTransport())

    @app.get("/status")
    def get_status() -> dict[str, object]:
        return status_payload(runtime_provider.status())

    return app


class _UnavailableTransport:
    def request(self, command: bytes) -> DeviceMessage:
        raise DeviceCoreRuntimeError("Serial transport is not implemented yet")
