import pytest

from dutchmate_core.device_connection.errors import MalformedMessageError
from dutchmate_core.device_connection.messages import HelloMessage, UartMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser


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


def test_feed_requires_bytes() -> None:
    parser = NdjsonStreamParser()

    with pytest.raises(TypeError):
        parser.feed("not bytes")  # type: ignore[arg-type]
