"""HTTP-only follow and line-console behavior; no serial or daemon ownership."""

import io
import json
from threading import Event

import httpx
import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceClientError


def page(cursor, records=(), omitted=0):
    return {"ok": True, "records": list(records), "next_cursor": cursor, "omitted_records": omitted}


def test_follow_uses_returned_cursor_and_exits_only_the_view_on_interrupt(monkeypatch):
    from dutchmate_cli.follow import run_follow

    requests = []
    output = []

    def handler(request):
        requests.append(request)
        assert request.method == "GET" and request.url.path == "/dut/evidence"
        if len(requests) == 1:
            assert "cursor" not in request.url.params
            return httpx.Response(200, json=page("opaque-a"))
        if len(requests) == 2:
            assert request.url.params["cursor"] == "opaque-a"
            return httpx.Response(
                200,
                json=page(
                    "opaque-b",
                    [
                        {
                            "session_id": "session",
                            "evidence_seq": 2,
                            "type": "uart_rx",
                            "display_text": "hello\ufffd\n",
                            "data_b64": "aGVsbG//Cg==",
                        }
                    ],
                    omitted=3,
                ),
            )
        assert request.url.params["cursor"] == "opaque-b"
        raise KeyboardInterrupt

    def forbidden(*args, **kwargs):
        raise AssertionError("client view tried to change recorder ownership")

    monkeypatch.setattr(main, "start_service", forbidden)
    monkeypatch.setattr(main, "stop_service", forbidden)
    run_follow(transport=httpx.MockTransport(handler), emit=output.append)
    assert "hello\ufffd\n" in "".join(output)
    assert "3" in "".join(output) and "deferred" in "".join(output)
    assert len(requests) == 3


def test_follow_reports_expiry_and_does_not_silently_reattach():
    from dutchmate_cli.follow import run_follow

    requests = []

    def handler(request):
        requests.append(request)
        assert request.url.params["cursor"] == "expired"
        return httpx.Response(
            410,
            json={"ok": False, "error": "cursor_expired", "detail": "Cursor no longer retained"},
        )

    with pytest.raises(ServiceClientError, match="cursor_expired"):
        run_follow(cursor="expired", transport=httpx.MockTransport(handler))
    assert len(requests) == 1


@pytest.mark.parametrize("ending, expected", [("crlf", "crlf"), ("profile_default", "lf")])
def test_console_sends_lines_through_service_and_displays_authoritative_evidence(ending, expected):
    from dutchmate_cli.console import run_console

    requests = []
    output = []
    sent = Event()

    def handler(request):
        requests.append(request)
        if request.url.path == "/status":
            return httpx.Response(
                200,
                json={
                    "capabilities": ["uart_receive", "uart_send"],
                    "effective_profile": {"hardware": {"uart": {"default_line_ending": "lf"}}},
                },
            )
        if request.url.path == "/dut/evidence":
            if "cursor" not in request.url.params:
                return httpx.Response(200, json=page("attached"))
            sent.wait(0.05)
            return httpx.Response(
                200,
                json=page(
                    "sent",
                    [
                        {
                            "type": "uart_tx_result",
                            "accepted_bytes": 4,
                            "status": "accepted",
                            "session_id": "session",
                            "evidence_seq": 2,
                        }
                    ],
                ),
            )
        assert request.url.path == "/dut/uart/send" and request.method == "POST"
        assert json.loads(request.read()) == {"text": "go", "line_ending": expected}
        sent.set()
        return httpx.Response(200, json={"ok": True, "audit_status": "recorded"})

    run_console(
        line_ending=ending,
        input_stream=io.StringIO("go\r\n"),
        transport=httpx.MockTransport(handler),
        emit=output.append,
    )
    assert sent.is_set()
    assert {r.url.path for r in requests} == {"/status", "/dut/evidence", "/dut/uart/send"}
    assert "uart_tx_result" in "".join(output)


def test_console_requires_effective_uart_send_before_attach_or_input():
    from dutchmate_cli.console import run_console

    def handler(request):
        assert request.url.path == "/status"
        return httpx.Response(200, json={"capabilities": ["uart_receive"]})

    with pytest.raises(ServiceClientError, match="uart_send"):
        run_console(input_stream=io.StringIO("go\n"), transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("interrupt", [False, True])
def test_console_eof_or_ctrl_c_closes_only_client_requests(interrupt):
    from dutchmate_cli.console import run_console

    class Input(io.StringIO):
        def readline(self, *args):
            if interrupt:
                raise KeyboardInterrupt
            return ""

    def handler(request):
        if request.url.path == "/status":
            return httpx.Response(200, json={"capabilities": ["uart_send"]})
        assert request.method == "GET" and request.url.path == "/dut/evidence"
        return httpx.Response(200, json=page("tail"))

    run_console(
        input_stream=Input(),
        line_ending="lf",
        transport=httpx.MockTransport(handler),
        emit=lambda text: None,
    )


def test_console_reports_operation_active_and_can_read_the_next_line():
    from dutchmate_cli.console import run_console

    attempts = []
    output = []

    def handler(request):
        if request.url.path == "/status":
            return httpx.Response(200, json={"capabilities": ["uart_send"]})
        if request.url.path == "/dut/evidence":
            return httpx.Response(200, json=page("tail"))
        assert request.url.path == "/dut/uart/send"
        attempts.append(json.loads(request.read()))
        return httpx.Response(
            409, json={"ok": False, "error": "operation_active", "detail": "Interact is active"}
        )

    run_console(
        input_stream=io.StringIO("one\ntwo\n"),
        line_ending="lf",
        transport=httpx.MockTransport(handler),
        emit=output.append,
    )
    assert [a["text"] for a in attempts] == ["one", "two"]
    assert "operation_active" in "".join(output)


@pytest.mark.parametrize("command", ["follow", "console"])
def test_commands_use_resolved_service_url_and_handle_client_exit(command, monkeypatch):
    calls = []

    def run(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr(main, f"run_{command}", run, raising=False)
    result = CliRunner().invoke(main.app, [command, "--service-url", "http://local:1234"])
    assert result.exit_code == 0, result.output
    assert calls[0]["service_url"] == "http://local:1234"
