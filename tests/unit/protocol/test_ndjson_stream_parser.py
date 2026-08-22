import pytest

from dutchmate_core.device_connection.errors import FrameTooLargeError, MalformedMessageError
from dutchmate_core.device_connection.messages import HelloMessage, UartMessage
from dutchmate_core.device_connection.stream import (
    MAX_DEVICE_FRAME_BYTES,
    NdjsonStreamParser,
)


def test_feed_complete_line_returns_message() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[]}\n'
    )

    assert messages == [
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=(),
        )
    ]
    assert parser.pending_bytes == b""


def test_feed_multiple_messages_in_one_chunk() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(
        b'{"type":"hello","v":1,"firmware":"0.1.0","device":"dutchmate-rp2040","capabilities":[]}\n'
        b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n'
    )

    assert messages == [
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=(),
        ),
        UartMessage(channel=0, timestamp_us=1, data=b"X", text="X"),
    ]


def test_feed_split_message_across_chunks() -> None:
    parser = NdjsonStreamParser()

    assert parser.feed(b'{"type":"uart","channel":0,') == []
    assert parser.pending_bytes == b'{"type":"uart","channel":0,'

    messages = parser.feed(b'"timestamp_us":1,"data_b64":"WA=="}\n')

    assert messages == [UartMessage(channel=0, timestamp_us=1, data=b"X", text="X")]
    assert parser.pending_bytes == b""


def test_feed_ignores_empty_lines() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(
        b'\n\r\n{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n\n'
    )

    assert messages == [UartMessage(channel=0, timestamp_us=1, data=b"X", text="X")]


def test_feed_preserves_trailing_partial_after_complete_line() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(
        b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n{"type":"hello"'
    )

    assert messages == [UartMessage(channel=0, timestamp_us=1, data=b"X", text="X")]
    assert parser.pending_bytes == b'{"type":"hello"'


def test_feed_malformed_completed_line_raises() -> None:
    parser = NdjsonStreamParser()

    with pytest.raises(MalformedMessageError):
        parser.feed(b'{"type":"hello"\n')


def test_feed_delivers_valid_frames_before_terminal_invalid_frame() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(
        b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n'
        b'{"type":"hello"\n'
        b'{"type":"uart","channel":0,"timestamp_us":2,"data_b64":"WQ=="}\n'
    )

    assert messages == [UartMessage(channel=0, timestamp_us=1, data=b"X", text="X")]
    with pytest.raises(MalformedMessageError):
        parser.feed(b"")


def test_feed_requires_bytes() -> None:
    parser = NdjsonStreamParser()

    with pytest.raises(TypeError):
        parser.feed("not bytes")  # type: ignore[arg-type]


def test_feed_accepts_exact_maximum_complete_frame() -> None:
    parser = NdjsonStreamParser()
    prefix = (
        b'{"type":"hello","v":1,"firmware":"0.1.0",'
        b'"device":"dutchmate-rp2040","capabilities":[]'
    )
    padding = b" " * (MAX_DEVICE_FRAME_BYTES - len(prefix) - len(b"}\n"))

    messages = parser.feed(prefix + padding + b"}\n")

    assert messages == [
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=(),
        )
    ]


def test_feed_rejects_complete_frame_above_maximum_before_decode() -> None:
    parser = NdjsonStreamParser()

    with pytest.raises(FrameTooLargeError) as raised:
        parser.feed(b"x" * MAX_DEVICE_FRAME_BYTES + b"\n")

    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == MAX_DEVICE_FRAME_BYTES + 1
    assert raised.value.max_frame_bytes == MAX_DEVICE_FRAME_BYTES
    assert parser.pending_bytes == b""


def test_feed_rejects_pending_maximum_without_room_for_lf() -> None:
    parser = NdjsonStreamParser()

    assert parser.feed(b"x" * (MAX_DEVICE_FRAME_BYTES - 1)) == []
    with pytest.raises(FrameTooLargeError) as raised:
        parser.feed(b"x")

    assert raised.value.observed_frame_bytes == MAX_DEVICE_FRAME_BYTES
    assert raised.value.max_frame_bytes == MAX_DEVICE_FRAME_BYTES
    assert parser.pending_bytes == b""
