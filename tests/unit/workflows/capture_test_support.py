import json
from collections.abc import Callable, Iterable
from datetime import datetime, timezone
from pathlib import Path

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendEvent,
    BackendInfo,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.enhanced import EnhancedNdjsonEventStream
from dutchmate_core.session_store.models import SessionHandle, SessionSummary
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_core.workflows.capture import (
    CaptureRecorder,
    CaptureRecordResult,
    CaptureSessionStorage,
)


def fixed_clock() -> datetime:
    return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)


def fixed_id() -> str:
    return "capture01"


def enhanced_snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
    )
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2350",
            firmware="0.1.0",
            capabilities=frozenset({"gpio_control", "uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=1_000,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        ),
        integrity=UartIntegrity(
            loss_status="none_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=0,
        ),
    )


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


class LifecycleCaptureEventSource(FakeCaptureEventSource):
    def __init__(
        self,
        script: list[BackendEvent | None],
        *,
        clock: FakeMonotonicClock,
        trace: list[str],
        session_exists: Callable[[], bool],
    ) -> None:
        super().__init__(script, clock=clock)
        self._trace = trace
        self._session_exists = session_exists

    def begin_workflow(self) -> None:
        assert self._session_exists()
        self._trace.append("begin")

    def end_workflow(self) -> None:
        self._trace.append("end")

    def read_event(self) -> BackendEvent | None:
        self._trace.append("read")
        return super().read_event()


class EnhancedCaptureFixtureRecorder:
    """Compose Enhanced fixture parsing with the shared capture recorder."""

    def __init__(
        self,
        *,
        recorder: CaptureRecorder,
        event_stream: EnhancedNdjsonEventStream | None = None,
    ) -> None:
        self._recorder = recorder
        self._event_stream = event_stream or EnhancedNdjsonEventStream()

    @classmethod
    def start(
        cls,
        *,
        session_store: CaptureSessionStorage,
        command: str,
        firmware: str | None = None,
        device: str | None = None,
        baseline: bool = False,
        uart_processor: UartCaptureProcessor | None = None,
    ) -> "EnhancedCaptureFixtureRecorder":
        return cls(
            recorder=CaptureRecorder.start(
                session_store=session_store,
                command=command,
                firmware=firmware,
                device=device,
                baseline=baseline,
                uart_processor=uart_processor,
            )
        )

    @property
    def session_handle(self) -> SessionHandle:
        return self._recorder.session_handle

    @property
    def pending_bytes(self) -> bytes:
        return self._event_stream.pending_bytes

    def feed(self, chunk: bytes) -> list[CaptureRecordResult]:
        return [self._recorder.record_event(event) for event in self._event_stream.feed(chunk)]


def run_enhanced_capture_fixture(
    *,
    chunks: Iterable[bytes],
    session_store: CaptureSessionStorage,
    command: str,
    firmware: str | None = None,
    device: str | None = None,
    baseline: bool = False,
    uart_processor: UartCaptureProcessor | None = None,
) -> SessionSummary:
    """Record a finite Enhanced fixture stream and return its summary."""

    recorder = EnhancedCaptureFixtureRecorder.start(
        session_store=session_store,
        command=command,
        firmware=firmware,
        device=device,
        baseline=baseline,
        uart_processor=uart_processor,
    )
    for chunk in chunks:
        recorder.feed(chunk)
    return session_store.summarize_session(recorder.session_handle.session_id)


def read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
