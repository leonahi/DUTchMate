"""Service-owned backend reopen and replaceable-control composition."""

from __future__ import annotations

import time
from collections.abc import Callable
from contextlib import suppress
from threading import Condition, Event, RLock, Thread, current_thread
from typing import Protocol, cast

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
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        """Return a fully prepared replacement or raise for a failed attempt."""


class ReplaceableCaptureSource(CaptureEventSource, Protocol):
    """Stable capture facade that exclusively owns concrete backend sources."""

    def wait_for_idle_disconnect(self, timeout_s: float) -> bool:
        """Wait for an idle disconnected source that can be claimed."""

    def close_current_source_for_reconnect(self, *, idle: bool = False) -> None:
        """Detach and close the consumed source before reconnect opening."""

    def replace_source(
        self,
        replacement: CaptureEventSource,
        *,
        backend_snapshot: BackendSnapshot | None = None,
    ) -> None:
        """Accept ownership of one validated concrete replacement."""

    def close(self) -> None:
        """Terminalize the stable facade and its current concrete source."""


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


class EnhancedReconnectHost(CaptureEventSource, DeviceControl, UartSender, Protocol):
    """Ready async Enhanced host used as source, control, and UART sender."""

    @property
    def info(self) -> BackendInfo: ...

    @property
    def segment(self) -> SegmentContext | None: ...

    def wait_for_segment(self, timeout_s: float) -> SegmentContext | None: ...

    def close(self) -> None: ...


class OpenEnhancedHost(Protocol):
    """Open one async Enhanced reconnect host."""

    def __call__(
        self,
        *,
        port: str,
        baudrate: int,
        segment_id: int,
    ) -> EnhancedReconnectHost: ...


class _LegacyOpenCaptureReplacement(Protocol):
    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource: ...


class BackendReconnectCoordinator:
    """Serialize idle and active reconnect attempts for one stable source owner."""

    def __init__(
        self,
        *,
        source_owner: ReplaceableCaptureSource,
        open_replacement: OpenCaptureReplacement,
        on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wait_for_idle_retry: Callable[[float], bool] | None = None,
        wait_for_active_retry: Callable[[float], bool] | None = None,
        active_retry_interval_s: float = 0.1,
        idle_initial_retry_s: float = 0.1,
        idle_max_retry_s: float = 2.0,
    ) -> None:
        if active_retry_interval_s <= 0:
            raise ValueError("active reconnect retry interval must be positive")
        if idle_initial_retry_s <= 0:
            raise ValueError("idle reconnect initial retry interval must be positive")
        if idle_max_retry_s <= 0:
            raise ValueError("idle reconnect maximum retry interval must be positive")
        if idle_initial_retry_s > idle_max_retry_s:
            raise ValueError(
                "idle reconnect initial retry interval must not exceed maximum"
            )

        self._source_owner = source_owner
        self._open_replacement = open_replacement
        self._on_connected = on_connected
        self._clock = monotonic_clock
        self._active_retry_interval_s = active_retry_interval_s
        self._idle_initial_retry_s = idle_initial_retry_s
        self._idle_max_retry_s = idle_max_retry_s
        self._condition = Condition()
        self._stop_requested = Event()
        self._wait_for_idle_retry = (
            wait_for_idle_retry
            if wait_for_idle_retry is not None
            else self._stop_requested.wait
        )
        if wait_for_active_retry is not None:
            self._active_retry_wait = wait_for_active_retry
        elif sleep is time.sleep:
            self._active_retry_wait = self._stop_requested.wait
        else:

            def deterministic_active_retry_wait(delay: float) -> bool:
                sleep(delay)
                return self._stop_requested.is_set()

            self._active_retry_wait = deterministic_active_retry_wait
        self._worker: Thread | None = None
        self._attempt_active = False
        self._attempt_owner: Thread | None = None
        self._closing = False
        self._closed = False
        self._close_error: BaseException | None = None

    def start(self) -> None:
        """Start the single non-daemon idle reconnect worker."""

        with self._condition:
            if self._closing or self._closed:
                raise RuntimeError("backend reconnect coordinator is closed")
            if self._worker is not None:
                raise RuntimeError("backend reconnect coordinator is already started")
            worker = Thread(
                target=self._run_idle,
                name="dutchmate-backend-reconnect",
                daemon=False,
            )
            self._worker = worker
            try:
                worker.start()
            except BaseException:
                self._worker = None
                raise

    def __call__(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        """Own one bounded active-workflow reconnect attempt."""

        with self._condition:
            if self._closing or self._closed:
                return None
            if self._attempt_active:
                raise RuntimeError("backend reconnect is already active")
            self._attempt_active = True
            self._attempt_owner = current_thread()
        try:
            self._source_owner.close_current_source_for_reconnect()
            return self._retry_active(segment_id=segment_id, deadline=deadline)
        finally:
            with self._condition:
                self._attempt_active = False
                self._attempt_owner = None
                self._condition.notify_all()

    def close(self) -> None:
        """Stop reconnect activity and join the idle worker exactly once."""

        with self._condition:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            if self._closing:
                first_closer = False
                worker = None
            else:
                first_closer = True
                self._closing = True
                self._stop_requested.set()
                worker = self._worker
                self._condition.notify_all()

            if not first_closer:
                self._condition.wait_for(lambda: self._closed)
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return

        close_error: BaseException | None = None
        try:
            if worker is not None and worker is not current_thread():
                worker.join()
            with self._condition:
                if self._attempt_owner is not current_thread():
                    self._condition.wait_for(lambda: not self._attempt_active)
        except BaseException as exc:
            close_error = exc
        finally:
            with self._condition:
                if self._close_error is None:
                    self._close_error = close_error
                retained_error = self._close_error
                self._closed = True
                self._condition.notify_all()

        if retained_error is not None:
            raise retained_error

    def _run_idle(self) -> None:
        try:
            while not self._stop_requested.is_set():
                if not self._source_owner.wait_for_idle_disconnect(0.1):
                    continue
                with self._condition:
                    if self._closing or self._closed:
                        return
                    if self._attempt_active:
                        self._condition.wait_for(
                            lambda: not self._attempt_active or self._closing
                        )
                        continue
                    self._attempt_active = True
                    self._attempt_owner = current_thread()
                try:
                    if self._stop_requested.is_set():
                        return
                    self._source_owner.close_current_source_for_reconnect(idle=True)
                    self._retry_idle()
                finally:
                    with self._condition:
                        self._attempt_active = False
                        self._attempt_owner = None
                        self._condition.notify_all()
        except BaseException as exc:
            self._retain_close_error(exc)

    def _retry_active(
        self,
        *,
        segment_id: int,
        deadline: float,
    ) -> ReconnectedCaptureSource | None:
        while not self._stop_requested.is_set() and self._clock() < deadline:
            try:
                replacement = self._open_replacement(
                    segment_id=segment_id,
                    deadline=deadline,
                    stop_requested=self._stop_requested,
                )
            except BackendInputError:
                raise
            except Exception:
                if self._wait_for_active_retry(deadline):
                    return None
                continue
            if self._stop_requested.is_set() or self._clock() >= deadline:
                self._close_rejected(replacement)
                return None
            return self._publish(replacement)
        return None

    def _retry_idle(self) -> None:
        retry_delay_s = self._idle_initial_retry_s
        while not self._stop_requested.is_set():
            try:
                replacement = self._open_replacement(
                    segment_id=0,
                    deadline=None,
                    stop_requested=self._stop_requested,
                )
            except Exception:
                if self._stop_requested.is_set():
                    return
                if self._wait_for_idle_retry(retry_delay_s):
                    return
                retry_delay_s = min(retry_delay_s * 2, self._idle_max_retry_s)
                continue
            if self._stop_requested.is_set():
                self._close_rejected(replacement)
                return
            self._publish(replacement)
            return

    def _wait_for_active_retry(self, deadline: float) -> bool:
        remaining_s = deadline - self._clock()
        if remaining_s > 0 and not self._stop_requested.is_set():
            interrupted = self._active_retry_wait(
                min(self._active_retry_interval_s, remaining_s)
            )
            return interrupted or self._stop_requested.is_set()
        return self._stop_requested.is_set()

    def _publish(
        self,
        replacement: ReconnectedCaptureSource,
    ) -> ReconnectedCaptureSource | None:
        callback_error: BaseException | None = None
        with self._condition:
            if self._closing or self._closed:
                publish = False
            else:
                publish = True
                try:
                    if self._on_connected is not None:
                        self._on_connected(replacement)
                except BaseException as exc:
                    callback_error = exc
                else:
                    if self._closing or self._closed:
                        publish = False
                    else:
                        self._source_owner.replace_source(
                            replacement.source,
                            backend_snapshot=replacement.backend_snapshot,
                        )
                        return ReconnectedCaptureSource(
                            source=self._source_owner,
                            backend_snapshot=replacement.backend_snapshot,
                        )

        if not publish or callback_error is not None:
            self._close_rejected(replacement)
        if callback_error is not None:
            raise callback_error
        return None

    def _close_rejected(self, replacement: ReconnectedCaptureSource) -> None:
        close = getattr(replacement.source, "close", None)
        if not callable(close):
            return
        try:
            close()
        except BaseException as exc:
            self._retain_close_error(exc)
            raise

    def _retain_close_error(self, error: BaseException) -> None:
        with self._condition:
            if self._close_error is None:
                self._close_error = error
            self._stop_requested.set()
            self._condition.notify_all()


class RetryingCaptureReconnect:
    """Retry backend opening within the workflow-supplied monotonic deadline."""

    def __init__(
        self,
        *,
        source_owner: ReplaceableCaptureSource,
        open_replacement: _LegacyOpenCaptureReplacement,
        on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        retry_interval_s: float = 0.1,
    ) -> None:
        if retry_interval_s <= 0:
            raise ValueError("reconnect retry interval must be positive")
        self._source_owner = source_owner
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
        self._source_owner.close_current_source_for_reconnect()
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
            self._source_owner.replace_source(replacement.source)
            try:
                if self._on_connected is not None:
                    self._on_connected(replacement)
            except BaseException:
                with suppress(BaseException):
                    self._source_owner.close()
                raise
            return ReconnectedCaptureSource(
                source=self._source_owner,
                backend_snapshot=replacement.backend_snapshot,
            )
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
        with suppress(BaseException):
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
    source_owner: ReplaceableCaptureSource,
    expected_snapshot: BackendSnapshot,
    open_connection: OpenBasicConnection,
    sender: ReplaceableUartSender,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> BackendReconnectCoordinator:
    """Build coordinated idle and active reopen for one selected Basic backend."""

    opened_senders: dict[int, BasicBackendConnection] = {}

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        del deadline
        if stop_requested.is_set():
            raise RuntimeError("backend reconnect coordinator is closing")
        connection = open_connection(settings)
        source = BasicBackendEventSource(connection, segment_id=segment_id)
        try:
            _require_matching_basic_snapshot(expected_snapshot, source.snapshot)
        except BaseException:
            with suppress(BaseException):
                source.close()
            raise
        opened_senders[id(source)] = connection
        return ReconnectedCaptureSource(
            source=source,
            backend_snapshot=source.snapshot,
        )

    def publish_sender(replacement: ReconnectedCaptureSource) -> None:
        sender.replace(opened_senders.pop(id(replacement.source)))

    return BackendReconnectCoordinator(
        source_owner=source_owner,
        open_replacement=open_replacement,
        on_connected=publish_sender,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def build_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    source_owner: ReplaceableCaptureSource,
    expected_info: BackendInfo,
    control: ReplaceableDeviceControl,
    sender: ReplaceableUartSender,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
    open_host: OpenEnhancedHost | None = None,
    open_transport: OpenEnhancedTransport | None = None,
) -> BackendReconnectCoordinator:
    """Build coordinated Enhanced reopen through the async host boundary."""

    if (open_host is None) == (open_transport is None):
        raise ValueError("Enhanced reconnect requires exactly one host opener")

    if open_host is not None:
        return _build_async_enhanced_capture_reconnect(
            settings=settings,
            source_owner=source_owner,
            expected_info=expected_info,
            control=control,
            sender=sender,
            open_host=open_host,
            monotonic_clock=monotonic_clock,
            sleep=sleep,
        )

    assert open_transport is not None
    return _build_legacy_enhanced_capture_reconnect(
        settings=settings,
        source_owner=source_owner,
        expected_info=expected_info,
        control=control,
        sender=sender,
        open_transport=open_transport,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def _build_async_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    source_owner: ReplaceableCaptureSource,
    expected_info: BackendInfo,
    control: ReplaceableDeviceControl,
    sender: ReplaceableUartSender,
    open_host: OpenEnhancedHost,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> BackendReconnectCoordinator:
    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        if stop_requested.is_set():
            raise RuntimeError("backend reconnect coordinator is closing")
        serial_port = settings.serial_port
        if serial_port is None:
            raise ValueError("Enhanced reconnect requires an explicit serial port")
        host = open_host(
            port=serial_port,
            baudrate=settings.baudrate,
            segment_id=segment_id,
        )
        try:
            _require_matching_enhanced_identity(expected_info, host.info)
            if deadline is not None:
                while host.segment is None:
                    if stop_requested.is_set():
                        raise RuntimeError("backend reconnect coordinator is closing")
                    remaining_s = deadline - monotonic_clock()
                    if remaining_s <= 0:
                        raise TimeoutError(
                            "Enhanced timestamp provenance was not established"
                        )
                    host.wait_for_segment(min(0.1, remaining_s))
            return ReconnectedCaptureSource(
                source=host,
                backend_snapshot=_backend_snapshot(
                    info=host.info,
                    segment=host.segment,
                    tx_enabled=settings.tx_enabled,
                ),
            )
        except BaseException:
            with suppress(BaseException):
                host.close()
            raise

    def publish_host(replacement: ReconnectedCaptureSource) -> None:
        host = cast(EnhancedReconnectHost, replacement.source)
        control.replace(host)
        sender.replace(host)

    return BackendReconnectCoordinator(
        source_owner=source_owner,
        open_replacement=open_replacement,
        on_connected=publish_host,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def _build_legacy_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    source_owner: ReplaceableCaptureSource,
    expected_info: BackendInfo,
    control: ReplaceableDeviceControl,
    sender: ReplaceableUartSender,
    open_transport: OpenEnhancedTransport,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> BackendReconnectCoordinator:
    """Keep unchanged startup callers working until they select ``open_host``."""

    opened_adapters: dict[int, tuple[EnhancedDeviceControl, EnhancedUartSender]] = {}

    def open_replacement(
        *,
        segment_id: int,
        deadline: float | None,
        stop_requested: Event,
    ) -> ReconnectedCaptureSource:
        if stop_requested.is_set():
            raise RuntimeError("backend reconnect coordinator is closing")
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
            if deadline is not None:
                while source.segment is None and monotonic_clock() < deadline:
                    source.prime_segment()
                if source.segment is None:
                    raise TimeoutError(
                        "Enhanced timestamp provenance was not established"
                    )
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

    return BackendReconnectCoordinator(
        source_owner=source_owner,
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
    segment: SegmentContext | None,
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


def _require_matching_basic_snapshot(
    expected: BackendSnapshot,
    replacement: BackendSnapshot,
) -> None:
    if (
        replacement.info.mode != expected.info.mode
        or replacement.info.port != expected.info.port
        or replacement.info.device != expected.info.device
        or replacement.info.firmware != expected.info.firmware
        or replacement.capability_policy != expected.capability_policy
    ):
        raise BackendInputError(
            "Reconnected Basic backend identity changed",
            backend_mode="basic",
        )
