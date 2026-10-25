"""Connection ownership commands are thin service clients."""

import httpx
import pytest
from typer.testing import CliRunner

from dutchmate_cli import main
from dutchmate_cli.client import ServiceClientError
from dutchmate_cli.status import format_status


@pytest.mark.parametrize("action", ["release", "reacquire"])
def test_ownership_client_calls_only_the_atomic_service_endpoint(action):
    from dutchmate_cli.client import change_connection

    def handler(request):
        assert request.method == "POST"
        assert request.url.path == f"/connection/{action}"
        return httpx.Response(
            200,
            json={"ok": True, "connection_state": "released", "session_id": "one", "segment_id": 0},
        )

    assert change_connection(action, transport=httpx.MockTransport(handler))["session_id"] == "one"


@pytest.mark.parametrize("action", ["release", "reacquire"])
def test_commands_resolve_url_and_display_boundary_without_backend_access(action, monkeypatch):
    def change(requested, *, service_url):
        assert requested == action and service_url == "http://local:2041"
        return {
            "ok": True,
            "connection_state": "released",
            "session_id": "session-one",
            "segment_id": 2,
        }

    monkeypatch.setattr(main, "change_connection", change, raising=False)
    result = CliRunner().invoke(main.app, [action, "--service-url", "http://local:2041"])
    assert result.exit_code == 0, result.output
    assert "session-one" in result.output and "released" in result.output


@pytest.mark.parametrize("state", ["connecting", "released", "reacquiring", "faulted"])
def test_status_displays_explicit_ownership_state(state):
    assert f"Connection: {state}" in format_status({"connection_state": state, "connected": False})


def test_ownership_client_reports_cleanup_unconfirmed():
    from dutchmate_cli.client import change_connection

    with pytest.raises(ServiceClientError, match="cleanup_unconfirmed"):
        change_connection(
            "reacquire",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(
                    503,
                    json={
                        "error": "service_unavailable",
                        "detail": "Cleanup unconfirmed",
                        "context": {"reason": "cleanup_unconfirmed"},
                    },
                )
            ),
        )


def test_start_forwards_resolved_usb_selector_to_service_process(tmp_path, monkeypatch):
    from test_lifecycle import FakeProcess

    from dutchmate_cli.lifecycle import start_service
    from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile

    calls = []

    def popen(command, **kwargs):
        calls.append(command)
        return FakeProcess()

    monkeypatch.setattr("dutchmate_cli.lifecycle.subprocess.Popen", popen)
    checks = iter([False, True])
    profile = resolve_dut_profile(
        DutProfileConfig(
            mode="basic",
            serial_port="/dev/old",
            topology="native_usb_console",
            usb_vid=1000,
            usb_pid=2000,
            usb_serial_number="unit",
        )
    )
    start_service(
        profile=profile,
        host="127.0.0.1",
        port=2040,
        pid_file=tmp_path / "pid",
        log_file=tmp_path / "log",
        wait_timeout_s=0,
        health_check=lambda url: next(checks),
        is_running=lambda pid: False,
    )
    command = calls[0]
    assert command[command.index("--usb-vid") + 1] == "1000"
    assert command[command.index("--usb-pid") + 1] == "2000"
    assert command[command.index("--usb-serial-number") + 1] == "unit"
