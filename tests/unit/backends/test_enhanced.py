"""Enhanced wire-to-normalized-event compatibility adapter tests."""

import pytest

from dutchmate_core.backends import (
    BackendInputError,
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.backends.enhanced import (
    EnhancedCaptureEventSource,
    EnhancedNdjsonEventStream,
    normalize_enhanced_message,
)
from dutchmate_core.device_connection.errors import ProtocolValidationError
from dutchmate_core.device_connection.messages import (
    BufferOverflowMessage,
    BufferStatusMessage,
    HelloMessage,
    UartMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.transport import TransportTimeoutError


class FakeEnhancedMessageSource:
    def __init__(self, outcomes: list[DeviceMessage | Exception]) -> None:
        self._outcomes = outcomes

    def read_message(self) -> DeviceMessage:
        outcome = self._outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


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


def test_sync_adapter_maps_protocol_failure_to_backend_input_error() -> None:
    source = EnhancedCaptureEventSource(
        FakeEnhancedMessageSource([ProtocolValidationError("invalid message")]),
        segment_id=0,
        source_origin_us=0,
    )

    with pytest.raises(BackendInputError, match="invalid message"):
        source.read_event()


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

    assert events == [
        UartReceiveEvent(segment_id=4, timestamp_us=25, channel=0, data=b"X\n")
    ]


def test_ndjson_stream_maps_invalid_input_to_backend_input_error() -> None:
    stream = EnhancedNdjsonEventStream()

    with pytest.raises(BackendInputError):
        stream.feed(b"not-json\n")
