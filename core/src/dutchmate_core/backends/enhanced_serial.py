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
    enhanced_message_timestamp_us,
    enhanced_segment_context,
    normalize_enhanced_hello,
    normalize_enhanced_message,
)
from dutchmate_core.device_connection.errors import ProtocolError
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
    HelloMessage,
)
from dutchmate_core.device_connection.parser import DeviceMessage
from dutchmate_core.device_connection.stream import NdjsonStreamParser
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
    validate_host_command_frame,
)

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
        self._command_lock = asyncio.Lock()
        self._close_lock = asyncio.Lock()
        self._reader_task: asyncio.Task[None] | None = None
        self._hello_waiter: asyncio.Future[BackendInfo] | None = None
        self._pending_response: asyncio.Future[DeviceMessage] | None = None
        self._info: BackendInfo | None = None
        self._segment: SegmentContext | None = None
        self._terminal_error: BackendDisconnectedError | BackendInputError | None = None
        self._terminal = asyncio.Event()
        self._closed = False
        self._resource_close_started = False
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
                self._hello_waiter.add_done_callback(_consume_hello_waiter_exception)
                self._reader_task = asyncio.create_task(
                    self._read_loop(),
                    name="dutchmate-enhanced-serial-reader",
                )
            waiter = self._hello_waiter
            assert waiter is not None
        try:
            return await self._wait_for_hello(waiter, timeout_s)
        except TimeoutError as exc:
            await self._terminate(
                BackendDisconnectedError("Timed out waiting for Enhanced hello")
            )
            raise TransportTimeoutError("Timed out waiting for Enhanced hello") from exc

    async def _wait_for_hello(
        self,
        waiter: asyncio.Future[BackendInfo],
        timeout_s: float,
    ) -> BackendInfo:
        """Wait without allowing one caller's cancellation to cancel shared hello state."""

        result = asyncio.get_running_loop().create_future()

        def complete(source: asyncio.Future[BackendInfo]) -> None:
            if result.done():
                return
            if source.cancelled():
                result.cancel()
                return
            error = source.exception()
            if error is not None:
                result.set_exception(error)
                return
            result.set_result(source.result())

        waiter.add_done_callback(complete)
        try:
            return await asyncio.wait_for(result, timeout_s)
        finally:
            waiter.remove_done_callback(complete)
            if not result.done():
                result.cancel()

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
                if self._terminal_error is not None:
                    return
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
        info = self._info
        segment = self._segment
        events: list[BackendEvent] = []
        received_hello = False
        for message in messages:
            if info is None:
                if not isinstance(message, HelloMessage):
                    self._set_terminal(
                        BackendInputError(
                            "Expected Enhanced hello as the first message",
                            backend_mode="enhanced",
                        )
                    )
                    return
                info = normalize_enhanced_hello(message, port=self._port)
                received_hello = True
                continue
            timestamp_us = enhanced_message_timestamp_us(message)
            if timestamp_us is not None:
                if segment is None:
                    segment = enhanced_segment_context(
                        self._segment_id,
                        timestamp_us,
                    )
                event = normalize_enhanced_message(
                    message,
                    segment_id=self._segment_id,
                    source_origin_us=segment.timestamp.source_origin_us,
                )
                assert event is not None
                events.append(event)
                continue
            if self._info is not None and isinstance(
                message,
                (CommandSuccessMessage, CommandErrorMessage),
            ):
                if self._parser.terminal_error is not None:
                    continue
                pending = self._pending_response
                if pending is None or pending.done():
                    self._set_terminal(
                        BackendInputError(
                            "Enhanced command response has no pending request",
                            backend_mode="enhanced",
                        )
                    )
                    break
                pending.set_result(message)
                continue
            self._set_terminal(
                BackendInputError(
                    "Unexpected Enhanced message after hello",
                    backend_mode="enhanced",
                )
            )
            break
        self._info = info
        self._segment = segment
        parser_error = self._parser.terminal_error
        if parser_error is not None:
            self._set_terminal(backend_input_error_from_protocol(parser_error))
        elif received_hello and self._terminal_error is None:
            self._complete_hello_waiter()
        for event in events:
            await self._events.put(event)

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        """Write one command and wait for the sole reader to route its response."""

        validate_host_command_frame(command)
        _validate_timeout(timeout_s, field="Enhanced command timeout")
        async with self._command_lock:
            self._raise_if_terminal()
            response: asyncio.Future[DeviceMessage] = (
                asyncio.get_running_loop().create_future()
            )
            response.add_done_callback(_consume_response_waiter_exception)
            self._pending_response = response
            try:
                await self._writer.write_frame(command)
                try:
                    return await asyncio.wait_for(asyncio.shield(response), timeout_s)
                except TimeoutError as exc:
                    timeout = TransportTimeoutError(
                        "Timed out waiting for Enhanced command response"
                    )
                    disconnected = BackendDisconnectedError(
                        "Enhanced command response timed out; connection closed"
                    )
                    self._set_terminal(disconnected, cancel_pending_response=True)
                    await self._terminate(disconnected)
                    raise timeout from exc
            except TransportWriteError:
                disconnected = BackendDisconnectedError(
                    "Enhanced command write failed; connection closed"
                )
                self._set_terminal(disconnected, cancel_pending_response=True)
                await self._terminate(disconnected)
                raise
            except asyncio.CancelledError:
                disconnected = BackendDisconnectedError(
                    "Enhanced command cancelled after transmission began"
                )
                self._set_terminal(disconnected, cancel_pending_response=True)
                await asyncio.shield(self._terminate(disconnected))
                raise
            finally:
                if self._pending_response is response:
                    self._pending_response = None

    def _complete_hello_waiter(self) -> None:
        info = self._info
        assert info is not None
        waiter = self._hello_waiter
        if waiter is not None and not waiter.done():
            waiter.set_result(info)

    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
        """Return one queued evidence event, timeout, or the terminal read failure."""

        if timeout_s is not None:
            _validate_timeout(
                timeout_s,
                field="Enhanced receive timeout",
                allow_zero=True,
            )
        if not self._events.empty():
            return self._events.get_nowait()
        self._raise_if_terminal()

        event_task = asyncio.create_task(self._events.get())
        terminal_task = asyncio.create_task(self._terminal.wait())
        try:
            done, _ = await asyncio.wait(
                {event_task, terminal_task},
                timeout=timeout_s,
                return_when=asyncio.FIRST_COMPLETED,
            )
            if not done:
                return None
            if event_task in done:
                return event_task.result()
            if not self._events.empty():
                return self._events.get_nowait()
            self._raise_if_terminal()
            raise AssertionError("terminal event set without terminal error")
        finally:
            for task in (event_task, terminal_task):
                if not task.done():
                    task.cancel()
                with suppress(asyncio.CancelledError):
                    await task

    def _set_terminal(
        self,
        error: BackendDisconnectedError | BackendInputError,
        *,
        cancel_pending_response: bool = False,
    ) -> None:
        if self._terminal_error is not None:
            return
        self._terminal_error = error
        self._terminal.set()
        waiter = self._hello_waiter
        if waiter is not None and not waiter.done():
            waiter.set_exception(error)
        response = self._pending_response
        if response is not None and not response.done():
            if cancel_pending_response:
                response.cancel()
            else:
                response.set_exception(error)

    def _raise_if_terminal(self) -> None:
        if self._terminal_error is not None:
            raise self._terminal_error

    async def _close_resource(self) -> None:
        if self._resource_close_started:
            return
        self._resource_close_started = True
        try:
            await self._reader.close()
        except Exception:
            return
        self._resource_closed = True

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


def _consume_hello_waiter_exception(waiter: asyncio.Future[BackendInfo]) -> None:
    if not waiter.cancelled():
        waiter.exception()


def _consume_response_waiter_exception(waiter: asyncio.Future[DeviceMessage]) -> None:
    if not waiter.cancelled():
        waiter.exception()
