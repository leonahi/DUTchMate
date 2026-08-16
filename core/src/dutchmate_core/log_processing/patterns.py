"""Pattern detection for completed UART log lines."""

from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field

from dutchmate_core.uart_capture.line_buffer import UartLine

DEFAULT_PATTERNS = ("ERROR", "ASSERT", "PANIC", "HardFault", "BOOT_OK")


@dataclass(frozen=True, slots=True)
class PatternMatch:
    """A configured pattern found in one UART log line."""

    pattern: str
    line_text: str
    line_raw: bytes
    match_start_byte: int | None = field(default=None, compare=False)
    match_end_byte: int | None = field(default=None, compare=False)
    ingestion_index: int | None = field(default=None, compare=False)
    line_index_in_event: int | None = field(default=None, compare=False)
    line_start_ingestion_index: int | None = field(default=None, compare=False)
    line_start_event_offset: int | None = field(default=None, compare=False)
    line_end_ingestion_index: int | None = field(default=None, compare=False)
    line_end_event_offset: int | None = field(default=None, compare=False)


class PatternDetector:
    """Find configured text patterns in completed UART log lines."""

    def __init__(self, patterns: Sequence[str] = DEFAULT_PATTERNS) -> None:
        self._patterns = _validate_patterns(patterns)

    @property
    def patterns(self) -> tuple[str, ...]:
        """Configured patterns in scan order."""

        return self._patterns

    def scan_line(self, line: UartLine) -> list[PatternMatch]:
        """Return all configured patterns present in one completed UART line."""

        if not isinstance(line, UartLine):
            raise TypeError("pattern detector input must be a UartLine")

        matches: list[PatternMatch] = []
        for pattern in self._patterns:
            if pattern not in line.text:
                continue
            encoded_pattern = pattern.encode("utf-8")
            match_start_byte = line.raw.find(encoded_pattern)
            if match_start_byte < 0:
                continue
            matches.append(
                PatternMatch(
                    pattern=pattern,
                    line_text=line.text,
                    line_raw=line.raw,
                    match_start_byte=match_start_byte,
                    match_end_byte=match_start_byte + len(encoded_pattern),
                    ingestion_index=line.ingestion_index,
                    line_index_in_event=line.line_index_in_event,
                    line_start_ingestion_index=line.start_ingestion_index,
                    line_start_event_offset=line.start_event_offset,
                    line_end_ingestion_index=line.end_ingestion_index,
                    line_end_event_offset=line.end_event_offset,
                )
            )
        return matches

    def scan_lines(self, lines: Iterable[UartLine]) -> list[PatternMatch]:
        """Return pattern matches for a sequence of completed UART lines."""

        matches: list[PatternMatch] = []
        for line in lines:
            matches.extend(self.scan_line(line))
        return matches


def _validate_patterns(patterns: Sequence[str]) -> tuple[str, ...]:
    if isinstance(patterns, str):
        raise TypeError("patterns must be a sequence of strings, not a single string")

    validated = tuple(patterns)
    if not validated:
        raise ValueError("at least one pattern is required")

    seen: set[str] = set()
    for pattern in validated:
        if not isinstance(pattern, str):
            raise TypeError("patterns must be strings")
        if pattern == "":
            raise ValueError("patterns must not be empty")
        encoded = pattern.encode("utf-8")
        if len(encoded) > 256:
            raise ValueError("patterns must contain at most 256 UTF-8 bytes")
        if "\r" in pattern or "\n" in pattern:
            raise ValueError("patterns must not contain CR or LF")
        if pattern in seen:
            raise ValueError(f"duplicate pattern: {pattern}")
        seen.add(pattern)

    return validated
