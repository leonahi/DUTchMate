from pathlib import Path

from fastapi.testclient import TestClient

from dutchmate_core.backends import BackendInputError
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.gpio_config.config import GpioConfigError
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import DeviceCoreRuntimeError
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.validation import GpioIdentifierValidationError, InputValidationError
from dutchmate_core.workflows.capture import CaptureReconnectError
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
        "detail_truncated": False,
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
        GpioConfigurationError(
            "GPIO role 'reset' is not configured",
            operation="reset",
            required_role="reset",
            role_state="unconfigured",
        )
    )

    assert error == ServiceError(
        error="not_configured",
        detail="GPIO role 'reset' is not configured",
        status_code=409,
        context={
            "operation": "reset",
            "required_role": "reset",
            "role_state": "unconfigured",
        },
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


def test_maps_reconnect_error_to_service_unavailable() -> None:
    error = service_error_from_exception(
        CaptureReconnectError(
            end_reason="reconnect_timeout",
            detail="Backend did not reconnect before the reconnect deadline",
            operation="capture",
            session_id="20260820T120000Z-a1b2c3d4",
            reconnect_timeout_s=5.0,
        )
    )

    assert error == ServiceError(
        error="service_unavailable",
        detail="Backend did not reconnect before the reconnect deadline",
        status_code=503,
        context={
            "operation": "capture",
            "session_id": "20260820T120000Z-a1b2c3d4",
            "reconnect_timeout_s": 5.0,
        },
    )
    assert error.payload() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Backend did not reconnect before the reconnect deadline",
        "detail_truncated": False,
        "context": {
            "operation": "capture",
            "session_id": "20260820T120000Z-a1b2c3d4",
            "reconnect_timeout_s": 5.0,
        },
    }


def test_maps_reconnect_limit_with_exact_context() -> None:
    error = service_error_from_exception(
        CaptureReconnectError(
            end_reason="reconnect_limit",
            detail="Session reached the 32-segment reconnect limit",
            operation="boot_test",
            session_id="20260820T120000Z-a1b2c3d4",
            segment_count=32,
            max_segments=32,
        )
    )

    assert error.payload() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": "Session reached the 32-segment reconnect limit",
        "detail_truncated": False,
        "context": {
            "operation": "boot_test",
            "session_id": "20260820T120000Z-a1b2c3d4",
            "segment_count": 32,
            "max_segments": 32,
        },
    }


def test_service_error_sanitizes_and_bounds_diagnostic_detail() -> None:
    error = service_error_from_exception(ValueError("start\n" + "é" * 600 + "\x00end"))

    assert error.error == "invalid_argument"
    assert error.detail.startswith("start ")
    assert "\n" not in error.detail
    assert "\x00" not in error.detail
    assert len(error.detail.encode("utf-8")) <= 1024
    assert error.detail_truncated is True


def test_maps_backend_input_error_to_bad_gateway() -> None:
    error = service_error_from_exception(BackendInputError("invalid enhanced frame"))

    assert error == ServiceError(
        error="backend_input_error",
        detail="invalid enhanced frame",
        status_code=502,
    )


def test_maps_classified_backend_input_error_with_bounded_context() -> None:
    error = service_error_from_exception(
        BackendInputError(
            "Enhanced protocol frame exceeds the device-to-host size limit",
            input_error="frame_too_large",
            operation="capture",
            backend_mode="enhanced",
            observed_frame_bytes=65537,
            max_frame_bytes=65536,
        )
    )

    assert error == ServiceError(
        error="backend_input_error",
        detail="Enhanced protocol frame exceeds the device-to-host size limit",
        status_code=502,
        context={
            "operation": "capture",
            "backend_mode": "enhanced",
            "input_error": "frame_too_large",
            "observed_frame_bytes": 65537,
            "max_frame_bytes": 65536,
        },
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


def test_maps_gpio_identifier_error_with_exact_structured_context() -> None:
    error = service_error_from_exception(
        GpioIdentifierValidationError(
            field="dut_signal",
            reason="invalid_length",
            actual_bytes=65,
        )
    )

    assert error == ServiceError(
        error="invalid_argument",
        detail="GPIO dut_signal must encode to 1..64 UTF-8 bytes",
        status_code=400,
        context={
            "field": "dut_signal",
            "reason": "invalid_length",
            "max_bytes": 64,
            "actual_bytes": 65,
        },
    )


def test_exception_handlers_return_json_error_response() -> None:
    app = create_app()

    @app.get("/raise-not-configured")
    def raise_not_configured() -> None:
        raise GpioConfigurationError(
            "GPIO role 'reset' is not configured",
            operation="boot_test",
            required_role="reset",
            role_state="unconfigured",
        )

    response = TestClient(app).get("/raise-not-configured")

    assert response.status_code == 409
    assert response.json() == {
        "ok": False,
        "error": "not_configured",
        "detail": "GPIO role 'reset' is not configured",
        "detail_truncated": False,
        "context": {
            "operation": "boot_test",
            "required_role": "reset",
            "role_state": "unconfigured",
        },
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
        "detail_truncated": False,
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
        "detail_truncated": False,
    }
