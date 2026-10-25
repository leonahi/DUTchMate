"""Deterministic Stage 7 lifecycle regressions, with no physical hardware."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from test_device_core_actions_v2 import setup_runtime
from test_device_core_monitor import ControlledSource, _snapshot

from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.workflows.capture import ReconnectedCaptureSource
from dutchmate_core.workflows.device_actions import DeviceActionError
from dutchmate_service.backend_reconnect import BackendReconnectCoordinator


def attach_owner(runtime, recorder, opener=None):
    replacements = []
    initial_snapshot = recorder.capture_source_health().backend_snapshot

    def open_source(**kwargs):
        if opener is not None:
            return opener(**kwargs)
        source = ControlledSource()
        replacements.append(source)
        return ReconnectedCaptureSource(source=source, backend_snapshot=initial_snapshot)

    owner = BackendReconnectCoordinator(source_owner=recorder, open_replacement=open_source)
    runtime._connection_owner = owner
    runtime._backend_reconnect = owner
    return owner, replacements


def connections(store, recorder):
    return [
        json.loads(line)
        for line in (store.root / recorder.active_session_id / "connection_events.jsonl")
        .read_text()
        .splitlines()
    ]


def test_release_is_durable_before_close_drains_rx_and_preserves_session_and_cursor(tmp_path):
    runtime, recorder, store, source, _, _ = setup_runtime(tmp_path)
    owner, replacements = attach_owner(runtime, recorder)
    original_close = source.close
    session = recorder.active_session_id
    observed = Event()

    def close():
        try:
            assert connections(store, recorder)[-1]["type"] == "release_requested"
            source.publish(UartReceiveEvent(0, 10, 0, b"admitted before close\n"))
            observed.set()
        finally:
            original_close()

    source.close = close
    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        released = runtime.release_connection()
        assert released.connection_state == "released"
        assert observed.is_set() and source.closed
        assert runtime.status().connection_state == "released"
        assert runtime.status().connected is False
        assert runtime.status().active_session_id == session
        assert not recorder.wait_for_idle_disconnect(0)
        metadata = store.load_metadata(session)
        assert metadata["state"] == "active"
        assert metadata["segments"][-1]["end_reason"] == "released"
        assert metadata["continuity"]["observation_gap_count"] == 1
        assert (tmp_path / session / "uart_raw.log").read_bytes() == b"admitted before close\n"
        reacquired = runtime.reacquire_connection()
        assert reacquired.connection_state == "connected"
        assert reacquired.segment_id == 1 and reacquired.session_id == session
        tail = recorder.durable_tail()
        replacements[0].publish(UartReceiveEvent(0, 3, 0, b"after gap\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        page = runtime.evidence(cursor=cursor, wait_s=0)
        kinds = [r["type"] for r in page.records]
        assert kinds.index("release_requested") < kinds.index("released")
        assert (
            kinds.index("released")
            < kinds.index("reacquire_started")
            < kinds.index("reacquire_succeeded")
        )
        assert "unexpected_disconnect" not in kinds
        assert [r["segment_id"] for r in page.records if r["type"] == "uart_rx"] == [0, 1]
    finally:
        runtime.close()


def test_monitor_finishes_released_while_follow_does_not_own_transport(tmp_path):
    runtime, recorder, store, source, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    started = Event()
    original_start = recorder.start_monitor_operation

    def start(**kwargs):
        result = original_start(**kwargs)
        started.set()
        return result

    recorder.start_monitor_operation = start
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(runtime.monitor, duration_s=10)
            assert started.wait(1)
            cursor = runtime.evidence(wait_s=0).next_cursor
            runtime.release_connection()
            assert pending.result(timeout=1).outcome == "released"
            assert any(
                r["type"] == "released" for r in runtime.evidence(cursor=cursor, wait_s=0).records
            )
    finally:
        runtime.close()


def test_release_rejects_inflight_tx_without_interrupting_its_audit(tmp_path):
    runtime, recorder, store, _, sender, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    entered, finish = Event(), Event()

    def sending():
        entered.set()
        assert finish.wait(2)

    sender.on_send = sending
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            sent = pool.submit(runtime.send_uart, text="go", line_ending="none")
            try:
                assert entered.wait(1)
                with pytest.raises((ConnectionLifecycleError, DeviceActionError)) as raised:
                    runtime.release_connection()
                assert raised.value.error == "operation_active"
                assert recorder.state == "connected"
            finally:
                finish.set()
            assert sent.result(timeout=1).audit_status == "recorded"
    finally:
        finish.set()
        runtime.close()


def test_competing_reacquire_fails_busy_and_shutdown_prevents_publication(tmp_path):
    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)
    entered, finish, shutdown = Event(), Event(), Event()
    replacement = ControlledSource()

    def opening(**kwargs):
        entered.set()
        assert finish.wait(2)
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=_snapshot())

    owner, _ = attach_owner(runtime, recorder, opening)
    original_cancel = owner.cancel_pending if hasattr(owner, "cancel_pending") else lambda: None

    def cancel():
        original_cancel()
        shutdown.set()

    owner.cancel_pending = cancel
    try:
        runtime.release_connection()
        with ThreadPoolExecutor(max_workers=2) as pool:
            reacquire = pool.submit(runtime.reacquire_connection)
            try:
                assert entered.wait(1)
                with pytest.raises((ConnectionLifecycleError, DeviceActionError)) as raised:
                    runtime.reacquire_connection()
                assert raised.value.error == "operation_active"
                closing = pool.submit(runtime.close)
                assert shutdown.wait(1)
            finally:
                finish.set()
            with pytest.raises(ConnectionLifecycleError):
                reacquire.result(timeout=1)
            closing.result(timeout=1)
        assert replacement.closed
        with pytest.raises(ConnectionLifecycleError):
            runtime.reacquire_connection()
    finally:
        finish.set()
        runtime.close()


def test_reacquire_after_terminal_session_creates_a_fresh_journal(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError

    runtime, recorder, store, source, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    old = recorder.active_session_id
    try:
        source.publish(BackendDisconnectedError("cable lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect()
        recorder.reconnect_timed_out()
        assert runtime.status().connection_state == "disconnected"
        boundary = runtime.reacquire_connection()
        assert boundary.session_id != old and boundary.segment_id == 0
        assert store.load_metadata(old)["state"] == "failed"
        assert store.load_metadata(boundary.session_id)["state"] == "active"
    finally:
        runtime.close()


@pytest.mark.parametrize("confirmed", [True, False])
def test_failed_reacquire_cleanup_certainty_controls_future_ownership(tmp_path, confirmed):
    from contextlib import suppress

    from dutchmate_core.backends.contracts import BackendOpenError

    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)
    attempts = []

    def opening(**kwargs):
        attempts.append(True)
        raise BackendOpenError(cleanup_confirmed=confirmed)

    attach_owner(runtime, recorder, opening)
    try:
        runtime.release_connection()
        with pytest.raises((ConnectionLifecycleError, DeviceActionError)) as raised:
            runtime.reacquire_connection()
        assert raised.value.context["reason"] == (
            "open_failed" if confirmed else "cleanup_unconfirmed"
        )
        assert runtime.status().connection_state == ("released" if confirmed else "faulted")
        with pytest.raises(ConnectionLifecycleError):
            runtime.reacquire_connection()
        assert len(attempts) == (2 if confirmed else 1)
    finally:
        with suppress(Exception):
            runtime.close()


def test_release_rejects_active_interact_and_read_only_activity_does_not_block(tmp_path):
    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    sent, cancellation = Event(), Event()
    sender.on_send = sent.set
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            operation = pool.submit(
                runtime.interact,
                text="go",
                line_ending="none",
                duration_s=10,
                cancellation=cancellation,
            )
            try:
                assert sent.wait(1)
                runtime.evidence(wait_s=0)
                with pytest.raises((ConnectionLifecycleError, DeviceActionError)) as raised:
                    runtime.release_connection()
                assert raised.value.error == "operation_active"
            finally:
                cancellation.set()
            assert operation.result(timeout=1).outcome == "cancelled"
        assert runtime.release_connection().connection_state == "released"
    finally:
        cancellation.set()
        runtime.close()


def test_http_release_reacquire_and_cursor_contract(tmp_path):
    from fastapi.testclient import TestClient

    from dutchmate_service.app import create_app

    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    try:
        with TestClient(create_app(runtime)) as client:
            cursor = client.get("/dut/evidence").json()["next_cursor"]
            response = client.post("/connection/release")
            assert response.status_code == 200
            assert response.json()["connection_state"] == "released"
            assert client.get("/status").json()["connection_state"] == "released"
            assert client.post("/connection/release").status_code == 409
            resumed = client.post("/connection/reacquire")
            assert resumed.status_code == 200 and resumed.json()["segment_id"] == 1
            page = client.get("/dut/evidence", params={"cursor": cursor, "wait_s": 0}).json()
            assert "released" in [r["type"] for r in page["records"]]
    finally:
        runtime.close()


def test_detach_cancels_a_late_manual_open_before_publication(tmp_path):
    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)
    entered, finish = Event(), Event()
    replacement = ControlledSource()

    def opening(**kwargs):
        entered.set()
        assert finish.wait(2)
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=_snapshot())

    attach_owner(runtime, recorder, opening)
    try:
        runtime.release_connection()
        with ThreadPoolExecutor(max_workers=1) as pool:
            opening_request = pool.submit(runtime.reacquire_connection)
            try:
                assert entered.wait(1)
                runtime.disconnect()
            finally:
                finish.set()
            with pytest.raises(ConnectionLifecycleError):
                opening_request.result(timeout=1)
        assert replacement.closed
        assert recorder.state != "connected"
    finally:
        finish.set()
        runtime.close()


def test_unclassified_open_failure_is_blocking_without_cleanup_proof(tmp_path):
    from contextlib import suppress

    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)

    def opening(**kwargs):
        raise RuntimeError("no cleanup proof returned")

    attach_owner(runtime, recorder, opening)
    try:
        runtime.release_connection()
        with pytest.raises(ConnectionLifecycleError) as raised:
            runtime.reacquire_connection()
        assert raised.value.context["reason"] == "cleanup_unconfirmed"
        assert runtime.status().connection_state == "faulted"
    finally:
        with suppress(Exception):
            runtime.close()


def test_release_called_inside_a_submitted_mutation_is_still_busy(tmp_path):
    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    rejection = []

    def during_send():
        try:
            runtime.release_connection()
        except (ConnectionLifecycleError, DeviceActionError) as exc:
            rejection.append(exc.error)

    sender.on_send = during_send
    try:
        runtime.send_uart(text="go", line_ending="none")
        assert rejection == ["operation_active"]
        assert recorder.state == "connected"
    finally:
        runtime.close()


def test_reacquire_rolls_over_segment_bound_and_preserves_public_cursor(tmp_path):
    runtime, recorder, store, _, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    predecessor = recorder.active_session_id
    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        for _ in range(32):
            runtime.release_connection()
            boundary = runtime.reacquire_connection()
        assert boundary.session_id != predecessor and boundary.segment_id == 0
        old = store.load_metadata(predecessor)
        current = store.load_metadata(boundary.session_id)
        assert old["state"] == "completed" and old["end_reason"] == "rollover_segments"
        assert len(old["segments"]) == 32
        assert current["segments"][0]["start_reason"] == "reacquire"
        page = runtime.evidence(cursor=cursor, limit=500, wait_s=0)
        assert sum(r["type"] == "released" for r in page.records) == 32
        assert sum(r["type"] == "reacquire_succeeded" for r in page.records) == 32
    finally:
        runtime.close()


def test_new_ownership_session_does_not_inherit_prior_session_loss(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError, BufferOverflowEvent

    runtime, recorder, store, source, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    try:
        tail = recorder.durable_tail()
        source.publish(BufferOverflowEvent(0, 1, 0, 7))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        source.publish(BackendDisconnectedError("lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect()
        recorder.reconnect_timed_out()
        runtime.reacquire_connection()
        assert runtime.status().integrity.dropped_bytes == 0
    finally:
        runtime.close()


def test_follow_cursor_at_terminal_session_reports_expiry_for_new_ownership(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError
    from dutchmate_core.evidence.tail import EvidenceCursorExpired

    runtime, recorder, _, source, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    try:
        source.publish(BackendDisconnectedError("lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect()
        recorder.reconnect_timed_out()
        cursor = runtime.evidence(wait_s=0).next_cursor
        runtime.reacquire_connection()
        with pytest.raises(EvidenceCursorExpired):
            runtime.evidence(cursor=cursor, wait_s=0)
    finally:
        runtime.close()


def test_rollover_while_released_does_not_publish_a_fake_open_segment(tmp_path, monkeypatch):
    runtime, recorder, store, _, _, _ = setup_runtime(tmp_path)
    attach_owner(runtime, recorder)
    try:
        runtime.release_connection()
        predecessor = recorder.active_session_id
        original = store._v2_unit_fits

        def full(metadata, *, unit_bytes):
            return metadata["session_id"] != predecessor and original(
                metadata, unit_bytes=unit_bytes
            )

        monkeypatch.setattr(store, "_v2_unit_fits", full)
        boundary = runtime.reacquire_connection()
        assert boundary.session_id != predecessor
        metadata = store.load_metadata(boundary.session_id)
        assert metadata["segments"][0]["ended_at"] is not None
        assert metadata["segments"][0]["end_reason"] == "released"
        assert metadata["continuity"]["observation_gap_count"] == 1
        assert metadata["segments"][-1]["start_reason"] == "reacquire"
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "event_type", ["release_requested", "released", "reacquire_started", "reacquire_succeeded"]
)
def test_lifecycle_persistence_failure_preserves_fault_and_never_reports_free_ownership(
    tmp_path, monkeypatch, event_type
):
    from contextlib import suppress

    from dutchmate_core.session_store.models import SessionPersistenceError

    runtime, recorder, store, _, _, _ = setup_runtime(tmp_path)
    _, replacements = attach_owner(runtime, recorder)
    original = store.append_v2_connection_event

    def append(*args, **kwargs):
        if kwargs.get("event_type") == event_type:
            raise SessionPersistenceError(
                operation="lifecycle", path=tmp_path, detail="injected failure"
            )
        return original(*args, **kwargs)

    try:
        if event_type.startswith("reacquire"):
            runtime.release_connection()
        monkeypatch.setattr(store, "append_v2_connection_event", append)
        operation = (
            runtime.reacquire_connection
            if event_type.startswith("reacquire")
            else runtime.release_connection
        )
        with pytest.raises(SessionPersistenceError):
            operation()
        assert runtime.status().connection_state == "faulted"
        assert all(source.closed for source in replacements)
        with pytest.raises(ConnectionLifecycleError):
            runtime.reacquire_connection()
    finally:
        with suppress(Exception):
            runtime.close()
