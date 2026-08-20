from datetime import datetime, timezone
from pathlib import Path

import pytest
from session_store_support import enhanced_snapshot

from dutchmate_core.backends import UartReceiveEvent
from dutchmate_core.session_store.models import SessionHandle, SessionQueryError
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.uart_capture.line_buffer import MAX_UART_LINE_BYTES
from dutchmate_core.uart_capture.processor import UartCaptureProcessor


def test_recent_logs_replays_complete_partial_and_oversized_records(tmp_path: Path) -> None:
    store, handle = _native_store(tmp_path, suffix="replay")
    processor = UartCaptureProcessor()
    events = (
        UartReceiveEvent(0, 10, 0, b"older\nnew"),
        UartReceiveEvent(0, 20, 0, b"est\npartial"),
        UartReceiveEvent(0, 30, 1, b"x" * (MAX_UART_LINE_BYTES + 1) + b"\n"),
    )
    for event in events:
        store.append_uart_capture(
            handle,
            event=event,
            result=processor.process_event(event),
        )
    store.complete_session(handle)

    logs = store.replay_recent_logs(session_id=handle.session_id, lines=1)

    assert logs.session_selection == "explicit"
    assert logs.active is False
    assert logs.snapshot_event_count == 3
    assert [line.line_text for line in logs.complete_lines] == ["newest\n"]
    assert logs.complete_lines[0].line_raw_b64 == "bmV3ZXN0Cg=="
    assert logs.complete_lines[0].timestamp_us == 20
    assert logs.complete_lines[0].ingestion_index == 1
    assert logs.omitted_complete_lines == 1
    assert [line.line_text for line in logs.partial_lines] == ["partial"]
    assert logs.partial_lines[0].partial is True
    assert logs.partial_lines[0].timestamp_us == 20
    assert len(logs.oversized_lines) == 1
    assert logs.oversized_lines[0].total_line_bytes == MAX_UART_LINE_BYTES + 2
    assert logs.oversized_lines[0].terminated is True
    assert [segment["segment_id"] for segment in logs.timestamp_provenance] == [0]


def test_recent_logs_prefers_active_then_latest_terminal_native(tmp_path: Path) -> None:
    terminal_store, terminal = _native_store(tmp_path, second=0, suffix="terminal")
    terminal_store.complete_session(terminal)
    active_store, active = _native_store(tmp_path, second=1, suffix="active")

    active_logs = active_store.replay_recent_logs(active_session_id=active.session_id)
    terminal_logs = active_store.replay_recent_logs(active_session_id=terminal.session_id)

    assert active_logs.session_selection == "active"
    assert active_logs.session_id == active.session_id
    assert active_logs.active is True
    assert terminal_logs.session_selection == "latest_terminal"
    assert terminal_logs.session_id == terminal.session_id


def test_recent_logs_rejects_legacy_and_malformed_complete_uart_evidence(
    tmp_path: Path,
) -> None:
    legacy = SessionStore(
        root=tmp_path,
        clock=lambda: datetime(2026, 8, 21, tzinfo=timezone.utc),
        id_factory=lambda: "legacy",
    ).create_session(command="capture")
    with pytest.raises(SessionQueryError) as unsupported:
        SessionStore(root=tmp_path).replay_recent_logs(session_id=legacy.session_id)
    assert unsupported.value.error == "unsupported_session_schema"
    assert unsupported.value.operation == "get_logs"
    assert unsupported.value.detected_schema_version == 0

    store, handle = _native_store(tmp_path, second=1, suffix="corrupt")
    handle.paths.uart_events.write_bytes(b'{"type":"uart"}\n')
    store.complete_session(handle)
    with pytest.raises(SessionQueryError) as corrupt:
        store.replay_recent_logs(session_id=handle.session_id)
    assert corrupt.value.error == "persistence_fault"
    assert corrupt.value.operation == "get_logs"


@pytest.mark.parametrize("lines", [0, 1001, True])
def test_recent_logs_rejects_invalid_line_limit(tmp_path: Path, lines: object) -> None:
    with pytest.raises(ValueError, match="1 to 1000"):
        SessionStore(root=tmp_path).replay_recent_logs(lines=lines)  # type: ignore[arg-type]


def _native_store(
    root: Path,
    *,
    second: int = 0,
    suffix: str,
) -> tuple[SessionStore, SessionHandle]:
    store = SessionStore(
        root=root,
        clock=lambda: datetime(2026, 8, 21, 12, 0, second, tzinfo=timezone.utc),
        id_factory=lambda: suffix,
    )
    handle = store.create_session(
        command="capture --seconds 1",
        backend_snapshot=enhanced_snapshot(),
        workflow="capture",
        duration_s=1.0,
        reconnect_timeout_s=5.0,
    )
    return store, handle
