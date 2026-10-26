"""Exercise service-test isolation without a real service or serial device."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.models import SessionHandle
from dutchmate_core.session_store.store import SessionStore
from dutchmate_service.app import create_app

SERVICE_TESTS = Path(__file__).resolve().parent


def _active_session(root: Path) -> tuple[SessionStore, SessionHandle]:
    profile = resolve_dut_profile(DutProfileConfig(), mode="basic", serial_port="/dev/test-only")
    snapshot = BackendSnapshot(
        info=BackendInfo(
            mode="basic",
            port="/dev/test-only",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
        ),
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
                observation_point="host_serial_read",
                event_granularity="serial_read_chunk",
            ),
        ),
        integrity=UartIntegrity(
            loss_status="not_observable", observation_scope=None, dropped_bytes=None
        ),
    )
    store = SessionStore(root=root)
    handle = store.create_v2_session(profile=profile, backend_snapshot=snapshot)
    store.append_v2_uart_receive(handle, event=UartReceiveEvent(0, 10, 0, b"external RX\n"))
    return store, handle


def _state_snapshot(root: Path) -> dict[str, tuple[bytes, int]]:
    return {
        str(path.relative_to(root)): (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }


def test_service_tests_preserve_unrelated_default_state(tmp_path: Path) -> None:
    """Catch default-root test startup abandoning an unrelated active v2 session."""
    developer = tmp_path / "developer"
    state = developer / ".dutchmate"
    store, handle = _active_session(state / "sessions")
    (state / "config.toml").write_text("# unrelated developer configuration\n")
    (state / "dutchmate-service.pid").write_text("42424242\n")
    (state / "dutchmate-service.log").write_text("unrelated live service log\n")
    before = _state_snapshot(state)
    isolated_tests = tmp_path / "service-tests"

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            str(SERVICE_TESTS / "test_errors.py"),
            f"{__file__}::test_startup_still_recovers_stale_v2_session[default]",
            "-q",
            "-p",
            "no:cacheprovider",
            "--basetemp",
            str(isolated_tests),
        ],
        cwd=developer,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    metadata = store.load_metadata(handle.session_id)
    assert metadata["state"] == "active"
    assert metadata["end_reason"] is None
    assert metadata["ended_at"] is None
    assert _state_snapshot(state) == before
    # The default-root app also wrote and recovered its own per-test session.
    assert list(isolated_tests.glob("*/.dutchmate/sessions/*/metadata.json"))


@pytest.mark.parametrize("session_root", ("default", "explicit"))
def test_startup_still_recovers_stale_v2_session(tmp_path: Path, session_root: str) -> None:
    """Catch isolation that disables intentional production startup recovery."""
    root = Path(".dutchmate/sessions") if session_root == "default" else tmp_path / "stale-sessions"
    store, handle = _active_session(root)
    raw = handle.paths.uart_raw.read_bytes()
    events = handle.paths.uart_events.read_bytes()

    app = create_app() if session_root == "default" else create_app(session_root=root)
    with TestClient(app) as client:
        response = client.get(f"/sessions/{handle.session_id}")

    assert response.status_code == 200
    assert response.json()["state"] == "abandoned"
    assert response.json()["end_reason"] == "service_restart"
    metadata = json.loads(handle.paths.metadata.read_text())
    assert metadata["state"] == "abandoned"
    assert metadata["segments"][0]["end_reason"] == "service_restart"
    assert store.load_metadata(handle.session_id)["ended_at"] is not None
    assert handle.paths.uart_raw.read_bytes() == raw
    assert handle.paths.uart_events.read_bytes() == events
