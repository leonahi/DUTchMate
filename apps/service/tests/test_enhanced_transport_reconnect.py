"""HIL-order reconnect through installed serial/asyncio and real host/recorder."""

import json
import time
from contextlib import suppress

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

    def records(artifact):
        return [
            json.loads(line) for line in (tmp_path / session / artifact).read_text().splitlines()
        ]

    try:
        resources[0].disconnect()
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            status = client.get("/status").json()
            if status["connection_state"] == "faulted":
                break
            if status["connected"] and status["timestamp_provenance"]["segment_id"] == 1:
                break
            time.sleep(0.001)
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
        client.close()
        with suppress(Exception):
            runtime.close()
        for resource in resources:
            resource.dispose()
    assert all(resource.close_calls == 1 for resource in resources)
