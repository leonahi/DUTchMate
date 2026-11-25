"""HIL-order reconnect through installed serial/asyncio and real host/recorder."""

import json
import time
from contextlib import suppress
from threading import Event

import pytest
from enhanced_serial_fixture import PipeSerial
from fastapi.testclient import TestClient
from serial import SerialException

from dutchmate_core.backends.enhanced_serial_io import open_async_enhanced_serial_adapter
from dutchmate_core.profile import resolve_dut_profile
from dutchmate_core.profile.config import parse_dut_profile_config
from dutchmate_service import startup
from dutchmate_service.app import create_app
from dutchmate_service.enhanced_async import open_enhanced_async_host


@pytest.mark.parametrize("close_mode", ["closed", "failed", "incomplete", "unknown"])
def test_terminal_read_cleanup_controls_replacement_opening_and_profile_ack_order(
    tmp_path, monkeypatch, close_mode
):
    resources = []
    hosts = []

    async def open_adapter(**kwargs):
        resource = PipeSerial(
            origin_us=(len(resources) + 1) * 1000,
            close_mode=close_mode if not resources else "closed",
        )
        resources.append(resource)
        return await open_async_enhanced_serial_adapter(
            **kwargs, open_connection=resource.open_connection
        )

    def open_host(**kwargs):
        host = open_enhanced_async_host(**kwargs, open_adapter=open_adapter)
        hosts.append(host)
        return host

    monkeypatch.setattr(startup, "open_enhanced_async_host", open_host)
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {
                    "mode": "enhanced",
                    "serial_port": "/test/pipe",
                    "reconnect_timeout_s": 5.0,
                },
                "hardware": {
                    "dut_io_voltage": 3.3,
                    "control": {
                        "boot": {
                            "channel": "CTRL1",
                            "dut_signal": "GP2",
                            "mode": "push_pull",
                            "active_level": "high",
                            "idle_level": "low",
                        },
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RUN",
                            "mode": "open_drain",
                            "active_level": "low",
                        },
                    },
                },
            }
        )
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    client = TestClient(create_app(runtime=runtime, profile=profile))
    recorder = runtime._evidence_recorder
    session = recorder.active_session_id
    failure_pending = Event()
    allow_failure_publication = Event()
    owner = runtime._backend_reconnect
    original_retain_close_error = owner._retain_close_error

    def retain_close_error_after_status_read(error):
        # Hold the real coordinator at the known recorder/diagnostic handoff.
        failure_pending.set()
        assert allow_failure_publication.wait(2), "test did not release diagnostic publication"
        original_retain_close_error(error)

    if close_mode != "closed":
        monkeypatch.setattr(owner, "_retain_close_error", retain_close_error_after_status_read)

    def records(artifact):
        return [
            json.loads(line) for line in (tmp_path / session / artifact).read_text().splitlines()
        ]

    try:
        resources[0].disconnect()
        if close_mode != "closed":
            assert failure_pending.wait(2), "cleanup failure did not reach coordinator"
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = client.get("/status").json()
            if failure_pending.is_set() and not allow_failure_publication.is_set():
                assert status["connection_state"] == "faulted"
                assert status.get("connection_error") is None
                allow_failure_publication.set()
            if (
                status["connection_state"] == "faulted"
                and status.get("connection_error") is not None
            ):
                break
            if status["connected"] and status["timestamp_provenance"]["segment_id"] == 1:
                break
            time.sleep(0.001)
        else:
            pytest.fail(f"Reconnect did not publish a complete terminal outcome: {status}")
        connection = records("connection_events.jsonl")
        assert [r["type"] for r in connection[:3]] == [
            "connected",
            "unexpected_disconnect",
            "reconnect_started",
        ]
        assert connection[2]["detail"]["timeout_s"] == 5.0
        if close_mode == "closed":
            assert status["connected"], status
            assert status["timestamp_provenance"]["segment_id"] == 1
            hardware = records("hardware_events.jsonl")
            attempts = [
                r for r in hardware if r["type"] == "control_attempt" and r["segment_id"] == 1
            ]
            assert [a["parameters"]["channel"] for a in attempts] == ["CTRL1", "CTRL0"]
            acks = [
                next(
                    r
                    for r in hardware
                    if r["type"] == "control_result" and r["attempt_id"] == a["attempt_id"]
                )
                for a in attempts
            ]
            assert all(r["status"] == "success" for r in acks)
            opened = next(r for r in connection if r["type"] == "segment_opened")
            success = next(r for r in connection if r["type"] == "reconnect_succeeded")
            assert (
                opened["evidence_seq"]
                < attempts[0]["evidence_seq"]
                < acks[0]["evidence_seq"]
                < attempts[1]["evidence_seq"]
                < acks[1]["evidence_seq"]
                < success["evidence_seq"]
            )
            assert [r["device_timestamp_us"] for r in acks] == [2001, 2002]
            assert client.post("/dut/reset", json={"pulse_ms": 100}).status_code == 200
            assert len(resources) == 2
        else:
            assert status["connection_state"] == "faulted"
            assert status["connection_error"]["context"]["reason"] == "cleanup_unconfirmed"
            assert len(resources) == 1  # No replacement ownership after uncertain cleanup.
            assert not any(r["type"] == "reconnect_succeeded" for r in connection)
        assert resources[0].close_calls == 1
        assert hosts[0]._adapter._terminal_error.__cause__ is resources[0].read_error
        for _ in range(2):
            if close_mode == "closed":
                runtime.close()
            else:
                with pytest.raises(SerialException) as cleanup:
                    runtime.close()
                assert cleanup.value is resources[0].read_error
    finally:
        allow_failure_publication.set()
        client.close()
        with suppress(Exception):
            runtime.close()
        for resource in resources:
            resource.dispose()
    assert all(resource.close_calls == 1 for resource in resources)


@pytest.mark.parametrize(
    "capable,response", [(False, "ok"), (True, "ok"), (True, "reject"), (True, "timeout")]
)
def test_observation_startup_without_controls_and_fresh_reacquire(
    tmp_path, monkeypatch, capable, response
):
    resources = []

    async def open_adapter(**kwargs):
        resource = PipeSerial(
            origin_us=(len(resources) + 1) * 1000, power_sense=capable, sense_response=response
        )
        resources.append(resource)
        return await open_async_enhanced_serial_adapter(
            **kwargs, open_connection=resource.open_connection
        )

    def open_host(**kwargs):
        return open_enhanced_async_host(**kwargs, open_adapter=open_adapter)

    monkeypatch.setattr(startup, "open_enhanced_async_host", open_host)
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {"mode": "enhanced", "serial_port": "/test/pipe"},
                "hardware": {"dut_io_voltage": 3.3},
            }
        )
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    try:
        if capable and response == "timeout":
            from dutchmate_core.connection import ConnectionLifecycleError

            with pytest.raises(ConnectionLifecycleError, match="timed out"):
                create_app(runtime=runtime, profile=profile)
            assert resources[0].is_open is False
            return
        client = TestClient(create_app(runtime=runtime, profile=profile))
        for epoch in range(2):
            if capable:
                assert resources[epoch].commands == [
                    {"cmd": "configure_power_sense", "enabled": True}
                ]
            else:
                assert resources[epoch].commands == []
            deadline = time.monotonic() + 2
            while capable and response == "ok" and time.monotonic() < deadline:
                health = runtime._evidence_recorder.capture_source_health()
                if health.dut_vio_observation is not None:
                    break
                time.sleep(0.001)
            health = runtime._evidence_recorder.capture_source_health()
            assert health.dut_vio_setup_rejected is (capable and response == "reject")
            if capable and response == "ok":
                assert health.dut_vio_observation.sample.voltage_mv == 3300
                assert health.dut_vio_observation.segment_id == epoch
                root = tmp_path / runtime._evidence_recorder.active_session_id
                expected = b"\xff\x00\n" * (epoch + 1)
                while (
                    time.monotonic() < deadline and (root / "uart_raw.log").read_bytes() != expected
                ):
                    time.sleep(0.001)
                assert (root / "uart_raw.log").read_bytes() == expected
            if epoch == 0:
                assert client.post("/connection/release").status_code == 200
                assert (
                    runtime._evidence_recorder.capture_source_health().dut_vio_observation is None
                )
                assert client.post("/connection/reacquire").status_code == 200
        client.close()
    finally:
        runtime.close()
        for resource in resources:
            resource.dispose()


def test_congested_uart_and_voltage_preserve_bytes_and_automatic_reconnect(tmp_path, monkeypatch):
    import base64

    resources = []

    async def open_adapter(**kwargs):
        resource = PipeSerial(origin_us=(len(resources) + 1) * 1000, power_sense=True)
        resources.append(resource)
        return await open_async_enhanced_serial_adapter(
            **kwargs, open_connection=resource.open_connection
        )

    monkeypatch.setattr(
        startup,
        "open_enhanced_async_host",
        lambda **kw: open_enhanced_async_host(**kw, open_adapter=open_adapter),
    )
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {"mode": "enhanced", "serial_port": "/test/pipe"},
                "hardware": {
                    "dut_io_voltage": 3.3,
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RUN",
                            "mode": "open_drain",
                            "active_level": "low",
                        }
                    },
                },
            }
        )
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    client = TestClient(create_app(runtime=runtime, profile=profile))
    try:
        resource = resources[0]
        assert [c["cmd"] for c in resource.commands] == [
            "configure_gpio_mode",
            "configure_power_sense",
        ]
        expected = b"\xff\x00\n"
        frames = []
        for i in range(1000):
            data = bytes([i % 256]) * 49 + b"\n"
            expected += data
            frames.append(
                json.dumps(
                    {
                        "type": "uart",
                        "channel": 0,
                        "timestamp_us": 2000 + i,
                        "data_b64": base64.b64encode(data).decode(),
                    }
                ).encode()
                + b"\n"
            )
            if i % 25 == 0:
                frames.append(
                    json.dumps(
                        {
                            "type": "dut_vio",
                            "timestamp_us": 2000 + i,
                            "status": "ok",
                            "adc_raw": 1024,
                            "voltage_mv": 1650,
                            "adc_reference_mv": 3300,
                            "reference_source": "nominal",
                        }
                    ).encode()
                    + b"\n"
                )
        payload = b"".join(frames)
        for offset in range(0, len(payload), 4096):
            resource.loop.call_soon_threadsafe(
                resource.protocol.data_received, payload[offset : offset + 4096]
            )
        root = tmp_path / runtime._evidence_recorder.active_session_id
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and (root / "uart_raw.log").read_bytes() != expected:
            time.sleep(0.001)
        assert (root / "uart_raw.log").read_bytes() == expected
        resource.disconnect()
        deadline = time.monotonic() + 3
        while time.monotonic() < deadline:
            if len(resources) == 2 and runtime.status().connection_state == "connected":
                health = runtime._evidence_recorder.capture_source_health()
                if health.dut_vio_observation is not None:
                    break
            time.sleep(0.001)
        assert len(resources) == 2
        assert resources[0].close_calls == 1
        assert [c["cmd"] for c in resources[1].commands] == [
            "configure_gpio_mode",
            "configure_power_sense",
        ]
        assert health.dut_vio_observation.segment_id == 1
        runtime.close()
        assert (root / "uart_raw.log").read_bytes() == expected + b"\xff\x00\n"
        records = []
        for path in root.glob("*_events.jsonl"):
            records.extend(json.loads(line) for line in path.read_text().splitlines())
        sequences = sorted(record["evidence_seq"] for record in records)
        assert sequences == list(range(len(sequences)))
        assert sum(r["type"] == "dut_vio" for r in records) == 42
        assert resources[1].close_calls == 1
        assert not any(r.callback_errors for r in resources)
    finally:
        client.close()
        runtime.close()
        for resource in resources:
            resource.dispose()


def test_staged_observation_setup_drains_more_than_serial_fifo_capacity(tmp_path, monkeypatch):
    resources = []

    async def open_adapter(**kwargs):
        resource = PipeSerial(origin_us=(len(resources) + 1) * 1000, power_sense=True)
        if resources:
            resource.before_sense_ack = 300
        resources.append(resource)
        return await open_async_enhanced_serial_adapter(
            **kwargs, open_connection=resource.open_connection
        )

    monkeypatch.setattr(
        startup,
        "open_enhanced_async_host",
        lambda **kw: open_enhanced_async_host(**kw, open_adapter=open_adapter),
    )
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {"mode": "enhanced", "serial_port": "/test/pipe"},
                "hardware": {"dut_io_voltage": 3.3},
            }
        )
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    client = TestClient(create_app(runtime=runtime, profile=profile))
    try:
        assert client.post("/connection/release").status_code == 200
        response = client.post("/connection/reacquire")
        assert response.status_code == 200, response.json()
        root = tmp_path / runtime._evidence_recorder.active_session_id
        deadline = time.monotonic() + 2
        expected = b"\xff\x00\n" + b"X" * 300 + b"\xff\x00\n"
        while time.monotonic() < deadline and (root / "uart_raw.log").read_bytes() != expected:
            time.sleep(0.001)
        assert (root / "uart_raw.log").read_bytes() == expected
        assert resources[1].close_calls == 0
    finally:
        runtime.close()
        client.close()
        for resource in resources:
            resource.dispose()
