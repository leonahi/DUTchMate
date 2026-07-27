import pytest

from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.device_connection.serial_transport import (
    SerialCommandTransport,
    open_serial_command_transport,
)
from dutchmate_core.device_connection.transport import TransportTimeoutError


class FakeSerial:
    def __init__(self, reads: list[bytes] | None = None) -> None:
        self.reads = reads or []
        self.writes: list[bytes] = []
        self.flush_count = 0
        self.closed = False

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        return len(data)

    def flush(self) -> None:
        self.flush_count += 1

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        if not self.reads:
            return b""
        return self.reads.pop(0)

    def close(self) -> None:
        self.closed = True


def test_request_writes_command_and_returns_success_response() -> None:
    serial = FakeSerial([b'{"ok":true,"timestamp_us":123}\n'])
    transport = SerialCommandTransport(serial)

    response = transport.request(b'{"cmd":"reset","pulse_ms":100}\n')

    assert response == CommandSuccessMessage(timestamp_us=123)
    assert serial.writes == [b'{"cmd":"reset","pulse_ms":100}\n']
    assert serial.flush_count == 1


def test_request_returns_command_error_response() -> None:
    serial = FakeSerial(
        [b'{"ok":false,"error":"not_configured","detail":"reset is not configured"}\n']
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(b'{"cmd":"reset","pulse_ms":100}\n')

    assert response == CommandErrorMessage(
        error="not_configured",
        detail="reset is not configured",
    )


def test_request_ignores_non_command_messages_before_response() -> None:
    serial = FakeSerial(
        [
            b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040",'
            b'"capabilities":[]}\n',
            b'{"ok":true}\n',
        ]
    )
    transport = SerialCommandTransport(serial)

    response = transport.request(b'{"cmd":"reset","pulse_ms":100}\n')

    assert response == CommandSuccessMessage()


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


def test_request_rejects_non_newline_terminated_command() -> None:
    transport = SerialCommandTransport(FakeSerial())

    with pytest.raises(ValueError, match="newline-terminated"):
        transport.request(b'{"cmd":"reset"}')


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
