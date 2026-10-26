"""Basic release regressions using the real source/recorder and fake serial I/O."""

from __future__ import annotations

import asyncio
import json
from collections import deque
from contextlib import suppress
from threading import Condition, Event, Thread

import httpx
import pytest
from fastapi.testclient import TestClient

from dutchmate_core.backends import BackendDisconnectedError
from dutchmate_core.backends.basic import BasicBackendConnection
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_service.app import create_app
from dutchmate_service.startup import build_startup_runtime


class SerialPort:
    def __init__(self) -> None:
        self.condition = Condition()
        self.reading = Event()
        self.closed = False
        self.chunks: deque[bytes] = deque()
        self.on_close = lambda: None
        self.close_error = False

    def read(self, size=1):
        self.reading.set()
        with self.condition:
            self.condition.wait_for(lambda: self.closed or self.chunks)
            if self.chunks:
                return self.chunks.popleft()
            raise OSError("controlled serial EOF")

    def feed(self, data: bytes) -> None:
        with self.condition:
            self.chunks.append(data)
            self.condition.notify_all()

    def close(self) -> None:
        self.on_close()
        with self.condition:
            self.closed = True
            self.condition.notify_all()
        if self.close_error:
            raise OSError("controlled close failure")


def build(tmp_path, monkeypatch):
    ports = []

    def opening(settings):
        port = SerialPort()
        ports.append(port)
        return BasicBackendConnection(serial_port=port, settings=settings)

    monkeypatch.setattr("dutchmate_service.startup.open_basic_backend_connection", opening)
    profile = resolve_dut_profile(DutProfileConfig(), mode="basic", serial_port="/dev/test-only")
    runtime = build_startup_runtime(session_root=tmp_path, profile=profile)
    assert ports[0].reading.wait(1)
    return runtime, ports


def events(runtime):
    root = runtime.session_store.root / runtime._evidence_recorder.active_session_id
    return [
        json.loads(line) for line in (root / "connection_events.jsonl").read_text().splitlines()
    ]


class LateCloseWakeup:
    """Order real consumer EOF before real close publishes its final wakeup."""

    def __init__(self, runtime, monkeypatch, *, pause=False):
        self.source = runtime._evidence_recorder._source
        self.terminal_seen = Event()
        self.before_wakeup = Event()
        self.allow_wakeup = Event()
        self.wakeup_published = Event()
        self.stranded = Event()
        self.rescue = Event()
        if not pause:
            self.allow_wakeup.set()
        original_read = self.source.read_event
        original_put = self.source._outcomes.put_nowait

        def read():
            try:
                return original_read()
            except BackendDisconnectedError:
                self.terminal_seen.set()
                if self.wakeup_published.is_set() and self.source.has_pending_events:
                    # Bound the broken baseline's hot loop and traceback growth.
                    self.stranded.set()
                    self.rescue.wait()
                raise

        def publish(outcome):
            assert self.terminal_seen.wait(1), "real consumer never observed EOF"
            self.before_wakeup.set()
            assert self.allow_wakeup.wait(2)
            original_put(outcome)
            self.wakeup_published.set()

        monkeypatch.setattr(self.source, "read_event", read)
        monkeypatch.setattr(self.source._outcomes, "put_nowait", publish)

    def cleanup_failed_baseline(self):
        self.allow_wakeup.set()
        if self.stranded.is_set():
            # Test-only rescue after the failure assertion; consume the wakeup
            # normally rather than discarding any FIFO RX during teardown.
            self.source._terminal_error = None
        self.rescue.set()


def test_http_release_drains_real_basic_source_after_eof_before_close_wakeup(tmp_path, monkeypatch):
    runtime, ports = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    source = recorder._source
    owner_worker = runtime._connection_owner._worker
    session = recorder.active_session_id
    raw = tmp_path / session / "uart_raw.log"
    tail = recorder.durable_tail()
    ports[0].feed(b"ambient\n")
    assert recorder.wait_for_durable_tail(tail, timeout_s=1)
    gate = LateCloseWakeup(runtime, monkeypatch)
    physical_close = Event()

    def closing():
        assert events(runtime)[-1]["type"] == "release_requested"
        # The blocked physical read returns a final admitted chunk as close
        # interrupts it; the real serial reader must enqueue and drain it.
        ports[0].feed(b"last admitted RX\n")
        physical_close.set()

    ports[0].on_close = closing
    done = Event()
    responses, failures = [], []
    client = TestClient(create_app(runtime))

    def release():
        try:
            responses.append(client.post("/connection/release"))
        except BaseException as error:
            failures.append(error)
        finally:
            done.set()

    worker = Thread(target=release, daemon=True)
    worker.start()
    try:
        assert physical_close.wait(1)
        assert gate.before_wakeup.wait(1)
        assert ports[0].closed and not source._reader.is_alive()
        assert raw.read_bytes() == b"ambient\nlast admitted RX\n"
        assert done.wait(1), "Basic release stranded a late close wakeup after terminal EOF"
        assert not failures
        assert responses[0].status_code == 200
        assert responses[0].json()["connection_state"] == "released"
        assert ports[0].closed and not source._reader.is_alive()
        assert not source.has_pending_events
        assert raw.read_bytes() == b"ambient\nlast admitted RX\n"
        assert client.get("/status").json()["connection_state"] == "released"
        metadata = runtime.session_store.load_metadata(session)
        assert metadata["segments"][0]["end_reason"] == "released"
        assert metadata["continuity"]["observation_gap_count"] == 1
        assert [e["type"] for e in events(runtime)] == [
            "connected",
            "release_requested",
            "released",
        ]
        assert client.post("/connection/reacquire").json()["connection_state"] == "connected"
        assert ports[1].reading.wait(1)
        tail = recorder.durable_tail()
        ports[1].feed(b"after gap\n")
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert raw.read_bytes() == b"ambient\nlast admitted RX\nafter gap\n"
        assert recorder.active_session_id == session
        metadata = runtime.session_store.load_metadata(session)
        assert len(metadata["segments"]) == 2
        assert metadata["segments"][1]["start_reason"] == "reacquire"
    finally:
        gate.cleanup_failed_baseline()
        assert done.wait(2), "failed regression could not clean up release"
        worker.join(timeout=1)
        runtime.close()
        client.close()
    assert not recorder._thread.is_alive()
    assert not owner_worker.is_alive()
    assert all(port.closed for port in ports)
    assert runtime.session_store.load_metadata(session)["state"] == "completed"


@pytest.mark.parametrize("concurrent_shutdown", [False, True])
async def test_cancelled_http_release_still_settles_and_relinquishes_ownership(
    tmp_path, monkeypatch, concurrent_shutdown
):
    runtime, ports = build(tmp_path, monkeypatch)
    gate = LateCloseWakeup(runtime, monkeypatch, pause=True)
    ports[0].on_close = lambda: ports[0].feed(b"cancelled request close RX\n")
    finished = Event()
    original = runtime.release_connection

    def release():
        try:
            return original()
        finally:
            finished.set()

    monkeypatch.setattr(runtime, "release_connection", release)
    shutdown_started = Event()
    cancel_pending = runtime._connection_owner.cancel_pending

    def cancel_owner():
        cancel_pending()
        shutdown_started.set()

    monkeypatch.setattr(runtime._connection_owner, "cancel_pending", cancel_owner)
    closing = None
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=create_app(runtime)), base_url="http://test"
    ) as client:
        pending = asyncio.create_task(client.post("/connection/release"))
        try:
            assert await asyncio.to_thread(gate.before_wakeup.wait, 1)
            pending.cancel()
            with pytest.raises(asyncio.CancelledError):
                await pending
            with pytest.raises(ConnectionLifecycleError) as busy:
                original()
            assert busy.value.error == "operation_active"
            if concurrent_shutdown:
                closing = asyncio.create_task(asyncio.to_thread(runtime.close))
                assert await asyncio.to_thread(shutdown_started.wait, 1)
            gate.allow_wakeup.set()
            assert await asyncio.to_thread(finished.wait, 1), "cancelled release stranded ownership"
            if closing is not None:
                await asyncio.wait_for(asyncio.shield(closing), timeout=1)
                assert (await client.get("/status")).json()["connected"] is False
            else:
                assert (await client.get("/status")).json()["connection_state"] == "released"
                assert (await client.post("/connection/reacquire")).status_code == 200
        finally:
            gate.cleanup_failed_baseline()
            assert await asyncio.to_thread(finished.wait, 2)
            with suppress(asyncio.CancelledError):
                await pending
            await asyncio.to_thread(runtime.close)
            if closing is not None:
                await closing
    assert all(port.closed for port in ports)
    assert not runtime._evidence_recorder._thread.is_alive()


def test_shutdown_drains_late_basic_wakeup_and_preserves_final_rx(tmp_path, monkeypatch):
    runtime, ports = build(tmp_path, monkeypatch)
    recorder = runtime._evidence_recorder
    session = recorder.active_session_id
    gate = LateCloseWakeup(runtime, monkeypatch)
    ports[0].on_close = lambda: ports[0].feed(b"shutdown admitted RX\n")
    done = Event()
    errors = []

    def close():
        try:
            runtime.close()
        except BaseException as error:
            errors.append(error)
        finally:
            done.set()

    worker = Thread(target=close, daemon=True)
    worker.start()
    try:
        assert gate.before_wakeup.wait(1)
        assert done.wait(1), "shutdown stranded a late close wakeup"
        assert not errors
    finally:
        gate.cleanup_failed_baseline()
        assert done.wait(2)
        worker.join(timeout=1)
    assert (tmp_path / session / "uart_raw.log").read_bytes() == b"shutdown admitted RX\n"
    assert runtime.session_store.load_metadata(session)["state"] == "completed"
    assert [e["type"] for e in events(runtime)] == ["connected"]
    assert not recorder._thread.is_alive()
    assert not gate.source._reader.is_alive()
    assert not runtime._connection_owner._worker.is_alive()


@pytest.mark.parametrize("failure", ["close", "release_requested", "released"])
def test_basic_release_error_does_not_strand_claim_or_shutdown(tmp_path, monkeypatch, failure):
    runtime, ports = build(tmp_path, monkeypatch)
    source = runtime._evidence_recorder._source
    store = runtime.session_store
    append = store.append_v2_connection_event
    if failure == "close":
        ports[0].close_error = True
    else:

        def persist(*args, **kwargs):
            if kwargs.get("event_type") == failure:
                raise SessionPersistenceError(operation="release", path=tmp_path, detail="injected")
            return append(*args, **kwargs)

        monkeypatch.setattr(store, "append_v2_connection_event", persist)
    try:
        response = TestClient(create_app(runtime)).post("/connection/release")
        assert response.status_code in {500, 503}
        assert runtime.status().connection_state == "faulted"
        assert not runtime._lifecycle_active
        assert not runtime._connection_owner._attempt_active
        assert "released" not in [e["type"] for e in events(runtime)]
        with pytest.raises(ConnectionLifecycleError) as invalid:
            runtime.reacquire_connection()
        assert invalid.value.error == "invalid_connection_state"
    finally:
        with suppress(Exception):
            runtime.close()
    assert ports[0].closed
    source._reader.join(timeout=1)
    assert not source._reader.is_alive()
    assert not runtime._evidence_recorder._thread.is_alive()
    assert not runtime._connection_owner._worker.is_alive()
