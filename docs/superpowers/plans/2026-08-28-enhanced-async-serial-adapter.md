# Enhanced Asynchronous Serial Adapter Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and fake-test one `AsyncEnhancedSerialAdapter` that exclusively reads an Enhanced connection, dispatches one serialized command response, and publishes normalized UART/telemetry events through a bounded asynchronous FIFO.

**Architecture:** The new adapter lives in the core backend adapter layer and composes the existing bounded NDJSON parser and Enhanced normalization functions. Injected asynchronous reader and frame-writer protocols isolate serial I/O; the first slice does not select the adapter in service startup. One reader task classifies the shared wire stream, one command lock permits one request in flight, and one bounded queue preserves event order.

**Tech Stack:** Python 3.10+, `asyncio`, typing `Protocol`, existing DUTchMate protocol/domain types, pytest, pytest-asyncio, Ruff, and mypy.

**Spec:** `docs/superpowers/specs/2026-08-27-enhanced-async-serial-adapter-design.md`

## Global Constraints

- The first implementation slice is fake-backed and must not change `apps/service` startup, reconnect, runtime, HTTP, CLI, MCP, firmware, or persisted session formats.
- `AsyncEnhancedSerialAdapter` is implemented in `core/src/dutchmate_core/backends/enhanced_serial.py` and is not re-exported from the stable `dutchmate_core.backends` facade in this slice.
- Exactly one task may call the injected reader for one adapter instance.
- Enhanced protocol v1 permits exactly one command in flight because responses have no correlation identifier.
- Device-to-host frames remain bounded at 65,536 bytes; host-to-device frames remain bounded at 2,048 bytes.
- The normalized event queue has a configurable positive capacity and defaults to exactly 256 events.
- Queue saturation applies backpressure; it never silently drops, overwrites, or reorders evidence.
- `receive_event()` returns `None` only for ordinary timeout and otherwise raises `BackendDisconnectedError` or `BackendInputError` after queued valid-prefix events are drained.
- A write failure raises `TransportWriteError` to that request, then leaves `BackendDisconnectedError` as the adapter's terminal backend outcome.
- A command timeout raises `TransportTimeoutError` to that request, then leaves `BackendDisconnectedError` as the terminal backend outcome.
- Cancellation while waiting for the command lock leaves the connection usable; cancellation after transmission begins closes it.
- Do not add production `pyserial-asyncio` wiring or an exact-accounting pyserial frame writer in this plan; those belong to the next integration slice.
- Do not introduce new third-party dependencies.
- Do not update the Graphify graph for this new module until the complete slice is implemented and verified.

## File Map

- Create `core/src/dutchmate_core/backends/enhanced_serial.py`: injected async I/O protocols and the single-owner Enhanced adapter.
- Create `tests/unit/backends/test_enhanced_serial.py`: deterministic async reader/writer fakes and adapter behavior tests.
- Modify `core/src/dutchmate_core/device_connection/stream.py`: expose the parser's retained terminal error without changing parsing.
- Modify `tests/unit/protocol/test_ndjson_stream_parser.py`: prove the new parser property before and after terminal input.
- Modify `core/src/dutchmate_core/device_connection/transport.py`: define `AsyncCommandTransport` and one shared host-frame validator.
- Modify `core/src/dutchmate_core/device_connection/serial_transport.py`: delegate existing synchronous validation to the shared validator without changing I/O behavior.
- Modify `core/src/dutchmate_core/backends/enhanced.py`: make the existing pure segment/timestamp helpers reusable by the new adapter.
- Modify `docs/development_status.md`: record completion evidence and retain the next production-integration step as the sole resume target.

---

### Task 1: Expose Retained Parser Failure

**Files:**

- Modify: `core/src/dutchmate_core/device_connection/stream.py`
- Test: `tests/unit/protocol/test_ndjson_stream_parser.py`

**Interfaces:**

- Consumes: existing `NdjsonStreamParser._terminal_error: ProtocolError | None`.
- Produces: `NdjsonStreamParser.terminal_error -> ProtocolError | None`.

- [ ] **Step 1: Write the failing parser-state tests**

Add these tests near the existing valid-prefix tests:

```python
def test_terminal_error_is_none_before_failure() -> None:
    parser = NdjsonStreamParser()

    assert parser.terminal_error is None


def test_terminal_error_exposes_failure_after_valid_prefix() -> None:
    parser = NdjsonStreamParser()

    messages = parser.feed(_UART_FRAME_BODY + b"\n{\"type\":}\n")

    assert messages == [UartMessage(channel=0, timestamp_us=1, data=b"X", text="X")]
    assert isinstance(parser.terminal_error, MalformedMessageError)
```

- [ ] **Step 2: Run the new tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/protocol/test_ndjson_stream_parser.py -k terminal_error -v
```

Expected: both tests fail because `NdjsonStreamParser` has no `terminal_error` property.

- [ ] **Step 3: Add the read-only property**

Insert immediately after `pending_bytes`:

```python
    @property
    def terminal_error(self) -> ProtocolError | None:
        """Return the first terminal parsing failure, if parsing has stopped."""

        return self._terminal_error
```

- [ ] **Step 4: Run parser tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/protocol/test_ndjson_stream_parser.py -v
```

Expected: all parser tests pass, including exact/pending frame limits and valid-prefix behavior.

- [ ] **Step 5: Commit the parser seam**

```bash
git add core/src/dutchmate_core/device_connection/stream.py tests/unit/protocol/test_ndjson_stream_parser.py
git commit -m "Expose Enhanced parser terminal state"
```

---

### Task 2: Start One Reader And Validate Hello

**Files:**

- Create: `core/src/dutchmate_core/backends/enhanced_serial.py`
- Create: `tests/unit/backends/test_enhanced_serial.py`

**Interfaces:**

- Consumes: `NdjsonStreamParser`, `normalize_enhanced_hello(hello, port=...)`, `BackendInfo`, `BackendDisconnectedError`, and `BackendInputError`.
- Produces: `AsyncSerialReader.read(size: int) -> bytes`, `AsyncSerialReader.close() -> None`, `AsyncFrameWriter.write_frame(frame: bytes) -> None`, and `AsyncEnhancedSerialAdapter.start(timeout_s: float) -> BackendInfo`.

- [ ] **Step 1: Add deterministic async I/O fakes and failing lifecycle tests**

Create `tests/unit/backends/test_enhanced_serial.py` with these shared fakes and tests:

```python
import asyncio

import pytest

from dutchmate_core.backends import BackendInfo, BackendInputError
from dutchmate_core.backends.enhanced_serial import AsyncEnhancedSerialAdapter

HELLO_FRAME = (
    b'{"type":"hello","v":1,"firmware":"0.1.0",'
    b'"device":"dutchmate-rp2040","capabilities":["uart_receive"]}\n'
)


class FakeAsyncSerialReader:
    def __init__(self) -> None:
        self.outcomes: asyncio.Queue[bytes | Exception] = asyncio.Queue()
        self.read_calls = 0
        self.closed = False
        self.close_count = 0

    async def read(self, size: int) -> bytes:
        self.read_calls += 1
        outcome = await self.outcomes.get()
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
    *,
    event_queue_capacity: int = 256,
) -> AsyncEnhancedSerialAdapter:
    return AsyncEnhancedSerialAdapter(
        reader=reader,
        writer=writer or FakeAsyncFrameWriter(),
        port="/dev/ttyACM0",
        segment_id=3,
        event_queue_capacity=event_queue_capacity,
    )


async def test_start_uses_one_reader_and_returns_normalized_hello() -> None:
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
    assert reader.read_calls == 2  # hello read plus one blocked follow-up read
    await adapter.close()


async def test_start_rejects_non_hello_first_message() -> None:
    reader = FakeAsyncSerialReader()
    reader.feed(b'{"ok":true}\n')
    adapter = make_adapter(reader)

    with pytest.raises(BackendInputError, match="hello"):
        await adapter.start(0.1)

    await adapter.close()


@pytest.mark.parametrize(
    "overrides",
    [
        {"segment_id": -1},
        {"read_size": 0},
        {"event_queue_capacity": 0},
    ],
)
def test_constructor_rejects_invalid_bounds(overrides: dict[str, int]) -> None:
    arguments: dict[str, object] = {
        "reader": FakeAsyncSerialReader(),
        "writer": FakeAsyncFrameWriter(),
        "port": "/dev/ttyACM0",
        "segment_id": 0,
    }
    arguments.update(overrides)

    with pytest.raises(ValueError):
        AsyncEnhancedSerialAdapter(**arguments)  # type: ignore[arg-type]
```

- [ ] **Step 2: Run lifecycle tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py -v
```

Expected: collection fails because `dutchmate_core.backends.enhanced_serial` does not exist.

- [ ] **Step 3: Create the adapter boundary and reader lifecycle**

Create `core/src/dutchmate_core/backends/enhanced_serial.py` with these public signatures and constructor state:

```python
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
    async def read(self, size: int) -> bytes:
        """Return the next serial byte chunk, or empty bytes for EOF."""

    async def close(self) -> None:
        """Close the owned serial resource."""


class AsyncFrameWriter(Protocol):
    async def write_frame(self, frame: bytes) -> None:
        """Write and flush one complete host command frame."""


class AsyncEnhancedSerialAdapter:
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
        if self._info is None:
            raise RuntimeError("Enhanced serial adapter has not completed hello")
        return self._info

    @property
    def segment_id(self) -> int:
        return self._segment_id

    @property
    def segment(self) -> SegmentContext | None:
        return self._segment
```

Implement `start()`, `_read_loop()`, initial-hello dispatch, `_set_terminal()`, and `close()` with these rules:

```python
    async def start(self, timeout_s: float) -> BackendInfo:
        _validate_timeout(timeout_s, field="Enhanced hello timeout")
        async with self._start_lock:
            self._raise_if_terminal()
            if self._info is not None:
                return self._info
            if self._reader_task is None:
                self._hello_waiter = asyncio.get_running_loop().create_future()
                self._reader_task = asyncio.create_task(
                    self._read_loop(), name="dutchmate-enhanced-serial-reader"
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
                if self._terminal_error is not None:
                    return
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
        async with self._close_lock:
            if self._closed:
                return
            self._closed = True
            await self._terminate(
                BackendDisconnectedError("Enhanced serial adapter is closed")
            )
```

For Task 2, `_dispatch_batch()` accepts exactly one initial `HelloMessage`, normalizes it, and treats every other first message or repeated hello as `BackendInputError` containing `hello`. Later tasks extend the same method for event and response messages.

Add the timeout validator used by this and later tasks:

```python
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
```

- [ ] **Step 4: Run lifecycle tests and verify GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py -v
```

Expected: both lifecycle tests pass with no pending-task warning.

- [ ] **Step 5: Run type/lint checks for the new module**

Run:

```bash
.venv/bin/ruff check core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
.venv/bin/mypy core/src/dutchmate_core/backends/enhanced_serial.py
```

Expected: both commands exit successfully.

- [ ] **Step 6: Commit the single-reader hello lifecycle**

```bash
git add core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
git commit -m "Add Enhanced async reader lifecycle"
```

---

### Task 3: Publish Normalized Events With Provenance

**Files:**

- Modify: `core/src/dutchmate_core/backends/enhanced.py`
- Modify: `core/src/dutchmate_core/backends/enhanced_serial.py`
- Test: `tests/unit/backends/test_enhanced_serial.py`

**Interfaces:**

- Consumes: Task 2 `AsyncEnhancedSerialAdapter`, `normalize_enhanced_message()`, and the injected fake reader.
- Produces: `enhanced_message_timestamp_us(message) -> int | None`, `enhanced_segment_context(segment_id, source_origin_us) -> SegmentContext`, and `AsyncEnhancedSerialAdapter.receive_event(timeout_s: float | None = None) -> BackendEvent | None`.

- [ ] **Step 1: Write failing FIFO/provenance/timeout tests**

Append tests that feed hello plus UART, overflow, and status frames in one chunk. Assert exact FIFO output and first-event origin:

```python
async def test_receive_event_normalizes_fifo_and_establishes_origin() -> None:
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
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    assert await adapter.receive_event(0.1) == BufferOverflowEvent(
        segment_id=3, timestamp_us=10, channel=0, dropped_bytes=4
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
```

Import `BufferOverflowEvent`, `BufferStatusEvent`, and `UartReceiveEvent` from `dutchmate_core.backends`.

- [ ] **Step 2: Run the new test and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py::test_receive_event_normalizes_fifo_and_establishes_origin -v
```

Expected: failure because `receive_event()` and reusable provenance helpers do not exist.

- [ ] **Step 3: Make Enhanced normalization helpers reusable**

In `enhanced.py`, rename `_enhanced_segment_context` to `enhanced_segment_context` and `_message_timestamp_us` to `enhanced_message_timestamp_us`; update all existing references in that module. Keep these exact implementations and do not export them from `backends/__init__.py`:

```python
def enhanced_segment_context(
    segment_id: int,
    source_origin_us: int,
) -> SegmentContext:
    return SegmentContext(
        segment_id=segment_id,
        timestamp=SegmentTimestamp(
            source="device",
            clock="rp2040_timer",
            unit="us",
            origin="segment_start",
            source_origin_us=source_origin_us,
            observation_point="debug_helper_uart_receive",
            event_granularity="uart_event",
        ),
    )


def enhanced_message_timestamp_us(message: DeviceMessage) -> int | None:
    if isinstance(message, (UartMessage, BufferOverflowMessage, BufferStatusMessage)):
        return message.timestamp_us
    return None
```

- [ ] **Step 4: Dispatch evidence and implement event waiting**

Import the reusable helpers, `normalize_enhanced_message`, and evidence message types in `enhanced_serial.py`. Replace Task 2's post-hello fallback with this evidence branch before reporting an unexpected message:

```python
            timestamp_us = enhanced_message_timestamp_us(message)
            if timestamp_us is not None:
                if self._segment is None:
                    self._segment = enhanced_segment_context(
                        self._segment_id,
                        timestamp_us,
                    )
                event = normalize_enhanced_message(
                    message,
                    segment_id=self._segment_id,
                    source_origin_us=self._segment.timestamp.source_origin_us,
                )
                assert event is not None
                await self._events.put(event)
                continue
```

Implement event waiting without inserting a terminal sentinel into the bounded evidence queue:

```python
    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
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
```

- [ ] **Step 5: Run async and legacy Enhanced tests**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py tests/unit/backends/test_enhanced.py tests/unit/backends/test_contracts.py -v
```

Expected: all tests pass; synchronous compatibility behavior is unchanged.

- [ ] **Step 6: Commit normalized asynchronous event delivery**

```bash
git add core/src/dutchmate_core/backends/enhanced.py core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
git commit -m "Publish Enhanced async backend events"
```

---

### Task 4: Serialize And Dispatch Command Requests

**Files:**

- Modify: `core/src/dutchmate_core/device_connection/transport.py`
- Modify: `core/src/dutchmate_core/device_connection/serial_transport.py`
- Modify: `core/src/dutchmate_core/backends/enhanced_serial.py`
- Test: `tests/unit/protocol/test_serial_transport.py`
- Test: `tests/unit/backends/test_enhanced_serial.py`

**Interfaces:**

- Consumes: Task 2 `AsyncFrameWriter.write_frame()`, Task 3 event dispatch, `MAX_HOST_FRAME_BYTES`, and existing `TransportWriteError`/`TransportTimeoutError`.
- Produces: `AsyncCommandTransport.request(command: bytes, timeout_s: float) -> DeviceMessage`, `validate_host_command_frame(command: bytes) -> None`, and the matching adapter method.

- [ ] **Step 1: Write failing shared-validation and interleaving tests**

Add this synchronous regression test to `test_serial_transport.py` after `_compact_json_frame_of_size`, importing `validate_host_command_frame` from `device_connection.transport`:

```python
def test_shared_host_frame_validator_preserves_exact_limit() -> None:
    validate_host_command_frame(_compact_json_frame_of_size(MAX_HOST_FRAME_BYTES))

    with pytest.raises(HostCommandFrameTooLargeError) as raised:
        validate_host_command_frame(
            _compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1)
        )

    assert raised.value.actual_frame_bytes == MAX_HOST_FRAME_BYTES + 1
    assert raised.value.max_frame_bytes == MAX_HOST_FRAME_BYTES
```

Add async tests with these assertions, importing `CommandErrorMessage` and `CommandSuccessMessage`:

```python
async def test_request_routes_response_and_retains_interleaved_event() -> None:
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    request = asyncio.create_task(adapter.request(b'{"cmd":"test"}\n', 0.1))
    await asyncio.sleep(0)
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


async def test_concurrent_requests_write_only_one_frame_at_a_time() -> None:
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    second = asyncio.create_task(adapter.request(b'{"cmd":"two"}\n', 0.1))
    await asyncio.sleep(0)
    assert writer.frames == [b'{"cmd":"one"}\n']

    reader.feed(b'{"ok":true,"timestamp_us":1}\n')
    assert await first == CommandSuccessMessage(timestamp_us=1)
    await asyncio.sleep(0)
    assert writer.frames == [b'{"cmd":"one"}\n', b'{"cmd":"two"}\n']
    reader.feed(b'{"ok":false,"error":"timeout","detail":"busy"}\n')
    assert await second == CommandErrorMessage(error="timeout", detail="busy")
    await adapter.close()
```

Add these validation and write-failure tests; `_compact_json_frame_of_size()` in this new test module uses the same calculation as the synchronous transport test:

```python
async def test_request_rejects_invalid_frames_before_writer() -> None:
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
        await adapter.request(_compact_json_frame_of_size(MAX_HOST_FRAME_BYTES + 1), 0.1)

    assert writer.frames == []
    await adapter.close()


async def test_write_failure_preserves_frame_count_then_disconnects() -> None:
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    writer.failure = TransportWriteError(
        "write failed",
        frame_bytes_accepted=7,
        error="hardware_fault",
    )
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)

    with pytest.raises(TransportWriteError) as raised:
        await adapter.request(b'{"cmd":"test"}\n', 0.1)
    assert raised.value.frame_bytes_accepted == 7

    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)
```

Also feed `b'{"ok":true}\n'` after a successful hello without starting a request and assert `BackendInputError` from `receive_event()`.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py -k "request or concurrent" -v
.venv/bin/pytest tests/unit/protocol/test_serial_transport.py -k host_frame -v
```

Expected: failures because the async protocol, validator, and adapter request path do not exist.

- [ ] **Step 3: Add the shared async protocol and frame validator**

In `transport.py`, add:

```python
from dutchmate_core.device_connection.commands import MAX_HOST_FRAME_BYTES
from dutchmate_core.device_connection.errors import HostCommandFrameTooLargeError


class AsyncCommandTransport(Protocol):
    """Asynchronous one-at-a-time host command exchange."""

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        """Send one complete command and return its parsed response."""


def validate_host_command_frame(command: bytes) -> None:
    """Validate the complete encoded host frame before serial dispatch."""

    if not isinstance(command, bytes):
        raise TypeError("serial commands must be bytes")
    if len(command) > MAX_HOST_FRAME_BYTES:
        raise HostCommandFrameTooLargeError(
            actual_frame_bytes=len(command),
            max_frame_bytes=MAX_HOST_FRAME_BYTES,
        )
    if not command.endswith(b"\n"):
        raise ValueError("serial commands must be newline-terminated NDJSON")
```

Replace the identical initial checks in `SerialCommandTransport.request()` with `validate_host_command_frame(command)`. Run all existing serial transport tests to prove unchanged synchronous behavior.

- [ ] **Step 4: Implement serialized asynchronous requests**

Add `self._command_lock = asyncio.Lock()` and `self._pending_response: asyncio.Future[DeviceMessage] | None = None`. Extend dispatch so only `CommandSuccessMessage` or `CommandErrorMessage` completes the pending future; a response with no pending future sets a `BackendInputError` terminal state.

Insert this branch after evidence dispatch and before the unexpected-message fallback. Checking the parser's terminal state prevents a response from succeeding when a later frame in the same read is invalid:

```python
            if isinstance(message, (CommandSuccessMessage, CommandErrorMessage)):
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
                    return
                pending.set_result(message)
                continue
```

Implement `request()` with this structure:

```python
    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        validate_host_command_frame(command)
        _validate_timeout(timeout_s, field="Enhanced command timeout")
        transmission_started = False
        async with self._command_lock:
            self._raise_if_terminal()
            response = asyncio.get_running_loop().create_future()
            self._pending_response = response
            try:
                transmission_started = True
                await self._writer.write_frame(command)
                try:
                    return await asyncio.wait_for(asyncio.shield(response), timeout_s)
                except TimeoutError as exc:
                    timeout = TransportTimeoutError(
                        "Timed out waiting for Enhanced command response"
                    )
                    response.cancel()
                    await self._terminate(
                        BackendDisconnectedError(
                            "Enhanced command response timed out; connection closed"
                        )
                    )
                    raise timeout from exc
            except TransportWriteError:
                response.cancel()
                await self._terminate(
                    BackendDisconnectedError(
                        "Enhanced command write failed; connection closed"
                    )
                )
                raise
            except asyncio.CancelledError:
                if transmission_started:
                    response.cancel()
                    await asyncio.shield(
                        self._terminate(
                            BackendDisconnectedError(
                                "Enhanced command cancelled after transmission began"
                            )
                        )
                    )
                raise
            finally:
                if self._pending_response is response:
                    self._pending_response = None
```

`_set_terminal()` must set the terminal exception on an unfinished pending response. `_terminate()` must set terminal state, close the reader resource, and await reader-task completion without awaiting the current reader task.

- [ ] **Step 5: Run command, serial transport, and adapter suites**

Run:

```bash
.venv/bin/pytest tests/unit/protocol/test_serial_transport.py tests/unit/backends/test_enhanced_serial.py -v
```

Expected: all tests pass, including synchronous short-write accounting and asynchronous interleaving.

- [ ] **Step 6: Commit command routing**

```bash
git add core/src/dutchmate_core/device_connection/transport.py core/src/dutchmate_core/device_connection/serial_transport.py core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/protocol/test_serial_transport.py tests/unit/backends/test_enhanced_serial.py
git commit -m "Route Enhanced async command responses"
```

---

### Task 5: Prove Backpressure, Terminal Errors, Cancellation, And Shutdown

**Files:**

- Modify: `core/src/dutchmate_core/backends/enhanced_serial.py`
- Test: `tests/unit/backends/test_enhanced_serial.py`

**Interfaces:**

- Consumes: the complete Task 4 adapter and fakes.
- Produces: repeatable terminal behavior and deterministic lifecycle semantics required by the approved spec.

- [ ] **Step 1: Add failing bounded-queue and valid-prefix tests**

Import `MAX_DEVICE_FRAME_BYTES` from `device_connection.stream`. Use these exact tests for queue capacity and terminal-prefix ordering:

```python
async def test_event_queue_backpressures_without_losing_fifo() -> None:
    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, event_queue_capacity=1)
    await adapter.start(0.1)
    reader.feed(
        b'{"type":"uart","channel":0,"timestamp_us":10,"data_b64":"WA=="}\n'
        b'{"type":"uart","channel":0,"timestamp_us":11,"data_b64":"WQ=="}\n'
    )

    await asyncio.sleep(0)
    assert reader.read_calls == 2
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=0, channel=0, data=b"X"
    )
    await asyncio.sleep(0)
    assert reader.read_calls == 3
    assert await adapter.receive_event(0.1) == UartReceiveEvent(
        segment_id=3, timestamp_us=1, channel=0, data=b"Y"
    )
    await adapter.close()


async def test_valid_prefix_precedes_repeatable_terminal_input_error() -> None:
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
    assert first.value.input_error == second.value.input_error == "invalid_json"


async def test_oversized_pending_frame_preserves_size_context() -> None:
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
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    await asyncio.sleep(0)
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
    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    reader.feed(HELLO_FRAME)

    with pytest.raises(BackendInputError, match="hello"):
        await adapter.receive_event(0.1)
```

- [ ] **Step 2: Add failing disconnect and cancellation tests**

Add exact disconnect and cancellation coverage:

```python
@pytest.mark.parametrize("outcome", [b"", OSError("removed")])
async def test_reader_failure_is_repeatable_disconnect(
    outcome: bytes | Exception,
) -> None:
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
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 0.1))
    blocked = asyncio.create_task(adapter.request(b'{"cmd":"two"}\n', 0.1))
    await asyncio.sleep(0)
    blocked.cancel()
    with pytest.raises(asyncio.CancelledError):
        await blocked

    reader.feed(b'{"ok":true}\n')
    assert await first == CommandSuccessMessage()
    third = asyncio.create_task(adapter.request(b'{"cmd":"three"}\n', 0.1))
    await asyncio.sleep(0)
    reader.feed(b'{"ok":true,"timestamp_us":3}\n')
    assert await third == CommandSuccessMessage(timestamp_us=3)
    await adapter.close()


async def test_cancel_after_transmission_closes_connection() -> None:
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    request = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    await asyncio.sleep(0)
    assert writer.frames == [b'{"cmd":"one"}\n']

    request.cancel()
    with pytest.raises(asyncio.CancelledError):
        await request
    assert reader.closed is True
    with pytest.raises(BackendDisconnectedError):
        await adapter.receive_event(0.1)


async def test_command_timeout_closes_connection() -> None:
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
    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)

    with pytest.raises(TransportTimeoutError):
        await adapter.start(0.001)
    assert reader.closed is True
    with pytest.raises(BackendDisconnectedError):
        await adapter.start(0.1)


async def test_close_is_idempotent_and_wakes_event_consumer() -> None:
    reader = FakeAsyncSerialReader()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader)
    await adapter.start(0.1)
    receive = asyncio.create_task(adapter.receive_event())
    await asyncio.sleep(0)

    await adapter.close()
    await adapter.close()

    with pytest.raises(BackendDisconnectedError):
        await receive
    assert reader.close_count == 1


async def test_close_fails_pending_and_queued_commands() -> None:
    reader = FakeAsyncSerialReader()
    writer = FakeAsyncFrameWriter()
    reader.feed(HELLO_FRAME)
    adapter = make_adapter(reader, writer)
    await adapter.start(0.1)
    first = asyncio.create_task(adapter.request(b'{"cmd":"one"}\n', 1.0))
    second = asyncio.create_task(adapter.request(b'{"cmd":"two"}\n', 1.0))
    await asyncio.sleep(0)

    await adapter.close()

    with pytest.raises(BackendDisconnectedError):
        await first
    with pytest.raises(BackendDisconnectedError):
        await second
    assert writer.frames == [b'{"cmd":"one"}\n']
```

- [ ] **Step 3: Run the lifecycle tests and verify RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py -k "backpressure or prefix or disconnect or cancel or timeout or close" -v
```

Expected: the valid-prefix response, in-flight cancellation, hello/command timeout, and blocked-waiter tests fail until terminal ordering, cancellation-safe cleanup, and close wake-up are complete.

- [ ] **Step 4: Complete terminal-state and shutdown implementation**

Ensure `_dispatch_batch()` checks `parser.terminal_error` before completing hello or command response futures from that batch, but still queues valid-prefix evidence. Ensure `_set_terminal()` retains only the first backend error and sets `self._terminal`. Ensure `_raise_if_terminal()` raises the retained object after the evidence queue is empty.

Retain the exactly-once resource closure introduced in Task 2:

```python
    async def _close_resource(self) -> None:
        if self._resource_closed:
            return
        self._resource_closed = True
        await self._reader.close()
```

Make `_terminate()` safe both inside and outside the reader task:

```python
    async def _terminate(
        self,
        error: BackendDisconnectedError | BackendInputError,
    ) -> None:
        self._set_terminal(error)
        task = self._reader_task
        current = asyncio.current_task()
        if task is not None and task is not current and not task.done():
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        await self._close_resource()
```

When a terminal signal and queued event are simultaneously ready,
`receive_event()` must return the queued event first. After the queue is empty,
it raises the retained terminal error without waiting.

- [ ] **Step 5: Run the complete focused suite**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py tests/unit/backends/test_enhanced.py tests/unit/backends/test_contracts.py tests/unit/protocol/test_ndjson_stream_parser.py tests/unit/protocol/test_serial_transport.py -v
```

Expected: all focused tests pass without pending-task, unhandled-future, or unawaited-coroutine warnings.

- [ ] **Step 6: Run focused static checks**

Run:

```bash
.venv/bin/ruff check core/src/dutchmate_core/backends/enhanced_serial.py core/src/dutchmate_core/backends/enhanced.py core/src/dutchmate_core/device_connection/stream.py core/src/dutchmate_core/device_connection/transport.py core/src/dutchmate_core/device_connection/serial_transport.py tests/unit/backends/test_enhanced_serial.py tests/unit/protocol/test_ndjson_stream_parser.py tests/unit/protocol/test_serial_transport.py
.venv/bin/mypy core/src/dutchmate_core/backends/enhanced_serial.py core/src/dutchmate_core/backends/enhanced.py core/src/dutchmate_core/device_connection
```

Expected: both commands exit successfully.

- [ ] **Step 7: Commit completed fake-backed adapter behavior**

```bash
git add core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
git commit -m "Harden Enhanced async adapter lifecycle"
```

---

### Task 6: Reconcile Status, Graph, And Full Validation

**Files:**

- Modify: `docs/development_status.md`
- Update generated files: `graphify-out/` through `graphify update .`

**Interfaces:**

- Consumes: the verified adapter slice from Tasks 1-5.
- Produces: one authoritative resume target and graph evidence matching the new module/interface relationships.

- [ ] **Step 1: Run the complete repository validation gate**

Run each command independently:

```bash
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest
git diff --check
```

Expected: Ruff exits zero; mypy reports success for every configured source file; pytest reports zero failures; `git diff --check` prints no errors.

- [ ] **Step 2: Update the Graphify graph after the structural change**

Run:

```bash
graphify update .
```

Expected: the graph update completes and includes `AsyncEnhancedSerialAdapter`, `AsyncCommandTransport`, and their relationships. Do not stage generated Graphify files unless the repository's established commit policy for this working tree explicitly requires them.

- [ ] **Step 3: Reconcile the sole development-status document**

Run `git rev-parse --short HEAD` and put that exact code commit in the baseline line. Update the review date to `2026-08-28`. Record:

- the fake-backed `AsyncEnhancedSerialAdapter` foundation is complete;
- it is not production-selected yet;
- the next step is the real `pyserial-asyncio` read factory plus exact-accounting asynchronous frame writer and service composition integration;
- a completed nested checklist item under step 4 for the fake-backed single-reader/dispatcher foundation;
- the exact Ruff, mypy source-file count, pytest passed count, focused test evidence, and `git diff --check` result printed in Step 1.

Do not mark the existing “Replace the interim synchronous message source” or continuous-ingestion items complete because production still uses `SerialCommandTransport` and `EnhancedCaptureEventSource`.

- [ ] **Step 4: Verify status has no competing or stale next step**

Run:

```bash
rg -n "Next step|First implementation slice|AsyncEnhancedSerialAdapter|pyserial-asyncio|Code baseline reviewed|Latest Validation" docs/development_status.md
git diff --check
```

Expected: one current resume target points to production async integration, the completed foundation is evidence rather than a competing queue, and the diff check is clean.

- [ ] **Step 5: Commit status reconciliation**

```bash
git add docs/development_status.md
git commit -m "Record Enhanced async adapter foundation"
```

- [ ] **Step 6: Confirm final commit and worktree scope**

Run:

```bash
git log -2 --oneline
git status --short
```

Expected: the latest commit records status reconciliation; any remaining dirty files are pre-existing or generated Graphify artifacts, not uncommitted adapter/source/test/status work.
