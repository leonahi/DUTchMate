"""Service-facing Device Core runtime composition."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from threading import Event, Lock, RLock
from typing import Literal, Protocol
from uuid import uuid4

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendCapabilityPolicy,
    BackendInfo,
    BackendMode,
    BackendSnapshot,
    DeviceControl,
    SegmentContext,
    UartIntegrity,
    UartSendCapabilityPolicy,
    UartSender,
    apply_capability_policy,
    integrity_for_backend,
)
from dutchmate_core.connection import (
    ConnectionBoundary,
    ConnectionLifecycleError,
    ConnectionOwner,
    ConnectionState,
)
from dutchmate_core.evidence.recorder import (
    ContinuousEvidenceRecorder,
    DurableEvidenceTail,
)
from dutchmate_core.evidence.tail import (
    EvidenceCursorExpired,
    EvidencePage,
    validate_evidence_query,
)
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.configurator import GpioConfigurator
from dutchmate_core.gpio_config.modes import (
    GpioConfigurationError,
    GpioControlChannel,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRequestSource,
    GpioRoleName,
)
from dutchmate_core.operations.interact import InteractResult
from dutchmate_core.operations.monitor import (
    ActiveMonitor,
    ActiveMonitorSummary,
    EvidenceCursor,
    EvidenceRange,
    MonitorCondition,
    MonitorMatch,
    MonitorMatcher,
    MonitorOutcome,
    MonitorRequest,
    MonitorResult,
    validate_monitor_request,
)
from dutchmate_core.profile import DutProfile
from dutchmate_core.session_store.models import (
    BaselineMutationResult,
    CommandedBootMode,
    FirstError,
    RecentLogs,
    SessionComparison,
    SessionDetail,
    SessionListPage,
    SessionRetentionStatus,
)
from dutchmate_core.validation import (
    UartTxPayload,
    prepare_uart_tx_payload,
    validate_boot_mode,
    validate_capture_duration,
    validate_gpio_configuration,
    validate_gpio_source,
    validate_reset_pulse,
    validate_wait_pattern,
    validate_wait_timeout,
)
from dutchmate_core.workflows.capture import (
    CaptureEventSource,
    CaptureSourceMonitor,
    ReconnectLifecycle,
)
from dutchmate_core.workflows.device_actions import (
    DeviceActionError,
    DeviceActionResult,
    DeviceActionRunner,
)
from dutchmate_core.workflows.uart_send import (
    UartSendError,
    UartSendResult,
    UartSendWorkflow,
)


class DeviceCoreRuntimeError(RuntimeError):
    """Raised when the runtime cannot perform the requested operation."""


class DeviceCoreSessionStorage(Protocol):
    """Capture and bounded-query storage operations required by the runtime."""

    def read_evidence_page(
        self, *, cursor: str | None, tail_session_id: str | None, limit: int,
    ) -> EvidencePage: ...

    def list_session_page(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        """Return one bounded newest-first session page."""

    def get_session_detail(self, session_id: str) -> SessionDetail:
        """Return bounded schema-aware detail for one session."""

    def replay_recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = 300,
        active_session_id: str | None = None,
    ) -> RecentLogs:
        """Return bounded recent UART replay for one selected native session."""

    def load_detected_pattern(
        self,
        session_id: str,
        detected_pattern_index: int,
    ) -> FirstError:
        """Return one authoritative stored detected-pattern record."""

    def mark_baseline(self, session_id: str) -> BaselineMutationResult:
        """Designate one eligible session as the project baseline."""

    def clear_baseline(self, session_id: str) -> BaselineMutationResult:
        """Clear the project baseline only when it names the requested session."""

    def compare_session(self, session_id: str) -> SessionComparison:
        """Compare one terminal session with the designated baseline."""


@dataclass(frozen=True, slots=True)
class DeviceCoreStatus:
    """Current service-facing Device Core state."""

    connected: bool
    port: str | None
    firmware: str | None
    device: str | None
    capabilities: tuple[str, ...]
    active_session_id: str | None
    control_channels: dict[GpioControlChannel, GpioControlChannelState]
    commanded_boot_mode: CommandedBootMode | None = None
    backend_mode: BackendMode | None = None
    backend_capabilities: tuple[str, ...] = ()
    capability_policy: BackendCapabilityPolicy | None = None
    timestamp_provenance: SegmentContext | None = None
    integrity: UartIntegrity | None = None
    connection_state: ConnectionState = "disconnected"
    reconnect_remaining_s: float | None = None
    retention: SessionRetentionStatus = SessionRetentionStatus()
    profile_name: str | None = None
    profile_digest_sha256: str | None = None
    effective_profile: dict[str, object] | None = None
    active_operations: tuple[ActiveMonitorSummary, ...] = ()
    connection_error: dict[str, object] | None = None


class DeviceCoreRuntime:
    """Compose Phase 1 core services behind one service-facing object."""

    def __init__(
        self,
        *,
        device_control: DeviceControl,
        uart_sender: UartSender | None = None,
        session_store: DeviceCoreSessionStorage,
        gpio_registry: GpioModeRegistry | None = None,
        message_source: CaptureEventSource | None = None,
        capture_clock: Callable[[], float] | None = None,
        port: str | None = None,
        backend_mode: BackendMode | None = None,
        tx_policy_enabled: bool = False,
        segment_context: SegmentContext | None = None,
        backend_reconnect: ReconnectLifecycle | None = None,
        dut_io_voltage: float | None = None,
        action_wall_clock: Callable[[], datetime] | None = None,
        uart_wall_clock: Callable[[], datetime] | None = None,
        uart_attempt_id_factory: Callable[[], str] | None = None,
        profile: DutProfile | None = None,
        evidence_recorder: ContinuousEvidenceRecorder | None = None,
        monitor_id_factory: Callable[[], str] | None = None,
        connection_owner: ConnectionOwner | None = None,
    ) -> None:
        if profile is not None:
            port = profile.current_serial_port
            backend_mode = profile.backend_mode
            tx_policy_enabled = profile.uart.tx_enabled
            dut_io_voltage = profile.dut_io_voltage
        self._connection_owner = connection_owner
        self._lifecycle_lock = Lock()
        self._lifecycle_active = False
        self._profile = profile
        self._evidence_recorder = evidence_recorder
        self._monitor_id_factory = monitor_id_factory or (lambda: f"monitor-{uuid4()}")
        self._message_source = message_source
        self._status_clock = capture_clock or time.monotonic
        self._backend_reconnect = backend_reconnect
        self._dut_io_voltage = dut_io_voltage
        self._session_store = session_store
        self._mutation_lock = RLock()
        self._active_mutations = 0
        self._interact_owner: str | None = None
        self._uart_send_workflow = (
            UartSendWorkflow(
                sender=uart_sender,
                wall_clock=uart_wall_clock,
                attempt_id_factory=uart_attempt_id_factory,
            )
            if uart_sender is not None
            else None
        )
        self._gpio_registry = gpio_registry or GpioModeRegistry()
        self._gpio_configurator = GpioConfigurator(
            registry=self._gpio_registry,
            control=device_control,
        )
        self._action_runner = DeviceActionRunner(
            registry=self._gpio_registry,
            control=device_control,
            wall_clock=action_wall_clock,
        )
        self._port = port
        self._connection_state: ConnectionState = "disconnected"
        self._source_connection_generation: int | None = None
        self._commanded_boot_mode: CommandedBootMode | None = None
        self._backend_mode = backend_mode
        self._backend_info: BackendInfo | None = None
        self._backend_capabilities: frozenset[BackendCapability] = frozenset()
        self._integrity: UartIntegrity | None = None
        self._capability_policy = BackendCapabilityPolicy(
            uart_send=UartSendCapabilityPolicy(
                tx_policy_enabled=tx_policy_enabled,
            )
        )
        source_segment = getattr(message_source, "segment", None)
        self._segment_context = (
            segment_context
            if segment_context is not None
            else source_segment
            if isinstance(source_segment, SegmentContext)
            else None
        )
        self._active_session_id: str | None = (
            evidence_recorder.active_session_id if evidence_recorder is not None else None
        )
        self._operation_lock = RLock()
        self._active_monitors: dict[str, ActiveMonitor] = {}
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._close_error: BaseException | None = None

    @property
    def _connected(self) -> bool:
        return self._connection_state == "connected"

    @contextmanager
    def _ownership_change(self) -> Iterator[None]:
        if not self._lifecycle_lock.acquire(blocking=False):
            raise ConnectionLifecycleError(
                "operation_active", "A connection lifecycle request is active"
            )
        mutation_acquired = False
        try:
            with self._operation_lock:
                if self._closing or self._closed:
                    raise ConnectionLifecycleError(
                        "invalid_connection_state", "Runtime is shutting down"
                    )
                self._check_interact_owner(None)
                if self._active_mutations:
                    raise ConnectionLifecycleError(
                        "operation_active", "A submitted mutation is active"
                    )
                self._lifecycle_active = True
            mutation_acquired = self._mutation_lock.acquire(blocking=False)
            if not mutation_acquired:
                raise ConnectionLifecycleError("operation_active", "A mutating action is active")
            yield
        finally:
            with self._operation_lock:
                self._lifecycle_active = False
            if mutation_acquired:
                self._mutation_lock.release()
            self._lifecycle_lock.release()

    def _ownership_boundary(self) -> ConnectionBoundary:
        recorder = self._evidence_recorder
        if recorder is None:
            raise ConnectionLifecycleError(
                "service_unavailable", "No authoritative ownership journal"
            )
        status = self.status()
        return ConnectionBoundary(
            status.connection_state, recorder.active_session_id, recorder.segment.segment_id
        )

    def release_connection(self) -> ConnectionBoundary:
        with self._ownership_change():
            if self.status().connection_state != "connected" or self._connection_owner is None:
                raise ConnectionLifecycleError(
                    "invalid_connection_state", "Release requires connected ownership"
                )
            self._connection_owner.release()
            with self._operation_lock:
                monitors = tuple(self._active_monitors.values())
            for monitor in monitors:
                monitor.completed.wait()
            return self._ownership_boundary()

    def reacquire_connection(self) -> ConnectionBoundary:
        with self._ownership_change():
            if (
                self.status().connection_state not in {"released", "disconnected"}
                or self._connection_owner is None
            ):
                raise ConnectionLifecycleError(
                    "invalid_connection_state",
                    "Reacquire requires released or disconnected ownership",
                )
            with self._operation_lock:
                monitors = tuple(self._active_monitors.values())
            for monitor in monitors:
                monitor.completed.wait()
            self._connection_owner.reacquire()
            return self._ownership_boundary()

    @property
    def session_store(self) -> DeviceCoreSessionStorage:
        """Capture-session storage used by this runtime."""

        return self._session_store

    def close(self) -> None:
        """Close the currently owned backend source exactly once."""

        with self._operation_lock:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            if self._closing:
                first_closer = False
                source = None
            else:
                self._closing = True
                first_closer = True
                source = self._message_source
                self._message_source = None
                self._mark_backend_disconnected()
                active_monitors = tuple(self._active_monitors.values())
                for monitor in active_monitors:
                    monitor.cancellation.set()

        if not first_closer:
            self._close_complete.wait()
            with self._operation_lock:
                retained_error = self._close_error
            if retained_error is not None:
                raise retained_error
            return

        if self._connection_owner is not None:
            self._connection_owner.cancel_pending()
        close_error: BaseException | None = None
        for monitor in active_monitors:
            monitor.completed.wait()
        # In-flight standalone actions must finish their result evidence before
        # reconnect supervision or authoritative recording can be closed.
        with self._mutation_lock:
            reconnect_close = getattr(self._backend_reconnect, "close", None)
            if callable(reconnect_close):
                try:
                    reconnect_close()
                except BaseException as exc:
                    close_error = exc
            try:
                if source is not None:
                    self._close_event_source(source)
                if self._evidence_recorder is not None:
                    self._evidence_recorder.close()
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
            finally:
                with self._operation_lock:
                    self._close_error = close_error
                    self._closed = True
                self._close_complete.set()
        if close_error is not None:
            raise close_error

    def list_sessions(
        self,
        *,
        limit: int = 50,
        cursor: str | None = None,
    ) -> SessionListPage:
        """Return one bounded page without requiring a backend connection."""

        return self._session_store.list_session_page(limit=limit, cursor=cursor)

    def get_session(self, session_id: str) -> SessionDetail:
        """Return bounded session detail without expanding raw evidence arrays."""

        return self._session_store.get_session_detail(session_id)

    def recent_logs(
        self,
        *,
        session_id: str | None = None,
        lines: int = 300,
    ) -> RecentLogs:
        """Return recent UART evidence without requiring a backend connection."""

        with self._operation_lock:
            active_session_id = self._active_session_id
        return self._session_store.replay_recent_logs(
            session_id=session_id,
            lines=lines,
            active_session_id=active_session_id,
        )

    def evidence(
        self, *, cursor: str | None = None, limit: int = 100, wait_s: float = 1.0,
    ) -> EvidencePage:
        """Observe durable evidence; attachment and polling never acquire reader ownership."""

        validate_evidence_query(cursor=cursor, limit=limit, wait_s=wait_s)
        recorder = self._evidence_recorder
        if recorder is None and cursor is None:
            raise DeviceCoreRuntimeError("Authoritative evidence recorder is unavailable")
        previous = recorder.durable_tail() if recorder is not None else None
        while True:
            try:
                page = self._session_store.read_evidence_page(
                    cursor=cursor,
                    tail_session_id=previous.session_id if previous is not None else None,
                    limit=limit,
                )
                break
            except EvidenceCursorExpired:
                if cursor is not None or recorder is None or previous is None:
                    raise
                # An attachment has no historical position to preserve. If rollover
                # retired this sampled tail, wait for publication and sample again.
                changed = recorder.wait_for_durable_tail(previous, timeout_s=1.0)
                if changed is None:
                    raise DeviceCoreRuntimeError("Durable evidence tail is unavailable") from None
                previous = changed
        if cursor is not None and not page.records and wait_s and recorder is not None:
            assert previous is not None
            recorder.wait_for_durable_tail(previous, timeout_s=wait_s)
            page = self._session_store.read_evidence_page(
                cursor=page.next_cursor,
                tail_session_id=recorder.durable_tail().session_id,
                limit=limit,
            )
        return page

    def mark_baseline(self, session_id: str) -> BaselineMutationResult:
        """Designate a stored session without requiring a backend connection."""

        return self._session_store.mark_baseline(session_id)

    def clear_baseline(self, session_id: str) -> BaselineMutationResult:
        """Clear a named designation without requiring a backend connection."""

        return self._session_store.clear_baseline(session_id)

    def compare_session(self, session_id: str) -> SessionComparison:
        """Compare stored evidence without requiring a backend connection."""

        return self._session_store.compare_session(session_id)

    @property
    def gpio_registry(self) -> GpioModeRegistry:
        """GPIO role configuration state used by this runtime."""

        return self._gpio_registry

    def record_backend_connection(self, info: BackendInfo) -> DeviceCoreStatus:
        """Record normalized identity for the selected connected backend."""

        if info.mode == "basic" and (info.device is not None or info.firmware is not None):
            raise ValueError("Basic backend identity must omit device and firmware")
        with self._operation_lock:
            self._connection_state = "connected"
            self._commanded_boot_mode = None
            self._backend_mode = info.mode
            self._backend_info = info
            self._backend_capabilities = info.capabilities
            self._integrity = integrity_for_backend(info.mode)
            self._port = info.port
        return self.status()

    def disconnect(self) -> DeviceCoreStatus:
        """Detach publication and mark the backend disconnected."""

        if self._connection_owner is not None:
            self._connection_owner.cancel_pending()
        with self._operation_lock:
            self._connection_state = "disconnected"
            self._commanded_boot_mode = None
            self._backend_info = None
            self._backend_capabilities = frozenset()
            self._segment_context = None
            self._integrity = None
        return self.status()

    def status(self) -> DeviceCoreStatus:
        """Return the current service-facing status snapshot."""

        with self._operation_lock:
            self._reconcile_capture_source_health()
            status_source = self._evidence_recorder or self._message_source
            source_segment = getattr(status_source, "segment", None)
            if self._connected and isinstance(source_segment, SegmentContext):
                self._segment_context = source_segment
            recorder_state = (
                self._evidence_recorder.state if self._evidence_recorder is not None else None
            )
            if self._evidence_recorder is not None:
                self._active_session_id = (
                    self._evidence_recorder.active_session_id
                    if recorder_state in {"connected", "reconnecting", "released", "reacquiring"}
                    else None
                )
            if recorder_state in {
                "reconnecting",
                "released",
                "reacquiring",
                "faulted",
                "disconnected",
            }:
                self._connection_state = recorder_state
            connection_state = self._connection_state
            retention = getattr(
                self._session_store,
                "retention_status",
                SessionRetentionStatus(),
            )
            failure = self._connection_owner.failure if self._connection_owner is not None else None
            return DeviceCoreStatus(
                connection_error=(
                    {"error": failure.error, "detail": str(failure), "context": failure.context}
                    if failure is not None
                    else None
                ),
                connected=self._connected,
                port=self._port,
                firmware=(self._backend_info.firmware if self._backend_info is not None else None),
                device=(self._backend_info.device if self._backend_info is not None else None),
                capabilities=(
                    tuple(
                        sorted(
                            apply_capability_policy(
                                self._backend_capabilities,
                                self._capability_policy,
                            )
                        )
                    )
                ),
                active_session_id=self._active_session_id,
                control_channels=self._gpio_registry.snapshot(),
                commanded_boot_mode=self._commanded_boot_mode,
                backend_mode=self._backend_mode,
                backend_capabilities=tuple(sorted(self._backend_capabilities)),
                capability_policy=(
                    self._capability_policy if self._backend_mode is not None else None
                ),
                timestamp_provenance=(self._segment_context),
                integrity=self._integrity,
                connection_state=connection_state,
                retention=retention,
                profile_name=(self._profile.name if self._profile is not None else None),
                profile_digest_sha256=(
                    self._profile.digest_sha256 if self._profile is not None else None
                ),
                effective_profile=(
                    self._profile.projection() if self._profile is not None else None
                ),
                active_operations=tuple(
                    ActiveMonitorSummary(
                        operation_id=monitor.operation_id,
                        mode=monitor.mode,
                        operation_type=monitor.operation_type,
                        deadline_remaining_s=max(
                            0.0,
                            monitor.deadline - self._status_clock(),
                        ),
                    )
                    for monitor in self._active_monitors.values()
                ),
            )

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[GpioRoleName, GpioControlChannelState]:
        """Apply configured GPIO modes after a Debug Helper hello is available."""

        with self._mutation():
            self._require_connected()
            if config.dut_io_voltage is None and config.controls:
                raise DeviceCoreRuntimeError(
                    "hardware.dut_io_voltage must be configured before GPIO control"
                )
            if config.dut_io_voltage is not None:
                self._dut_io_voltage = config.dut_io_voltage
            applied: dict[GpioRoleName, GpioControlChannelState] = {}
            for mapping in config.controls.values():
                applied[mapping.role] = self.configure_gpio_mode(
                    role=mapping.role,
                    channel=mapping.channel,
                    dut_signal=mapping.dut_signal,
                    mode=mapping.mode,
                    active_level=mapping.active_level,
                    idle_level=mapping.idle_level,
                    source="config",
                )
            return applied

    def configure_gpio_mode(
        self,
        *,
        role: str,
        channel: str,
        dut_signal: str,
        mode: str,
        active_level: str,
        source: GpioModeRequestSource = "runtime",
        idle_level: str | None = None,
    ) -> GpioControlChannelState:
        """Configure one GPIO role through firmware and update runtime state."""

        request = validate_gpio_configuration(
            role=role,
            channel=channel,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        source_name = validate_gpio_source(source)
        with self._mutation():
            self._require_connected()
            if self._dut_io_voltage is None:
                raise DeviceCoreRuntimeError(
                    "hardware.dut_io_voltage must be configured before GPIO control"
                )
            self._require_control_capability("configure_gpio_mode")
            recorder = self._require_action_recorder()
            attempt_id = str(uuid4())
            recorder.audit_control_attempt(
                attempt_id=attempt_id,
                role=request.role,
                parameters={
                    "action": "configure_gpio_mode",
                    "channel": request.channel,
                    "dut_signal": request.dut_signal,
                    "mode": request.mode,
                    "active_level": request.active_level,
                    "idle_level": request.idle_level,
                    "source": source_name,
                },
            )
            boot_mapping = self._gpio_registry.find_by_role("boot")
            affects_boot_state = request.role == "boot" or (
                boot_mapping is not None and boot_mapping.channel == request.channel
            )
            try:
                state = self._gpio_configurator.configure_mode(
                    role=request.role,
                    channel=request.channel,
                    dut_signal=request.dut_signal,
                    mode=request.mode,
                    active_level=request.active_level,
                    idle_level=request.idle_level,
                    source=source_name,
                )
            except GpioConfigurationError:
                self._control_result(recorder, attempt_id=attempt_id, status="backend_input_error")
                if affects_boot_state:
                    self._commanded_boot_mode = None
                raise
            self._control_result(
                recorder,
                attempt_id=attempt_id,
                status=state.last_rejected.error if state.last_rejected else "success",
                device_timestamp_us=state.device_timestamp_us if not state.last_rejected else None,
            )
            if state.last_rejected is not None:
                if affects_boot_state and state.last_rejected.error in {
                    "hardware_fault",
                    "timeout",
                }:
                    self._commanded_boot_mode = None
            elif state.state == "configured":
                if request.role == "boot":
                    self._commanded_boot_mode = "normal"
                elif self._gpio_registry.find_by_role("boot") is None:
                    self._commanded_boot_mode = None
            return state

    @staticmethod
    def _control_result(
        recorder: ContinuousEvidenceRecorder,
        *,
        attempt_id: str,
        status: str,
        device_timestamp_us: int | None = None,
    ) -> None:
        try:
            recorder.audit_control_result(
                attempt_id=attempt_id,
                status=status,
                device_timestamp_us=device_timestamp_us,
            )
        except (RuntimeError, ValueError) as exc:
            raise DeviceActionError(
                error="persistence_fault",
                detail="Control result could not be stored; the durable attempt outcome is unknown",
                context={
                    "attempt_id": attempt_id,
                    "outcome": "unknown",
                    "may_have_reached_dut": True,
                },
            ) from exc

    def _require_control_capability(self, operation: str) -> None:
        effective = apply_capability_policy(self._backend_capabilities, self._capability_policy)
        if "gpio_control" not in effective:
            raise DeviceActionError(
                error="unsupported_capability",
                detail="Operation requires effective capability 'gpio_control'",
                context={
                    "operation": operation,
                    "backend_mode": self._backend_mode,
                    "required_capabilities": ["gpio_control"],
                    "available_capabilities": sorted(effective),
                    "backend_capabilities": sorted(self._backend_capabilities),
                    "disabled_by_policy": [],
                },
            )

    def _control_action(
        self,
        *,
        role: str,
        parameters: dict[str, object],
        dispatch: Callable[[], DeviceActionResult],
    ) -> DeviceActionResult:
        recorder = self._require_action_recorder()
        self._require_control_capability(str(parameters["action"]))
        mapping = self._gpio_registry.require_role_configured(
            role,
            operation=str(parameters["action"]),
        )
        attempt_id = str(uuid4())
        recorder.audit_control_attempt(
            attempt_id=attempt_id,
            role=role,
            parameters={
                **parameters,
                "channel": mapping.channel,
                "active_level": mapping.active_level,
                "mode": mapping.mode,
                "idle_level": mapping.idle_level,
                "dut_signal": mapping.dut_signal,
            },
        )
        try:
            result = dispatch()
        except DeviceActionError as exc:
            self._control_result(recorder, attempt_id=attempt_id, status=exc.error)
            raise
        self._control_result(
            recorder,
            attempt_id=attempt_id,
            status="success",
            device_timestamp_us=result.device_timestamp_us,
        )
        return result

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Audit and pulse the configured reset role without disturbing RX."""

        pulse_ms = validate_reset_pulse(pulse_ms)
        with self._mutation():
            return self._control_action(
                role="reset",
                parameters={"action": "reset", "pulse_ms": pulse_ms},
                dispatch=lambda: self._action_runner.reset_dut(pulse_ms=pulse_ms),
            )

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Audit and set the configured boot role."""

        mode = validate_boot_mode(mode)
        with self._mutation():
            try:
                result = self._control_action(
                    role="boot",
                    parameters={"action": "set_boot_mode", "mode": mode},
                    dispatch=lambda: self._action_runner.set_boot_mode(mode=mode),
                )
            except DeviceActionError as exc:
                if exc.error not in {
                    "invalid_argument",
                    "not_configured",
                    "unsupported_capability",
                }:
                    self._commanded_boot_mode = None
                raise
            self._commanded_boot_mode = result.mode
            return result

    def capture_uart(self, *, duration_s: float) -> MonitorResult:
        """Run the legacy capture spelling as a bounded Monitor alias."""

        duration_s = validate_capture_duration(duration_s)
        return self.monitor(duration_s=duration_s)

    def monitor(
        self,
        *,
        duration_s: object | None = None,
        conditions: Sequence[MonitorCondition] | None = None,
        timeout_s: object | None = None,
        cancellation: Event | None = None,
    ) -> MonitorResult:
        """Run one bounded read-only window over already-authoritative evidence."""

        request = validate_monitor_request(
            duration_s=duration_s,
            conditions=conditions,
            timeout_s=timeout_s,
        )
        return self._run_bounded_operation(request=request, cancellation=cancellation)

    def _run_bounded_operation(
        self,
        *,
        request: MonitorRequest,
        cancellation: Event | None = None,
        operation_type: Literal["monitor", "interact"] = "monitor",
        operation_id: str | None = None,
        start_action: Callable[[str], None] | None = None,
        action_parameters: dict[str, object] | None = None,
    ) -> MonitorResult:
        recorder = self._evidence_recorder
        if recorder is None:
            raise DeviceCoreRuntimeError("Continuous evidence recorder is unavailable")
        cancellation = cancellation or Event()
        completion = Event()
        bound_s = request.duration_s or request.timeout_s
        assert bound_s is not None
        with self._operation_lock:
            if self._closing or self._closed or self._lifecycle_active:
                raise DeviceCoreRuntimeError("Device Core runtime is changing ownership")
            recorder_state = recorder.state
            if recorder_state not in {"connected", "reconnecting"}:
                raise DeviceCoreRuntimeError("Monitor requires a connected or reconnecting backend")
            health = recorder.capture_source_health()
            snapshot = health.backend_snapshot
            capabilities = (
                snapshot.capabilities
                if snapshot is not None
                else apply_capability_policy(
                    self._backend_capabilities,
                    self._capability_policy,
                )
            )
            if "uart_receive" not in capabilities:
                raise DeviceCoreRuntimeError("Monitor requires effective capability 'uart_receive'")
            operation_id = operation_id or self._monitor_id_factory()
            deadline = self._status_clock() + bound_s
            active = ActiveMonitor(
                operation_id=operation_id,
                mode=request.mode,
                deadline=deadline,
                cancellation=cancellation,
                completed=completion,
                operation_type=operation_type,
            )
            start_cursor, incomplete_channels, evidence_reader = recorder.start_monitor_operation(
                operation_id=operation_id,
                parameters={**_monitor_parameters(request), **(action_parameters or {})},
                operation_type=operation_type,
            )
            try:
                self._active_monitors[operation_id] = active
            except BaseException as exc:
                try:
                    recorder.complete_monitor_operation(
                        operation_id=operation_id,
                        outcome="error",
                        error={
                            "code": (
                                exc.error
                                if isinstance(exc, (DeviceActionError, UartSendError))
                                else f"{operation_type}_error"
                            ),
                            "detail": str(exc),
                        },
                    )
                except BaseException as terminal_error:
                    evidence_reader.close()
                    raise terminal_error from exc
                evidence_reader.close()
                raise

        matcher: MonitorMatcher | None = None
        cursor = start_cursor
        match = None
        outcome: MonitorOutcome
        terminalized = False
        try:
            if start_action is not None and not cancellation.is_set():
                start_action(operation_id)
            matcher = (
                MonitorMatcher(
                    request.conditions,
                    incomplete_channels=incomplete_channels,
                )
                if request.mode == "conditions"
                else None
            )
            while True:
                if cancellation.is_set():
                    outcome = "cancelled"
                    break
                recorder_state = recorder.state
                if recorder_state in {"released", "reacquiring", "disconnected"}:
                    outcome = "disconnected" if recorder_state == "disconnected" else "released"
                    break
                if recorder_state == "faulted":
                    raise DeviceCoreRuntimeError(
                        "Authoritative evidence recording faulted during Monitor"
                    )
                remaining_s = deadline - self._status_clock()
                if remaining_s <= 0:
                    outcome = (
                        "disconnected"
                        if recorder_state == "reconnecting"
                        else "elapsed"
                        if request.mode == "duration"
                        else "timeout"
                    )
                    break
                tail = recorder.wait_for_durable_tail(
                    DurableEvidenceTail(
                        session_id=cursor.session_id,
                        next_evidence_seq=cursor.next_evidence_seq,
                    ),
                    timeout_s=min(remaining_s, 0.05),
                )
                if tail is None:
                    continue
                next_cursor = EvidenceCursor(
                    session_id=tail.session_id,
                    next_evidence_seq=tail.next_evidence_seq,
                )
                evidence = recorder.read_monitor_evidence(
                    reader=evidence_reader,
                    end=next_cursor,
                )
                cursor = next_cursor
                if matcher is not None:
                    match = matcher.process(evidence)
                    if match is not None:
                        outcome = "matched"
                        break

            terminal = recorder.complete_monitor_operation(
                operation_id=operation_id,
                outcome=outcome,
                matched_condition=(match.persistence_projection() if match is not None else None),
                line_processing_limited=(
                    matcher.line_processing_limited if matcher is not None else False
                ),
            )
            terminalized = True
            return _monitor_result(
                operation_id=operation_id,
                request=request,
                start_cursor=start_cursor,
                terminal=terminal,
                match=match,
                line_processing_limited=(
                    matcher.line_processing_limited if matcher is not None else False
                ),
                recorder=recorder,
            )
        except BaseException as exc:
            if not terminalized and recorder.state != "faulted":
                try:
                    recorder.complete_monitor_operation(
                        operation_id=operation_id,
                        outcome="error",
                        error={
                            "code": (
                                exc.error
                                if isinstance(exc, (DeviceActionError, UartSendError))
                                else f"{operation_type}_error"
                            ),
                            "detail": str(exc),
                        },
                        matched_condition=None,
                        line_processing_limited=(
                            matcher.line_processing_limited if matcher is not None else False
                        ),
                    )
                except BaseException as terminal_error:
                    raise terminal_error from exc
            raise
        finally:
            evidence_reader.close()
            with self._operation_lock:
                self._active_monitors.pop(operation_id, None)
            completion.set()

    def wait_pattern(
        self,
        *,
        pattern: str,
        timeout_s: float,
    ) -> MonitorResult:
        """Run the legacy wait spelling as a conditional Monitor alias."""

        validated_pattern = validate_wait_pattern(pattern)
        validated_timeout = validate_wait_timeout(timeout_s)
        return self.monitor(
            conditions=(MonitorCondition(pattern=validated_pattern),),
            timeout_s=validated_timeout,
        )

    def _tx_payload(
        self,
        *,
        data_b64: object = None,
        text: object = None,
        line_ending: object = None,
    ) -> UartTxPayload:
        return prepare_uart_tx_payload(
            data_b64=data_b64,
            text=text,
            line_ending=line_ending,
            profile_default=self._profile.uart.default_line_ending if self._profile else "none",
        )

    def _require_action_recorder(self) -> ContinuousEvidenceRecorder:
        self._require_connected()
        recorder = self._evidence_recorder
        if recorder is None:
            raise DeviceCoreRuntimeError("Continuous evidence recorder is unavailable")
        if self._closing or self._closed or recorder.state != "connected":
            raise DeviceActionError(
                error="invalid_connection_state",
                detail="Action requires a connected backend",
            )
        return recorder

    @contextmanager
    def _mutation(self, *, owner: str | None = None) -> Iterator[None]:
        # Never hold the status/operation lock while waiting for a physical action.
        with self._operation_lock:
            self._check_interact_owner(owner)
        with self._mutation_lock:
            with self._operation_lock:
                self._check_interact_owner(owner)
                self._require_action_recorder()
                self._active_mutations += 1
            try:
                yield
            finally:
                with self._operation_lock:
                    self._active_mutations -= 1

    def _check_interact_owner(self, owner: str | None) -> None:
        if self._lifecycle_active:
            raise ConnectionLifecycleError("operation_active", "Connection ownership is changing")
        if self._interact_owner is not None and self._interact_owner != owner:
            raise DeviceActionError(
                error="operation_active",
                detail="An exclusive Interact operation is active",
                context={"operation_id": self._interact_owner},
            )

    def _require_tx_capability(self) -> None:
        effective = apply_capability_policy(self._backend_capabilities, self._capability_policy)
        if "uart_send" not in effective:
            raise UartSendError(
                error="unsupported_capability",
                detail="Operation requires effective capability 'uart_send'",
                context={
                    "operation": "uart_send",
                    "backend_mode": self._backend_mode,
                    "required_capabilities": ["uart_send"],
                    "available_capabilities": sorted(effective),
                    "backend_capabilities": sorted(self._backend_capabilities),
                    "disabled_by_policy": (
                        ["hardware.uart.tx_enabled"]
                        if "uart_send" in self._backend_capabilities
                        and not self._capability_policy.uart_send.tx_policy_enabled
                        else []
                    ),
                },
            )

    def _send_payload(
        self,
        payload: UartTxPayload,
        *,
        operation_id: str | None = None,
    ) -> UartSendResult:
        recorder = self._require_action_recorder()
        self._require_tx_capability()
        if self._uart_send_workflow is None:
            raise DeviceCoreRuntimeError("UART sender is not configured")
        return self._uart_send_workflow.run(payload, recorder=recorder, operation_id=operation_id)

    def send_uart(
        self,
        *,
        data_b64: object = None,
        text: object = None,
        line_ending: object = None,
    ) -> UartSendResult:
        """Transmit one exact audited payload without changing RX ownership."""

        payload = self._tx_payload(data_b64=data_b64, text=text, line_ending=line_ending)
        with self._mutation():
            return self._send_payload(payload)

    def interact(
        self,
        *,
        data_b64: object = None,
        text: object = None,
        line_ending: object = None,
        duration_s: object | None = None,
        conditions: Sequence[MonitorCondition] | None = None,
        timeout_s: object | None = None,
        cancellation: Event | None = None,
    ) -> InteractResult:
        """Send once and observe with the existing bounded operation machinery."""

        payload = self._tx_payload(data_b64=data_b64, text=text, line_ending=line_ending)
        request = validate_monitor_request(
            duration_s=duration_s,
            conditions=conditions,
            timeout_s=timeout_s,
        )
        with self._mutation():
            self._require_tx_capability()
            owner = f"interact-{uuid4()}"
            with self._operation_lock:
                self._interact_owner = owner
            tx: UartSendResult | None = None
            tx_error: dict[str, object] | None = None

            def send(operation_id: str) -> None:
                nonlocal tx, tx_error
                try:
                    tx = self._send_payload(payload, operation_id=operation_id)
                except UartSendError as exc:
                    tx_error = {"code": exc.error, "detail": exc.detail, "context": exc.context}
                    if (
                        self._evidence_recorder is not None
                        and self._evidence_recorder.state == "disconnected"
                    ):
                        return
                    if (
                        exc.error in {"persistence_fault", "backend_input_error"}
                        or not exc.context
                        or exc.context.get("connection_interrupted") is not True
                    ):
                        raise

            try:
                result = self._run_bounded_operation(
                    request=request,
                    cancellation=cancellation,
                    operation_type="interact",
                    operation_id=owner,
                    start_action=send,
                    action_parameters={
                        "data_b64": payload.data_b64,
                        "transformation": payload.transformation(),
                    },
                )
                return InteractResult(
                    **{field: getattr(result, field) for field in result.__dataclass_fields__},
                    data_b64=payload.data_b64,
                    transformation=payload.transformation(),
                    tx=tx,
                    tx_error=tx_error,
                )
            finally:
                with self._operation_lock:
                    self._interact_owner = None

    def _mark_backend_disconnected(self) -> None:
        with self._operation_lock:
            self._connection_state = "disconnected"
            self._commanded_boot_mode = None
            self._backend_info = None
            self._backend_capabilities = frozenset()
            self._segment_context = None
            self._integrity = None

    def _reconcile_capture_source_health(self) -> None:
        source = self._evidence_recorder or self._message_source
        if not isinstance(source, CaptureSourceMonitor):
            return
        health = source.capture_source_health()
        if not health.connected:
            self._mark_backend_disconnected()
            return
        snapshot = health.backend_snapshot
        if snapshot is not None and (
            self._source_connection_generation is None
            or health.connection_generation > self._source_connection_generation
        ):
            self._adopt_backend_snapshot(snapshot)
            self._source_connection_generation = health.connection_generation
        if (
            self._connected
            and health.integrity is not None
            and (
                snapshot is None
                or health.connection_generation == self._source_connection_generation
            )
        ):
            self._integrity = health.integrity

    def _adopt_backend_snapshot(self, snapshot: BackendSnapshot) -> None:
        if snapshot.capability_policy != self._capability_policy:
            raise ValueError("reconnected backend capability policy changed")
        self._connection_state = "connected"
        self._commanded_boot_mode = None
        self._backend_mode = snapshot.info.mode
        self._backend_info = snapshot.info
        self._backend_capabilities = snapshot.info.capabilities
        self._segment_context = snapshot.segment
        self._integrity = snapshot.integrity
        self._port = snapshot.info.port

    @staticmethod
    def _close_event_source(source: CaptureEventSource) -> None:
        close = getattr(source, "close", None)
        if callable(close):
            close()

    def _require_connected(self) -> None:
        self._reconcile_capture_source_health()
        if not self._connected:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")


def _monitor_parameters(request: MonitorRequest) -> dict[str, object]:
    if request.mode == "duration":
        return {
            "mode": "duration",
            "duration_s": request.duration_s,
        }
    return {
        "mode": "conditions",
        "conditions": [
            {"pattern": condition.pattern, "name": condition.name}
            for condition in request.conditions
        ],
        "timeout_s": request.timeout_s,
    }


def _monitor_result(
    *,
    operation_id: str,
    request: MonitorRequest,
    start_cursor: EvidenceCursor,
    terminal: dict[str, object],
    match: MonitorMatch | None,
    line_processing_limited: bool,
    recorder: ContinuousEvidenceRecorder,
) -> MonitorResult:
    if terminal.get("operation_id") != operation_id:
        raise DeviceCoreRuntimeError("Monitor terminal operation identity changed")
    outcome = terminal.get("outcome")
    if outcome not in {
        "elapsed",
        "matched",
        "timeout",
        "disconnected",
        "released",
        "cancelled",
        "error",
    }:
        raise DeviceCoreRuntimeError("Monitor terminal outcome is invalid")
    end_cursor = _monitor_cursor(terminal.get("end_cursor"), field="end")
    raw_ranges = terminal.get("evidence_ranges")
    if not isinstance(raw_ranges, list) or not raw_ranges:
        raise DeviceCoreRuntimeError("Monitor terminal evidence ranges are invalid")
    ranges = tuple(_monitor_range(item) for item in raw_ranges)
    integrity, timestamp_provenance = recorder.summarize_monitor_evidence(ranges)
    return MonitorResult(
        operation_id=operation_id,
        outcome=outcome,
        mode=request.mode,
        duration_s=request.duration_s,
        conditions=request.conditions,
        timeout_s=request.timeout_s,
        start_cursor=start_cursor,
        end_cursor=end_cursor,
        evidence_ranges=ranges,
        match=match,
        line_processing_limited=line_processing_limited
        or terminal.get("line_processing_limited") is True,
        integrity=integrity,
        timestamp_provenance=timestamp_provenance,
    )


def _monitor_cursor(value: object, *, field: str) -> EvidenceCursor:
    if not isinstance(value, dict):
        raise DeviceCoreRuntimeError(f"Monitor terminal {field} cursor is invalid")
    session_id = value.get("session_id")
    next_evidence_seq = value.get("next_evidence_seq")
    if (
        not isinstance(session_id, str)
        or not session_id
        or isinstance(next_evidence_seq, bool)
        or not isinstance(next_evidence_seq, int)
        or next_evidence_seq < 0
    ):
        raise DeviceCoreRuntimeError(f"Monitor terminal {field} cursor is invalid")
    return EvidenceCursor(session_id, next_evidence_seq)


def _monitor_range(value: object) -> EvidenceRange:
    if not isinstance(value, dict):
        raise DeviceCoreRuntimeError("Monitor terminal evidence range is invalid")
    session_id = value.get("session_id")
    start = value.get("start_evidence_seq")
    end = value.get("end_evidence_seq_exclusive")
    if (
        not isinstance(session_id, str)
        or not session_id
        or isinstance(start, bool)
        or not isinstance(start, int)
        or start < 0
        or isinstance(end, bool)
        or not isinstance(end, int)
        or end < start
    ):
        raise DeviceCoreRuntimeError("Monitor terminal evidence range is invalid")
    return EvidenceRange(session_id, start, end)
