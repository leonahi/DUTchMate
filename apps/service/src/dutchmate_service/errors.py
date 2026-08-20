"""HTTP error mapping for the Device Core Service."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dutchmate_core.backends.contracts import BackendInputError
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.gpio_config.config import GpioConfigError
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.validation import InputValidationError
from dutchmate_core.workflows.capture import CaptureReconnectError
from dutchmate_core.workflows.device_actions import DeviceActionError


@dataclass(frozen=True, slots=True)
class ServiceError:
    """HTTP-facing service error response."""

    error: str
    detail: str
    status_code: int

    def payload(self) -> dict[str, object]:
        return {
            "ok": False,
            "error": self.error,
            "detail": self.detail,
        }


def service_error_from_exception(exc: Exception) -> ServiceError:
    """Map known core exceptions to the service error contract."""

    if isinstance(exc, DeviceActionError):
        return ServiceError(
            error=exc.error,
            detail=exc.detail,
            status_code=_status_for_error(exc.error),
        )

    if isinstance(exc, SessionPersistenceError):
        return ServiceError(error=exc.error, detail=str(exc), status_code=500)

    if isinstance(exc, CaptureReconnectError):
        return ServiceError(error=exc.error, detail=str(exc), status_code=503)

    if isinstance(exc, BackendInputError):
        return ServiceError(error=exc.error, detail=str(exc), status_code=502)

    if isinstance(exc, GpioConfigurationError):
        return ServiceError(error="not_configured", detail=str(exc), status_code=409)

    if isinstance(exc, DeviceCoreRuntimeError):
        return ServiceError(error="service_unavailable", detail=str(exc), status_code=503)

    if isinstance(exc, RequestValidationError):
        return ServiceError(
            error="invalid_argument",
            detail="Request validation failed",
            status_code=400,
        )

    if isinstance(exc, ProtocolValidationError | GpioConfigError | ValueError):
        return ServiceError(error="invalid_argument", detail=str(exc), status_code=400)

    return ServiceError(error="internal_error", detail="Internal service error", status_code=500)


def register_error_handlers(app: FastAPI) -> None:
    """Register service exception handlers on an app."""

    @app.exception_handler(DeviceActionError)
    async def handle_device_action_error(
        request: Request,
        exc: DeviceActionError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(GpioConfigurationError)
    async def handle_gpio_configuration_error(
        request: Request,
        exc: GpioConfigurationError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(DeviceCoreRuntimeError)
    async def handle_runtime_error(
        request: Request,
        exc: DeviceCoreRuntimeError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(SessionPersistenceError)
    async def handle_session_persistence_error(
        request: Request,
        exc: SessionPersistenceError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(CaptureReconnectError)
    async def handle_capture_reconnect_error(
        request: Request,
        exc: CaptureReconnectError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(BackendInputError)
    async def handle_backend_input_error(
        request: Request,
        exc: BackendInputError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(ProtocolValidationError)
    async def handle_protocol_validation_error(
        request: Request,
        exc: ProtocolValidationError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(InputValidationError)
    async def handle_input_validation_error(
        request: Request,
        exc: InputValidationError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(GpioConfigError)
    async def handle_gpio_config_error(
        request: Request,
        exc: GpioConfigError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))


def _json_response(error: ServiceError) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.payload())


def _status_for_error(error: str) -> int:
    if error == "invalid_argument":
        return 400
    if error in {"not_configured", "capture_active"}:
        return 409
    if error in {"timeout", "hardware_fault"}:
        return 502
    return 400
