"""Public durable cursor contract over the real store and recorder (no hardware)."""

import base64
import json
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient
from test_device_core_actions_v2 import setup_runtime
from test_device_core_monitor import ControlledSource, _runtime

from dutchmate_core.backends import UartReceiveEvent
from dutchmate_service.app import create_app


def publish(recorder, source, data=b"new\xff\n"):
    previous = recorder.durable_tail()
    source.publish(UartReceiveEvent(0, 42, 0, data))
    assert recorder.wait_for_durable_tail(previous, timeout_s=1)


def rollover(monkeypatch, store, session_id):
    original = store._v2_unit_fits

    def fits(metadata, *, unit_bytes):
        return metadata["session_id"] != session_id and original(metadata, unit_bytes=unit_bytes)

    monkeypatch.setattr(store, "_v2_unit_fits", fits)


def test_tail_attach_order_and_exact_bytes_are_independent_of_reader_ownership(tmp_path):
    runtime, recorder, _, source, _, _ = setup_runtime(tmp_path)
    try:
        publish(recorder, source, b"old\n")
        session = recorder.active_session_id
        client = TestClient(create_app(runtime))
        attached = client.get("/dut/evidence").json()
        assert attached["records"] == []
        assert attached["omitted_records"] == 0
        cursor = attached["next_cursor"]
        publish(recorder, source)
        runtime.send_uart(text="go", line_ending="lf")
        page = client.get("/dut/evidence", params={"cursor": cursor, "wait_s": 0}).json()
        assert [r["type"] for r in page["records"]] == [
            "uart_rx",
            "uart_tx_attempt",
            "uart_tx_result",
        ]
        rx = page["records"][0]
        assert rx["data_b64"] == "bmV3/wo="
        assert rx["display_text"] == "new\ufffd\n"
        assert rx["session_id"] == session
        assert rx["segment_id"] == 0 and rx["channel"] == 0 and rx["timestamp_us"] == 42
        assert rx["timestamp"]["source"] == "device"
        assert rx["raw_offset_start"] == 4 and rx["raw_offset_end"] == 9
        assert [r["evidence_seq"] for r in page["records"]] == [2, 3, 4]
        assert (
            client.get("/dut/evidence", params={"cursor": page["next_cursor"], "wait_s": 0}).json()[
                "records"
            ]
            == []
        )
        client.close()
        publish(recorder, source, b"still recording\n")
        assert recorder.active_session_id == session
        assert not source.closed and source.max_concurrent_reads == 1
        assert (tmp_path / session / "uart_raw.log").read_bytes().endswith(b"still recording\n")
    finally:
        runtime.close()


def test_cursor_pages_across_explicit_session_rollover(tmp_path, monkeypatch):
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    try:
        attached = runtime.evidence(wait_s=0).payload()
        predecessor = recorder.active_session_id
        publish(recorder, source, b"before\n")
        rollover(monkeypatch, store, predecessor)
        publish(recorder, source, b"after\n")
        successor = recorder.active_session_id
        assert successor != predecessor
        cursor = attached["next_cursor"]
        observed = []
        for _ in range(5):
            page = runtime.evidence(cursor=cursor, limit=1, wait_s=0).payload()
            observed.extend(page["records"])
            cursor = page["next_cursor"]
        assert [(r["session_id"], r["type"]) for r in observed] == [
            (predecessor, "uart_rx"),
            (successor, "rollover_succeeded"),
            (successor, "uart_rx"),
        ]
        assert [base64.b64decode(r["data_b64"]) for r in observed if r["type"] == "uart_rx"] == [
            b"before\n",
            b"after\n",
        ]
    finally:
        runtime.close()


def test_byte_cap_defers_whole_records_and_cursor_can_recover_them(tmp_path):
    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    client = TestClient(create_app(runtime))
    try:
        cursor = client.get("/dut/evidence").json()["next_cursor"]
        # Invalid UTF-8 expands in the display projection; both bytes and JSON overhead count.
        data = b"\xff" * 9000
        for _ in range(12):
            publish(recorder, source, data)
        response = client.get("/dut/evidence", params={"cursor": cursor, "wait_s": 0})
        assert response.status_code == 200
        assert len(response.content) <= 262144
        page = response.json()
        assert page["omitted_records"] > 0
        assert len(page["records"]) + page["omitted_records"] == 12
        records = list(page["records"])
        assert all(base64.b64decode(r["data_b64"]) == data for r in records)
        while True:
            page = runtime.evidence(cursor=page["next_cursor"], wait_s=0).payload()
            if not page["records"]:
                break
            records.extend(page["records"])
        assert [r["evidence_seq"] for r in records] == list(range(1, 13))
        assert (tmp_path / recorder.active_session_id / "uart_raw.log").read_bytes() == data * 12
        assert source.max_concurrent_reads == 1
    finally:
        client.close()
        runtime.close()


def test_retention_deleted_cursor_expires_without_skipping(tmp_path, monkeypatch):
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source, max_count=1)
    try:
        cursor = runtime.evidence(wait_s=0).payload()["next_cursor"]
        predecessor = recorder.active_session_id
        publish(recorder, source, b"unread\n")
        rollover(monkeypatch, store, predecessor)
        publish(recorder, source, b"successor\n")
        store.run_retention()
        assert not (tmp_path / predecessor).exists()
        response = TestClient(create_app(runtime)).get(
            "/dut/evidence", params={"cursor": cursor, "wait_s": 0}
        )
        assert response.status_code == 410
        assert response.json()["error"] == "cursor_expired"
    finally:
        runtime.close()


def test_long_poll_wakes_on_durable_admission(tmp_path):
    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    try:
        cursor = runtime.evidence(wait_s=0).payload()["next_cursor"]
        entered = Event()

        def poll():
            entered.set()
            return runtime.evidence(cursor=cursor, wait_s=2).payload()

        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(poll)
            assert entered.wait(1)
            assert not pending.done()
            publish(recorder, source, b"wake\n")
            page = pending.result(timeout=1)
        assert [r["data_b64"] for r in page["records"]] == ["d2FrZQo="]
        start = time.monotonic()
        empty = runtime.evidence(cursor=page["next_cursor"], wait_s=0.01).payload()
        assert empty["records"] == []
        assert time.monotonic() - start < 0.5
    finally:
        runtime.close()


@pytest.mark.parametrize(
    "params",
    [
        {"limit": 0},
        {"limit": 501},
        {"limit": 1.5},
        {"wait_s": -1},
        {"wait_s": 31},
        {"wait_s": "nan"},
        {"wait_s": "inf"},
        {"cursor": "invalid"},
        {"cursor": ""},
    ],
)
def test_invalid_evidence_queries_have_no_side_effects(tmp_path, params):
    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    try:
        before = recorder.durable_tail()
        response = TestClient(create_app(runtime)).get("/dut/evidence", params=params)
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_argument"
        assert recorder.durable_tail() == before
    finally:
        runtime.close()


def test_slow_snapshot_read_does_not_block_admission_and_has_a_committed_boundary(
    tmp_path, monkeypatch
):
    from dutchmate_core.session_store.tail import EvidenceSnapshot

    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    reading = Event()
    release = Event()
    project = EvidenceSnapshot._project

    def slow_project(snapshot, record):
        reading.set()
        assert release.wait(2)
        return project(snapshot, record)

    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        publish(recorder, source, b"first\n")
        monkeypatch.setattr(EvidenceSnapshot, "_project", slow_project)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(runtime.evidence, cursor=cursor, wait_s=0)
            try:
                assert reading.wait(1)
                # This durable admission must finish while the client's replay is blocked.
                publish(recorder, source, b"second\n")
                assert not pending.done()
                assert (tmp_path / recorder.active_session_id / "uart_raw.log").read_bytes() == (
                    b"first\nsecond\n"
                )
            finally:
                release.set()
            first = pending.result(timeout=1)
        assert [r["data_b64"] for r in first.records] == ["Zmlyc3QK"]
        second = runtime.evidence(cursor=first.next_cursor, wait_s=0)
        assert [r["data_b64"] for r in second.records] == ["c2Vjb25kCg=="]
        assert store._v2_tail_read_leases == {}
    finally:
        release.set()
        runtime.close()


def test_largest_control_byte_rx_is_delivered_whole_under_the_response_cap(tmp_path):
    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        data = b"\x00" * 32768
        publish(recorder, source, data)
        result = runtime.evidence(cursor=cursor, wait_s=0)
        assert len(result.compact_json()) <= 262144
        assert len(result.records) == 1 and result.omitted_records == 0
        assert base64.b64decode(result.records[0]["data_b64"]) == data
    finally:
        runtime.close()


def test_marker_projection_never_echoes_untrusted_disconnect_exception(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError

    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        source.publish(BackendDisconnectedError("private UART dump SECRET\x1b[31m"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        result = runtime.evidence(cursor=cursor, wait_s=0)
        assert result.records
        assert b"SECRET" not in result.compact_json()
        assert b"private UART" not in result.compact_json()
        assert all(len(str(record)) < 2000 for record in result.records)
    finally:
        runtime.close()


def service_transport(client):
    import httpx

    def request(message):
        response = client.request(
            message.method,
            str(message.url),
            content=message.read(),
            headers={"content-type": "application/json"},
        )
        return httpx.Response(response.status_code, content=response.content)

    return httpx.MockTransport(request)


@pytest.mark.parametrize("ending, expected", [("crlf", b"go\r\n"), ("profile_default", b"go")])
@pytest.mark.parametrize("interrupt", [False, True])
def test_console_http_tx_is_audited_and_eof_or_interrupt_leaves_recorder_alive(
    tmp_path,
    monkeypatch,
    ending,
    expected,
    interrupt,
):
    import io

    import serial

    from dutchmate_cli.console import run_console

    class Input(io.StringIO):
        def readline(self, *args):
            line = super().readline(*args)
            if not line and interrupt:
                raise KeyboardInterrupt
            return line

    def forbidden_serial(*args, **kwargs):
        raise AssertionError("Console opened a serial port")

    monkeypatch.setattr(serial, "Serial", forbidden_serial)
    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)
    session = recorder.active_session_id
    output = []
    try:
        with TestClient(create_app(runtime)) as client:
            run_console(
                line_ending=ending,
                input_stream=Input("go\n"),
                service_url="http://testserver",
                transport=service_transport(client),
                emit=output.append,
            )
        assert sender.calls == [expected]
        records = [
            json.loads(line)
            for line in (tmp_path / session / "operation_events.jsonl").read_text().splitlines()
        ]
        assert [r["type"] for r in records] == ["uart_tx_attempt", "uart_tx_result"]
        assert base64.b64decode(records[0]["data_b64"]) == expected
        assert records[0]["transformation"]["resolved_line_ending"] == (
            "crlf" if ending == "crlf" else "none"
        )
        assert "uart_tx_result" in "".join(output)
        assert not source.closed
        publish(recorder, source, b"ambient after console\n")
        assert recorder.active_session_id == session and source.max_concurrent_reads == 1
    finally:
        runtime.close()


def test_console_http_receives_operation_active_during_real_interact(tmp_path):
    import io

    from dutchmate_cli.console import run_console

    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)
    sent = Event()
    sender.on_send = sent.set
    cancellation = Event()
    output = []
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            operation = pool.submit(
                runtime.interact,
                text="interact",
                line_ending="none",
                duration_s=5,
                cancellation=cancellation,
            )
            try:
                assert sent.wait(1)
                with TestClient(create_app(runtime)) as client:
                    run_console(
                        line_ending="lf",
                        input_stream=io.StringIO("console\n"),
                        service_url="http://testserver",
                        transport=service_transport(client),
                        emit=output.append,
                    )
                assert "operation_active" in "".join(output)
                assert sender.calls == [b"interact"]
                assert not source.closed
            finally:
                cancellation.set()
            assert operation.result(timeout=1).outcome == "cancelled"
        publish(recorder, source, b"still ambient\n")
    finally:
        cancellation.set()
        runtime.close()


def test_snapshot_lease_protects_only_inflight_replay_and_releases_on_error(tmp_path, monkeypatch):
    from dutchmate_core.session_store.tail import EvidenceSnapshot

    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source, max_count=1)
    reading = Event()
    release = Event()

    def failed_project(snapshot, record):
        reading.set()
        assert release.wait(2)
        raise RuntimeError("view output failed")

    try:
        cursor = runtime.evidence(wait_s=0).next_cursor
        predecessor = recorder.active_session_id
        publish(recorder, source, b"before\n")
        monkeypatch.setattr(EvidenceSnapshot, "_project", failed_project)
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(runtime.evidence, cursor=cursor, wait_s=0)
            try:
                assert reading.wait(1)
                rollover(monkeypatch, store, predecessor)
                publish(recorder, source, b"after\n")
                retained = store.run_retention()
                assert predecessor in retained.protected_session_ids
                assert (tmp_path / predecessor).is_dir()
            finally:
                release.set()
            with pytest.raises(RuntimeError, match="view output failed"):
                pending.result(timeout=1)
        assert store._v2_tail_read_leases == {}
        assert predecessor in store.run_retention().deleted_session_ids
        assert not source.closed
    finally:
        release.set()
        runtime.close()


def test_offsets_inside_a_record_are_rejected_as_invalid_cursor(tmp_path):
    source = ControlledSource()
    runtime, recorder, _ = _runtime(tmp_path, source)
    try:
        # Corrupt an otherwise valid opaque token; never accept a non-record boundary.
        cursor = runtime.evidence(wait_s=0).next_cursor
        values = json.loads(base64.urlsafe_b64decode(cursor))
        values[6] = 1  # inside the initial connection JSONL record
        bad = base64.urlsafe_b64encode(json.dumps(values).encode()).decode()
        response = TestClient(create_app(runtime)).get(
            "/dut/evidence", params={"cursor": bad, "wait_s": 0}
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_argument"
    finally:
        runtime.close()


def test_attach_racing_retention_uses_the_current_tail_without_expiring(tmp_path, monkeypatch):
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source, max_count=1)
    predecessor = recorder.active_session_id
    original = store.read_evidence_page
    first = True

    def racing_read(**kwargs):
        nonlocal first
        if first:
            first = False
            rollover(monkeypatch, store, predecessor)
            publish(recorder, source, b"rollover during attach\n")
            assert not (tmp_path / predecessor).exists()
        return original(**kwargs)

    monkeypatch.setattr(store, "read_evidence_page", racing_read)
    try:
        attached = runtime.evidence(wait_s=0)
        assert attached.records == ()
        publish(recorder, source, b"after attach\n")
        page = runtime.evidence(cursor=attached.next_cursor, wait_s=0)
        assert [r["data_b64"] for r in page.records] == ["YWZ0ZXIgYXR0YWNoCg=="]
    finally:
        runtime.close()
