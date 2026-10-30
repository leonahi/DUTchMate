"""Async HTTP port from the MCP adapter to the Device Core Service."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import TracebackType
from typing import Final, NoReturn, cast
from urllib.parse import quote

import httpx

from dutchmate_core.diagnostics import project_diagnostic_detail
from dutchmate_core.evidence.tail import validate_evidence_query
from dutchmate_core.operations.monitor import MonitorCondition, validate_monitor_request
from dutchmate_core.validation import (
    prepare_uart_send_payload,
    prepare_uart_tx_payload,
    validate_boot_mode,
    validate_capture_duration,
    validate_reset_pulse,
    validate_session_id,
    validate_wait_pattern,
    validate_wait_timeout,
)

DEFAULT_SERVICE_URL: Final = "http://127.0.0.1:2040"
DEFAULT_REQUEST_TIMEOUT_S: Final = 2.0
WORKFLOW_TIMEOUT_GRACE_S: Final = 2.0
CONNECTION_MUTATION_TIMEOUT_S: Final = 65.0
SERVICE_NOT_RUNNING_DETAIL: Final = (
    "Device Core Service is not running. Start it with an explicit Basic or "
    "Enhanced backend before calling DUTchMate tools."
)


class DeviceCoreClientError(RuntimeError):
    """Base error raised by the MCP Device Core HTTP port."""


class DeviceCoreUnavailableError(DeviceCoreClientError):
    """Raised when the configured Device Core Service cannot be reached."""

    error = "service_unavailable"

    def __init__(self, detail: str = SERVICE_NOT_RUNNING_DETAIL) -> None:
        self.detail = detail
        super().__init__(detail)

    def payload(self) -> dict[str, object]:
        """Return a canonical structured error for a future MCP tool result."""

        return {
            "ok": False,
            "error": self.error,
            "detail": self.detail,
            "detail_truncated": False,
        }


class DeviceCoreProtocolError(DeviceCoreClientError):
    """Raised when the HTTP peer does not honor the Device Core JSON contract."""


class DeviceCoreServiceError(DeviceCoreClientError):
    """Preserve one canonical structured Device Core Service error response."""

    def __init__(self, *, status_code: int, response_payload: dict[str, object]) -> None:
        self.status_code = status_code
        self.response_payload = response_payload.copy()
        self.error = cast(str, response_payload["error"])
        self.detail = cast(str, response_payload["detail"])
        self.detail_truncated = cast(bool, response_payload["detail_truncated"])
        context = response_payload.get("context")
        self.context = cast(dict[str, object] | None, context)
        super().__init__(self.detail)

    def payload(self) -> dict[str, object]:
        """Return the service payload without recasting its error or context."""

        return self.response_payload.copy()


class DeviceCoreClient:
    """Call bounded Device Core endpoints without owning hardware or sessions."""

    def __init__(
        self,
        service_url: str = DEFAULT_SERVICE_URL,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.service_url = _validated_service_url(service_url)
        self._client = httpx.AsyncClient(
            base_url=self.service_url,
            timeout=DEFAULT_REQUEST_TIMEOUT_S,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self) -> DeviceCoreClient:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        """Close the owned HTTP connection pool."""

        await self._client.aclose()

    async def get_status(self) -> dict[str, object]:
        return await self._request("GET", "/status")

    async def monitor(
        self,
        *,
        duration_s: float | None = None,
        conditions: Sequence[Mapping[str, object]] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, object]:
        body, bound = _operation_body(
            duration_s=duration_s,
            conditions=conditions,
            timeout_s=timeout_s,
        )
        return await self._request(
            "POST",
            "/dut/monitor",
            json=body,
            timeout_s=bound + WORKFLOW_TIMEOUT_GRACE_S,
        )

    async def interact(
        self,
        *,
        data_b64: str | None = None,
        text: str | None = None,
        line_ending: str | None = None,
        duration_s: float | None = None,
        conditions: Sequence[Mapping[str, object]] | None = None,
        timeout_s: float | None = None,
    ) -> dict[str, object]:
        body, bound = _operation_body(
            duration_s=duration_s,
            conditions=conditions,
            timeout_s=timeout_s,
        )
        body.update(_uart_body(data_b64=data_b64, text=text, line_ending=line_ending))
        return await self._request(
            "POST",
            "/dut/interact",
            json=body,
            timeout_s=bound + WORKFLOW_TIMEOUT_GRACE_S,
        )

    async def send_uart(
        self,
        *,
        data_b64: str | None = None,
        text: str | None = None,
        line_ending: str | None = None,
    ) -> dict[str, object]:
        body = _uart_body(data_b64=data_b64, text=text, line_ending=line_ending)
        return await self._request("POST", "/dut/uart/send", json=body)

    async def reset_dut(self, *, pulse_ms: int = 100) -> dict[str, object]:
        validated_pulse = validate_reset_pulse(pulse_ms)
        return await self._request(
            "POST",
            "/dut/reset",
            json={"pulse_ms": validated_pulse},
        )

    async def set_dut_boot_mode(self, *, mode: str) -> dict[str, object]:
        validated_mode = validate_boot_mode(mode)
        return await self._request(
            "POST",
            "/dut/boot-mode",
            json={"mode": validated_mode},
        )

    async def get_evidence(
        self,
        *,
        cursor: str | None = None,
        limit: int = 100,
        wait_s: float = 1.0,
    ) -> dict[str, object]:
        validate_evidence_query(cursor=cursor, limit=limit, wait_s=wait_s)
        params: dict[str, str | int | float] = {"limit": limit, "wait_s": wait_s}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._request(
            "GET",
            "/dut/evidence",
            params=params,
            timeout_s=wait_s + WORKFLOW_TIMEOUT_GRACE_S,
        )

    async def release_connection(self) -> dict[str, object]:
        return await self._request(
            "POST",
            "/connection/release",
            timeout_s=CONNECTION_MUTATION_TIMEOUT_S,
        )

    async def reacquire_connection(self) -> dict[str, object]:
        return await self._request(
            "POST",
            "/connection/reacquire",
            timeout_s=CONNECTION_MUTATION_TIMEOUT_S,
        )

    # Retained only for the pre-v2 catalog; migrate its consumers in Slice 2.
    async def set_boot_mode(self, *, mode: str) -> dict[str, object]:
        return await self.set_dut_boot_mode(mode=mode)

    async def capture_uart(self, *, duration_s: float) -> dict[str, object]:
        return await self._timed_workflow(
            "/dut/capture",
            duration_s=validate_capture_duration(duration_s),
        )

    async def run_boot_test(self, *, duration_s: float) -> dict[str, object]:
        return await self._timed_workflow(
            "/dut/boot-test",
            duration_s=validate_capture_duration(duration_s),
        )

    async def wait_for_uart_pattern(
        self,
        *,
        pattern: str,
        timeout_s: float,
    ) -> dict[str, object]:
        validated_pattern = validate_wait_pattern(pattern)
        validated_timeout = validate_wait_timeout(timeout_s)
        return await self._request(
            "POST",
            "/dut/wait-pattern",
            json={"pattern": validated_pattern, "timeout_s": validated_timeout},
            timeout_s=max(
                DEFAULT_REQUEST_TIMEOUT_S,
                validated_timeout + WORKFLOW_TIMEOUT_GRACE_S,
            ),
        )

    async def send_uart_command(
        self,
        *,
        cmd: str,
        append_newline: bool = True,
        force: bool = False,
    ) -> dict[str, object]:
        prepare_uart_send_payload(cmd, append_newline=append_newline)
        if not isinstance(force, bool):
            raise ValueError("UART send force must be a boolean")
        return await self._request(
            "POST",
            "/dut/uart/send",
            json={
                "cmd": cmd,
                "append_newline": append_newline,
                "force": force,
            },
        )

    async def get_recent_logs(
        self,
        *,
        lines: int = 300,
        session_id: str | None = None,
    ) -> dict[str, object]:
        if isinstance(lines, bool) or not isinstance(lines, int) or not 1 <= lines <= 1000:
            raise ValueError("log lines must be an integer from 1 to 1000")
        params: dict[str, str | int] = {"lines": lines}
        if session_id is not None:
            params["session_id"] = validate_session_id(session_id)
        return await self._request("GET", "/dut/logs", params=params)

    async def get_session(self, session_id: str) -> dict[str, object]:
        session_name = validate_session_id(session_id)
        return await self._request(
            "GET",
            f"/sessions/{quote(session_name, safe='')}",
        )

    async def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 100:
            raise ValueError("session limit must be an integer from 1 to 100")
        if cursor is not None and (not isinstance(cursor, str) or not cursor):
            raise ValueError("session cursor must be a non-empty string")
        params: dict[str, str | int] = {"limit": limit}
        if cursor is not None:
            params["cursor"] = cursor
        return await self._request("GET", "/sessions", params=params)

    async def get_recent_uart_log(
        self,
        *,
        lines: int = 300,
        session_id: str | None = None,
    ) -> dict[str, object]:
        return await self.get_recent_logs(lines=lines, session_id=session_id)

    async def get_debug_session(self, session_id: str) -> dict[str, object]:
        return await self.get_session(session_id)

    async def list_debug_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> dict[str, object]:
        return await self.list_sessions(limit=limit, cursor=cursor)

    async def _timed_workflow(
        self,
        path: str,
        *,
        duration_s: float,
    ) -> dict[str, object]:
        return await self._request(
            "POST",
            path,
            json={"duration_s": duration_s},
            timeout_s=max(
                DEFAULT_REQUEST_TIMEOUT_S,
                duration_s + WORKFLOW_TIMEOUT_GRACE_S,
            ),
        )

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Mapping[str, object] | None = None,
        params: Mapping[str, str | int | float] | None = None,
        timeout_s: float = DEFAULT_REQUEST_TIMEOUT_S,
    ) -> dict[str, object]:
        try:
            response = await self._client.request(
                method,
                path,
                json=json,
                params=params,
                timeout=timeout_s,
            )
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            raise DeviceCoreUnavailableError() from exc
        except httpx.TimeoutException as exc:
            raise DeviceCoreUnavailableError(
                "Device Core Service request timed out. The service state is unknown."
            ) from exc
        except httpx.RequestError as exc:
            raise DeviceCoreUnavailableError(
                "Device Core Service request failed before a valid response was received."
            ) from exc

        payload = _json_object(response)
        if 200 <= response.status_code < 300:
            return payload
        _raise_service_error(response.status_code, payload)


def _operation_body(
    *,
    duration_s: float | None,
    conditions: Sequence[Mapping[str, object]] | None,
    timeout_s: float | None,
) -> tuple[dict[str, object], float]:
    mapped = None
    if conditions is not None:
        if isinstance(conditions, (str, bytes)) or not isinstance(conditions, Sequence):
            raise ValueError("Monitor conditions must be a sequence of condition objects")
        mapped = []
        for condition in conditions:
            if not isinstance(condition, Mapping) or "pattern" not in condition:
                raise ValueError("Monitor conditions require a pattern")
            mapped.append(
                MonitorCondition(
                    pattern=cast(str, condition["pattern"]),
                    name=cast(str | None, condition.get("name")),
                )
            )
    validated = validate_monitor_request(
        duration_s=duration_s,
        conditions=mapped,
        timeout_s=timeout_s,
    )
    body: dict[str, object] = {}
    if duration_s is not None:
        body["duration_s"] = duration_s
    if conditions is not None:
        body["conditions"] = [dict(item) for item in conditions]
    if timeout_s is not None:
        body["timeout_s"] = timeout_s
    bound = validated.duration_s if validated.mode == "duration" else validated.timeout_s
    assert bound is not None
    return body, bound


def _uart_body(
    *,
    data_b64: str | None,
    text: str | None,
    line_ending: str | None,
) -> dict[str, object]:
    prepare_uart_tx_payload(data_b64=data_b64, text=text, line_ending=line_ending)
    return {
        name: value
        for name, value in (("data_b64", data_b64), ("text", text), ("line_ending", line_ending))
        if value is not None
    }


def _validated_service_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Device Core service URL must be a non-empty string")
    try:
        url = httpx.URL(value.strip())
    except httpx.InvalidURL as exc:
        raise ValueError("Device Core service URL is invalid") from exc
    if url.scheme not in {"http", "https"} or not url.host:
        raise ValueError("Device Core service URL must be an absolute HTTP(S) URL")
    if url.username or url.password:
        raise ValueError("Device Core service URL must not contain credentials")
    if url.query or url.fragment:
        raise ValueError("Device Core service URL must not contain a query or fragment")
    if url.path not in {"", "/"}:
        raise ValueError("Device Core service URL must not contain a path")
    return str(url).rstrip("/")


def _json_object(response: httpx.Response) -> dict[str, object]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise DeviceCoreProtocolError(
            f"Device Core Service returned invalid JSON with HTTP {response.status_code}"
        ) from exc
    if not isinstance(payload, Mapping):
        raise DeviceCoreProtocolError(
            f"Device Core Service returned a non-object JSON response with HTTP "
            f"{response.status_code}"
        )
    return dict(payload)


def _raise_service_error(status_code: int, payload: dict[str, object]) -> NoReturn:
    error = payload.get("error")
    detail = payload.get("detail")
    detail_truncated = payload.get("detail_truncated")
    context = payload.get("context")
    if (
        payload.get("ok") is not False
        or not isinstance(error, str)
        or not error
        or not isinstance(detail, str)
        or not detail
        or not isinstance(detail_truncated, bool)
        or (context is not None and not isinstance(context, dict))
    ):
        raise DeviceCoreProtocolError(
            f"Device Core Service returned an invalid error contract with HTTP {status_code}"
        )
    try:
        projected, truncated = project_diagnostic_detail(
            fallback_code="service_protocol_error",
            detail=detail,
        )
    except UnicodeError as exc:
        raise DeviceCoreProtocolError(
            f"Device Core Service returned invalid diagnostic text with HTTP {status_code}"
        ) from exc
    if truncated or projected != detail:
        raise DeviceCoreProtocolError(
            f"Device Core Service returned invalid diagnostic text with HTTP {status_code}"
        )
    raise DeviceCoreServiceError(status_code=status_code, response_payload=payload)
