"""Test-owned physical surrogate behind the real Device Core/service/MCP stack."""

import json
from collections import deque
from threading import Condition, Event

import httpx

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendInfo,
    BackendSnapshot,
    BackendUartSendResult,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.evidence import ContinuousEvidenceRecorder
from dutchmate_core.gpio_config.config import HardwareControlMapping, HardwareGpioConfig
from dutchmate_core.profile import DutProfileConfig, UartProfileConfig, resolve_dut_profile
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import ReconnectedCaptureSource
from dutchmate_mcp_server.server import create_server
from dutchmate_mcp_server.service_client import DeviceCoreClient
from dutchmate_service.app import create_app
from dutchmate_service.backend_reconnect import BackendReconnectCoordinator


class ControlledSource:
    """Condition-driven normalized receive port, following existing runtime test fakes."""

    def __init__(self, segment):
        self.segment = segment
        self.condition = Condition()
        self.events = deque()
        self.closed = False
        self.max_concurrent_reads = 0
        self.active_reads = 0

    def publish(self, event):
        with self.condition:
            self.events.append(event)
            self.condition.notify_all()

    def read_event(self):
        with self.condition:
            self.active_reads += 1
            self.max_concurrent_reads = max(self.active_reads, self.max_concurrent_reads)
            try:
                self.condition.wait_for(lambda: self.events or self.closed)
                if not self.events:
                    raise BackendDisconnectedError("test source closed")
                event = self.events.popleft()
            finally:
                self.active_reads -= 1
        if isinstance(event, BaseException):
            raise event
        return event

    def close(self):
        with self.condition:
            self.closed = True
            self.condition.notify_all()


class FakePhysicalBackend:
    """Only physical RX/TX/control is replaced; runtime, ownership and storage are real."""

    def __init__(self):
        self.tx = []
        self.controls = []
        self.sent = Event()
        self.on_send = lambda: None
        self.write_failure = None
        self.control_failure = None

    def send_uart(self, data):
        self.tx.append(data)
        self.sent.set()
        self.on_send()
        if self.write_failure is not None:
            raise self.write_failure
        return BackendUartSendResult(bytes_accepted=len(data), device_timestamp_us=100)

    def configure_gpio_mode(self, **kwargs):
        self.controls.append(("configure_gpio_mode", kwargs))
        return len(self.controls)

    def pulse_control(self, **kwargs):
        self.controls.append(("pulse_control", kwargs))
        if self.control_failure is not None:
            raise self.control_failure
        return len(self.controls)

    def set_control_state(self, **kwargs):
        self.controls.append(("set_control_state", kwargs))
        return len(self.controls)


class ObservedASGITransport(httpx.ASGITransport):
    """Observe actual requests/responses without replacing routes, serializers or errors."""

    def __init__(self, app):
        super().__init__(app=app)
        self.requests = []
        self.responses = []

    async def handle_async_request(self, request):
        self.requests.append(request)
        response = await super().handle_async_request(request)
        await response.aread()
        self.responses.append((request, response.status_code, response.json()))
        return response


class ServiceFixture:
    def __init__(self, root, *, tx_enabled=True, configured=True, gpio_capable=True):
        controls = {}
        if configured and gpio_capable:
            controls = {
                "reset": HardwareControlMapping("reset", "CTRL0", "NRST", "open_drain", "low"),
                "boot": HardwareControlMapping(
                    "boot", "CTRL1", "BOOT0", "push_pull", "high", "low"
                ),
            }
        self.profile = resolve_dut_profile(
            DutProfileConfig(
                name="mcp-asgi",
                mode="enhanced",
                serial_port="test-only",
                uart=UartProfileConfig(tx_enabled=tx_enabled, default_line_ending="crlf"),
                hardware=HardwareGpioConfig(dut_io_voltage=3.3, controls=controls),
            )
        )
        segment = SegmentContext(
            0,
            SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=1000,
                observation_point="debug_helper_uart_rx",
                event_granularity="firmware_uart_event",
            ),
        )
        capabilities = {"uart_receive", "uart_send", "device_timestamp", "overflow_telemetry"}
        if gpio_capable:
            capabilities.add("gpio_control")
        info = BackendInfo(
            "enhanced", "test-only", "test-helper", "fixture", frozenset(capabilities)
        )
        snapshot = BackendSnapshot(
            info=info,
            capabilities=info.capabilities if tx_enabled else info.capabilities - {"uart_send"},
            capability_policy=BackendCapabilityPolicy(UartSendCapabilityPolicy(tx_enabled)),
            segment=segment,
            integrity=UartIntegrity("none_reported", "debug_helper_rx_buffer", 0),
        )
        self.source = ControlledSource(segment)
        self.sources = [self.source]
        self.physical = FakePhysicalBackend()
        self.store = SessionStore(root=root)
        self.recorder = ContinuousEvidenceRecorder(
            source=self.source,
            session_store=self.store,
            profile=self.profile,
            backend_snapshot=snapshot,
        )

        def reopen(**kwargs):
            self.source = ControlledSource(segment)
            self.sources.append(self.source)
            return ReconnectedCaptureSource(source=self.source, backend_snapshot=snapshot)

        self.owner = BackendReconnectCoordinator(
            source_owner=self.recorder, open_replacement=reopen
        )
        self.runtime = DeviceCoreRuntime(
            device_control=self.physical,
            uart_sender=self.physical,
            session_store=self.store,
            profile=self.profile,
            evidence_recorder=self.recorder,
            connection_owner=self.owner,
            backend_reconnect=self.owner,
        )
        self.runtime.record_backend_connection(info)
        if controls:
            self.runtime.apply_hardware_config(self.profile.hardware_gpio_config)
        self.app = create_app(self.runtime)
        self.transport = ObservedASGITransport(self.app)
        self.server = create_server(
            client_factory=lambda: DeviceCoreClient(
                "http://service-test",
                transport=self.transport,
            )
        )

    @property
    def session(self):
        return self.recorder.active_session_id

    def publish(self, data, timestamp=20):
        previous = self.recorder.durable_tail()
        self.source.publish(UartReceiveEvent(0, timestamp, 0, data))
        assert self.recorder.wait_for_durable_tail(previous, timeout_s=2)

    def records(self, stream="operation", session=None):
        path = self.store.root / (session or self.session) / f"{stream}_events.jsonl"
        return [json.loads(line) for line in path.read_text().splitlines()]

    def close(self):
        self.runtime.close()
