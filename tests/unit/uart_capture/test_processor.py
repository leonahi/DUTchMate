import pytest

from dutchmate_core.device_connection.messages import UartMessage
from dutchmate_core.log_processing.patterns import PatternDetector, PatternMatch
from dutchmate_core.uart_capture.line_buffer import UartLine
from dutchmate_core.uart_capture.processor import UartCaptureProcessor, UartCaptureResult


def test_process_message_returns_completed_lines_and_matches() -> None:
    processor = UartCaptureProcessor()
    message = UartMessage(
        channel=0,
        timestamp_us=100,
        data=b"BOOT_OK\n",
        text="BOOT_OK\n",
    )

    result = processor.process_message(message)

    assert result == UartCaptureResult(
        channel=0,
        timestamp_us=100,
        lines=(UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n"),),
        matches=(
            PatternMatch(pattern="BOOT_OK", line_text="BOOT_OK\n", line_raw=b"BOOT_OK\n"),
        ),
    )


def test_process_message_buffers_split_lines_until_complete() -> None:
    processor = UartCaptureProcessor()

    first = processor.process_message(
        UartMessage(channel=0, timestamp_us=100, data=b"ERR", text="ERR")
    )
    second = processor.process_message(
        UartMessage(
            channel=0,
            timestamp_us=200,
            data=b"OR: sensor failed\n",
            text="OR: sensor failed\n",
        )
    )

    assert first.lines == ()
    assert first.matches == ()
    assert processor.pending_bytes(0) == b""
    assert second.lines == (
        UartLine(raw=b"ERROR: sensor failed\n", text="ERROR: sensor failed\n"),
    )
    assert [match.pattern for match in second.matches] == ["ERROR"]


def test_process_message_keeps_channel_buffers_separate() -> None:
    processor = UartCaptureProcessor()

    assert processor.process_message(
        UartMessage(channel=0, timestamp_us=100, data=b"ERR", text="ERR")
    ).lines == ()
    assert processor.process_message(
        UartMessage(channel=1, timestamp_us=110, data=b"BOOT_", text="BOOT_")
    ).lines == ()

    channel_zero = processor.process_message(
        UartMessage(channel=0, timestamp_us=200, data=b"OR\n", text="OR\n")
    )
    channel_one = processor.process_message(
        UartMessage(channel=1, timestamp_us=210, data=b"OK\n", text="OK\n")
    )

    assert channel_zero.lines == (UartLine(raw=b"ERROR\n", text="ERROR\n"),)
    assert [match.pattern for match in channel_zero.matches] == ["ERROR"]
    assert channel_one.lines == (UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n"),)
    assert [match.pattern for match in channel_one.matches] == ["BOOT_OK"]


def test_process_message_uses_uart_data_not_message_text() -> None:
    processor = UartCaptureProcessor()
    message = UartMessage(
        channel=0,
        timestamp_us=100,
        data=b"system idle\n",
        text="ERROR\n",
    )

    result = processor.process_message(message)

    assert result.lines == (UartLine(raw=b"system idle\n", text="system idle\n"),)
    assert result.matches == ()


def test_process_message_supports_custom_pattern_detector() -> None:
    processor = UartCaptureProcessor(pattern_detector=PatternDetector(patterns=("READY",)))
    message = UartMessage(channel=0, timestamp_us=100, data=b"READY\n", text="READY\n")

    result = processor.process_message(message)

    assert [match.pattern for match in result.matches] == ["READY"]


def test_pending_bytes_returns_empty_bytes_for_unused_channel() -> None:
    processor = UartCaptureProcessor()

    assert processor.pending_bytes(0) == b""


def test_flush_channel_returns_partial_line_and_matches() -> None:
    processor = UartCaptureProcessor()
    processor.process_message(
        UartMessage(channel=0, timestamp_us=100, data=b"PANIC: stopped", text="PANIC: stopped")
    )

    result = processor.flush_channel(0)

    assert result == UartCaptureResult(
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
    processor.process_message(
        UartMessage(channel=0, timestamp_us=100, data=b"BOOT_OK\n", text="BOOT_OK\n")
    )

    assert processor.flush_channel(0) is None


def test_process_message_requires_uart_message() -> None:
    processor = UartCaptureProcessor()

    with pytest.raises(TypeError):
        processor.process_message("BOOT_OK")  # type: ignore[arg-type]
