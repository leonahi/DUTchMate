"""Actual Enhanced parser/adapter/owner-loop input reaches continuous v2 evidence."""

import base64
import json

from test_enhanced_serial import FakeAsyncSerialReader

from dutchmate_core.backends.enhanced_serial import AsyncEnhancedSerialAdapter
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.profile import DutProfileConfig, UartProfileConfig, resolve_dut_profile
from dutchmate_service import startup
from dutchmate_service.enhanced_async import open_enhanced_async_host


def frame(value):
    return (json.dumps(value) + "\n").encode()


class FixtureWire:
    def __init__(self, reader):
        self.reader = reader
        self.commands = []
        self.timestamp = 1000

    def uart(self, data):
        self.timestamp += 100
        return frame(
            {
                "type": "uart",
                "channel": 0,
                "timestamp_us": self.timestamp,
                "data_b64": base64.b64encode(data).decode(),
            }
        )

    async def write_frame(self, data):
        command = json.loads(data)
        self.commands.append(command)
        response = {"ok": True, "timestamp_us": self.timestamp}
        prefix = b""
        if command["cmd"] == "pulse_control":
            prefix = self.uart(b"FIRST BOOT BYTE\n")
        if command["cmd"] == "uart_send":
            response["bytes_accepted"] = len(base64.b64decode(command["data_b64"]))
            prefix = self.uart(b"REPLY\n")
        self.reader.feed(prefix + frame(response))


def test_enhanced_wire_telemetry_control_reconnect_and_v2_evidence(tmp_path, monkeypatch):
    hosts = []
    wires = []
    readers = []

    async def open_adapter(*, port, segment_id, baudrate):
        reader = FakeAsyncSerialReader()
        wire = FixtureWire(reader)
        readers.append(reader)
        wires.append(wire)
        reader.feed(
            frame(
                {
                    "type": "hello",
                    "v": 1,
                    "firmware": "stage8-test",
                    "device": "dutchmate-rp2350",
                    "capabilities": [
                        "uart_receive",
                        "uart_send",
                        "gpio_control",
                        "device_timestamp",
                    ],
                }
            )
            + wire.uart(b"ambient before operations\n")
        )
        adapter = AsyncEnhancedSerialAdapter(
            reader=reader,
            writer=wire,
            port=port,
            segment_id=segment_id,
        )
        await adapter.start(1)
        return adapter

    def open_host(**kwargs):
        host = open_enhanced_async_host(**kwargs, open_adapter=open_adapter)
        hosts.append(host)
        return host

    monkeypatch.setattr(startup, "open_enhanced_async_host", open_host)
    profile = resolve_dut_profile(
        DutProfileConfig(
            uart=UartProfileConfig(tx_enabled=True),
            hardware=HardwareGpioConfig(dut_io_voltage=3.3, controls={}),
        ),
        mode="enhanced",
        serial_port="/dev/ttyACM0",
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    recorder = runtime._evidence_recorder
    store = runtime.session_store
    session = recorder.active_session_id

    def feed(data):
        tail = recorder.durable_tail()
        hosts[-1]._loop.call_soon_threadsafe(readers[-1].feed, data)
        assert recorder.wait_for_durable_tail(tail, timeout_s=2)

    try:
        # A sentinel proves the initial UART event survived origin establishment.
        feed(wires[-1].uart(b"idle sentinel\n"))
        raw_path = tmp_path / session / "uart_raw.log"
        assert raw_path.read_bytes().startswith(b"ambient before operations\n")
        assert runtime.monitor(duration_s=0.01).outcome == "elapsed"
        from dutchmate_core.operations import MonitorCondition

        assert (
            runtime.interact(
                data_b64="AP8=", conditions=(MonitorCondition("REPLY"),), timeout_s=1
            ).outcome
            == "matched"
        )
        runtime.configure_gpio_mode(
            role="reset",
            channel="CTRL0",
            dut_signal="NRST",
            mode="open_drain",
            active_level="low",
        )
        runtime.configure_gpio_mode(
            role="boot",
            channel="CTRL1",
            dut_signal="BOOT0",
            mode="push_pull",
            active_level="high",
            idle_level="low",
        )
        runtime.set_boot_mode(mode="bootloader")
        runtime.reset_dut(pulse_ms=5)
        feed(wires[-1].uart(b"after reset\n"))
        assert b"FIRST BOOT BYTE\n" in raw_path.read_bytes()
        assert (
            runtime.monitor(
                conditions=(MonitorCondition("FIRST BOOT BYTE"),), timeout_s=0.01
            ).outcome
            == "timeout"
        )

        feed(
            frame(
                {"type": "buffer_overflow", "channel": 0, "timestamp_us": 1500, "dropped_bytes": 7}
            )
        )
        feed(
            frame(
                {
                    "type": "buffer_status",
                    "timestamp_us": 1600,
                    "uart_rx_size_bytes": 32768,
                    "uart_rx_used_bytes": 0,
                    "uart_rx_high_water_bytes": 32768,
                    "dropped_bytes_total": 7,
                    "overflow_events": 1,
                }
            )
        )
        detail = store.get_session_detail(session)
        assert detail.summary.evidence_quality["backend_integrity"] == {
            "loss_status": "loss_reported",
            "dropped_bytes": 7,
            "observation_scope": "debug_helper_rx_buffer",
        }
        assert runtime.status().active_operations == ()

        runtime.release_connection()
        runtime.reacquire_connection()
        feed(wires[-1].uart(b"new segment\n"))
        metadata = store.load_metadata(session)
        assert len(metadata["segments"]) == 2
        for segment in metadata["segments"]:
            assert segment["timestamp"]["source"] == "device"
            assert segment["timestamp"]["clock"] == "rp2350_timer"
            assert segment["timestamp"]["source_origin_us"] == 1100
        hardware = [
            json.loads(line)
            for line in (tmp_path / session / "hardware_events.jsonl").read_text().splitlines()
        ]
        assert [r["type"] for r in hardware].count("control_attempt") == 4
        assert [r["type"] for r in hardware].count("control_result") == 4
        status = next(r for r in hardware if r["type"] == "buffer_status")
        assert status["uart_rx_size_bytes"] == 32768
        assert status["uart_rx_high_water_bytes"] == 32768
        assert status["dropped_bytes_total"] == 7
        commands = wires[0].commands
        assert [c["cmd"] for c in commands] == [
            "uart_send",
            "configure_gpio_mode",
            "configure_gpio_mode",
            "set_control_state",
            "pulse_control",
        ]
        assert all("role" not in c and "dut_signal" not in c for c in commands)
        assert all("EVENT" not in json.dumps(c) for c in commands)
        assert all(r.maximum_concurrent_reads == 1 for r in readers)
    finally:
        runtime.close()
