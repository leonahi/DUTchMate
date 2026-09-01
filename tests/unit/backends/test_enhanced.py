"""Enhanced async command and normalized-event adapter tests."""

import pytest

from dutchmate_core.backends import (
    BackendInputError,
    BackendUartSendResult,
    BackendWriteError,
    BufferOverflowEvent,
    BufferStatusEvent,
    DeviceControlError,
    UartReceiveEvent,
)
from dutchmate_core.backends.enhanced import (
    AsyncEnhancedDeviceControl,
    AsyncEnhancedUartSender,
    EnhancedNdjsonEventStream,
    normalize_enhanced_message,
)
from dutchmate_core.device_connection.errors import (
    FrameTooLargeError,
    HostCommandFrameTooLargeError,
    ProtocolValidationError,
)
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
)


class FakeAsyncCommandTransport:
    def __init__(self, response: DeviceMessage | Exception) -> None:
        self.response = response
        self.requests: list[tuple[bytes, float]] = []

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        self.requests.append((command, timeout_s))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


async def test_async_enhanced_control_uses_same_command_and_timestamp() -> None:
    transport = FakeAsyncCommandTransport(CommandSuccessMessage(timestamp_us=123))

    timestamp = await AsyncEnhancedDeviceControl(transport).pulse_control(
        channel="CTRL0",
        pulse_ms=100,
    )

    assert timestamp == 123
    assert transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]


async def test_async_enhanced_uart_sender_uses_same_acknowledgement_rules() -> None:
    transport = FakeAsyncCommandTransport(
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=3)
    )

    result = await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert result == BackendUartSendResult(
        bytes_accepted=3,
        device_timestamp_us=500,
    )
    assert transport.requests == [(b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)]


@pytest.mark.parametrize(
    "response",
    [
        CommandErrorMessage(error="hardware_fault", detail="firmware busy"),
        CommandSuccessMessage(timestamp_us=None, bytes_accepted=3),
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=2),
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=("uart_send",),
        ),
    ],
)
async def test_async_uart_sender_rejects_invalid_acknowledgements(
    response: DeviceMessage,
) -> None:
    transport = FakeAsyncCommandTransport(response)

    with pytest.raises(BackendWriteError):
        await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]


@pytest.mark.parametrize(
    "outcome",
    [
        CommandErrorMessage(error="hardware_fault", detail="firmware busy"),
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=("uart_send",),
        ),
        TransportTimeoutError("quiet"),
        TransportWriteError(
            "Enhanced serial command write failed",
            frame_bytes_accepted=2,
            error="hardware_fault",
        ),
        ProtocolValidationError("invalid command response"),
    ],
)
async def test_async_device_control_rejects_transport_and_protocol_failures(
    outcome: DeviceMessage | Exception,
) -> None:
    transport = FakeAsyncCommandTransport(outcome)

    with pytest.raises((DeviceControlError, BackendInputError)):
        await AsyncEnhancedDeviceControl(transport).pulse_control(
            channel="CTRL0", pulse_ms=100
        )

    assert transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]


@pytest.mark.parametrize(
    "outcome",
    [
        TransportTimeoutError("quiet"),
        TransportWriteError(
            "Enhanced serial command write failed",
            frame_bytes_accepted=2,
            error="timeout",
        ),
        ProtocolValidationError("invalid command response"),
    ],
)
async def test_async_uart_sender_rejects_transport_failures(
    outcome: Exception,
) -> None:
    transport = FakeAsyncCommandTransport(outcome)

    with pytest.raises((BackendWriteError, BackendInputError)):
        await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]


async def test_async_uart_sender_preserves_backend_input_error_before_transport_mapping() -> None:
    failure = BackendInputError(
        "already classified",
        input_error="invalid_message",
        operation="uart_send",
        backend_mode="enhanced",
    )

    with pytest.raises(BackendInputError) as raised:
        await AsyncEnhancedUartSender(FakeAsyncCommandTransport(failure)).send_uart(
            b"go\n"
        )

    assert raised.value is failure


async def test_async_uart_sender_classifies_device_frame_too_large() -> None:
    failure = FrameTooLargeError(
        observed_frame_bytes=65537,
        max_frame_bytes=65536,
    )
    transport = FakeAsyncCommandTransport(failure)

    with pytest.raises(BackendInputError) as raised:
        await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert raised.value.operation == "uart_send"
    assert raised.value.backend_mode == "enhanced"
    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == 65537
    assert raised.value.max_frame_bytes == 65536
    assert transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]


async def test_async_device_control_classifies_device_frame_too_large() -> None:
    failure = FrameTooLargeError(
        observed_frame_bytes=65537,
        max_frame_bytes=65536,
    )
    transport = FakeAsyncCommandTransport(failure)

    with pytest.raises(BackendInputError) as raised:
        await AsyncEnhancedDeviceControl(transport).pulse_control(
            channel="CTRL0", pulse_ms=100
        )

    assert raised.value.operation == "reset"
    assert raised.value.backend_mode == "enhanced"
    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == 65537
    assert raised.value.max_frame_bytes == 65536
    assert transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]


async def test_async_device_control_preserves_host_frame_validation_identity() -> None:
    failure = HostCommandFrameTooLargeError(
        actual_frame_bytes=2049,
        max_frame_bytes=2048,
    )
    transport = FakeAsyncCommandTransport(failure)

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        await AsyncEnhancedDeviceControl(transport).pulse_control(
            channel="CTRL0", pulse_ms=100
        )

    assert raised.value is failure
    assert transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]


async def test_async_uart_sender_preserves_host_frame_validation_identity() -> None:
    failure = HostCommandFrameTooLargeError(
        actual_frame_bytes=2049,
        max_frame_bytes=2048,
    )
    transport = FakeAsyncCommandTransport(failure)

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert raised.value is failure
    assert transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]


def test_normalizes_uart_bytes_and_segment_relative_timestamp() -> None:
    event = normalize_enhanced_message(
        UartMessage(channel=1, timestamp_us=1250, data=b"boot \xff\n", text="ignored"),
        segment_id=3,
        source_origin_us=1000,
    )

    assert event == UartReceiveEvent(
        segment_id=3,
        timestamp_us=250,
        channel=1,
        data=b"boot \xff\n",
    )


def test_normalizes_buffer_telemetry() -> None:
    overflow = normalize_enhanced_message(
        BufferOverflowMessage(channel=0, timestamp_us=1100, dropped_bytes=64),
        segment_id=2,
        source_origin_us=1000,
    )
    status = normalize_enhanced_message(
        BufferStatusMessage(
            timestamp_us=1200,
            uart_rx_size_bytes=32768,
            uart_rx_used_bytes=100,
            uart_rx_high_water_bytes=500,
            dropped_bytes_total=64,
            overflow_events=1,
        ),
        segment_id=2,
        source_origin_us=1000,
    )

    assert overflow == BufferOverflowEvent(
        segment_id=2,
        timestamp_us=100,
        channel=0,
        dropped_bytes=64,
    )
    assert status == BufferStatusEvent(
        segment_id=2,
        timestamp_us=200,
        size_bytes=32768,
        used_bytes=100,
        high_water_bytes=500,
        dropped_bytes_total=64,
        overflow_events=1,
    )


def test_ignores_non_evidence_wire_messages() -> None:
    event = normalize_enhanced_message(
        HelloMessage(firmware="0.1.0", device="dutchmate-rp2040", capabilities=()),
        segment_id=0,
        source_origin_us=0,
    )

    assert event is None


def test_rejects_event_timestamp_before_segment_origin() -> None:
    with pytest.raises(BackendInputError, match="precedes"):
        normalize_enhanced_message(
            UartMessage(channel=0, timestamp_us=999, data=b"x", text="x"),
            segment_id=0,
            source_origin_us=1000,
        )


def test_ndjson_stream_emits_only_normalized_evidence_events() -> None:
    stream = EnhancedNdjsonEventStream(segment_id=4, source_origin_us=100)

    events = stream.feed(
        b'{"type":"hello","v":1,"firmware":"0.1.0",'
        b'"device":"dutchmate-rp2040","capabilities":[]}\n'
        b'{"type":"uart","channel":0,"timestamp_us":125,"data_b64":"WAo="}\n'
    )

    assert events == [UartReceiveEvent(segment_id=4, timestamp_us=25, channel=0, data=b"X\n")]


def test_ndjson_stream_maps_invalid_input_to_backend_input_error() -> None:
    stream = EnhancedNdjsonEventStream()

    with pytest.raises(BackendInputError) as raised:
        stream.feed(b"{not-json}\n")

    assert raised.value.input_error == "invalid_json"
    assert raised.value.backend_mode == "enhanced"


def test_ndjson_stream_delivers_valid_events_before_terminal_invalid_frame() -> None:
    stream = EnhancedNdjsonEventStream()

    events = stream.feed(
        b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n'
        b'{"type":"unknown-DUT-SECRET"}\n'
        b'{"type":"uart","channel":0,"timestamp_us":2,"data_b64":"WQ=="}\n'
    )

    assert events == [UartReceiveEvent(segment_id=0, timestamp_us=1, channel=0, data=b"X")]
    with pytest.raises(BackendInputError) as raised:
        stream.feed(b"")
    assert str(raised.value) == (
        "Enhanced protocol message does not match the expected schema"
    )
    assert raised.value.input_error == "invalid_message"
    assert "DUT-SECRET" not in str(raised.value)


def test_ndjson_stream_preserves_bounded_frame_size_context() -> None:
    stream = EnhancedNdjsonEventStream()

    with pytest.raises(BackendInputError) as raised:
        stream.feed(b"x" * 65536)

    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == 65536
    assert raised.value.max_frame_bytes == 65536

