"""Service-owned backend reopen and replaceable-control composition."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import replace
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
    BackendOpenError,
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
from dutchmate_core.backends.selection import select_backend_settings
from dutchmate_core.backends.settings import BackendSettings
from dutchmate_core.connection import ConnectionLifecycleError
from dutchmate_core.session_store.models import SessionPersistenceError
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

    def reconnect_timed_out(self) -> None:
        """Terminalize the active ownership session after the profile deadline."""

    def close(self) -> None:
        """Terminalize the stable facade and its current concrete source."""


class OpenBasicConnection(Protocol):
    """Open one raw Basic connection from resolved settings."""

    def __call__(self, settings: BackendSettings) -> BasicBackendConnection:
        """Return an opened Basic connection."""


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


class _CandidateCleanupFailure(Exception):
    """Keep a rejected candidate's primary failure distinct from close failure."""

    def __init__(
        self,
        *,
        primary_error: BaseException,
        cleanup_error: BaseException,
    ) -> None:
        super().__init__(str(primary_error))
        self.primary_error = primary_error
        self.cleanup_error = cleanup_error


class ManualSourceOwner(Protocol):
    def release(self) -> None: ...
    def begin_reacquire(self) -> None: ...
    def reacquire_failed(self, *, cleanup_unknown: bool = False) -> None: ...
    def accept_reacquired_source(
        self, source: CaptureEventSource, *, backend_snapshot: BackendSnapshot
    ) -> None: ...


class BackendReconnectCoordinator:
    """Serialize idle and active reconnect attempts for one stable source owner."""

    def __init__(
        self,
        *,
        source_owner: ReplaceableCaptureSource,
        open_replacement: OpenCaptureReplacement,
        on_connected: Callable[[ReconnectedCaptureSource], None] | None = None,
        on_rejected: Callable[[ReconnectedCaptureSource], None] | None = None,
        monotonic_clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
        wait_for_idle_retry: Callable[[float], bool] | None = None,
        wait_for_active_retry: Callable[[float], bool] | None = None,
        active_retry_interval_s: float = 0.1,
        idle_initial_retry_s: float = 0.1,
        idle_max_retry_s: float = 2.0,
        reconnect_timeout_s: float = 5.0,
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
        if reconnect_timeout_s <= 0:
            raise ValueError("reconnect timeout must be positive")

        self._source_owner = source_owner
        self._open_replacement = open_replacement
        self._on_connected = on_connected
        self._on_rejected = on_rejected
        self._clock = monotonic_clock
        self._active_retry_interval_s = active_retry_interval_s
        self._idle_initial_retry_s = idle_initial_retry_s
        self._idle_max_retry_s = idle_max_retry_s
        self._reconnect_timeout_s = reconnect_timeout_s
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
        self._failure: ConnectionLifecycleError | None = None
        self._suspended = False
        self._worker: Thread | None = None
        self._attempt_active = False
        self._attempt_owner: Thread | None = None
        self._closing = False
        self._closed = False
        self._close_error: BaseException | None = None

    @property
    def failure(self) -> ConnectionLifecycleError | None:
        with self._condition:
            return self._failure

    def cancel_pending(self) -> None:
        """Prevent a submitted open from being published after shutdown/detach."""
        with self._condition:
            self._stop_requested.set()
            self._condition.notify_all()

    @contextmanager
    def _manual_claim(self) -> Iterator[None]:
        with self._condition:
            if (
                self._closing
                or self._closed
                or self._stop_requested.is_set()
                or self._close_error is not None
            ):
                raise ConnectionLifecycleError(
                    "invalid_connection_state",
                    "Connection ownership is closed or cleanup is unconfirmed",
                )
            if self._attempt_active:
                raise ConnectionLifecycleError(
                    "operation_active", "A connection lifecycle request is active"
                )
            self._attempt_active = True
            self._attempt_owner = current_thread()
            self._suspended = True
        try:
            yield
        finally:
            with self._condition:
                self._attempt_active = False
                self._attempt_owner = None
                self._condition.notify_all()

    def release(self) -> None:
        with self._manual_claim():
            try:
                cast(ManualSourceOwner, self._source_owner).release()
            except ConnectionLifecycleError:
                with self._condition:
                    self._suspended = False
                    self._condition.notify_all()
                raise
            except SessionPersistenceError as exc:
                self._retain_close_error(exc)
                self._failure = ConnectionLifecycleError(
                    "persistence_fault", "Lifecycle journaling failed", reason="persistence_fault"
                )
                raise
            except BaseException as exc:
                self._retain_close_error(exc)
                raise ConnectionLifecycleError(
                    "service_unavailable",
                    "Release cleanup is unconfirmed",
                    reason="cleanup_unconfirmed",
                ) from exc

    def reacquire(self) -> None:
        with self._manual_claim():
            owner = cast(ManualSourceOwner, self._source_owner)
            owner.begin_reacquire()
            replacement: ReconnectedCaptureSource | None = None
            try:
                deadline = self._clock() + self._reconnect_timeout_s
                if self._stop_requested.is_set():
                    raise ConnectionLifecycleError(
                        "invalid_connection_state", "Connection ownership is shutting down"
                    )
                replacement = self._open_replacement(
                    segment_id=0,
                    deadline=deadline,
                    stop_requested=self._stop_requested,
                )
                with self._condition:
                    if self._clock() >= deadline:
                        raise ConnectionLifecycleError(
                            "service_unavailable",
                            "Reacquire deadline expired",
                            reason="open_timeout",
                        )
                    if self._closing or self._closed or self._stop_requested.is_set():
                        raise ConnectionLifecycleError(
                            "invalid_connection_state", "Connection ownership is shutting down"
                        )
                    if self._on_connected is not None:
                        self._on_connected(replacement)
                    if self._closing or self._closed or self._stop_requested.is_set():
                        raise ConnectionLifecycleError(
                            "invalid_connection_state", "Connection ownership is shutting down"
                        )
                    if replacement.backend_snapshot is None:
                        raise ValueError("Reacquire requires segment provenance")
                    owner.accept_reacquired_source(
                        replacement.source, backend_snapshot=replacement.backend_snapshot
                    )
                    replacement = None
                    self._suspended = False
                    self._failure = None
                    self._condition.notify_all()
            except BaseException as exc:
                unknown = (
                    not isinstance(exc, ConnectionLifecycleError)
                    and getattr(exc, "cleanup_confirmed", None) is not True
                )
                if replacement is not None:
                    try:
                        self._close_rejected(replacement)
                        unknown = False
                    except BaseException:
                        unknown = True
                self._failure = (
                    exc
                    if isinstance(exc, ConnectionLifecycleError) and not unknown
                    else ConnectionLifecycleError(
                        "service_unavailable",
                        "Reacquire failed",
                        reason="cleanup_unconfirmed" if unknown else "open_failed",
                    )
                )
                if unknown:
                    self._retain_close_error(exc)
                owner.reacquire_failed(cleanup_unknown=unknown)
                if isinstance(exc, SessionPersistenceError):
                    self.cancel_pending()
                    if not unknown:
                        self._failure = ConnectionLifecycleError(
                            "persistence_fault",
                            "Lifecycle journaling failed",
                            reason="persistence_fault",
                        )
                    raise
                if isinstance(exc, ConnectionLifecycleError) and not unknown:
                    raise
                raise ConnectionLifecycleError(
                    "service_unavailable",
                    "Reacquire failed",
                    reason="cleanup_unconfirmed" if unknown else "open_failed",
                ) from exc

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
            if self._closing or self._closed or self._suspended:
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
                    if self._suspended:
                        self._condition.wait_for(
                            lambda: not self._suspended or self._stop_requested.is_set()
                        )
                        continue
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
                    deadline = self._clock() + self._reconnect_timeout_s
                    reconnected = self._retry_idle(deadline=deadline)
                    if not reconnected and not self._stop_requested.is_set():
                        selection_failed = getattr(
                            self._source_owner, "reconnect_selection_failed", None
                        )
                        if (
                            self._failure is not None
                            and self._failure.context.get("reason") == "ambiguous_device"
                            and callable(selection_failed)
                        ):
                            selection_failed("ambiguous_device")
                        else:
                            self._source_owner.reconnect_timed_out()
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
            except BackendOpenError as exc:
                if not exc.cleanup_confirmed:
                    self._retain_close_error(exc)
                    return None
                if self._wait_for_active_retry(deadline):
                    return None
                continue
            except _CandidateCleanupFailure as exc:
                self._retain_close_error(exc.cleanup_error)
                if isinstance(exc.primary_error, BackendInputError):
                    raise exc.primary_error from exc
                if not isinstance(exc.primary_error, Exception):
                    raise exc.primary_error from exc
                return None
            except BackendInputError:
                raise
            except Exception as exc:
                if getattr(exc, "cleanup_confirmed", None) is False:
                    self._retain_close_error(exc)
                    return None
                if self._wait_for_active_retry(deadline):
                    return None
                continue
            if self._stop_requested.is_set() or self._clock() >= deadline:
                self._close_rejected(replacement)
                return None
            return self._publish(replacement)
        return None

    def _retry_idle(self, *, deadline: float) -> bool:
        retry_delay_s = self._idle_initial_retry_s
        while not self._stop_requested.is_set() and self._clock() < deadline:
            try:
                replacement = self._open_replacement(
                    segment_id=0,
                    deadline=deadline,
                    stop_requested=self._stop_requested,
                )
            except _CandidateCleanupFailure as exc:
                self._retain_close_error(exc.cleanup_error)
                return False
            except Exception as exc:
                if isinstance(exc, ConnectionLifecycleError):
                    self._failure = exc
                    if exc.context.get("reason") == "ambiguous_device":
                        return False
                if getattr(exc, "cleanup_confirmed", None) is False:
                    self._retain_close_error(exc)
                    return False
                if self._stop_requested.is_set():
                    return False
                remaining_s = deadline - self._clock()
                if remaining_s <= 0:
                    return False
                if self._wait_for_idle_retry(min(retry_delay_s, remaining_s)):
                    return False
                retry_delay_s = min(retry_delay_s * 2, self._idle_max_retry_s)
                continue
            if self._stop_requested.is_set() or self._clock() >= deadline:
                self._close_rejected(replacement)
                return False
            self._publish(replacement)
            return True
        return False

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
            if self._closing or self._closed or self._suspended or self._stop_requested.is_set():
                publish = False
            else:
                publish = True
                try:
                    if self._on_connected is not None:
                        self._on_connected(replacement)
                except BaseException as exc:
                    callback_error = exc
                else:
                    if self._closing or self._closed or self._stop_requested.is_set():
                        publish = False
                    else:
                        self._failure = None
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
        first_error: BaseException | None = None
        if self._on_rejected is not None:
            try:
                self._on_rejected(replacement)
            except BaseException as exc:
                self._retain_close_error(exc)
                first_error = exc
        close = getattr(replacement.source, "close", None)
        if callable(close):
            try:
                close()
            except BaseException as exc:
                self._retain_close_error(exc)
                if first_error is None:
                    first_error = exc
        if first_error is not None:
            raise first_error

    def _retain_close_error(self, error: BaseException) -> None:
        with self._condition:
            first_failure = self._close_error is None
            if first_failure:
                self._close_error = error
                self._failure = ConnectionLifecycleError(
                    "service_unavailable",
                    "Physical cleanup is unconfirmed",
                    reason="cleanup_unconfirmed",
                )
            self._stop_requested.set()
            self._condition.notify_all()
        if first_failure:
            mark_fault = getattr(self._source_owner, "cleanup_unconfirmed", None)
            if callable(mark_fault):
                mark_fault()


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
        selected = select_backend_settings(settings)
        connection = open_connection(selected)
        source = BasicBackendEventSource(connection, segment_id=segment_id)
        try:
            _require_matching_basic_snapshot(
                replace(
                    expected_snapshot,
                    info=replace(expected_snapshot.info, port=cast(str, selected.serial_port)),
                )
                if settings.topology == "native_usb_console"
                and settings.usb_serial_number is not None
                else expected_snapshot,
                source.snapshot,
            )
        except BaseException as primary_error:
            cleanup_error = _close_unpublished_candidate(source)
            if cleanup_error is not None:
                raise _CandidateCleanupFailure(
                    primary_error=primary_error,
                    cleanup_error=cleanup_error,
                ) from primary_error
            raise
        opened_senders[id(source)] = connection
        return ReconnectedCaptureSource(
            source=source,
            backend_snapshot=source.snapshot,
        )

    def publish_sender(replacement: ReconnectedCaptureSource) -> None:
        sender.replace(opened_senders.pop(id(replacement.source)))

    def discard_sender(replacement: ReconnectedCaptureSource) -> None:
        opened_senders.pop(id(replacement.source), None)

    return BackendReconnectCoordinator(
        source_owner=source_owner,
        open_replacement=open_replacement,
        on_connected=publish_sender,
        on_rejected=discard_sender,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
        reconnect_timeout_s=settings.reconnect_timeout_s,
    )


def build_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    source_owner: ReplaceableCaptureSource,
    expected_info: BackendInfo,
    expected_snapshot: BackendSnapshot | None = None,
    control: ReplaceableDeviceControl,
    sender: ReplaceableUartSender,
    open_host: OpenEnhancedHost,
    monotonic_clock: Callable[[], float],
    sleep: Callable[[float], None],
) -> BackendReconnectCoordinator:
    """Build coordinated Enhanced reopen through the async host boundary."""

    expected_snapshot = expected_snapshot or backend_snapshot(
        info=expected_info,
        segment=None,
        tx_enabled=settings.tx_enabled,
    )
    return _build_async_enhanced_capture_reconnect(
        settings=settings,
        source_owner=source_owner,
        expected_snapshot=expected_snapshot,
        control=control,
        sender=sender,
        open_host=open_host,
        monotonic_clock=monotonic_clock,
        sleep=sleep,
    )


def _build_async_enhanced_capture_reconnect(
    *,
    settings: BackendSettings,
    source_owner: ReplaceableCaptureSource,
    expected_snapshot: BackendSnapshot,
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
        selected = select_backend_settings(settings)
        serial_port = selected.serial_port
        if serial_port is None:
            raise ValueError("Enhanced reconnect requires an explicit serial port")
        host = open_host(
            port=serial_port,
            baudrate=settings.baudrate,
            segment_id=segment_id,
        )
        try:
            _require_matching_enhanced_snapshot(
                replace(expected_snapshot, info=replace(expected_snapshot.info, port=serial_port))
                if settings.topology == "native_usb_console"
                and settings.usb_serial_number is not None
                else expected_snapshot,
                backend_snapshot(
                    info=host.info,
                    segment=host.segment,
                    tx_enabled=settings.tx_enabled,
                ),
            )
            if deadline is None:
                raise ValueError("Enhanced reconnect requires a finite deadline")
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
                backend_snapshot=backend_snapshot(
                    info=host.info,
                    segment=host.segment,
                    tx_enabled=settings.tx_enabled,
                ),
            )
        except BaseException as primary_error:
            cleanup_error = _close_unpublished_candidate(host)
            if cleanup_error is not None:
                raise _CandidateCleanupFailure(
                    primary_error=primary_error,
                    cleanup_error=cleanup_error,
                ) from primary_error
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
        reconnect_timeout_s=settings.reconnect_timeout_s,
    )


def backend_snapshot(
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


def _close_unpublished_candidate(candidate: object) -> BaseException | None:
    close = getattr(candidate, "close", None)
    if not callable(close):
        return None
    try:
        close()
    except BaseException as exc:
        return exc
    return None


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


def _require_matching_enhanced_snapshot(
    expected: BackendSnapshot,
    replacement: BackendSnapshot,
) -> None:
    _require_matching_enhanced_identity(expected.info, replacement.info)
    if replacement.capability_policy != expected.capability_policy:
        raise BackendInputError(
            "Reconnected Debug Helper capability policy changed",
            backend_mode="enhanced",
        )
    if replacement.capabilities != expected.capabilities:
        raise BackendInputError(
            "Reconnected Debug Helper capabilities changed",
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
