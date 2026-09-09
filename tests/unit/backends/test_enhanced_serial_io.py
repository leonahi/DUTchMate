"""Concrete Enhanced async serial I/O boundary tests."""

import asyncio
import importlib
import threading
from collections.abc import Callable
from types import SimpleNamespace

import pytest

from dutchmate_core.backends import BackendInfo, BackendInputError
from dutchmate_core.backends.enhanced_serial_io import (
    _OwnedStreamReader,
    _serial_asyncio_opener,
    _ThreadedSerialFrameWriter,
    open_async_enhanced_serial_adapter,
)
from dutchmate_core.device_connection.messages import CommandSuccessMessage
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
)

HELLO_FRAME = (
    b'{"type":"hello","v":1,"firmware":"0.1.0",'
    b'"device":"dutchmate-rp2350","capabilities":["uart_receive"]}\n'
)


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


class FakeStreamTransport:
    def __init__(self, serial_port: object | None) -> None:
        self.serial_port = serial_port
        self.extra_info_names: list[str] = []

    def get_extra_info(self, name: str, default: object | None = None) -> object | None:
        self.extra_info_names.append(name)
        return self.serial_port if name == "serial" else default


class FakeStreamWriter(BlockingCloseStreamWriter):
    def __init__(self, serial_port: object | None) -> None:
        super().__init__()
        self.transport = FakeStreamTransport(serial_port)
        self.stream_write_calls: list[bytes] = []
        self.release_close.set()

    def write(self, data: bytes) -> None:
        self.stream_write_calls.append(data)
        raise AssertionError("command frames must not use StreamWriter.write")


class RecordingOpener:
    def __init__(
        self,
        reader: FakeStreamReader,
        writer: FakeStreamWriter,
    ) -> None:
        self.reader = reader
        self.writer = writer
        self.calls: list[dict[str, object]] = []
        self.failure: Exception | None = None

    async def __call__(self, **kwargs: object) -> tuple[FakeStreamReader, FakeStreamWriter]:
        self.calls.append(kwargs)
        if self.failure is not None:
            raise self.failure
        return self.reader, self.writer


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


class DtrControlledSerial:
    def __init__(self, events: list[object]) -> None:
        self.events = events

    @property
    def dtr(self) -> bool:
        raise AssertionError("DTR is write-only in this test")

    @dtr.setter
    def dtr(self, value: bool) -> None:
        self.events.append(("dtr", value))

    def open(self) -> None:
        self.events.append("open")

    def reset_input_buffer(self) -> None:
        self.events.append("reset_input_buffer")

    def close(self) -> None:
        self.events.append("close")


class AttachedSerialTransport:
    def __init__(self, serial_port: DtrControlledSerial) -> None:
        self.serial_port = serial_port
        self.closed = False

    def is_closing(self) -> bool:
        return self.closed

    def close(self) -> None:
        self.closed = True


class OrderedCloseStreamWriter(BlockingCloseStreamWriter):
    def __init__(self, events: list[object]) -> None:
        super().__init__()
        self.events = events
        self.release_close.set()

    def close(self) -> None:
        self.events.append("writer_close")
        super().close()


async def test_production_opener_holds_dtr_low_before_starting_epoch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if restart can hide DTR low from the firmware epoch poller."""

    events: list[object] = []
    serial_port = DtrControlledSerial(events)

    def serial_for_url(url: str, **kwargs: object) -> DtrControlledSerial:
        events.append(("serial_for_url", url, kwargs))
        return serial_port

    async def connection_for_serial(
        loop: asyncio.AbstractEventLoop,
        protocol_factory: Callable[[], asyncio.Protocol],
        attached_serial: DtrControlledSerial,
    ) -> tuple[AttachedSerialTransport, object]:
        del loop
        events.append(("attach_reader", attached_serial))
        protocol = protocol_factory()
        return AttachedSerialTransport(attached_serial), protocol

    async def legacy_open_serial_connection(**kwargs: object) -> object:
        events.append(("legacy_open_serial_connection", kwargs))
        return object()

    async def record_sleep(delay: float) -> None:
        events.append(("sleep", delay))

    modules = {
        "serial": SimpleNamespace(serial_for_url=serial_for_url),
        "serial_asyncio": SimpleNamespace(
            connection_for_serial=connection_for_serial,
            open_serial_connection=legacy_open_serial_connection,
        ),
    }
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: modules[name],
    )
    monkeypatch.setattr(asyncio, "sleep", record_sleep)

    await _serial_asyncio_opener()(
        url="/dev/ttyACM0",
        baudrate=460800,
        limit=65536,
    )

    assert events == [
        (
            "serial_for_url",
            "/dev/ttyACM0",
            {"baudrate": 460800, "do_not_open": True},
        ),
        ("dtr", False),
        "open",
        ("attach_reader", serial_port),
        "reset_input_buffer",
        ("sleep", 0.1),
        ("dtr", True),
    ]


async def test_production_opener_closes_serial_if_reader_attachment_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    serial_port = DtrControlledSerial(events)

    async def connection_for_serial(*args: object) -> object:
        del args
        raise OSError("reader attachment failed")

    modules = {
        "serial": SimpleNamespace(serial_for_url=lambda *args, **kwargs: serial_port),
        "serial_asyncio": SimpleNamespace(connection_for_serial=connection_for_serial),
    }
    monkeypatch.setattr(
        importlib,
        "import_module",
        lambda name: modules[name],
    )

    with pytest.raises(OSError, match="reader attachment failed"):
        await _serial_asyncio_opener()(
            url="/dev/ttyACM0",
            baudrate=460800,
            limit=65536,
        )

    assert events == [("dtr", False), "open", "close"]


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


async def test_owned_stream_reader_holds_dtr_low_before_closing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fails if graceful shutdown can leave the firmware epoch active."""

    events: list[object] = []
    serial_port = DtrControlledSerial(events)
    writer = OrderedCloseStreamWriter(events)

    async def record_sleep(delay: float) -> None:
        events.append(("sleep", delay))

    monkeypatch.setattr(asyncio, "sleep", record_sleep)
    owned = _OwnedStreamReader(
        FakeStreamReader(),
        writer,
        serial_port=serial_port,
    )

    await owned.close()

    assert events == [("dtr", False), ("sleep", 0.1), "writer_close"]


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


async def test_factory_returns_started_adapter_and_writes_on_stream_serial() -> None:
    """Fails if startup, ownership, or exact command dispatch uses the wrong path."""

    reader = FakeStreamReader()
    reader.chunks.put_nowait(HELLO_FRAME)
    serial = ThreadTrackingSerial([])
    stream_writer = FakeStreamWriter(serial)
    opener = RecordingOpener(reader, stream_writer)

    adapter = await open_async_enhanced_serial_adapter(
        port="/dev/ttyACM0",
        segment_id=0,
        open_connection=opener,
    )
    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 0.1))
    assert await asyncio.to_thread(serial.written.wait, 1.0)
    reader.chunks.put_nowait(b'{"ok":true,"timestamp_us":8}\n')

    assert await request == CommandSuccessMessage(timestamp_us=8)
    assert opener.calls == [
        {
            "url": "/dev/ttyACM0",
            "baudrate": 115200,
            "limit": 65536,
        }
    ]
    assert adapter.info == BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="dutchmate-rp2350",
        firmware="0.1.0",
        capabilities=frozenset({"uart_receive"}),
    )
    assert stream_writer.transport.extra_info_names == ["serial"]
    assert stream_writer.stream_write_calls == []
    assert serial.writes == [b'{"cmd":"test"}\n']

    await adapter.close()
    await adapter.close()
    assert stream_writer.close_count == 1


async def test_factory_does_not_apply_dut_uart_rate_to_usb_cdc() -> None:
    """Fails if the Enhanced UART setting reaches the host CDC line coding."""

    reader = FakeStreamReader()
    reader.chunks.put_nowait(HELLO_FRAME)
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)

    adapter = await open_async_enhanced_serial_adapter(
        port="/dev/ttyACM0",
        segment_id=0,
        baudrate=460800,
        open_connection=opener,
    )

    assert opener.calls == [
        {
            "url": "/dev/ttyACM0",
            "baudrate": 115200,
            "limit": 65536,
        }
    ]

    await adapter.close()


async def test_open_failure_is_preserved_before_any_stream_exists() -> None:
    """Fails if opener errors are replaced or close an unreturned stream."""

    reader = FakeStreamReader()
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)
    opener.failure = OSError("open failed")

    with pytest.raises(OSError, match="open failed"):
        await open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=0,
            open_connection=opener,
        )

    assert stream_writer.close_count == 0


async def test_missing_serial_resource_closes_once_without_masking_primary() -> None:
    """Fails if transport inspection leaks or cleanup replaces its primary error."""

    reader = FakeStreamReader()
    stream_writer = FakeStreamWriter(None)
    stream_writer.wait_closed_failure = OSError("cleanup failed")
    opener = RecordingOpener(reader, stream_writer)

    with pytest.raises(
        RuntimeError,
        match="pyserial-asyncio transport omitted serial resource",
    ):
        await open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=0,
            open_connection=opener,
        )

    assert stream_writer.close_count == 1


async def test_constructor_failure_after_open_closes_once() -> None:
    """Fails if adapter validation after open leaves the owned stream alive."""

    reader = FakeStreamReader()
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)

    with pytest.raises(ValueError, match="segment ID"):
        await open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=-1,
            open_connection=opener,
        )

    assert stream_writer.close_count == 1


async def test_non_hello_start_failure_closes_once() -> None:
    """Fails if hello classification or startup cleanup is bypassed."""

    reader = FakeStreamReader()
    reader.chunks.put_nowait(b'{"ok":true}\n')
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)

    with pytest.raises(BackendInputError, match="Expected Enhanced hello"):
        await open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=0,
            open_connection=opener,
        )

    assert stream_writer.close_count == 1


async def test_hello_timeout_closes_once_and_leaves_no_reader_task() -> None:
    """Fails if timed-out startup leaves either transport or sole reader alive."""

    reader = FakeStreamReader()
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)

    with pytest.raises(TransportTimeoutError, match="Enhanced hello"):
        await open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=0,
            hello_timeout_s=0.01,
            open_connection=opener,
        )

    assert stream_writer.close_count == 1
    assert not any(
        task.get_name() == "dutchmate-enhanced-serial-reader" and not task.done()
        for task in asyncio.all_tasks()
    )


async def test_cancelled_factory_wait_closes_once_before_propagating() -> None:
    """Fails if cancellation escapes before closing or leaves the reader running."""

    reader = FakeStreamReader()
    stream_writer = FakeStreamWriter(ThreadTrackingSerial([]))
    opener = RecordingOpener(reader, stream_writer)
    opening = asyncio.create_task(
        open_async_enhanced_serial_adapter(
            port="/dev/ttyACM0",
            segment_id=0,
            open_connection=opener,
        )
    )
    await reader.read_started.wait()

    opening.cancel()
    with pytest.raises(asyncio.CancelledError):
        await opening

    assert stream_writer.close_count == 1
    assert not any(
        task.get_name() == "dutchmate-enhanced-serial-reader" and not task.done()
        for task in asyncio.all_tasks()
    )
