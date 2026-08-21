from __future__ import annotations

import json
from collections.abc import Awaitable, Callable

import httpx
import pytest

from dutchmate_mcp_server.service_client import (
    DeviceCoreClient,
    DeviceCoreProtocolError,
    DeviceCoreServiceError,
    DeviceCoreUnavailableError,
)


async def test_client_maps_the_phase2_tool_surface_to_device_core() -> None:
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"accepted": request.url.path})

    async with DeviceCoreClient(
        transport=httpx.MockTransport(handler),
    ) as client:
        assert await client.reset_dut() == {"accepted": "/dut/reset"}
        await client.set_boot_mode(mode="bootloader")
        await client.capture_uart(duration_s=3)
        await client.run_boot_test(duration_s=4.5)
        await client.wait_for_uart_pattern(pattern="BOOT_OK", timeout_s=5)
        await client.send_uart_command(cmd="version", force=True)
        await client.get_recent_uart_log(lines=25, session_id="session-1")
        await client.get_debug_session("session-1")
        await client.list_debug_sessions(limit=10, cursor="opaque+/=")

    assert [(request.method, request.url.path) for request in requests] == [
        ("POST", "/dut/reset"),
        ("POST", "/dut/boot-mode"),
        ("POST", "/dut/capture"),
        ("POST", "/dut/boot-test"),
        ("POST", "/dut/wait-pattern"),
        ("POST", "/dut/uart/send"),
        ("GET", "/dut/logs"),
        ("GET", "/sessions/session-1"),
        ("GET", "/sessions"),
    ]
    assert _request_json(requests[0]) == {"pulse_ms": 100}
    assert _request_json(requests[1]) == {"mode": "bootloader"}
    assert _request_json(requests[2]) == {"duration_s": 3.0}
    assert _request_json(requests[3]) == {"duration_s": 4.5}
    assert _request_json(requests[4]) == {"pattern": "BOOT_OK", "timeout_s": 5.0}
    assert _request_json(requests[5]) == {
        "cmd": "version",
        "append_newline": True,
        "force": True,
    }
    assert dict(requests[6].url.params) == {"lines": "25", "session_id": "session-1"}
    assert dict(requests[8].url.params) == {"limit": "10", "cursor": "opaque+/="}
    assert requests[2].extensions["timeout"]["read"] == 5.0
    assert requests[4].extensions["timeout"]["read"] == 7.0


async def test_client_validates_tool_arguments_before_dispatch() -> None:
    request_count = 0

    async def handler(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        return httpx.Response(200, json={})

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        invalid_calls: tuple[Callable[[], Awaitable[dict[str, object]]], ...] = (
            lambda: client.reset_dut(pulse_ms=True),  # type: ignore[arg-type]
            lambda: client.set_boot_mode(mode="recovery"),
            lambda: client.capture_uart(duration_s=301),
            lambda: client.run_boot_test(duration_s=float("inf")),
            lambda: client.wait_for_uart_pattern(pattern="bad\n", timeout_s=1),
            lambda: client.send_uart_command(cmd="", append_newline=False),
            lambda: client.get_recent_uart_log(lines=0),
            lambda: client.get_debug_session("../escape"),
            lambda: client.list_debug_sessions(limit=True),  # type: ignore[arg-type]
        )
        for call in invalid_calls:
            with pytest.raises(ValueError):
                await call()

    assert request_count == 0


async def test_client_preserves_structured_service_errors() -> None:
    error_payload: dict[str, object] = {
        "ok": False,
        "error": "reconnect_limit",
        "detail": "maximum reconnect segments reached",
        "detail_truncated": False,
        "context": {
            "operation": "capture",
            "session_id": "session-1",
            "segment_count": 32,
            "max_segments": 32,
        },
    }

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json=error_payload)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreServiceError) as raised:
            await client.capture_uart(duration_s=2)

    assert raised.value.status_code == 503
    assert raised.value.error == "reconnect_limit"
    assert raised.value.context == error_payload["context"]
    assert raised.value.payload() == error_payload


@pytest.mark.parametrize(
    ("status_code", "response_factory"),
    [
        (200, lambda: httpx.Response(200, content=b"not json")),
        (200, lambda: httpx.Response(200, json=[])),
        (409, lambda: httpx.Response(409, json={"error": "capture_active"})),
        (307, lambda: httpx.Response(307, json={"redirect": True})),
    ],
)
async def test_client_rejects_invalid_service_response_contracts(
    status_code: int,
    response_factory: Callable[[], httpx.Response],
) -> None:
    del status_code

    async def handler(request: httpx.Request) -> httpx.Response:
        return response_factory()

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreProtocolError):
            await client.reset_dut()


async def test_client_reports_connection_failure_as_structured_unavailable() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreUnavailableError) as raised:
            await client.reset_dut()

    assert raised.value.payload() == {
        "ok": False,
        "error": "service_unavailable",
        "detail": raised.value.detail,
        "detail_truncated": False,
    }
    assert "explicit Basic or Enhanced backend" in raised.value.detail


@pytest.mark.parametrize(
    "service_url",
    [
        "",
        "127.0.0.1:2040",
        "ftp://127.0.0.1:2040",
        "http://user:secret@127.0.0.1:2040",
        "http://127.0.0.1:2040/api",
        "http://127.0.0.1:2040?debug=true",
        "http://127.0.0.1:2040#fragment",
    ],
)
def test_client_rejects_invalid_service_urls(service_url: str) -> None:
    with pytest.raises(ValueError):
        DeviceCoreClient(service_url)


def _request_json(request: httpx.Request) -> object:
    return json.loads(request.content)
