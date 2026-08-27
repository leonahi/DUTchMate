import pytest

from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import (
    FrameTooLargeError,
    HostCommandFrameTooLargeError,
)
from dutchmate_core.device_connection.messages import (
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.serial_transport import (
    SerialCommandTransport,
    open_serial_command_transport,
)
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
)


class FakeSerial:
    def __init__(
        self,
        reads: list[bytes] | None = None,
        *,
        write_outcomes: list[int | Exception] | None = None,
        flush_failure: Exception | None = None,
    ) -> None:
        self.reads = reads or []
        self.write_outcomes = write_outcomes or []
        self.flush_failure = flush_failure
        self.writes: list[bytes] = []
        self.flush_count = 0
        self.closed = False
        self.read_sizes: list[int | None] = []

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        if self.write_outcomes:
            outcome = self.write_outcomes.pop(0)
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        return len(data)

    def flush(self) -> None:
        self.flush_count += 1
        if self.flush_failure is not None:
            raise self.flush_failure

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        self.read_sizes.append(size)
        if not self.reads:
            return b""
        return self.reads.pop(0)

    def close(self) -> None:
        self.closed = True


class SerialTimeoutException(Exception):
    """Pyserial-shaped timeout used without importing the serial framework."""


def _compact_json_frame_of_size(size: int) -> bytes:
    baseline = b'{"cmd":"test","data":""}\n'
    return b'{"cmd":"test","data":"' + b"x" * (size - len(baseline)) + b'"}\n'


def test_request_writes_command_and_returns_success_response() -> None:
    serial = FakeSerial([b'{"ok":true,"timestamp_us":123}\n'])
    transport = SerialCommandTransport(serial)

    response = transport.request(
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    )

    assert response == CommandSuccessMessage(timestamp_us=123)
    assert serial.writes == [
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    ]
    assert serial.flush_count == 1


def test_request_retries_ordered_short_writes_before_reading_response() -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(
        [b'{"ok":true}\n'],
        write_outcomes=[2, 3, len(command) - 5],
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(command)

    assert response == CommandSuccessMessage()
    assert serial.writes == [command, command[2:], command[5:]]
    assert serial.flush_count == 1
    assert serial.read_sizes == [65536]


def test_request_reports_partial_frame_acceptance_when_write_fails() -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(write_outcomes=[2, OSError("adapter removed")])
    transport = SerialCommandTransport(serial)

    with pytest.raises(TransportWriteError, match="write failed") as raised:
        transport.request(command)

    assert raised.value.error == "hardware_fault"
    assert raised.value.frame_bytes_accepted == 2
    assert serial.writes == [command, command[2:]]
    assert serial.flush_count == 0
    assert serial.read_sizes == []


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("write timeout"), SerialTimeoutException("write timeout")],
)
def test_request_classifies_write_timeout_with_partial_frame_acceptance(
    failure: Exception,
) -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(write_outcomes=[2, failure])
    transport = SerialCommandTransport(serial)

    with pytest.raises(TransportWriteError) as raised:
        transport.request(command)

    assert raised.value.error == "timeout"
    assert raised.value.frame_bytes_accepted == 2
    assert serial.flush_count == 0
    assert serial.read_sizes == []


def test_request_reports_complete_frame_acceptance_when_flush_fails() -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(
        [b'{"ok":true}\n'],
        flush_failure=OSError("adapter removed"),
    )
    transport = SerialCommandTransport(serial)

    with pytest.raises(TransportWriteError, match="flush failed") as raised:
        transport.request(command)

    assert raised.value.error == "hardware_fault"
    assert raised.value.frame_bytes_accepted == len(command)
    assert serial.writes == [command]
    assert serial.flush_count == 1
    assert serial.read_sizes == []


@pytest.mark.parametrize(
    ("invalid_progress", "expected_error"),
    [
        (0, "timeout"),
        (-1, "hardware_fault"),
        (4096, "hardware_fault"),
        (True, "hardware_fault"),
    ],
)
def test_request_rejects_invalid_serial_write_progress(
    invalid_progress: int,
    expected_error: str,
) -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(
        [b'{"ok":true}\n'],
        write_outcomes=[invalid_progress],
    )
    transport = SerialCommandTransport(serial)

    with pytest.raises(TransportWriteError, match="invalid progress") as raised:
        transport.request(command)

    assert raised.value.error == expected_error
    assert raised.value.frame_bytes_accepted == 0
    assert serial.writes == [command]
    assert serial.flush_count == 0
    assert serial.read_sizes == []


def test_request_accepts_exact_host_frame_limit() -> None:
    serial = FakeSerial([b'{"ok":true}\n'])
    transport = SerialCommandTransport(serial)
    command = _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES)

    response = transport.request(command)

    assert response == CommandSuccessMessage()
    assert serial.writes == [command]
    assert serial.flush_count == 1


def test_request_rejects_oversized_host_frame_before_serial_dispatch() -> None:
    serial = FakeSerial()
    transport = SerialCommandTransport(serial)

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        transport.request(_compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1))

    assert raised.value.actual_frame_bytes == MAX_HOST_FRAME_BYTES + 1
    assert raised.value.max_frame_bytes == MAX_HOST_FRAME_BYTES
    assert serial.writes == []
    assert serial.flush_count == 0
    assert serial.read_sizes == []


def test_request_returns_command_error_response() -> None:
    serial = FakeSerial(
        [b'{"ok":false,"error":"not_configured","detail":"CTRL0 is not configured"}\n']
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    )

    assert response == CommandErrorMessage(
        error="not_configured",
        detail="CTRL0 is not configured",
    )


def test_request_queues_non_command_messages_before_response() -> None:
    serial = FakeSerial(
        [
            b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
            b'"capabilities":[]}\n',
            b'{"ok":true}\n',
        ]
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    )

    assert response == CommandSuccessMessage()
    assert transport.read_message() == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=(),
    )


def test_drain_pending_messages_preserves_event_order() -> None:
    serial = FakeSerial(
        [
            b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"Qk9PVAo="}\n',
            b'{"type":"buffer_status","timestamp_us":11,"uart_rx_size_bytes":32768,'
            b'"uart_rx_used_bytes":64,"uart_rx_high_water_bytes":128,'
            b'"dropped_bytes_total":0,"overflow_events":0}\n',
            b'{"ok":true,"timestamp_us":12}\n',
        ]
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    )

    assert response == CommandSuccessMessage(timestamp_us=12)
    assert transport.drain_pending_messages() == (
        UartMessage(
            channel=0,
            timestamp_us=10,
            data=b"BOOT\n",
            text="BOOT\n",
        ),
        BufferStatusMessage(
            timestamp_us=11,
            uart_rx_size_bytes=32768,
            uart_rx_used_bytes=64,
            uart_rx_high_water_bytes=128,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )
    assert transport.drain_pending_messages() == ()


def test_read_message_returns_queued_message_before_reading_serial_port() -> None:
    serial = FakeSerial(
        [
            b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"QQ=="}\n',
            b'{"ok":true}\n',
            b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"Qg=="}\n',
        ]
    )
    transport = SerialCommandTransport(serial)
    transport.request(b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n')

    first = transport.read_message()
    second = transport.read_message()

    assert isinstance(first, UartMessage)
    assert first.data == b"A"
    assert isinstance(second, UartMessage)
    assert second.data == b"B"


def test_read_message_returns_non_command_message() -> None:
    serial = FakeSerial(
        [
            b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
            b'"capabilities":[]}\n'
        ]
    )
    transport = SerialCommandTransport(serial)

    assert transport.read_message() == HelloMessage(
        firmware="0.1.0",
        device="dutchmate-rp2040",
        capabilities=(),
    )


def test_read_message_times_out_when_no_bytes_are_available() -> None:
    transport = SerialCommandTransport(FakeSerial())

    with pytest.raises(TransportTimeoutError, match="waiting for Debug Helper message"):
        transport.read_message()


def test_read_message_times_out_on_incomplete_line() -> None:
    transport = SerialCommandTransport(FakeSerial([b'{"ok":true}']))

    with pytest.raises(TransportTimeoutError, match="complete Debug Helper message"):
        transport.read_message()


def test_read_message_bounds_serial_read_and_rejects_full_pending_frame() -> None:
    serial = FakeSerial([b"x" * 65536])
    transport = SerialCommandTransport(serial)

    with pytest.raises(FrameTooLargeError) as raised:
        transport.read_message()

    assert serial.read_sizes == [65536]
    assert raised.value.observed_frame_bytes == 65536
    assert raised.value.max_frame_bytes == 65536


def test_request_rejects_non_newline_terminated_command() -> None:
    transport = SerialCommandTransport(FakeSerial())

    with pytest.raises(ValueError, match="newline-terminated"):
        transport.request(b'{"cmd":"pulse_control","channel":"CTRL0"}')


def test_close_closes_underlying_serial_port() -> None:
    serial = FakeSerial()
    transport = SerialCommandTransport(serial)

    transport.close()

    assert serial.closed is True


def test_open_serial_command_transport_uses_factory_arguments() -> None:
    calls: list[dict[str, object]] = []
    serial = FakeSerial()

    def factory(**kwargs: object) -> FakeSerial:
        calls.append(kwargs)
        return serial

    transport = open_serial_command_transport(
        port="/dev/ttyACM0",
        baudrate=460800,
        timeout_s=0.5,
        serial_factory=factory,
    )

    assert isinstance(transport, SerialCommandTransport)
    assert calls == [{"port": "/dev/ttyACM0", "baudrate": 460800, "timeout": 0.5}]
