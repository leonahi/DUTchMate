import json
from datetime import datetime, timezone
from pathlib import Path

import pytest
from runtime_test_support import (
    FakeCaptureSource,
    FakeDeviceControl,
    FakeMonotonicClock,
    enhanced_info,
)

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendDisconnectedError,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.models import NativeSessionDetail
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES
from dutchmate_core.workflows.capture import (
    CaptureSourceHealth,
    ReconnectedCaptureSource,
)
from dutchmate_core.workflows.device_actions import DeviceActionError


def test_wait_pattern_stops_after_persisting_complete_matching_event(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            UartReceiveEvent(0, 10, 0, b"REA"),
            UartReceiveEvent(0, 20, 0, b"DY\nafter\n"),
            UartReceiveEvent(0, 30, 0, b"unread\n"),
        ],
        clock=clock,
    )
    store = _store(tmp_path)
    runtime = _runtime(source, clock, store)

    result = runtime.wait_pattern(pattern="READY", timeout_s=2.0)

    assert result.matched is True
    assert result.summary.workflow == "wait_pattern"
    assert result.summary.duration_s is None
    assert result.summary.timeout_s == 2.0
    assert result.summary.wait_pattern == "READY"
    assert result.summary.match_mode == "literal"
    assert result.summary.case_sensitive is True
    assert result.summary.end_reason == "pattern_matched"
    assert result.summary.detected_pattern_index == 0
    assert result.match is not None
    assert result.match.pattern == "READY"
    assert result.match.match_excerpt.text == "READY\n"
    assert result.match.match_start_byte == 0
    assert result.match.match_end_byte == 5
    session_root = tmp_path / result.summary.session_id
    assert session_root.joinpath("uart_raw.log").read_bytes() == b"READY\nafter\n"
    patterns = json.loads(session_root.joinpath("detected_patterns.json").read_text())
    assert patterns[0]["pattern"] == "READY"
    detail = store.get_session_detail(result.summary.session_id)
    assert isinstance(detail, NativeSessionDetail)
    assert detail.wait_pattern == "READY"
    assert detail.timeout_s == 2.0
    assert detail.matched is True
    assert detail.detected_pattern_index == 0


def test_wait_pattern_timeout_is_successful_unmatched_terminal_session(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([None, None, None], clock=clock)
    store = _store(tmp_path)
    runtime = _runtime(source, clock, store)

    result = runtime.wait_pattern(pattern="never", timeout_s=0.25)

    assert result.matched is False
    assert result.match is None
    assert result.summary.state == "completed"
    assert result.summary.end_reason == "timeout"
    assert result.summary.detected_pattern_index is None
    metadata = store.load_metadata(result.summary.session_id)
    assert metadata["matched"] is False
    assert metadata["timeout_s"] == 0.25


def test_wait_pattern_discards_pre_cursor_events_and_uses_empty_local_buffer(
    tmp_path: Path,
) -> None:
    class CursorSource(FakeCaptureSource):
        def discard_pending_events(self) -> None:
            self._script.pop(0)

    clock = FakeMonotonicClock()
    source = CursorSource(
        [
            UartReceiveEvent(0, 1, 0, b"READY\npre"),
            UartReceiveEvent(0, 2, 0, b"READY\n"),
        ],
        clock=clock,
    )
    store = _store(tmp_path)
    runtime = _runtime(source, clock, store)

    result = runtime.wait_pattern(pattern="READY", timeout_s=1.0)

    assert result.matched is True
    session_root = tmp_path / result.summary.session_id
    assert session_root.joinpath("uart_raw.log").read_bytes() == b"READY\n"
    assert result.match is not None and result.match.ingestion_index == 0


def test_wait_pattern_excludes_oversized_lines_and_persists_default_matches(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource(
        [
            UartReceiveEvent(
                0,
                1,
                0,
                b"READY" + b"x" * MAX_UART_LINE_BYTES + b"\n",
            ),
            UartReceiveEvent(0, 2, 0, b"ERROR READY\n"),
        ],
        clock=clock,
    )
    result = _runtime(source, clock, _store(tmp_path)).wait_pattern(
        pattern="READY",
        timeout_s=1.0,
    )

    assert result.matched is True
    assert result.match is not None and result.match.ingestion_index == 1
    assert result.summary.line_processing.status == "limit_exceeded"
    assert result.summary.line_processing.oversized_line_count == 1
    assert result.summary.first_error is not None
    assert result.summary.first_error.pattern == "ERROR"
    assert result.summary.first_error.detected_pattern_index == 1


def test_wait_pattern_never_joins_requested_literal_across_reconnect(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    initial = FakeCaptureSource(
        [
            UartReceiveEvent(0, 1, 0, b"REA"),
            BackendDisconnectedError("removed"),
        ],
        clock=clock,
    )
    replacement = FakeCaptureSource(
        [UartReceiveEvent(1, 2, 0, b"DY\n")],
        clock=clock,
    )
    replacement.segment = SegmentContext(
        segment_id=1,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2040_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=100,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )
    snapshot = BackendSnapshot(
        info=enhanced_info(),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
        ),
        segment=replacement.segment,
        integrity=UartIntegrity(
            loss_status="none_reported",
            observation_scope="debug_helper_rx_buffer",
            dropped_bytes=0,
        ),
    )

    def reconnect(*, segment_id: int, deadline: float) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline > 0
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=snapshot)

    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=initial,
        capture_clock=clock,
        session_store=_store(tmp_path),
        backend_reconnect=reconnect,
    )
    runtime.record_backend_connection(enhanced_info())

    result = runtime.wait_pattern(pattern="READY", timeout_s=0.6)

    assert result.matched is False
    assert result.summary.interrupted is True
    assert result.summary.resumed is True
    assert result.summary.segment_count == 2


@pytest.mark.parametrize(
    ("pattern", "timeout_s"),
    [("", 1.0), ("x" * 257, 1.0), ("bad\npattern", 1.0), ("ok", True)],
)
def test_wait_pattern_validates_before_capability_or_connection(
    tmp_path: Path,
    pattern: object,
    timeout_s: object,
) -> None:
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        session_store=_store(tmp_path),
    )

    with pytest.raises(ValueError):
        runtime.wait_pattern(  # type: ignore[arg-type]
            pattern=pattern,
            timeout_s=timeout_s,
        )
    assert not tuple(tmp_path.iterdir())


def test_wait_pattern_requires_effective_uart_receive_before_session_creation(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        capture_clock=clock,
        session_store=_store(tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(capabilities=frozenset()))

    with pytest.raises(DeviceActionError) as error:
        runtime.wait_pattern(pattern="READY", timeout_s=1.0)
    assert error.value.error == "unsupported_capability"
    assert error.value.context == {
        "operation": "wait_pattern",
        "backend_mode": "enhanced",
        "required_capabilities": ["uart_receive"],
        "available_capabilities": [],
        "backend_capabilities": [],
        "disabled_by_policy": [],
    }
    assert not tuple(tmp_path.iterdir())


def test_wait_pattern_reconciles_idle_reconnect_before_capability_admission(
    tmp_path: Path,
) -> None:
    """Catch capability admission before newer connected monitor health is adopted."""

    class MonitoredSource(FakeCaptureSource):
        def __init__(self, *, clock: FakeMonotonicClock) -> None:
            super().__init__(
                [UartReceiveEvent(1, 100, 0, b"READY\n")],
                clock=clock,
            )
            self.health = CaptureSourceHealth(False, None)

        def capture_source_health(self) -> CaptureSourceHealth:
            return self.health

    clock = FakeMonotonicClock()
    source = MonitoredSource(clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        capture_clock=clock,
        session_store=_store(tmp_path),
    )
    runtime.record_backend_connection(enhanced_info(capabilities=frozenset()))
    replacement = BackendSnapshot(
        info=enhanced_info(),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False)
        ),
        segment=SegmentContext(
            segment_id=1,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=100,
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
    source.segment = replacement.segment
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=replacement.integrity,
        backend_snapshot=replacement,
        connection_generation=1,
    )

    result = runtime.wait_pattern(pattern="READY", timeout_s=1.0)

    assert result.matched is True
    assert runtime.status().backend_capabilities == tuple(
        sorted(replacement.info.capabilities)
    )
    runtime.close()


def _store(root: Path) -> SessionStore:
    return SessionStore(
        root=root,
        clock=lambda: datetime(2026, 8, 21, 12, 0, tzinfo=timezone.utc),
        id_factory=lambda: "wait",
    )


def _runtime(
    source: FakeCaptureSource,
    clock: FakeMonotonicClock,
    store: SessionStore,
) -> DeviceCoreRuntime:
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        capture_clock=clock,
        session_store=store,
    )
    runtime.record_backend_connection(enhanced_info())
    return runtime
