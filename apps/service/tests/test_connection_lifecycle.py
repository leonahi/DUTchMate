"""Real service composition with deterministic fake physical ports only."""

from threading import Condition, Event

import pytest

from dutchmate_core.backends.basic import BasicBackendConnection
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.device_connection.discovery import SerialPortCandidate
from dutchmate_core.profile import resolve_dut_profile
from dutchmate_core.profile.config import parse_dut_profile_config
from dutchmate_service.startup import build_startup_runtime


class Port:
    def __init__(self):
        self.condition = Condition()
        self.closed = False
        self.disconnected = False
        self.reading = Event()

    def read(self, size=1):
        self.reading.set()
        with self.condition:
            self.condition.wait_for(lambda: self.closed or self.disconnected)
        raise OSError("physical surrogate closed")

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()

    def disconnect(self):
        with self.condition:
            self.disconnected = True
            self.condition.notify_all()

    def write(self, data):
        return len(data)


def build(tmp_path, monkeypatch):
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {
                    "mode": "basic",
                    "serial_port": "/dev/old",
                    "topology": "native_usb_console",
                    "selector": {"vid": 1000, "pid": 2000, "serial_number": "unit"},
                },
            }
        )
    )
    candidates = [
        SerialPortCandidate("/dev/old", "test", "usb", vid=1000, pid=2000, serial_number="unit")
    ]
    opened = []

    def open_connection(settings):
        port = Port()
        opened.append((settings, port))
        return BasicBackendConnection(serial_port=port, settings=settings)

    monkeypatch.setattr(
        "dutchmate_core.backends.selection.list_serial_ports", lambda: list(candidates)
    )
    monkeypatch.setattr("dutchmate_service.startup.open_basic_backend_connection", open_connection)
    runtime = build_startup_runtime(session_root=tmp_path, profile=profile)
    assert opened[0][1].reading.wait(1)
    return runtime, candidates, opened


def change_path(candidates, path):
    candidates[:] = [
        SerialPortCandidate(path, "test", "usb", vid=1000, pid=2000, serial_number="unit")
    ]


def test_native_usb_manual_reacquire_accepts_unique_path_and_retains_provenance(
    tmp_path, monkeypatch
):
    runtime, candidates, opened = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    session = recorder.active_session_id
    try:
        runtime.release_connection()
        assert opened[0][1].closed
        change_path(candidates, "/dev/new")
        boundary = runtime.reacquire_connection()
        assert boundary.session_id == session and boundary.segment_id == 1
        assert opened[1][1].reading.wait(1)
        assert runtime.status().port == "/dev/new"
        metadata = runtime.session_store.load_metadata(session)
        assert [s["backend"]["port"] for s in metadata["segments"]] == ["/dev/old", "/dev/new"]
        assert metadata["segments"][1]["serial"]["open_transition"] == "driver_managed"
        assert metadata["continuity"]["observation_gap_count"] == 1
    finally:
        runtime.close()


def test_ambiguous_native_usb_reacquire_reports_reason_without_opening(tmp_path, monkeypatch):
    runtime, candidates, opened = build(tmp_path, monkeypatch)
    try:
        runtime.release_connection()
        change_path(candidates, "/dev/a")
        candidates.append(
            SerialPortCandidate("/dev/b", "test", "usb", vid=1000, pid=2000, serial_number="unit")
        )
        with pytest.raises(ConnectionLifecycleError) as raised:
            runtime.reacquire_connection()
        assert raised.value.context["reason"] == "ambiguous_device"
        assert runtime.status().connection_state == "released"
        assert len(opened) == 1
        change_path(candidates, "/dev/new")
        assert runtime.reacquire_connection().connection_state == "connected"
    finally:
        runtime.close()


def test_native_usb_automatic_reconnect_keeps_unobserved_gap_and_changes_segment(
    tmp_path, monkeypatch
):
    runtime, candidates, opened = build(tmp_path, monkeypatch)
    session = runtime.status().active_session_id
    opened_replacement = Event()
    original = runtime._backend_reconnect._open_replacement

    def open_replacement(**kwargs):
        replacement = original(**kwargs)
        opened_replacement.set()
        return replacement

    runtime._backend_reconnect._open_replacement = open_replacement
    try:
        change_path(candidates, "/dev/new")
        opened[0][1].disconnect()
        assert opened_replacement.wait(1)
        assert opened[1][1].reading.wait(1)
        status = runtime.status()
        assert status.connected and status.port == "/dev/new"
        metadata = runtime.session_store.load_metadata(session)
        assert len(metadata["segments"]) == 2
        assert metadata["continuity"]["observation_gap_count"] == 1
        assert (tmp_path / session / "uart_raw.log").read_bytes() == b""
    finally:
        runtime.close()


def test_released_recorder_suppresses_real_worker_reopen(tmp_path, monkeypatch):
    runtime, candidates, opened = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    observed_release = Event()
    original = recorder.wait_for_idle_disconnect

    def wait(timeout):
        if recorder.state == "released":
            observed_release.set()
        return original(timeout)

    monkeypatch.setattr(recorder, "wait_for_idle_disconnect", wait)
    try:
        runtime.release_connection()
        assert observed_release.wait(1)
        assert len(opened) == 1 and opened[0][1].closed
        assert not recorder.wait_for_idle_disconnect(0)
    finally:
        runtime.close()


def test_automatic_open_cleanup_failure_faults_and_blocks_ownership(tmp_path, monkeypatch):
    from contextlib import suppress

    from dutchmate_core.backends.contracts import BackendOpenError

    runtime, _, opened = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    attempted = Event()

    def unknown(**kwargs):
        attempted.set()
        raise BackendOpenError(cleanup_confirmed=False)

    monkeypatch.setattr(runtime._backend_reconnect, "_open_replacement", unknown)
    try:
        opened[0][1].disconnect()
        assert attempted.wait(1)
        assert recorder.wait_for_fault(timeout_s=1)
        assert runtime.status().connection_state == "faulted"
        with pytest.raises(ConnectionLifecycleError):
            runtime.reacquire_connection()
    finally:
        with suppress(Exception):
            runtime.close()


def test_automatic_ambiguous_usb_selection_fails_explicitly_without_opening(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient

    from dutchmate_service.app import create_app

    runtime, candidates, opened = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    try:
        change_path(candidates, "/dev/a")
        candidates.append(
            SerialPortCandidate("/dev/b", "test", "usb", vid=1000, pid=2000, serial_number="unit")
        )
        opened[0][1].disconnect()
        with recorder._condition:
            assert recorder._condition.wait_for(lambda: recorder.state == "disconnected", timeout=1)
        payload = TestClient(create_app(runtime)).get("/status").json()
        assert payload["connection_error"]["error"] == "service_unavailable"
        assert payload["connection_error"]["context"]["reason"] == "ambiguous_device"
        assert len(opened) == 1
    finally:
        runtime.close()


def test_service_entrypoint_preserves_resolved_usb_identity_arguments(tmp_path, monkeypatch):
    from dutchmate_service import main

    received = []

    def create(**kwargs):
        received.append(kwargs["profile"])
        return object()

    monkeypatch.setattr(main, "create_app", create)
    monkeypatch.setattr(main.uvicorn, "run", lambda *args, **kwargs: None)
    main.main(
        [
            "--config",
            str(tmp_path / "absent.toml"),
            "--backend",
            "basic",
            "--serial-port",
            "/dev/old",
            "--topology",
            "native_usb_console",
            "--usb-vid",
            "1000",
            "--usb-pid",
            "2000",
            "--usb-serial-number",
            "unit",
        ]
    )
    assert received[0].selector.strategy == "usb_identity"
    assert received[0].selector.serial_number == "unit"
    assert received[0].backend_settings.usb_vid == 1000


def test_confirmed_open_cleanup_preserves_idle_retry_backoff():
    from test_backend_reconnect import ClosableSource, FakeClock, FakeSourceOwner

    from dutchmate_core.backends.contracts import BackendOpenError
    from dutchmate_core.workflows.capture import ReconnectedCaptureSource
    from dutchmate_service.backend_reconnect import BackendReconnectCoordinator

    clock = FakeClock()
    source = FakeSourceOwner()
    attempted = []
    delays = []

    def opening(**kwargs):
        attempted.append(True)
        if len(attempted) <= 2:
            raise BackendOpenError(cleanup_confirmed=True)
        return ReconnectedCaptureSource(source=ClosableSource(), backend_snapshot=None)

    def wait(delay):
        delays.append(delay)
        clock.sleep(delay)
        return False

    owner = BackendReconnectCoordinator(
        source_owner=source,
        open_replacement=opening,
        monotonic_clock=clock,
        wait_for_idle_retry=wait,
    )
    try:
        assert owner._retry_idle(deadline=10)
        assert delays == [0.1, 0.2]
    finally:
        owner.close()
