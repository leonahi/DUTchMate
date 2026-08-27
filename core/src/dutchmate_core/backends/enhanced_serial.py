"""Single-owner asynchronous adapter for one Enhanced serial connection."""

from __future__ import annotations

import asyncio
import math
from contextlib import suppress
from typing import Protocol

from dutchmate_core.backends.contracts import (
    BackendDisconnectedError,
    BackendEvent,
    BackendInfo,
    BackendInputError,
    SegmentContext,
)
from dutchmate_core.backends.enhanced import (
    backend_input_error_from_protocol,
    normalize_enhanced_hello,
)
from dutchmate_core.device_connection.errors import ProtocolError
from dutchmate_core.device_connection.messages import HelloMessage
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.device_connection.transport import TransportTimeoutError

DEFAULT_ASYNC_READ_SIZE = 4096
DEFAULT_ENHANCED_EVENT_QUEUE_CAPACITY = 256


class AsyncSerialReader(Protocol):
    """Async byte reader owned by one Enhanced adapter."""

    async def read(self, size: int) -> bytes:
        """Return the next serial byte chunk, or empty bytes for EOF."""

    async def close(self) -> None:
        """Close the owned serial resource."""


class AsyncFrameWriter(Protocol):
    """Async Enhanced command-frame writer."""

    async def write_frame(self, frame: bytes) -> None:
        """Write and flush one complete host command frame."""


class AsyncEnhancedSerialAdapter:
    """Own one async reader and validate its initial Enhanced hello."""

    def __init__(
        self,
        *,
        reader: AsyncSerialReader,
        writer: AsyncFrameWriter,
        port: str,
        segment_id: int,
        parser: NdjsonStreamParser | None = None,
        read_size: int = DEFAULT_ASYNC_READ_SIZE,
        event_queue_capacity: int = DEFAULT_ENHANCED_EVENT_QUEUE_CAPACITY,
    ) -> None:
        if isinstance(segment_id, bool) or not isinstance(segment_id, int) or segment_id < 0:
            raise ValueError("Enhanced segment ID must be a non-negative integer")
        if isinstance(read_size, bool) or not isinstance(read_size, int) or read_size <= 0:
            raise ValueError("Enhanced serial read size must be a positive integer")
        if (
            isinstance(event_queue_capacity, bool)
            or not isinstance(event_queue_capacity, int)
            or event_queue_capacity <= 0
        ):
            raise ValueError("Enhanced event queue capacity must be a positive integer")
        self._reader = reader
        self._writer = writer
        self._port = port
        self._segment_id = segment_id
        self._parser = parser or NdjsonStreamParser()
        self._read_size = read_size
        self._events: asyncio.Queue[BackendEvent] = asyncio.Queue(event_queue_capacity)
        self._start_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._hello_waiter: asyncio.Future[BackendInfo] | None = None
        self._info: BackendInfo | None = None
        self._segment: SegmentContext | None = None
        self._terminal_error: BackendDisconnectedError | BackendInputError | None = None
        self._terminal = asyncio.Event()
        self._closed = False
        self._resource_closed = False

    @property
    def info(self) -> BackendInfo:
        """Return normalized identity after a valid hello."""

        if self._info is None:
            raise RuntimeError("Enhanced serial adapter has not completed hello")
        return self._info

    @property
    def segment_id(self) -> int:
        """Return the session-local segment ID assigned by the caller."""

        return self._segment_id

    @property
    def segment(self) -> SegmentContext | None:
        """Return timestamp provenance once later event support establishes it."""

        return self._segment

    async def start(self, timeout_s: float) -> BackendInfo:
        """Start the sole reader and wait for its normalized hello."""

        _validate_timeout(timeout_s, field="Enhanced hello timeout")
        async with self._start_lock:
            self._raise_if_terminal()
            if self._info is not None:
                return self._info
            if self._reader_task is None:
                self._hello_waiter = asyncio.get_running_loop().create_future()
                self._reader_task = asyncio.create_task(
                    self._read_loop(),
                    name="dutchmate-enhanced-serial-reader",
                )
            waiter = self._hello_waiter
            assert waiter is not None
        try:
            return await asyncio.wait_for(asyncio.shield(waiter), timeout_s)
        except TimeoutError as exc:
            await self._terminate(
                BackendDisconnectedError("Timed out waiting for Enhanced hello")
            )
            if waiter.done() and not waiter.cancelled():
                waiter.exception()
            raise TransportTimeoutError("Timed out waiting for Enhanced hello") from exc

    async def _read_loop(self) -> None:
        try:
            while True:
                chunk = await self._reader.read(self._read_size)
                if not chunk:
                    raise BackendDisconnectedError("Enhanced serial connection closed")
                try:
                    messages = self._parser.feed(chunk)
                except ProtocolError as exc:
                    self._set_terminal(backend_input_error_from_protocol(exc))
                    return
                await self._dispatch_batch(messages)
                if self._parser.terminal_error is not None:
                    self._set_terminal(
                        backend_input_error_from_protocol(self._parser.terminal_error)
                    )
                    return
        except asyncio.CancelledError:
            raise
        except (BackendDisconnectedError, BackendInputError) as exc:
            self._set_terminal(exc)
        except Exception as exc:
            error = BackendDisconnectedError("Enhanced serial read failed")
            error.__cause__ = exc
            self._set_terminal(error)
        finally:
            await self._close_resource()

    async def _dispatch_batch(self, messages: list[DeviceMessage]) -> None:
        terminal_error = self._parser.terminal_error
        for message in messages:
            if self._info is None:
                if not isinstance(message, HelloMessage):
                    self._set_terminal(
                        BackendInputError(
                            "Expected Enhanced hello as the first message",
                            backend_mode="enhanced",
                        )
                    )
                    return
                self._info = normalize_enhanced_hello(message, port=self._port)
                if terminal_error is None:
                    waiter = self._hello_waiter
                    if waiter is not None and not waiter.done():
                        waiter.set_result(self._info)
                continue
            self._set_terminal(
                BackendInputError(
                    "Unexpected Enhanced message after hello",
                    backend_mode="enhanced",
                )
            )
            return

    def _set_terminal(
        self,
        error: BackendDisconnectedError | BackendInputError,
    ) -> None:
        if self._terminal_error is not None:
            return
        self._terminal_error = error
        self._terminal.set()
        waiter = self._hello_waiter
        if waiter is not None and not waiter.done():
            waiter.set_exception(error)

    def _raise_if_terminal(self) -> None:
        if self._terminal_error is not None:
            raise self._terminal_error

    async def _close_resource(self) -> None:
        if self._resource_closed:
            return
        self._resource_closed = True
        await self._reader.close()

    async def _terminate(
        self,
        error: BackendDisconnectedError | BackendInputError,
    ) -> None:
        self._set_terminal(error)
        task = self._reader_task
        if task is not None and task is not asyncio.current_task() and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._close_resource()

    async def close(self) -> None:
        """Terminalize the adapter and close the owned reader exactly once."""

        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            await self._terminate(
                BackendDisconnectedError("Enhanced serial adapter is closed")
            )


def _validate_timeout(
    value: float,
    *,
    field: str,
    allow_zero: bool = False,
) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a finite number")
    if not math.isfinite(value) or value < 0 or (value == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "positive"
        raise ValueError(f"{field} must be finite and {qualifier}")
