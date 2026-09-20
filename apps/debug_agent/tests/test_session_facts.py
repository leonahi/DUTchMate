from __future__ import annotations

import json
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    BufferStatusEvent,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartReceiveEvent,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.models import SessionQueryError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_core.validation import InputValidationError
from dutchmate_debug_agent.session_facts import load_session_facts


def test_loads_bounded_native_facts_without_raw_artifacts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    event = UartReceiveEvent(segment_id=0, timestamp_us=10, channel=0, data=b"ERROR failed\n")
    store.append_uart_capture(
        handle,
        event=event,
        result=UartCaptureProcessor().process_event(event),
    )
    store.append_buffer_status(
        handle,
        event=BufferStatusEvent(
            segment_id=0,
            timestamp_us=20,
            size_bytes=32768,
            used_bytes=10,
            high_water_bytes=20,
            dropped_bytes_total=0,
            overflow_events=0,
        ),
    )
    store.complete_session(handle)

    facts = load_session_facts(store, handle.session_id)
    payload = asdict(facts)

    assert facts.session_id == handle.session_id
    assert facts.schema_version == 1
    assert facts.command == "capture --seconds 1"
    assert facts.duration_s == 1.0
    assert facts.state == "completed"
    assert facts.error is None
    assert facts.commanded_boot_mode is None
    assert facts.backend_mode == "enhanced"
    assert facts.backend_identity["device"] == "dutchmate-rp2350"
    assert facts.backend_capabilities == ("gpio_control", "uart_receive", "uart_send")
    assert facts.capabilities == ("gpio_control", "uart_receive")
    assert facts.reconnect_timeout_s == 5.0
    assert facts.integrity.loss_status == "none_reported"
    assert facts.segments[0]["segment_id"] == 0
    assert facts.first_error is not None
    assert facts.first_error.match_excerpt.text == "ERROR failed\n"
    assert {count.type: count.count for count in facts.hardware_event_counts} == {
        "buffer_status": 1
    }
    assert facts.storage["evidence_budget_bytes"] > 0
    assert "artifacts" not in payload
    assert "uart_events" not in payload
    assert "hardware_events" not in payload
    json.dumps(payload)


def test_rejects_legacy_session_without_inferred_native_facts(tmp_path: Path) -> None:
    store = _store(tmp_path)
    handle = store.create_session(command="capture", firmware="0.0.1", device="legacy")

    with pytest.raises(SessionQueryError) as raised:
        load_session_facts(store, handle.session_id)

    assert raised.value.error == "unsupported_session_schema"
    assert raised.value.detected_schema_version == 0


def test_rejects_unknown_session_schema(tmp_path: Path) -> None:
    store = _store(tmp_path)
    handle = store.create_session(
        command="capture",
        backend_snapshot=_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["schema_version"] = 7
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(SessionQueryError) as raised:
        load_session_facts(store, handle.session_id)

    assert raised.value.error == "unsupported_session_schema"
    assert raised.value.detected_schema_version == 7


def test_rejects_path_traversal_session_id(tmp_path: Path) -> None:
    with pytest.raises(InputValidationError, match="path-safe"):
        load_session_facts(_store(tmp_path), "../other-session")


def _store(root: Path) -> SessionStore:
    return SessionStore(
        root=root,
        clock=lambda: datetime(2026, 7, 14, 12, 30, 45, tzinfo=timezone.utc),
        id_factory=lambda: "phase4-facts",
    )


def _snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
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
                source_origin_us=1000,
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
