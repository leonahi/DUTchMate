from __future__ import annotations

import httpx
import pytest

from dutchmate_cli.client import (
    ServiceApiError,
    ServiceUnavailableError,
    capture_uart,
    configure_gpio_mode,
    fetch_recent_logs,
    fetch_status,
    get_debug_session,
    list_debug_sessions,
    reset_dut,
    run_boot_test,
    set_boot_mode,
    wait_for_pattern,
)


def test_fetch_status_returns_status_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/status"
        return httpx.Response(200, json={"connected": False, "control_channels": {}})

    payload = fetch_status(transport=httpx.MockTransport(handler))

    assert payload == {"connected": False, "control_channels": {}}


def test_fetch_status_maps_connection_failure_to_service_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ServiceUnavailableError) as error:
        fetch_status(transport=httpx.MockTransport(handler))

    assert "Run 'dutchmate start' first" in str(error.value)


def test_fetch_status_includes_service_error_detail() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"detail": "runtime failed"})

    with pytest.raises(ServiceApiError) as error:
        fetch_status(transport=httpx.MockTransport(handler))

    assert str(error.value) == "Device Core Service returned HTTP 500: runtime failed"


def test_service_error_message_preserves_structured_error_code() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            409,
            json={"error": "capture_active", "detail": "capture is already active"},
        )

    with pytest.raises(ServiceApiError) as error:
        wait_for_pattern(
            pattern="READY",
            timeout_s=1,
            transport=httpx.MockTransport(handler),
        )

    assert "[capture_active]: capture is already active" in str(error.value)


def test_list_debug_sessions_forwards_bounded_page_arguments() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions"
        assert dict(request.url.params) == {"limit": "25", "cursor": "next-page"}
        return httpx.Response(200, json={"items": [], "next_cursor": None})

    payload = list_debug_sessions(
        limit=25,
        cursor="next-page",
        transport=httpx.MockTransport(handler),
    )

    assert payload == {"items": [], "next_cursor": None}


@pytest.mark.parametrize("limit", [0, 101, True, 1.5])
def test_list_debug_sessions_rejects_invalid_limit_before_http(limit: object) -> None:
    def unexpected_request(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid session limit reached HTTP transport")

    with pytest.raises(ValueError, match="integer from 1 to 100"):
        list_debug_sessions(
            limit=limit,  # type: ignore[arg-type]
            transport=httpx.MockTransport(unexpected_request),
        )


def test_get_debug_session_fetches_exact_validated_id() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/sessions/20260820T120000Z-abc12345"
        return httpx.Response(
            200,
            json={
                "session_id": "20260820T120000Z-abc12345",
                "schema_version": 1,
                "compatibility": "native",
            },
        )

    payload = get_debug_session(
        "20260820T120000Z-abc12345",
        transport=httpx.MockTransport(handler),
    )

    assert payload["compatibility"] == "native"


def test_fetch_recent_logs_forwards_selection_and_limit() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/logs"
        assert dict(request.url.params) == {
            "lines": "12",
            "session_id": "20260820T120000Z-abc12345",
        }
        return httpx.Response(200, json={"session_id": "20260820T120000Z-abc12345"})

    payload = fetch_recent_logs(
        session_id="20260820T120000Z-abc12345",
        lines=12,
        transport=httpx.MockTransport(handler),
    )

    assert payload["session_id"] == "20260820T120000Z-abc12345"


def test_wait_for_pattern_forwards_literal_and_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/wait-pattern"
        assert request.read() == b'{"pattern":"READY.*","timeout_s":2.5}'
        return httpx.Response(200, json={"matched": False, "session_id": "wait-1"})

    payload = wait_for_pattern(
        pattern="READY.*",
        timeout_s=2.5,
        transport=httpx.MockTransport(handler),
    )

    assert payload == {"matched": False, "session_id": "wait-1"}


@pytest.mark.parametrize(
    ("pattern", "timeout_s"),
    [("", 1.0), ("bad\rpattern", 1.0), ("x" * 257, 1.0), ("READY", True)],
)
def test_wait_for_pattern_rejects_invalid_input_before_http(
    pattern: object,
    timeout_s: object,
) -> None:
    with pytest.raises(ValueError):
        wait_for_pattern(  # type: ignore[arg-type]
            pattern=pattern,
            timeout_s=timeout_s,
        )


@pytest.mark.parametrize("lines", [0, 1001, True, 1.5])
def test_fetch_recent_logs_rejects_invalid_limit_before_http(lines: object) -> None:
    with pytest.raises(ValueError, match="integer from 1 to 1000"):
        fetch_recent_logs(lines=lines)  # type: ignore[arg-type]


def test_get_debug_session_rejects_unsafe_id_before_http() -> None:
    def unexpected_request(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("unsafe session ID reached HTTP transport")

    with pytest.raises(ValueError, match="path-safe"):
        get_debug_session(
            "../outside",
            transport=httpx.MockTransport(unexpected_request),
        )


def test_configure_gpio_mode_posts_request_payload() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/gpio/mode"
        assert request.method == "POST"
        assert request.read() == (
            b'{"channel":"CTRL2","role":"power_en","dut_signal":"REG_EN",'
            b'"mode":"push_pull","active_level":"high","idle_level":"low"}'
        )
        return httpx.Response(
            200,
            json={
                "ok": True,
                "channel": "CTRL2",
                "role": "power_en",
                "dut_signal": "REG_EN",
                "mode": "push_pull",
                "active_level": "high",
                "idle_level": "low",
                "source": "runtime",
                "timestamp_us": 182334400,
            },
        )

    payload = configure_gpio_mode(
        channel="CTRL2",
        role="power_en",
        dut_signal="REG_EN",
        mode="push_pull",
        active_level="high",
        idle_level="low",
        transport=httpx.MockTransport(handler),
    )

    assert payload["channel"] == "CTRL2"
    assert payload["role"] == "power_en"


def test_configure_gpio_mode_maps_connection_failure_to_service_unavailable() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("connection refused", request=request)

    with pytest.raises(ServiceUnavailableError) as error:
        configure_gpio_mode(
            channel="CTRL0",
            role="reset",
            dut_signal="RESET_N",
            mode="open_drain",
            active_level="low",
            transport=httpx.MockTransport(handler),
        )

    assert "Run 'dutchmate start' first" in str(error.value)


@pytest.mark.parametrize(
    ("role", "dut_signal", "mode", "active_level", "idle_level"),
    [
        (" reset", "RESET_N", "open_drain", "low", None),
        ("reset", "RESET\x00N", "open_drain", "low", None),
        ("reset", "RESET_N", "open_drain", "high", None),
        ("reset", "RESET_N", "push_pull", "high", None),
        ("reset", "RESET_N", "push_pull", "high", "high"),
    ],
)
def test_configure_gpio_mode_rejects_invalid_request_before_http(
    role: str,
    dut_signal: str,
    mode: str,
    active_level: str,
    idle_level: str | None,
) -> None:
    def unexpected_request(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid GPIO configuration reached HTTP transport")

    with pytest.raises(ValueError):
        configure_gpio_mode(
            channel="CTRL0",
            role=role,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
            transport=httpx.MockTransport(unexpected_request),
        )


def test_reset_dut_posts_pulse_width() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/reset"
        assert request.method == "POST"
        assert request.read() == b'{"pulse_ms":250}'
        return httpx.Response(200, json={"ok": True, "timestamp_us": 182334500})

    payload = reset_dut(pulse_ms=250, transport=httpx.MockTransport(handler))

    assert payload == {"ok": True, "timestamp_us": 182334500}


def test_set_boot_mode_posts_mode() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/boot-mode"
        assert request.method == "POST"
        assert request.read() == b'{"mode":"bootloader"}'
        return httpx.Response(200, json={"ok": True, "timestamp_us": 182334600})

    payload = set_boot_mode(mode="bootloader", transport=httpx.MockTransport(handler))

    assert payload == {"ok": True, "timestamp_us": 182334600}


def test_capture_uart_posts_duration_with_duration_aware_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/capture"
        assert request.method == "POST"
        assert request.read() == b'{"duration_s":5.0}'
        assert request.extensions["timeout"]["read"] == 7.0
        return httpx.Response(
            200,
            json={
                "ok": True,
                "session_id": "20260729T100000Z-capture01",
                "truncated": False,
                "interrupted": False,
                "resumed": False,
                "overflow": False,
                "segments": 1,
            },
        )

    payload = capture_uart(duration_s=5.0, transport=httpx.MockTransport(handler))

    assert payload["session_id"] == "20260729T100000Z-capture01"


def test_capture_uart_maps_read_timeout_to_service_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("capture timed out", request=request)

    with pytest.raises(ServiceApiError) as error:
        capture_uart(duration_s=5.0, transport=httpx.MockTransport(handler))

    assert str(error.value) == "Device Core Service request timed out."


@pytest.mark.parametrize(
    "duration_s",
    [0.0, -1.0, 300.1, float("inf"), float("nan"), True],
)
def test_capture_uart_rejects_invalid_duration(duration_s: object) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        capture_uart(duration_s=duration_s)


def test_run_boot_test_posts_duration_with_duration_aware_timeout() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/boot-test"
        assert request.method == "POST"
        assert request.read() == b'{"duration_s":5.0}'
        assert request.extensions["timeout"]["read"] == 7.0
        return httpx.Response(
            200,
            json={
                "ok": True,
                "session_id": "20260729T100000Z-boot01",
                "truncated": False,
                "interrupted": False,
                "resumed": False,
                "overflow": False,
                "segments": 1,
            },
        )

    payload = run_boot_test(duration_s=5.0, transport=httpx.MockTransport(handler))

    assert payload["session_id"] == "20260729T100000Z-boot01"


@pytest.mark.parametrize(
    "duration_s",
    [0.0, -1.0, 300.1, float("inf"), float("nan"), True],
)
def test_run_boot_test_rejects_invalid_duration(duration_s: object) -> None:
    with pytest.raises(ValueError, match="positive finite"):
        run_boot_test(duration_s=duration_s)
