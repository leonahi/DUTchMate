"""Stage 5 CLI payloads and bounded interaction surface."""

import json

import httpx
from typer.testing import CliRunner

import dutchmate_cli.client as client
import dutchmate_cli.main as main


def test_send_client_preserves_exact_payload_and_has_no_force():
    requests = []

    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json={"ok": True, "data_b64": "AP8="})

    client.send_uart_command(data_b64="AP8=", transport=httpx.MockTransport(handle))
    assert requests == [{"data_b64": "AP8="}]


def test_interact_command_sends_explicit_text_and_completion(monkeypatch):
    requests = []

    def interact(**kwargs):
        requests.append(kwargs)
        return {"operation_id": "interact-1", "outcome": "timeout", "evidence_ranges": []}

    monkeypatch.setattr(main, "interact_uart", interact, raising=False)
    result = CliRunner().invoke(
        main.app, ["interact", "go", "--line-ending", "lf", "--until", "READY", "--timeout", "1"]
    )
    assert result.exit_code == 0
    assert "Interact timeout" in result.stdout
    assert requests[0]["text"] == "go"
    assert requests[0]["line_ending"] == "lf"


def test_send_command_requires_explicit_line_ending_and_rejects_force(monkeypatch):
    requests = []

    def send(**kwargs):
        requests.append(kwargs)
        return {"ok": True, "audit_status": "recorded", "accepted_bytes": 2}

    monkeypatch.setattr(main, "send_uart_command", send)
    assert CliRunner().invoke(main.app, ["send", "go"]).exit_code == 2
    assert CliRunner().invoke(main.app, ["send", "go", "--force"]).exit_code == 2
    result = CliRunner().invoke(main.app, ["send", "--data-b64", "AP8="])
    assert result.exit_code == 0
    assert requests[0]["data_b64"] == "AP8="
