"""Service-facing Device Core runtime composition."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import TypeAlias, cast

from dutchmate_core.backends.contracts import (
    BackendCapability,
    BackendCapabilityPolicy,
    BackendInfo,
    BackendMode,
    BackendSnapshot,
    SegmentContext,
    UartIntegrity,
    UartSendCapabilityPolicy,
    apply_capability_policy,
    integrity_for_backend,
)
from dutchmate_core.backends.settings import DEFAULT_RECONNECT_TIMEOUT_S
from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.transport import CommandTransport
from dutchmate_core.gpio_config.config import HardwareGpioConfig
from dutchmate_core.gpio_config.configurator import GpioConfigurator
from dutchmate_core.gpio_config.modes import (
    GpioControlChannel,
    GpioControlChannelState,
    GpioModeRegistry,
    GpioModeRequestSource,
    GpioRoleName,
)
from dutchmate_core.session_store.store import SessionStore, SessionSummary, SessionWorkflow
from dutchmate_core.validation import (
    validate_capture_duration,
    validate_gpio_configuration,
    validate_gpio_source,
)
from dutchmate_core.workflows.capture import (
    CaptureEventSource,
    CaptureRecorder,
    TransportCaptureRunner,
)
from dutchmate_core.workflows.device_actions import (
    DeviceActionError,
    DeviceActionResult,
    DeviceActionRunner,
)

DeviceCoreTransport: TypeAlias = CommandTransport


class DeviceCoreRuntimeError(RuntimeError):
    """Raised when the runtime cannot perform the requested operation."""


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
    backend_mode: BackendMode | None = None
    backend_capabilities: tuple[str, ...] = ()
    capability_policy: BackendCapabilityPolicy | None = None
    timestamp_provenance: SegmentContext | None = None
    integrity: UartIntegrity | None = None


class DeviceCoreRuntime:
    """Compose Phase 1 core services behind one service-facing object."""

    def __init__(
        self,
        *,
        transport: DeviceCoreTransport,
        session_store: SessionStore | None = None,
        session_root: Path | str = Path(".dutchmate/sessions"),
        gpio_registry: GpioModeRegistry | None = None,
        message_source: CaptureEventSource | None = None,
        capture_clock: Callable[[], float] | None = None,
        port: str | None = None,
        backend_mode: BackendMode | None = None,
        tx_policy_enabled: bool = False,
        segment_context: SegmentContext | None = None,
        reconnect_timeout_s: float = DEFAULT_RECONNECT_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._message_source = message_source
        self._capture_clock = capture_clock
        self._session_store = session_store or SessionStore(root=session_root)
        self._gpio_registry = gpio_registry or GpioModeRegistry()
        self._gpio_configurator = GpioConfigurator(
            registry=self._gpio_registry,
            transport=self._transport,
        )
        self._action_runner = DeviceActionRunner(
            registry=self._gpio_registry,
            transport=self._transport,
        )
        self._port = port
        self._hello: HelloMessage | None = None
        self._connected = False
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
        self._reconnect_timeout_s = reconnect_timeout_s
        self._operation_lock = RLock()

    @property
    def session_store(self) -> SessionStore:
        """Filesystem-backed session store used by this runtime."""

        return self._session_store

    @property
    def gpio_registry(self) -> GpioModeRegistry:
        """GPIO role configuration state used by this runtime."""

        return self._gpio_registry

    def record_hello(self, hello: HelloMessage, *, port: str | None = None) -> DeviceCoreStatus:
        """Record a validated Debug Helper hello message."""

        with self._operation_lock:
            self._hello = hello
            self._connected = True
            self._backend_mode = "enhanced"
            if port is not None:
                self._port = port
            self._backend_capabilities = _normalize_hello_capabilities(hello.capabilities)
            self._integrity = integrity_for_backend("enhanced")
            self._backend_info = (
                BackendInfo(
                    mode="enhanced",
                    port=self._port,
                    device=hello.device,
                    firmware=hello.firmware,
                    capabilities=self._backend_capabilities,
                )
                if self._port is not None
                else None
            )
        return self.status()

    def record_basic_connection(self, info: BackendInfo) -> DeviceCoreStatus:
        """Record an opened Basic backend without requiring a hello message."""

        if info.mode != "basic" or info.device is not None or info.firmware is not None:
            raise ValueError("Basic backend identity must omit device and firmware")
        with self._operation_lock:
            self._hello = None
            self._connected = True
            self._backend_mode = "basic"
            self._backend_info = info
            self._backend_capabilities = info.capabilities
            self._integrity = integrity_for_backend("basic")
            self._port = info.port
        return self.status()

    def disconnect(self) -> DeviceCoreStatus:
        """Mark the Debug Helper connection as disconnected."""

        with self._operation_lock:
            self._hello = None
            self._connected = False
            self._backend_info = None
            self._backend_capabilities = frozenset()
            self._segment_context = None
            self._integrity = None
        return self.status()

    def status(self) -> DeviceCoreStatus:
        """Return the current service-facing status snapshot."""

        with self._operation_lock:
            source_segment = getattr(self._message_source, "segment", None)
            if isinstance(source_segment, SegmentContext):
                self._segment_context = source_segment
            return DeviceCoreStatus(
                connected=self._connected,
                port=self._port,
                firmware=self._hello.firmware if self._hello is not None else None,
                device=self._hello.device if self._hello is not None else None,
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
                backend_mode=self._backend_mode,
                backend_capabilities=tuple(sorted(self._backend_capabilities)),
                capability_policy=(
                    self._capability_policy if self._backend_mode is not None else None
                ),
                timestamp_provenance=(self._segment_context),
                integrity=self._integrity,
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
            return self._gpio_configurator.configure_mode(
                role=request.role,
                channel=request.channel,
                dut_signal=request.dut_signal,
                mode=request.mode,
                active_level=request.active_level,
                idle_level=request.idle_level,
                source=source_name,
            )

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
            return self._action_runner.set_boot_mode(mode=mode)

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

    def _run_capture_workflow(
        self,
        *,
        duration_s: float,
        command: str,
        workflow: SessionWorkflow,
        required_role: str | None = None,
        start_action: Callable[[], DeviceActionResult] | None = None,
    ) -> SessionSummary:
        active_session_id: str | None = None
        recorder: CaptureRecorder | None = None
        terminalized = False
        native_session = False
        try:
            with self._operation_lock:
                self._require_connected()
                self._require_no_active_capture()
                if self._message_source is None:
                    raise DeviceCoreRuntimeError("Capture message source is not configured")

                runner = TransportCaptureRunner(
                    transport=self._message_source,
                    duration_s=duration_s,
                    monotonic_clock=self._capture_clock,
                )
                if required_role is not None:
                    self._gpio_registry.require_role_configured(required_role)

                backend_snapshot = self._backend_snapshot()
                native_session = backend_snapshot is not None
                recorder = CaptureRecorder.start(
                    session_store=self._session_store,
                    command=command,
                    firmware=self._hello.firmware if self._hello is not None else None,
                    device=self._hello.device if self._hello is not None else None,
                    backend_snapshot=backend_snapshot,
                    workflow=workflow if native_session else None,
                    duration_s=duration_s if native_session else None,
                    reconnect_timeout_s=(self._reconnect_timeout_s if native_session else None),
                )
                active_session_id = recorder.session_id
                self._active_session_id = active_session_id

                if start_action is not None:
                    start_action()

            runner.run(recorder)
            recorder.finalize()
            if native_session and not recorder.terminalized:
                self._session_store.complete_session(recorder.session_handle)
            terminalized = True
            summary = self._session_store.summarize_session(recorder.session_id)
            if summary.integrity is not None:
                with self._operation_lock:
                    self._integrity = summary.integrity
            return summary
        except Exception as exc:
            if (
                recorder is not None
                and native_session
                and not terminalized
                and not recorder.terminalized
            ):
                recorder.finalize()
                if recorder.terminalized:
                    terminalized = True
                    summary = self._session_store.summarize_session(recorder.session_id)
                    if summary.integrity is not None:
                        with self._operation_lock:
                            self._integrity = summary.integrity
                    return summary
                self._session_store.fail_session(
                    recorder.session_handle,
                    end_reason="backend_error",
                    error_code=(
                        exc.error if isinstance(exc, DeviceActionError) else "internal_error"
                    ),
                    detail=str(exc),
                )
            raise
        finally:
            if active_session_id is not None:
                with self._operation_lock:
                    if self._active_session_id == active_session_id:
                        self._active_session_id = None

    def _require_connected(self) -> None:
        if not self._connected:
            raise DeviceCoreRuntimeError("Debug Helper is not connected")

    def _require_no_active_capture(self) -> None:
        if self._active_session_id is not None:
            raise DeviceActionError(
                error="capture_active",
                detail="capture is already active",
            )

    def _backend_snapshot(self) -> BackendSnapshot | None:
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
            segment=self._segment_context,
            integrity=self._integrity,
        )


def _normalize_hello_capabilities(
    capabilities: tuple[str, ...],
) -> frozenset[BackendCapability]:
    normalized: set[BackendCapability] = set()
    for capability in capabilities:
        normalized_name = "uart_receive" if capability == "uart_capture" else capability
        normalized.add(cast(BackendCapability, normalized_name))
    return frozenset(normalized)
