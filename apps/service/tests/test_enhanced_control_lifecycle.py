"""Profile controls must be acknowledged again for each physical helper epoch."""

import json
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest
from fastapi.testclient import TestClient
from test_startup_config import FakeEnhancedAsyncHost, _enhanced_info, _enhanced_segment

from dutchmate_core.backends import BackendDisconnectedError, DeviceControlError, UartReceiveEvent
from dutchmate_core.gpio_config import modes
from dutchmate_core.profile import resolve_dut_profile
from dutchmate_core.profile.config import parse_dut_profile_config
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_service import startup
from dutchmate_service.app import create_app

EXPECTED_MODES = [
    ("CTRL1", "push_pull", "high", "low"),
    ("CTRL0", "open_drain", "low", None),
]


class EpochHost(FakeEnhancedAsyncHost):
    """Model firmware losing its channel modes when physical ownership closes."""

    def __init__(self, generation):
        super().__init__(
            info=_enhanced_info(), segment_id=0, segment=_enhanced_segment(segment_id=0)
        )
        self.generation = generation
        self.configured = set()
        self.configure_entered = Event()
        self.allow_configuration = Event()
        self.allow_configuration.set()
        self.reject_channel = None
        self.configuration_error = "invalid_argument"
        self.configuration_uart = None
        self.after_configuration = None
        self.uart_sent = Event()
        self.close_calls = 0

    def configure_gpio_mode(self, **kwargs):
        super().configure_gpio_mode(**kwargs)
        self.configure_entered.set()
        assert self.allow_configuration.wait(3), "test did not release configuration barrier"
        if kwargs["channel"] == self.reject_channel:
            raise DeviceControlError(error=self.configuration_error, detail="helper refused mode")
        self.configured.add(kwargs["channel"])
        if self.configuration_uart is not None:
            self.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=len(self.configuration_requests),
                    channel=0,
                    data=self.configuration_uart,
                )
            )
        if self.after_configuration is not None:
            self.after_configuration()
        return self.generation * 1000 + len(self.configuration_requests)

    def pulse_control(self, *, channel, pulse_ms):
        if channel not in self.configured:
            raise DeviceControlError(error="not_configured", detail=f"{channel} is not configured")
        return super().pulse_control(channel=channel, pulse_ms=pulse_ms)

    def set_control_state(self, *, channel, state):
        if channel not in self.configured:
            raise DeviceControlError(error="not_configured", detail=f"{channel} is not configured")
        return super().set_control_state(channel=channel, state=state)

    def close(self):
        self.close_calls += 1
        self.configured.clear()
        super().close()

    def send_uart(self, data):
        result = super().send_uart(data)
        self.uart_sent.set()
        return result


@pytest.fixture
def enhanced(tmp_path, monkeypatch, request):
    hosts = []
    candidate_options = {}
    ticks = iter(range(100))
    monkeypatch.setattr(
        modes,
        "_utc_now",
        lambda: datetime(2026, 10, 27, tzinfo=timezone.utc) + timedelta(seconds=next(ticks)),
    )

    def open_host(**kwargs):
        host = EpochHost(len(hosts) + 1)
        if hosts:
            for name, value in candidate_options.items():
                setattr(host, name, value)
        hosts.append(host)
        return host

    monkeypatch.setattr(startup, "open_enhanced_async_host", open_host)
    profile = resolve_dut_profile(
        parse_dut_profile_config(
            {
                "backend": {"mode": "enhanced", "serial_port": "/dev/ttyACM0"},
                "hardware": {
                    "dut_io_voltage": 3.3,
                    "uart": {"tx_enabled": True},
                    "control": {
                        "reset": {
                            "channel": "CTRL0",
                            "dut_signal": "RUN",
                            "mode": "open_drain",
                            "active_level": "low",
                        },
                        "boot": {
                            "channel": "CTRL1",
                            "dut_signal": "GP2",
                            "mode": "push_pull",
                            "active_level": "high",
                            "idle_level": "low",
                        },
                        **getattr(request, "param", {}),
                    },
                },
            }
        )
    )
    runtime = startup.build_startup_runtime(session_root=tmp_path, profile=profile)
    client = TestClient(create_app(runtime=runtime, profile=profile))
    try:
        yield runtime, client, hosts, candidate_options
    finally:
        for host in hosts:
            host.allow_configuration.set()
        client.close()
        if not runtime._closed:
            if any(host._close_error is not None for host in hosts):
                with pytest.raises(RuntimeError, match="candidate close failed"):
                    runtime.close()
            else:
                runtime.close()


def records(runtime, artifact):
    session = runtime._evidence_recorder.active_session_id
    return [
        json.loads(line)
        for line in (runtime.session_store.root / session / artifact).read_text().splitlines()
    ]


def wait_connected(runtime):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        status = runtime.status()
        if status.connected and status.timestamp_provenance.segment_id == 1:
            return
        if status.connection_state == "faulted":
            pytest.fail(f"replacement faulted: {status.connection_error}")
        time.sleep(0.001)
    pytest.fail("replacement did not become connected")


def configuration_results(runtime, segment_id):
    hardware = records(runtime, "hardware_events.jsonl")
    attempts = {
        r["attempt_id"]
        for r in hardware
        if r["type"] == "control_attempt"
        and r["segment_id"] == segment_id
        and r["parameters"]["action"] == "configure_gpio_mode"
    }
    return [r for r in hardware if r["type"] == "control_result" and r["attempt_id"] in attempts]


def test_reacquire_restores_profile_controls_before_immediate_reset(enhanced):
    runtime, client, hosts, _ = enhanced
    assert client.post("/dut/reset", json={"pulse_ms": 100}).status_code == 200
    assert client.post("/connection/release").status_code == 200
    assert hosts[0].closed and not hosts[0].configured
    assert client.post("/connection/reacquire").status_code == 200
    result = client.post("/dut/reset", json={"pulse_ms": 100})
    assert result.status_code == 200, result.json()
    assert client.post("/dut/boot-mode", json={"mode": "bootloader"}).status_code == 200
    assert hosts[1].configuration_requests == EXPECTED_MODES == hosts[0].configuration_requests
    controls = client.get("/status").json()["control_channels"]
    assert controls["CTRL1"]["device_timestamp_us"] == 2001
    assert controls["CTRL0"]["device_timestamp_us"] == 2002
    assert controls["CTRL0"]["configured_at"] == "2026-10-27T00:00:03Z"
    connections = records(runtime, "connection_events.jsonl")
    success = next(r["evidence_seq"] for r in connections if r["type"] == "reacquire_succeeded")
    new_config = configuration_results(runtime, 1)
    assert new_config  # Config acknowledgements must precede lifecycle success, not follow it.
    assert max(r["evidence_seq"] for r in new_config[:2]) < success


def test_status_hides_previous_acceptance_while_new_configuration_is_pending(enhanced):
    runtime, client, hosts, options = enhanced
    previous = client.get("/status").json()["control_channels"]
    assert previous["CTRL0"]["state"] == "configured"
    assert client.post("/connection/release").status_code == 200
    released = client.get("/status").json()["control_channels"]
    assert all(
        s["state"] == "unconfigured" and s["configured_at"] is None for s in released.values()
    )
    barrier = Event()
    options["allow_configuration"] = barrier
    with ThreadPoolExecutor() as executor:
        future = executor.submit(client.post, "/connection/reacquire")
        try:
            deadline = time.monotonic() + 1
            while len(hosts) < 2 and time.monotonic() < deadline:
                time.sleep(0.001)
            assert len(hosts) == 2 and hosts[1].configure_entered.wait(1)
            status = client.get("/status").json()
            assert status["connection_state"] == "reacquiring"
            assert all(
                s["state"] == "unconfigured" and s["device_timestamp_us"] is None
                for s in status["control_channels"].values()
            )
            assert not future.done()
        finally:
            barrier.set()
        assert future.result().status_code == 200


def test_ordinary_actions_do_not_reapply_same_generation_configuration(enhanced):
    _, client, hosts, _ = enhanced
    for _ in range(2):
        assert client.post("/dut/reset", json={"pulse_ms": 10}).status_code == 200
        assert client.post("/dut/boot-mode", json={"mode": "normal"}).status_code == 200
    assert hosts[0].configuration_requests == EXPECTED_MODES


def test_new_epoch_uses_immutable_profile_rather_than_previous_runtime_override(enhanced):
    _, client, hosts, _ = enhanced
    result = client.post(
        "/gpio/mode",
        json={
            "channel": "CTRL2",
            "role": "reset",
            "dut_signal": "ALTERNATE_RUN",
            "mode": "open_drain",
            "active_level": "low",
        },
    )
    assert result.status_code == 200
    assert client.get("/status").json()["control_channels"]["CTRL2"]["state"] == "configured"
    assert client.post("/connection/release").status_code == 200
    assert client.post("/connection/reacquire").status_code == 200
    status = client.get("/status").json()
    assert status["control_channels"]["CTRL0"]["state"] == "configured"
    assert status["control_channels"]["CTRL0"]["dut_signal"] == "RUN"
    assert status["control_channels"]["CTRL2"]["state"] == "unconfigured"
    assert hosts[1].configuration_requests == EXPECTED_MODES


@pytest.mark.parametrize(
    "enhanced",
    [
        {
            "wake": {
                "channel": "CTRL2",
                "dut_signal": "WAKE",
                "mode": "open_drain",
                "active_level": "low",
            },
            "power_enable": {
                "channel": "CTRL3",
                "dut_signal": "POWER_N",
                "mode": "push_pull",
                "active_level": "low",
                "idle_level": "high",
            },
        }
    ],
    indirect=True,
)
def test_profile_drives_all_four_channels_without_hardcoded_reset_boot_defaults(enhanced):
    _, client, hosts, _ = enhanced
    expected = [
        ("CTRL1", "push_pull", "high", "low"),
        ("CTRL3", "push_pull", "low", "high"),
        ("CTRL0", "open_drain", "low", None),
        ("CTRL2", "open_drain", "low", None),
    ]
    assert hosts[0].configuration_requests == expected
    assert client.post("/connection/release").status_code == 200
    assert client.post("/connection/reacquire").status_code == 200
    assert hosts[1].configuration_requests == expected
    assert all(
        state["state"] == "configured"
        for state in client.get("/status").json()["control_channels"].values()
    )


@pytest.mark.parametrize("error", ["invalid_argument", "timeout"])
def test_reacquire_configuration_failure_does_not_publish_success(enhanced, error):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    options.update(reject_channel="CTRL0", configuration_error=error)
    result = client.post("/connection/reacquire")
    assert result.status_code != 200
    assert result.json()["error"] == error
    assert hosts[1].closed
    status = client.get("/status").json()
    assert not status["connected"]
    assert all(s["state"] != "configured" for s in status["control_channels"].values())
    assert not any(
        r["type"] == "reacquire_succeeded" for r in records(runtime, "connection_events.jsonl")
    )
    assert any(
        r["type"] == "control_result" and r["status"] == error
        for r in records(runtime, "hardware_events.jsonl")
    )


def test_reacquire_initialization_close_failure_retains_cleanup_uncertainty(enhanced):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    options.update(reject_channel="CTRL0", _close_error=RuntimeError("candidate close failed"))
    result = client.post("/connection/reacquire")
    assert result.status_code != 200
    status = client.get("/status").json()
    assert status["connection_state"] == "faulted"
    assert status["connection_error"]["context"]["reason"] == "cleanup_unconfirmed"
    assert hosts[1].close_calls == 1
    assert all(s["state"] != "configured" for s in status["control_channels"].values())
    with pytest.raises(RuntimeError, match="candidate close failed"):
        runtime.close()
    assert hosts[1].close_calls == 1


@pytest.mark.parametrize(
    ("helper_error", "reported_error"),
    [("invalid_argument", "invalid_argument"), ("unexpected_response", "backend_input_error")],
)
def test_partial_profile_initialization_rolls_back_boot_mode(
    enhanced, helper_error, reported_error
):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    options.update(reject_channel="CTRL0", configuration_error=helper_error)
    result = client.post("/connection/reacquire")
    assert result.status_code != 200
    assert result.json()["error"] == reported_error
    assert result.json()["detail"] == "helper refused mode"
    assert hosts[1].configuration_requests == EXPECTED_MODES
    configs = configuration_results(runtime, 1)
    assert [r["status"] for r in configs] == ["success", reported_error]
    assert runtime._evidence_recorder._fault.error == reported_error
    assert all(s.state == "unconfigured" for s in runtime.gpio_registry.snapshot().values())
    assert runtime._commanded_boot_mode is None
    status = client.get("/status").json()
    assert status["commanded_boot_mode"] is None
    assert not any(
        r["type"] == "reacquire_succeeded" for r in records(runtime, "connection_events.jsonl")
    )
    assert hosts[1].close_calls == 1


def test_deadline_after_final_profile_ack_rolls_back_control_acceptance(enhanced):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    clock = [0.0]
    runtime._connection_owner._clock = lambda: clock[0]

    def expire_after_last_ack():
        if len(hosts[1].configuration_requests) == 2:
            clock[0] = 6.0

    options["after_configuration"] = expire_after_last_ack
    result = client.post("/connection/reacquire")
    assert result.status_code == 503
    assert result.json()["context"]["reason"] == "open_timeout"
    assert hosts[1].configuration_requests == EXPECTED_MODES
    assert [r["status"] for r in configuration_results(runtime, 1)] == ["success", "success"]
    assert all(s.state == "unconfigured" for s in runtime.gpio_registry.snapshot().values())
    assert runtime._commanded_boot_mode is None
    assert not any(
        r["type"] == "reacquire_succeeded" for r in records(runtime, "connection_events.jsonl")
    )
    assert hosts[1].close_calls == 1


@pytest.mark.parametrize("automatic", [False, True], ids=["reacquire", "reconnect"])
@pytest.mark.parametrize("cleanup_fails", [False, True], ids=["closed", "cleanup-unconfirmed"])
def test_recorder_publication_failure_closes_candidate_exactly_once(
    enhanced, monkeypatch, automatic, cleanup_fails
):
    runtime, client, hosts, options = enhanced
    recorder = runtime._evidence_recorder
    owner = runtime._connection_owner
    primary = SessionPersistenceError(
        operation="append_segment", path=runtime.session_store.root, detail="segment disk failure"
    )
    if not automatic:
        assert client.post("/connection/release").status_code == 200
    if cleanup_fails:
        options["_close_error"] = RuntimeError("candidate close failed")

    def fail_publication(*args, **kwargs):
        raise primary

    monkeypatch.setattr(runtime.session_store, "append_v2_segment", fail_publication)
    if automatic:
        publication_errors = []
        publish = owner._publish

        def observe_publication(*args, **kwargs):
            try:
                return publish(*args, **kwargs)
            except BaseException as exc:
                publication_errors.append(exc)
                raise

        monkeypatch.setattr(owner, "_publish", observe_publication)
        hosts[0].publish(BackendDisconnectedError("lost USB"))
        assert recorder.wait_for_fault(timeout_s=2)
        owner._worker.join(timeout=1)
        assert not owner._worker.is_alive()
        assert publication_errors == [primary]
    else:
        with pytest.raises(SessionPersistenceError) as raised:
            runtime.reacquire_connection()
        assert raised.value is primary
    assert recorder._fault is primary
    assert len(hosts) == 2
    assert hosts[1].close_calls == 1
    assert recorder._source is None
    status = client.get("/status").json()
    assert status["connection_state"] == "faulted" and not status["connected"]
    if cleanup_fails:
        assert status["connection_error"]["context"]["reason"] == "cleanup_unconfirmed"
    else:
        assert status["connection_error"]["error"] == "persistence_fault"
    assert not any(
        r["type"] in {"reacquire_succeeded", "reconnect_succeeded"}
        for r in records(runtime, "connection_events.jsonl")
    )
    assert client.post("/connection/reacquire").status_code != 200
    assert len(hosts) == 2
    if cleanup_fails:
        with pytest.raises(RuntimeError, match="candidate close failed"):
            runtime.close()
    else:
        runtime.close()
    assert hosts[1].close_calls == 1


def test_automatic_reconnect_reapplies_profile_before_immediate_control(enhanced):
    runtime, client, hosts, _ = enhanced
    hosts[0].publish(BackendDisconnectedError("lost USB"))
    wait_connected(runtime)
    result = client.post("/dut/reset", json={"pulse_ms": 10})
    assert result.status_code == 200, result.json()
    assert hosts[1].configuration_requests == EXPECTED_MODES
    assert client.post("/dut/boot-mode", json={"mode": "normal"}).status_code == 200
    configs = configuration_results(runtime, 1)
    success = next(
        r["evidence_seq"]
        for r in records(runtime, "connection_events.jsonl")
        if r["type"] == "reconnect_succeeded"
    )
    assert len(configs) >= 2 and max(r["evidence_seq"] for r in configs[:2]) < success


def test_automatic_reconnect_configuration_rejection_is_not_a_success(enhanced):
    runtime, client, hosts, options = enhanced
    options["reject_channel"] = "CTRL0"
    hosts[0].publish(BackendDisconnectedError("lost USB"))
    assert runtime._evidence_recorder.wait_for_fault(timeout_s=2)
    runtime._backend_reconnect._worker.join(timeout=1)
    assert not runtime._backend_reconnect._worker.is_alive()
    status = client.get("/status").json()
    assert status["connection_error"]["error"] == "invalid_argument"
    assert hosts[1].closed
    assert not any(
        r["type"] == "reconnect_succeeded" for r in records(runtime, "connection_events.jsonl")
    )


def test_reconnect_does_not_accept_a_late_previous_epoch_configuration(enhanced, monkeypatch):
    runtime, client, hosts, _ = enhanced
    initializing = Event()
    initialized = Event()
    recorder = runtime._evidence_recorder
    original = recorder._connection_initializer

    def initialize(snapshot, check_ready):
        initializing.set()
        original(snapshot, check_ready)
        initialized.set()

    recorder.set_connection_initializer(initialize)
    old = hosts[0]
    acknowledged = Event()
    accept_old = Event()
    original_accept = runtime.gpio_registry.accept_mode

    def accept_mode(**kwargs):
        if kwargs["role"] == "wake":
            acknowledged.set()
            assert accept_old.wait(3)
        return original_accept(**kwargs)

    monkeypatch.setattr(runtime.gpio_registry, "accept_mode", accept_mode)
    with ThreadPoolExecutor() as executor:
        action = executor.submit(
            client.post,
            "/gpio/mode",
            json={
                "channel": "CTRL2",
                "role": "wake",
                "dut_signal": "WAKE",
                "mode": "push_pull",
                "active_level": "high",
                "idle_level": "low",
            },
        )
        try:
            assert acknowledged.wait(1)
            old.publish(BackendDisconnectedError("lost USB after old acknowledgement"))
            assert initializing.wait(1)
            # If initialization overtakes the submitted action, force its old
            # acknowledgement to arrive after the new generation is published.
            if initialized.wait(0.1):
                wait_connected(runtime)
        finally:
            accept_old.set()
        assert action.result().status_code == 200
    wait_connected(runtime)
    status = client.get("/status").json()
    assert status["control_channels"]["CTRL2"]["state"] == "unconfigured"
    assert client.post("/dut/reset", json={"pulse_ms": 10}).status_code == 200


def test_profile_initialization_cannot_extend_the_reacquire_deadline(enhanced):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    clock = [0.0]
    runtime._connection_owner._clock = lambda: clock[0]
    options["after_configuration"] = lambda: clock.__setitem__(0, 6.0)
    result = client.post("/connection/reacquire")
    assert result.status_code == 503
    assert result.json()["error"] == "service_unavailable"
    assert hosts[1].configuration_requests == EXPECTED_MODES[:1]
    assert hosts[1].closed and hosts[1].close_count == 1
    assert not any(
        r["type"] == "reacquire_succeeded" for r in records(runtime, "connection_events.jsonl")
    )


def test_shutdown_during_initialization_cannot_publish_reacquire_success(enhanced, monkeypatch):
    runtime, client, hosts, options = enhanced
    assert client.post("/connection/release").status_code == 200
    barrier = Event()
    options["allow_configuration"] = barrier
    cancelled = Event()
    original = runtime._connection_owner.cancel_pending

    def cancel():
        original()
        cancelled.set()

    monkeypatch.setattr(runtime._connection_owner, "cancel_pending", cancel)
    with ThreadPoolExecutor() as executor:
        acquisition = executor.submit(client.post, "/connection/reacquire")
        deadline = time.monotonic() + 1
        while len(hosts) < 2 and time.monotonic() < deadline:
            time.sleep(0.001)
        assert len(hosts) == 2 and hosts[1].configure_entered.wait(1)
        closing = executor.submit(runtime.close)
        try:
            assert cancelled.wait(1)
        finally:
            barrier.set()
        assert acquisition.result(timeout=2).status_code != 200
        closing.result(timeout=2)
    assert hosts[1].closed and hosts[1].close_count == 1
    assert not any(
        r["type"] == "reacquire_succeeded" for r in records(runtime, "connection_events.jsonl")
    )


def test_uart_buffered_during_profile_initialization_remains_durable(enhanced):
    runtime, client, _, options = enhanced
    assert client.post("/connection/release").status_code == 200
    options["configuration_uart"] = b"EARLY BOOT\n"
    assert client.post("/connection/reacquire").status_code == 200
    session = runtime._evidence_recorder.active_session_id
    raw = runtime.session_store.root / session / "uart_raw.log"
    deadline = time.monotonic() + 1
    while raw.read_bytes() != b"EARLY BOOT\nEARLY BOOT\n" and time.monotonic() < deadline:
        time.sleep(0.001)
    assert raw.read_bytes() == b"EARLY BOOT\nEARLY BOOT\n"
    assert all(r["segment_id"] == 1 for r in records(runtime, "uart_events.jsonl"))


def test_interact_observation_can_resume_after_profile_reinitialization_without_tx_retry(enhanced):
    runtime, client, hosts, _ = enhanced
    with ThreadPoolExecutor() as executor:
        operation = executor.submit(
            client.post,
            "/dut/interact",
            json={
                "text": "PING",
                "line_ending": "lf",
                "conditions": [{"pattern": "READY"}],
                "timeout_s": 1,
            },
        )
        assert hosts[0].uart_sent.wait(1)
        hosts[0].publish(BackendDisconnectedError("lost USB while observing"))
        wait_connected(runtime)
        hosts[1].publish(UartReceiveEvent(0, 1, 0, b"READY\n"))
        result = operation.result(timeout=2)
    assert result.status_code == 200, result.json()
    assert result.json()["outcome"] == "matched", result.json()
    assert hosts[0].uart_requests == [b"PING\n"]
    assert hosts[1].uart_requests == []
    assert hosts[1].configuration_requests == EXPECTED_MODES
