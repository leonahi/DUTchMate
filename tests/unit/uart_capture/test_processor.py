import pytest

from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.log_processing.patterns import PatternDetector, PatternMatch
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult


def test_process_event_returns_completed_lines_and_matches() -> None:
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=100,
        data=b"BOOT_OK\n",
    )

    result = processor.process_event(event)

    assert result == UartCaptureResult(
        segment_id=0,
        channel=0,
        timestamp_us=100,
        lines=(UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n"),),
        matches=(PatternMatch(pattern="BOOT_OK", line_text="BOOT_OK\n", line_raw=b"BOOT_OK\n"),),
    )


def test_process_event_buffers_split_lines_until_complete() -> None:
    processor = UartCaptureProcessor()

    first = processor.process_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"ERR")
    )
    second = processor.process_event(
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=200,
            data=b"OR: sensor failed\n",
        )
    )

    assert first.lines == ()
    assert first.matches == ()
    assert processor.pending_bytes(0) == b""
    assert second.lines == (UartLine(raw=b"ERROR: sensor failed\n", text="ERROR: sensor failed\n"),)
    assert [match.pattern for match in second.matches] == ["ERROR"]


def test_process_event_tracks_split_line_event_and_byte_boundaries() -> None:
    processor = UartCaptureProcessor()

    processor.process_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"pre ER")
    )
    result = processor.process_event(
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=200,
            data=b"ROR\nnext\n",
        )
    )

    first_line, second_line = result.lines
    assert (
        first_line.ingestion_index,
        first_line.line_index_in_event,
        first_line.start_ingestion_index,
        first_line.start_event_offset,
        first_line.end_ingestion_index,
        first_line.end_event_offset,
    ) == (1, 0, 0, 0, 1, 4)
    assert (
        second_line.ingestion_index,
        second_line.line_index_in_event,
        second_line.start_ingestion_index,
        second_line.start_event_offset,
        second_line.end_ingestion_index,
        second_line.end_event_offset,
    ) == (1, 1, 1, 4, 1, 9)
    assert result.matches[0].match_start_byte == 4
    assert result.matches[0].match_end_byte == 9


def test_process_event_keeps_channel_buffers_separate() -> None:
    processor = UartCaptureProcessor()

    assert (
        processor.process_event(
            UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"ERR")
        ).lines
        == ()
    )
    assert (
        processor.process_event(
            UartReceiveEvent(segment_id=0, channel=1, timestamp_us=110, data=b"BOOT_")
        ).lines
        == ()
    )

    channel_zero = processor.process_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=200, data=b"OR\n")
    )
    channel_one = processor.process_event(
        UartReceiveEvent(segment_id=0, channel=1, timestamp_us=210, data=b"OK\n")
    )

    assert channel_zero.lines == (UartLine(raw=b"ERROR\n", text="ERROR\n"),)
    assert [match.pattern for match in channel_zero.matches] == ["ERROR"]
    assert channel_one.lines == (UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n"),)
    assert [match.pattern for match in channel_one.matches] == ["BOOT_OK"]


def test_process_event_derives_text_from_raw_uart_data() -> None:
    processor = UartCaptureProcessor()
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=100,
        data=b"system idle\n",
    )

    result = processor.process_event(event)

    assert result.lines == (UartLine(raw=b"system idle\n", text="system idle\n"),)
    assert result.matches == ()


def test_process_event_supports_custom_pattern_detector() -> None:
    processor = UartCaptureProcessor(pattern_detector=PatternDetector(patterns=("READY",)))
    event = UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"READY\n")

    result = processor.process_event(event)

    assert [match.pattern for match in result.matches] == ["READY"]


def test_pending_bytes_returns_empty_bytes_for_unused_channel() -> None:
    processor = UartCaptureProcessor()

    assert processor.pending_bytes(0) == b""


def test_flush_channel_returns_partial_line_and_matches() -> None:
    processor = UartCaptureProcessor()
    processor.process_event(
        UartReceiveEvent(
            segment_id=0,
            channel=0,
            timestamp_us=100,
            data=b"PANIC: stopped",
        )
    )

    result = processor.flush_channel(0)

    assert result == UartCaptureResult(
        segment_id=0,
        channel=0,
        timestamp_us=None,
        lines=(UartLine(raw=b"PANIC: stopped", text="PANIC: stopped"),),
        matches=(
            PatternMatch(
                pattern="PANIC",
                line_text="PANIC: stopped",
                line_raw=b"PANIC: stopped",
            ),
        ),
    )
    assert processor.pending_bytes(0) == b""


def test_flush_channel_returns_none_for_empty_channel() -> None:
    processor = UartCaptureProcessor()

    assert processor.flush_channel(0) is None


def test_flush_channel_returns_none_when_channel_has_no_pending_line() -> None:
    processor = UartCaptureProcessor()
    processor.process_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"BOOT_OK\n")
    )

    assert processor.flush_channel(0) is None


def test_process_event_requires_uart_receive_event() -> None:
    processor = UartCaptureProcessor()

    with pytest.raises(TypeError):
        processor.process_event("BOOT_OK")  # type: ignore[arg-type]


def test_process_event_keeps_segment_buffers_separate() -> None:
    processor = UartCaptureProcessor()

    processor.process_event(
        UartReceiveEvent(segment_id=0, channel=0, timestamp_us=100, data=b"ERR")
    )
    result = processor.process_event(
        UartReceiveEvent(segment_id=1, channel=0, timestamp_us=0, data=b"OR\n")
    )

    assert result.lines == (UartLine(raw=b"OR\n", text="OR\n"),)
    assert processor.pending_bytes(0, segment_id=0) == b"ERR"
