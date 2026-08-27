"""Service-owned backend reopen and replaceable-control composition."""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import suppress
from threading import RLock
from typing import Protocol

from dutchmate_core.backends.basic import (
    BasicBackendConnection,
    BasicBackendEventSource,
)
from dutchmate_core.backends.contracts import (
    BackendCapabilityPolicy,
    BackendInfo,
    BackendInputError,
    BackendSnapshot,
    BackendUartSendResult,
    ControlState,
    DeviceControl,
    SegmentContext,
    UartSendCapabilityPolicy,
    UartSender,
    apply_capability_policy,
    integrity_for_backend,
)
from dutchmate_core.backends.enhanced import (
    EnhancedCaptureEventSource,
    EnhancedDeviceControl,
    EnhancedUartSender,
    backend_input_error_from_protocol,
    normalize_enhanced_hello,
)
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.device_connection.errors import ProtocolError
from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.serial_transport import SerialCommandTransport
from dutchmate_core.workflows.capture import (
    CaptureEventSource,
    ReconnectedCaptureSource,
)


class OpenCaptureReplacement(Protocol):
    """Open one segment-bound replacement source."""

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        """Return a fully prepared replacement or raise for a failed attempt."""


class OpenBasicConnection(Protocol):
    """Open one raw Basic connection from resolved settings."""

    def __call__(self, settings: BackendSettings) -> BasicBackendConnection:
        """Return an opened Basic connection."""


class OpenEnhancedTransport(Protocol):
    """Open one Enhanced serial command transport."""

    def __call__(
        self,
        *,
        port: str,
        baudrate: int,
    ) -> SerialCommandTransport:
        """Return an opened Enhanced command transport."""


class RetryingCaptureReconnect:
    """Retry backend opening within the workflow-supplied monotonic deadline."""

    def __init__(
        self,
        *,
        current_source: CaptureEventSource,
        open_replacement: OpenCaptureReplacement,
        on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        retry_interval_s: float = 0.1,
    ) -> None:
        if retry_interval_s <= 0:
            raise ValueError("reconnect retry interval must be positive")
        self._current_source = current_source
        self._open_replacement = open_replacement
        self._on_connected = on_connected
        self._clock = monotonic_clock
        self._sleep = sleep
        self._retry_interval_s = retry_interval_s

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        self._close_source(self._current_source)
        while self._clock() < deadline:
            try:
                replacement = self._open_replacement(
                    segment_id=segment_id,
                    deadline=deadline,
                )
            except BackendInputError:
                raise
            except Exception:
                self._wait_for_retry(deadline)
                continue
            if self._clock() >= deadline:
                self._close_source(replacement.source)
                return None
            self._current_source = replacement.source
            if self._on_connected is not None:
                self._on_connected(replacement)
            return replacement
        return None

    def _wait_for_retry(self, deadline: float) -> None:
        remaining_s = deadline - self._clock()
        if remaining_s > 0:
            self._sleep(min(self._retry_interval_s, remaining_s))

    @staticmethod
    def _close_source(source: CaptureEventSource) -> None:
        close = getattr(source, "close", None)
        if not callable(close):
            return
        with suppress(Exception):
            close()


class ReplaceableDeviceControl:
    """Keep runtime control ports stable while Enhanced transports are replaced."""

    def __init__(self, control: DeviceControl) -> None:
        self._control = control
        self._lock = RLock()

    def replace(self, control: DeviceControl) -> None:
        """Publish a newly connected backend control adapter."""

        with self._lock:
            self._control = control

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        with self._lock:
            return self._control.configure_gpio_mode(
                channel=channel,
                mode=mode,
                active_level=active_level,
                idle_level=idle_level,
            )

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        with self._lock:
            return self._control.pulse_control(channel=channel, pulse_ms=pulse_ms)

    def set_control_state(self, *, channel: str, state: ControlState) -> int | None:
        with self._lock:
            return self._control.set_control_state(channel=channel, state=state)


class ReplaceableUartSender:
    """Keep the runtime UART-send port stable across backend replacement."""

    def __init__(self, sender: UartSender) -> None:
        self._sender = sender
        self._lock = RLock()

    def replace(self, sender: UartSender) -> None:
        """Publish a newly connected UART-send adapter."""

        with self._lock:
            self._sender = sender

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        with self._lock:
            return self._sender.send_uart(data)


def build_basic_capture_reconnect(
    *,
    settings: BackendSettings,
    current_source: BasicBackendEventSource,
    open_connection: OpenBasicConnection,
    sender: ReplaceableUartSender,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> RetryingCaptureReconnect:
    """Build the bounded reopen adapter for one selected Basic backend."""

    opened_senders: dict[int, BasicBackendConnection] = {}

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        del deadline
        connection = open_connection(settings)
        source = BasicBackendEventSource(connection, segment_id=segment_id)
        opened_senders[id(source)] = connection
        return ReconnectedCaptureSource(
            source=source,
            backend_snapshot=source.snapshot,
        )

    def publish_sender(replacement: ReconnectedCaptureSource) -> None:
        sender.replace(opened_senders.pop(id(replacement.source)))

    return RetryingCaptureReconnect(
        current_source=current_source,
        open_replacement=open_replacement,
        on_connected=publish_sender,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def build_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    current_source: EnhancedCaptureEventSource,
    expected_info: BackendInfo,
    control: ReplaceableDeviceControl,
    sender: ReplaceableUartSender,
    open_transport: OpenEnhancedTransport,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> RetryingCaptureReconnect:
    """Build bounded Enhanced reopen, hello, provenance, and control replacement."""

    opened_adapters: dict[int, tuple[EnhancedDeviceControl, EnhancedUartSender]] = {}

    def open_replacement(
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource:
        serial_port = settings.serial_port
        if serial_port is None:
            raise ValueError("Enhanced reconnect requires an explicit serial port")
        transport = open_transport(
            port=serial_port,
            baudrate=settings.baudrate,
        )
        try:
            try:
                hello = read_enhanced_hello(transport)
            except BackendInputError:
                raise
            except ProtocolError as exc:
                raise backend_input_error_from_protocol(exc) from exc
            except RuntimeError as exc:
                raise BackendInputError(str(exc), backend_mode="enhanced") from exc
            info = normalize_enhanced_hello(hello, port=serial_port)
            _require_matching_enhanced_identity(expected_info, info)
            source = EnhancedCaptureEventSource(
                transport,
                segment_id=segment_id,
                source_origin_us=None,
            )
            while source.segment is None and monotonic_clock() < deadline:
                source.prime_segment()
            if source.segment is None:
                raise TimeoutError("Enhanced timestamp provenance was not established")
            replacement = ReconnectedCaptureSource(
                source=source,
                backend_snapshot=_backend_snapshot(
                    info=info,
                    segment=source.segment,
                    tx_enabled=settings.tx_enabled,
                ),
            )
            opened_adapters[id(source)] = (
                EnhancedDeviceControl(transport),
                EnhancedUartSender(transport),
            )
            return replacement
        except Exception:
            transport.close()
            raise

    def publish_control(replacement: ReconnectedCaptureSource) -> None:
        replacement_control, replacement_sender = opened_adapters.pop(
            id(replacement.source)
        )
        control.replace(replacement_control)
        sender.replace(replacement_sender)

    return RetryingCaptureReconnect(
        current_source=current_source,
        open_replacement=open_replacement,
        on_connected=publish_control,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def read_enhanced_hello(transport: SerialCommandTransport) -> HelloMessage:
    """Read and validate one Debug Helper hello message."""

    message = transport.read_message()
    if not isinstance(message, HelloMessage):
        message_name = type(message).__name__
        raise RuntimeError(f"Expected Debug Helper hello message, got {message_name}")
    return message


def _backend_snapshot(
    *,
    info: BackendInfo,
    segment: SegmentContext,
    tx_enabled: bool,
) -> BackendSnapshot:
    policy = BackendCapabilityPolicy(
        uart_send=UartSendCapabilityPolicy(tx_policy_enabled=tx_enabled)
    )
    return BackendSnapshot(
        info=info,
        capabilities=apply_capability_policy(info.capabilities, policy),
        capability_policy=policy,
        segment=segment,
        integrity=integrity_for_backend(info.mode),
    )


def _require_matching_enhanced_identity(
    expected: BackendInfo,
    replacement: BackendInfo,
) -> None:
    if (
        replacement.mode != expected.mode
        or replacement.port != expected.port
        or replacement.device != expected.device
        or replacement.firmware != expected.firmware
    ):
        raise BackendInputError(
            "Reconnected Debug Helper identity changed",
            backend_mode="enhanced",
        )
