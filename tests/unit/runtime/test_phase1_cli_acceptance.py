"""Hardware-free Basic/Enhanced acceptance through CLI, HTTP, and real core/store."""

import io
import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import httpx
import pytest
from fastapi.testclient import TestClient
from test_connection_ownership import attach_owner
from test_device_core_actions_v2 import setup_runtime
from test_device_core_monitor import ControlledSource
from typer.testing import CliRunner

from dutchmate_cli import client as cli_client
from dutchmate_cli import main
from dutchmate_cli.console import run_console
from dutchmate_cli.follow import run_follow
from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.workflows.capture import ReconnectedCaptureSource
from dutchmate_service.app import create_app


class ServiceTransport(httpx.BaseTransport):
    def __init__(self, service):
        self.service = service
        self.paths = []

    def handle_request(self, request):
        self.paths.append((request.method, request.url.path))
        response = self.service.request(
            request.method,
            str(request.url),
            content=request.content,
            headers=request.headers,
        )
        return httpx.Response(
            response.status_code, content=response.content, headers=response.headers
        )


@pytest.mark.parametrize("mode", ["basic", "enhanced"])
def test_atomic_cli_surface_shares_continuous_v2_evidence(tmp_path, monkeypatch, mode):
    runtime, recorder, store, source, sender, control = setup_runtime(tmp_path, mode=mode)
    replacements = []
    snapshot = recorder.capture_source_health().backend_snapshot

    def reopen(**kwargs):
        replacement = ControlledSource()
        replacement.segment = snapshot.segment
        replacements.append(replacement)
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=snapshot)

    attach_owner(runtime, recorder, reopen)
    session = recorder.active_session_id
    service = TestClient(create_app(runtime))
    transport = ServiceTransport(service)
    original_request = cli_client._request_service

    def through_service(**kwargs):
        kwargs["transport"] = transport
        return original_request(**kwargs)

    monkeypatch.setattr(cli_client, "_request_service", through_service)
    runner = CliRunner()

    def cli(*args):
        result = runner.invoke(main.app, [*args, "--service-url", "http://acceptance"])
        assert result.exit_code == 0, (result.output, result.exception)
        return result.output

    def publish(data, timestamp=10):
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, timestamp, 0, data))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)

    try:
        publish(b"ambient before clients\n")
        assert f"Backend: {mode}" in cli("status")
        assert "elapsed" in cli("monitor", "--seconds", "0.01")

        started = Event()
        original_start = recorder.start_monitor_operation

        def start(**kwargs):
            value = original_start(**kwargs)
            started.set()
            return value

        monkeypatch.setattr(recorder, "start_monitor_operation", start)
        with ThreadPoolExecutor(max_workers=1) as pool:
            monitor = pool.submit(cli, "monitor", "--until", "READY", "--timeout", "1")
            assert started.wait(1)
            publish(b"READY\n")
            assert "matched" in monitor.result(timeout=2)

        assert "recorded" in cli("send", "--data-b64", "AP8=")
        assert sender.calls == [b"\x00\xff"]
        sender.on_send = lambda: source.publish(UartReceiveEvent(0, 20, 0, b"REPLY\n"))
        assert "matched" in cli(
            "interact", "go", "--line-ending", "crlf", "--until", "REPLY", "--timeout", "1"
        )
        assert sender.calls[-1] == b"go\r\n"
        publish(b"HardFault thirty seconds after Interact\n", 30_000_020)
        assert "HardFault" in cli("logs", "--session", session)
        assert session in cli("sessions")
        assert "2" in cli("session", session)

        cursor = cli_client.fetch_evidence(wait_s=0)["next_cursor"]
        publish(b"following\n")
        output = []

        def interrupt_view(text):
            output.append(text)
            if "following" in text:
                raise KeyboardInterrupt

        run_follow(cursor=cursor, emit=interrupt_view)
        assert "following" in "".join(output)
        publish(b"after follow detached\n")
        run_console(input_stream=io.StringIO("shell\n"), line_ending="lf", emit=output.append)
        assert sender.calls[-1] == b"shell\n"

        if mode == "enhanced":
            cli(
                "gpio",
                "mode",
                "CTRL0",
                "reset",
                "NRST",
                "--mode",
                "open_drain",
                "--active-level",
                "low",
            )
            cli(
                "gpio",
                "mode",
                "CTRL1",
                "boot",
                "BOOT0",
                "--mode",
                "push_pull",
                "--active-level",
                "high",
                "--idle-level",
                "low",
            )
            cli("dut", "boot-mode", "bootloader")

            def immediate_boot(operation, args):
                if operation == "pulse_control":
                    publish(b"FIRST BOOT BYTE\n", 30_000_030)

            control._on_call = immediate_boot
            cli("dut", "reset", "--pulse-ms", "5")
            assert "FIRST BOOT BYTE" in cli("logs", "--session", session)

        assert "released" in cli("release")
        assert source.closed
        assert "connected" in cli("reacquire")
        tail = recorder.durable_tail()
        replacements[0].publish(UartReceiveEvent(0, 1, 0, b"after handoff\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        detail = cli_client.get_debug_session(session)
        assert detail["schema_version"] == 2
        metadata = store.load_metadata(session)
        assert metadata["continuity"] == {"observation_gap_count": 1}
        assert len(metadata["segments"]) == 2
        assert source.max_concurrent_reads == 1
        assert not replacements[0].closed
        raw = (tmp_path / session / "uart_raw.log").read_bytes()
        assert b"ambient before clients\n" in raw
        assert b"HardFault thirty seconds after Interact\n" in raw
        assert b"after follow detached\n" in raw
        assert b"after handoff\n" in raw
        attempts = [
            json.loads(line)
            for line in (tmp_path / session / "operation_events.jsonl").read_text().splitlines()
            if json.loads(line)["type"] == "uart_tx_attempt"
        ]
        assert [a["data_b64"] for a in attempts] == ["AP8=", "Z28NCg==", "c2hlbGwK"]
        assert ("POST", "/dut/uart/send") in transport.paths
        assert ("GET", "/dut/evidence") in transport.paths
    finally:
        runtime.close()
        service.close()
