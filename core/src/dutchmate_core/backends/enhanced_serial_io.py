"""Concrete stream and exact-write I/O for one Enhanced serial connection."""

from __future__ import annotations

import asyncio
import importlib
from collections.abc import Awaitable, Callable
from typing import Protocol, cast

from dutchmate_core.backends.enhanced_serial import (
    DEFAULT_ENHANCED_EVENT_QUEUE_CAPACITY,
    AsyncEnhancedSerialAdapter,
)
from dutchmate_core.device_connection.serial_transport import (
    DEFAULT_BAUDRATE,
    SerialFrameSink,
    write_serial_frame,
)
from dutchmate_core.device_connection.stream import MAX_DEVICE_FRAME_BYTES

DEFAULT_ASYNC_HELLO_TIMEOUT_SECONDS = 1.0
DEFAULT_USB_CDC_LINE_BAUDRATE = 115200
USB_CDC_DTR_RESET_SECONDS = 0.1


class _StreamReader(Protocol):
    async def read(self, size: int) -> bytes:
        """Return the next bytes or empty bytes for EOF."""


class _StreamTransport(Protocol):
    def get_extra_info(self, name: str, default: object | None = None) -> object | None:
        """Return transport-owned connection information."""


class _StreamWriter(Protocol):
    transport: _StreamTransport

    def close(self) -> None:
        """Begin closing the stream transport."""

    async def wait_closed(self) -> None:
        """Wait until the stream transport is closed."""


class _DtrControl(Protocol):
    @property
    def dtr(self) -> bool:
        """Return the current DTR state."""

    @dtr.setter
    def dtr(self, value: bool) -> None:
        """Set the DTR state."""


class OpenSerialConnection(Protocol):
    def __call__(
        self,
        *,
        url: str,
        baudrate: int,
        limit: int,
    ) -> Awaitable[tuple[_StreamReader, _StreamWriter]]:
        """Open one pyserial-asyncio stream pair."""


class _OwnedStreamReader:
    def __init__(
        self,
        reader: _StreamReader,
        writer: _StreamWriter,
        *,
        serial_port: _DtrControl | None = None,
    ) -> None:
        self._reader = reader
        self._writer = writer
        self._serial_port = serial_port
        self._close_task: asyncio.Task[None] | None = None

    async def read(self, size: int) -> bytes:
        return await self._reader.read(size)

    async def close(self) -> None:
        task = self._close_task
        if task is None:
            task = asyncio.create_task(self._run_close())
            self._close_task = task
        await asyncio.shield(task)

    async def _run_close(self) -> None:
        if self._serial_port is not None:
            try:
                self._serial_port.dtr = False
            except Exception:
                pass
            else:
                await asyncio.sleep(USB_CDC_DTR_RESET_SECONDS)
        self._writer.close()
        await self._writer.wait_closed()


class _ThreadedSerialFrameWriter:
    def __init__(self, serial_port: SerialFrameSink) -> None:
        self._serial_port = serial_port

    async def write_frame(self, frame: bytes) -> None:
        await asyncio.to_thread(write_serial_frame, self._serial_port, frame)


def _serial_asyncio_opener() -> OpenSerialConnection:
    async def open_connection(
        *,
        url: str,
        baudrate: int,
        limit: int,
    ) -> tuple[_StreamReader, _StreamWriter]:
        serial_module = importlib.import_module("serial")
        serial_asyncio_module = importlib.import_module("serial_asyncio")
        serial_port = serial_module.serial_for_url(
            url,
            baudrate=baudrate,
            do_not_open=True,
        )

        # The firmware treats DTR rising as the start of a connection epoch and
        # immediately emits its one-shot hello.  pyserial's normal open path
        # asserts DTR before its final input flush, which can discard that hello.
        # Hold DTR low until the serial port is configured, flushed, and attached
        # to the asyncio reader, then assert it exactly once.
        serial_port.dtr = False
        try:
            serial_port.open()
            loop = asyncio.get_running_loop()
            stream_reader = asyncio.StreamReader(limit=limit)
            protocol = asyncio.StreamReaderProtocol(stream_reader)
            transport, _ = await serial_asyncio_module.connection_for_serial(
                loop,
                lambda: protocol,
                serial_port,
            )
            stream_writer = asyncio.StreamWriter(
                transport,
                protocol,
                stream_reader,
                loop,
            )
            serial_port.reset_input_buffer()
            await asyncio.sleep(USB_CDC_DTR_RESET_SECONDS)
            serial_port.dtr = True
        except BaseException:
            serial_port.close()
            raise

        return stream_reader, cast(_StreamWriter, stream_writer)

    return open_connection


async def _run_cleanup(close: Callable[[], Awaitable[None]]) -> None:
    await close()


async def _close_without_masking_primary(
    close: Callable[[], Awaitable[None]],
) -> None:
    close_task = asyncio.create_task(_run_cleanup(close))
    while True:
        try:
            await asyncio.shield(close_task)
            return
        except asyncio.CancelledError:
            if close_task.done():
                return
        except BaseException:
            return


async def open_async_enhanced_serial_adapter(
    *,
    port: str,
    segment_id: int,
    baudrate: int = DEFAULT_BAUDRATE,
    hello_timeout_s: float = DEFAULT_ASYNC_HELLO_TIMEOUT_SECONDS,
    event_queue_capacity: int = DEFAULT_ENHANCED_EVENT_QUEUE_CAPACITY,
    open_connection: OpenSerialConnection | None = None,
) -> AsyncEnhancedSerialAdapter:
    """Open, hello-validate, and return one production Enhanced adapter."""

    opener = open_connection if open_connection is not None else _serial_asyncio_opener()
    stream_reader, stream_writer = await opener(
        url=port,
        # Enhanced baudrate config belongs to the firmware-owned DUT UART. USB
        # CDC line coding is independent and uses a portable host-side value.
        baudrate=DEFAULT_USB_CDC_LINE_BAUDRATE,
        limit=MAX_DEVICE_FRAME_BYTES,
    )
    serial_resource = stream_writer.transport.get_extra_info("serial")
    owned_reader = _OwnedStreamReader(
        stream_reader,
        stream_writer,
        serial_port=(
            cast(_DtrControl, serial_resource)
            if open_connection is None and serial_resource is not None
            else None
        ),
    )
    adapter: AsyncEnhancedSerialAdapter | None = None
    try:
        if serial_resource is None:
            raise RuntimeError("pyserial-asyncio transport omitted serial resource")
        writer = _ThreadedSerialFrameWriter(cast(SerialFrameSink, serial_resource))
        adapter = AsyncEnhancedSerialAdapter(
            reader=owned_reader,
            writer=writer,
            port=port,
            segment_id=segment_id,
            event_queue_capacity=event_queue_capacity,
        )
        await adapter.start(hello_timeout_s)
        return adapter
    except BaseException:
        close = adapter.close if adapter is not None else owned_reader.close
        await _close_without_masking_primary(close)
        raise
