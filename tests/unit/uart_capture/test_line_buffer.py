import pytest

from dutchmate_core.uart_capture.line_buffer import UartLine, UartLineBuffer


def test_feed_complete_line() -> None:
    buffer = UartLineBuffer()

    lines = buffer.feed(b"BOOT_OK\n")

    assert lines == [UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n")]
    assert buffer.pending_bytes == b""


def test_feed_multiple_lines() -> None:
    buffer = UartLineBuffer()

    lines = buffer.feed(b"line 1\nline 2\n")

    assert lines == [
        UartLine(raw=b"line 1\n", text="line 1\n"),
        UartLine(raw=b"line 2\n", text="line 2\n"),
    ]


def test_feed_split_line_across_chunks() -> None:
    buffer = UartLineBuffer()

    assert buffer.feed(b"BOOT_") == []
    assert buffer.pending_bytes == b"BOOT_"

    lines = buffer.feed(b"OK\n")

    assert lines == [UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n")]
    assert buffer.pending_bytes == b""


def test_pattern_split_across_chunks_is_emitted_as_one_line() -> None:
    buffer = UartLineBuffer()

    assert buffer.feed(b"ER") == []
    lines = buffer.feed(b"ROR: sensor failed\n")

    assert lines == [UartLine(raw=b"ERROR: sensor failed\n", text="ERROR: sensor failed\n")]


def test_preserves_trailing_partial_line() -> None:
    buffer = UartLineBuffer()

    lines = buffer.feed(b"line 1\npartial")

    assert lines == [UartLine(raw=b"line 1\n", text="line 1\n")]
    assert buffer.pending_bytes == b"partial"


def test_lossy_utf8_text_view() -> None:
    buffer = UartLineBuffer()

    lines = buffer.feed(b"\xff\xfeOK\n")

    assert lines == [UartLine(raw=b"\xff\xfeOK\n", text="\ufffd\ufffdOK\n")]


def test_flush_returns_partial_line() -> None:
    buffer = UartLineBuffer()

    assert buffer.feed(b"partial") == []

    assert buffer.flush() == UartLine(raw=b"partial", text="partial")
    assert buffer.pending_bytes == b""


def test_flush_returns_none_when_empty() -> None:
    buffer = UartLineBuffer()

    assert buffer.flush() is None


def test_feed_requires_bytes() -> None:
    buffer = UartLineBuffer()

    with pytest.raises(TypeError):
        buffer.feed("not bytes")  # type: ignore[arg-type]
