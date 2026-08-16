from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.backends.enhanced import EnhancedCaptureEventSource
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.serial_transport import SerialCommandTransport
from dutchmate_core.gpio_config.config import parse_hardware_gpio_config
from dutchmate_core.gpio_config.modes import GpioConfigurationError
from dutchmate_core.runtime import (
    DeviceCoreRuntime,
    DeviceCoreRuntimeError,
    DeviceCoreStatus,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.device_actions import DeviceActionError, DeviceActionResult


class FakeTransport:
    def __init__(self, responses: list[DeviceMessage] | None = None) -> None:
        self.responses = responses or []
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> DeviceMessage:
        self.requests.append(command)
        if not self.responses:
            raise AssertionError("fake transport has no queued response")
        return self.responses.pop(0)


class FakeSerial:
    def __init__(
        self,
        reads: list[bytes],
        *,
        on_write: Callable[[bytes], None] | None = None,
    ) -> None:
        self.reads = reads
        self.on_write = on_write
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        if self.on_write is not None:
            self.on_write(data)
        return len(data)

    def flush(self) -> None:
        pass

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        if not self.reads:
            return b""
        return self.reads.pop(0)

    def close(self) -> None:
        pass


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class AdvancingMonotonicClock:
    def __init__(self, *, step_s: float = 0.1) -> None:
        self.value = 0.0
        self._step_s = step_s

    def __call__(self) -> float:
        self.value += self._step_s
        return self.value


class FakeCaptureSource:
    def __init__(
        self,
        script: list[BackendEvent | Exception | None],
        *,
        clock: FakeMonotonicClock,
        on_read: Callable[[], None] | None = None,
        read_duration_s: float = 0.1,
    ) -> None:
        self._script = script
        self._clock = clock
        self._on_read = on_read
        self._read_duration_s = read_duration_s
        self.segment = SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        )

    def read_event(self) -> BackendEvent | None:
        if self._on_read is not None:
            on_read = self._on_read
            self._on_read = None
            on_read()
        self._clock.advance(self._read_duration_s)
        if not self._script:
            return None

        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result


def hello() -> HelloMessage:
    return HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control", "uart_send"),
    )


def test_initial_status_is_disconnected_with_unconfigured_gpio(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        session_root=tmp_path,
        port="/dev/ttyACM0",
    )

    status = runtime.status()

    assert status == DeviceCoreStatus(
        connected=False,
        port="/dev/ttyACM0",
        firmware=None,
        device=None,
        capabilities=(),
        active_session_id=None,
        control_channels=status.control_channels,
    )
    assert status.control_channels["CTRL0"].state == "unconfigured"
    assert status.control_channels["CTRL3"].state == "unconfigured"
    assert runtime.session_store.root == tmp_path


def test_record_hello_updates_connection_status(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(transport=FakeTransport(), session_root=tmp_path)

    status = runtime.record_hello(hello(), port="/dev/tty.usbmodem2040")

    assert status.connected is True
    assert status.port == "/dev/tty.usbmodem2040"
    assert status.firmware == "0.1.0"
    assert status.device == "dutchmate-rp2040"
    assert status.backend_mode == "enhanced"
    assert status.backend_capabilities == ("gpio_control", "uart_receive", "uart_send")
    assert status.capabilities == ("gpio_control", "uart_receive")
    assert status.capability_policy is not None
    assert status.capability_policy.uart_send.tx_policy_enabled is False
    assert status.integrity is not None
    assert status.integrity.loss_status == "none_reported"


def test_tx_policy_cannot_manufacture_unreported_backend_capability(
    tmp_path: Path,
) -> None:
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        session_root=tmp_path,
        tx_policy_enabled=True,
    )
    no_send_hello = HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=("uart_capture", "gpio_control"),
    )

    status = runtime.record_hello(no_send_hello, port="/dev/ttyACM0")

    assert status.backend_capabilities == ("gpio_control", "uart_receive")
    assert status.capabilities == ("gpio_control", "uart_receive")
    assert status.capability_policy is not None
    assert status.capability_policy.uart_send.tx_policy_enabled is True


def test_apply_hardware_config_requires_connection(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(transport=FakeTransport(), session_root=tmp_path)
    config = parse_hardware_gpio_config({})

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.apply_hardware_config(config)


def test_apply_hardware_config_sends_configured_modes(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            CommandSuccessMessage(timestamp_us=100),
            CommandSuccessMessage(timestamp_us=200),
        ]
    )
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello())
    config = parse_hardware_gpio_config(
        {
            "hardware": {
                "control": {
                    "reset": {
                        "channel": "CTRL0",
                        "dut_signal": "RESET_N",
                        "mode": "open_drain",
                        "active_level": "low",
                    },
                    "boot": {
                        "channel": "CTRL1",
                        "dut_signal": "BOOT0",
                        "mode": "push_pull",
                        "active_level": "high",
                        "idle_level": "low",
                    },
                }
            }
        }
    )

    states = runtime.apply_hardware_config(config)

    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"configure_gpio_mode","channel":"CTRL1","role":"boot",'
        b'"mode":"push_pull","active_level":"high","idle_level":"low"}\n',
    ]
    assert states["reset"].state == "configured"
    assert states["reset"].channel == "CTRL0"
    assert states["reset"].source == "config"
    assert states["reset"].device_timestamp_us == 100
    assert states["boot"].state == "configured"
    assert states["boot"].channel == "CTRL1"
    assert states["boot"].source == "config"
    assert states["boot"].device_timestamp_us == 200
    assert runtime.status().control_channels["CTRL0"] == states["reset"]


def test_reset_uses_shared_gpio_state_and_transport(tmp_path: Path) -> None:
    transport = FakeTransport(
        [
            CommandSuccessMessage(timestamp_us=100),
            CommandSuccessMessage(timestamp_us=300),
        ]
    )
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello())
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
    )

    result = runtime.reset_dut(pulse_ms=250)

    assert result == DeviceActionResult(action="reset", timestamp_us=300)
    assert transport.requests == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL0","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"reset","pulse_ms":250}\n',
    ]


def test_disconnect_clears_connection_metadata_but_keeps_gpio_state(tmp_path: Path) -> None:
    transport = FakeTransport([CommandSuccessMessage(timestamp_us=100)])
    runtime = DeviceCoreRuntime(transport=transport, session_root=tmp_path)
    runtime.record_hello(hello(), port="/dev/ttyACM0")
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
    )

    status = runtime.disconnect()

    assert status.connected is False
    assert status.port == "/dev/ttyACM0"
    assert status.firmware is None
    assert status.integrity is None
    assert status.control_channels["CTRL0"].state == "configured"


def test_capture_uart_records_transport_messages_and_connection_metadata(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            UartReceiveEvent(
                segment_id=0,
                channel=0,
                timestamp_us=100,
                data=b"BOOT_OK\n",
            ),
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=200,
                size_bytes=32768,
                used_bytes=10,
                high_water_bytes=100,
                dropped_bytes_total=0,
                overflow_events=0,
            ),
        ],
        clock=clock,
    )
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "runtime",
    )
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_hello(hello(), port="/dev/ttyACM0")

    summary = runtime.capture_uart(duration_s=0.4)

    assert summary.command == "capture --seconds 0.4"
    assert summary.firmware == "0.1.0"
    assert summary.device == "dutchmate-rp2040"
    assert summary.backend_mode == "enhanced"
    assert summary.port == "/dev/ttyACM0"
    assert summary.backend_capabilities == (
        "gpio_control",
        "uart_receive",
        "uart_send",
    )
    assert summary.capabilities == ("gpio_control", "uart_receive")
    assert summary.capability_policy is not None
    assert summary.capability_policy.uart_send.tx_policy_enabled is False
    assert summary.integrity is not None
    assert summary.integrity.loss_status == "none_reported"
    assert summary.segment_contexts[0].timestamp.observation_point == (
        "debug_helper_uart_receive"
    )
    assert runtime.status().active_session_id is None
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"BOOT_OK\n"


def test_capture_uart_exposes_active_session_and_rejects_hardware_operations(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    runtime: DeviceCoreRuntime

    def assert_capture_guards() -> None:
        assert runtime.status().active_session_id is not None
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.capture_uart(duration_s=0.1)
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.run_boot_test(duration_s=0.1)
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.reset_dut()
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.set_boot_mode(mode="normal")
        with pytest.raises(DeviceActionError, match="capture is already active"):
            runtime.configure_gpio_mode(
                role="power_en",
                channel="CTRL2",
                dut_signal="POWER_EN",
                mode="push_pull",
                active_level="high",
                idle_level="low",
            )

    source = FakeCaptureSource([], clock=clock, on_read=assert_capture_guards)
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=source,
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())

    runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None


def test_capture_updates_connected_integrity_from_buffer_telemetry(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=200,
                size_bytes=32768,
                used_bytes=32768,
                high_water_bytes=32768,
                dropped_bytes_total=37,
                overflow_events=1,
            )
        ],
        clock=clock,
    )
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=source,
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello(), port="/dev/ttyACM0")

    summary = runtime.capture_uart(duration_s=0.3)

    assert summary.integrity is not None
    assert summary.integrity.loss_status == "loss_reported"
    assert summary.integrity.dropped_bytes == 37
    status = runtime.status()
    assert status.integrity == summary.integrity


def test_capture_uart_requires_connection(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_root=tmp_path,
    )

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.capture_uart(duration_s=0.1)


def test_capture_uart_requires_message_source(tmp_path: Path) -> None:
    runtime = DeviceCoreRuntime(transport=FakeTransport(), session_root=tmp_path)
    runtime.record_hello(hello())

    with pytest.raises(DeviceCoreRuntimeError, match="message source"):
        runtime.capture_uart(duration_s=0.1)


def test_capture_uart_clears_active_session_after_transport_failure(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([RuntimeError("serial failed")], clock=clock)
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=source,
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())

    with pytest.raises(RuntimeError, match="serial failed"):
        runtime.capture_uart(duration_s=0.2)

    assert runtime.status().active_session_id is None


@pytest.mark.parametrize("duration_s", [0, 300.1, True])
def test_capture_uart_rejects_invalid_duration_before_creating_session(
    tmp_path: Path,
    duration_s: object,
) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())

    with pytest.raises(ValueError, match="positive finite"):
        runtime.capture_uart(duration_s=duration_s)  # type: ignore[arg-type]

    assert list(tmp_path.iterdir()) == []


def test_run_boot_test_creates_session_before_reset_and_records_queued_uart(
    tmp_path: Path,
) -> None:
    runtime: DeviceCoreRuntime

    def assert_session_reserved_before_reset(command: bytes) -> None:
        if b'"cmd":"reset"' not in command:
            return
        active_session_id = runtime.status().active_session_id
        assert active_session_id is not None
        assert (tmp_path / active_session_id / "metadata.json").is_file()

    serial = FakeSerial(
        [
            b'{"ok":true,"timestamp_us":10}\n',
            b'{"type":"uart","channel":0,"timestamp_us":20,'
            b'"data_b64":"Qk9PVF9PSwo="}\n',
            b'{"ok":true,"timestamp_us":30}\n',
        ],
        on_write=assert_session_reserved_before_reset,
    )
    transport = SerialCommandTransport(serial)
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_session_time,
        id_factory=lambda: "boot-test",
    )
    runtime = DeviceCoreRuntime(
        transport=transport,
        message_source=EnhancedCaptureEventSource(
            transport,
            segment_id=0,
            source_origin_us=0,
        ),
        capture_clock=AdvancingMonotonicClock(),
        session_store=store,
    )
    runtime.record_hello(hello())
    runtime.configure_gpio_mode(
        role="reset",
        channel="CTRL2",
        dut_signal="NRST",
        mode="open_drain",
        active_level="low",
    )

    summary = runtime.run_boot_test(duration_s=0.4)

    assert summary.command == "boot-test --seconds 0.4"
    assert serial.writes == [
        b'{"cmd":"configure_gpio_mode","channel":"CTRL2","role":"reset",'
        b'"mode":"open_drain","active_level":"low"}\n',
        b'{"cmd":"reset","pulse_ms":100}\n',
    ]
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"BOOT_OK\n"
    assert runtime.status().active_session_id is None


def test_run_boot_test_requires_reset_role_before_creating_session(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    transport = FakeTransport()
    runtime = DeviceCoreRuntime(
        transport=transport,
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())

    with pytest.raises(GpioConfigurationError, match="'reset'.*not configured"):
        runtime.run_boot_test(duration_s=0.2)

    assert transport.requests == []
    assert list(tmp_path.iterdir()) == []


def test_run_boot_test_clears_active_session_after_reset_failure(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    transport = FakeTransport(
        [
            CommandErrorMessage(
                error="hardware_fault",
                detail="reset pulse failed",
            )
        ]
    )
    runtime = DeviceCoreRuntime(
        transport=transport,
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())
    runtime.gpio_registry.accept_mode(
        role="reset",
        channel="CTRL0",
        dut_signal="RESET_N",
        mode="open_drain",
        active_level="low",
        source="runtime",
    )

    with pytest.raises(DeviceActionError, match="reset pulse failed"):
        runtime.run_boot_test(duration_s=0.2)

    assert transport.requests == [b'{"cmd":"reset","pulse_ms":100}\n']
    assert runtime.status().active_session_id is None
    assert len(list(tmp_path.iterdir())) == 1


@pytest.mark.parametrize("duration_s", [0, 300.1, True])
def test_run_boot_test_rejects_invalid_duration_before_creating_session(
    tmp_path: Path,
    duration_s: object,
) -> None:
    clock = FakeMonotonicClock()
    runtime = DeviceCoreRuntime(
        transport=FakeTransport(),
        message_source=FakeCaptureSource([], clock=clock),
        capture_clock=clock,
        session_root=tmp_path,
    )
    runtime.record_hello(hello())

    with pytest.raises(ValueError, match="positive finite"):
        runtime.run_boot_test(duration_s=duration_s)  # type: ignore[arg-type]

    assert list(tmp_path.iterdir()) == []


def _fixed_session_time() -> datetime:
    return datetime(2026, 7, 27, 12, 0, tzinfo=timezone.utc)
