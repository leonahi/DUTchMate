"""Synchronous service facade for one owner-loop Enhanced async adapter."""

from __future__ import annotations

import asyncio
import threading
from collections.abc import Callable, Coroutine
from concurrent.futures import Future
from contextlib import suppress
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

from dutchmate_core.backends.contracts import (
    BackendEvent,
    BackendInfo,
    BackendUartSendResult,
    ControlState,
    SegmentContext,
)
from dutchmate_core.backends.enhanced import (
    AsyncEnhancedDeviceControl,
    AsyncEnhancedUartSender,
)
from dutchmate_core.backends.enhanced_serial_io import (
    open_async_enhanced_serial_adapter,
)
from dutchmate_core.device_connection.parser import DeviceMessage

DEFAULT_ENHANCED_EVENT_POLL_TIMEOUT_S = 0.1
T = TypeVar("T")


class _AsyncEnhancedAdapter(Protocol):
    """The one async resource the service host owns on its loop."""

    @property
    def info(self) -> BackendInfo: ...

    @property
    def segment_id(self) -> int: ...

    @property
    def segment(self) -> SegmentContext | None: ...

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage: ...

    async def receive_event(
        self,
        timeout_s: float | None = None,
    ) -> BackendEvent | None: ...

    async def discard_pending_events(self) -> None: ...

    async def close(self) -> None: ...


class OpenAsyncEnhancedAdapter(Protocol):
    """Open the one adapter that the service host will own."""

    def __call__(
        self,
        *,
        port: str,
        segment_id: int,
        baudrate: int,
    ) -> Coroutine[Any, Any, _AsyncEnhancedAdapter]: ...


@dataclass(frozen=True, slots=True)
class _OpenedHost:
    adapter: _AsyncEnhancedAdapter
    control: AsyncEnhancedDeviceControl
    uart_sender: AsyncEnhancedUartSender
    info: BackendInfo
    segment_id: int
    segment: SegmentContext | None


class EnhancedAsyncHost:
    """Own one asyncio loop and expose its Enhanced adapter synchronously."""

    def __init__(self) -> None:
        self._state_lock = threading.Lock()
        self._loop_ready = threading.Event()
        self._close_complete = threading.Event()
        self._loop: asyncio.AbstractEventLoop | None = None
        self._owner_thread_id: int | None = None
        self._closing = False
        self._closed = False
        self._close_error: BaseException | None = None
        self._adapter: _AsyncEnhancedAdapter | None = None
        self._control: AsyncEnhancedDeviceControl | None = None
        self._uart_sender: AsyncEnhancedUartSender | None = None
        self._info: BackendInfo | None = None
        self._segment_id: int | None = None
        self._segment: SegmentContext | None = None
        self._inflight: set[Future[Any]] = set()
        self._thread = threading.Thread(
            target=self._run_loop,
            name="dutchmate-enhanced-async-host",
        )
        self._thread.start()
        self._loop_ready.wait()

    @property
    def owner_thread_id(self) -> int:
        """Return the owner-loop thread identity for lifecycle diagnostics."""

        with self._state_lock:
            if self._owner_thread_id is None:
                raise RuntimeError("Enhanced async host owner loop is unavailable")
            return self._owner_thread_id

    @property
    def info(self) -> BackendInfo:
        with self._state_lock:
            if self._info is None:
                raise RuntimeError("Enhanced async host is not ready")
            return self._info

    @property
    def segment_id(self) -> int:
        with self._state_lock:
            if self._segment_id is None:
                raise RuntimeError("Enhanced async host is not ready")
            return self._segment_id

    @property
    def segment(self) -> SegmentContext | None:
        with self._state_lock:
            return self._segment

    def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        control = self._control_for_operation()
        return self._submit(
            lambda: control.configure_gpio_mode(
                channel=channel,
                mode=mode,
                active_level=active_level,
                idle_level=idle_level,
            )
        )

    def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        control = self._control_for_operation()
        return self._submit(
            lambda: control.pulse_control(channel=channel, pulse_ms=pulse_ms)
        )

    def set_control_state(
        self,
        *,
        channel: str,
        state: ControlState,
    ) -> int | None:
        control = self._control_for_operation()
        return self._submit(
            lambda: control.set_control_state(channel=channel, state=state)
        )

    def send_uart(self, data: bytes) -> BackendUartSendResult:
        sender = self._uart_sender_for_operation()
        return self._submit(lambda: sender.send_uart(data))

    def read_event(self) -> BackendEvent | None:
        adapter = self._adapter_for_operation()
        event, segment = self._submit(lambda: self._receive_event(adapter))
        with self._state_lock:
            self._segment = segment
        return event

    def discard_pending_events(self) -> None:
        adapter = self._adapter_for_operation()
        self._submit(adapter.discard_pending_events)

    def close(self) -> None:
        """Terminalize the adapter once, then stop and join its owner loop."""

        if threading.get_ident() == self.owner_thread_id:
            raise RuntimeError("Enhanced async host cannot close on its owner thread")

        with self._state_lock:
            if self._closed:
                retained_error = self._close_error
                if retained_error is not None:
                    raise retained_error
                return
            if self._closing:
                first_closer = False
            else:
                self._closing = True
                first_closer = True
            loop = self._loop
            adapter = self._adapter
            inflight = tuple(self._inflight)

        if not first_closer:
            self._close_complete.wait()
            retained_error = self._close_error
            if retained_error is not None:
                raise retained_error
            return

        close_error: BaseException | None = None
        try:
            if loop is not None and adapter is not None:
                future = asyncio.run_coroutine_threadsafe(adapter.close(), loop)
                future.result()
            for pending in inflight:
                with suppress(BaseException):
                    pending.result()
        except BaseException as exc:
            close_error = exc
        finally:
            try:
                if loop is not None:
                    loop.call_soon_threadsafe(loop.stop)
                self._thread.join()
            except BaseException as exc:
                if close_error is None:
                    close_error = exc
            finally:
                with self._state_lock:
                    self._close_error = close_error
                    self._closed = True
                self._close_complete.set()
        if close_error is not None:
            raise close_error

    def _run_loop(self) -> None:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        with self._state_lock:
            self._loop = loop
            self._owner_thread_id = threading.get_ident()
        self._loop_ready.set()
        try:
            loop.run_forever()
        finally:
            loop.close()

    def _submit(self, operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
        with self._state_lock:
            if self._closing or self._closed:
                raise RuntimeError("Enhanced async host is closed")
            loop = self._loop
            if loop is None:
                raise RuntimeError("Enhanced async host owner loop is unavailable")
            future = asyncio.run_coroutine_threadsafe(operation(), loop)
            self._inflight.add(future)
        future.add_done_callback(self._forget_submission)
        return future.result()

    def _forget_submission(self, future: Future[Any]) -> None:
        with self._state_lock:
            self._inflight.discard(future)

    def _control_for_operation(self) -> AsyncEnhancedDeviceControl:
        with self._state_lock:
            if self._control is None:
                raise RuntimeError("Enhanced async host is not ready")
            return self._control

    def _uart_sender_for_operation(self) -> AsyncEnhancedUartSender:
        with self._state_lock:
            if self._uart_sender is None:
                raise RuntimeError("Enhanced async host is not ready")
            return self._uart_sender

    def _adapter_for_operation(self) -> _AsyncEnhancedAdapter:
        with self._state_lock:
            if self._adapter is None:
                raise RuntimeError("Enhanced async host is not ready")
            return self._adapter

    async def _receive_event(
        self,
        adapter: _AsyncEnhancedAdapter,
    ) -> tuple[BackendEvent | None, SegmentContext | None]:
        event = await adapter.receive_event(DEFAULT_ENHANCED_EVENT_POLL_TIMEOUT_S)
        return event, adapter.segment

    def _install(self, opened: _OpenedHost) -> None:
        with self._state_lock:
            self._adapter = opened.adapter
            self._control = opened.control
            self._uart_sender = opened.uart_sender
            self._info = opened.info
            self._segment_id = opened.segment_id
            self._segment = opened.segment

    def _stop_failed_open(self) -> None:
        with self._state_lock:
            self._closing = True
            loop = self._loop
        try:
            if loop is not None:
                loop.call_soon_threadsafe(loop.stop)
            self._thread.join()
        finally:
            with self._state_lock:
                self._closed = True
            self._close_complete.set()


async def _open_host_on_owner_loop(
    *,
    port: str,
    baudrate: int,
    segment_id: int,
    open_adapter: OpenAsyncEnhancedAdapter,
) -> _OpenedHost:
    adapter = await open_adapter(
        port=port,
        baudrate=baudrate,
        segment_id=segment_id,
    )
    try:
        return _OpenedHost(
            adapter=adapter,
            control=AsyncEnhancedDeviceControl(adapter),
            uart_sender=AsyncEnhancedUartSender(adapter),
            info=adapter.info,
            segment_id=adapter.segment_id,
            segment=adapter.segment,
        )
    except BaseException:
        with suppress(BaseException):
            await adapter.close()
        raise


def open_enhanced_async_host(
    *,
    port: str,
    baudrate: int,
    segment_id: int,
    open_adapter: OpenAsyncEnhancedAdapter = open_async_enhanced_serial_adapter,
) -> EnhancedAsyncHost:
    """Open one ready Enhanced adapter on its permanent owner loop."""

    host = EnhancedAsyncHost()
    try:
        opened = host._submit(
            lambda: _open_host_on_owner_loop(
                port=port,
                baudrate=baudrate,
                segment_id=segment_id,
                open_adapter=open_adapter,
            )
        )
        host._install(opened)
    except BaseException:
        host._stop_failed_open()
        raise
    return host
