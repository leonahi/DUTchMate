"""Service-facing Device Core runtime composition."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, replace
from datetime import datetime
from functools import partial
from threading import Event, RLock
from typing import Literal, Protocol

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendCapabilityPolicy,
    BackendEvent,
    BackendInfo,
    BackendInputError,
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
from dutchmate_core.backends.settings import DEFAULT_RECONNECT_TIMEOUT_S
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
from dutchmate_core.log_processing.patterns import DEFAULT_PATTERNS, PatternDetector
from dutchmate_core.session_store.models import (
    BaselineMutationResult,
    CommandedBootMode,
    FirstError,
    RecentLogs,
    SessionComparison,
    SessionDetail,
    SessionHandle,
    SessionListPage,
    SessionRetentionStatus,
    SessionSummary,
    SessionWorkflow,
    WaitPatternResult,
)
from dutchmate_core.uart_capture.processor import UartCaptureProcessor
from dutchmate_core.validation import (
    UartSendValidationError,
    prepare_uart_send_payload,
    validate_capture_duration,
    validate_gpio_configuration,
    validate_gpio_source,
    validate_wait_pattern,
    validate_wait_timeout,
)
from dutchmate_core.workflows.capture import (
    CaptureEventSource,
    CaptureReconnect,
    CaptureSessionStorage,
    CaptureWorkflow,
    ReconnectedCaptureSource,
)
from dutchmate_core.workflows.device_actions import (
    DeviceActionError,
    DeviceActionResult,
    DeviceActionRunner,
)
from dutchmate_core.workflows.uart_send import (
    ActiveUartSendSession,
    UartSendError,
    UartSendResult,
    UartSendSessionStorage,
    UartSendWorkflow,
)


class DeviceCoreRuntimeError(RuntimeError):
    """Raised when the runtime cannot perform the requested operation."""


ConnectionState = Literal["connected", "disconnected", "reconnecting"]


class DeviceCoreSessionStorage(CaptureSessionStorage, UartSendSessionStorage, Protocol):
    """Capture and bounded-query storage operations required by the runtime."""

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
    active_workflow: SessionWorkflow | None = None
    reconnect_remaining_s: float | None = None
    retention: SessionRetentionStatus = SessionRetentionStatus()


class _SessionCaptureSource:
    """Map one live connection source onto a new session-local segment zero."""

    def __init__(self, source: CaptureEventSource, segment: SegmentContext) -> None:
        self._source = source
        self._source_segment_id = segment.segment_id
        self.segment = replace(segment, segment_id=0)

    def read_event(self) -> BackendEvent | None:
        event = self._source.read_event()
        if event is None:
            return None
        if event.segment_id != self._source_segment_id:
            raise BackendInputError("backend event source changed its bound segment ID")
        return replace(event, segment_id=0)

    def discard_pending_events(self) -> None:
        """Advance a wait cursor on the wrapped source when supported."""

        discard = getattr(self._source, "discard_pending_events", None)
        if callable(discard):
            discard()

    def close(self) -> None:
        """Close the live source represented by this session-local view."""

        close = getattr(self._source, "close", None)
        if callable(close):
            close()


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
        reconnect_timeout_s: float = DEFAULT_RECONNECT_TIMEOUT_S,
        backend_reconnect: CaptureReconnect | None = None,
        action_wall_clock: Callable[[], datetime] | None = None,
        uart_wall_clock: Callable[[], datetime] | None = None,
        uart_monotonic_ns: Callable[[], int] | None = None,
        uart_attempt_id_factory: Callable[[], str] | None = None,
    ) -> None:
        self._message_source = message_source
        self._capture_clock = capture_clock
        self._status_clock = capture_clock or time.monotonic
        self._backend_reconnect = backend_reconnect
        self._session_store = session_store
        self._session_mutation_lock = RLock()
        self._capture_workflow = CaptureWorkflow(
            session_store=self._session_store,
            mutation_lock=self._session_mutation_lock,
        )
        self._uart_send_workflow = (
            UartSendWorkflow(
                sender=uart_sender,
                session_store=self._session_store,
                mutation_lock=self._session_mutation_lock,
                wall_clock=uart_wall_clock,
                monotonic_ns=uart_monotonic_ns,
                attempt_id_factory=uart_attempt_id_factory,
                backend_mode=backend_mode,
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
        self._connected = False
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
        self._active_session_id: str | None = None
        self._active_session_handle: SessionHandle | None = None
        self._active_segment_context: SegmentContext | None = None
        self._active_session_terminalized = False
        self._active_workflow: SessionWorkflow | None = None
        self._capture_in_progress = False
        self._reconnect_timeout_s = reconnect_timeout_s
        self._reconnect_deadline: float | None = None
        self._operation_lock = RLock()
        self._closing = False
        self._closed = False
        self._close_complete = Event()
        self._close_error: BaseException | None = None
        self._reconnect_in_progress = False
        self._reconnect_complete = Event()
        self._reconnect_complete.set()
        self._reconnect_cleanup_error: BaseException | None = None

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
                reconnect_in_progress = False
            else:
                self._closing = True
                first_closer = True
                source = self._message_source
                self._message_source = None
                reconnect_in_progress = self._reconnect_in_progress
                self._mark_backend_disconnected()

        if not first_closer:
            self._close_complete.wait()
            with self._operation_lock:
                retained_error = self._close_error
            if retained_error is not None:
                raise retained_error
            return

        close_error: BaseException | None = None
        try:
            if source is not None:
                self._close_event_source(source)
        except BaseException as exc:
            close_error = exc
        finally:
            if reconnect_in_progress:
                self._reconnect_complete.wait()
            with self._operation_lock:
                if close_error is None:
                    close_error = self._reconnect_cleanup_error
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
            self._connected = True
            self._commanded_boot_mode = None
            self._backend_mode = info.mode
            self._backend_info = info
            self._backend_capabilities = info.capabilities
            self._integrity = integrity_for_backend(info.mode)
            self._port = info.port
        return self.status()

    def disconnect(self) -> DeviceCoreStatus:
        """Mark the Debug Helper connection as disconnected."""

        with self._operation_lock:
            self._connected = False
            self._commanded_boot_mode = None
            self._backend_info = None
            self._backend_capabilities = frozenset()
            self._segment_context = None
            self._integrity = None
        return self.status()

    def status(self) -> DeviceCoreStatus:
        """Return the current service-facing status snapshot."""

        with self._operation_lock:
            source_segment = getattr(self._message_source, "segment", None)
            if self._connected and isinstance(source_segment, SegmentContext):
                self._segment_context = source_segment
            reconnect_remaining_s = (
                max(0.0, self._reconnect_deadline - self._status_clock())
                if self._reconnect_deadline is not None
                else None
            )
            connection_state: ConnectionState = (
                "reconnecting"
                if self._reconnect_deadline is not None
                else "connected"
                if self._connected
                else "disconnected"
            )
            retention = getattr(
                self._session_store,
                "retention_status",
                SessionRetentionStatus(),
            )
            return DeviceCoreStatus(
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
                active_workflow=self._active_workflow,
                reconnect_remaining_s=reconnect_remaining_s,
                retention=retention,
            )

    def apply_hardware_config(
        self,
        config: HardwareGpioConfig,
    ) -> dict[GpioRoleName, GpioControlChannelState]:
        """Apply configured GPIO modes after a Debug Helper hello is available."""

        with self._operation_lock:
            self._require_connected()
            self._require_no_active_capture()
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
        with self._operation_lock:
            self._require_connected()
            self._require_no_active_capture()
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
                if affects_boot_state:
                    self._commanded_boot_mode = None
                raise
            if state.last_rejected is not None:
                if (
                    affects_boot_state
                    and state.last_rejected.error in {"hardware_fault", "timeout"}
                ):
                    self._commanded_boot_mode = None
            elif state.state == "configured":
                if request.role == "boot":
                    self._commanded_boot_mode = "normal"
                elif self._gpio_registry.find_by_role("boot") is None:
                    self._commanded_boot_mode = None
            return state

    def reset_dut(self, *, pulse_ms: int = 100) -> DeviceActionResult:
        """Pulse the configured DUT reset role."""

        with self._operation_lock:
            self._require_connected()
            self._require_no_active_capture()
            return self._action_runner.reset_dut(pulse_ms=pulse_ms)

    def set_boot_mode(self, *, mode: str) -> DeviceActionResult:
        """Set the configured DUT boot/control role."""

        with self._operation_lock:
            self._require_connected()
            self._require_no_active_capture()
            try:
                result = self._action_runner.set_boot_mode(mode=mode)
            except DeviceActionError as exc:
                if exc.error not in {
                    "invalid_command",
                    "invalid_argument",
                    "not_configured",
                    "capture_active",
                }:
                    self._commanded_boot_mode = None
                raise
            if result.mode is None:
                raise DeviceCoreRuntimeError("Accepted boot-mode result omitted mode")
            self._commanded_boot_mode = result.mode
            return result

    def capture_uart(self, *, duration_s: float) -> SessionSummary:
        """Capture UART and telemetry messages into one filesystem session."""

        duration_s = validate_capture_duration(duration_s)
        return self._run_capture_workflow(
            duration_s=duration_s,
            command=f"capture --seconds {duration_s:g}",
            workflow="capture",
        )

    def run_boot_test(self, *, duration_s: float) -> SessionSummary:
        """Reset the DUT and capture its boot UART into one session."""

        duration_s = validate_capture_duration(duration_s)
        return self._run_capture_workflow(
            duration_s=duration_s,
            command=f"boot-test --seconds {duration_s:g}",
            workflow="boot_test",
            required_role="reset",
            start_action=self._action_runner.reset_dut,
        )

    def wait_pattern(
        self,
        *,
        pattern: str,
        timeout_s: float,
    ) -> WaitPatternResult:
        """Capture new UART evidence until one literal completes or time expires."""

        validated_pattern = validate_wait_pattern(pattern)
        validated_timeout = validate_wait_timeout(timeout_s)
        detector_patterns = (validated_pattern,) + tuple(
            pattern_name
            for pattern_name in DEFAULT_PATTERNS
            if pattern_name != validated_pattern
        )
        summary = self._run_capture_workflow(
            duration_s=validated_timeout,
            command="wait-pattern",
            workflow="wait_pattern",
            required_capability="uart_receive",
            uart_processor=UartCaptureProcessor(
                pattern_detector=PatternDetector(detector_patterns)
            ),
            requested_pattern=validated_pattern,
            discard_preexisting=True,
        )
        if summary.matched is None or summary.wait_pattern != validated_pattern:
            raise DeviceCoreRuntimeError("Wait-pattern session result is incomplete")
        match = (
            self._session_store.load_detected_pattern(
                summary.session_id,
                summary.detected_pattern_index,
            )
            if summary.detected_pattern_index is not None
            else None
        )
        if match is not None and match.pattern != validated_pattern:
            raise DeviceCoreRuntimeError("Wait-pattern detected record does not match request")
        return WaitPatternResult(
            summary=summary,
            pattern=validated_pattern,
            matched=summary.matched,
            match=match,
        )

    def send_uart(
        self,
        *,
        cmd: str,
        append_newline: bool = True,
        force: bool = False,
    ) -> UartSendResult:
        """Validate and transmit one public UTF-8 UART command."""

        payload = prepare_uart_send_payload(cmd, append_newline=append_newline)
        if not isinstance(force, bool):
            raise UartSendValidationError("UART send force must be a boolean")
        with self._session_mutation_lock, self._operation_lock:
            effective_capabilities = apply_capability_policy(
                self._backend_capabilities,
                self._capability_policy,
            )
            if "uart_send" not in effective_capabilities:
                disabled_by_policy = (
                    ["hardware.uart.tx_enabled"]
                    if "uart_send" in self._backend_capabilities
                    and not self._capability_policy.uart_send.tx_policy_enabled
                    else []
                )
                raise UartSendError(
                    error="unsupported_capability",
                    detail="Operation requires effective capability 'uart_send'",
                    context={
                        "operation": "uart_send",
                        "backend_mode": self._backend_mode,
                        "required_capabilities": ["uart_send"],
                        "available_capabilities": sorted(effective_capabilities),
                        "backend_capabilities": sorted(self._backend_capabilities),
                        "disabled_by_policy": disabled_by_policy,
                    },
                )
            active_session: ActiveUartSendSession | None = None
            if self._capture_in_progress:
                if not force:
                    raise UartSendError(
                        error="capture_active",
                        detail="UART receive workflow is active; explicit force is required",
                    )
                if self._active_session_handle is None or self._active_segment_context is None:
                    raise UartSendError(
                        error="capture_active",
                        detail="UART receive workflow has not published its session yet",
                    )
                active_session = ActiveUartSendSession(
                    handle=self._active_session_handle,
                    segment=self._active_segment_context,
                )
            self._require_connected()
            if self._uart_send_workflow is None:
                raise DeviceCoreRuntimeError("UART sender is not configured")
            try:
                return self._uart_send_workflow.run(
                    payload,
                    active_session=active_session,
                )
            except UartSendError as exc:
                if exc.error == "backend_input_error":
                    if self._message_source is not None:
                        self._close_event_source(self._message_source)
                    self._mark_backend_disconnected()
                    if active_session is not None:
                        self._session_store.fail_session(
                            active_session.handle,
                            end_reason="backend_input_error",
                            error_code="backend_input_error",
                            detail=exc.detail,
                        )
                        self._active_session_terminalized = True
                if exc.session_terminalized:
                    self._active_session_terminalized = True
                raise

    def _run_capture_workflow(
        self,
        *,
        duration_s: float,
        command: str,
        workflow: SessionWorkflow,
        required_role: str | None = None,
        required_capability: BackendCapability | None = None,
        start_action: Callable[[], DeviceActionResult] | None = None,
        uart_processor: UartCaptureProcessor | None = None,
        requested_pattern: str | None = None,
        discard_preexisting: bool = False,
    ) -> SessionSummary:
        with self._operation_lock:
            effective_capabilities = apply_capability_policy(
                self._backend_capabilities,
                self._capability_policy,
            )
            if (
                required_capability is not None
                and required_capability not in effective_capabilities
            ):
                raise DeviceActionError(
                    error="unsupported_capability",
                    detail=f"Operation requires effective capability '{required_capability}'",
                    context={
                        "operation": workflow,
                        "backend_mode": self._backend_mode,
                        "required_capabilities": [required_capability],
                        "available_capabilities": sorted(effective_capabilities),
                        "backend_capabilities": sorted(self._backend_capabilities),
                        "disabled_by_policy": [],
                    },
                )
            self._require_connected()
            self._require_no_active_capture()
            if self._message_source is None:
                raise DeviceCoreRuntimeError("Capture message source is not configured")
            if required_role is not None:
                self._gpio_registry.require_role_configured(
                    required_role,
                    operation=workflow,
                )
            source = self._session_capture_source(self._message_source)
            source_segment = getattr(source, "segment", None)
            backend_snapshot = self._backend_snapshot(
                segment_context=(
                    source_segment if isinstance(source_segment, SegmentContext) else None
                )
            )
            firmware = self._backend_info.firmware if self._backend_info is not None else None
            device = self._backend_info.device if self._backend_info is not None else None
            self._capture_in_progress = True
            self._active_workflow = workflow
            commanded_boot_mode = self._commanded_boot_mode
            self._active_segment_context = (
                source_segment if isinstance(source_segment, SegmentContext) else None
            )

        reconnect = (
            partial(
                self._reconnect_capture_source,
                expected_snapshot=backend_snapshot,
            )
            if backend_snapshot is not None and self._backend_reconnect is not None
            else None
        )

        try:
            summary = self._capture_workflow.run(
                source=source,
                duration_s=duration_s,
                command=command,
                firmware=firmware,
                device=device,
                monotonic_clock=self._capture_clock,
                reconnect_timeout_s=self._reconnect_timeout_s,
                backend_snapshot=backend_snapshot,
                workflow=workflow,
                commanded_boot_mode=commanded_boot_mode,
                uart_processor=uart_processor,
                start_action=start_action,
                on_session_handle_started=self._set_active_session,
                reconnect=reconnect,
                on_backend_disconnected=self._mark_backend_disconnected,
                requested_pattern=requested_pattern,
                discard_preexisting=discard_preexisting,
                is_session_terminalized=self._is_active_session_terminalized,
            )
            if summary.integrity is not None:
                with self._operation_lock:
                    self._integrity = summary.integrity
            return summary
        except BackendInputError:
            self._mark_backend_disconnected()
            raise
        finally:
            with self._operation_lock:
                self._capture_in_progress = False
                self._active_session_id = None
                self._active_session_handle = None
                self._active_segment_context = None
                self._active_session_terminalized = False
                self._active_workflow = None
                self._reconnect_deadline = None

    def _set_active_session(self, handle: SessionHandle) -> None:
        with self._operation_lock:
            self._active_session_id = handle.session_id
            self._active_session_handle = handle

    def _is_active_session_terminalized(self) -> bool:
        with self._operation_lock:
            return self._active_session_terminalized

    def _mark_backend_disconnected(self) -> None:
        with self._operation_lock:
            self._connected = False
            self._commanded_boot_mode = None
            self._backend_info = None
            self._backend_capabilities = frozenset()
            self._segment_context = None
            self._integrity = None

    def _reconnect_capture_source(
        self,
        *,
        expected_snapshot: BackendSnapshot,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        reconnect = self._backend_reconnect
        if reconnect is None:
            return None
        with self._operation_lock:
            if self._closing or self._closed:
                return None
            self._reconnect_in_progress = True
            self._reconnect_cleanup_error = None
            self._reconnect_complete.clear()
            self._reconnect_deadline = deadline
            self._message_source = None
        try:
            replacement = reconnect(segment_id=segment_id, deadline=deadline)
            if replacement is None:
                return None
            try:
                self._validate_replacement(expected_snapshot, replacement.backend_snapshot)
            except Exception:
                try:
                    self._close_event_source(replacement.source)
                except BaseException as exc:
                    with self._operation_lock:
                        if self._closing:
                            self._reconnect_cleanup_error = exc
                    raise
                raise
            with self._operation_lock:
                reject_replacement = self._closing or self._closed
                if not reject_replacement:
                    snapshot = replacement.backend_snapshot
                    self._message_source = replacement.source
                    self._connected = True
                    self._backend_mode = snapshot.info.mode
                    self._backend_info = snapshot.info
                    self._backend_capabilities = snapshot.info.capabilities
                    self._segment_context = snapshot.segment
                    self._active_segment_context = snapshot.segment
                    self._integrity = snapshot.integrity
                    self._port = snapshot.info.port
            if reject_replacement:
                try:
                    self._close_event_source(replacement.source)
                except BaseException as exc:
                    with self._operation_lock:
                        self._reconnect_cleanup_error = exc
                    raise
                return None
            return replacement
        finally:
            with self._operation_lock:
                self._reconnect_in_progress = False
                self._reconnect_deadline = None
            self._reconnect_complete.set()

    def _validate_replacement(
        self,
        expected: BackendSnapshot,
        replacement: BackendSnapshot,
    ) -> None:
        expected_identity = (
            expected.info.mode,
            expected.info.port,
            expected.info.device,
            expected.info.firmware,
        )
        replacement_identity = (
            replacement.info.mode,
            replacement.info.port,
            replacement.info.device,
            replacement.info.firmware,
        )
        if replacement_identity != expected_identity:
            raise ValueError("reconnected backend identity does not match active session")
        if replacement.capability_policy != self._capability_policy:
            raise ValueError("reconnected backend capability policy changed")

    @staticmethod
    def _close_event_source(source: CaptureEventSource) -> None:
        close = getattr(source, "close", None)
        if callable(close):
            close()

    def _require_connected(self) -> None:
        if not self._connected:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    def _require_no_active_capture(self) -> None:
        if self._capture_in_progress:
            raise DeviceActionError(
                error="capture_active",
                detail="capture is already active",
            )

    @staticmethod
    def _session_capture_source(source: CaptureEventSource) -> CaptureEventSource:
        segment = getattr(source, "segment", None)
        if not isinstance(segment, SegmentContext) or segment.segment_id == 0:
            return source
        return _SessionCaptureSource(source, segment)

    def _backend_snapshot(
        self,
        *,
        segment_context: SegmentContext | None = None,
    ) -> BackendSnapshot | None:
        if self._backend_info is None:
            return None
        if self._integrity is None:
            raise DeviceCoreRuntimeError("Connected backend integrity state is unavailable")
        return BackendSnapshot(
            info=self._backend_info,
            capabilities=apply_capability_policy(
                self._backend_capabilities,
                self._capability_policy,
            ),
            capability_policy=self._capability_policy,
            segment=(segment_context if segment_context is not None else self._segment_context),
            integrity=self._integrity,
        )
