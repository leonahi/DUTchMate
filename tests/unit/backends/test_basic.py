from collections import deque
from pathlib import Path
from threading import Condition

import pytest

from dutchmate_core.backends import (
    BackendCapabilityError,
    BackendDisconnectedError,
    BackendWriteError,
    UartReceiveEvent,
)
from dutchmate_core.backends.basic import (
    BasicBackendEventSource,
    open_basic_backend_connection,
)
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import CaptureWorkflow


class FakeRawSerial:
    def __init__(self) -> None:
        self.read_calls = 0
        self.closed = False

    def read(self, size: int = 1) -> bytes:
        self.read_calls += 1
        return b""

    def write(self, data: bytes) -> int:
        return len(data)

    def close(self) -> None:
        self.closed = True


class ScriptedRawSerial(FakeRawSerial):
    def __init__(self, outcomes: list[bytes | Exception] | None = None) -> None:
        super().__init__()
        self._outcomes = deque(outcomes or [])
        self._condition = Condition()
        self.read_sizes: list[int] = []
        self.write_calls: list[bytes] = []
        self.write_outcomes: deque[int | Exception] = deque()

    def add_read(self, outcome: bytes | Exception) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read(self, size: int = 1) -> bytes:
        with self._condition:
            self.read_calls += 1
            self.read_sizes.append(size)
            while not self._outcomes and not self.closed:
                self._condition.wait(timeout=0.1)
            if self.closed:
                raise OSError("serial closed")
            outcome = self._outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def write(self, data: bytes) -> int:
        self.write_calls.append(data)
        if not self.write_outcomes:
            return len(data)
        outcome = self.write_outcomes.popleft()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def close(self) -> None:
        with self._condition:
            self.closed = True
            self._condition.notify_all()


def _settings(*, tx_enabled: bool = False) -> BackendSettings:
    return BackendSettings(
        mode="basic",
        serial_port="/dev/ttyUSB0",
        reconnect_timeout_s=5.0,
        baudrate=230400,
        data_bits=8,
        parity="none",
        stop_bits=1,
        tx_enabled=tx_enabled,
    )


def test_open_basic_connection_uses_raw_8n1_without_reading_hello() -> None:
    serial = FakeRawSerial()
    calls: list[dict[str, object]] = []

    def factory(**kwargs: object) -> FakeRawSerial:
        calls.append(kwargs)
        return serial

    connection = open_basic_backend_connection(_settings(), serial_factory=factory)

    assert calls == [
        {
            "port": "/dev/ttyUSB0",
            "baudrate": 230400,
            "bytesize": 8,
            "parity": "N",
            "stopbits": 1,
            "timeout": 1.0,
            "write_timeout": 1.0,
            "xonxoff": False,
            "rtscts": False,
            "dsrdtr": False,
        }
    ]
    assert serial.read_calls == 0
    assert connection.info.mode == "basic"
    assert connection.info.device is None
    assert connection.info.firmware is None
    assert connection.info.capabilities == frozenset({"uart_receive", "uart_send"})
    assert connection.capabilities == frozenset({"uart_receive"})
    assert connection.capability_policy.uart_send.tx_policy_enabled is False


def test_basic_tx_capability_follows_explicit_policy() -> None:
    connection = open_basic_backend_connection(
        _settings(tx_enabled=True),
        serial_factory=lambda **_kwargs: FakeRawSerial(),
    )

    assert connection.info.capabilities == frozenset({"uart_receive", "uart_send"})
    assert connection.capabilities == frozenset({"uart_receive", "uart_send"})


def test_basic_connection_closes_owned_serial_port() -> None:
    serial = FakeRawSerial()
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )

    connection.close()

    assert serial.closed is True


async def test_basic_source_normalizes_raw_chunks_with_host_provenance() -> None:
    serial = ScriptedRawSerial([b"boot \xff", b"ready\n"])
    clock_values = iter([5_000_000_000, 5_000_250_000, 5_001_000_000])
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )
    source = BasicBackendEventSource(
        connection,
        segment_id=3,
        monotonic_ns=lambda: next(clock_values),
        read_size=512,
    )

    first = await source.receive_event(timeout_s=0.5)
    second = await source.receive_event(timeout_s=0.5)

    assert first == UartReceiveEvent(
        segment_id=3,
        timestamp_us=250,
        channel=0,
        data=b"boot \xff",
    )
    assert second == UartReceiveEvent(
        segment_id=3,
        timestamp_us=1_000,
        channel=0,
        data=b"ready\n",
    )
    assert serial.read_sizes[:2] == [512, 512]
    assert source.info == connection.info
    assert source.segment_id == 3
    assert source.segment.timestamp.source == "host"
    assert source.segment.timestamp.clock == "monotonic"
    assert source.segment.timestamp.source_origin_us == 5_000_000
    assert source.segment.timestamp.observation_point == "host_serial_read"
    assert source.segment.timestamp.event_granularity == "serial_read_chunk"
    source.close()


async def test_basic_source_timeout_does_not_end_fifo_ingestion() -> None:
    serial = ScriptedRawSerial()
    clock_values = iter([10_000_000, 10_500_000])
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )
    source = BasicBackendEventSource(
        connection,
        segment_id=0,
        monotonic_ns=lambda: next(clock_values),
    )

    assert await source.receive_event(timeout_s=0.01) is None

    serial.add_read(b"later")
    assert await source.receive_event(timeout_s=0.5) == UartReceiveEvent(
        segment_id=0,
        timestamp_us=500,
        channel=0,
        data=b"later",
    )
    source.close()


async def test_basic_source_drains_queued_data_before_disconnect() -> None:
    serial = ScriptedRawSerial([b"last bytes", OSError("adapter removed")])
    clock_values = iter([1_000_000, 1_250_000])
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )
    source = BasicBackendEventSource(
        connection,
        segment_id=1,
        monotonic_ns=lambda: next(clock_values),
    )

    assert await source.receive_event(timeout_s=0.5) == UartReceiveEvent(
        segment_id=1,
        timestamp_us=250,
        channel=0,
        data=b"last bytes",
    )
    with pytest.raises(BackendDisconnectedError, match="Basic serial read failed"):
        await source.receive_event(timeout_s=0.5)
    with pytest.raises(BackendDisconnectedError, match="Basic serial read failed"):
        await source.receive_event(timeout_s=0.5)
    source.close()


def test_basic_source_records_raw_bytes_through_shared_capture_pipeline(tmp_path: Path) -> None:
    serial = ScriptedRawSerial([b"BOOT_OK\n"])
    source_clock = iter([20_000_000, 20_750_000])
    workflow_clock = iter([0.0, 0.0, 0.0, 2.0])
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )
    source = BasicBackendEventSource(
        connection,
        segment_id=0,
        monotonic_ns=lambda: next(source_clock),
    )
    store = SessionStore(root=tmp_path)

    summary = CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=1.0,
        command="capture --seconds 1",
        monotonic_clock=lambda: next(workflow_clock),
    )

    assert (store.root / summary.session_id / "uart_raw.log").read_bytes() == b"BOOT_OK\n"
    assert summary.device is None
    assert summary.firmware is None
    assert summary.backend_mode == "basic"
    assert summary.port == "/dev/ttyUSB0"
    assert summary.backend_capabilities == ("uart_receive", "uart_send")
    assert summary.capabilities == ("uart_receive",)
    assert summary.capability_policy is not None
    assert summary.capability_policy.uart_send.tx_policy_enabled is False
    assert summary.integrity is not None
    assert summary.integrity.loss_status == "not_observable"
    assert summary.integrity.observation_scope is None
    assert summary.integrity.dropped_bytes is None
    assert summary.segment_contexts[0].timestamp.observation_point == "host_serial_read"
    source.close()


def test_basic_send_rejects_disabled_tx_without_writing() -> None:
    serial = ScriptedRawSerial()
    connection = open_basic_backend_connection(
        _settings(),
        serial_factory=lambda **_kwargs: serial,
    )

    with pytest.raises(BackendCapabilityError, match="UART send is disabled"):
        connection.send_uart(b"reboot\n")

    assert serial.write_calls == []


def test_basic_send_retries_short_writes_in_order() -> None:
    serial = ScriptedRawSerial()
    serial.write_outcomes.extend([2, 1, 3])
    connection = open_basic_backend_connection(
        _settings(tx_enabled=True),
        serial_factory=lambda **_kwargs: serial,
    )

    accepted = connection.send_uart(b"reboot")

    assert accepted == 6
    assert serial.write_calls == [b"reboot", b"boot", b"oot"]


def test_basic_send_reports_partial_acceptance_on_failure() -> None:
    serial = ScriptedRawSerial()
    serial.write_outcomes.extend([2, OSError("write timeout")])
    connection = open_basic_backend_connection(
        _settings(tx_enabled=True),
        serial_factory=lambda **_kwargs: serial,
    )

    with pytest.raises(BackendWriteError, match="write failed") as exc_info:
        connection.send_uart(b"reboot")

    assert exc_info.value.bytes_accepted == 2
    assert serial.write_calls == [b"reboot", b"boot"]


@pytest.mark.parametrize("invalid_progress", [0, -1, 7, True])
def test_basic_send_rejects_invalid_serial_write_progress(
    invalid_progress: int,
) -> None:
    serial = ScriptedRawSerial()
    serial.write_outcomes.append(invalid_progress)
    connection = open_basic_backend_connection(
        _settings(tx_enabled=True),
        serial_factory=lambda **_kwargs: serial,
    )

    with pytest.raises(BackendWriteError, match="invalid progress") as exc_info:
        connection.send_uart(b"reboot")

    assert exc_info.value.bytes_accepted == 0
