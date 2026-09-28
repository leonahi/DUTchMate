from __future__ import annotations

import json
from collections import deque
from pathlib import Path
from threading import Condition

import pytest

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendSnapshot,
    BufferOverflowEvent,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.evidence.recorder import (
    ContinuousEvidenceRecorder,
    DurableEvidenceTail,
)
from dutchmate_core.profile import DutProfileConfig, resolve_dut_profile
from dutchmate_core.session_store.models import (
    SessionPersistenceError,
    V2SessionDetail,
)
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


class CloseErrorSource(ControlledSource):
    def close(self) -> None:
        super().close()
        raise RuntimeError("source close failed")


def _segment(segment_id: int) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=100,
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
        capabilities=frozenset(
            {"uart_receive", "device_timestamp", "overflow_telemetry"}
        ),
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


def _profile():  # type: ignore[no-untyped-def]
    return resolve_dut_profile(
        DutProfileConfig(),
        mode="enhanced",
        serial_port="/dev/ttyACM0",
    )


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def test_idle_uart_is_durable_and_pattern_projected_without_a_workflow(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    initial_tail = recorder.durable_tail()

    try:
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=25,
                channel=0,
                data=b"READY\nHardFault at pc=0x1000\n",
            )
        )
        tail = recorder.wait_for_durable_tail(initial_tail, timeout_s=1)

        assert tail == DurableEvidenceTail(
            session_id=initial_tail.session_id,
            next_evidence_seq=initial_tail.next_evidence_seq + 1,
        )
        detail = store.get_session_detail(tail.session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.first_error is not None
        assert detail.first_error.pattern == "HardFault"
        assert (tmp_path / tail.session_id / "uart_raw.log").read_bytes() == (
            b"READY\nHardFault at pc=0x1000\n"
        )
        assert source.max_concurrent_reads == 1
    finally:
        recorder.close()


def test_delayed_hardfault_remains_recorded_after_an_idle_client_window(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    initial_tail = recorder.durable_tail()

    try:
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=10,
                channel=0,
                data=b"action response complete\n",
            )
        )
        client_window_tail = recorder.wait_for_durable_tail(initial_tail, timeout_s=1)
        assert client_window_tail is not None

        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=30_000_010,
                channel=0,
                data=b"HardFault after client returned\n",
            )
        )
        delayed_tail = recorder.wait_for_durable_tail(client_window_tail, timeout_s=1)

        assert delayed_tail is not None
        assert delayed_tail.session_id == client_window_tail.session_id
        detail = store.get_session_detail(delayed_tail.session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.first_error is not None
        assert detail.first_error.pattern == "HardFault"
    finally:
        recorder.close()


def test_telemetry_and_uart_share_one_contiguous_durable_order(tmp_path: Path) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    initial_tail = recorder.durable_tail()

    try:
        source.publish(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=1,
                size_bytes=32768,
                used_bytes=10,
                high_water_bytes=20,
                dropped_bytes_total=0,
                overflow_events=0,
            )
        )
        source.publish(
            BufferOverflowEvent(
                segment_id=0,
                timestamp_us=2,
                channel=0,
                dropped_bytes=7,
            )
        )
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=3,
                channel=0,
                data=b"still recording\n",
            )
        )

        tail = recorder.wait_for_durable_tail(
            DurableEvidenceTail(
                initial_tail.session_id,
                initial_tail.next_evidence_seq + 2,
            ),
            timeout_s=1,
        )

        assert tail is not None
        root = tmp_path / tail.session_id
        records = sorted(
            _read_jsonl(root / "connection_events.jsonl")
            + _read_jsonl(root / "hardware_events.jsonl")
            + _read_jsonl(root / "uart_events.jsonl"),
            key=lambda record: record["evidence_seq"],
        )
        assert [record["evidence_seq"] for record in records] == list(
            range(tail.next_evidence_seq)
        )
        assert [record["type"] for record in records] == [
            "connected",
            "buffer_status",
            "buffer_overflow",
            "uart_rx",
        ]
        metadata = store.load_metadata(tail.session_id)
        assert metadata["evidence_quality"]["backend_integrity"] == {  # type: ignore[index]
            "loss_status": "loss_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 7,
        }
        assert recorder.capture_source_health().integrity == UartIntegrity(
            loss_status="loss_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=7,
        )
    finally:
        recorder.close()


def test_oversized_line_fact_and_summary_are_persisted_with_uart(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    tail = recorder.durable_tail()

    try:
        for timestamp_us, data in (
            (1, b"a" * 32768),
            (2, b"a" * 32768),
            (3, b"x\n"),
        ):
            source.publish(
                UartReceiveEvent(
                    segment_id=0,
                    timestamp_us=timestamp_us,
                    channel=0,
                    data=data,
                )
            )
            updated = recorder.wait_for_durable_tail(tail, timeout_s=1)
            assert updated is not None
            tail = updated

        detail = store.get_session_detail(tail.session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.summary.line_processing.status == "limit_exceeded"
        assert detail.summary.line_processing.oversized_line_count == 1
        hardware = _read_jsonl(tmp_path / tail.session_id / "hardware_events.jsonl")
        assert [record["type"] for record in hardware] == ["line_limit_exceeded"]
        assert [record["evidence_seq"] for record in hardware] == [4]
    finally:
        recorder.close()


def test_rollover_does_not_join_partial_lines_across_sessions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    initial = recorder.durable_tail()

    try:
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=1,
                channel=0,
                data=b"Hard",
            )
        )
        before_rollover = recorder.wait_for_durable_tail(initial, timeout_s=1)
        assert before_rollover is not None

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
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=2,
                channel=0,
                data=b"Fault\n",
            )
        )
        after_rollover = recorder.wait_for_durable_tail(before_rollover, timeout_s=1)

        assert after_rollover is not None
        assert after_rollover.session_id != before_rollover.session_id
        detail = store.get_session_detail(after_rollover.session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.first_error is None
        assert json.loads(
            (tmp_path / after_rollover.session_id / "detected_patterns.json").read_text(
                encoding="utf-8"
            )
        ) == []
    finally:
        recorder.close()


def test_rollover_flushes_one_unterminated_oversized_line_fact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    tail = recorder.durable_tail()

    try:
        for timestamp_us, data in (
            (1, b"a" * 32768),
            (2, b"a" * 32768),
            (3, b"x"),
        ):
            source.publish(UartReceiveEvent(0, timestamp_us, 0, data))
            updated = recorder.wait_for_durable_tail(tail, timeout_s=1)
            assert updated is not None
            tail = updated

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
        source.publish(UartReceiveEvent(0, 4, 0, b"\n"))
        successor = recorder.wait_for_durable_tail(tail, timeout_s=1)

        assert successor is not None
        assert successor.session_id != tail.session_id
        facts = _read_jsonl(
            tmp_path / successor.session_id / "hardware_events.jsonl"
        )
        assert [fact["type"] for fact in facts] == ["line_limit_exceeded"]
        assert facts[0]["terminated"] is False
        assert facts[0]["total_line_bytes"] == 65537
    finally:
        recorder.close()


def test_telemetry_triggered_rollover_does_not_join_partial_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    tail = recorder.durable_tail()

    try:
        source.publish(UartReceiveEvent(0, 1, 0, b"Hard"))
        updated = recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert updated is not None
        tail = updated
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
        source.publish(
            BufferStatusEvent(
                segment_id=0,
                timestamp_us=2,
                size_bytes=32768,
                used_bytes=0,
                high_water_bytes=0,
                dropped_bytes_total=0,
                overflow_events=0,
            )
        )
        successor = recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert successor is not None
        assert successor.session_id != tail.session_id
        source.publish(UartReceiveEvent(0, 3, 0, b"Fault\n"))
        assert recorder.wait_for_durable_tail(successor, timeout_s=1) is not None

        detail = store.get_session_detail(successor.session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.first_error is None
    finally:
        recorder.close()


def test_rollover_rebuilds_session_local_integrity_projection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    initial = recorder.durable_tail()

    try:
        source.publish(
            BufferOverflowEvent(
                segment_id=0,
                timestamp_us=1,
                channel=0,
                dropped_bytes=7,
            )
        )
        before_rollover = recorder.wait_for_durable_tail(initial, timeout_s=1)
        assert before_rollover is not None
        assert recorder.capture_source_health().integrity == UartIntegrity(
            "loss_reported",
            "debug_helper_rx_buffer",
            7,
        )

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
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=2,
                channel=0,
                data=b"successor\n",
            )
        )
        successor = recorder.wait_for_durable_tail(before_rollover, timeout_s=1)

        assert successor is not None
        assert successor.session_id != before_rollover.session_id
        metadata = store.load_metadata(successor.session_id)
        assert metadata["evidence_quality"]["backend_integrity"] == {  # type: ignore[index]
            "loss_status": "none_reported",
            "observation_scope": "debug_helper_rx_buffer",
            "dropped_bytes": 0,
        }
        assert recorder.capture_source_health().integrity == UartIntegrity(
            "none_reported",
            "debug_helper_rx_buffer",
            0,
        )
    finally:
        recorder.close()


def test_replacement_source_continues_same_session_with_new_segment(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    replacement = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )

    try:
        source.publish(BackendDisconnectedError("removed"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect(idle=True)
        recorder.replace_source(replacement, backend_snapshot=_snapshot())
        before = recorder.durable_tail()
        replacement.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=8,
                channel=0,
                data=b"after reconnect\n",
            )
        )

        tail = recorder.wait_for_durable_tail(before, timeout_s=1)

        assert tail is not None
        assert tail.session_id == before.session_id
        uart = _read_jsonl(tmp_path / tail.session_id / "uart_events.jsonl")
        assert uart[-1]["segment_id"] == 1
        metadata = store.load_metadata(tail.session_id)
        assert [segment["segment_id"] for segment in metadata["segments"]] == [0, 1]  # type: ignore[union-attr]
        assert metadata["continuity"] == {"observation_gap_count": 1}
        connection_types = [
            record["type"]
            for record in _read_jsonl(
                tmp_path / tail.session_id / "connection_events.jsonl"
            )
        ]
        assert connection_types == [
            "connected",
            "unexpected_disconnect",
            "reconnect_started",
            "segment_opened",
            "reconnect_succeeded",
        ]
        first_segment = metadata["segments"][0]  # type: ignore[index]
        assert first_segment["ended_at"] is not None
        assert first_segment["end_reason"] == "unexpected_disconnect"
    finally:
        recorder.close()


def test_reconnect_timeout_records_failure_and_disconnects_service_state(
    tmp_path: Path,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    session_id = recorder.active_session_id

    source.publish(BackendDisconnectedError("removed"))
    assert recorder.wait_for_disconnect(timeout_s=1)
    recorder.close_current_source_for_reconnect(idle=True)
    recorder.reconnect_timed_out()

    metadata = store.load_metadata(session_id)
    assert recorder.state == "disconnected"
    assert recorder.capture_source_health().connected is False
    assert metadata["state"] == "failed"
    assert metadata["end_reason"] == "reconnect_timeout"
    assert metadata["error"]["code"] == "reconnect_timeout"  # type: ignore[index]
    assert [
        record["type"]
        for record in _read_jsonl(tmp_path / session_id / "connection_events.jsonl")
    ] == [
        "connected",
        "unexpected_disconnect",
        "reconnect_started",
        "reconnect_failed",
    ]
    recorder.close()


def test_persistence_fault_closes_source_and_fails_ownership(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    original_append = persistence.append_serialized

    def fail_uart_append(path: Path, payload: bytes) -> None:
        if path.name == "uart_events.jsonl":
            raise SessionPersistenceError(
                operation="append test evidence",
                path=path,
                detail="disk full",
            )
        original_append(path, payload)

    monkeypatch.setattr(persistence, "append_serialized", fail_uart_append)
    source.publish(
        UartReceiveEvent(
            segment_id=0,
            timestamp_us=1,
            channel=0,
            data=b"lost locally\n",
        )
    )

    assert recorder.wait_for_fault(timeout_s=1)
    assert source.closed is True
    metadata = store.load_metadata(recorder.active_session_id)
    assert metadata["state"] == "failed"
    assert metadata["end_reason"] == "persistence_error"
    assert metadata["evidence_quality"]["local_recording"] == "persistence_fault"  # type: ignore[index]
    recorder.close()


def test_shutdown_flushes_and_terminalizes_active_v2_session(tmp_path: Path) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    session_id = recorder.active_session_id

    recorder.close()

    metadata = store.load_metadata(session_id)
    assert metadata["state"] == "completed"
    assert metadata["end_reason"] == "service_shutdown"


def test_shutdown_drains_all_normalized_events_before_terminalizing(tmp_path: Path) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    session_id = recorder.active_session_id
    for timestamp_us, data in ((1, b"one\n"), (2, b"two\n"), (3, b"three\n")):
        source.publish(
            UartReceiveEvent(
                segment_id=0,
                timestamp_us=timestamp_us,
                channel=0,
                data=data,
            )
        )

    recorder.close()

    assert (tmp_path / session_id / "uart_raw.log").read_bytes() == b"one\ntwo\nthree\n"
    assert store.load_metadata(session_id)["state"] == "completed"


def test_shutdown_flushes_one_unterminated_oversized_line_fact(tmp_path: Path) -> None:
    source = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    session_id = recorder.active_session_id
    tail = recorder.durable_tail()
    source.publish(
        UartReceiveEvent(
            segment_id=0,
            timestamp_us=1,
            channel=0,
            data=b"a" * 32768,
        )
    )
    updated = recorder.wait_for_durable_tail(tail, timeout_s=1)
    assert updated is not None
    source.publish(
        UartReceiveEvent(
            segment_id=0,
            timestamp_us=2,
            channel=0,
            data=b"a" * 32768,
        )
    )
    updated = recorder.wait_for_durable_tail(updated, timeout_s=1)
    assert updated is not None
    source.publish(
        UartReceiveEvent(
            segment_id=0,
            timestamp_us=3,
            channel=0,
            data=b"x",
        )
    )
    assert recorder.wait_for_durable_tail(updated, timeout_s=1) is not None

    recorder.close()

    facts = _read_jsonl(tmp_path / session_id / "hardware_events.jsonl")
    assert [fact["type"] for fact in facts] == ["line_limit_exceeded"]
    assert facts[0]["terminated"] is False
    assert facts[0]["total_line_bytes"] == 65537


def test_disconnect_flushes_partial_state_before_replacement(tmp_path: Path) -> None:
    source = ControlledSource()
    replacement = ControlledSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    tail = recorder.durable_tail()

    try:
        source.publish(UartReceiveEvent(0, 1, 0, b"Hard"))
        tail = recorder.wait_for_durable_tail(tail, timeout_s=1)
        assert tail is not None
        source.publish(BackendDisconnectedError("removed"))
        assert recorder.wait_for_disconnect(timeout_s=1)
        recorder.close_current_source_for_reconnect(idle=True)
        recorder.replace_source(replacement, backend_snapshot=_snapshot())
        tail = recorder.durable_tail()
        replacement.publish(UartReceiveEvent(0, 2, 0, b"Fault\n"))
        assert recorder.wait_for_durable_tail(tail, timeout_s=1) is not None

        detail = store.get_session_detail(recorder.active_session_id)
        assert isinstance(detail, V2SessionDetail)
        assert detail.first_error is None
    finally:
        recorder.close()


def test_shutdown_terminalizes_after_source_close_error(tmp_path: Path) -> None:
    source = CloseErrorSource()
    store = SessionStore(root=tmp_path)
    recorder = ContinuousEvidenceRecorder(
        source=source,
        session_store=store,
        profile=_profile(),
        backend_snapshot=_snapshot(),
    )
    session_id = recorder.active_session_id

    with pytest.raises(RuntimeError, match="source close failed"):
        recorder.close()

    assert not recorder._thread.is_alive()  # noqa: SLF001
    metadata = store.load_metadata(session_id)
    assert metadata["state"] == "completed"
    assert metadata["end_reason"] == "service_shutdown"
