"""HTTP client helpers for the local Device Core Service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast
from urllib.parse import quote

import httpx

from dutchmate_core.validation import (
    prepare_uart_send_payload,
    validate_capture_duration,
    validate_gpio_configuration,
    validate_session_id,
    validate_wait_pattern,
    validate_wait_timeout,
)

DEFAULT_SERVICE_URL: Final = "http://127.0.0.1:2040"
DEFAULT_TIMEOUT_SECONDS: Final = 2.0
CAPTURE_TIMEOUT_GRACE_SECONDS: Final = 2.0
SERVICE_NOT_RUNNING_MESSAGE: Final = (
    "Device Core Service is not running. Run 'dutchmate start' first."
)


class ServiceClientError(RuntimeError):
    """Raised when the CLI cannot complete a Device Core Service request."""


class ServiceUnavailableError(ServiceClientError):
    """Raised when the local Device Core Service cannot be reached."""


class ServiceApiError(ServiceClientError):
    """Raised when the local Device Core Service returns an error response."""


def fetch_status(
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Fetch the current Device Core Service status payload."""

    response = _request_service(
        method="GET",
        path="/status",
        service_url=service_url,
        transport=transport,
    )
    return _response_payload(response, description="status payload")


def list_debug_sessions(
    *,
    limit: int = 50,
    cursor: str | None = None,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Fetch one bounded newest-first session page."""

    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("session limit must be an integer from 1 to 100")
    if cursor is not None and (not isinstance(cursor, str) or not cursor):
        raise ValueError("session cursor must be a non-empty string")
    params: dict[str, str | int] = {"limit": limit}
    if cursor is not None:
        params["cursor"] = cursor
    response = _request_service(
        method="GET",
        path="/sessions",
        service_url=service_url,
        transport=transport,
        params=params,
    )
    return _response_payload(response, description="session list payload")


def get_debug_session(
    session_id: str,
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Fetch bounded schema-aware detail for one session."""

    validated_id = validate_session_id(session_id)
    response = _request_service(
        method="GET",
        path=f"/sessions/{quote(validated_id, safe='')}",
        service_url=service_url,
        transport=transport,
    )
    return _response_payload(response, description="session detail payload")


def mark_session_baseline(
    session_id: str,
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Designate one stored session as the project baseline."""

    validated_id = validate_session_id(session_id)
    response = _request_service(
        method="POST",
        path=f"/sessions/{quote(validated_id, safe='')}/baseline",
        service_url=service_url,
        transport=transport,
    )
    return _response_payload(response, description="baseline mark response")


def clear_session_baseline(
    session_id: str,
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Clear the project baseline only when it names the requested session."""

    validated_id = validate_session_id(session_id)
    response = _request_service(
        method="DELETE",
        path=f"/sessions/{quote(validated_id, safe='')}/baseline",
        service_url=service_url,
        transport=transport,
    )
    return _response_payload(response, description="baseline clear response")


def fetch_recent_logs(
    *,
    session_id: str | None = None,
    lines: int = 300,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Fetch bounded recent UART replay for one selected native session."""

    if isinstance(lines, bool) or not isinstance(lines, int) or not 1 <= lines <= 1000:
        raise ValueError("log lines must be an integer from 1 to 1000")
    params: dict[str, str | int] = {"lines": lines}
    if session_id is not None:
        params["session_id"] = validate_session_id(session_id)
    response = _request_service(
        method="GET",
        path="/dut/logs",
        service_url=service_url,
        transport=transport,
        params=params,
    )
    return _response_payload(response, description="recent logs payload")


def wait_for_pattern(
    *,
    pattern: str,
    timeout_s: float,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Run one finite literal wait against new UART evidence."""

    validated_pattern = validate_wait_pattern(pattern)
    validated_timeout = validate_wait_timeout(timeout_s)
    response = _request_service(
        method="POST",
        path="/dut/wait-pattern",
        service_url=service_url,
        transport=transport,
        json={"pattern": validated_pattern, "timeout_s": validated_timeout},
        timeout_s=max(
            DEFAULT_TIMEOUT_SECONDS,
            validated_timeout + CAPTURE_TIMEOUT_GRACE_SECONDS,
        ),
    )
    return _response_payload(response, description="wait-pattern response")


def send_uart_command(
    cmd: str,
    *,
    append_newline: bool = True,
    force: bool = False,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Send one validated text command through the Device Core Service."""

    prepare_uart_send_payload(cmd, append_newline=append_newline)
    if not isinstance(force, bool):
        raise ValueError("UART send force must be a boolean")
    response = _request_service(
        method="POST",
        path="/dut/uart/send",
        service_url=service_url,
        transport=transport,
        json={
            "cmd": cmd,
            "append_newline": append_newline,
            "force": force,
        },
    )
    return _response_payload(response, description="UART-send response")


def configure_gpio_mode(
    *,
    channel: str,
    role: str,
    dut_signal: str,
    mode: str,
    active_level: str,
    idle_level: str | None = None,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Configure one Device Core Service GPIO control channel."""

    request = validate_gpio_configuration(
        channel=channel,
        role=role,
        dut_signal=dut_signal,
        mode=mode,
        active_level=active_level,
        idle_level=idle_level,
    )
    request_payload: dict[str, object] = {
        "channel": request.channel,
        "role": request.role,
        "dut_signal": request.dut_signal,
        "mode": request.mode,
        "active_level": request.active_level,
    }
    if request.idle_level is not None:
        request_payload["idle_level"] = request.idle_level

    response = _request_service(
        method="POST",
        path="/gpio/mode",
        service_url=service_url,
        transport=transport,
        json=request_payload,
    )
    return _response_payload(response, description="GPIO mode response")


def reset_dut(
    *,
    pulse_ms: int = 100,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Pulse the configured DUT reset role through the Device Core Service."""

    response = _request_service(
        method="POST",
        path="/dut/reset",
        service_url=service_url,
        transport=transport,
        json={"pulse_ms": pulse_ms},
    )
    return _response_payload(response, description="reset response")


def set_boot_mode(
    *,
    mode: str,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Set the configured DUT boot/control role through the Device Core Service."""

    response = _request_service(
        method="POST",
        path="/dut/boot-mode",
        service_url=service_url,
        transport=transport,
        json={"mode": mode},
    )
    return _response_payload(response, description="boot-mode response")


def capture_uart(
    *,
    duration_s: float,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Capture DUT UART evidence through the Device Core Service."""

    return _run_timed_capture_request(
        path="/dut/capture",
        description="capture",
        duration_s=duration_s,
        service_url=service_url,
        transport=transport,
    )


def run_boot_test(
    *,
    duration_s: float,
    service_url: str = DEFAULT_SERVICE_URL,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, object]:
    """Reset the DUT and capture boot evidence through the Device Core Service."""

    return _run_timed_capture_request(
        path="/dut/boot-test",
        description="boot-test",
        duration_s=duration_s,
        service_url=service_url,
        transport=transport,
    )


def _run_timed_capture_request(
    *,
    path: str,
    description: str,
    duration_s: float,
    service_url: str,
    transport: httpx.BaseTransport | None,
) -> dict[str, object]:
    try:
        duration_s = validate_capture_duration(duration_s)
    except ValueError as exc:
        raise ValueError(f"{description} {exc}") from exc

    response = _request_service(
        method="POST",
        path=path,
        service_url=service_url,
        transport=transport,
        json={"duration_s": duration_s},
        timeout_s=max(
            DEFAULT_TIMEOUT_SECONDS,
            duration_s + CAPTURE_TIMEOUT_GRACE_SECONDS,
        ),
    )
    return _response_payload(response, description=f"{description} response")


def _request_service(
    *,
    method: str,
    path: str,
    service_url: str,
    transport: httpx.BaseTransport | None = None,
    json: Mapping[str, object] | None = None,
    params: Mapping[str, str | int] | None = None,
    timeout_s: float = DEFAULT_TIMEOUT_SECONDS,
) -> httpx.Response:
    try:
        with httpx.Client(
            base_url=service_url,
            timeout=timeout_s,
            transport=transport,
        ) as client:
            response = client.request(method, path, json=json, params=params)
    except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
        raise ServiceUnavailableError(SERVICE_NOT_RUNNING_MESSAGE) from exc
    except httpx.ReadTimeout as exc:
        raise ServiceApiError("Device Core Service request timed out.") from exc
    except httpx.HTTPError as exc:
        raise ServiceApiError(f"Unable to contact Device Core Service: {exc}") from exc

    if response.is_error:
        raise ServiceApiError(_response_error_message(response))

    return response


def _response_payload(response: httpx.Response, *, description: str) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ServiceApiError("Device Core Service returned invalid JSON.") from exc

    if not isinstance(payload, Mapping):
        raise ServiceApiError(f"Device Core Service returned an invalid {description}.")

    return cast(dict[str, object], payload)


def _response_error_message(response: httpx.Response) -> str:
    prefix = f"Device Core Service returned HTTP {response.status_code}"
    try:
        payload = response.json()
    except ValueError:
        return f"{prefix}."

    if isinstance(payload, Mapping):
        detail = payload.get("detail")
        error = payload.get("error")
        if isinstance(detail, str) and detail:
            suffix = _uart_send_error_suffix(payload.get("context"))
            if isinstance(error, str) and error:
                return f"{prefix} [{error}]: {detail}{suffix}"
            return f"{prefix}: {detail}{suffix}"

    return f"{prefix}."


def _uart_send_error_suffix(context: object) -> str:
    if not isinstance(context, Mapping):
        return ""
    attempt_id = context.get("attempt_id")
    if not isinstance(attempt_id, str) or not attempt_id:
        return ""
    accepted = context.get("bytes_accepted")
    accepted_text = str(accepted) if isinstance(accepted, int) else "unknown"
    return (
        f" Attempt: {attempt_id}; accepted bytes: {accepted_text}."
        " Warning: bytes may have reached the DUT."
    )
