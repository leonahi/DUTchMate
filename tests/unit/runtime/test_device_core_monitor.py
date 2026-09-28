"""Runtime Monitor windows over continuously durable evidence."""

from __future__ import annotations

import json
import time
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Condition, Event

import pytest
from runtime_test_support import FakeDeviceControl

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    BufferOverflowEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.evidence import ContinuousEvidenceRecorder
from dutchmate_core.operations import (
    EvidenceRange,
    MonitorCondition,
    MonitorMatcher,
    MonitorTimestampProvenance,
)
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.runtime import DeviceCoreRuntime, DeviceCoreRuntimeError
from dutchmate_core.session_store.metadata import MIN_V2_EVIDENCE_BUDGET_BYTES
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.session_store.store import SessionStore


class ControlledSource:
    def __init__(self, *, segment_id: int = 0) -> None:
        self.segment = _segment(segment_id)
        self._condition = Condition()
        self._outcomes: deque[BackendEvent | BaseException | None] = deque()
        self.closed = False
        self.read_count = 0
        self._active_reads = 0
        self.max_concurrent_reads = 0

    def publish(self, outcome: BackendEvent | BaseException | None) -> None:
        with self._condition:
            self._outcomes.append(outcome)
            self._condition.notify_all()

    def read_event(self) -> BackendEvent | None:
        with self._condition:
            self.read_count += 1
            self._active_reads += 1
            self.max_concurrent_reads = max(
                self.max_concurrent_reads,
                self._active_reads,
            )
            try:
                while not self._outcomes and not self.closed:
                    self._condition.wait()
                if not self._outcomes and self.closed:
                    raise BackendDisconnectedError("source closed")
                outcome = self._outcomes.popleft()
            finally:
                self._active_reads -= 1
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome

    def close(self) -> None:
        with self._condition:
            self.closed = True
            self._condition.notify_all()


def _segment(segment_id: int) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=segment_id * 1000,
            observation_point="debug_helper_uart_rx",
            event_granularity="firmware_uart_event",
        ),
    )


def _snapshot(segment_id: int = 0) -> BackendSnapshot:
    info = BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="dutchmate-rp2350",
        firmware="0.1.0",
        capabilities=frozenset({"uart_receive", "device_timestamp"}),
    )
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
    )
    return BackendSnapshot(
        info=info,
        capabilities=info.capabilities,
        capability_policy=policy,
        segment=_segment(segment_id),
        integrity=UartIntegrity("none_reported", "debug_helper_rx_buffer", 0),
    )


def _runtime(
    tmp_path: Path,
    source: ControlledSource,
    *,
    operation_ids: tuple[str, ...] = ("monitor-test",),
    evidence_budget_bytes: int | None = None,
    max_count: int | None = None,
) -> tuple[DeviceCoreRuntime, ContinuousEvidenceRecorder, SessionStore]:
    profile = resolve_dut_profile(
        DutProfileConfig(),
        mode="enhanced",
        serial_port="/dev/ttyACM0",
    )
    store_options: dict[str, object] = {}
    if evidence_budget_bytes is not None:
        store_options["evidence_budget_bytes"] = evidence_budget_bytes
    if max_count is not None:
        store_options["max_count"] = max_count
    store = SessionStore(root=tmp_path, **store_options)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=profile,
        backend_snapshot=_snapshot(source.segment.segment_id),
    )
    identifiers = iter(operation_ids)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        session_store=store,
        profile=profile,
        evidence_recorder=recorder,
        monitor_id_factory=lambda: next(identifiers),
    )
    runtime.record_backend_connection(_snapshot().info)
    return runtime, recorder, store


def _wait_for_operation_start(
    store: SessionStore,
    session_id: str,
    *,
    count: int = 1,
) -> None:
    path = store.root / session_id / "operation_events.jsonl"
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline:
        if len(path.read_text(encoding="utf-8").splitlines()) >= count:
            return
        time.sleep(0.001)
    raise AssertionError("Monitor operation was not durably started")


def _operation_records(store: SessionStore, session_id: str) -> list[dict[str, object]]:
    path = store.root / session_id / "operation_events.jsonl"
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_duration_monitor_persists_bounded_window_without_second_reader(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        result = runtime.monitor(duration_s=0.01)

        assert result.operation_id == "monitor-test"
        assert result.outcome == "elapsed"
        assert result.mode == "duration"
        assert result.duration_s == 0.01
        assert result.start_cursor.session_id == recorder.active_session_id
        assert result.end_cursor.next_evidence_seq > result.start_cursor.next_evidence_seq
        assert source.max_concurrent_reads == 1
        record_types = [
            record["type"]
            for record in _operation_records(store, result.end_cursor.session_id)
        ]
        assert record_types == [
            "operation_started",
            "operation_terminal",
        ]
    finally:
        runtime.close()


def test_condition_monitor_ignores_history_and_persists_exact_match(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    initial_tail = recorder.durable_tail()
    source.publish(
        UartReceiveEvent(
            segment_id=0,
            timestamp_us=1,
            channel=0,
            data=b"OLD_READY\nRE",
        )
    )
    assert recorder.wait_for_durable_tail(initial_tail, timeout_s=1) is not None

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=2,
                    channel=0,
                    data=b"ADY\nREADY\n",
                )
            )
            result = pending.result(timeout=1)

        assert result.outcome == "matched"
        assert result.match is not None
        assert result.match.source_evidence_seq >= result.start_cursor.next_evidence_seq
        assert result.match.match_start_byte == 0
        assert result.match.excerpt_raw == b"READY\n"
        terminal = _operation_records(store, result.end_cursor.session_id)[-1]
        assert terminal["matched_condition"] == result.match.persistence_projection()
        assert terminal["line_processing_limited"] is False
    finally:
        runtime.close()


def test_condition_monitor_timeout_is_normal_terminal_outcome(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, _recorder, _store = _runtime(tmp_path, source)

    try:
        result = runtime.monitor(
            conditions=(MonitorCondition(pattern="READY"),),
            timeout_s=0.01,
        )

        assert result.outcome == "timeout"
        assert result.match is None
    finally:
        runtime.close()


def test_legacy_wait_pattern_is_a_thin_monitor_alias(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.wait_pattern,
                pattern="READY",
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=5,
                    channel=0,
                    data=b"READY\n",
                )
            )
            result = pending.result(timeout=1)

        assert result.outcome == "matched"
        assert result.mode == "conditions"
        assert result.conditions == (MonitorCondition(pattern="READY"),)
        assert source.max_concurrent_reads == 1
    finally:
        runtime.close()


def test_legacy_capture_uart_is_a_thin_monitor_alias(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, _recorder, _store = _runtime(tmp_path, source)

    try:
        result = runtime.capture_uart(duration_s=0.01)

        assert result.outcome == "elapsed"
        assert result.mode == "duration"
    finally:
        runtime.close()


def test_legacy_monitor_aliases_have_no_v1_runtime_fallback(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, recorder, _store = _runtime(tmp_path, source)
    runtime._evidence_recorder = None  # noqa: SLF001

    try:
        with pytest.raises(DeviceCoreRuntimeError, match="recorder is unavailable"):
            runtime.capture_uart(duration_s=0.01)
        with pytest.raises(DeviceCoreRuntimeError, match="recorder is unavailable"):
            runtime.wait_pattern(pattern="READY", timeout_s=0.01)
    finally:
        runtime._evidence_recorder = recorder  # noqa: SLF001
        runtime.close()


def test_monitor_continues_across_reconnect_with_same_operation_id(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(BackendDisconnectedError("link lost"))
            assert recorder.wait_for_disconnect(timeout_s=1)
            recorder.close_current_source_for_reconnect()
            replacement = ControlledSource(segment_id=1)
            recorder.replace_source(replacement, backend_snapshot=_snapshot(1))
            replacement.publish(
                UartReceiveEvent(
                    segment_id=1,
                    timestamp_us=10,
                    channel=0,
                    data=b"READY\n",
                )
            )
            result = pending.result(timeout=1)

        assert result.operation_id == "monitor-test"
        assert result.outcome == "matched"
        assert result.match is not None
        assert result.match.segment_id == 1
    finally:
        runtime.close()


def test_monitor_reconnect_timeout_returns_disconnected_terminal_outcome(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(BackendDisconnectedError("link lost"))
            assert recorder.wait_for_disconnect(timeout_s=1)
            recorder.close_current_source_for_reconnect()
            recorder.reconnect_timed_out()
            result = pending.result(timeout=1)

        assert result.outcome == "disconnected"
        assert result.match is None
        terminal = _operation_records(store, result.end_cursor.session_id)[-1]
        assert terminal["outcome"] == "disconnected"
    finally:
        runtime.close()


def test_monitor_backend_input_fault_persists_error_terminal_record(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(BackendInputError("invalid backend frame"))
            with pytest.raises(DeviceCoreRuntimeError, match="recording faulted"):
                pending.result(timeout=1)
            _wait_for_operation_start(store, recorder.active_session_id, count=2)

        terminal = _operation_records(store, recorder.active_session_id)[-1]
        assert terminal["type"] == "operation_terminal"
        assert terminal["outcome"] == "error"
        assert terminal["error"]["code"] == "backend_input_error"  # type: ignore[index]
    finally:
        runtime.close()


def test_two_monitors_observe_same_durable_event_without_another_reader(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(
        tmp_path,
        source,
        operation_ids=("monitor-one", "monitor-two"),
    )

    try:
        with ThreadPoolExecutor(max_workers=2) as executor:
            first = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            second = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id, count=2)
            assert len(runtime.status().active_operations) == 2
            source.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=20,
                    channel=0,
                    data=b"READY\n",
                )
            )
            results = (first.result(timeout=1), second.result(timeout=1))

        assert {result.operation_id for result in results} == {
            "monitor-one",
            "monitor-two",
        }
        assert {result.outcome for result in results} == {"matched"}
        assert source.max_concurrent_reads == 1
    finally:
        runtime.close()


def test_monitor_cancellation_persists_cancelled_terminal_record(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    cancellation = Event()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
                cancellation=cancellation,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            cancellation.set()
            result = pending.result(timeout=1)

        assert result.outcome == "cancelled"
        assert _operation_records(store, result.end_cursor.session_id)[-1][
            "outcome"
        ] == "cancelled"
    finally:
        runtime.close()


def test_monitor_evidence_ranges_follow_session_rollover(tmp_path: Path) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(
        tmp_path,
        source,
        evidence_budget_bytes=MIN_V2_EVIDENCE_BUDGET_BYTES,
    )
    initial_session_id = recorder.active_session_id

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=2.0,
            )
            _wait_for_operation_start(store, initial_session_id)
            tail = recorder.durable_tail()
            payload = b"x" * 32767 + b"\n"
            for timestamp_us in range(1, 20):
                source.publish(
                    UartReceiveEvent(
                        segment_id=0,
                        timestamp_us=timestamp_us,
                        channel=0,
                        data=payload,
                    )
                )
                changed = recorder.wait_for_durable_tail(tail, timeout_s=1)
                assert changed is not None
                tail = changed
                if tail.session_id != initial_session_id:
                    break
            else:
                raise AssertionError("test evidence did not trigger session rollover")
            source.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=30,
                    channel=0,
                    data=b"READY\n",
                )
            )
            result = pending.result(timeout=1)

        assert result.outcome == "matched"
        assert len(result.evidence_ranges) == 2
        assert result.evidence_ranges[0].session_id == initial_session_id
        assert result.evidence_ranges[1].session_id == result.end_cursor.session_id
    finally:
        runtime.close()


def test_monitor_start_rollover_flushes_pre_cursor_partial_line(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    tail = recorder.durable_tail()
    source.publish(UartReceiveEvent(0, 1, 0, b"ER"))
    changed = recorder.wait_for_durable_tail(tail, timeout_s=1)
    assert changed is not None
    predecessor_id = changed.session_id
    original_fits = store._v2_unit_fits  # noqa: SLF001

    def force_predecessor_rollover(
        metadata: dict[str, object],
        *,
        unit_bytes: int,
    ) -> bool:
        if metadata.get("predecessor_session_id") is None:
            return False
        return original_fits(metadata, unit_bytes=unit_bytes)

    monkeypatch.setattr(store, "_v2_unit_fits", force_predecessor_rollover)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="ERROR"),),
                timeout_s=0.05,
            )
            while recorder.active_session_id == predecessor_id:
                time.sleep(0.001)
            source.publish(UartReceiveEvent(0, 2, 0, b"ROR\n"))
            result = pending.result(timeout=1)

        assert result.outcome == "timeout"
        assert result.start_cursor.session_id == result.end_cursor.session_id
        assert result.start_cursor.session_id != predecessor_id
    finally:
        runtime.close()


def test_monitor_terminal_rollover_flushes_partial_line_before_successor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    cancellation = Event()

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="NEVER"),),
                timeout_s=1.0,
                cancellation=cancellation,
            )
            predecessor_id = recorder.active_session_id
            _wait_for_operation_start(store, predecessor_id)
            tail = recorder.durable_tail()
            source.publish(UartReceiveEvent(0, 1, 0, b"ER"))
            changed = recorder.wait_for_durable_tail(tail, timeout_s=1)
            assert changed is not None
            uart_path = tmp_path / predecessor_id / "uart_raw.log"
            deadline = time.monotonic() + 1
            while uart_path.read_bytes() != b"ER" and time.monotonic() < deadline:
                time.sleep(0.001)
            assert uart_path.read_bytes() == b"ER"
            original_fits = store._v2_unit_fits  # noqa: SLF001

            def force_predecessor_rollover(
                metadata: dict[str, object],
                *,
                unit_bytes: int,
            ) -> bool:
                if metadata.get("predecessor_session_id") is None:
                    return False
                return original_fits(metadata, unit_bytes=unit_bytes)

            monkeypatch.setattr(store, "_v2_unit_fits", force_predecessor_rollover)
            cancellation.set()
            result = pending.result(timeout=1)

        assert result.end_cursor.session_id != predecessor_id
        tail = recorder.durable_tail()
        source.publish(UartReceiveEvent(0, 2, 0, b"ROR\n"))
        changed = recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert changed is not None
        assert json.loads(
            (tmp_path / changed.session_id / "detected_patterns.json").read_text(
                encoding="utf-8"
            )
        ) == []
    finally:
        runtime.close()


def test_monitor_local_read_error_persists_error_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    def fail_read(*_args: object, **_kwargs: object) -> tuple[()]:
        raise RuntimeError("injected Monitor read failure")

    monkeypatch.setattr(recorder, "read_monitor_evidence", fail_read)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            tail = recorder.durable_tail()
            source.publish(UartReceiveEvent(0, 1, 0, b"anything\n"))
            assert recorder.wait_for_durable_tail(tail, timeout_s=1) is not None
            with pytest.raises(RuntimeError, match="injected Monitor read failure"):
                pending.result(timeout=1)

        terminal = _operation_records(store, recorder.active_session_id)[-1]
        assert terminal["outcome"] == "error"
        assert terminal["error"]["code"] == "monitor_error"  # type: ignore[index]
        assert store.load_metadata(recorder.active_session_id)["active_operations"] == {}
    finally:
        runtime.close()


def test_monitor_matching_error_persists_error_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    def fail_match(
        _matcher: MonitorMatcher,
        _evidence: object,
    ) -> object:
        raise RuntimeError("injected Monitor matcher failure")

    monkeypatch.setattr(MonitorMatcher, "process", fail_match)
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, recorder.active_session_id)
            source.publish(UartReceiveEvent(0, 1, 0, b"evidence\n"))
            with pytest.raises(RuntimeError, match="injected Monitor matcher failure"):
                pending.result(timeout=1)

        terminal = _operation_records(store, recorder.active_session_id)[-1]
        assert terminal["outcome"] == "error"
        assert terminal["error"]["code"] == "monitor_error"  # type: ignore[index]
    finally:
        runtime.close()


def test_monitor_post_start_initialization_error_persists_error_terminal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    def fail_reader(*_args: object, **_kwargs: object) -> object:
        raise RuntimeError("injected Monitor reader initialization failure")

    monkeypatch.setattr(store, "open_v2_monitor_evidence_reader", fail_reader)
    try:
        with pytest.raises(
            RuntimeError,
            match="injected Monitor reader initialization failure",
        ):
            runtime.monitor(duration_s=0.01)

        terminal = _operation_records(store, recorder.active_session_id)[-1]
        assert terminal["outcome"] == "error"
        assert terminal["error"]["code"] == "monitor_error"  # type: ignore[index]
        assert store.load_metadata(recorder.active_session_id)["active_operations"] == {}
    finally:
        runtime.close()


def test_monitor_terminal_persistence_failure_faults_recorder_and_clears_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)
    original_complete = store.complete_v2_operation

    def fail_complete(*args: object, **kwargs: object) -> object:
        if kwargs.get("outcome") == "elapsed":
            raise SessionPersistenceError(
                operation="complete Monitor",
                path=tmp_path,
                detail="injected disk failure",
            )
        return original_complete(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(store, "complete_v2_operation", fail_complete)
    with pytest.raises(SessionPersistenceError, match="injected disk failure"):
        runtime.monitor(duration_s=0.01)

    assert recorder.state == "faulted"
    metadata = store.load_metadata(recorder.active_session_id)
    assert metadata["state"] == "failed"
    assert metadata["active_operations"] == {}
    runtime.close()


def test_monitor_quality_and_provenance_cover_all_rollover_ranges(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            predecessor_id = recorder.active_session_id
            _wait_for_operation_start(store, predecessor_id)
            tail = recorder.durable_tail()
            source.publish(BufferOverflowEvent(0, 1, 0, 7))
            changed = recorder.wait_for_durable_tail(tail, timeout_s=1)
            assert changed is not None
            original_fits = store._v2_unit_fits  # noqa: SLF001

            def force_predecessor_rollover(
                metadata: dict[str, object],
                *,
                unit_bytes: int,
            ) -> bool:
                if metadata.get("predecessor_session_id") is None:
                    return False
                return original_fits(metadata, unit_bytes=unit_bytes)

            monkeypatch.setattr(store, "_v2_unit_fits", force_predecessor_rollover)
            source.publish(UartReceiveEvent(0, 2, 0, b"READY\n"))
            result = pending.result(timeout=1)

        assert result.integrity == UartIntegrity(
            "loss_reported",
            "debug_helper_rx_buffer",
            7,
        )
        assert [item.session_id for item in result.timestamp_provenance] == [
            predecessor_id,
            result.end_cursor.session_id,
        ]
    finally:
        runtime.close()


def test_monitor_range_lease_protects_predecessor_until_result_is_built(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source, max_count=1)
    predecessor_id = recorder.active_session_id
    original_summary = recorder.summarize_monitor_evidence
    observed_protection: list[tuple[str, ...]] = []

    def summarize_with_concurrent_retention(
        ranges: tuple[EvidenceRange, ...],
    ) -> tuple[UartIntegrity | None, tuple[MonitorTimestampProvenance, ...]]:
        retention = store.run_retention()
        observed_protection.append(retention.protected_session_ids)
        assert retention.deleted_session_ids == ()
        assert predecessor_id in retention.protected_session_ids
        return original_summary(ranges)

    monkeypatch.setattr(
        recorder,
        "summarize_monitor_evidence",
        summarize_with_concurrent_retention,
    )
    try:
        with ThreadPoolExecutor(max_workers=1) as executor:
            pending = executor.submit(
                runtime.monitor,
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=1.0,
            )
            _wait_for_operation_start(store, predecessor_id)
            original_fits = store._v2_unit_fits  # noqa: SLF001

            def force_predecessor_rollover(
                metadata: dict[str, object],
                *,
                unit_bytes: int,
            ) -> bool:
                if metadata.get("predecessor_session_id") is None:
                    return False
                return original_fits(metadata, unit_bytes=unit_bytes)

            monkeypatch.setattr(store, "_v2_unit_fits", force_predecessor_rollover)
            source.publish(UartReceiveEvent(0, 1, 0, b"READY\n"))
            result = pending.result(timeout=1)

        assert result.outcome == "matched"
        assert observed_protection
        assert (tmp_path / predecessor_id).exists()

        released = store.run_retention()

        assert released.deleted_session_ids == (predecessor_id,)
        assert not (tmp_path / predecessor_id).exists()
    finally:
        runtime.close()


@pytest.mark.parametrize("duration_s", [0, 301, True])
def test_invalid_monitor_has_no_operation_persistence_side_effect(
    tmp_path: Path,
    duration_s: object,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with pytest.raises(ValueError):
            runtime.monitor(duration_s=duration_s)  # type: ignore[arg-type]

        assert _operation_records(store, recorder.active_session_id) == []
    finally:
        runtime.close()


@pytest.mark.parametrize("timeout_s", [0, 301, True])
def test_invalid_condition_timeout_has_no_operation_persistence_side_effect(
    tmp_path: Path,
    timeout_s: object,
) -> None:
    source = ControlledSource()
    runtime, recorder, store = _runtime(tmp_path, source)

    try:
        with pytest.raises(ValueError):
            runtime.monitor(
                conditions=(MonitorCondition(pattern="READY"),),
                timeout_s=timeout_s,
            )

        assert _operation_records(store, recorder.active_session_id) == []
    finally:
        runtime.close()
