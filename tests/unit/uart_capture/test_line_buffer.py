import pytest

from dutchmate_core.uart_capture.line_buffer import (
    MAX_UART_LINE_BYTES,
    UartLine,
    UartLineBuffer,
)


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


def test_exact_limit_line_is_emitted_normally() -> None:
    buffer = UartLineBuffer()
    raw = (b"a" * (MAX_UART_LINE_BYTES - 1)) + b"\n"

    result = buffer.feed_result(raw, ingestion_index=0, timestamp_us=10)

    assert result.lines[0].raw == raw
    assert result.oversized_lines == ()
    assert result.newly_oversized_line_count == 0


def test_byte_after_limit_discards_only_derived_copy_and_counts_until_lf() -> None:
    buffer = UartLineBuffer()

    first = buffer.feed_result(
        b"a" * MAX_UART_LINE_BYTES,
        ingestion_index=0,
        timestamp_us=10,
    )
    second = buffer.feed_result(
        b"ERROR\n",
        ingestion_index=1,
        timestamp_us=20,
    )

    assert first.lines == ()
    assert first.newly_oversized_line_count == 0
    assert buffer.pending_bytes == b""
    assert second.lines == ()
    assert second.newly_oversized_line_count == 1
    oversized = second.oversized_lines[0]
    assert oversized.total_bytes == MAX_UART_LINE_BYTES + 6
    assert oversized.terminated is True
    assert (
        oversized.start_ingestion_index,
        oversized.start_event_offset,
        oversized.end_ingestion_index,
        oversized.end_event_offset,
    ) == (0, 0, 1, 6)


def test_processing_recovers_after_oversized_lf_in_same_event() -> None:
    buffer = UartLineBuffer()

    result = buffer.feed_result(
        (b"a" * MAX_UART_LINE_BYTES) + b"\nOK\n",
        ingestion_index=7,
        timestamp_us=30,
    )

    assert result.newly_oversized_line_count == 1
    assert result.oversized_lines[0].line_index_in_event == 0
    assert result.oversized_lines[0].total_bytes == MAX_UART_LINE_BYTES + 1
    assert [line.raw for line in result.lines] == [b"OK\n"]
    assert result.lines[0].line_index_in_event == 1


def test_flush_finalizes_oversized_trailing_line_without_materializing_it() -> None:
    buffer = UartLineBuffer()
    buffer.feed_result(
        b"a" * MAX_UART_LINE_BYTES,
        ingestion_index=0,
        timestamp_us=10,
    )
    crossed = buffer.feed_result(b"x", ingestion_index=1, timestamp_us=20)

    flushed = buffer.flush_result()

    assert crossed.newly_oversized_line_count == 1
    assert crossed.oversized_lines == ()
    assert buffer.pending_bytes == b""
    oversized = flushed.oversized_lines[0]
    assert oversized.total_bytes == MAX_UART_LINE_BYTES + 1
    assert oversized.terminated is False
    assert oversized.ingestion_index == 1
    assert oversized.end_event_offset == 1
    assert oversized.timestamp_us == 20
