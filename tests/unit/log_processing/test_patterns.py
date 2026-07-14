import pytest

from dutchmate_core.log_processing.patterns import (
    DEFAULT_PATTERNS,
    PatternDetector,
    PatternMatch,
)
from dutchmate_core.uart_capture.line_buffer import UartLine


def test_detector_uses_default_patterns() -> None:
    detector = PatternDetector()

    assert detector.patterns == DEFAULT_PATTERNS


def test_scan_line_matches_default_pattern() -> None:
    detector = PatternDetector()
    line = UartLine(raw=b"ERROR: sensor failed\n", text="ERROR: sensor failed\n")

    matches = detector.scan_line(line)

    assert matches == [
        PatternMatch(
            pattern="ERROR",
            line_text="ERROR: sensor failed\n",
            line_raw=b"ERROR: sensor failed\n",
        )
    ]


def test_scan_line_returns_no_matches() -> None:
    detector = PatternDetector()
    line = UartLine(raw=b"system idle\n", text="system idle\n")

    assert detector.scan_line(line) == []


def test_scan_line_can_match_multiple_patterns_in_one_line() -> None:
    detector = PatternDetector()
    line = UartLine(raw=b"ERROR then PANIC\n", text="ERROR then PANIC\n")

    matches = detector.scan_line(line)

    assert [match.pattern for match in matches] == ["ERROR", "PANIC"]


def test_scan_lines_scans_iterable_in_order() -> None:
    detector = PatternDetector(patterns=("BOOT_OK", "ASSERT"))
    lines = [
        UartLine(raw=b"BOOT_OK\n", text="BOOT_OK\n"),
        UartLine(raw=b"ASSERT: failed\n", text="ASSERT: failed\n"),
    ]

    matches = detector.scan_lines(lines)

    assert [match.pattern for match in matches] == ["BOOT_OK", "ASSERT"]


def test_custom_patterns_replace_defaults() -> None:
    detector = PatternDetector(patterns=("READY",))
    line = UartLine(raw=b"READY\n", text="READY\n")

    assert detector.scan_line(line) == [
        PatternMatch(pattern="READY", line_text="READY\n", line_raw=b"READY\n")
    ]


def test_matching_uses_text_view_not_raw_bytes() -> None:
    detector = PatternDetector(patterns=("ERROR",))
    line = UartLine(raw=b"ERROR\n", text="not an error\n")

    assert detector.scan_line(line) == []


def test_matching_is_case_sensitive() -> None:
    detector = PatternDetector(patterns=("ERROR",))
    line = UartLine(raw=b"error\n", text="error\n")

    assert detector.scan_line(line) == []


@pytest.mark.parametrize("patterns", [(), []])
def test_patterns_must_not_be_empty(patterns: tuple[str, ...] | list[str]) -> None:
    with pytest.raises(ValueError):
        PatternDetector(patterns=patterns)


def test_patterns_must_not_be_a_single_string() -> None:
    with pytest.raises(TypeError):
        PatternDetector(patterns="ERROR")  # type: ignore[arg-type]


def test_patterns_must_not_contain_empty_strings() -> None:
    with pytest.raises(ValueError):
        PatternDetector(patterns=("ERROR", ""))


def test_patterns_must_not_contain_duplicates() -> None:
    with pytest.raises(ValueError):
        PatternDetector(patterns=("ERROR", "ERROR"))


def test_patterns_must_be_strings() -> None:
    with pytest.raises(TypeError):
        PatternDetector(patterns=("ERROR", 123))  # type: ignore[list-item]


def test_scan_line_requires_uart_line() -> None:
    detector = PatternDetector()

    with pytest.raises(TypeError):
        detector.scan_line("ERROR")  # type: ignore[arg-type]
