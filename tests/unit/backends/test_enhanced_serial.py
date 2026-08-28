"""Async Enhanced serial reader lifecycle tests."""

import asyncio
import gc

import pytest

from dutchmate_core.backends import (
    BackendDisconnectedError,
    BackendInfo,
    BackendInputError,
    BufferOverflowEvent,
    BufferStatusEvent,
    UartReceiveEvent,
)
from dutchmate_core.backends.enhanced_serial import AsyncEnhancedSerialAdapter
from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import HostCommandFrameTooLargeError
from dutchmate_core.device_connection.messages import (
    CommandErrorMessage,
    CommandSuccessMessage,
)
from dutchmate_core.device_connection.stream import MAX_DEVICE_FRAME_BYTES
from dutchmate_core.device_connection.transport import (
    TransportTimeoutError,
    TransportWriteError,
)

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
        self.second_read_returned = asyncio.Event()
        self.third_read_started = asyncio.Event()
        self.next_chunk_requested = asyncio.Event()
        self.closed_event = asyncio.Event()
        self.closed = False
        self.close_count = 0
        self.close_failure: Exception | None = None
        self._has_returned_data = False

    async def read(self, size: int) -> bytes:
        self.read_calls += 1
        self.active_reads += 1
        self.maximum_concurrent_reads = max(
            self.maximum_concurrent_reads,
            self.active_reads,
        )
        self.reading.set()
        if self._has_returned_data:
            self.next_chunk_requested.set()
        if self.read_calls == 2:
            self.second_read_started.set()
        if self.read_calls == 3:
            self.third_read_started.set()
        try:
            outcome = await self.outcomes.get()
        finally:
            self.active_reads -= 1
        if self.read_calls == 2:
            self.second_read_returned.set()
        if isinstance(outcome, Exception):
            raise outcome
        if outcome:
            self._has_returned_data = True
        return outcome

    async def close(self) -> None:
        self.closed = True
        self.close_count += 1
        self.closed_event.set()
        if self.close_failure is not None:
            raise self.close_failure

    def feed(self, data: bytes) -> None:
        self.outcomes.put_nowait(data)

    def fail(self, error: Exception) -> None:
        self.outcomes.put_nowait(error)


class FakeAsyncFrameWriter:
    def __init__(self) -> None:
        self.frames: list[bytes] = []
        self.failure: Exception | None = None
        self.written: asyncio.Queue[bytes] = asyncio.Queue()

    async def write_frame(self, frame: bytes) -> None:
        self.frames.append(frame)
        self.written.put_nowait(frame)
        if self.failure is not None:
            raise self.failure


class BlockingAsyncFrameWriter(FakeAsyncFrameWriter):
    def __init__(self) -> None:
        super().__init__()
        self.release = asyncio.Event()

    async def write_frame(self, frame: bytes) -> None:
        await super().write_frame(frame)
        await self.release.wait()


class CloseBlockingAsyncSerialReader(FakeAsyncSerialReader):
    def __init__(self) -> None:
        super().__init__()
        self.close_started = asyncio.Event()
        self.release_close = asyncio.Event()
        self.close_completed = asyncio.Event()

    async def close(self) -> None:
        self.closed = True
        self.close_count += 1
        self.close_started.set()
        await self.release_close.wait()
        self.closed_event.set()
        self.close_completed.set()


class TerminationBarrierAdapter(AsyncEnhancedSerialAdapter):
    """Pause cleanup after request code has selected its terminal outcome."""

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)  # type: ignore[arg-type]
        self.termination_started = asyncio.Event()
        self.allow_termination = asyncio.Event()

    async def _terminate(
        self,
        error: BackendDisconnectedError | BackendInputError,
    ) -> None:
        self.termination_started.set()
        await self.allow_termination.wait()
        await super()._terminate(error)


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


def _compact_json_frame_of_size(size: int) -> bytes:
    baseline = b'{"cmd":"test","data":""}\n'
    return b'{"cmd":"test","data":"' + b"x" * (size - len(baseline)) + b'"}\n'


async def _request_after_entering(
    adapter: AsyncEnhancedSerialAdapter,
    entered: asyncio.Event,
    command: bytes,
    timeout_s: float,
) -> CommandSuccessMessage | CommandErrorMessage:
    entered.set()
    response = await adapter.request(command, timeout_s)
    assert isinstance(response, (CommandSuccessMessage, CommandErrorMessage))
    return response


async def _receive_after_entering(
    adapter: AsyncEnhancedSerialAdapter,
    entered: asyncio.Event,
) -> object:
    entered.set()
    return await adapter.receive_event()


async def _close_after_entering(
    adapter: AsyncEnhancedSerialAdapter,
    entered: asyncio.Event,
) -> None:
    entered.set()
    await adapter.close()


async def test_request_routes_response_and_retains_interleaved_event() -> None:
    """Fails if command routing consumes or reorders interleaved UART evidence."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"test"}\n'
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":700,"data_b64":"WA=="}\n'
        b'{"ok":true,"timestamp_us":701}\n'
    )

    assert await request == CommandSuccessMessage(timestamp_us=701)
    assert writer.frames == [b'{"cmd":"test"}\n']
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    await adapter.close()


async def test_same_batch_response_waits_for_capacity_one_evidence_admission() -> None:
    """Fails if a response overtakes earlier evidence blocked outside the FIFO."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer, event_queue_capacity=1)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"one"}\n'

    try:
        reader.feed(
            b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
            b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"WQ=="}\n'
            b'{"ok":true,"timestamp_us":12}\n'
        )
        await asyncio.wait_for(reader.second_read_returned.wait(), timeout=0.1)

        pending = adapter._pending_response
        assert pending is not None
        assert not pending.done()
        assert not request.done()
        assert await adapter.receive_event(0.1) == UartReceiveEvent(
            segment_id=3, timestamp_us=0, channel=0, data=b"X"
        )
        assert await request == CommandSuccessMessage(timestamp_us=12)
        assert await adapter.receive_event(0.1) == UartReceiveEvent(
            segment_id=3, timestamp_us=1, channel=0, data=b"Y"
        )
    finally:
        await adapter.close()
        await asyncio.gather(request, return_exceptions=True)


async def test_concurrent_requests_write_only_one_frame_at_a_time() -> None:
    """Fails if a second uncorrelated command is written before the first resolves."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    second = asyncio.create_task(adapter.request(b'{"cmd":"two"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    assert writer.frames == [b'{"cmd":"one"}\n']

    reader.feed(b'{"ok":true,"timestamp_us":1}\n')
    assert await first == CommandSuccessMessage(timestamp_us=1)
    assert await writer.written.get() == b'{"cmd":"two"}\n'
    assert writer.frames == [b'{"cmd":"one"}\n', b'{"cmd":"two"}\n']
    reader.feed(b'{"ok":false,"error":"timeout","detail":"busy"}\n')
    assert await second == CommandErrorMessage(error="timeout", detail="busy")
    await adapter.close()


async def test_request_rejects_invalid_frames_before_writer() -> None:
    """Fails if an invalid host frame reaches the serial writer."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    with pytest.raises(TypeError):
        await adapter.request("not bytes", 0.1)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="newline-terminated"):
        await adapter.request(b'{"cmd":"test"}', 0.1)
    with pytest.raises(HostCommandFrameTooLargeError):
        await adapter.request(
            _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1),
            0.1,
        )

    assert writer.frames == []
    await adapter.close()


@pytest.mark.parametrize("timeout_s", [0, -0.1, float("inf"), float("nan"), True])
async def test_request_rejects_invalid_timeout_before_writer(timeout_s: float) -> None:
    """Fails if a non-positive or non-finite command timeout reaches the writer."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    with pytest.raises(ValueError, match="Enhanced command timeout"):
        await adapter.request(b'{"cmd":"test"}\n', timeout_s)

    assert writer.frames == []
    await adapter.close()


async def test_write_failure_preserves_frame_count_then_disconnects() -> None:
    """Fails if async routing replaces write accounting or its repeatable terminal."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    failure = TransportWriteError(
        "write failed",
        frame_bytes_accepted=7,
        error="hardware_fault",
    )
    writer.failure = failure
    reader.close_failure = OSError("close failed")
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    with pytest.raises(TransportWriteError) as raised:
        await adapter.request(b'{"cmd":"test"}\n', 0.1)
    assert raised.value is failure
    assert raised.value.frame_bytes_accepted == 7

    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)
    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)
    assert reader.close_count == 1


async def test_request_timeout_closes_and_terminalizes_adapter() -> None:
    """Fails if a timed-out response leaves the reader or connection reusable."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.close_failure = OSError("close failed")
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 0.001))
    assert await writer.written.get() == b'{"cmd":"test"}\n'

    with pytest.raises(TransportTimeoutError, match="command response"):
        await request
    with pytest.raises(BackendDisconnectedError, match="timed out"):
        await adapter.receive_event(0.1)
    assert reader.active_reads == 0
    assert reader.close_count == 1


async def test_cancelling_transmitted_request_closes_and_terminalizes_adapter() -> None:
    """Fails if caller cancellation leaves an uncorrelated response path alive."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.close_failure = OSError("close failed")
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"test"}\n'
    request.cancel()

    with pytest.raises(asyncio.CancelledError):
        await request
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)
    with pytest.raises(BackendDisconnectedError, match="cancelled"):
        await adapter.receive_event(0.1)
    assert reader.active_reads == 0
    assert reader.close_count == 1


async def test_cancellation_selects_terminal_before_response_can_be_orphaned() -> None:
    """Fails if cancelling the response future races terminal cause selection."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = TerminationBarrierAdapter(
        reader=reader,
        writer=writer,
        port="/dev/ttyACM0",
        segment_id=3,
    )
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"test"}\n'
    request.cancel()
    await adapter.termination_started.wait()

    reader.feed(b'{"ok":true}\n')
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)
    adapter.allow_termination.set()

    with pytest.raises(asyncio.CancelledError):
        await request
    for _ in range(2):
        with pytest.raises(BackendDisconnectedError, match="cancelled"):
            await adapter.receive_event(0.1)
    assert reader.close_count == 1


async def test_response_without_pending_request_terminalizes_reader() -> None:
    """Fails if an uncorrelated response is dropped or exposed as evidence."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)

    reader.feed(b'{"ok":true}\n')
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)

    with pytest.raises(BackendInputError, match="no pending request"):
        await adapter.receive_event(0.1)
    assert reader.active_reads == 0
    assert reader.close_count == 1


async def test_orphan_response_retains_same_batch_prefix_evidence() -> None:
    """Fails if an orphan response discards valid evidence preceding it."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)

    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":700,"data_b64":"WA=="}\n'
        b'{"ok":true}\n'
    )
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)

    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3,
        timestamp_us=0,
        channel=0,
        data=b"X",
    )
    for _ in range(2):
        with pytest.raises(BackendInputError, match="no pending request"):
            await adapter.receive_event(0.1)


async def test_same_batch_parser_error_precedes_response_and_retains_event() -> None:
    """Fails if response success masks later malformed input in its parser batch."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer, event_queue_capacity=1)
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"test"}\n'
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":700,"data_b64":"WA=="}\n'
        b'{"type":"uart","channel":0,"timestamp_us":710,"data_b64":"WQ=="}\n'
        b'{"ok":true,"timestamp_us":711}\n'
        b'{"type":}\n'
    )

    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    with pytest.raises(BackendInputError, match="not valid JSON") as request_error:
        await request
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=10, channel=0, data=b"Y"
    )
    with pytest.raises(BackendInputError, match="not valid JSON") as event_error:
        await adapter.receive_event(0.1)
    assert event_error.value is request_error.value


async def test_same_batch_parser_terminal_waits_for_capacity_one_prefix_admission(
) -> None:
    """Fails if malformed input becomes observable before valid-prefix admission."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer, event_queue_capacity=1)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"one"}\n'

    try:
        reader.feed(
            b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
            b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"WQ=="}\n'
            b'{"type":}\n'
        )
        await asyncio.wait_for(reader.second_read_returned.wait(), timeout=0.1)

        pending = adapter._pending_response
        assert pending is not None
        assert not pending.done()
        assert not request.done()
        assert await adapter.receive_event(0.1) == UartReceiveEvent(
            segment_id=3, timestamp_us=0, channel=0, data=b"X"
        )
        with pytest.raises(BackendInputError, match="not valid JSON") as request_error:
            await request
        assert await adapter.receive_event(0.1) == UartReceiveEvent(
            segment_id=3, timestamp_us=1, channel=0, data=b"Y"
        )
        for _ in range(2):
            with pytest.raises(BackendInputError, match="not valid JSON") as replayed:
                await adapter.receive_event(0.1)
            assert replayed.value is request_error.value
    finally:
        await adapter.close()
        await asyncio.gather(request, return_exceptions=True)


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


async def test_start_preserves_event_validation_after_hello_in_the_same_batch() -> None:
    """Fails if hello resolves before all same-batch event semantics are valid."""

    reader = FakeAsyncSerialReader()
    reader.feed(
        HELLO_FRAME
        + b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
        + b'{"type":"uart","channel":0,"timestamp_us":9,"data_b64":"WQ=="}\n'
    )
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="precedes its segment origin"):
        await adapter.start(0.1)

    await adapter.close()
    assert reader.close_count == 1


async def test_start_accepts_evidence_after_hello_in_the_same_batch() -> None:
    """Fails if same-batch evidence still terminalizes a valid hello handshake."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME + UART_FRAME)
    adapter = make_adapter(reader)

    assert await adapter.start(0.1) == BackendInfo(
        mode="enhanced",
        port="/dev/ttyACM0",
        device="dutchmate-rp2040",
        firmware="0.1.0",
        capabilities=frozenset({"uart_receive"}),
    )

    await adapter.close()
    assert reader.close_count == 1


async def test_start_rejects_unexpected_message_after_hello_in_the_same_batch() -> None:
    """Fails if hello resolves before later same-batch input is validated."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME + b'{"ok":true}\n')
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="after hello"):
        await adapter.start(0.1)

    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)
    await adapter.close()


async def test_receive_event_normalizes_fifo_and_establishes_origin() -> None:
    """Fails if evidence is not normalized in wire order from its first timestamp."""

    reader = FakeAsyncSerialReader()
    reader.feed(
        HELLO_FRAME
        + b'{"type":"uart","channel":0,"timestamp_us":500,"data_b64":"WA=="}\n'
        + b'{"type":"buffer_overflow","channel":0,"timestamp_us":510,"dropped_bytes":4}\n'
        + b'{"type":"buffer_status","timestamp_us":520,"uart_rx_size_bytes":32768,'
        b'"uart_rx_used_bytes":8,"uart_rx_high_water_bytes":16,'
        b'"dropped_bytes_total":4,"overflow_events":1}\n'
    )
    adapter = make_adapter(reader)

    await adapter.start(0.1)

    assert adapter.segment is not None
    assert adapter.segment.timestamp.source_origin_us == 500
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3,
        timestamp_us=0,
        channel=0,
        data=b"X",
    )
    assert await adapter.receive_event(0.1) == BufferOverflowEvent(
        segment_id=3,
        timestamp_us=10,
        channel=0,
        dropped_bytes=4,
    )
    assert await adapter.receive_event(0.1) == BufferStatusEvent(
        segment_id=3,
        timestamp_us=20,
        size_bytes=32768,
        used_bytes=8,
        high_water_bytes=16,
        dropped_bytes_total=4,
        overflow_events=1,
    )
    assert await adapter.receive_event(0.001) is None
    await adapter.close()


@pytest.mark.parametrize("timeout_s", [-0.001, float("inf"), float("nan"), True])
async def test_receive_event_rejects_invalid_timeouts(timeout_s: float) -> None:
    """Fails if invalid waits are passed to asyncio instead of rejected at the boundary."""

    adapter = make_adapter(FakeAsyncSerialReader())

    with pytest.raises(ValueError, match="Enhanced receive timeout"):
        await adapter.receive_event(timeout_s)


async def test_receive_event_accepts_zero_timeout() -> None:
    """Fails if a non-blocking evidence poll is rejected as an invalid timeout."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)

    await adapter.start(0.1)

    assert await adapter.receive_event(0) is None
    await adapter.close()


async def test_receive_event_drains_queued_evidence_before_terminal_error() -> None:
    """Fails if terminalization overtakes evidence that was already accepted into FIFO."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME + UART_FRAME)
    adapter = make_adapter(reader)

    await adapter.start(0.1)
    await reader.second_read_started.wait()
    reader.fail(OSError("device removed"))
    await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)

    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3,
        timestamp_us=0,
        channel=0,
        data=b"X",
    )
    with pytest.raises(BackendDisconnectedError, match="read failed"):
        await adapter.receive_event(0.1)

    await adapter.close()


async def test_cancelling_receive_event_cleans_up_its_waiters() -> None:
    """Fails if cancelling an event wait leaves queue or terminal waiter tasks pending."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)

    receive_task = asyncio.create_task(adapter.receive_event())
    await asyncio.sleep(0)
    receive_task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await receive_task
    await asyncio.sleep(0)

    current_task = asyncio.current_task()
    pending_tasks = {
        task
        for task in asyncio.all_tasks()
        if task is not current_task and not task.done()
    }
    assert pending_tasks == {adapter._reader_task}
    await adapter.close()


async def test_event_queue_applies_backpressure_without_dropping_wire_order() -> None:
    """Fails if a full bounded queue lets the sole reader advance before a drain."""

    reader = FakeAsyncSerialReader()
    reader.feed(
        HELLO_FRAME
        + b'{"type":"uart","channel":0,"timestamp_us":500,"data_b64":"WA=="}\n'
        + b'{"type":"buffer_overflow","channel":0,"timestamp_us":510,"dropped_bytes":4}\n'
    )
    adapter = make_adapter(reader, event_queue_capacity=1)

    await adapter.start(0.1)

    assert not reader.next_chunk_requested.is_set()
    assert await adapter.receive_event(0.1) == UartReceiveEvent(3, 0, 0, b"X")
    await asyncio.wait_for(reader.next_chunk_requested.wait(), timeout=0.1)
    assert await adapter.receive_event(0.1) == BufferOverflowEvent(3, 10, 0, 4)
    await adapter.close()


async def test_protocol_input_terminalization_stops_the_reader_without_explicit_close(
) -> None:
    """Fails if input terminalization leaves the only reader blocked for close()."""

    reader = FakeAsyncSerialReader()
    reader.feed(b'{"ok":true}\n')
    adapter = make_adapter(reader)

    try:
        with pytest.raises(BackendInputError, match="hello"):
            await adapter.start(0.1)

        await asyncio.wait_for(reader.closed_event.wait(), timeout=0.1)
        assert reader.active_reads == 0
        assert reader.close_count == 1
    finally:
        await adapter.close()


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


async def test_event_queue_backpressures_without_losing_fifo() -> None:
    """Fails if a full FIFO drops/reorders evidence or lets its sole reader advance."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, event_queue_capacity=1)
    await adapter.start(0.1)
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
        b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"WQ=="}\n'
    )

    await asyncio.wait_for(reader.second_read_returned.wait(), timeout=0.1)
    assert not reader.third_read_started.is_set()
    assert reader.active_reads == 0
    assert reader.maximum_concurrent_reads == 1
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    await asyncio.wait_for(reader.third_read_started.wait(), timeout=0.1)
    assert reader.maximum_concurrent_reads == 1
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=1, channel=0, data=b"Y"
    )
    await adapter.close()


async def test_valid_prefix_precedes_repeatable_terminal_input_error() -> None:
    """Fails if terminal input overtakes accepted evidence or changes on replay."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
        b'{"type":}\n'
        b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"WQ=="}\n'
    )

    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    with pytest.raises(BackendInputError) as first:
        await adapter.receive_event(0.1)
    with pytest.raises(BackendInputError) as second:
        await adapter.receive_event(0.1)
    assert first.value is second.value
    assert first.value.input_error == second.value.input_error == "invalid_json"


async def test_oversized_pending_frame_preserves_size_context() -> None:
    """Fails if pending-frame overflow loses its exact bounded size context."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    reader.feed(b"x" * MAX_DEVICE_FRAME_BYTES)

    with pytest.raises(BackendInputError) as raised:
        await adapter.receive_event(0.1)
    assert raised.value.input_error == "frame_too_large"
    assert raised.value.observed_frame_bytes == MAX_DEVICE_FRAME_BYTES
    assert raised.value.max_frame_bytes == MAX_DEVICE_FRAME_BYTES


async def test_invalid_frame_fails_response_but_keeps_prior_event() -> None:
    """Fails if same-batch response success masks invalid input or drops its prefix."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    assert not request.done()
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
        b'{"ok":true}\n'
        b'{"type":}\n'
    )

    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    with pytest.raises(BackendInputError):
        await request


async def test_repeated_hello_is_terminal_input_error() -> None:
    """Fails if a second hello is accepted as evidence or connection state."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    reader.feed(HELLO_FRAME)

    with pytest.raises(BackendInputError, match="hello"):
        await adapter.receive_event(0.1)


@pytest.mark.parametrize("outcome", [b"", OSError("removed")])
async def test_reader_failure_is_repeatable_disconnect(
    outcome: bytes | Exception,
) -> None:
    """Fails if EOF/read failure is raw, transient, or loses its original cause."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    if isinstance(outcome, Exception):
        reader.fail(outcome)
    else:
        reader.feed(outcome)

    with pytest.raises(BackendDisconnectedError) as first:
        await adapter.receive_event(0.1)
    with pytest.raises(BackendDisconnectedError) as second:
        await adapter.receive_event(0.1)
    assert first.value is second.value
    if isinstance(outcome, Exception):
        assert first.value.__cause__ is outcome


async def test_cancel_while_waiting_for_command_lock_keeps_connection() -> None:
    """Fails if pre-transmission cancellation poisons the shared connection."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    blocked_entered = asyncio.Event()
    blocked = asyncio.create_task(
        _request_after_entering(
            adapter,
            blocked_entered,
            b'{"cmd":"two"}\n',
            0.1,
        )
    )
    await asyncio.wait_for(blocked_entered.wait(), timeout=0.1)
    assert adapter._command_lock.locked()
    assert not blocked.done()
    blocked.cancel()
    with pytest.raises(asyncio.CancelledError):
        await blocked
    assert writer.frames == [b'{"cmd":"one"}\n']

    reader.feed(b'{"ok":true}\n')
    assert await first == CommandSuccessMessage()
    third = asyncio.create_task(adapter.request(b'{"cmd":"three"}\n', 0.1))
    assert await writer.written.get() == b'{"cmd":"three"}\n'
    reader.feed(b'{"ok":true,"timestamp_us":3}\n')
    assert await third == CommandSuccessMessage(timestamp_us=3)
    assert writer.frames == [b'{"cmd":"one"}\n', b'{"cmd":"three"}\n']
    assert reader.maximum_concurrent_reads == 1
    await adapter.close()


async def test_cancel_after_transmission_closes_connection() -> None:
    """Fails if post-transmission cancellation leaves an orphan response path."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    assert not request.done()
    assert writer.frames == [b'{"cmd":"one"}\n']

    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    assert reader.closed is True
    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)


async def test_command_timeout_closes_connection() -> None:
    """Fails if response timeout permits reuse of an uncorrelated command stream."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    with pytest.raises(TransportTimeoutError):
        await adapter.request(b'{"cmd":"one"}\n', 0.001)
    assert reader.closed is True
    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)


async def test_hello_timeout_is_transport_timeout_then_disconnect() -> None:
    """Fails if hello timeout leaks the reader or permits a later restart."""

    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)

    with pytest.raises(TransportTimeoutError):
        await adapter.start(0.001)
    assert reader.closed is True
    with pytest.raises(BackendDisconnectedError):
        await adapter.start(0.1)


async def test_close_is_idempotent_and_wakes_event_consumer() -> None:
    """Fails if close strands a consumer or closes its owned reader twice."""

    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    consumer_entered = asyncio.Event()
    receive = asyncio.create_task(_receive_after_entering(adapter, consumer_entered))
    await asyncio.wait_for(consumer_entered.wait(), timeout=0.1)
    assert not receive.done()

    await adapter.close()
    await adapter.close()

    with pytest.raises(BackendDisconnectedError) as consumer_error:
        await receive
    with pytest.raises(BackendDisconnectedError) as replayed_error:
        await adapter.receive_event(0.1)
    assert consumer_error.value is replayed_error.value
    assert reader.close_count == 1


async def test_close_wakes_blocked_hello_with_retained_terminal() -> None:
    """Fails if close strands hello or exposes a different terminal object."""

    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)
    start = asyncio.create_task(adapter.start(1.0))
    await asyncio.wait_for(reader.reading.wait(), timeout=0.1)
    assert not start.done()

    await adapter.close()

    with pytest.raises(BackendDisconnectedError) as hello_error:
        await start
    with pytest.raises(BackendDisconnectedError) as replayed_error:
        await adapter.receive_event(0.1)
    assert hello_error.value is replayed_error.value
    assert reader.close_count == 1


async def test_close_fails_pending_and_queued_commands() -> None:
    """Fails if close strands waiters, changes errors, or transmits queued work."""

    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    second_entered = asyncio.Event()
    second = asyncio.create_task(
        _request_after_entering(
            adapter,
            second_entered,
            b'{"cmd":"two"}\n',
            1.0,
        )
    )
    await asyncio.wait_for(second_entered.wait(), timeout=0.1)
    assert adapter._command_lock.locked()
    assert not second.done()
    consumer_entered = asyncio.Event()
    receive = asyncio.create_task(_receive_after_entering(adapter, consumer_entered))
    await asyncio.wait_for(consumer_entered.wait(), timeout=0.1)
    assert not receive.done()

    await adapter.close()

    with pytest.raises(BackendDisconnectedError) as first_error:
        await first
    with pytest.raises(BackendDisconnectedError) as second_error:
        await second
    with pytest.raises(BackendDisconnectedError) as event_error:
        await receive
    assert first_error.value is second_error.value is event_error.value
    assert writer.frames == [b'{"cmd":"one"}\n']


async def test_close_releases_request_blocked_in_write_frame() -> None:
    """Fails if close cannot release a transmitted request blocked in the writer."""

    reader = FakeAsyncSerialReader()
    writer = BlockingAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    assert await writer.written.get() == b'{"cmd":"one"}\n'
    second_entered = asyncio.Event()
    second = asyncio.create_task(
        _request_after_entering(
            adapter,
            second_entered,
            b'{"cmd":"two"}\n',
            1.0,
        )
    )
    await asyncio.wait_for(second_entered.wait(), timeout=0.1)
    assert adapter._command_lock.locked()
    assert not second.done()
    consumer_entered = asyncio.Event()
    receive = asyncio.create_task(_receive_after_entering(adapter, consumer_entered))
    await asyncio.wait_for(consumer_entered.wait(), timeout=0.1)
    assert not receive.done()

    await adapter.close()

    pending_tasks: set[asyncio.Task[object]] = set()
    try:
        _, pending = await asyncio.wait(
            {first, second, receive},
            timeout=0.1,
        )
        pending_tasks = set(pending)
        assert pending_tasks == set()
    finally:
        if pending_tasks:
            writer.release.set()
        await asyncio.gather(first, second, receive, return_exceptions=True)

    with pytest.raises(BackendDisconnectedError) as first_error:
        await first
    with pytest.raises(BackendDisconnectedError) as second_error:
        await second
    with pytest.raises(BackendDisconnectedError) as event_error:
        await receive
    assert first_error.value is second_error.value is event_error.value
    assert writer.frames == [b'{"cmd":"one"}\n']
    assert not writer.release.is_set()


async def test_resource_close_completion_is_shared_across_reader_cancellation_and_close(
) -> None:
    """Fails if cancellation turns resource-close start into false completion."""

    reader = CloseBlockingAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    reader.feed(b"")
    await asyncio.wait_for(reader.close_started.wait(), timeout=0.1)
    reader_task = adapter._reader_task
    assert reader_task is not None
    reader_stopped = asyncio.Event()
    reader_task.add_done_callback(lambda _task: reader_stopped.set())
    first_entered = asyncio.Event()
    second_entered = asyncio.Event()
    first = asyncio.create_task(_close_after_entering(adapter, first_entered))
    second = asyncio.create_task(_close_after_entering(adapter, second_entered))
    await asyncio.wait_for(first_entered.wait(), timeout=0.1)
    await asyncio.wait_for(second_entered.wait(), timeout=0.1)
    await asyncio.wait_for(reader_stopped.wait(), timeout=0.1)

    try:
        assert not first.done()
        assert not second.done()
    finally:
        reader.release_close.set()
        await asyncio.gather(first, second, return_exceptions=True)

    await adapter.close()
    assert first.exception() is None
    assert second.exception() is None
    assert reader.close_completed.is_set()
    assert reader.close_count == 1
