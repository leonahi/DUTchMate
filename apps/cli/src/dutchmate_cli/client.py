"""HTTP client helpers for the local Device Core Service."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Final, cast

import httpx

DEFAULT_SERVICE_URL: Final = "http://127.0.0.1:2040"
DEFAULT_TIMEOUT_SECONDS: Final = 2.0
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

    request_payload: dict[str, object] = {
        "channel": channel,
        "role": role,
        "dut_signal": dut_signal,
        "mode": mode,
        "active_level": active_level,
    }
    if idle_level is not None:
        request_payload["idle_level"] = idle_level

    response = _request_service(
        method="POST",
        path="/gpio/mode",
        service_url=service_url,
        transport=transport,
        json=request_payload,
    )
    return _response_payload(response, description="GPIO mode response")


def _request_service(
    *,
    method: str,
    path: str,
    service_url: str,
    transport: httpx.BaseTransport | None = None,
    json: Mapping[str, object] | None = None,
) -> httpx.Response:
    try:
        with httpx.Client(
            base_url=service_url,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            transport=transport,
        ) as client:
            response = client.request(method, path, json=json)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
        raise ServiceUnavailableError(SERVICE_NOT_RUNNING_MESSAGE) from exc
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
        if isinstance(detail, str) and detail:
            return f"{prefix}: {detail}"

    return f"{prefix}."
