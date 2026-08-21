"""HTTP error mapping for the Device Core Service."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from dutchmate_core.backends.contracts import BackendInputError
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.diagnostics import project_diagnostic_detail
from dutchmate_core.gpio_config.config import GpioConfigError
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.models import SessionPersistenceError, SessionQueryError
from dutchmate_core.validation import InputValidationError, UartSendValidationError
from dutchmate_core.workflows.capture import CaptureReconnectError
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_core.workflows.uart_send import UartSendError


@dataclass(frozen=True, slots=True)
class ServiceError:
    """HTTP-facing service error response."""

    error: str
    detail: str
    status_code: int
    detail_truncated: bool = False
    context: dict[str, object] | None = None

    def payload(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "ok": False,
            "error": self.error,
            "detail": self.detail,
            "detail_truncated": self.detail_truncated,
        }
        if self.context is not None:
            payload["context"] = self.context
        return payload


def service_error_from_exception(exc: Exception) -> ServiceError:
    """Map known core exceptions to the service error contract."""

    if isinstance(exc, DeviceActionError):
        return _service_error(
            error=exc.error,
            detail=exc.detail,
            status_code=_status_for_error(exc.error),
            context=exc.context,
        )

    if isinstance(exc, UartSendError):
        return _service_error(
            error=exc.error,
            detail=exc.detail,
            status_code=_status_for_error(exc.error),
            context=exc.context,
        )

    if isinstance(exc, UartSendValidationError):
        context: dict[str, object] | None = (
            {
                "actual_bytes": exc.actual_bytes,
                "max_bytes": exc.max_bytes,
            }
            if exc.actual_bytes is not None
            else None
        )
        return _service_error(
            error="invalid_argument",
            detail=str(exc),
            status_code=400,
            context=context,
        )

    if isinstance(exc, SessionPersistenceError):
        return _service_error(error=exc.error, detail=str(exc), status_code=500)

    if isinstance(exc, SessionQueryError):
        return _service_error(
            error=exc.error,
            detail=str(exc),
            status_code=_status_for_error(exc.error),
            context=_session_query_context(exc),
        )

    if isinstance(exc, CaptureReconnectError):
        return _service_error(
            error=exc.error,
            detail=str(exc),
            status_code=503,
            context=_reconnect_context(exc),
        )

    if isinstance(exc, BackendInputError):
        return _service_error(error=exc.error, detail=str(exc), status_code=502)

    if isinstance(exc, GpioConfigurationError):
        return _service_error(error="not_configured", detail=str(exc), status_code=409)

    if isinstance(exc, DeviceCoreRuntimeError):
        return _service_error(error="service_unavailable", detail=str(exc), status_code=503)

    if isinstance(exc, RequestValidationError):
        return _service_error(
            error="invalid_argument",
            detail="Request validation failed",
            status_code=400,
        )

    if isinstance(exc, ProtocolValidationError | GpioConfigError | ValueError):
        return _service_error(error="invalid_argument", detail=str(exc), status_code=400)

    return _service_error(
        error="internal_error",
        detail="Internal service error",
        status_code=500,
    )


def _service_error(
    *,
    error: str,
    detail: str,
    status_code: int,
    context: dict[str, object] | None = None,
) -> ServiceError:
    projected_detail, truncated = project_diagnostic_detail(
        fallback_code=error,
        detail=detail,
    )
    return ServiceError(
        error=error,
        detail=projected_detail,
        status_code=status_code,
        detail_truncated=truncated,
        context=context,
    )


def _reconnect_context(exc: CaptureReconnectError) -> dict[str, object] | None:
    if (
        exc.end_reason == "reconnect_timeout"
        and exc.operation is not None
        and exc.session_id is not None
        and exc.reconnect_timeout_s is not None
    ):
        return {
            "operation": exc.operation,
            "session_id": exc.session_id,
            "reconnect_timeout_s": exc.reconnect_timeout_s,
        }
    if (
        exc.end_reason == "reconnect_limit"
        and exc.operation is not None
        and exc.session_id is not None
        and exc.segment_count is not None
        and exc.max_segments is not None
    ):
        return {
            "operation": exc.operation,
            "session_id": exc.session_id,
            "segment_count": exc.segment_count,
            "max_segments": exc.max_segments,
        }
    return None


def _session_query_context(exc: SessionQueryError) -> dict[str, object]:
    context: dict[str, object] = {"operation": exc.operation}
    if exc.session_id is not None:
        context["session_id"] = exc.session_id
    if exc.error == "unsupported_session_schema":
        context.update(
            {
                "detected_schema_version": exc.detected_schema_version,
                "supported_schema_versions": [1],
            }
        )
    return context


def register_error_handlers(app: FastAPI) -> None:
    """Register service exception handlers on an app."""

    @app.exception_handler(DeviceActionError)
    async def handle_device_action_error(
        request: Request,
        exc: DeviceActionError,
    ) -> JSONResponse:
        return _json_response(service_error_from_exception(exc))

    @app.exception_handler(UartSendError)
    async def handle_uart_send_error(
        request: Request,
        exc: UartSendError,
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

    @app.exception_handler(SessionQueryError)
    async def handle_session_query_error(
        request: Request,
        exc: SessionQueryError,
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
    if error == "not_found":
        return 404
    if error == "unsupported_session_schema":
        return 409
    if error == "persistence_fault":
        return 500
    if error in {"not_configured", "capture_active", "unsupported_capability"}:
        return 409
    if error in {"timeout", "hardware_fault"}:
        return 502
    return 400
