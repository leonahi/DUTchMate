from pathlib import Path

from fastapi.testclient import TestClient

from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.gpio_config.config import GpioConfigError
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.validation import InputValidationError
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.app import create_app
from dutchmate_service.errors import ServiceError, service_error_from_exception


def test_service_error_payload_shape() -> None:
    error = ServiceError(
        error="invalid_argument",
        detail="bad input",
        status_code=400,
    )

    assert error.payload() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "bad input",
    }


def test_maps_device_action_error_with_embedded_code() -> None:
    error = service_error_from_exception(
        DeviceActionError(error="hardware_fault", detail="reset driver failed")
    )

    assert error == ServiceError(
        error="hardware_fault",
        detail="reset driver failed",
        status_code=502,
    )


def test_maps_not_configured_workflow_error() -> None:
    error = service_error_from_exception(
        GpioConfigurationError("GPIO role 'reset' is not configured")
    )

    assert error == ServiceError(
        error="not_configured",
        detail="GPIO role 'reset' is not configured",
        status_code=409,
    )


def test_maps_runtime_error_to_service_unavailable() -> None:
    error = service_error_from_exception(DeviceCoreRuntimeError("Debug Helper is not connected"))

    assert error == ServiceError(
        error="service_unavailable",
        detail="Debug Helper is not connected",
        status_code=503,
    )


def test_maps_session_persistence_error_to_server_fault() -> None:
    error = service_error_from_exception(
        SessionPersistenceError(
            operation="append",
            path=Path("uart_events.jsonl"),
            detail="disk full",
        )
    )

    assert error == ServiceError(
        error="persistence_fault",
        detail="session persistence append failed for uart_events.jsonl: disk full",
        status_code=500,
    )


def test_maps_validation_errors_to_invalid_argument() -> None:
    protocol_error = service_error_from_exception(ProtocolValidationError("bad protocol"))
    input_error = service_error_from_exception(InputValidationError("bad input"))
    config_error = service_error_from_exception(GpioConfigError("bad config"))

    assert protocol_error == ServiceError(
        error="invalid_argument",
        detail="bad protocol",
        status_code=400,
    )
    assert input_error == ServiceError(
        error="invalid_argument",
        detail="bad input",
        status_code=400,
    )
    assert config_error == ServiceError(
        error="invalid_argument",
        detail="bad config",
        status_code=400,
    )


def test_exception_handlers_return_json_error_response() -> None:
    app = create_app()

    @app.get("/raise-not-configured")
    def raise_not_configured() -> None:
        raise GpioConfigurationError("GPIO role 'reset' is not configured")

    response = TestClient(app).get("/raise-not-configured")

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "not_configured",
        "detail": "GPIO role 'reset' is not configured",
    }


def test_input_validation_handler_returns_json_error_response() -> None:
    app = create_app()

    @app.get("/raise-invalid-input")
    def raise_invalid_input() -> None:
        raise InputValidationError("bad input")

    response = TestClient(app).get("/raise-invalid-input")

    assert response.status_code == 400
    assert response.json() == {
        "ok": False,
        "error": "invalid_argument",
        "detail": "bad input",
    }


def test_exception_handlers_preserve_firmware_error_code() -> None:
    app = create_app()

    @app.get("/raise-firmware-error")
    def raise_firmware_error() -> None:
        raise DeviceActionError(error="capture_active", detail="capture is already active")

    response = TestClient(app).get("/raise-firmware-error")

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "capture_active",
        "detail": "capture is already active",
    }
