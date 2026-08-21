from __future__ import annotations

import httpx
import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceApiError, send_uart_command
from dutchmate_cli.send import format_uart_send


def test_send_client_forwards_text_flags_without_raw_encoding() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/dut/uart/send"
        assert request.read() == b'{"cmd":"go","append_newline":false,"force":true}'
        return httpx.Response(
            200,
            json={
                "ok": True,
                "performed_at": "2026-08-21T10:00:00Z",
                "device_timestamp_us": 10,
                "attempt_id": "attempt01",
                "perturbation_logged": True,
            },
        )

    payload = send_uart_command(
        "go",
        append_newline=False,
        force=True,
        transport=httpx.MockTransport(handler),
    )

    assert payload["attempt_id"] == "attempt01"


def test_send_client_validates_final_payload_before_http() -> None:
    def unexpected(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("invalid UART payload reached HTTP")

    with pytest.raises(ValueError, match="1..1024"):
        send_uart_command(
            "",
            append_newline=False,
            transport=httpx.MockTransport(unexpected),
        )


def test_send_client_failure_reports_unknown_acceptance_warning() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            502,
            json={
                "error": "timeout",
                "detail": "UART send timed out",
                "context": {
                    "attempt_id": "attempt01",
                    "bytes_accepted": None,
                    "may_have_reached_dut": True,
                },
            },
        )

    with pytest.raises(ServiceApiError) as raised:
        send_uart_command(
            "go",
            force=True,
            transport=httpx.MockTransport(handler),
        )

    message = str(raised.value)
    assert "Attempt: attempt01" in message
    assert "accepted bytes: unknown" in message
    assert "bytes may have reached the DUT" in message


def test_format_forced_send_reports_attempt_and_evidence_pair() -> None:
    output = format_uart_send(
        {
            "performed_at": "2026-08-21T10:00:00Z",
            "device_timestamp_us": 100,
            "attempt_id": "attempt01",
            "perturbation_logged": True,
        }
    )

    assert "UART command sent" in output
    assert "Device timestamp: 100 us" in output
    assert "Attempt: attempt01" in output
    assert "Perturbation logged: yes" in output


def test_send_command_composes_no_newline_and_force(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_send(
        cmd: str,
        *,
        append_newline: bool,
        force: bool,
        service_url: str,
    ) -> dict[str, object]:
        assert cmd == "go"
        assert append_newline is False
        assert force is True
        assert service_url == "http://127.0.0.1:2040"
        return {
            "performed_at": "2026-08-21T10:00:00Z",
            "attempt_id": "attempt01",
            "perturbation_logged": True,
        }

    monkeypatch.setattr(main, "send_uart_command", fake_send)

    result = CliRunner().invoke(main.app, ["send", "go", "--no-newline", "--force"])

    assert result.exit_code == 0
    assert "Attempt: attempt01" in result.output
