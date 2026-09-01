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
    BackendInfo,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.runtime import DeviceCoreRuntime, DeviceCoreRuntimeError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.workflows.capture import CaptureSourceHealth


class MutableHealthSource:
    def __init__(self, health: CaptureSourceHealth) -> None:
        self.health = health
        self.close_count = 0
        self.segment = SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=0,
                observation_point="debug_helper_uart_receive",
                event_granularity="uart_event",
            ),
        )

    def read_event(self) -> None:
        return None

    def capture_source_health(self) -> CaptureSourceHealth:
        return self.health

    def close(self) -> None:
        self.close_count += 1


def monitored_runtime(
    tmp_path: Path,
    source: MutableHealthSource,
    *,
    clock: FakeMonotonicClock | None = None,
) -> DeviceCoreRuntime:
    return DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )


def replacement_snapshot(
    *,
    segment_id: int,
    tx_policy_enabled: bool = False,
) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=tx_policy_enabled)
    )
    info = enhanced_info(port="/dev/ttyACM0")
    return BackendSnapshot(
        info=info,
        capabilities=(
            info.capabilities
            if tx_policy_enabled
            else frozenset({"gpio_control", "uart_receive"})
        ),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=segment_id,
            timestamp=SegmentTimestamp(
                source="device",
                clock="rp2040_timer",
                unit="us",
                origin="segment_start",
                source_origin_us=segment_id * 10_000,
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


def test_status_reconciles_idle_terminal_and_clears_connection_state(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    runtime._commanded_boot_mode = "bootloader"  # noqa: SLF001 - invalidation proof.
    source.health = CaptureSourceHealth(False, None)

    status = runtime.status()

    assert status.connected is False
    assert status.connection_state == "disconnected"
    assert status.commanded_boot_mode is None
    assert status.firmware is None
    assert status.device is None
    assert status.backend_capabilities == ()
    assert status.capabilities == ()
    assert status.timestamp_provenance is None
    assert status.integrity is None
    runtime.close()


def test_connection_required_operation_reconciles_before_admission(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    source.health = CaptureSourceHealth(False, None)

    with pytest.raises(DeviceCoreRuntimeError, match="not connected"):
        runtime.capture_uart(duration_s=0.1)

    assert runtime.status().active_session_id is None
    runtime.close()


def test_connected_enhanced_monitor_updates_live_integrity(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    expected = UartIntegrity("loss_reported", "debug_helper_rx_buffer", 12)
    source.health = CaptureSourceHealth(True, expected)

    assert runtime.status().integrity == expected
    runtime.close()


def test_basic_monitor_without_integrity_stays_not_observable(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(
        BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            firmware=None,
            device=None,
            capabilities=frozenset({"uart_receive"}),
        )
    )

    assert runtime.status().integrity == UartIntegrity("not_observable", None, None)
    runtime.close()


def test_connected_monitor_cannot_restore_disconnected_runtime(tmp_path: Path) -> None:
    expected = UartIntegrity("loss_reported", "debug_helper_rx_buffer", 3)
    source = MutableHealthSource(CaptureSourceHealth(True, expected))
    runtime = monitored_runtime(tmp_path, source)
    runtime.record_backend_connection(enhanced_info())
    runtime.disconnect()

    status = runtime.status()

    assert status.connected is False
    assert status.connection_state == "disconnected"
    assert status.integrity is None
    runtime.close()


def test_newer_connection_generation_adopts_validated_backend_snapshot(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(False, None))
    runtime = monitored_runtime(tmp_path, source)
    replacement = replacement_snapshot(segment_id=1)
    source.segment = replacement.segment
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=replacement.integrity,
        backend_snapshot=replacement,
        connection_generation=1,
    )

    status = runtime.status()

    assert status.connected is True
    assert status.backend_capabilities == tuple(sorted(replacement.info.capabilities))
    assert status.timestamp_provenance == replacement.segment

    source.health = CaptureSourceHealth(
        connected=False,
        integrity=None,
        backend_snapshot=replacement,
        connection_generation=1,
    )
    assert runtime.status().connected is False

    source.health = CaptureSourceHealth(
        connected=True,
        integrity=replacement.integrity,
        backend_snapshot=replacement,
        connection_generation=1,
    )
    assert runtime.status().connected is False

    replacement = replacement_snapshot(segment_id=2)
    source.segment = replacement.segment
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=replacement.integrity,
        backend_snapshot=replacement,
        connection_generation=2,
    )

    status = runtime.status()

    assert status.connected is True
    assert status.backend_capabilities == tuple(sorted(replacement.info.capabilities))
    assert status.timestamp_provenance == replacement.segment
    runtime.close()


def test_older_connection_generation_cannot_restore_after_newer_adoption(
    tmp_path: Path,
) -> None:
    source = MutableHealthSource(CaptureSourceHealth(False, None))
    runtime = monitored_runtime(tmp_path, source)
    newer = replacement_snapshot(segment_id=2)
    source.segment = newer.segment
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=newer.integrity,
        backend_snapshot=newer,
        connection_generation=2,
    )
    assert runtime.status().connected is True

    source.health = CaptureSourceHealth(
        connected=False,
        integrity=None,
        backend_snapshot=newer,
        connection_generation=2,
    )
    assert runtime.status().connected is False

    older = replacement_snapshot(segment_id=1)
    source.segment = older.segment
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=older.integrity,
        backend_snapshot=older,
        connection_generation=1,
    )

    status = runtime.status()

    assert status.connected is False
    assert status.integrity is None
    runtime.close()


def test_connection_generation_rejects_changed_capability_policy(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(False, None))
    runtime = monitored_runtime(tmp_path, source)
    replacement = replacement_snapshot(segment_id=1, tx_policy_enabled=True)
    source.health = CaptureSourceHealth(
        connected=True,
        integrity=replacement.integrity,
        backend_snapshot=replacement,
        connection_generation=1,
    )

    with pytest.raises(ValueError, match="reconnected backend capability policy changed"):
        runtime.status()

    runtime.close()


def test_active_reconnect_rejects_changed_effective_capabilities(tmp_path: Path) -> None:
    source = MutableHealthSource(CaptureSourceHealth(False, None))
    runtime = monitored_runtime(tmp_path, source)
    expected = replacement_snapshot(segment_id=0)
    replacement = BackendSnapshot(
        info=enhanced_info(capabilities=frozenset({"uart_receive"})),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=expected.capability_policy,
        segment=replacement_snapshot(segment_id=1).segment,
        integrity=expected.integrity,
    )

    with pytest.raises(ValueError, match="reconnected backend capabilities changed"):
        runtime._validate_replacement(expected, replacement)  # noqa: SLF001

    runtime.close()


def test_capture_source_health_rejects_negative_connection_generation() -> None:
    with pytest.raises(ValueError, match="source connection generation must be non-negative"):
        CaptureSourceHealth(True, None, connection_generation=-1)


def test_plain_capture_source_remains_compatible(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = FakeCaptureSource([], clock=clock)
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        capture_clock=clock,
        session_store=SessionStore(root=tmp_path),
    )
    runtime.record_backend_connection(enhanced_info())

    assert runtime.status().connected is True
    runtime.close()


def test_disconnected_monitor_does_not_erase_reconnect_deadline(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    source = MutableHealthSource(CaptureSourceHealth(True, None))
    runtime = monitored_runtime(tmp_path, source, clock=clock)
    runtime.record_backend_connection(enhanced_info())
    runtime._reconnect_deadline = 10.0  # noqa: SLF001 - precedence assertion.
    source.health = CaptureSourceHealth(False, None)

    status = runtime.status()

    assert status.connected is False
    assert status.connection_state == "reconnecting"
    assert status.reconnect_remaining_s == 10.0
    runtime._reconnect_deadline = None  # noqa: SLF001 - test cleanup.
    runtime.close()
