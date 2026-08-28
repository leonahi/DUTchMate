"""Concrete stream and exact-write I/O for one Enhanced serial connection."""

from __future__ import annotations

import asyncio
from typing import Protocol

from dutchmate_core.device_connection.serial_transport import (
    SerialFrameSink,
    write_serial_frame,
)


class _StreamReader(Protocol):
    async def read(self, size: int) -> bytes:
        """Return the next bytes or empty bytes for EOF."""


class _StreamWriter(Protocol):
    def close(self) -> None:
        """Begin closing the stream transport."""

    async def wait_closed(self) -> None:
        """Wait until the stream transport is closed."""


class _OwnedStreamReader:
    def __init__(self, reader: _StreamReader, writer: _StreamWriter) -> None:
        self._reader = reader
        self._writer = writer
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
        self._writer.close()
        await self._writer.wait_closed()


class _ThreadedSerialFrameWriter:
    def __init__(self, serial_port: SerialFrameSink) -> None:
        self._serial_port = serial_port

    async def write_frame(self, frame: bytes) -> None:
        await asyncio.to_thread(write_serial_frame, self._serial_port, frame)
