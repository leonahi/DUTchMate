import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import pytest
from runtime_test_support import FakeCaptureSource, FakeMonotonicClock, FakeTransport, enhanced_info

from dutchmate_core.backends import BackendUartSendResult, BackendWriteError, UartReceiveEvent
from dutchmate_core.backends.enhanced import EnhancedDeviceControl
from dutchmate_core.runtime import DeviceCoreRuntime
from dutchmate_core.session_store.models import (
    NativeSessionDetail,
    SessionHandle,
    SessionPersistenceError,
)
from dutchmate_core.session_store.store import SessionStore
from dutchmate_core.validation import UartSendValidationError
from dutchmate_core.workflows.uart_send import UartSendError


class FakeSender:
    def __init__(self, *outcomes: BackendUartSendResult | BackendWriteError) -> None:
        self.outcomes = list(outcomes)
        self.payloads: list[bytes] = []

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        self.payloads.append(data)
        if not self.outcomes:
            raise AssertionError("fake sender has no outcome")
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BackendWriteError):
            raise outcome
        return outcome


def test_standalone_send_appends_one_lf_and_creates_no_attempt(tmp_path: Path) -> None:
    sender = FakeSender(BackendUartSendResult(7, device_timestamp_us=1_250))
    runtime = _runtime(tmp_path, sender=sender)

    result = runtime.send_uart(cmd="reboot")

    assert sender.payloads == [b"reboot\n"]
    assert result.device_timestamp_us == 1_250
    assert result.attempt_id is None
    assert result.perturbation_logged is False
    assert result.performed_at == "2026-08-21T10:00:00Z"


@pytest.mark.parametrize(
    ("cmd", "append_newline", "expected"),
    [
        ("", True, b"\n"),
        ("go\n", True, b"go\n"),
        ("go\r\n", True, b"go\r\n"),
        ("go\r", True, b"go\r\n"),
        ("go", False, b"go"),
    ],
)
def test_send_payload_terminator_rules(
    tmp_path: Path,
    cmd: str,
    append_newline: bool,
    expected: bytes,
) -> None:
    sender = FakeSender(BackendUartSendResult(len(expected), device_timestamp_us=1_250))
    runtime = _runtime(tmp_path, sender=sender)

    runtime.send_uart(cmd=cmd, append_newline=append_newline)

    assert sender.payloads == [expected]


def test_invalid_send_precedes_capability_and_dispatch(tmp_path: Path) -> None:
    sender = FakeSender()
    runtime = _runtime(tmp_path, sender=sender, tx_enabled=False)

    with pytest.raises(UartSendValidationError) as raised:
        runtime.send_uart(cmd="x" * 1024)

    assert raised.value.actual_bytes == 1025
    assert raised.value.max_bytes == 1024
    assert sender.payloads == []


def test_tx_policy_reports_why_effective_capability_is_absent(tmp_path: Path) -> None:
    runtime = _runtime(tmp_path, sender=FakeSender(), tx_enabled=False)

    with pytest.raises(UartSendError, match="effective capability") as raised:
        runtime.send_uart(cmd="go")

    assert raised.value.error == "unsupported_capability"
    assert raised.value.context is not None
    assert raised.value.context["disabled_by_policy"] == ["hardware.uart.tx_enabled"]


def test_forced_send_records_attempt_before_dispatch_and_matching_result(
    tmp_path: Path,
) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender(BackendUartSendResult(3, device_timestamp_us=150))
    store = _store(tmp_path)
    sent_results = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        sent_results.append(runtime.send_uart(cmd="go", force=True))

    source = FakeCaptureSource(
        [UartReceiveEvent(0, 200, 0, b"ready\n")],
        clock=clock,
        on_read=send_during_capture,
    )
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
        store=store,
    )

    summary = runtime.capture_uart(duration_s=0.25)

    result = sent_results[0]
    assert result.attempt_id == "attempt01"
    assert result.perturbation_logged is True
    events = _hardware_events(tmp_path / summary.session_id)
    assert [event["type"] for event in events] == ["uart_tx_attempt", "uart_tx_result"]
    assert events[0] == {
        "type": "uart_tx_attempt",
        "attempt_id": "attempt01",
        "segment_id": 0,
        "attempted_at": "2026-08-21T10:00:00Z",
        "data_b64": "Z28K",
        "payload_bytes": 3,
        "forced": True,
    }
    assert events[1]["attempt_id"] == "attempt01"
    assert events[1]["outcome"] == "success"
    assert events[1]["bytes_accepted"] == 3
    assert events[1]["device_timestamp_us"] == 150
    assert events[1]["timestamp_us"] == 150
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b"ready\n"


def test_send_during_capture_requires_explicit_force(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender()
    errors: list[UartSendError] = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        try:
            runtime.send_uart(cmd="go")
        except UartSendError as exc:
            errors.append(exc)

    source = FakeCaptureSource([None], clock=clock, on_read=send_during_capture)
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
    )

    runtime.capture_uart(duration_s=0.25)

    assert errors[0].error == "capture_active"
    assert sender.payloads == []


def test_forced_backend_failure_records_known_partial_acceptance(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender(
        BackendWriteError("write timed out", bytes_accepted=2, error="timeout")
    )
    errors: list[UartSendError] = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        try:
            runtime.send_uart(cmd="go", force=True)
        except UartSendError as exc:
            errors.append(exc)

    source = FakeCaptureSource([None], clock=clock, on_read=send_during_capture)
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
    )

    summary = runtime.capture_uart(duration_s=0.25)

    assert errors[0].error == "timeout"
    assert errors[0].context == {
        "attempt_id": "attempt01",
        "bytes_accepted": 2,
        "may_have_reached_dut": True,
    }
    result = _hardware_events(tmp_path / summary.session_id)[1]
    assert result["outcome"] == "failed"
    assert result["error"] == "timeout"
    assert result["bytes_accepted"] == 2


class FailingAttemptStore(SessionStore):
    def append_uart_tx_attempt(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        segment_id: int,
        attempted_at: str,
        data: bytes,
    ) -> None:
        del attempt_id, segment_id, attempted_at, data
        raise SessionPersistenceError(
            operation="append",
            path=handle.paths.hardware_events,
            detail="disk unavailable",
        )


class FailingResultStore(SessionStore):
    def append_uart_tx_result(
        self,
        handle: SessionHandle,
        *,
        attempt_id: str,
        segment_id: int,
        completed_at: str,
        outcome: Literal["success", "failed"],
        error: str | None,
        bytes_accepted: int | None,
        timestamp_us: int | None,
        device_timestamp_us: int | None,
    ) -> None:
        del (
            attempt_id,
            segment_id,
            completed_at,
            outcome,
            error,
            bytes_accepted,
            timestamp_us,
            device_timestamp_us,
        )
        raise SessionPersistenceError(
            operation="append",
            path=handle.paths.hardware_events,
            detail="disk unavailable",
        )


def test_attempt_persistence_failure_prevents_dispatch(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender()
    store = FailingAttemptStore(
        root=tmp_path,
        clock=_fixed_time,
        id_factory=lambda: "runtime",
    )
    errors: list[UartSendError] = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        try:
            runtime.send_uart(cmd="go", force=True)
        except UartSendError as exc:
            errors.append(exc)

    source = FakeCaptureSource([None], clock=clock, on_read=send_during_capture)
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
        store=store,
    )

    runtime.capture_uart(duration_s=0.25)

    assert errors[0].error == "persistence_fault"
    assert sender.payloads == []


def test_result_persistence_failure_leaves_unknown_durable_attempt(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender(BackendUartSendResult(3, device_timestamp_us=100))
    store = FailingResultStore(
        root=tmp_path,
        clock=_fixed_time,
        id_factory=lambda: "runtime",
    )
    errors: list[UartSendError] = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        try:
            runtime.send_uart(cmd="go", force=True)
        except UartSendError as exc:
            errors.append(exc)

    source = FakeCaptureSource([None], clock=clock, on_read=send_during_capture)
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
        store=store,
    )

    summary = runtime.capture_uart(duration_s=0.25)

    assert errors[0].error == "persistence_fault"
    assert errors[0].context == {
        "attempt_id": "attempt01",
        "outcome": "unknown",
        "may_have_reached_dut": True,
    }
    assert [event["type"] for event in _hardware_events(tmp_path / summary.session_id)] == [
        "uart_tx_attempt"
    ]
    detail = store.get_session_detail(summary.session_id)
    assert isinstance(detail, NativeSessionDetail)
    assert detail.unresolved_uart_tx_attempts == 1


def test_attempt_quota_rejection_stops_capture_without_dispatch(tmp_path: Path) -> None:
    clock = FakeMonotonicClock()
    sender = FakeSender()
    store = SessionStore(
        root=tmp_path,
        clock=_fixed_time,
        id_factory=lambda: "runtime",
        evidence_budget_bytes=200,
    )
    errors: list[UartSendError] = []
    runtime: DeviceCoreRuntime

    def send_during_capture() -> None:
        try:
            runtime.send_uart(cmd="go", force=True)
        except UartSendError as exc:
            errors.append(exc)

    source = FakeCaptureSource(
        [UartReceiveEvent(0, 10, 0, b"must-not-be-admitted\n")],
        clock=clock,
        on_read=send_during_capture,
    )
    runtime = _runtime(
        tmp_path,
        sender=sender,
        source=source,
        capture_clock=clock,
        store=store,
    )

    summary = runtime.capture_uart(duration_s=0.25)

    assert errors[0].error == "persistence_fault"
    assert errors[0].session_terminalized is True
    assert sender.payloads == []
    assert summary.end_reason == "size_limit"
    assert summary.truncated is True
    assert summary.truncation is not None
    assert summary.truncation["rejected_unit_type"] == "uart_tx_attempt"
    assert (tmp_path / summary.session_id / "uart_raw.log").read_bytes() == b""


def _runtime(
    tmp_path: Path,
    *,
    sender: FakeSender,
    tx_enabled: bool = True,
    source: FakeCaptureSource | None = None,
    capture_clock: FakeMonotonicClock | None = None,
    store: SessionStore | None = None,
) -> DeviceCoreRuntime:
    runtime = DeviceCoreRuntime(
        device_control=EnhancedDeviceControl(FakeTransport()),
        uart_sender=sender,
        message_source=source,
        capture_clock=capture_clock,
        session_store=store or _store(tmp_path),
        tx_policy_enabled=tx_enabled,
        uart_wall_clock=_fixed_time,
        uart_attempt_id_factory=lambda: "attempt01",
    )
    runtime.record_backend_connection(enhanced_info())
    return runtime


def _store(tmp_path: Path) -> SessionStore:
    return SessionStore(root=tmp_path, clock=_fixed_time, id_factory=lambda: "runtime")


def _fixed_time() -> datetime:
    return datetime(2026, 8, 21, 10, 0, tzinfo=timezone.utc)


def _hardware_events(session_root: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in session_root.joinpath("hardware_events.jsonl").read_text().splitlines()
    ]
