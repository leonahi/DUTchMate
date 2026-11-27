"""Exercise the load runner against the current CLI without a live service."""

import json
import runpy
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from typer.testing import CliRunner

from dutchmate_cli import client, main

SCRIPT = (
    Path(__file__).parents[3] / "hardware/firmware/rp2350_debug_helper/tools/run_load_profile.py"
)


@pytest.mark.parametrize("command,accepted_bytes", [("SUSTAIN", 8), ("BURST", 6)])
@pytest.mark.parametrize("send_allowed,capture_exit", [(True, 0), (False, 0), (True, 1)])
def test_load_profile_sends_explicit_lf_and_reports_cli_failures(
    tmp_path, monkeypatch, command, accepted_bytes, send_allowed, capture_exit
):
    # Catch retired CLI flags, missing/wrong line endings and ignored exit codes.
    run = runpy.run_path(str(SCRIPT))["main"]
    monkeypatch.setitem(
        run.__globals__,
        "__file__",
        str(tmp_path / "hardware/firmware/rp2350_debug_helper/tools/run_load_profile.py"),
    )
    pid_file = tmp_path / ".dutchmate/dutchmate-service.pid"
    pid_file.parent.mkdir()
    pid_file.write_text("12345\n")
    output = tmp_path / "results/load.json"
    monkeypatch.setattr(sys, "argv", [str(SCRIPT), command, "--out", str(output)])
    monkeypatch.setitem(run.__globals__, "time", SimpleNamespace(sleep=lambda _: None))
    requests = []

    def handle(request):
        assert request.method == "POST"
        assert request.url.path == "/dut/uart/send"
        requests.append(json.loads(request.content))
        if not send_allowed:
            return httpx.Response(409, json={"detail": "UART TX disabled by policy"})
        return httpx.Response(
            200, json={"ok": True, "audit_status": "recorded", "accepted_bytes": accepted_bytes}
        )

    def send(**kwargs):
        return client.send_uart_command(**kwargs, transport=httpx.MockTransport(handle))

    monkeypatch.setattr(main, "send_uart_command", send)

    def run_cli(args, **kwargs):
        result = CliRunner().invoke(main.app, args[1:])
        return subprocess.CompletedProcess(args, result.exit_code, result.output, "")

    class Capture:
        returncode = capture_exit

        def communicate(self, timeout=None):
            return "capture result\n", None

        def poll(self):
            return self.returncode

    # Only the slow capture subprocess is replaced; send uses the real CLI/client.
    monkeypatch.setitem(
        run.__globals__,
        "subprocess",
        SimpleNamespace(
            Popen=lambda *args, **kwargs: Capture(),
            run=run_cli,
            PIPE=subprocess.PIPE,
            STDOUT=subprocess.STDOUT,
            CompletedProcess=subprocess.CompletedProcess,
        ),
    )
    if send_allowed and capture_exit == 0:
        run()
    else:
        with pytest.raises(SystemExit) as failure:
            run()
        assert failure.value.code == 1

    assert requests == [{"text": command, "line_ending": "lf"}]
    result = json.loads(output.read_text())
    assert result["fixture_command"] == command
    assert result["send_exit_code"] == (0 if send_allowed else 1)
    assert result["capture_exit_code"] == capture_exit
    assert result["capture_output"] == "capture result\n"
    if not send_allowed:
        assert "UART TX disabled by policy" in result["send_output"]
