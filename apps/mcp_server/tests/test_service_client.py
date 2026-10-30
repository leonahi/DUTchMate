from __future__ import annotations

import json
from collections.abc import Callable

import httpx
import pytest

from dutchmate_mcp_server.service_client import (
    DeviceCoreClient,
    DeviceCoreProtocolError,
    DeviceCoreServiceError,
    DeviceCoreUnavailableError,
)


@pytest.mark.parametrize(
    ("status_code", "response_factory"),
    [
        (200, lambda: httpx.Response(200, content=b"not json")),
        (200, lambda: httpx.Response(200, json=[])),
        (409, lambda: httpx.Response(409, json={"error": "operation_active"})),
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


@pytest.mark.parametrize(
    ("method", "arguments", "http_method", "path", "body", "query", "timeout"),
    [
        ("get_status", {}, "GET", "/status", None, {}, 2.0),
        ("monitor", {"duration_s": 3}, "POST", "/dut/monitor", {"duration_s": 3}, {}, 5.0),
        (
            "interact",
            {"data_b64": "AP8=", "duration_s": 0.25},
            "POST",
            "/dut/interact",
            {"data_b64": "AP8=", "duration_s": 0.25},
            {},
            2.25,
        ),
        (
            "send_uart",
            {"data_b64": "AP8="},
            "POST",
            "/dut/uart/send",
            {"data_b64": "AP8="},
            {},
            2.0,
        ),
        ("reset_dut", {}, "POST", "/dut/reset", {"pulse_ms": 100}, {}, 2.0),
        (
            "set_dut_boot_mode",
            {"mode": "bootloader"},
            "POST",
            "/dut/boot-mode",
            {"mode": "bootloader"},
            {},
            2.0,
        ),
        (
            "get_evidence",
            {"cursor": "opaque+/=雪", "limit": 500, "wait_s": 30},
            "GET",
            "/dut/evidence",
            None,
            {"cursor": "opaque+/=雪", "limit": "500", "wait_s": "30"},
            32.0,
        ),
        (
            "get_recent_logs",
            {"session_id": "session-2", "lines": 25},
            "GET",
            "/dut/logs",
            None,
            {"session_id": "session-2", "lines": "25"},
            2.0,
        ),
        (
            "list_sessions",
            {"limit": 10, "cursor": "opaque+/=雪"},
            "GET",
            "/sessions",
            None,
            {"limit": "10", "cursor": "opaque+/=雪"},
            2.0,
        ),
        (
            "get_session",
            {"session_id": "session ?#雪"},
            "GET",
            "/sessions/session ?#雪",
            None,
            {},
            2.0,
        ),
        ("release_connection", {}, "POST", "/connection/release", None, {}, 65.0),
        ("reacquire_connection", {}, "POST", "/connection/reacquire", None, {}, 65.0),
    ],
)
async def test_v2_client_maps_service_requests_without_extra_dispatch(
    method,
    arguments,
    http_method,
    path,
    body,
    query,
    timeout,
):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        assert await getattr(client, method)(**arguments) == {"ok": True}

    assert len(requests) == 1
    request = requests[0]
    assert (request.method, request.url.path) == (http_method, path)
    assert (_request_json(request) if request.content else None) == body
    assert dict(request.url.params) == query
    assert request.extensions["timeout"] == {
        "connect": timeout,
        "read": timeout,
        "write": timeout,
        "pool": timeout,
    }
    if method == "get_session":
        assert request.url.raw_path == b"/sessions/session%20%3F%23%E9%9B%AA"


@pytest.mark.parametrize(
    ("method", "arguments", "query"),
    [
        ("get_evidence", {}, {"limit": "100", "wait_s": "1.0"}),
        ("get_evidence", {"wait_s": 0}, {"limit": "100", "wait_s": "0"}),
        ("get_recent_logs", {}, {"lines": "300"}),
        ("list_sessions", {}, {"limit": "50"}),
    ],
)
async def test_v2_query_defaults_omit_absent_cursor_and_session(method, arguments, query):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={})

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        await getattr(client, method)(**arguments)

    assert dict(requests[0].url.params) == query
    if method == "get_evidence":
        assert requests[0].extensions["timeout"]["read"] == arguments.get("wait_s", 1.0) + 2


@pytest.mark.parametrize("method", ["monitor", "interact"])
@pytest.mark.parametrize(
    ("completion", "timeout"),
    [
        ({"duration_s": 300}, 302.0),
        (
            {
                "conditions": [{"pattern": "READY", "name": "ready"}, {"pattern": "ERROR"}],
                "timeout_s": 4.5,
            },
            6.5,
        ),
    ],
)
async def test_v2_operation_preserves_completion_mode_and_timeout(method, completion, timeout):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    arguments = dict(completion)
    if method == "interact":
        arguments.update(text="INFO", line_ending="lf")
    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        await getattr(client, method)(**arguments)

    assert _request_json(requests[0]) == arguments
    assert requests[0].extensions["timeout"]["read"] == timeout


@pytest.mark.parametrize("method", ["send_uart", "interact"])
@pytest.mark.parametrize("line_ending", ["none", "lf", "cr", "crlf", "profile_default"])
@pytest.mark.parametrize("text", ["INFO", "  λ\n"])
async def test_v2_text_payload_is_forwarded_without_implicit_transformation(
    method, line_ending, text
):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    arguments = {"text": text, "line_ending": line_ending}
    if method == "interact":
        arguments["duration_s"] = 1
    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        await getattr(client, method)(**arguments)

    assert _request_json(requests[0]) == arguments


@pytest.mark.parametrize(
    ("method", "arguments"),
    [
        ("monitor", {}),
        ("monitor", {"duration_s": True}),
        ("monitor", {"duration_s": 0}),
        ("monitor", {"duration_s": 301}),
        ("monitor", {"duration_s": float("inf")}),
        ("monitor", {"duration_s": 1, "conditions": [{"pattern": "OK"}], "timeout_s": 2}),
        ("monitor", {"conditions": [], "timeout_s": 1}),
        ("monitor", {"conditions": [{"pattern": "OK"}] * 9, "timeout_s": 1}),
        ("monitor", {"conditions": [{"pattern": "OK"}]}),
        ("monitor", {"conditions": [{"pattern": "OK"}], "timeout_s": float("nan")}),
        ("monitor", {"conditions": [{"pattern": "OK"}], "timeout_s": True}),
        ("monitor", {"conditions": [{"pattern": "OK\n"}], "timeout_s": 1}),
        ("monitor", {"conditions": [{"pattern": "x" * 257}], "timeout_s": 1}),
        ("monitor", {"conditions": [{"pattern": "OK", "name": " bad"}], "timeout_s": 1}),
        ("monitor", {"conditions": [{}], "timeout_s": 1}),
        ("monitor", {"conditions": ["OK"], "timeout_s": 1}),
        ("monitor", {"conditions": "OK", "timeout_s": 1}),
        ("monitor", {"conditions": 1, "timeout_s": 1}),
        ("interact", {"data_b64": "eA=="}),
        ("interact", {"text": "INFO", "duration_s": 1}),
        ("interact", {"data_b64": "eA==", "duration_s": True}),
        ("interact", {"data_b64": "eA==", "conditions": [], "timeout_s": 1}),
        ("send_uart", {}),
        ("send_uart", {"text": "INFO"}),
        ("send_uart", {"data_b64": "eA==", "text": "x", "line_ending": "lf"}),
        ("send_uart", {"data_b64": "!"}),
        ("send_uart", {"data_b64": ""}),
        ("send_uart", {"data_b64": "eA==", "line_ending": "none"}),
        ("send_uart", {"text": "x" * 1024, "line_ending": "lf"}),
        ("send_uart", {"text": "x", "line_ending": "auto"}),
        ("reset_dut", {"pulse_ms": True}),
        ("reset_dut", {"pulse_ms": 1.5}),
        ("reset_dut", {"pulse_ms": 10001}),
        ("set_dut_boot_mode", {"mode": "recovery"}),
        ("get_evidence", {"limit": True}),
        ("get_evidence", {"limit": 501}),
        ("get_evidence", {"wait_s": -1}),
        ("get_evidence", {"wait_s": 31}),
        ("get_evidence", {"wait_s": float("inf")}),
        ("get_evidence", {"wait_s": True}),
        ("get_evidence", {"cursor": ""}),
        ("get_evidence", {"cursor": "x" * 2049}),
        ("get_recent_logs", {"lines": 1001}),
        ("get_recent_logs", {"lines": True}),
        ("get_recent_logs", {"session_id": "../escape"}),
        ("list_sessions", {"limit": 0}),
        ("list_sessions", {"limit": True}),
        ("list_sessions", {"cursor": ""}),
        ("get_session", {"session_id": "../escape"}),
        ("get_session", {"session_id": ".."}),
        ("get_session", {"session_id": " session"}),
    ],
)
async def test_v2_invalid_arguments_do_not_dispatch_http(method, arguments):
    async def handler(request):
        pytest.fail(f"invalid request reached HTTP: {request.method} {request.url.path}")

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ValueError):
            await getattr(client, method)(**arguments)


@pytest.mark.parametrize("method", ["send_uart", "interact"])
@pytest.mark.parametrize("retired", ["cmd", "append_newline", "force"])
async def test_v2_payload_methods_reject_retired_arguments(method, retired):
    async def handler(request):
        pytest.fail("retired arguments reached HTTP")

    arguments = {"data_b64": "eA==", retired: True}
    if method == "interact":
        arguments["duration_s"] = 1
    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(TypeError):
            await getattr(client, method)(**arguments)


@pytest.mark.parametrize(
    ("method", "arguments", "expected_body"),
    [
        ("reset_dut", {"pulse_ms": 10000}, {"pulse_ms": 10000}),
        ("set_dut_boot_mode", {"mode": "normal"}, {"mode": "normal"}),
    ],
)
async def test_v2_control_preserves_explicit_values(method, arguments, expected_body):
    requests = []

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json={"ok": True})

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        await getattr(client, method)(**arguments)
    assert _request_json(requests[0]) == expected_body


@pytest.mark.parametrize(
    "outcome", ["elapsed", "matched", "timeout", "disconnected", "released", "cancelled", "error"]
)
@pytest.mark.parametrize("method", ["monitor", "interact"])
async def test_v2_operation_results_preserve_outcomes_ranges_and_exact_evidence(method, outcome):
    payload = {
        "ok": True,
        "operation_id": "op-1",
        "outcome": outcome,
        "mode": "duration",
        "duration_s": 1,
        "conditions": [],
        "timeout_s": None,
        "start_cursor": {"session_id": "s1", "next_evidence_seq": 4},
        "end_cursor": {"session_id": "s2", "next_evidence_seq": 9},
        "evidence_ranges": [
            {"session_id": "s1", "start_evidence_seq": 3, "end_evidence_seq_exclusive": 8},
            {"session_id": "s2", "start_evidence_seq": 0, "end_evidence_seq_exclusive": 9},
        ],
        "matched_condition": None,
        "line_processing_limited": False,
        "integrity": {
            "loss_status": "not_observable",
            "observation_scope": None,
            "dropped_bytes": None,
        },
        "timestamp_provenance": [],
    }
    arguments = {"duration_s": 1}
    if method == "interact":
        arguments["data_b64"] = "AP8="
        payload.update(
            data_b64="AP8=",
            transformation={
                "input_form": "data_b64",
                "line_ending": None,
                "resolved_line_ending": None,
            },
            tx=None,
            tx_error={"error": "timeout", "bytes_accepted": None},
        )

    async def handler(request):
        return httpx.Response(200, json=payload)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        assert await getattr(client, method)(**arguments) == payload


async def test_v2_evidence_cursor_round_trip_preserves_records_and_omission():
    requests = []
    cursor = "opaque+/=雪"
    pages = [
        {"ok": True, "records": [], "next_cursor": cursor, "omitted_records": 0},
        {
            "ok": True,
            "records": [
                {"evidence_seq": 9, "segment_id": 1, "type": "uart_rx", "data_b64": "AP8="}
            ],
            "next_cursor": "opaque-next",
            "omitted_records": 2,
        },
    ]

    async def handler(request):
        requests.append(request)
        return httpx.Response(200, json=pages[len(requests) - 1])

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        first = await client.get_evidence(wait_s=0)
        second = await client.get_evidence(cursor=first["next_cursor"], wait_s=30)

    assert first == pages[0]
    assert second == pages[1]
    assert dict(requests[1].url.params)["cursor"] == cursor


@pytest.mark.parametrize("schema", [0, 1, 2])
async def test_v2_session_client_does_not_rewrite_service_compatibility(schema):
    payload = {
        "session_id": "s1",
        "schema_version": schema,
        "compatibility": "legacy_read_only" if schema == 0 else "native",
    }

    async def handler(request):
        return httpx.Response(200, json=payload)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        assert await client.get_session(session_id="s1") == payload


@pytest.mark.parametrize(
    ("status", "code"),
    [
        (400, "invalid_argument"),
        (409, "unsupported_capability"),
        (409, "not_configured"),
        (409, "operation_active"),
        (409, "invalid_connection_state"),
        (409, "invalid_session_state"),
        (410, "cursor_expired"),
        (409, "unsupported_session_schema"),
        (500, "persistence_fault"),
        (502, "backend_input_error"),
        (502, "hardware_fault"),
        (502, "timeout"),
        (503, "service_unavailable"),
    ],
)
async def test_v2_preserves_service_error_status_and_bounded_fields_without_retry(status, code):
    requests = []
    payload = {
        "ok": False,
        "error": code,
        "detail": "bounded service diagnostic",
        "detail_truncated": True,
        "context": {"operation": "evidence", "session_id": "s1", "reason": code},
    }

    async def handler(request):
        requests.append(request)
        return httpx.Response(status, json=payload)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreServiceError) as raised:
            await client.get_evidence(cursor="opaque")
    assert len(requests) == 1
    assert raised.value.status_code == status
    assert raised.value.payload() == payload


@pytest.mark.parametrize(
    "failure", [httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout, httpx.ReadError]
)
async def test_v2_transport_failures_are_bounded_and_do_not_retry_actions(failure):
    requests = []

    async def handler(request):
        requests.append(request)
        raise failure("private exception dump " * 1000, request=request)

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreUnavailableError) as raised:
            await client.send_uart(data_b64="eA==")
    assert len(requests) == 1
    assert raised.value.payload()["error"] == "service_unavailable"
    assert len(raised.value.detail.encode()) <= 1024
    assert "private exception" not in raised.value.detail
    if failure is httpx.ReadTimeout:
        assert "unknown" in raised.value.detail


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(200, content=b"private raw content " * 1000),
        httpx.Response(200, json=["private response"]),
        httpx.Response(409, json={"error": "private invalid error"}),
    ],
)
async def test_v2_malformed_service_responses_do_not_expose_raw_content(response):
    async def handler(request):
        return response

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreProtocolError) as raised:
            await client.get_status()
    assert len(str(raised.value).encode()) <= 1024
    assert "private" not in str(raised.value)


@pytest.mark.parametrize(
    "detail",
    ["private dump " * 1000, "unsafe\x00diagnostic", "\ud800"],
    ids=["overlong", "control", "invalid-unicode"],
)
async def test_noncanonical_service_error_detail_is_rejected_without_exposure(detail):
    async def handler(request):
        return httpx.Response(
            409,
            content=json.dumps(
                {
                    "ok": False,
                    "error": "operation_active",
                    "detail": detail,
                    "detail_truncated": False,
                }
            ).encode(),
        )

    async with DeviceCoreClient(transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(DeviceCoreProtocolError) as raised:
            await client.reset_dut()
    assert len(str(raised.value).encode()) <= 1024
    assert "private dump" not in str(raised.value)
    assert "unsafe" not in str(raised.value)
