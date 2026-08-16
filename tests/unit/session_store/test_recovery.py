import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from dutchmate_core.backends import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendSnapshot,
    SegmentContext,
    SegmentTimestamp,
    UartIntegrity,
    UartSendCapabilityPolicy,
)
from dutchmate_core.session_store.store import (
    SessionHandle,
    SessionRecoveryError,
    SessionStore,
)


def _clock() -> datetime:
    return datetime(2026, 8, 16, 12, 0, tzinfo=timezone.utc)


def _recovery_clock() -> datetime:
    return datetime(2026, 8, 16, 12, 5, tzinfo=timezone.utc)


def _snapshot() -> BackendSnapshot:
    policy = BackendCapabilityPolicy(uart_send=UartSendCapabilityPolicy(tx_policy_enabled=False))
    return BackendSnapshot(
        info=BackendInfo(
            mode="basic",
            port="/dev/ttyUSB0",
            device=None,
            firmware=None,
            capabilities=frozenset({"uart_receive", "uart_send"}),
        ),
        capabilities=frozenset({"uart_receive"}),
        capability_policy=policy,
        segment=SegmentContext(
            segment_id=0,
            timestamp=SegmentTimestamp(
                source="host",
                clock="monotonic",
                unit="us",
                origin="segment_start",
                source_origin_us=100,
                observation_point="host_serial_read",
                event_granularity="serial_read_chunk",
            ),
        ),
        integrity=UartIntegrity(
            loss_status="not_observable",
            observation_scope=None,
            dropped_bytes=None,
        ),
    )


def _create_active_native(root: Path, *, suffix: str = "active") -> SessionHandle:
    return SessionStore(
        root=root,
        clock=_clock,
        id_factory=lambda: suffix,
    ).create_session(
        command="capture --seconds 5",
        backend_snapshot=_snapshot(),
        workflow="capture",
        duration_s=5.0,
        reconnect_timeout_s=5.0,
    )


def test_recovery_abandons_stale_active_native_session(tmp_path: Path) -> None:
    handle = _create_active_native(tmp_path)
    session_id = handle.session_id
    store = SessionStore(root=tmp_path, clock=_recovery_clock)

    result = store.recover_stale_sessions()
    summary = store.summarize_session(session_id)
    metadata = store.load_metadata(session_id)

    assert result.recovered_session_ids == (session_id,)
    assert result.diagnostics == ()
    assert store.last_recovery == result
    assert summary.state == "abandoned"
    assert summary.end_reason == "service_restart"
    assert summary.ended_at == "2026-08-16T12:05:00Z"
    assert summary.error is None
    assert metadata["segments"][0]["ended_at"] == "2026-08-16T12:05:00Z"  # type: ignore[index]
    assert not tmp_path.joinpath(session_id, ".terminal-reserve").exists()


def test_recovery_does_not_reopen_or_rewrite_terminal_native_session(tmp_path: Path) -> None:
    handle = _create_active_native(tmp_path)
    session_id = handle.session_id
    creating_store = SessionStore(root=tmp_path, clock=_clock)
    creating_store.complete_session(handle)
    metadata_path = tmp_path / session_id / "metadata.json"
    before = metadata_path.read_bytes()

    result = SessionStore(root=tmp_path, clock=_recovery_clock).recover_stale_sessions()

    assert result.recovered_session_ids == ()
    assert result.diagnostics == ()
    assert metadata_path.read_bytes() == before


def test_recovery_reports_but_does_not_mutate_legacy_or_unknown_schema(
    tmp_path: Path,
) -> None:
    legacy = SessionStore(root=tmp_path, clock=_clock, id_factory=lambda: "legacy")
    legacy_handle = legacy.create_session(command="capture")
    unknown_root = tmp_path / "20260816T120000Z-unknown"
    unknown_root.mkdir()
    unknown_metadata = unknown_root / "metadata.json"
    unknown_metadata.write_text(json.dumps({"schema_version": 7}), encoding="utf-8")
    malformed_root = tmp_path / "20260816T120000Z-malformed"
    malformed_root.mkdir()
    malformed_metadata = malformed_root / "metadata.json"
    malformed_metadata.write_text(json.dumps({"schema_version": False}), encoding="utf-8")
    legacy_before = legacy_handle.paths.metadata.read_bytes()
    unknown_before = unknown_metadata.read_bytes()
    malformed_before = malformed_metadata.read_bytes()

    result = SessionStore(root=tmp_path, clock=_recovery_clock).recover_stale_sessions()

    assert result.recovered_session_ids == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == [
        "legacy_session_skipped",
        "persistence_fault",
        "unsupported_session_schema",
    ]
    assert legacy_handle.paths.metadata.read_bytes() == legacy_before
    assert unknown_metadata.read_bytes() == unknown_before
    assert malformed_metadata.read_bytes() == malformed_before


@pytest.mark.parametrize(
    ("reserve_bytes", "diagnostic_code"),
    ((None, "terminal_reserve_missing"), (b"short", "terminal_reserve_invalid")),
)
def test_recovery_continues_when_terminal_reserve_is_missing_or_invalid(
    tmp_path: Path,
    reserve_bytes: bytes | None,
    diagnostic_code: str,
) -> None:
    handle = _create_active_native(tmp_path)
    session_id = handle.session_id
    reserve = tmp_path / session_id / ".terminal-reserve"
    reserve.unlink()
    if reserve_bytes is not None:
        reserve.write_bytes(reserve_bytes)

    store = SessionStore(root=tmp_path, clock=_recovery_clock)
    result = store.recover_stale_sessions()

    assert result.recovered_session_ids == (session_id,)
    assert [diagnostic.code for diagnostic in result.diagnostics] == [diagnostic_code]
    assert store.summarize_session(session_id).state == "abandoned"


def test_recovery_does_not_rewrite_malformed_active_lifecycle(tmp_path: Path) -> None:
    handle = _create_active_native(tmp_path)
    metadata = json.loads(handle.paths.metadata.read_text(encoding="utf-8"))
    metadata["ended_at"] = "2026-08-16T12:01:00Z"
    handle.paths.metadata.write_text(json.dumps(metadata), encoding="utf-8")

    result = SessionStore(root=tmp_path, clock=_recovery_clock).recover_stale_sessions()

    assert result.recovered_session_ids == ()
    assert [diagnostic.code for diagnostic in result.diagnostics] == ["persistence_fault"]
    assert json.loads(handle.paths.metadata.read_text(encoding="utf-8"))["state"] == "active"
    assert handle.paths.terminal_reserve.exists()


def test_recovery_raises_when_terminal_metadata_cannot_be_replaced(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    _create_active_native(tmp_path)

    def fail_replace(source: Path, target: Path) -> None:
        raise OSError("disk unavailable")

    monkeypatch.setattr("dutchmate_core.session_store.persistence.os.replace", fail_replace)

    with pytest.raises(SessionRecoveryError, match="failed to recover stale session"):
        SessionStore(root=tmp_path, clock=_recovery_clock).recover_stale_sessions()
