import json
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot, fixed_clock, fixed_id

import dutchmate_core.session_store.persistence as persistence
from dutchmate_core.backends import (
    BufferOverflowEvent,
    SegmentContext,
    SegmentTimestamp,
    UartReceiveEvent,
)
from dutchmate_core.session_store.models import SessionPersistenceError
from dutchmate_core.session_store.store import SessionHandle, SessionStore, SessionSummary
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def test_create_session_initializes_required_files(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2350",
    )

    assert handle == SessionHandle(
        session_id="20260714T123045Z-abc12345",
        paths=handle.paths,
    )
    assert handle.paths.root == tmp_path / "20260714T123045Z-abc12345"
    assert handle.paths.metadata.exists()
    assert handle.paths.uart_raw.read_bytes() == b""


def test_wait_session_stores_policy_and_requires_authoritative_match_index(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="wait-pattern",
        backend_snapshot=enhanced_snapshot(),
        workflow="wait_pattern",
        reconnect_timeout_s=5.0,
        wait_pattern="READY",
        timeout_s=2.0,
    )
    metadata = store.load_metadata(handle.session_id)

    assert metadata["duration_s"] is None
    assert metadata["pattern"] == "READY"
    assert metadata["match_mode"] == "literal"
    assert metadata["case_sensitive"] is True
    assert metadata["timeout_s"] == 2.0
    assert metadata["matched"] is None
    with pytest.raises(ValueError, match="out of range"):
        store.complete_wait_pattern(
            handle,
            matched=True,
            detected_pattern_index=0,
        )

    store.complete_wait_pattern(
        handle,
        matched=False,
        detected_pattern_index=None,
    )
    summary = store.summarize_session(handle.session_id)
    assert summary.end_reason == "timeout"
    assert summary.matched is False
    assert handle.paths.uart_events.read_text(encoding="utf-8") == ""
    assert handle.paths.hardware_events.read_text(encoding="utf-8") == ""
    assert json.loads(handle.paths.detected_patterns.read_text(encoding="utf-8")) == []


def test_create_session_writes_initial_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2350",
        baseline=True,
    )

    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8")) == {
        "session_id": "20260714T123045Z-abc12345",
        "started_at": "2026-07-14T12:30:45Z",
        "command": "boot-test --seconds 15",
        "truncated": False,
        "interrupted": False,
        "resumed": False,
        "overflow": False,
        "baseline": True,
        "firmware": "0.1.0",
        "device": "dutchmate-rp2350",
        "line_processing": {
            "status": "complete",
            "max_line_bytes": 65536,
            "oversized_line_count": 0,
        },
        "segments": [
            {
                "segment_id": 0,
                "started_at": "2026-07-14T12:30:45Z",
                "ended_at": None,
                "end_reason": None,
                "hello": None,
                "first_device_timestamp_us": None,
                "last_device_timestamp_us": None,
                "timestamp_epoch": 0,
            }
        ],
    }


def test_create_session_writes_backend_identity_policy_and_provenance(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="capture --seconds 1",
        firmware="0.1.0",
        device="dutchmate-rp2350",
        backend_snapshot=enhanced_snapshot(),
    )

    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["backend_mode"] == "enhanced"
    assert metadata["backend_identity"] == {
        "port": "/dev/ttyACM0",
        "device": "dutchmate-rp2350",
        "firmware": "0.1.0",
    }
    assert metadata["backend_capabilities"] == [
        "gpio_control",
        "uart_receive",
        "uart_send",
    ]
    assert metadata["capabilities"] == ["gpio_control", "uart_receive"]
    assert metadata["capability_policy"] == {
        "uart_send": {
            "tx_policy_enabled": False,
            "source": "hardware.uart.tx_enabled",
        }
    }
    assert metadata["integrity"] == {
        "loss_status": "none_reported",
        "observation_scope": "debug_helper_rx_buffer",
        "dropped_bytes": 0,
    }
    assert metadata["segments"][0]["timestamp"] == {
        "source": "device",
        "clock": "rp2350_timer",
        "unit": "us",
        "origin": "segment_start",
        "source_origin_us": 1_000,
        "observation_point": "debug_helper_uart_receive",
        "event_granularity": "uart_event",
    }

    summary = store.summarize_session(handle.session_id)
    assert summary.backend_mode == "enhanced"
    assert summary.port == "/dev/ttyACM0"
    assert summary.integrity == enhanced_snapshot().integrity
    assert summary.segment_contexts == (enhanced_snapshot().segment,)


def test_create_native_session_writes_active_schema_v1_and_terminal_reserve(
    tmp_path: Path,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(
        command="capture --seconds 2.5",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=2.5,
        reconnect_timeout_s=4.0,
        commanded_boot_mode="bootloader",
    )
    metadata = store.load_metadata(handle.session_id)
    summary = store.summarize_session(handle.session_id)

    assert metadata["schema_version"] == 1
    assert metadata["state"] == "active"
    assert metadata["workflow"] == "capture"
    assert metadata["duration_s"] == 2.5
    assert metadata["reconnect_timeout_s"] == 4.0
    assert metadata["ended_at"] is None
    assert metadata["end_reason"] is None
    assert metadata["error"] is None
    assert metadata["commanded_boot_mode"] == "bootloader"
    assert "firmware" not in metadata
    assert "device" not in metadata
    assert metadata["storage"] == {
        "evidence_budget_bytes": 50 * 1024 * 1024,
        "evidence_bytes_written": 3,
        "metadata_max_bytes": 262144,
    }
    assert handle.paths.terminal_reserve.stat().st_size == 262144
    assert summary.schema_version == 1
    assert summary.state == "active"
    assert summary.workflow == "capture"


def test_create_native_session_does_not_publish_metadata_when_reserve_write_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    real_write = persistence.write_serialized

    def fail_reserve(path: Path, data: bytes) -> None:
        if path.name == ".terminal-reserve":
            raise SessionPersistenceError(
                operation="write",
                path=path,
                detail="simulated storage failure",
            )
        real_write(path, data)

    monkeypatch.setattr(persistence, "write_serialized", fail_reserve)

    with pytest.raises(SessionPersistenceError, match="terminal-reserve"):
        store.create_session(
            command="capture --seconds 2.5",
            backend_snapshot=enhanced_snapshot(),
            workflow="capture",
            duration_s=2.5,
            reconnect_timeout_s=4.0,
        )

    session_root = tmp_path / "20260714T123045Z-abc12345"
    assert session_root.is_dir()
    assert not (session_root / "metadata.json").exists()


def test_complete_native_session_is_terminal_and_one_way(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.complete_session(handle)
    summary = store.summarize_session(handle.session_id)

    assert summary.state == "completed"
    assert summary.end_reason == "duration_elapsed"
    assert summary.ended_at == "2026-07-14T12:30:45Z"
    assert summary.error is None
    assert not handle.paths.terminal_reserve.exists()
    with pytest.raises(ValueError, match="requires active"):
        store.complete_session(handle)
    event = UartReceiveEvent(
        segment_id=0,
        channel=0,
        timestamp_us=1,
        data=b"late\n",
    )
    with pytest.raises(ValueError, match="only append while active"):
        store.append_uart_capture(
            handle,
            event=event,
            result=UartCaptureProcessor().process_event(event),
        )


def test_failed_native_session_sanitizes_and_bounds_error_detail(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="boot_test",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )

    store.fail_session(
        handle,
        end_reason="backend_error",
        error_code="hardware_fault",
        detail=("failed\n\t" + ("é" * 600)),
    )
    summary = store.summarize_session(handle.session_id)

    assert summary.state == "failed"
    assert summary.error is not None
    assert summary.error["code"] == "hardware_fault"
    assert summary.error["detail_truncated"] is True
    detail = summary.error["detail"]
    assert isinstance(detail, str)
    assert "\n" not in detail and "\t" not in detail
    assert len(detail.encode("utf-8")) <= 1024


def test_load_metadata_reads_metadata_json(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")

    metadata = store.load_metadata(handle.session_id)

    assert metadata["session_id"] == "20260714T123045Z-abc12345"
    assert metadata["command"] == "capture"


def test_summarize_session_reads_legacy_rp2040_identity_and_timer(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="capture",
        firmware="0.1.0",
        device="dutchmate-rp2040",
    )
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"][0]["timestamp"] = {
        "source": "device",
        "clock": "rp2040_timer",
        "unit": "us",
        "origin": "segment_start",
        "source_origin_us": 1_000,
        "observation_point": "debug_helper_uart_receive",
        "event_granularity": "uart_event",
    }
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    summary = store.summarize_session(handle.session_id)

    assert summary.device == "dutchmate-rp2040"
    assert summary.segment_contexts[0].timestamp.clock == "rp2040_timer"


def test_record_segment_context_sets_unknown_provenance_once(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    context = SegmentContext(
        segment_id=0,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=8_500,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )

    store.record_segment_context(handle, context)
    store.record_segment_context(handle, context)

    metadata = store.load_metadata(handle.session_id)
    assert metadata["segments"][0]["timestamp"]["source_origin_us"] == 8_500  # type: ignore[index]

    conflicting = SegmentContext(
        segment_id=0,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2350_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=9_000,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )
    with pytest.raises(ValueError, match="cannot change"):
        store.record_segment_context(handle, conflicting)


def test_summarize_session_returns_compact_metadata_summary(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(
        command="boot-test --seconds 15",
        firmware="0.1.0",
        device="dutchmate-rp2350",
        baseline=True,
    )

    summary = store.summarize_session(handle.session_id)

    assert summary == SessionSummary(
        session_id="20260714T123045Z-abc12345",
        started_at="2026-07-14T12:30:45Z",
        command="boot-test --seconds 15",
        truncated=False,
        interrupted=False,
        resumed=False,
        overflow=False,
        baseline=True,
        firmware="0.1.0",
        device="dutchmate-rp2350",
        segment_count=1,
    )


def test_summarize_session_reflects_metadata_updates(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["interrupted"] = True
    metadata["resumed"] = True
    metadata["truncated"] = True
    metadata["segments"].append(
        {
            "segment_id": 1,
            "started_at": "2026-07-14T12:31:00Z",
            "ended_at": None,
            "end_reason": None,
            "hello": None,
            "first_device_timestamp_us": None,
            "last_device_timestamp_us": None,
            "timestamp_epoch": 1,
        }
    )
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")
    store.append_buffer_overflow(
        handle,
        event=BufferOverflowEvent(
            segment_id=0,
            channel=0,
            timestamp_us=100,
            dropped_bytes=10,
        ),
    )

    summary = store.summarize_session(handle.session_id)

    assert summary.truncated is True
    assert summary.interrupted is True
    assert summary.resumed is True
    assert summary.overflow is True
    assert summary.segment_count == 2


def test_summarize_session_rejects_invalid_segments_metadata(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["segments"] = "not a list"
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError):
        store.summarize_session(handle.session_id)


def test_summarize_session_rejects_invalid_required_metadata_type(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    handle = store.create_session(command="capture")
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["overflow"] = "false"
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(ValueError):
        store.summarize_session(handle.session_id)


def test_create_session_defaults_optional_metadata_to_none_and_false(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    handle = store.create_session(command="capture")

    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    assert metadata["firmware"] is None
    assert metadata["device"] is None
    assert metadata["baseline"] is False


def test_create_session_requires_command(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)

    with pytest.raises(ValueError):
        store.create_session(command="")


def test_create_session_fails_if_generated_session_id_already_exists(tmp_path: Path) -> None:
    store = SessionStore(root=tmp_path, clock=fixed_clock, id_factory=fixed_id)
    store.create_session(command="capture")

    with pytest.raises(FileExistsError):
        store.create_session(command="capture")
