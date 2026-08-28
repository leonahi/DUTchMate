# Enhanced Async Service Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Select the single-reader asynchronous Enhanced adapter in production service startup while preserving the synchronous runtime/API surface, finite-workflow reconnect behavior, and deterministic shutdown.

**Architecture:** Add async Enhanced semantic consumers in core, then place one synchronous bridge around one adapter and one dedicated asyncio loop in the service adapter layer. Initial Enhanced startup uses that host atomically for control, UART send, and finite capture; the existing synchronous reconnect path remains transitional and can open only after the async host closes.

**Tech Stack:** Python 3.10+, asyncio, threads, `pyserial-asyncio>=0.6`, FastAPI lifespan, pytest/pytest-asyncio, Ruff, mypy, Graphify

**Spec:** `docs/superpowers/specs/2026-08-28-enhanced-async-service-integration-design.md`

## Global Constraints

- Preserve the synchronous `DeviceCoreRuntime`, workflow, FastAPI endpoint, CLI, MCP, configuration, and session-evidence contracts.
- Initial production Enhanced startup must use `open_async_enhanced_serial_adapter()` and must not open `SerialCommandTransport` beside it.
- One selected Enhanced connection has exactly one serial resource, one physical reader, one parser, and one FIFO event queue.
- Keep asyncio loop/thread ownership in `apps/service`; core policy must not import service, FastAPI, thread, pyserial, or MCP details.
- Use the existing `AsyncCommandTransport` boundary; do not add an interface solely for symmetry.
- Preserve the one-second Enhanced command timeout and the 0.1-second finite-workflow event polling cadence; add no configuration surface.
- Preserve exact command bytes, response timestamps, error classifications/details, UART accepted-byte rules, and the 2,048-byte host frame limit.
- Preserve the adapter's 65,536-byte device frame limit, bounded FIFO backpressure, valid-event draining, and terminal-error ordering.
- The existing synchronous reconnect path remains available only after the failed async host has fully closed; do not migrate always-on ingestion or reconnect opening in this plan.
- The Basic and disconnected startup paths remain behaviorally unchanged.
- Internally constructed runtimes are app-owned and close in FastAPI lifespan; injected runtimes remain caller-owned.
- Structural changes require Ruff, mypy, full pytest, `git diff --check`, `graphify update .`, canonical Graphify artifacts, and a same-slice `docs/development_status.md` update.

## File Responsibility Map

- `core/src/dutchmate_core/backends/enhanced.py`: synchronous and asynchronous Enhanced semantic adapters plus shared pure response interpretation.
- `tests/unit/backends/test_enhanced.py`: sync/async semantic parity and exact public error behavior.
- `core/src/dutchmate_core/backends/enhanced_serial.py`: sole-reader adapter FIFO discard operation used by wait-pattern cursor advancement.
- `tests/unit/backends/test_enhanced_serial.py`: atomic queued-event discard behavior without reader duplication.
- `apps/service/src/dutchmate_service/enhanced_async.py`: one Enhanced adapter, event-loop thread, synchronous facades, state snapshots, and deterministic lifecycle.
- `apps/service/tests/test_enhanced_async.py`: bridge concurrency, projection, failure, and shutdown tests.
- `apps/service/src/dutchmate_service/startup.py`: initial async Enhanced composition and transitional reconnect wiring.
- `apps/service/src/dutchmate_service/backend_reconnect.py`: generalize the current-source annotation and retain ordered close-before-sync-reopen behavior.
- `apps/service/tests/test_startup_config.py`: async Enhanced startup, semantic use, capture use, and reconnect ordering integration.
- `core/src/dutchmate_core/runtime.py`: backend-neutral idempotent runtime close.
- `tests/unit/runtime/test_device_core_lifecycle.py`: runtime source ownership and replacement closure.
- `apps/service/src/dutchmate_service/app.py`: FastAPI lifespan ownership for internally built runtimes.
- `apps/service/tests/test_app_lifecycle.py`: internal versus injected runtime closure and construction cleanup.
- `docs/development_status.md`: sole progress tracker, validation evidence, and next Phase 1 item.
- `graphify-out/`: canonical structural graph outputs updated after all source changes.

---

### Task 1: Add Async Enhanced Semantic Consumers

**Files:**
- Modify: `core/src/dutchmate_core/backends/enhanced.py:1-150`
- Modify: `tests/unit/backends/test_enhanced.py:1-125`

**Interfaces:**
- Consumes: `AsyncCommandTransport.request(command: bytes, timeout_s: float) -> DeviceMessage` from `dutchmate_core.device_connection.transport`.
- Produces: `DEFAULT_ENHANCED_COMMAND_TIMEOUT_S = 1.0`; `AsyncEnhancedDeviceControl(transport: AsyncCommandTransport, *, timeout_s: float = 1.0)`; `AsyncEnhancedUartSender(transport: AsyncCommandTransport, *, timeout_s: float = 1.0)`.
- Preserves: `EnhancedDeviceControl`, `EnhancedUartSender`, their method signatures, command bytes, returned values, and public exceptions.

- [ ] **Step 1: Add the fake async transport and failing success-path parity tests**

Extend `tests/unit/backends/test_enhanced.py` with:

```python
class FakeAsyncCommandTransport:
    def __init__(self, response: DeviceMessage | Exception) -> None:
        self.response = response
        self.requests: list[tuple[bytes, float]] = []

    async def request(self, command: bytes, timeout_s: float) -> DeviceMessage:
        self.requests.append((command, timeout_s))
        if isinstance(self.response, Exception):
            raise self.response
        return self.response


async def test_async_enhanced_control_uses_same_command_and_timestamp() -> None:
    transport = FakeAsyncCommandTransport(CommandSuccessMessage(timestamp_us=123))

    timestamp = await AsyncEnhancedDeviceControl(transport).pulse_control(
        channel="CTRL0",
        pulse_ms=100,
    )

    assert timestamp == 123
    assert transport.requests == [
        (b'{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}\n', 1.0)
    ]


async def test_async_enhanced_uart_sender_uses_same_acknowledgement_rules() -> None:
    transport = FakeAsyncCommandTransport(
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=3)
    )

    result = await AsyncEnhancedUartSender(transport).send_uart(b"go\n")

    assert result == BackendUartSendResult(
        bytes_accepted=3,
        device_timestamp_us=500,
    )
    assert transport.requests == [(b'{"cmd":"uart_send","data_b64":"Z28K"}\n', 1.0)]
```

- [ ] **Step 2: Run the new tests and capture RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced.py -k "async_enhanced" -v
```

Expected: collection fails because `AsyncEnhancedDeviceControl` and
`AsyncEnhancedUartSender` do not exist.

- [ ] **Step 3: Extract shared response helpers and implement the async consumers**

In `enhanced.py`, import `AsyncCommandTransport`, retain the synchronous
transport, and add the exact public shapes:

```python
DEFAULT_ENHANCED_COMMAND_TIMEOUT_S = 1.0


class AsyncEnhancedDeviceControl:
    def __init__(
        self,
        transport: AsyncCommandTransport,
        *,
        timeout_s: float = DEFAULT_ENHANCED_COMMAND_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._timeout_s = timeout_s

    async def configure_gpio_mode(
        self,
        *,
        channel: str,
        mode: str,
        active_level: str,
        idle_level: str | None,
    ) -> int | None:
        command = configure_gpio_mode_command(
            channel=channel,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
        )
        return await self._request_success(
            command.to_ndjson(),
            operation="configure_gpio_mode",
            response_label="GPIO mode configuration",
        )

    async def pulse_control(self, *, channel: str, pulse_ms: int) -> int | None:
        command = pulse_control_command(channel=channel, pulse_ms=pulse_ms)
        return await self._request_success(command.to_ndjson(), operation="reset")

    async def set_control_state(
        self,
        *,
        channel: str,
        state: ControlState,
    ) -> int | None:
        command = set_control_state_command(channel=channel, state=state)
        return await self._request_success(
            command.to_ndjson(),
            operation="set_boot_mode",
        )

    async def _request_success(
        self,
        command: bytes,
        *,
        operation: str,
        response_label: str | None = None,
    ) -> int | None:
        label = response_label or operation
        try:
            response = await self._transport.request(command, self._timeout_s)
        except TransportWriteError as exc:
            raise DeviceControlError(error=exc.error, detail=str(exc)) from exc
        except TransportTimeoutError as exc:
            raise DeviceControlError(
                error="timeout",
                detail=f"Timed out waiting for {label} response",
            ) from exc
        except HostCommandFrameTooLargeError:
            raise
        except ProtocolError as exc:
            raise backend_input_error_from_protocol(exc, operation=operation) from exc
        return _control_success_timestamp(response, label=label)


class AsyncEnhancedUartSender:
    def __init__(
        self,
        transport: AsyncCommandTransport,
        *,
        timeout_s: float = DEFAULT_ENHANCED_COMMAND_TIMEOUT_S,
    ) -> None:
        self._transport = transport
        self._timeout_s = timeout_s

    async def send_uart(self, data: bytes) -> BackendUartSendResult:
        command = uart_send_command(data)
        try:
            response = await self._transport.request(
                command.to_ndjson(),
                self._timeout_s,
            )
        except TransportWriteError as exc:
            raise BackendWriteError(
                str(exc),
                bytes_accepted=None,
                error=exc.error,
            ) from exc
        except TransportTimeoutError as exc:
            raise BackendWriteError(
                "Enhanced UART send timed out",
                bytes_accepted=None,
                error="timeout",
            ) from exc
        except HostCommandFrameTooLargeError:
            raise
        except ProtocolError as exc:
            raise backend_input_error_from_protocol(exc, operation="uart_send") from exc
        except BackendInputError:
            raise
        except Exception as exc:
            raise BackendWriteError(
                "Enhanced UART send transport failed",
                bytes_accepted=None,
            ) from exc
        return _uart_send_result(response, expected_bytes=len(data))
```

Move the current response branches into
`_control_success_timestamp(response: DeviceMessage, *, label: str) -> int | None`
and `_uart_send_result(response: DeviceMessage, *, expected_bytes: int) -> BackendUartSendResult`.
Keep the exact existing error strings in those helpers and make the synchronous
classes call the same helpers after their current transport exception mapping.

- [ ] **Step 4: Add failing parity cases for every response/error boundary**

Parameterize both adapters over these exact outcomes:

```python
@pytest.mark.parametrize(
    "response",
    [
        CommandErrorMessage(error="hardware_fault", detail="firmware busy"),
        CommandSuccessMessage(timestamp_us=None, bytes_accepted=3),
        CommandSuccessMessage(timestamp_us=500, bytes_accepted=2),
        HelloMessage(
            firmware="0.1.0",
            device="dutchmate-rp2040",
            capabilities=("uart_send",),
        ),
    ],
)
async def test_async_uart_sender_matches_sync_rejections(response: DeviceMessage) -> None:
    with pytest.raises(BackendWriteError) as async_error:
        await AsyncEnhancedUartSender(FakeAsyncCommandTransport(response)).send_uart(b"go\n")
    with pytest.raises(BackendWriteError) as sync_error:
        EnhancedUartSender(FakeCommandTransport(response)).send_uart(b"go\n")
    assert (async_error.value.error, str(async_error.value)) == (
        sync_error.value.error,
        str(sync_error.value),
    )
```

Add equivalent control parity for `CommandErrorMessage`, unexpected response,
`TransportTimeoutError`, `TransportWriteError`, and `ProtocolError` subclasses
already exercised by the synchronous tests. Assert exact error code, detail,
timestamp, and command bytes—not only exception type.

- [ ] **Step 5: Run semantic tests for GREEN**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced.py -v
```

Expected: every existing synchronous test and every new async parity test
passes.

- [ ] **Step 6: Run focused static checks**

Run:

```bash
.venv/bin/ruff check core/src/dutchmate_core/backends/enhanced.py tests/unit/backends/test_enhanced.py
.venv/bin/mypy core/src/dutchmate_core/backends/enhanced.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 7: Commit the semantic boundary**

```bash
git add core/src/dutchmate_core/backends/enhanced.py tests/unit/backends/test_enhanced.py
git commit -m "Add async Enhanced semantic adapters"
```

---

### Task 2: Add Atomic Adapter FIFO Discard

**Files:**
- Modify: `core/src/dutchmate_core/backends/enhanced_serial.py:360-410`
- Modify: `tests/unit/backends/test_enhanced_serial.py`

**Interfaces:**
- Consumes: the adapter-owned `asyncio.Queue[BackendEvent]` populated by the sole reader.
- Produces: `AsyncEnhancedSerialAdapter.discard_pending_events() -> None`, an async owner-loop operation that removes only events already admitted when it begins.
- Preserves: `receive_event()` FIFO, terminal-error, bounded backpressure, and shutdown semantics.

- [ ] **Step 1: Add a failing same-batch discard test**

```python
async def test_discard_pending_events_advances_only_the_adapter_fifo() -> None:
    reader = FakeAsyncSerialReader()
    adapter = make_adapter(reader)
    reader.feed(HELLO_FRAME + UART_FRAME + UART_FRAME.replace(b'"timestamp_us":1', b'"timestamp_us":2'))

    await adapter.start(0.5)
    await reader.next_chunk_requested.wait()
    await adapter.discard_pending_events()

    assert await adapter.receive_event(timeout_s=0) is None
    assert reader.maximum_concurrent_reads == 1
    await adapter.close()
```

- [ ] **Step 2: Run the test and capture RED**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py::test_discard_pending_events_advances_only_the_adapter_fifo -v
```

Expected: FAIL because `discard_pending_events()` does not exist.

- [ ] **Step 3: Implement owner-loop queue draining without an await point**

Add beside `receive_event()`:

```python
async def discard_pending_events(self) -> None:
    """Discard events already admitted before a new workflow cursor begins."""

    while not self._events.empty():
        self._events.get_nowait()
```

The method intentionally contains no `await`: one event-loop turn drains the
current queue atomically relative to the reader task. It does not clear parser
state, command responses, terminal errors, or later events.

- [ ] **Step 4: Add terminal-state regression coverage**

Feed hello plus one event, then a terminal read failure. After discarding the
event, assert the next `receive_event()` raises the retained
`BackendDisconnectedError`; discard must never turn a terminal failure into an
ordinary timeout.

- [ ] **Step 5: Run the complete adapter suite and static checks**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced_serial.py -v
.venv/bin/ruff check core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
.venv/bin/mypy core/src/dutchmate_core/backends/enhanced_serial.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 6: Commit FIFO cursor support**

```bash
git add core/src/dutchmate_core/backends/enhanced_serial.py tests/unit/backends/test_enhanced_serial.py
git commit -m "Add async Enhanced FIFO discard"
```

---

### Task 3: Implement The Service-Owned Enhanced Async Host

**Files:**
- Create: `apps/service/src/dutchmate_service/enhanced_async.py`
- Create: `apps/service/tests/test_enhanced_async.py`

**Interfaces:**
- Consumes: `AsyncEnhancedSerialAdapter`, `AsyncEnhancedDeviceControl`, `AsyncEnhancedUartSender`, and `open_async_enhanced_serial_adapter(*, port, segment_id, baudrate) -> AsyncEnhancedSerialAdapter`.
- Produces: `EnhancedAsyncHost`; `open_enhanced_async_host(*, port: str, baudrate: int, segment_id: int, open_adapter: OpenAsyncEnhancedAdapter = open_async_enhanced_serial_adapter) -> EnhancedAsyncHost`.
- Implements synchronously: `DeviceControl`, `UartSender`, and the current `CaptureEventSource` shape (`read_event`, `discard_pending_events`, `segment`, `close`).

- [ ] **Step 1: Create deterministic fake adapter/factory scaffolding and a failing open/projection test**

In the new test file, define a fake async transport with immutable `info`,
`segment_id`, mutable `segment`, scripted `request()`/`receive_event()`,
`discard_pending_events()`, and counted `close()`. Record
`threading.get_ident()` in every async method.

```python
def test_host_opens_on_owner_loop_and_projects_identity() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0)

    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    assert host.info == _info()
    assert host.segment_id == 0
    assert host.owner_thread_id == fake.open_thread_id
    assert host.owner_thread_id != threading.get_ident()
    host.close()
```

Expose `owner_thread_id` only if needed by tests; otherwise have the fake and
opener record IDs and compare them directly.

- [ ] **Step 2: Run the new host test and capture RED**

Run:

```bash
.venv/bin/pytest apps/service/tests/test_enhanced_async.py::test_host_opens_on_owner_loop_and_projects_identity -v
```

Expected: collection fails because `dutchmate_service.enhanced_async` does not
exist.

- [ ] **Step 3: Implement loop startup, factory opening, and safe submission**

Create the module with these exact public signatures:

- `open_enhanced_async_host(*, port: str, baudrate: int, segment_id: int, open_adapter: OpenAsyncEnhancedAdapter = open_async_enhanced_serial_adapter) -> EnhancedAsyncHost`
- `EnhancedAsyncHost.info -> BackendInfo`
- `EnhancedAsyncHost.segment_id -> int`
- `EnhancedAsyncHost.segment -> SegmentContext | None`
- `EnhancedAsyncHost.configure_gpio_mode(*, channel: str, mode: str, active_level: str, idle_level: str | None) -> int | None`
- `EnhancedAsyncHost.pulse_control(*, channel: str, pulse_ms: int) -> int | None`
- `EnhancedAsyncHost.set_control_state(*, channel: str, state: ControlState) -> int | None`
- `EnhancedAsyncHost.send_uart(data: bytes) -> BackendUartSendResult`
- `EnhancedAsyncHost.read_event() -> BackendEvent | None`
- `EnhancedAsyncHost.discard_pending_events() -> None`
- `EnhancedAsyncHost.close() -> None`

Define a private `_AsyncEnhancedAdapter` protocol containing the exact
`AsyncCommandTransport` request method, the three identity/segment properties,
`receive_event(timeout_s)`, `discard_pending_events()`, and `close()`. Define
`OpenAsyncEnhancedAdapter` as a callable returning
`Coroutine[Any, Any, _AsyncEnhancedAdapter]`. This seam exists for deterministic
service lifecycle tests; production still returns the concrete
`AsyncEnhancedSerialAdapter`.

Use this generic internal submission boundary:

```python
DEFAULT_ENHANCED_EVENT_POLL_TIMEOUT_S = 0.1
T = TypeVar("T")


class EnhancedAsyncHost:
    def _submit(self, operation: Callable[[], Coroutine[Any, Any, T]]) -> T:
        with self._state_lock:
            if self._closing or self._closed:
                raise RuntimeError("Enhanced async host is closed")
            loop = self._loop
        future = asyncio.run_coroutine_threadsafe(operation(), loop)
        return future.result()
```

Back the shown fields with a lock-protected state machine. The loop thread
creates and installs its event loop, signals readiness, runs forever, and closes
the loop only after `run_forever()` exits. `_submit()` checks the open state
before creating the coroutine and returns `future.result()` so original
operation exceptions propagate.

`open_enhanced_async_host()` starts the loop, submits the injected factory,
caches `BackendInfo` and segment ID, constructs the async semantic consumers on
the loop, and returns only a ready host. Any open/construction failure stops and
joins the loop thread before re-raising the primary failure.

- [ ] **Step 4: Add failing semantic and event-facade tests**

Add tests proving:

```python
def test_control_send_and_capture_share_one_adapter_and_owner_loop() -> None:
    event = UartReceiveEvent(segment_id=0, timestamp_us=0, channel=0, data=b"boot\n")
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        request_outcomes=[
            CommandSuccessMessage(timestamp_us=10),
            CommandSuccessMessage(timestamp_us=20, bytes_accepted=3),
        ],
        event_outcomes=[event],
    )
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    assert host.pulse_control(channel="CTRL0", pulse_ms=100) == 10
    assert host.send_uart(b"go\n").device_timestamp_us == 20
    assert host.read_event() == event
    assert set(fake.operation_thread_ids) == {opener.thread_id}
    host.close()


def test_event_delivery_updates_a_thread_safe_segment_snapshot() -> None:
    segment = _segment(segment_id=0, source_origin_us=1_000)
    fake = FakeAsyncEnhancedAdapter(
        info=_info(),
        segment_id=0,
        event_outcomes=[
            UartReceiveEvent(segment_id=0, timestamp_us=0, channel=0, data=b"X")
        ],
        segment_after_receive=segment,
    )
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=OpenAdapterFake(fake),
    )

    assert host.segment is None
    assert host.read_event() is not None
    assert host.segment == segment
    host.close()


def test_discard_is_submitted_to_the_adapter_owner_loop() -> None:
    fake = FakeAsyncEnhancedAdapter(info=_info(), segment_id=0)
    opener = OpenAdapterFake(fake)
    host = open_enhanced_async_host(
        port="/dev/ttyACM0",
        baudrate=460800,
        segment_id=0,
        open_adapter=opener,
    )

    host.discard_pending_events()

    assert fake.discard_count == 1
    assert fake.discard_thread_id == opener.thread_id
    host.close()
```

Implement facade methods with the Task 1 async consumers. Implement event
receive through a private coroutine returning `(event, adapter.segment)` and
update the host's lock-protected segment snapshot after the submitted operation
returns. Never read mutable adapter state from the caller thread.

- [ ] **Step 5: Add a concurrent receive-and-command progress test**

Start `host.read_event()` in one worker thread while the fake receive coroutine
waits on an `asyncio.Event`. Call `host.pulse_control()` from the test thread and
assert its request completes before releasing the event. Then release the event,
join the worker, and assert both adapter operations ran on the same owner loop.
This proves a capture wait does not block command dispatch.

- [ ] **Step 6: Add failure and deterministic-close tests**

Cover all of these exact cases:

- factory failure stops and joins the thread and re-raises the same exception;
- `read_event()` returns `None` only for the fake's ordinary timeout;
- command and receive exceptions cross the bridge unchanged;
- `close()` sets closing before terminalizing the adapter;
- a blocked receive wakes when adapter close runs;
- two concurrent `close()` calls share one adapter close and both return only
  after cleanup;
- calls after close raise `RuntimeError("Enhanced async host is closed")`; and
- no host thread remains alive after close returns.

Implement concurrent close with one `threading.Event` completion barrier. The
first caller marks `_closing`, schedules `adapter.close()` directly on the loop
(bypassing `_submit()`), waits for it, requests `loop.stop()`, joins the owner
thread, marks `_closed`, and sets the barrier in a `finally` block. Later callers
that observe `_closing` wait on that same barrier and return the first caller's
retained cleanup outcome. Guard against running this synchronous method on the
owner thread before attempting `join()`; production closure must enter through
the service/runtime thread boundary.

- [ ] **Step 7: Run host tests and focused static checks**

Run:

```bash
.venv/bin/pytest apps/service/tests/test_enhanced_async.py -v
.venv/bin/ruff check apps/service/src/dutchmate_service/enhanced_async.py apps/service/tests/test_enhanced_async.py
.venv/bin/mypy apps/service/src/dutchmate_service/enhanced_async.py
git diff --check
```

Expected: all commands exit zero; tests never use sleeps for coordination.

- [ ] **Step 8: Commit the service host**

```bash
git add apps/service/src/dutchmate_service/enhanced_async.py apps/service/tests/test_enhanced_async.py
git commit -m "Add service-owned Enhanced async host"
```

---

### Task 4: Select The Async Host In Enhanced Startup

**Files:**
- Modify: `apps/service/src/dutchmate_service/startup.py:1-200`
- Modify: `apps/service/src/dutchmate_service/backend_reconnect.py:40-320`
- Modify: `apps/service/tests/test_startup_config.py`
- Modify: `apps/service/tests/test_backend_reconnect.py`

**Interfaces:**
- Consumes: `open_enhanced_async_host(*, port: str, baudrate: int, segment_id: int) -> EnhancedAsyncHost` from Task 3.
- Produces: initial Enhanced `DeviceCoreRuntime` composition using the same host as device control, UART sender, and capture source.
- Preserves: `build_startup_runtime(*, session_root: Path | str, session_evidence_budget_bytes: int, session_max_count: int | None, backend_settings: BackendSettings | None, monotonic_clock: Callable[[], float] | None, sleep: Callable[[float], None] | None) -> DeviceCoreRuntime`, synchronous Enhanced reconnect opening, and `read_enhanced_hello(SerialCommandTransport)` for that transitional path.

- [ ] **Step 1: Replace the initial Enhanced startup test with a failing async-host selection test**

Create a `FakeEnhancedAsyncHost` implementing the required sync facade and
scripted identity. Replace
`test_build_startup_runtime_with_serial_port_records_hello` with:

```python
def test_enhanced_startup_selects_one_async_host(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    host = FakeEnhancedAsyncHost(info=_enhanced_info(), segment_id=0)
    opened: list[tuple[str, int, int]] = []

    def fake_open_host(*, port: str, baudrate: int, segment_id: int) -> FakeEnhancedAsyncHost:
        opened.append((port, baudrate, segment_id))
        return host

    monkeypatch.setattr(startup, "open_enhanced_async_host", fake_open_host)
    monkeypatch.setattr(
        startup,
        "open_serial_command_transport",
        lambda **_kwargs: pytest.fail("initial Enhanced startup opened sync transport"),
    )

    runtime = build_startup_runtime(
        session_root=tmp_path,
        backend_settings=backend_settings(
            "enhanced",
            serial_port="/dev/ttyACM0",
            baudrate=460800,
        ),
    )

    assert opened == [("/dev/ttyACM0", 460800, 0)]
    assert runtime.status().connected is True
    assert runtime.status().device == "dutchmate-rp2040"
```

- [ ] **Step 2: Run the startup selection test and capture RED**

Run:

```bash
.venv/bin/pytest apps/service/tests/test_startup_config.py::test_enhanced_startup_selects_one_async_host -v
```

Expected: FAIL because startup still opens `SerialCommandTransport`.

- [ ] **Step 3: Rewire only the initial Enhanced branch**

In `startup.py`, replace initial transport/hello/source construction with:

```python
enhanced_host = open_enhanced_async_host(
    port=serial_port,
    baudrate=backend_settings.baudrate,
    segment_id=0,
)
try:
    info = enhanced_host.info
    control = ReplaceableDeviceControl(enhanced_host)
    sender = ReplaceableUartSender(enhanced_host)
    reconnect = build_enhanced_capture_reconnect(
        settings=backend_settings,
        current_source=enhanced_host,
        expected_info=info,
        control=control,
        sender=sender,
        open_transport=open_serial_command_transport,
        monotonic_clock=reconnect_clock,
        sleep=reconnect_sleep,
    )
    runtime = DeviceCoreRuntime(
        device_control=control,
        uart_sender=sender,
        message_source=enhanced_host,
        session_store=session_store,
        capture_clock=monotonic_clock,
        port=serial_port,
        backend_mode="enhanced",
        tx_policy_enabled=backend_settings.tx_enabled,
        reconnect_timeout_s=backend_settings.reconnect_timeout_s,
        backend_reconnect=reconnect,
    )
except BaseException:
    enhanced_host.close()
    raise
runtime.record_backend_connection(info)
return runtime
```

Keep `open_serial_command_transport` imported because the transitional reconnect
closure still uses it. Generalize `build_enhanced_capture_reconnect()`'s
`current_source` annotation from `EnhancedCaptureEventSource` to
`CaptureEventSource`; its behavior already depends only on that port.

- [ ] **Step 4: Migrate startup semantic/capture tests to the fake host**

Update the existing Enhanced startup tests that currently inject scripted
synchronous serial objects. Keep their endpoint/status assertions unchanged,
but script `FakeEnhancedAsyncHost` control, UART, and event outcomes. Explicitly
cover:

- startup hardware GPIO configuration reaches the host;
- UART send uses the host and retains error projection without input leakage;
- finite capture reads normalized events from the host; and
- malformed input closes the host and marks runtime disconnected.

Do not rewrite protocol-parser unit coverage here; it remains in core adapter
tests.

- [ ] **Step 5: Add a failing close-before-sync-reconnect ordering test**

Build an Enhanced runtime with a fake async host whose `read_event()` raises
`BackendDisconnectedError`. Have `host.close()` append `"async_closed"` to an
order list. Inject a synchronous reconnect opener that asserts the list is
exactly `["async_closed"]`, appends `"sync_opened"`, and returns the current
scripted replacement transport. Run a short finite capture and assert the order
is `["async_closed", "sync_opened"]` and the session resumes.

- [ ] **Step 6: Run startup, reconnect, and runtime integration tests**

Run:

```bash
.venv/bin/pytest apps/service/tests/test_startup_config.py apps/service/tests/test_backend_reconnect.py -v
.venv/bin/pytest tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_uart_send.py -v
```

Expected: all selected tests pass; initial Enhanced composition is async and
reconnect remains behaviorally unchanged.

- [ ] **Step 7: Run focused static checks**

Run:

```bash
.venv/bin/ruff check apps/service/src/dutchmate_service/startup.py apps/service/src/dutchmate_service/backend_reconnect.py apps/service/tests/test_startup_config.py apps/service/tests/test_backend_reconnect.py
.venv/bin/mypy apps/service/src/dutchmate_service/startup.py apps/service/src/dutchmate_service/backend_reconnect.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 8: Commit initial async selection**

```bash
git add apps/service/src/dutchmate_service/startup.py apps/service/src/dutchmate_service/backend_reconnect.py apps/service/tests/test_startup_config.py apps/service/tests/test_backend_reconnect.py
git commit -m "Select async Enhanced service host"
```

---

### Task 5: Add Runtime And FastAPI Lifecycle Ownership

**Files:**
- Modify: `core/src/dutchmate_core/runtime.py:187-270,840-855`
- Create: `tests/unit/runtime/test_device_core_lifecycle.py`
- Modify: `apps/service/src/dutchmate_service/app.py:1-165`
- Create: `apps/service/tests/test_app_lifecycle.py`

**Interfaces:**
- Consumes: the active capture source's optional synchronous `close()`.
- Produces: `DeviceCoreRuntime.close() -> None`; FastAPI lifespan closure for internally constructed runtimes.
- Preserves: injected-runtime ownership and all endpoint method signatures.

- [ ] **Step 1: Add failing idempotent runtime-close tests**

Create a minimal closable source and runtime using existing runtime test support:

```python
def test_runtime_close_closes_current_source_once(tmp_path: Path) -> None:
    source = ClosableEventSource()
    runtime = DeviceCoreRuntime(
        device_control=FakeDeviceControl(),
        message_source=source,
        session_store=SessionStore(root=tmp_path),
    )

    runtime.close()
    runtime.close()

    assert source.close_count == 1
```

Add a replacement-source case using the runtime's existing reconnect fixture:
after a successful replacement, `runtime.close()` must close the replacement,
not close the already closed original again.

- [ ] **Step 2: Run lifecycle unit tests and capture RED**

Run:

```bash
.venv/bin/pytest tests/unit/runtime/test_device_core_lifecycle.py -v
```

Expected: FAIL because `DeviceCoreRuntime.close()` does not exist.

- [ ] **Step 3: Implement backend-neutral idempotent runtime close**

Initialize `_closed = False`. Implement close so it captures and clears the
current source while holding `_operation_lock`, then closes outside the lock:

```python
def close(self) -> None:
    """Close the currently owned backend source exactly once."""

    with self._operation_lock:
        if self._closed:
            return
        self._closed = True
        source = self._message_source
        self._message_source = None
    if source is not None:
        self._close_event_source(source)
```

Do not import asyncio or service types into core.

- [ ] **Step 4: Add failing FastAPI ownership tests**

In `test_app_lifecycle.py`, define a full fake runtime by extending the existing
`FakeRuntime` with `close_count`. Add:

```python
def test_app_lifespan_closes_internally_constructed_runtime(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runtime = ClosableFakeRuntime(disconnected_status())
    monkeypatch.setattr(app_module, "build_startup_runtime", lambda **_kwargs: runtime)

    with TestClient(create_app()) as client:
        assert client.get("/status").status_code == 200
        assert runtime.close_count == 0

    assert runtime.close_count == 1


def test_app_lifespan_does_not_close_injected_runtime() -> None:
    runtime = ClosableFakeRuntime(disconnected_status())

    with TestClient(create_app(runtime)) as client:
        assert client.get("/status").status_code == 200

    assert runtime.close_count == 0
```

Add a third test: when startup hardware configuration raises unexpectedly after
an internal runtime is created, `create_app()` closes it once and re-raises that
same exception.

- [ ] **Step 5: Implement explicit FastAPI lifespan ownership**

Use `asyncio.to_thread` and `contextlib.asynccontextmanager`. Determine
`owns_runtime = runtime is None` before composition. Close only internally
owned runtimes:

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        yield
    finally:
        if owns_runtime:
            close = getattr(runtime_provider, "close", None)
            if callable(close):
                await asyncio.to_thread(close)


app = FastAPI(title="DUTchMate Device Core Service", lifespan=lifespan)
```

Wrap unexpected internal post-construction configuration failure in a local
`try`/`except BaseException` that closes `runtime_provider` before re-raising.
Do not add `close()` to `RuntimeProvider`; injected fakes are not required to be
closeable.

- [ ] **Step 6: Run lifecycle, endpoint, and static regression tests**

Run:

```bash
.venv/bin/pytest tests/unit/runtime/test_device_core_lifecycle.py apps/service/tests/test_app_lifecycle.py -v
.venv/bin/pytest apps/service/tests -v
.venv/bin/ruff check core/src/dutchmate_core/runtime.py apps/service/src/dutchmate_service/app.py tests/unit/runtime/test_device_core_lifecycle.py apps/service/tests/test_app_lifecycle.py
.venv/bin/mypy core/src/dutchmate_core/runtime.py apps/service/src/dutchmate_service/app.py
git diff --check
```

Expected: all commands exit zero.

- [ ] **Step 7: Commit lifecycle ownership**

```bash
git add core/src/dutchmate_core/runtime.py tests/unit/runtime/test_device_core_lifecycle.py apps/service/src/dutchmate_service/app.py apps/service/tests/test_app_lifecycle.py
git commit -m "Own service backend lifecycle"
```

---

### Task 6: Validate The Slice, Refresh Architecture, And Advance Status

**Files:**
- Modify: `docs/development_status.md`
- Modify after structural refresh: the eight canonical tracked files under `graphify-out/`

**Interfaces:**
- Consumes: all production and test interfaces from Tasks 1-5.
- Produces: a fully validated Phase 1 checklist slice and the next sole status item: service-owned continuous ingestion coordinator.
- Preserves: Phase 1 remains active and Phase 2/MCP work remains out of scope.

- [ ] **Step 1: Run the complete focused integration gate**

Run:

```bash
.venv/bin/pytest tests/unit/backends/test_enhanced.py tests/unit/backends/test_enhanced_serial.py apps/service/tests/test_enhanced_async.py apps/service/tests/test_startup_config.py apps/service/tests/test_backend_reconnect.py tests/unit/runtime/test_device_core_lifecycle.py apps/service/tests/test_app_lifecycle.py -v
```

Expected: all focused tests pass with no thread, task, or resource-leak warning.

- [ ] **Step 2: Run the repository-wide validation gate**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest
git diff --check
```

Expected: every command exits zero. Record the exact mypy source-file count and
pytest pass/skip counts printed by these commands for the status evidence.

- [ ] **Step 3: Verify the one-reader architecture in source and Graphify**

Run:

```bash
rg -n "open_async_enhanced_serial_adapter|open_serial_command_transport|read_message|receive_event" apps/service/src core/src/dutchmate_core/backends
graphify update .
graphify path "build_startup_runtime" "AsyncEnhancedSerialAdapter"
graphify path "EnhancedAsyncHost" "open_async_enhanced_serial_adapter"
```

Expected: initial Enhanced startup has a directed path to the async factory;
only the transitional reconnect closure references the synchronous Enhanced
opener; no service facade performs a physical read.

- [ ] **Step 4: Inspect and stage only canonical Graphify outputs**

The canonical tracked set is exactly:

```text
graphify-out/.graphify_labels.json
graphify-out/.graphify_labels.json.sig
graphify-out/.vocab.txt
graphify-out/GRAPH_REPORT.md
graphify-out/cost.json
graphify-out/graph.html
graphify-out/graph.json
graphify-out/manifest.json
```

Run `git status --short` and verify volatile cache, memory, reflection, dated
snapshot, and runtime-state files remain ignored. Do not stage any volatile
Graphify artifact.

- [ ] **Step 5: Update the sole development status**

Run `git log -1 --format=%h` and set `Code baseline reviewed` to that exact code
commit. In `docs/development_status.md`:

- mark the Enhanced semantic-consumer/lifecycle/startup-selection item complete;
- state that initial Enhanced startup now selects one async host/adapter while
  reconnect remains transitional and synchronous;
- set the sole next step to adding one service-owned continuous ingestion
  coordinator for the selected backend;
- retain Phase 1 as active and Phase 1B as partial; and
- add the exact Ruff, mypy, pytest, focused-test, Graphify, and `git diff --check`
  evidence from Steps 1-3.

Do not add progress summaries to the design, implementation plan, architecture,
or validation reference documents.

- [ ] **Step 6: Re-run final consistency checks**

Run:

```bash
.venv/bin/ruff check .
.venv/bin/mypy
.venv/bin/pytest
git diff --check
git status --short
```

Expected: validations remain green; status shows only the intended status file
and canonical Graphify changes.

- [ ] **Step 7: Commit the completed Phase 1 slice**

```bash
git add docs/development_status.md graphify-out/.graphify_labels.json graphify-out/.graphify_labels.json.sig graphify-out/.vocab.txt graphify-out/GRAPH_REPORT.md graphify-out/cost.json graphify-out/graph.html graphify-out/graph.json graphify-out/manifest.json
git commit -m "Complete Enhanced async service integration"
```

After the commit, reconcile `Code baseline reviewed` if the final commit contains
source changes not already represented by the recorded baseline; amend only the
status line and rerun `git diff --check` before considering the slice complete.
