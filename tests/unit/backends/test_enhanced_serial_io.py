"""Concrete Enhanced async serial I/O boundary tests."""

import asyncio
import threading

import pytest

from dutchmate_core.backends.enhanced_serial_io import (
    _OwnedStreamReader,
    _ThreadedSerialFrameWriter,
)
from dutchmate_core.device_connection.transport import TransportWriteError


class FakeStreamReader:
    def __init__(self) -> None:
        self.chunks: asyncio.Queue[bytes | Exception] = asyncio.Queue()
        self.read_sizes: list[int] = []
        self.read_started = asyncio.Event()

    async def read(self, size: int) -> bytes:
        self.read_sizes.append(size)
        self.read_started.set()
        outcome = await self.chunks.get()
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


class BlockingCloseStreamWriter:
    def __init__(self) -> None:
        self.close_count = 0
        self.close_started = asyncio.Event()
        self.release_close = asyncio.Event()
        self.close_completed = asyncio.Event()
        self.wait_closed_failure: Exception | None = None

    def close(self) -> None:
        self.close_count += 1
        self.close_started.set()

    async def wait_closed(self) -> None:
        await self.release_close.wait()
        if self.wait_closed_failure is not None:
            raise self.wait_closed_failure
        self.close_completed.set()


class ThreadTrackingSerial:
    def __init__(self, outcomes: list[int | Exception]) -> None:
        self.outcomes = outcomes
        self.writes: list[bytes] = []
        self.write_threads: list[int] = []
        self.flush_count = 0
        self.flush_threads: list[int] = []
        self.written = threading.Event()

    def write(self, data: bytes) -> int:
        self.writes.append(data)
        self.write_threads.append(threading.get_ident())
        self.written.set()
        outcome = self.outcomes.pop(0) if self.outcomes else len(data)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    def flush(self) -> None:
        self.flush_count += 1
        self.flush_threads.append(threading.get_ident())


async def test_owned_stream_reader_delegates_reads_and_shares_close_completion() -> None:
    """Fails if paired stream closure is duplicated or not awaited by all callers."""

    reader = FakeStreamReader()
    writer = BlockingCloseStreamWriter()
    reader.chunks.put_nowait(b"abc")
    owned = _OwnedStreamReader(reader, writer)

    assert await owned.read(17) == b"abc"
    assert reader.read_sizes == [17]

    first = asyncio.create_task(owned.close())
    second = asyncio.create_task(owned.close())
    await writer.close_started.wait()
    assert not first.done()
    assert not second.done()
    writer.release_close.set()
    await asyncio.gather(first, second)

    assert writer.close_count == 1
    assert writer.close_completed.is_set()


async def test_threaded_writer_uses_shared_exact_loop_off_event_loop() -> None:
    """Fails if command writes use the event loop or skip partial-write recovery."""

    event_loop_thread = threading.get_ident()
    frame = b'{"cmd":"test"}\n'
    serial = ThreadTrackingSerial([2, len(frame) - 2])
    writer = _ThreadedSerialFrameWriter(serial)

    await writer.write_frame(frame)

    assert serial.writes == [frame, frame[2:]]
    assert serial.flush_count == 1
    assert all(thread != event_loop_thread for thread in serial.write_threads)
    assert all(thread != event_loop_thread for thread in serial.flush_threads)


async def test_threaded_writer_preserves_partial_acceptance_error() -> None:
    """Fails if a worker-thread write loses exact accepted-byte accounting."""

    frame = b'{"cmd":"test"}\n'
    serial = ThreadTrackingSerial([2, OSError("adapter removed")])
    writer = _ThreadedSerialFrameWriter(serial)

    with pytest.raises(TransportWriteError) as raised:
        await writer.write_frame(frame)

    assert raised.value.frame_bytes_accepted == 2
    assert raised.value.error == "hardware_fault"
    assert serial.flush_count == 0
