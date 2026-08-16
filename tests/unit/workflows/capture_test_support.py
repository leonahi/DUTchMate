import json
from datetime import datetime, timezone
from pathlib import Path

from dutchmate_core.backends import BackendEvent, SegmentContext


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "capture01"


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class FakeCaptureEventSource:
    def __init__(
        self,
        script: list[BackendEvent | None],
        *,
        clock: FakeMonotonicClock,
        read_duration_s: float = 0.1,
    ) -> None:
        self._script = script
        self._clock = clock
        self._read_duration_s = read_duration_s
        self.read_count = 0
        self.segment: SegmentContext | None = None

    def read_event(self) -> BackendEvent | None:
        self.read_count += 1
        self._clock.advance(self._read_duration_s)
        if not self._script:
            return None
        return self._script.pop(0)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
