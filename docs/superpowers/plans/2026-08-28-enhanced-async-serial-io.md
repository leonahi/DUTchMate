# Enhanced Asynchronous Serial I/O Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one production-capable `pyserial-asyncio` connection factory that supplies `AsyncEnhancedSerialAdapter` with a single owned reader and an exact-accounting writer while preserving the synchronous production path.

**Architecture:** Extract the proven pyserial write/flush loop into one reusable device-connection helper, then build a concrete async I/O module around one `pyserial-asyncio` stream pair and its underlying serial object. The factory returns only a hello-validated adapter and closes every failed start; service startup remains synchronous until its consumers migrate atomically in a later slice.

**Tech Stack:** Python 3.10+, `asyncio`, `pyserial-asyncio>=0.6`, pyserial-compatible sinks, pytest/pytest-asyncio, Ruff, mypy, Graphify

**Spec:** `docs/superpowers/specs/2026-08-28-enhanced-async-serial-io-design.md`

## Global Constraints

- Keep production service startup on `SerialCommandTransport`; do not modify FastAPI endpoints, `DeviceCoreRuntime`, semantic control/UART adapters, continuous ingestion, or reconnect behavior.
- One physical Enhanced connection has one serial resource and exactly one physical reader. Never open a synchronous transport beside the async adapter.
- `StreamWriter.write()` must never carry command data. Async writes use `asyncio.to_thread()` against the same underlying serial object and the shared exact-accounting loop.
- Device-to-host frames remain bounded at 65,536 bytes; host-to-device frames remain bounded at 2,048 bytes.
- The async event queue remains positive and configurable with default capacity 256; adapter read chunks remain 4,096 bytes.
- The dependency floor remains `pyserial-asyncio>=0.6`; add no dependency or version change.
- A factory returns only a fully started, hello-validated adapter. Inspection, construction, hello, and cancellation failures close the stream exactly once without replacing the primary error.
- Preserve all existing synchronous behavior and public APIs. Do not remove compatibility code in this slice.
- Do not expose `asyncio`, `serial_asyncio`, pyserial, or Enhanced wire DTOs to application/domain policy.
- Update `docs/development_status.md` only when the complete production-I/O slice passes its gates; keep Phase 1B partial and name the semantic-consumer/lifecycle migration as the sole next step.
- Leave generated `graphify-out/` artifacts unstaged.

## File Responsibility Map

- `core/src/dutchmate_core/device_connection/serial_transport.py`: pyserial-compatible exact frame-write algorithm shared by synchronous and async infrastructure adapters.
- `core/src/dutchmate_core/backends/enhanced_serial_io.py`: library-specific stream wrappers, same-resource writer, cleanup, and production open/start factory.
- `tests/unit/protocol/test_serial_transport.py`: direct shared-writer contract plus unchanged synchronous request behavior.
- `tests/unit/backends/test_enhanced_serial_io.py`: deterministic stream/resource ownership, thread delegation, factory startup, and failure cleanup.
- `docs/development_status.md`: sole progress record, validation evidence, and next-step queue.

---

### Task 1: Extract The Exact Serial Frame Writer

**Files:**
- Modify: `core/src/dutchmate_core/device_connection/serial_transport.py:20-110`
- Modify: `tests/unit/protocol/test_serial_transport.py:1-170`

**Interfaces:**
- Consumes: `validate_host_command_frame(frame: bytes) -> None`, `TransportWriteError`, and `TransportWriteErrorCode` from `dutchmate_core.device_connection.transport`.
- Produces: `SerialFrameSink(Protocol)` with `write(data: bytes) -> int` and `flush() -> None`; `write_serial_frame(serial_port: SerialFrameSink, frame: bytes) -> None`.
- Preserves: `SerialPort`, `SerialCommandTransport.request(command: bytes) -> DeviceMessage`, and `open_serial_command_transport(...)` behavior and signatures.

- [ ] **Step 1: Add a failing direct contract test for the shared writer**

Extend the import and add this test using the existing `FakeSerial`:

```python
from dutchmate_core.device_connection.serial_transport import (
    SerialCommandTransport,
    open_serial_command_transport,
    write_serial_frame,
)


def test_shared_serial_frame_writer_retries_ordered_short_writes_and_flushes() -> None:
    frame = b'{"cmd":"test"}\n'
    serial = FakeSerial(write_outcomes=[2, 3, len(frame) - 5])

    write_serial_frame(serial, frame)

    assert serial.writes == [frame, frame[2:], frame[5:]]
    assert serial.flush_count == 1
    assert serial.read_sizes == []
```

- [ ] **Step 2: Run the new test and capture RED**

Run:

```bash
../../.venv/bin/pytest tests/unit/protocol/test_serial_transport.py::test_shared_serial_frame_writer_retries_ordered_short_writes_and_flushes -v
```

Expected: collection fails because `write_serial_frame` does not exist.

- [ ] **Step 3: Extract the narrow sink and exact writer**

Add the sink protocol, move the current ordered loop into the helper without changing error text or classification, and delegate from `request()`:

```python
class SerialFrameSink(Protocol):
    """Pyserial-compatible surface for exact host frame writes."""

    def write(self, data: bytes) -> int:
        """Return the number of bytes accepted from data."""

    def flush(self) -> None:
        """Wait until accepted output is flushed."""


class SerialPort(SerialFrameSink, Protocol):
    """Small pyserial-compatible surface used by the command transport."""

    def read_until(self, expected: bytes = b"\n", size: int | None = None) -> bytes:
        """Read bytes until a delimiter or timeout."""

    def close(self) -> None:
        """Close the serial port."""


def write_serial_frame(serial_port: SerialFrameSink, frame: bytes) -> None:
    """Write and flush one complete frame with exact accepted-byte errors."""

    validate_host_command_frame(frame)
    accepted = 0
    while accepted < len(frame):
        remaining = len(frame) - accepted
        try:
            written = serial_port.write(frame[accepted:])
        except Exception as exc:
            raise TransportWriteError(
                "Enhanced serial command write failed",
                frame_bytes_accepted=accepted,
                error=_classify_serial_write_error(exc),
            ) from exc
        if (
            isinstance(written, bool)
            or not isinstance(written, int)
            or written <= 0
            or written > remaining
        ):
            raise TransportWriteError(
                "Enhanced serial command write made invalid progress",
                frame_bytes_accepted=accepted,
                error=(
                    "timeout"
                    if written == 0 and not isinstance(written, bool)
                    else "hardware_fault"
                ),
            )
        accepted += written
    try:
        serial_port.flush()
    except Exception as exc:
        raise TransportWriteError(
            "Enhanced serial command flush failed",
            frame_bytes_accepted=accepted,
            error=_classify_serial_write_error(exc),
        ) from exc
```

Inside `SerialCommandTransport.request()`, retain the existing `_io_lock`, call
`write_serial_frame(self._serial_port, command)`, then keep the existing response
read/classification loop unchanged.

- [ ] **Step 4: Run direct and synchronous regression tests for GREEN**

Run:

```bash
../../.venv/bin/pytest tests/unit/protocol/test_serial_transport.py -v
../../.venv/bin/pytest tests/unit/backends/test_enhanced.py tests/unit/protocol/test_host_command_encoder.py -v
```

Expected: all selected tests pass; short-write, invalid-progress, partial-failure,
flush-failure, and exact 2,048/2,049-byte behavior remain unchanged.

- [ ] **Step 5: Run focused static checks**

Run:

```bash
../../.venv/bin/ruff check core/src/dutchmate_core/device_connection/serial_transport.py tests/unit/protocol/test_serial_transport.py
../../.venv/bin/mypy core/src/dutchmate_core/device_connection/serial_transport.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 6: Commit the shared writer extraction**

```bash
git add core/src/dutchmate_core/device_connection/serial_transport.py tests/unit/protocol/test_serial_transport.py
git commit -m "Extract exact serial frame writer"
```

---

### Task 2: Add Concrete Async Stream Reader And Writer Wrappers

**Files:**
- Create: `core/src/dutchmate_core/backends/enhanced_serial_io.py`
- Create: `tests/unit/backends/test_enhanced_serial_io.py`

**Interfaces:**
- Consumes: `AsyncSerialReader` and `AsyncFrameWriter` behavior from `dutchmate_core.backends.enhanced_serial`; `SerialFrameSink` and `write_serial_frame()` from Task 1.
- Produces: private `_OwnedStreamReader(reader, writer)` implementing `read(size)` and shared idempotent `close()`; private `_ThreadedSerialFrameWriter(serial_port)` implementing `write_frame(frame)`.
- Later task dependency: `_OwnedStreamReader` retains the paired stream writer; `_ThreadedSerialFrameWriter` retains exactly the serial sink passed by the stream transport.

- [ ] **Step 1: Create deterministic stream and serial fakes**

Create `tests/unit/backends/test_enhanced_serial_io.py` with these minimal fakes:

```python
import asyncio
import threading

import pytest


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
```

- [ ] **Step 2: Add RED tests for delegation, shared close, and worker-thread writes**

Add tests that import the not-yet-created private wrappers:

```python
from dutchmate_core.backends.enhanced_serial_io import (
    _OwnedStreamReader,
    _ThreadedSerialFrameWriter,
)
from dutchmate_core.device_connection.transport import TransportWriteError


async def test_owned_stream_reader_delegates_reads_and_shares_close_completion() -> None:
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
    frame = b'{"cmd":"test"}\n'
    serial = ThreadTrackingSerial([2, OSError("adapter removed")])
    writer = _ThreadedSerialFrameWriter(serial)

    with pytest.raises(TransportWriteError) as raised:
        await writer.write_frame(frame)

    assert raised.value.frame_bytes_accepted == 2
    assert raised.value.error == "hardware_fault"
    assert serial.flush_count == 0
```

- [ ] **Step 3: Run the wrapper tests and capture RED**

Run:

```bash
../../.venv/bin/pytest tests/unit/backends/test_enhanced_serial_io.py -v
```

Expected: collection fails because `enhanced_serial_io` does not exist.

- [ ] **Step 4: Implement the minimal concrete wrappers**

Create the module with narrow internal stream protocols and these implementations:

```python
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
```

- [ ] **Step 5: Run wrapper GREEN and boundary regressions**

Run:

```bash
../../.venv/bin/pytest tests/unit/backends/test_enhanced_serial_io.py tests/unit/protocol/test_serial_transport.py tests/unit/backends/test_enhanced_serial.py -v
../../.venv/bin/ruff check core/src/dutchmate_core/backends/enhanced_serial_io.py tests/unit/backends/test_enhanced_serial_io.py
../../.venv/bin/mypy core/src/dutchmate_core/backends/enhanced_serial_io.py
git diff --check
```

Expected: all commands exit zero, with no new task/future/coroutine warning.

- [ ] **Step 6: Commit the concrete wrappers**

```bash
git add core/src/dutchmate_core/backends/enhanced_serial_io.py tests/unit/backends/test_enhanced_serial_io.py
git commit -m "Add Enhanced async serial I/O wrappers"
```

---

### Task 3: Open And Start One Production Async Enhanced Adapter

**Files:**
- Modify: `core/src/dutchmate_core/backends/enhanced_serial_io.py`
- Modify: `tests/unit/backends/test_enhanced_serial_io.py`
- Modify: `docs/development_status.md:1-75, active Phase 1 queue step 4`

**Interfaces:**
- Consumes: Task 2 `_OwnedStreamReader` and `_ThreadedSerialFrameWriter`; `AsyncEnhancedSerialAdapter`; `MAX_DEVICE_FRAME_BYTES`; pyserial-asyncio 0.6 `open_serial_connection(*, url, baudrate, limit)` and `StreamWriter.transport.get_extra_info("serial")`.
- Produces: `OpenSerialConnection(Protocol)` and `open_async_enhanced_serial_adapter(*, port: str, segment_id: int, baudrate: int = 115200, hello_timeout_s: float = 1.0, event_queue_capacity: int = 256, open_connection: OpenSerialConnection | None = None) -> AsyncEnhancedSerialAdapter`.
- Preserves: no import or call from `apps/service`, `DeviceCoreRuntime`, current reconnect code, or the synchronous production factory.

- [ ] **Step 1: Extend stream fakes for transport ownership and startup**

Add a fake transport and a writer that fails if command data uses the stream API:

```python
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


HELLO_FRAME = (
    b'{"type":"hello","v":1,"firmware":"0.1.0",'
    b'"device":"dutchmate-rp2040","capabilities":["uart_receive"]}\n'
)
```

- [ ] **Step 2: Add RED tests for success, same-resource writes, and open arguments**

Add a fake opener that records keyword arguments, feed `HELLO_FRAME`, open the
adapter, then send one request. Use `asyncio.to_thread(serial.written.wait)` for
a `threading.Event` set by the fake serial's `write()` before feeding the command
response. Assert:

```python
assert open_calls == [
    {
        "url": "/dev/ttyACM0",
        "baudrate": 115200,
        "limit": 65536,
    }
]
assert adapter.info == BackendInfo(
    mode="enhanced",
    port="/dev/ttyACM0",
    device="dutchmate-rp2040",
    firmware="0.1.0",
    capabilities=frozenset({"uart_receive"}),
)
assert stream_writer.transport.extra_info_names == ["serial"]
assert stream_writer.stream_write_calls == []
assert serial.writes == [b'{"cmd":"test"}\n']
```

The response assertion is `CommandSuccessMessage(timestamp_us=8)`, and repeated
`await adapter.close()` calls leave `stream_writer.close_count == 1`.

- [ ] **Step 3: Add RED failure-cleanup tests**

Add these concrete tests (use `/dev/ttyACM0`, segment `0`, and a `0.01` hello
timeout consistently):

```python
async def test_open_failure_is_preserved_before_any_stream_exists() -> None:
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
```

Run:

```bash
../../.venv/bin/pytest tests/unit/backends/test_enhanced_serial_io.py -v
```

Expected: the new factory tests fail because the production entry point does not
exist.

- [ ] **Step 4: Implement the opener protocol, lazy library lookup, cleanup, and factory**

Extend `enhanced_serial_io.py` with the stream transport attribute, opener
protocol, and public entry point. Use this structure:

```python
import importlib
from collections.abc import Awaitable
from typing import cast

from dutchmate_core.backends.enhanced_serial import (
    DEFAULT_ENHANCED_EVENT_QUEUE_CAPACITY,
    AsyncEnhancedSerialAdapter,
)
from dutchmate_core.device_connection.serial_transport import DEFAULT_BAUDRATE
from dutchmate_core.device_connection.stream import MAX_DEVICE_FRAME_BYTES

DEFAULT_ASYNC_HELLO_TIMEOUT_SECONDS = 1.0


class _StreamTransport(Protocol):
    def get_extra_info(self, name: str, default: object | None = None) -> object | None:
        """Return transport-owned connection information."""


class _StreamWriter(Protocol):
    transport: _StreamTransport

    def close(self) -> None:
        """Begin closing the stream transport."""

    async def wait_closed(self) -> None:
        """Wait until the stream transport is closed."""


class OpenSerialConnection(Protocol):
    def __call__(
        self,
        *,
        url: str,
        baudrate: int,
        limit: int,
    ) -> Awaitable[tuple[_StreamReader, _StreamWriter]]:
        """Open one pyserial-asyncio stream pair."""


def _serial_asyncio_opener() -> OpenSerialConnection:
    module = importlib.import_module("serial_asyncio")
    return cast(OpenSerialConnection, module.open_serial_connection)


async def _close_without_masking_primary(reader: _OwnedStreamReader) -> None:
    close_task = asyncio.create_task(reader.close())
    while True:
        try:
            await asyncio.shield(close_task)
            return
        except asyncio.CancelledError:
            if close_task.done():
                return
        except Exception:
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
    opener = open_connection or _serial_asyncio_opener()
    stream_reader, stream_writer = await opener(
        url=port,
        baudrate=baudrate,
        limit=MAX_DEVICE_FRAME_BYTES,
    )
    owned_reader = _OwnedStreamReader(stream_reader, stream_writer)
    try:
        serial_resource = stream_writer.transport.get_extra_info("serial")
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
        await _close_without_masking_primary(owned_reader)
        raise
```

Remove unused imports after implementation. Do not export the private wrappers
from `dutchmate_core.backends.__init__`; the production factory is the intended
entry point.

- [ ] **Step 5: Run factory GREEN and complete focused regression coverage**

Run:

```bash
../../.venv/bin/pytest tests/unit/backends/test_enhanced_serial_io.py -v
../../.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py tests/unit/protocol/test_serial_transport.py tests/architecture/test_dependencies.py -v
```

Expected: all selected tests pass; no warning reports a leaked task, future, or
coroutine.

- [ ] **Step 6: Run the full slice validation gate**

Run:

```bash
../../.venv/bin/ruff check .
../../.venv/bin/mypy
../../.venv/bin/pytest
git diff --check
```

Expected: Ruff and mypy exit zero, all tests pass, and the diff check is silent.

- [ ] **Step 7: Refresh Graphify and verify the new dependency path**

Run:

```bash
graphify update .
graphify path "open_async_enhanced_serial_adapter" "AsyncEnhancedSerialAdapter" --undirected
graphify path "open_async_enhanced_serial_adapter" "write_serial_frame" --undirected
```

Expected: both paths exist in the refreshed graph. Record node/edge counts and
all Graphify warnings. Leave every `graphify-out/` change unstaged.

- [ ] **Step 8: Update authoritative status and commit the completed code slice**

Update `docs/development_status.md` in the same commit as the source and tests:

- use `Code baseline reviewed: pending current async serial I/O commit on
  2026-08-28`;
- state that the production-capable reader/writer factory is complete but
  service startup still selects the synchronous compatibility path;
- split Phase 1 queue step 4 so the real factory is checked and service selection
  remains unchecked;
- make the sole next step the async semantic control/UART consumer and service
  lifecycle design/migration;
- record the exact focused and full test counts printed in Steps 5-6; and
- retain Phase 1B as partial and all real-hardware gates as incomplete.

Then commit only source, tests, and status:

```bash
git add core/src/dutchmate_core/backends/enhanced_serial_io.py core/src/dutchmate_core/device_connection/serial_transport.py tests/unit/backends/test_enhanced_serial_io.py tests/unit/protocol/test_serial_transport.py docs/development_status.md
git diff --cached --check
git commit -m "Open production Enhanced async serial I/O"
```

Record the resulting commit hash for Task 4.

---

### Task 4: Reconcile The Exact Code Baseline

**Files:**
- Modify: `docs/development_status.md:1-75`

**Interfaces:**
- Consumes: the exact Task 3 code/test/status commit hash and its fresh validation evidence.
- Produces: one docs-only reconciliation commit whose `Code baseline reviewed` points to the exact Task 3 commit.
- Preserves: the sole next step, Phase 1B partial status, and all validation counts from Task 3.

- [ ] **Step 1: Replace only the pending baseline marker**

Run `git rev-parse --short HEAD` while Task 3 is still `HEAD`. Change:

```markdown
> Code baseline reviewed: pending current async serial I/O commit on 2026-08-28
```

Replace the words `pending current async serial I/O commit` with the literal
seven-character stdout printed by `git rev-parse --short HEAD`, retaining the
date and the surrounding backticks. Do not point the status baseline at the
later docs-only commit.

- [ ] **Step 2: Verify the status has one current target and no stale evidence**

Run:

```bash
rg -n "Code baseline reviewed|Current milestone|Next step|pyserial-asyncio|synchronous compatibility|Latest Validation|pending current" docs/development_status.md
git diff --check
```

Expected: exactly one baseline line names the Task 3 hash, no pending marker
remains, and the next step is still semantic async consumers plus service
lifecycle ownership.

- [ ] **Step 3: Commit the docs-only reconciliation**

```bash
git add docs/development_status.md
git diff --cached --check
git diff --cached --name-only
git commit -m "Reconcile async serial I/O status"
```

Expected: `git diff --cached --name-only` lists only
`docs/development_status.md` before the commit.

- [ ] **Step 4: Run final branch-state verification**

Run:

```bash
../../.venv/bin/ruff check .
../../.venv/bin/mypy
../../.venv/bin/pytest
git diff --check
git status --short
git log --oneline -6
```

Expected: all validation commands exit zero; only generated Graphify artifacts
may remain dirty; the latest two feature commits are the code slice and its
docs-only baseline reconciliation.
