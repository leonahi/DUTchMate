from pathlib import Path

from runtime_test_support import FakeCaptureSource, FakeMonotonicClock, FakeTransport, enhanced_info

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.backends.enhanced import EnhancedDeviceControl
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import ReconnectedCaptureSource


def test_runtime_close_closes_current_source_once(tmp_path: Path) -> None:
    """Catch a close that leaves the source owned or repeats source shutdown."""

    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )

    runtime.close()
    runtime.close()

    assert source.close_count == 1


def test_runtime_close_owns_reconnect_replacement_without_reclosing_original(
    tmp_path: Path,
) -> None:
    """Catch shutdown retaining the pre-reconnect source instead of its replacement."""

    clock = FakeMonotonicClock()
    initial = FakeCaptureSource([], clock=clock)
    replacement = FakeCaptureSource([], clock=clock)
    snapshot = _replacement_snapshot(segment_id=1)
    replacement.segment = snapshot.segment

    def reconnect(*, segment_id: int, deadline: float) -> ReconnectedCaptureSource:
        assert segment_id == 1
        assert deadline == 10.0
        initial.close()
        return ReconnectedCaptureSource(source=replacement, backend_snapshot=snapshot)

    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        message_source=initial,
        session_store=SessionStore(root=tmp_path),
        backend_reconnect=reconnect,
    )

    assert (
        runtime._reconnect_capture_source(  # noqa: SLF001 - exercises replacement ownership.
            expected_snapshot=snapshot,
            segment_id=1,
            deadline=10.0,
        )
        is not None
    )

    runtime.close()

    assert initial.close_count == 1
    assert replacement.close_count == 1


def _replacement_snapshot(segment_id: int) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=enhanced_info(port="/dev/ttyACM0"),
        capabilities=frozenset({"gpio_control", "uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=10_000,
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
