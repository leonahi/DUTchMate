import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.models import SessionSummary
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import (
    CaptureReconnectError,
    CaptureWorkflow,
    ReconnectedCaptureSource,
)


class FakeMonotonicClock:
    def __init__(self) -> None:
        self.value = 0.0

    def __call__(self) -> float:
        return self.value

    def advance(self, seconds: float) -> None:
        self.value += seconds


class ScriptedCaptureSource:
    def __init__(
        self,
        *,
        segment: SegmentContext,
        script: list[BackendEvent | Exception | None],
        clock: FakeMonotonicClock,
        read_duration_s: float = 0.1,
    ) -> None:
        self.segment = segment
        self._script = script
        self._clock = clock
        self._read_duration_s = read_duration_s
        self.close_count = 0

    def read_event(self) -> BackendEvent | None:
        self._clock.advance(self._read_duration_s)
        if not self._script:
            return None
        result = self._script.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    def close(self) -> None:
        self.close_count += 1


class ScriptedReconnect:
    def __init__(
        self,
        replacements: list[ReconnectedCaptureSource],
        *,
        on_attempt: Callable[[float], None] | None = None,
    ) -> None:
        self._replacements = replacements
        self._on_attempt = on_attempt
        self.calls: list[tuple[int, float]] = []

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        self.calls.append((segment_id, deadline))
        if self._on_attempt is not None:
            self._on_attempt(deadline)
        if not self._replacements:
            return None
        return self._replacements.pop(0)


def test_capture_resumes_without_joining_uart_lines_across_segments(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial_snapshot = _snapshot(0)
    replacement_snapshot = _snapshot(1)
    initial = ScriptedCaptureSource(
        segment=_required_segment(initial_snapshot),
        script=[
            UartReceiveEvent(segment_id=0, channel=0, timestamp_us=10, data=b"BOOT_"),
            BackendDisconnectedError("serial disconnected"),
        ],
        clock=clock,
    )
    replacement = ScriptedCaptureSource(
        segment=_required_segment(replacement_snapshot),
        script=[UartReceiveEvent(segment_id=1, channel=0, timestamp_us=5, data=b"OK\n")],
        clock=clock,
    )
    reconnect = ScriptedReconnect(
        [
            ReconnectedCaptureSource(
                source=replacement,
                backend_snapshot=replacement_snapshot,
            )
        ]
    )
    store = _store(tmp_path)

    summary = CaptureWorkflow(session_store=store).run(
        source=initial,
        duration_s=0.6,
        command="capture --seconds 0.6",
        monotonic_clock=clock,
        reconnect_timeout_s=0.5,
        backend_snapshot=initial_snapshot,
        reconnect=reconnect,
    )

    assert summary.state == "completed"
    assert summary.end_reason == "duration_elapsed"
    assert summary.interrupted is True
    assert summary.resumed is True
    assert summary.segment_count == 2
    assert len(reconnect.calls) == 1
    assert reconnect.calls[0][0] == 1
    assert reconnect.calls[0][1] == pytest.approx(0.6)
    session_root = tmp_path / summary.session_id
    assert json.loads(session_root.joinpath("detected_patterns.json").read_text()) == []
    uart_events = _read_jsonl(session_root / "uart_events.jsonl")
    assert [event["segment_id"] for event in uart_events] == [0, 1]
    assert all("timestamp_epoch" not in event for event in uart_events)
    assert [event["type"] for event in _read_jsonl(session_root / "hardware_events.jsonl")] == [
        "usb_disconnect",
        "usb_reconnect",
        "timestamp_discontinuity",
    ]
    metadata = store.load_metadata(summary.session_id)
    assert metadata["segments"][0]["end_reason"] == "usb_disconnect"  # type: ignore[index]
    assert metadata["segments"][1]["end_reason"] == "duration_elapsed"  # type: ignore[index]


def test_reconnect_deadline_failure_is_persisted_and_raised(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial_snapshot = _snapshot(0)
    source = ScriptedCaptureSource(
        segment=_required_segment(initial_snapshot),
        script=[BackendDisconnectedError("serial disconnected")],
        clock=clock,
    )
    reconnect = ScriptedReconnect([], on_attempt=lambda deadline: _set_clock(clock, deadline))
    store = _store(tmp_path)

    with pytest.raises(
        CaptureReconnectError,
        match="Backend did not reconnect before the reconnect deadline",
    ) as error_info:
        CaptureWorkflow(session_store=store).run(
            source=source,
            duration_s=2.0,
            command="capture --seconds 2",
            monotonic_clock=clock,
            reconnect_timeout_s=0.5,
            backend_snapshot=initial_snapshot,
            reconnect=reconnect,
        )

    assert error_info.value.operation == "capture"
    assert error_info.value.session_id == "20260714T123045Z-reconnect"
    assert error_info.value.reconnect_timeout_s == 0.5

    summary = store.summarize_session("20260714T123045Z-reconnect")
    assert summary.state == "failed"
    assert summary.end_reason == "reconnect_timeout"
    assert summary.interrupted is True
    assert summary.resumed is False
    assert summary.error is not None
    assert summary.error["code"] == "service_unavailable"
    assert len(reconnect.calls) == 1
    assert reconnect.calls[0][0] == 1
    assert reconnect.calls[0][1] == pytest.approx(0.6)


def test_workflow_deadline_wins_when_it_ties_reconnect_attempt(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial_snapshot = _snapshot(0)
    source = ScriptedCaptureSource(
        segment=_required_segment(initial_snapshot),
        script=[BackendDisconnectedError("serial disconnected")],
        clock=clock,
    )
    reconnect = ScriptedReconnect([], on_attempt=lambda deadline: _set_clock(clock, deadline))
    store = _store(tmp_path)

    summary = CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=0.5,
        command="capture --seconds 0.5",
        monotonic_clock=clock,
        reconnect_timeout_s=1.0,
        backend_snapshot=initial_snapshot,
        reconnect=reconnect,
    )

    assert summary.state == "completed"
    assert summary.end_reason == "duration_elapsed"
    assert summary.interrupted is True
    assert summary.resumed is False
    assert summary.error is None
    assert len(reconnect.calls) == 1
    assert reconnect.calls[0][0] == 1
    assert reconnect.calls[0][1] == pytest.approx(0.5)


def test_reconnect_quota_rejection_finishes_as_size_limit(tmp_path: Path) -> None:
    reference_root = tmp_path / "reference"
    reference_store = _store(reference_root)
    reference_clock = FakeMonotonicClock()
    reference_summary = _run_one_reconnect(
        store=reference_store,
        clock=reference_clock,
    )
    rejected_budget = _evidence_bytes(reference_root / reference_summary.session_id) - 1

    rejected_root = tmp_path / "rejected"
    rejected_store = _store(rejected_root, evidence_budget_bytes=rejected_budget)
    rejected_summary = _run_one_reconnect(
        store=rejected_store,
        clock=FakeMonotonicClock(),
    )

    assert rejected_summary.state == "completed"
    assert rejected_summary.end_reason == "size_limit"
    assert rejected_summary.truncated is True
    assert rejected_summary.interrupted is True
    assert rejected_summary.resumed is False
    assert rejected_summary.segment_count == 1
    hardware_events = _read_jsonl(
        rejected_root / rejected_summary.session_id / "hardware_events.jsonl"
    )
    assert [event["type"] for event in hardware_events] == ["usb_disconnect"]


def test_disconnect_from_segment_31_fails_without_another_reopen(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    snapshots = [_snapshot(segment_id) for segment_id in range(32)]
    sources = [
        ScriptedCaptureSource(
            segment=_required_segment(snapshot),
            script=[BackendDisconnectedError("serial disconnected")],
            clock=clock,
            read_duration_s=0.01,
        )
        for snapshot in snapshots
    ]
    reconnect = ScriptedReconnect(
        [
            ReconnectedCaptureSource(
                source=sources[segment_id], backend_snapshot=snapshots[segment_id]
            )
            for segment_id in range(1, 32)
        ]
    )
    store = _store(tmp_path)

    with pytest.raises(
        CaptureReconnectError,
        match="Session reached the 32-segment reconnect limit",
    ) as error_info:
        CaptureWorkflow(session_store=store).run(
            source=sources[0],
            duration_s=10.0,
            command="capture --seconds 10",
            monotonic_clock=clock,
            reconnect_timeout_s=1.0,
            backend_snapshot=snapshots[0],
            reconnect=reconnect,
        )

    assert error_info.value.operation == "capture"
    assert error_info.value.session_id == "20260714T123045Z-reconnect"
    assert error_info.value.segment_count == 32
    assert error_info.value.max_segments == 32

    summary = store.summarize_session("20260714T123045Z-reconnect")
    assert summary.state == "failed"
    assert summary.end_reason == "reconnect_limit"
    assert summary.segment_count == 32
    assert summary.interrupted is True
    assert summary.resumed is True
    assert [segment_id for segment_id, _deadline in reconnect.calls] == list(range(1, 32))


def test_backend_input_error_is_fatal_without_reconnect_attempt(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial_snapshot = _snapshot(0)
    source = ScriptedCaptureSource(
        segment=_required_segment(initial_snapshot),
        script=[
            BackendInputError(
                "invalid enhanced frame",
                input_error="frame_too_large",
                observed_frame_bytes=65536,
                max_frame_bytes=65536,
            )
        ],
        clock=clock,
    )
    reconnect = ScriptedReconnect([])
    store = _store(tmp_path)

    with pytest.raises(BackendInputError, match="invalid enhanced frame") as raised:
        CaptureWorkflow(session_store=store).run(
            source=source,
            duration_s=1.0,
            command="capture --seconds 1",
            monotonic_clock=clock,
            backend_snapshot=initial_snapshot,
            reconnect=reconnect,
        )

    assert raised.value.operation == "capture"
    assert raised.value.backend_mode == "enhanced"
    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == 65536
    assert raised.value.max_frame_bytes == 65536

    summary = store.summarize_session("20260714T123045Z-reconnect")
    assert summary.state == "failed"
    assert summary.end_reason == "backend_input_error"
    assert summary.interrupted is False
    assert summary.error is not None
    assert summary.error["code"] == "backend_input_error"
    assert "input_error" not in summary.error
    assert "observed_frame_bytes" not in summary.error
    assert "max_frame_bytes" not in summary.error
    assert source.close_count == 1
    assert reconnect.calls == []


def _snapshot(segment_id: int) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=BackendInfo(
            mode="enhanced",
            port="/dev/ttyACM0",
            device="dutchmate-rp2350",
            firmware="0.1.0",
            capabilities=frozenset({"uart_receive"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2350_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=segment_id * 100,
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


def _required_segment(snapshot: BackendSnapshot) -> SegmentContext:
    if snapshot.segment is None:
        raise AssertionError("test snapshot requires a segment")
    return snapshot.segment


def _store(root: Path, *, evidence_budget_bytes: int | None = None) -> SessionStore:
    def clock() -> datetime:
        return datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc)

    if evidence_budget_bytes is None:
        return SessionStore(root=root, clock=clock, id_factory=lambda: "reconnect")
    return SessionStore(
        root=root,
        clock=clock,
        id_factory=lambda: "reconnect",
        evidence_budget_bytes=evidence_budget_bytes,
    )


def _run_one_reconnect(
    *,
    store: SessionStore,
    clock: FakeMonotonicClock,
) -> SessionSummary:
    initial_snapshot = _snapshot(0)
    replacement_snapshot = _snapshot(1)
    source = ScriptedCaptureSource(
        segment=_required_segment(initial_snapshot),
        script=[BackendDisconnectedError("serial disconnected")],
        clock=clock,
    )
    replacement = ScriptedCaptureSource(
        segment=_required_segment(replacement_snapshot),
        script=[],
        clock=clock,
    )
    return CaptureWorkflow(session_store=store).run(
        source=source,
        duration_s=0.3,
        command="capture --seconds 0.3",
        monotonic_clock=clock,
        reconnect_timeout_s=1.0,
        backend_snapshot=initial_snapshot,
        reconnect=ScriptedReconnect(
            [
                ReconnectedCaptureSource(
                    source=replacement,
                    backend_snapshot=replacement_snapshot,
                )
            ]
        ),
    )


def _set_clock(clock: FakeMonotonicClock, value: float) -> None:
    clock.value = value


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _evidence_bytes(session_root: Path) -> int:
    return sum(
        session_root.joinpath(name).stat().st_size
        for name in (
            "uart_raw.log",
            "uart_events.jsonl",
            "hardware_events.jsonl",
            "detected_patterns.json",
        )
    )
