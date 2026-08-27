"""Async Enhanced serial reader lifecycle tests."""

import asyncio
import gc

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendInfo,
    BackendInputError,
)
from dutchmate_core.backends.enhanced_serial import AsyncEnhancedSerialAdapter
from dutchmate_core.device_connection.transport import TransportTimeoutError

HELLO_FRAME = (
    b'{"type":"hello","v":1,"firmware":"0.1.0",'
    b'"device":"dutchmate-rp2040","capabilities":["uart_receive"]}\n'
)
UART_FRAME = b'{"type":"uart","channel":0,"timestamp_us":1,"data_b64":"WA=="}\n'


class FakeAsyncSerialReader:
    def __init__(self) -> None:
        self.outcomes: asyncio.Queue[bytes | Exception] = asyncio.Queue()
        self.read_calls = 0
        self.active_reads = 0
        self.maximum_concurrent_reads = 0
        self.reading = asyncio.Event()
        self.second_read_started = asyncio.Event()
        self.closed = False
        self.close_count = 0

    async def read(self, size: int) -> bytes:
        self.read_calls += 1
        self.active_reads += 1
        self.maximum_concurrent_reads = max(
            self.maximum_concurrent_reads,
            self.active_reads,
        )
        self.reading.set()
        if self.read_calls == 2:
            self.second_read_started.set()
        try:
            outcome = await self.outcomes.get()
        finally:
            self.active_reads -= 1
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    async def close(self) -> None:
        self.closed = True
        self.close_count += 1

    def feed(self, data: bytes) -> None:
        self.outcomes.put_nowait(data)

    def fail(self, error: Exception) -> None:
        self.outcomes.put_nowait(error)


class FakeAsyncFrameWriter:
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.failure: Exception | None = None

    async def write_frame(self, frame: bytes) -> None:
        self.frames.append(frame)
        if self.failure is not None:
            raise self.failure


def make_adapter(
    reader: FakeAsyncSerialReader,
    writer: FakeAsyncFrameWriter | None = None,
    **overrides: object,
) -> AsyncEnhancedSerialAdapter:
    arguments: dict[str, object] = {
        "reader": reader,
        "writer": writer or FakeAsyncFrameWriter(),
        "port": "/dev/ttyACM0",
        "segment_id": 3,
    }
    arguments.update(overrides)
    return AsyncEnhancedSerialAdapter(**arguments)  # type: ignore[arg-type]


async def test_start_uses_one_reader_and_returns_normalized_hello() -> None:
    """Fails if concurrent starts each own a reader or do not share one hello."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)

    first, second = await asyncio.gather(adapter.start(0.1), adapter.start(0.1))

    expected = BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="dutchmate-rp2040",
        firmware="0.1.0",
        capabilities=frozenset({"uart_receive"}),
    )
    assert first == second == expected
    assert adapter.info == expected
    assert adapter.segment_id == 3
    await reader.second_read_started.wait()
    assert reader.active_reads == 1
    assert reader.maximum_concurrent_reads == 1

    await adapter.close()


async def test_start_rejects_non_hello_first_message() -> None:
    """Fails if the initial device frame is accepted without a hello handshake."""

    reader = FakeAsyncSerialReader()
    reader.feed(b'{"ok":true}\n')
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="hello"):
        await adapter.start(0.1)

    await adapter.close()


async def test_start_preserves_parser_error_after_valid_hello_and_post_hello_message() -> None:
    """Fails if post-hello input masks a retained parser terminal error."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME + UART_FRAME + b'{"type":}\n')
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="not valid JSON") as raised:
        await adapter.start(0.1)

    assert raised.value.input_error == "invalid_json"
    await adapter.close()
    assert reader.close_count == 1


async def test_start_rejects_post_hello_message_in_the_same_batch() -> None:
    """Fails if hello resolves before the whole parsed batch is accepted."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME + UART_FRAME)
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="after hello"):
        await adapter.start(0.1)

    await adapter.close()
    assert reader.close_count == 1


async def test_start_timeout_closes_the_reader_and_normalizes_the_failure() -> None:
    """Fails if a missing hello leaks the reader or exposes asyncio timeout errors."""

    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)

    with pytest.raises(TransportTimeoutError, match="Timed out waiting for Enhanced hello"):
        await adapter.start(0.01)

    assert reader.active_reads == 0
    assert reader.close_count == 1


async def test_start_normalizes_eof_as_a_disconnected_backend() -> None:
    """Fails if EOF is not projected through the backend disconnect contract."""

    reader = FakeAsyncSerialReader()
    reader.feed(b"")
    adapter = make_adapter(reader)

    with pytest.raises(BackendDisconnectedError, match="connection closed"):
        await adapter.start(0.1)

    await adapter.close()
    assert reader.close_count == 1


async def test_start_normalizes_reader_failure_as_a_disconnected_backend() -> None:
    """Fails if raw reader exceptions escape instead of becoming disconnects."""

    reader = FakeAsyncSerialReader()
    reader.fail(OSError("device removed"))
    adapter = make_adapter(reader)

    with pytest.raises(BackendDisconnectedError, match="read failed") as raised:
        await adapter.start(0.1)

    assert isinstance(raised.value.__cause__, OSError)
    await adapter.close()
    assert reader.close_count == 1


async def test_cancelled_start_does_not_leave_an_unretrieved_hello_exception() -> None:
    """Fails if cancelling the sole starter leaves close to log a future exception."""

    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)
    loop = asyncio.get_running_loop()
    contexts: list[dict[str, object]] = []
    previous_handler = loop.get_exception_handler()
    loop.set_exception_handler(lambda _loop, context: contexts.append(context))
    try:
        start_task = asyncio.create_task(adapter.start(1.0))
        await reader.reading.wait()
        start_task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await start_task
        await adapter.close()
        del start_task
        del adapter
        gc.collect()
        await asyncio.sleep(0)
    finally:
        loop.set_exception_handler(previous_handler)

    assert contexts == []
    assert reader.active_reads == 0
    assert reader.close_count == 1


@pytest.mark.parametrize(
    "overrides",
    [
        {"segment_id": -1},
        {"segment_id": True},
        {"read_size": 0},
        {"read_size": False},
        {"event_queue_capacity": 0},
        {"event_queue_capacity": True},
    ],
)
def test_constructor_rejects_invalid_bounds(overrides: dict[str, object]) -> None:
    """Fails if invalid values can create ambiguous reader or queue bounds."""

    with pytest.raises(ValueError):
        make_adapter(FakeAsyncSerialReader(), **overrides)


async def test_close_cancels_blocked_reader_and_closes_resource_once() -> None:
    """Fails if shutdown leaves the sole reader blocked or closes it more than once."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)

    await adapter.start(0.1)
    await reader.second_read_started.wait()
    await adapter.close()
    await adapter.close()

    assert reader.active_reads == 0
    assert reader.closed is True
    assert reader.close_count == 1
