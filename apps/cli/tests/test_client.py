from __future__ import annotations

import httpx
import pytest

from dutchmate_cli.client import (
    ServiceApiError,
    ServiceUnavailableError,
    configure_gpio_mode,
    fetch_status,
    reset_dut,
    set_boot_mode,
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
