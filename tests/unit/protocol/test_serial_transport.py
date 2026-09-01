import pytest

from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import HostCommandFrameTooLargeError
from dutchmate_core.device_connection.serial_transport import write_serial_frame
from dutchmate_core.device_connection.transport import (
    TransportWriteError,
    validate_host_command_frame,
)


class FakeSerial:
    def __init__(
        self,
        *,
        write_outcomes: list[int | Exception] | None = None,
        flush_failure: Exception | None = None,
    ) -> None:
        self.write_outcomes = write_outcomes or []
        self.flush_failure = flush_failure
        self.writes: list[bytes] = []
        self.flush_count = 0

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

class SerialTimeoutException(Exception):
    """Pyserial-shaped timeout used without importing the serial framework."""


def _compact_json_frame_of_size(size: int) -> bytes:
    baseline = b'{"cmd":"test","data":""}\n'
    return b'{"cmd":"test","data":"' + b"x" * (size - len(baseline)) + b'"}\n'


def test_shared_serial_frame_writer_retries_ordered_short_writes_and_flushes() -> None:
    frame = b'{"cmd":"test"}\n'
    serial = FakeSerial(write_outcomes=[2, 3, len(frame) - 5])

    write_serial_frame(serial, frame)

    assert serial.writes == [frame, frame[2:], frame[5:]]
    assert serial.flush_count == 1


def test_shared_host_frame_validator_preserves_exact_limit() -> None:
    validate_host_command_frame(_compact_json_frame_of_size(MAX_HOST_FRAME_BYTES))

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        validate_host_command_frame(
            _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1)
        )

    assert raised.value.actual_frame_bytes == MAX_HOST_FRAME_BYTES + 1
    assert raised.value.max_frame_bytes == MAX_HOST_FRAME_BYTES


def test_shared_writer_reports_partial_frame_acceptance_when_write_fails() -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(write_outcomes=[2, OSError("adapter removed")])

    with pytest.raises(TransportWriteError, match="write failed") as raised:
        write_serial_frame(serial, command)

    assert raised.value.error == "hardware_fault"
    assert raised.value.frame_bytes_accepted == 2
    assert serial.writes == [command, command[2:]]
    assert serial.flush_count == 0


@pytest.mark.parametrize(
    "failure",
    [TimeoutError("write timeout"), SerialTimeoutException("write timeout")],
)
def test_shared_writer_classifies_timeout_with_partial_frame_acceptance(
    failure: Exception,
) -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(write_outcomes=[2, failure])

    with pytest.raises(TransportWriteError) as raised:
        write_serial_frame(serial, command)

    assert raised.value.error == "timeout"
    assert raised.value.frame_bytes_accepted == 2
    assert serial.flush_count == 0


def test_shared_writer_reports_complete_frame_acceptance_when_flush_fails() -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(flush_failure=OSError("adapter removed"))

    with pytest.raises(TransportWriteError, match="flush failed") as raised:
        write_serial_frame(serial, command)

    assert raised.value.error == "hardware_fault"
    assert raised.value.frame_bytes_accepted == len(command)
    assert serial.writes == [command]
    assert serial.flush_count == 1


@pytest.mark.parametrize(
    ("invalid_progress", "expected_error"),
    [
        (0, "timeout"),
        (-1, "hardware_fault"),
        (4096, "hardware_fault"),
        (True, "hardware_fault"),
    ],
)
def test_shared_writer_rejects_invalid_serial_write_progress(
    invalid_progress: int,
    expected_error: str,
) -> None:
    command = b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
    serial = FakeSerial(write_outcomes=[invalid_progress])

    with pytest.raises(TransportWriteError, match="invalid progress") as raised:
        write_serial_frame(serial, command)

    assert raised.value.error == expected_error
    assert raised.value.frame_bytes_accepted == 0
    assert serial.writes == [command]
    assert serial.flush_count == 0


def test_shared_writer_accepts_exact_host_frame_limit() -> None:
    serial = FakeSerial()
    command = _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES)

    write_serial_frame(serial, command)

    assert serial.writes == [command]
    assert serial.flush_count == 1


def test_shared_writer_rejects_oversized_host_frame_before_serial_dispatch() -> None:
    serial = FakeSerial()

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        write_serial_frame(serial, _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1))

    assert raised.value.actual_frame_bytes == MAX_HOST_FRAME_BYTES + 1
    assert raised.value.max_frame_bytes == MAX_HOST_FRAME_BYTES
    assert serial.writes == []
    assert serial.flush_count == 0
