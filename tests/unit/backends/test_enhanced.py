"""Enhanced wire-to-normalized-event compatibility adapter tests."""

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
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
    EnhancedCaptureEventSource,
    EnhancedDeviceControl,
    EnhancedNdjsonEventStream,
    EnhancedUartSender,
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


class FakeEnhancedMessageSource:
    def __init__(self, outcomes: list[DeviceMessage | Exception]) -> None:
        self._outcomes = outcomes
        self.drain_count = 0

    def read_message(self) -> DeviceMessage:
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def drain_pending_messages(self) -> tuple[DeviceMessage, ...]:
        self.drain_count += 1
        return ()


class FakeCommandTransport:
    def __init__(self, response: DeviceMessage | Exception) -> None:
        self.response = response
        self.requests: list[bytes] = []

    def request(self, command: bytes) -> DeviceMessage:
        self.requests.append(command)
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


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
async def test_async_uart_sender_matches_sync_rejections(
    response: DeviceMessage,
) -> None:
    async_transport = FakeAsyncCommandTransport(response)
    sync_transport = FakeCommandTransport(response)
    with pytest.raises(BackendWriteError) as async_error:
        await AsyncEnhancedUartSender(async_transport).send_uart(b"go\n")
    with pytest.raises(BackendWriteError) as sync_error:
        EnhancedUartSender(sync_transport).send_uart(b"go\n")

    assert (async_error.value.error, str(async_error.value)) == (
        sync_error.value.error,
        str(sync_error.value),
    )
    assert async_error.value.bytes_accepted == sync_error.value.bytes_accepted
    assert async_transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]
    assert sync_transport.requests == [b'{"cmd":"uart_send","data_b64":"Z28K"}\n']


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
async def test_async_device_control_matches_sync_rejections(
    outcome: DeviceMessage | Exception,
) -> None:
    async_transport = FakeAsyncCommandTransport(outcome)
    sync_transport = FakeCommandTransport(outcome)
    with pytest.raises((DeviceControlError, BackendInputError)) as async_error:
        await AsyncEnhancedDeviceControl(async_transport).pulse_control(
            channel="CTRL0", pulse_ms=100
        )
    with pytest.raises((DeviceControlError, BackendInputError)) as sync_error:
        EnhancedDeviceControl(sync_transport).pulse_control(
            channel="CTRL0", pulse_ms=100
        )

    assert type(async_error.value) is type(sync_error.value)
    assert str(async_error.value) == str(sync_error.value)
    if isinstance(async_error.value, DeviceControlError):
        assert async_error.value.error == sync_error.value.error
        assert async_error.value.detail == sync_error.value.detail
    else:
        assert isinstance(sync_error.value, BackendInputError)
        assert async_error.value.context == sync_error.value.context
    assert async_transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]
    assert sync_transport.requests == [
        b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n'
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
async def test_async_uart_sender_matches_sync_transport_failures(
    outcome: Exception,
) -> None:
    async_transport = FakeAsyncCommandTransport(outcome)
    sync_transport = FakeCommandTransport(outcome)
    with pytest.raises((BackendWriteError, BackendInputError)) as async_error:
        await AsyncEnhancedUartSender(async_transport).send_uart(b"go\n")
    with pytest.raises((BackendWriteError, BackendInputError)) as sync_error:
        EnhancedUartSender(sync_transport).send_uart(b"go\n")

    assert type(async_error.value) is type(sync_error.value)
    assert str(async_error.value) == str(sync_error.value)
    if isinstance(async_error.value, BackendWriteError):
        assert isinstance(sync_error.value, BackendWriteError)
        assert async_error.value.error == sync_error.value.error
        assert async_error.value.bytes_accepted == sync_error.value.bytes_accepted
    else:
        assert isinstance(sync_error.value, BackendInputError)
        assert async_error.value.context == sync_error.value.context
    assert async_transport.requests == [
        (b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)
    ]
    assert sync_transport.requests == [b'{"cmd":"uart_send","data_b64":"Z28K"}\n']


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


def test_enhanced_uart_sender_requires_complete_timestamped_acknowledgement() -> None:
    transport = FakeCommandTransport(
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=3)
    )

    result = EnhancedUartSender(transport).send_uart(b"go\n")

    assert result.bytes_accepted == 3
    assert result.device_timestamp_us == 500
    assert transport.requests == [b'{"cmd":"uart_send","data_b64":"Z28K"}\n']


@pytest.mark.parametrize(
    "response",
    [
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=2),
        CommandSuccessMessage(timestamp_us=None, bytes_accepted=3),
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=None),
    ],
)
def test_enhanced_uart_sender_rejects_incomplete_acknowledgement(
    response: CommandSuccessMessage,
) -> None:
    with pytest.raises(BackendWriteError):
        EnhancedUartSender(FakeCommandTransport(response)).send_uart(b"go\n")


def test_enhanced_uart_sender_preserves_firmware_error() -> None:
    response = CommandErrorMessage(error="capture_active", detail="firmware busy")

    with pytest.raises(BackendWriteError) as raised:
        EnhancedUartSender(FakeCommandTransport(response)).send_uart(b"go\n")

    assert raised.value.error == "capture_active"
    assert raised.value.bytes_accepted is None


def test_enhanced_uart_sender_maps_command_frame_write_timeout() -> None:
    failure = TransportWriteError(
        "Enhanced serial command write failed",
        frame_bytes_accepted=2,
        error="timeout",
    )

    with pytest.raises(BackendWriteError) as raised:
        EnhancedUartSender(FakeCommandTransport(failure)).send_uart(b"go\n")

    assert str(raised.value) == "Enhanced serial command write failed"
    assert raised.value.error == "timeout"
    assert raised.value.bytes_accepted is None


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


def test_sync_adapter_maps_transport_timeout_to_inactivity() -> None:
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource([TransportTimeoutError("quiet")]),
        segment_id=0,
        source_origin_us=0,
    )

    assert source.read_event() is None
    assert source.segment.segment_id == 0
    assert source.segment.timestamp.source == "device"
    assert source.segment.timestamp.clock == "rp2040_timer"
    assert source.segment.timestamp.observation_point == "debug_helper_uart_receive"
    assert source.segment.timestamp.event_granularity == "uart_event"


def test_sync_adapter_maps_protocol_failure_to_backend_input_error() -> None:
    secret = "DUT-SECRET-CAPABILITY"
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource(
            [ProtocolValidationError(f"Unknown hello capability: {secret}")]
        ),
        segment_id=0,
        source_origin_us=0,
    )

    with pytest.raises(
        BackendInputError,
        match="Enhanced protocol message does not match the expected schema",
    ) as raised:
        source.read_event()

    assert secret not in str(raised.value)
    assert raised.value.input_error == "invalid_message"
    assert raised.value.backend_mode == "enhanced"


def test_sync_adapter_maps_transport_failure_to_backend_disconnect() -> None:
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource([OSError("device removed")]),
        segment_id=0,
        source_origin_us=0,
    )

    with pytest.raises(BackendDisconnectedError, match="Enhanced serial read failed"):
        source.read_event()


def test_sync_adapter_establishes_unknown_origin_from_first_evidence_event() -> None:
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource(
            [UartMessage(channel=0, timestamp_us=8_500, data=b"ready\n", text="ready\n")]
        ),
        segment_id=2,
        source_origin_us=None,
    )

    assert source.segment is None
    assert source.read_event() == UartReceiveEvent(
        segment_id=2,
        timestamp_us=0,
        channel=0,
        data=b"ready\n",
    )
    assert source.segment is not None
    assert source.segment.segment_id == 2
    assert source.segment.timestamp.source_origin_us == 8_500


def test_sync_adapter_primes_origin_without_losing_first_event() -> None:
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource(
            [UartMessage(channel=0, timestamp_us=8_500, data=b"ready\n", text="ready\n")]
        ),
        segment_id=2,
        source_origin_us=None,
    )

    segment = source.prime_segment()

    assert segment is not None
    assert segment.segment_id == 2
    assert source.read_event() == UartReceiveEvent(
        segment_id=2,
        timestamp_us=0,
        channel=0,
        data=b"ready\n",
    )


def test_sync_adapter_discards_local_and_transport_pre_cursor_events() -> None:
    message_source = FakeEnhancedMessageSource(
        [UartMessage(channel=0, timestamp_us=8_500, data=b"old\n", text="old\n")]
    )
    source = EnhancedCaptureEventSource(
        message_source,
        segment_id=0,
        source_origin_us=None,
    )
    source.prime_segment()

    source.discard_pending_events()

    assert message_source.drain_count == 1


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


def test_uart_sender_classifies_invalid_enhanced_response() -> None:
    failure = FrameTooLargeError(
        observed_frame_bytes=65537,
        max_frame_bytes=65536,
    )

    with pytest.raises(BackendInputError) as raised:
        EnhancedUartSender(FakeCommandTransport(failure)).send_uart(b"go\n")

    assert raised.value.operation == "uart_send"
    assert raised.value.backend_mode == "enhanced"
    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == 65537
    assert raised.value.max_frame_bytes == 65536


def test_device_control_classifies_invalid_enhanced_response() -> None:
    failure = ProtocolValidationError("invalid command response")

    with pytest.raises(BackendInputError) as raised:
        EnhancedDeviceControl(FakeCommandTransport(failure)).pulse_control(
            channel="CTRL0",
            pulse_ms=100,
        )

    assert raised.value.operation == "reset"
    assert raised.value.backend_mode == "enhanced"
    assert raised.value.input_error == "invalid_message"


def test_device_control_maps_command_frame_write_failure() -> None:
    failure = TransportWriteError(
        "Enhanced serial command write failed",
        frame_bytes_accepted=2,
        error="hardware_fault",
    )

    with pytest.raises(DeviceControlError) as raised:
        EnhancedDeviceControl(FakeCommandTransport(failure)).pulse_control(
            channel="CTRL0",
            pulse_ms=100,
        )

    assert raised.value.error == "hardware_fault"
    assert raised.value.detail == "Enhanced serial command write failed"


def test_device_control_preserves_outbound_host_frame_validation() -> None:
    failure = HostCommandFrameTooLargeError(
        actual_frame_bytes=2049,
        max_frame_bytes=2048,
    )

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        EnhancedDeviceControl(FakeCommandTransport(failure)).pulse_control(
            channel="CTRL0",
            pulse_ms=100,
        )

    assert raised.value is failure


def test_uart_sender_preserves_outbound_host_frame_validation() -> None:
    failure = HostCommandFrameTooLargeError(
        actual_frame_bytes=2049,
        max_frame_bytes=2048,
    )

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        EnhancedUartSender(FakeCommandTransport(failure)).send_uart(b"go\n")

    assert raised.value is failure
