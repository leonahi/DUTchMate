"""Stage 5 action evidence and exclusive bounded interactions."""

from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from pathlib import Path
from threading import Event

import pytest
from runtime_test_support import FakeDeviceControl
from test_device_core_monitor import ControlledSource, _snapshot

from dutchmate_core.backends import BackendUartSendResult, UartReceiveEvent
from dutchmate_core.device_connection.messages import CommandSuccessMessage
from dutchmate_core.evidence import ContinuousEvidenceRecorder
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.operations import MonitorCondition
from dutchmate_core.profile import DutProfileConfig, UartProfileConfig, resolve_dut_profile
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.device_actions import DeviceActionError


def records(root: Path, session: str, stream: str = "operation") -> list[dict]:
    return [
        json.loads(line)
        for line in (root / session / f"{stream}_events.jsonl").read_text().splitlines()
    ]


class Sender:
    def __init__(self) -> None:
        self.calls: list[bytes] = []
        self.on_send = lambda: None
        self.device_timestamp_us = 10

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        self.calls.append(data)
        self.on_send()
        return BackendUartSendResult(
            bytes_accepted=len(data), device_timestamp_us=self.device_timestamp_us
        )


def setup_runtime(tmp_path: Path, *, tx_enabled=True, mode="enhanced"):
    source = ControlledSource()
    profile = resolve_dut_profile(
        DutProfileConfig(
            uart=UartProfileConfig(tx_enabled=tx_enabled),
            hardware=HardwareGpioConfig(dut_io_voltage=3.3, controls={}),
        ),
        mode=mode,
        serial_port="/dev/ttyACM0" if mode == "enhanced" else "/dev/ttyUSB0",
    )
    snapshot = _snapshot()
    capabilities = snapshot.info.capabilities | {"uart_send", "gpio_control"}
    snapshot = replace(
        snapshot,
        info=replace(snapshot.info, capabilities=capabilities),
        capabilities=capabilities if tx_enabled else capabilities - {"uart_send"},
        capability_policy=replace(
            snapshot.capability_policy,
            uart_send=replace(snapshot.capability_policy.uart_send, tx_policy_enabled=tx_enabled),
        ),
    )
    if mode == "basic":
        from dutchmate_core.backends import SegmentTimestamp, UartIntegrity

        source.segment = replace(
            source.segment,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
                observation_point="host_serial_read",
                event_granularity="host_read_chunk",
            ),
        )
        capabilities = frozenset({"uart_receive", "uart_send"})
        snapshot = replace(
            snapshot,
            info=replace(
                snapshot.info,
                mode="basic",
                port="/dev/ttyUSB0",
                device=None,
                firmware=None,
                capabilities=capabilities,
            ),
            capabilities=capabilities if tx_enabled else capabilities - {"uart_send"},
            segment=source.segment,
            integrity=UartIntegrity("not_observable", None, None),
        )
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source, session_store=store, profile=profile, backend_snapshot=snapshot
    )
    sender = Sender()
    if mode == "basic":
        sender.device_timestamp_us = None
    control = FakeDeviceControl([CommandSuccessMessage(timestamp_us=1)] * 20)
    runtime = DeviceCoreRuntime(
        device_control=control,
        uart_sender=sender,
        session_store=store,
        profile=profile,
        evidence_recorder=recorder,
    )
    runtime.record_backend_connection(snapshot.info)
    return runtime, recorder, store, source, sender, control


def test_standalone_send_is_durable_before_dispatch_and_rx_remains_separate(tmp_path):
    runtime, recorder, store, source, sender, _ = setup_runtime(tmp_path)
    session = recorder.active_session_id

    def check_attempt():
        assert records(tmp_path, session)[-1]["type"] == "uart_tx_attempt"
        assert records(tmp_path, session)[-1]["data_b64"] == "AP8="

    sender.on_send = check_attempt
    try:
        result = runtime.send_uart(data_b64="AP8=")
        assert result.data_b64 == "AP8="
        assert result.accepted_bytes == 2
        assert result.audit_status == "recorded"
        assert records(tmp_path, session)[-1]["type"] == "uart_tx_result"
        assert (store.root / session / "uart_raw.log").read_bytes() == b""
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, 2, 0, b"ambient\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
    finally:
        runtime.close()


def test_interact_starts_before_tx_and_matches_immediate_rx(tmp_path):
    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)
    session = recorder.active_session_id

    def reply():
        assert [r["type"] for r in records(tmp_path, session)] == [
            "operation_started",
            "uart_tx_attempt",
        ]
        source.publish(UartReceiveEvent(0, 20, 0, b"periodic log\nREADY\n"))

    sender.on_send = reply
    try:
        result = runtime.interact(
            text="go", line_ending="lf", conditions=(MonitorCondition("READY"),), timeout_s=1
        )
        assert result.outcome == "matched"
        assert result.tx.data_b64 == "Z28K"
        assert result.match.excerpt_raw == b"READY\n"
        assert source.max_concurrent_reads == 1
        assert (tmp_path / session / "uart_raw.log").read_bytes() == b"periodic log\nREADY\n"
    finally:
        runtime.close()


def test_interact_excludes_mutations_but_monitor_and_standalone_send_coexist(tmp_path):
    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    sent = Event()
    sender.on_send = sent.set
    cancellation = Event()
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            operation = pool.submit(
                runtime.interact,
                text="go",
                line_ending="none",
                duration_s=1,
                cancellation=cancellation,
            )
            assert sent.wait(1)
            for mutate in [
                lambda: runtime.send_uart(text="x", line_ending="none"),
                runtime.reset_dut,
                lambda: runtime.set_boot_mode(mode="normal"),
                lambda: runtime.interact(text="x", line_ending="none", duration_s=0.01),
            ]:
                with pytest.raises(Exception) as exc:
                    mutate()
                assert exc.value.error == "operation_active"
            monitor = pool.submit(runtime.monitor, duration_s=0.01)
            assert monitor.result(timeout=1).outcome == "elapsed"
            cancellation.set()
            assert operation.result(timeout=1).outcome == "cancelled"
        assert runtime.send_uart(text="x", line_ending="none").accepted_bytes == 1
    finally:
        cancellation.set()
        runtime.close()


def test_persistence_failure_prevents_dispatch(tmp_path, monkeypatch):
    runtime, recorder, store, _, sender, _ = setup_runtime(tmp_path)

    def fail(*args, **kwargs):
        raise SessionPersistenceError(operation="attempt", path=tmp_path, detail="disk full")

    monkeypatch.setattr(store, "append_v2_uart_tx_attempt", fail)
    try:
        with pytest.raises(SessionPersistenceError):
            runtime.send_uart(text="go", line_ending="none")
        assert sender.calls == []
        assert recorder.state == "faulted"
    finally:
        runtime.close()


def test_audited_reset_persists_immediate_boot_rx_without_a_monitor(tmp_path):
    runtime, recorder, _, source, _, control = setup_runtime(tmp_path)
    runtime.configure_gpio_mode(
        role="reset", channel="CTRL0", dut_signal="NRST", mode="open_drain", active_level="low"
    )
    session = recorder.active_session_id

    def early_boot(operation, args):
        assert operation == "pulse_control"
        assert records(tmp_path, session) == []
        assert records(tmp_path, session, "hardware")[-1]["type"] == "control_attempt"
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, 20, 0, b"READY\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)

    control._on_call = early_boot
    try:
        result = runtime.reset_dut()
        assert result.action == "reset"
        assert records(tmp_path, session) == []
        assert (tmp_path / session / "uart_raw.log").read_bytes() == b"READY\n"
        assert records(tmp_path, session, "hardware")[-1]["type"] == "control_result"
        later = runtime.monitor(conditions=(MonitorCondition("READY"),), timeout_s=0.01)
        assert later.outcome == "timeout"
        assert source.max_concurrent_reads == 1
        assert not source.closed
    finally:
        runtime.close()


def test_runtime_has_no_boot_test_composite() -> None:
    assert not hasattr(DeviceCoreRuntime, "run_boot_test")


def test_service_byte_payload_interact_and_reset_contracts(tmp_path):
    from fastapi.testclient import TestClient

    from dutchmate_service.app import create_app

    runtime, recorder, _, _, _, _ = setup_runtime(tmp_path)
    client = TestClient(create_app(runtime))
    try:
        response = client.post("/dut/uart/send", json={"data_b64": "AP8="})
        assert response.status_code == 200
        assert response.json()["data_b64"] == "AP8="
        assert response.json()["audit_status"] == "recorded"
        for invalid in [
            {"text": "go"},
            {"data_b64": "eA==", "force": True},
            {"cmd": "go", "append_newline": True},
        ]:
            assert client.post("/dut/uart/send", json=invalid).status_code == 400
        response = client.post(
            "/dut/interact",
            json={
                "text": "go",
                "line_ending": "none",
                "conditions": [{"pattern": "NEVER"}],
                "timeout_s": 0.01,
            },
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "timeout"
        assert response.json()["tx"]["accepted_bytes"] == 2
        assert response.json()["evidence_ranges"]
        runtime.configure_gpio_mode(
            role="reset", channel="CTRL0", dut_signal="NRST", mode="open_drain", active_level="low"
        )
        response = client.post("/dut/reset", json={"pulse_ms": 5})
        assert response.status_code == 200
        assert response.json()["pulse_ms"] == 5
    finally:
        runtime.close()


def test_monitor_coexists_with_serialized_tx_control_and_continuous_rx(tmp_path):
    runtime, recorder, _, source, sender, control = setup_runtime(tmp_path)
    runtime.configure_gpio_mode(
        role="reset", channel="CTRL0", dut_signal="NRST", mode="open_drain", active_level="low"
    )
    entered, release, cancelled = Event(), Event(), Event()

    def hold_tx():
        entered.set()
        assert release.wait(2)

    sender.on_send = hold_tx
    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            monitor = pool.submit(runtime.monitor, duration_s=2, cancellation=cancelled)
            sending = pool.submit(runtime.send_uart, data_b64="eA==")
            assert entered.wait(1)
            reset = pool.submit(runtime.reset_dut)
            tail = recorder.durable_tail()
            source.publish(UartReceiveEvent(0, 1, 0, b"ambient during TX\n"))
            assert recorder.wait_for_durable_tail(tail, timeout_s=1)
            assert len(control.calls) == 1  # Only the earlier GPIO configuration.
            assert not reset.done()
            release.set()
            assert sending.result(timeout=1).accepted_bytes == 1
            assert reset.result(timeout=1).action == "reset"
            cancelled.set()
            assert monitor.result(timeout=1).outcome == "cancelled"
        events = sorted(
            records(tmp_path, recorder.active_session_id)
            + records(tmp_path, recorder.active_session_id, "hardware"),
            key=lambda event: event["evidence_seq"],
        )
        kinds = [event["type"] for event in events]
        assert kinds.index("uart_tx_result") < len(kinds) - 2
        assert kinds[-3:-1] == ["control_attempt", "control_result"]
    finally:
        release.set()
        cancelled.set()
        runtime.close()


def test_control_attempt_persistence_failure_prevents_hardware_dispatch(tmp_path, monkeypatch):
    runtime, recorder, store, _, _, control = setup_runtime(tmp_path)

    def fail(*args, **kwargs):
        raise SessionPersistenceError(operation="Control", path=tmp_path, detail="disk full")

    monkeypatch.setattr(store, "append_v2_control_attempt", fail)
    try:
        with pytest.raises(SessionPersistenceError):
            runtime.configure_gpio_mode(
                role="reset",
                channel="CTRL0",
                dut_signal="NRST",
                mode="open_drain",
                active_level="low",
            )
        assert control.calls == []
        assert recorder.state == "faulted"
    finally:
        runtime.close()


def test_partial_tx_failure_is_audited_without_retry(tmp_path):
    from dutchmate_core.backends import BackendWriteError
    from dutchmate_core.workflows.uart_send import UartSendError

    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)

    def fail():
        raise BackendWriteError("short write", bytes_accepted=1)

    sender.on_send = fail
    try:
        with pytest.raises(UartSendError) as error:
            runtime.send_uart(text="go", line_ending="none")
        assert error.value.context["bytes_accepted"] == 1
        terminal = records(tmp_path, recorder.active_session_id)[-1]
        assert terminal["type"] == "uart_tx_result"
        assert terminal["accepted_bytes"] == 1
        assert terminal["status"] == "hardware_fault"
        assert sender.calls == [b"go"]
    finally:
        runtime.close()


def test_failed_tx_result_persistence_remains_unknown_after_recovery(tmp_path, monkeypatch):
    from dutchmate_core.workflows.uart_send import UartSendError

    runtime, recorder, store, _, sender, _ = setup_runtime(tmp_path)
    session = recorder.active_session_id

    def fail(*args, **kwargs):
        raise SessionPersistenceError(operation="TX result", path=tmp_path, detail="disk full")

    monkeypatch.setattr(store, "append_v2_uart_tx_result", fail)
    try:
        with pytest.raises(UartSendError) as error:
            runtime.send_uart(data_b64="eA==")
        assert error.value.context["outcome"] == "unknown"
        assert sender.calls == [b"x"]
        assert recorder.state == "faulted"
        assert [r["type"] for r in records(tmp_path, session)] == ["uart_tx_attempt"]
    finally:
        runtime.close()
    recovered = SessionStore(root=tmp_path)
    assert recovered.get_session_detail(session).unresolved_uart_tx_attempts == 1


@pytest.mark.parametrize("reconnect", [True, False])
def test_interact_reconnect_retains_operation_and_never_retries_tx(tmp_path, reconnect):
    from test_device_core_monitor import _segment

    from dutchmate_core.backends import BackendDisconnectedError

    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)
    sent = Event()
    sender.on_send = sent.set
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                runtime.interact,
                text="go",
                line_ending="none",
                conditions=(MonitorCondition("READY"),),
                timeout_s=1,
            )
            assert sent.wait(1)
            source.publish(BackendDisconnectedError("link lost"))
            assert recorder.wait_for_disconnect(timeout_s=1)
            snapshot = recorder.capture_source_health().backend_snapshot
            recorder.close_current_source_for_reconnect()
            if reconnect:
                replacement = ControlledSource(segment_id=1)
                recorder.replace_source(
                    replacement, backend_snapshot=replace(snapshot, segment=_segment(1))
                )
                replacement.publish(UartReceiveEvent(1, 1, 0, b"READY\n"))
            else:
                recorder.reconnect_timed_out()
            result = pending.result(timeout=1)
        assert result.outcome == ("matched" if reconnect else "disconnected")
        assert result.tx.accepted_bytes == 2
        assert sender.calls == [b"go"]
        terminal = records(tmp_path, result.end_cursor.session_id)[-1]
        assert terminal["operation_type"] == "interact"
        assert terminal["operation_id"] == result.operation_id
    finally:
        runtime.close()


def test_interact_shutdown_cancels_and_releases_lease(tmp_path):
    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    sent = Event()
    sender.on_send = sent.set
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending = pool.submit(runtime.interact, data_b64="eA==", duration_s=2)
        assert sent.wait(1)
        runtime.close()
        assert pending.result(timeout=1).outcome == "cancelled"
    assert recorder.state == "closed"


def test_interact_deadline_during_disconnect_is_disconnected(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError

    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)

    def disconnect():
        source.publish(BackendDisconnectedError("link lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)

    sender.on_send = disconnect
    try:
        result = runtime.interact(data_b64="eA==", duration_s=0.05)
        assert result.outcome == "disconnected"
    finally:
        runtime.close()


def test_shutdown_waits_for_inflight_mutation_result_before_closing_recording(tmp_path):
    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    entered, release = Event(), Event()

    def hold():
        entered.set()
        assert release.wait(2)

    sender.on_send = hold
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            sending = pool.submit(runtime.send_uart, data_b64="eA==")
            assert entered.wait(1)
            closing = pool.submit(runtime.close)
            # Use the recorder state rather than relying on a timed sleep.
            assert recorder.state == "connected"
            release.set()
            assert sending.result(timeout=1).audit_status == "recorded"
            closing.result(timeout=1)
        assert records(tmp_path, recorder.active_session_id)[-1]["type"] == "uart_tx_result"
    finally:
        release.set()
        runtime.close()


def test_disabled_tx_is_rejected_without_mutating_raw_capabilities_or_evidence(tmp_path):
    from dutchmate_core.workflows.uart_send import UartSendError

    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path, tx_enabled=False)
    try:
        with pytest.raises(UartSendError) as failure:
            runtime.send_uart(data_b64="eA==")
        assert failure.value.error == "unsupported_capability"
        assert failure.value.context["disabled_by_policy"] == ["hardware.uart.tx_enabled"]
        assert "uart_send" in runtime.status().backend_capabilities
        assert "uart_send" not in runtime.status().capabilities
        assert records(tmp_path, recorder.active_session_id) == []
        assert sender.calls == []
        with pytest.raises(ValueError):
            runtime.interact(text="x" * 1025, line_ending="none", duration_s=0.01)
        assert records(tmp_path, recorder.active_session_id) == []
    finally:
        runtime.close()


def test_control_failure_is_audited_and_does_not_change_accepted_mapping(tmp_path):
    from dutchmate_core.device_connection.messages import CommandErrorMessage

    runtime, recorder, _, _, _, control = setup_runtime(tmp_path)
    runtime.configure_gpio_mode(
        role="boot",
        channel="CTRL1",
        dut_signal="BOOT0",
        mode="push_pull",
        active_level="high",
        idle_level="low",
    )
    control._responses = [CommandErrorMessage(error="hardware_fault", detail="driver failed")]
    try:
        with pytest.raises(DeviceActionError):
            runtime.set_boot_mode(mode="bootloader")
        event = records(tmp_path, recorder.active_session_id, "hardware")[-1]
        assert event["type"] == "control_result"
        assert event["status"] == "hardware_fault"
        assert runtime.status().commanded_boot_mode is None
        assert runtime.status().control_channels["CTRL1"].state == "configured"
    finally:
        runtime.close()


def test_tx_result_rollover_links_attempt_and_preserves_interact_ranges(tmp_path, monkeypatch):
    runtime, recorder, store, source, sender, _ = setup_runtime(tmp_path)
    predecessor = recorder.active_session_id
    original = store._v2_unit_fits

    def force_rollover(metadata, *, unit_bytes):
        if metadata.get("predecessor_session_id") is None:
            return False
        return original(metadata, unit_bytes=unit_bytes)

    def reply():
        monkeypatch.setattr(store, "_v2_unit_fits", force_rollover)
        source.publish(UartReceiveEvent(0, 1, 0, b"READY\n"))

    sender.on_send = reply
    try:
        result = runtime.interact(
            data_b64="eA==", conditions=(MonitorCondition("READY"),), timeout_s=1
        )
        assert result.outcome == "matched"
        assert len(result.evidence_ranges) == 2
        assert result.tx.attempt_session_id == predecessor
        assert result.tx.result_session_id != predecessor
        event = next(
            r
            for r in records(tmp_path, result.tx.result_session_id)
            if r["type"] == "uart_tx_result"
        )
        assert event["attempt_session_id"] == predecessor
        assert event["attempt_evidence_seq"] == result.tx.attempt_evidence_seq
    finally:
        runtime.close()


def test_tx_attempt_rollover_flushes_partial_continuous_line(tmp_path, monkeypatch):
    runtime, recorder, store, source, _, _ = setup_runtime(tmp_path)
    predecessor = recorder.active_session_id
    tail = recorder.durable_tail()
    source.publish(UartReceiveEvent(0, 1, 0, b"ER"))
    assert recorder.wait_for_durable_tail(tail, timeout_s=1)
    original = store._v2_unit_fits

    def force_rollover(metadata, *, unit_bytes):
        if metadata.get("predecessor_session_id") is None:
            return False
        return original(metadata, unit_bytes=unit_bytes)

    monkeypatch.setattr(store, "_v2_unit_fits", force_rollover)
    try:
        tx = runtime.send_uart(data_b64="eA==")
        assert tx.attempt_session_id != predecessor
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, 2, 0, b"ROR\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert (
            json.loads(
                (tmp_path / recorder.active_session_id / "detected_patterns.json").read_text()
            )
            == []
        )
    finally:
        runtime.close()


def test_unknown_tx_acceptance_can_observe_reconnect_without_resending(tmp_path):
    from test_device_core_monitor import _segment

    from dutchmate_core.backends import BackendDisconnectedError, BackendWriteError

    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)
    sent = Event()

    def interrupted():
        source.publish(BackendDisconnectedError("link lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        sent.set()
        raise BackendWriteError("response lost", error="timeout", bytes_accepted=None)

    sender.on_send = interrupted
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(
                runtime.interact,
                data_b64="eA==",
                conditions=(MonitorCondition("READY"),),
                timeout_s=1,
            )
            assert sent.wait(1)
            snapshot = recorder.capture_source_health().backend_snapshot
            recorder.close_current_source_for_reconnect()
            replacement = ControlledSource(segment_id=1)
            recorder.replace_source(
                replacement, backend_snapshot=replace(snapshot, segment=_segment(1))
            )
            replacement.publish(UartReceiveEvent(1, 1, 0, b"READY\n"))
            result = pending.result(timeout=1)
        assert result.outcome == "matched"
        assert result.tx is None
        assert result.tx_error["context"]["bytes_accepted"] is None
        assert sender.calls == [b"x"]
    finally:
        runtime.close()


@pytest.mark.asyncio
async def test_http_interact_cancellation_persists_terminal_and_releases_exclusivity(tmp_path):
    import asyncio

    import httpx

    from dutchmate_service.app import create_app

    runtime, recorder, _, _, sender, _ = setup_runtime(tmp_path)
    session = recorder.active_session_id
    sent = Event()
    sender.on_send = sent.set
    try:
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=create_app(runtime)), base_url="http://test"
        ) as client:
            request = asyncio.create_task(
                client.post(
                    "/dut/interact",
                    json={
                        "data_b64": "eA==",
                        "duration_s": 2,
                    },
                )
            )
            assert await asyncio.to_thread(sent.wait, 1)
            active = tuple(runtime._active_monitors.values())
            assert len(active) == 1
            request.cancel()
            with pytest.raises(asyncio.CancelledError):
                await request
            assert await asyncio.to_thread(active[0].completed.wait, 1)
        # The runtime action lock also waits for the finally block to release ownership.
        assert (await asyncio.to_thread(runtime.send_uart, data_b64="eA==")).accepted_bytes == 1
        terminals = [r for r in records(tmp_path, session) if r["type"] == "operation_terminal"]
        assert terminals[-1]["outcome"] == "cancelled"
        assert sender.calls == [b"x", b"x"]
    finally:
        runtime.close()


def test_control_result_persistence_failure_preserves_unknown_attempt(tmp_path, monkeypatch):
    runtime, recorder, store, _, _, control = setup_runtime(tmp_path)
    session = recorder.active_session_id

    def fail(*args, **kwargs):
        raise SessionPersistenceError(operation="Control result", path=tmp_path, detail="disk full")

    monkeypatch.setattr(store, "append_v2_control_result", fail)
    try:
        with pytest.raises(DeviceActionError):
            runtime.configure_gpio_mode(
                role="reset",
                channel="CTRL0",
                dut_signal="NRST",
                mode="open_drain",
                active_level="low",
            )
        assert len(control.calls) == 1
        assert recorder.state == "faulted"
    finally:
        runtime.close()
    assert SessionStore(root=tmp_path).get_session_detail(session).unresolved_control_attempts == 1


@pytest.mark.parametrize("mode", ["basic", "enhanced"])
def test_interact_duration_timeout_and_later_ambient_fault_use_one_recorder(tmp_path, mode):
    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path, mode=mode)
    try:
        duration = runtime.interact(data_b64="eA==", duration_s=0.01)
        timeout = runtime.interact(
            data_b64="eA==", conditions=(MonitorCondition("NEVER"),), timeout_s=0.01
        )
        assert duration.outcome == "elapsed"
        assert timeout.outcome == "timeout"
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, 20, 0, b"HardFault\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert (
            tmp_path / recorder.active_session_id / "uart_raw.log"
        ).read_bytes() == b"HardFault\n"
        assert json.loads(
            (tmp_path / recorder.active_session_id / "detected_patterns.json").read_text()
        )
        assert sender.calls == [b"x", b"x"]
        assert source.max_concurrent_reads == 1
        assert not source.closed
    finally:
        runtime.close()


def test_reconnect_terminal_before_tx_result_returns_disconnected_with_unknown_audit(tmp_path):
    from dutchmate_core.backends import BackendDisconnectedError

    runtime, recorder, _, source, sender, _ = setup_runtime(tmp_path)

    def disconnect_before_result():
        source.publish(BackendDisconnectedError("link lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect()
        recorder.reconnect_timed_out()

    sender.on_send = disconnect_before_result
    try:
        result = runtime.interact(data_b64="eA==", duration_s=1)
        assert result.outcome == "disconnected"
        assert result.tx is None
        assert result.tx_error["context"]["outcome"] == "unknown"
        assert sender.calls == [b"x"]
    finally:
        runtime.close()


def test_control_result_after_reconnect_failure_reports_unknown_instead_of_invalid_argument(
    tmp_path,
):
    from dutchmate_core.backends import BackendDisconnectedError

    runtime, recorder, _, source, _, control = setup_runtime(tmp_path)
    runtime.configure_gpio_mode(
        role="reset", channel="CTRL0", dut_signal="NRST", mode="open_drain", active_level="low"
    )

    def disconnect(*args):
        source.publish(BackendDisconnectedError("link lost"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect()
        recorder.reconnect_timed_out()

    control._on_call = disconnect
    try:
        with pytest.raises(DeviceActionError) as error:
            runtime.reset_dut()
        assert error.value.error == "persistence_fault"
        assert error.value.context["outcome"] == "unknown"
        assert len(control.calls) == 2
    finally:
        runtime.close()
