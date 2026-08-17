# Phase 1 Implementation Spec

> Status: draft
> Scope: Basic generic USB-to-UART backend, Enhanced RP2040 Debug Helper backend, Device Core Service, host CLI, and shared protocol/session contracts.

## Goal

Prove that one backend-independent host pipeline supports both Phase 1 device
backends:

```text
Basic:    build -> flash externally -> manual reset -> receive UART -> store evidence -> detect failure
Enhanced: build -> flash externally -> controlled reset -> receive UART -> store evidence -> detect failure
```

Phase 1 is split into two ordered milestones:

- **Phase 1A, Basic backend:** receive UART through a user-selected generic
  USB-to-UART adapter, optionally send UART bytes, preserve raw evidence, and
  return structured sessions through the local CLI and Device Core Service.
- **Phase 1B, Enhanced backend:** use the RP2040 Debug Helper behind the same
  UART receive/session pipeline, add device timestamps and buffer telemetry,
  and run automated reset/boot-test workflows through user-configured `CTRLn`
  roles.

Phase 1 is complete only when both milestones pass their mocked and real-hardware
acceptance tests. Phase 1B must add capabilities and evidence quality without
introducing a second host processing architecture.

## Non-Goals

- MCP integration
- AI log summaries or LLM-based diagnosis
- MessagePack + COBS protocol encoding
- GUI
- Multi-DUT support
- Power/current/voltage sensing
- GPIO `EVENTn` capture implementation; the Enhanced backend owns the event
  interface, but `gpio_events` remains Phase 5
- Arbitrary GPIO control workflows beyond configured Phase 1 roles
- Hybrid operation that combines UART from a generic adapter with control or
  events from a separate Debug Helper
- JTAG/SWD debugging
- Firmware flashing

Phase 2 MCP integration is planned in `docs/mcp_integration_plan.md`. Phase 1
should keep the Device Core Service API stable enough for the later MCP stdio
adapter, but must not implement MCP before CLI workflows are validated. The
current `dutchmate mcp` CLI command and `dutchmate-mcp` console script are
placeholders only.

## Implementation Order

Phase 1 should be built host-side first with fake backends and protocol fixtures,
then connected to each real backend in milestone order.

### Phase 1A: Basic Backend

1. Define the normalized UART receive interface and backend capability model.
   **Implemented in `dutchmate_core.backends.contracts` with shared fake Basic
   and Enhanced source contract tests.**
2. Refactor the shared UART processing/session path to consume normalized UART
   events independent of backend framing. **Implemented for UART processing,
   capture recording, and legacy session evidence writes. Enhanced NDJSON and
   synchronous transport messages are translated at explicit compatibility
   adapters before entering the shared path.**
3. Implement explicit Basic-backend selection and serial settings without a
   DUTchMate `hello` requirement. **Implemented across shared config parsing,
   CLI/service startup, Enhanced candidate resolution, and raw Basic 8-N-1
   connection setup. Basic requires an explicit port; Enhanced may remain
   selected but disconnected when no candidate exists.**
4. Implement generic USB-to-UART receive using raw serial bytes and host
   timestamp provenance. Add UART send when TX is enabled. **Implemented for
   the Basic backend adapter: one lazy-started reader owns raw serial reads,
   publishes FIFO normalized chunks with host-monotonic provenance, and drains
   accepted evidence before disconnect errors. Capability-gated writes retry
   short writes to completion and report partial acceptance on failure. Public
   Device Core/service/CLI UART-send exposure remains step 6 work.**
5. Expose backend mode, capabilities, timestamp provenance, and the UART
   loss-observation object through status, sessions, service responses, and CLI output.
   **Implemented for current runtime status and capture-like sessions/responses:
   backend support is separated from TX-policy-filtered effective capabilities,
   per-segment provenance remains attached to its segment ID, Basic reports
   `not_observable`, and Enhanced telemetry promotes integrity to
   `loss_reported`. Status and capture/boot-test CLI output expose the same
   facts. Runtime capture/boot-test sessions with a complete backend snapshot
   now use native schema-v1 lifecycle metadata; bounded retrieval remains step
   6 work.**
6. Complete deterministic `first_error` selection plus shared log/session,
   wait-pattern, UART-send, reconnect, and retention work required by the Phase
   1 done criteria. **In progress: admitted complete lines now retain event/byte
   boundaries, detected records carry first-occurrence raw offsets and bounded
   exact-byte excerpts, and capture/boot-test summaries select and expose
   deterministic `first_error` while excluding `BOOT_OK`. Derived line state is
   now independently capped at 65536 bytes per segment/channel, with exact
   oversized descriptors, persistent status/counts, and recovery after LF.
   Native capture/boot-test sessions now publish `active` metadata with a
   terminal reserve and transition once to `completed` or bounded-error
   `failed`, while recognized unversioned sessions remain v0. Startup now
   abandons stale native active sessions before backend opening and reports
   reserve/schema diagnostics without mutating legacy or unsupported schemas.
   Quota enforcement, schema-v1 retrieval, wait-pattern, public UART send,
   reconnect, and retention remain.**
7. Pass mocked Basic-backend tests and a real generic-adapter + Zephyr DUT
   fixture smoke test as defined under "DUT Firmware Validation Fixture".
   **Not started.**

### Phase 1B: Enhanced Backend

8. Rename the legacy Debug Helper wire capability `uart_capture` to
   `uart_receive` atomically across schemas, examples, parser, tests, and future
   firmware. **Not started.**
9. Adapt the implemented Debug Helper NDJSON parser/transport to the same UART
   receive interface used by Phase 1A. **An interim synchronous adapter and
   fixture-stream adapter now normalize UART and telemetry messages. The target
   asynchronous background reader, complete framing limits, and segment-origin
   coordination remain.**
10. Preserve the existing channel-aware `CTRLn` configuration and guarded
    reset/boot workflows behind Enhanced-backend capability checks. Replace
    the legacy role-specific wire actions with generic configured-channel pulse
    and active/idle actions, and remove user role metadata from firmware
    commands. **Host-side workflow behavior is substantially implemented;
    wire-action/configuration migration is not started.**
11. Implement RP2040 firmware for UART receive/send, device timestamps, buffer
    telemetry, and `CTRLn` control. Start with the 32 KiB UART RX ring-buffer
    baseline and close its measurement gate as defined in
    `docs/ring_buffer_sizing_plan.md`. **Not started.**
12. Define the Enhanced backend as the sole future owner of `EVENTn` input, but
    defer the `gpio_events` implementation and HIL criteria to Phase 5.
13. Pass mocked Enhanced-backend tests and a real RP2040 + the same Zephyr DUT
    fixture smoke test for reset, boot-test, UART evidence, timestamps, and
    overflow telemetry. **Not started.**

### Existing Shared Host Foundation

The repository already contains:

- Backend-neutral identity, timestamp provenance, normalized UART/telemetry
  event, asynchronous event-source, disconnect, and invalid-input contracts.
- Explicit Basic/Enhanced startup selection, exact serial-port validation,
  backend-specific baudrate defaults, 8-N-1 validation, and raw Basic opening
  without a Debug Helper `hello` probe.
- Basic raw-byte ingestion through one FIFO reader, per-read host-monotonic
  timestamps, and a TX-policy-gated full-write primitive that reports partial
  acceptance on failure.
- Runtime/backend snapshots containing mode, exact identity, pre-policy backend
  capabilities, effective capabilities, policy source, per-segment timestamp
  provenance, and UART-loss integrity, serialized through status and current
  capture/boot-test responses and CLI output.
- Shared UART processing, capture recording, and session evidence writes that
  consume normalized events, plus interim Enhanced transport/NDJSON adapters.
- Channel-aware Debug Helper v1 schemas, canonical examples, parser, and event
  models using the legacy `uart_capture` capability name.
- UART byte preservation, lossy UTF-8 display text, complete-line buffering,
  and pattern detection.
- Session creation, incremental UART/event writes, telemetry, summaries,
  newest-first discovery, and latest-session lookup.
- Enhanced NDJSON adapter fixtures, finite transport capture, reset-triggered boot-test,
  active-session guards, reset/boot action enforcement, and synchronous serial
  command transport.
- Service endpoints and CLI commands for status, finite capture, boot-test,
  GPIO mode, reset, and boot-mode.

Native versioned log/session retrieval, wait-pattern, reconnect, public
UART-send workflows, lifecycle/retention semantics, RP2040 firmware, and both
HIL paths remain incomplete.

### Current Host-Side Core Flow

The Enhanced adapter fixture path is:

```text
NDJSON byte chunks
  -> device_connection.NdjsonStreamParser
  -> device_connection.parse_device_message
  -> backends.enhanced.EnhancedNdjsonEventStream
  -> normalized backend events
  -> test fixture composition
  -> workflows.CaptureRecorder
  -> uart_capture.UartCaptureProcessor
  -> log_processing.PatternDetector
  -> session_store.SessionStore
  -> session_store.SessionSummary
```

Enhanced-only byte-chunk composition is test support rather than a production
workflow API. Production capture accepts injected normalized event sources and
does not open a serial port.

The service-facing core path currently reaches the same recorder through one
of the selected backend adapters:

```text
Basic raw serial -> backends.basic.BasicBackendEventSource
Enhanced serial -> backends.enhanced.EnhancedCaptureEventSource
  -> normalized backend events
  -> runtime.DeviceCoreRuntime.capture_uart
  -> workflows.TransportCaptureRunner
  -> workflows.CaptureRecorder
  -> session_store.SessionStore
  -> session_store.SessionSummary
```

The runtime publishes `active_session_id` while this loop is running and
rejects overlapping GPIO, reset, boot-mode, or capture operations with
`capture_active`.

Both current paths are Debug Helper-oriented. The target shared flow is:

```text
Selected Device Backend (Basic or Enhanced)
  -> one background serial reader
  -> BackendEventSource FIFO
  -> normalized backend events
  -> uart_capture processing
  -> log_processing
  -> session_store
```

`receive` is the directional backend capability, paired with `uart_send`.
`capture` remains the higher-level workflow that records received evidence into
a session, and `uart_capture` remains the existing processing package name. The
target `BackendEventSource` is asynchronous and returns `UartReceiveEvent`,
`BufferOverflowEvent`, or `BufferStatusEvent`; it never returns Debug Helper
wire-protocol messages or command responses.

The normalized event and source types should live in a backend-neutral module,
targeted as `dutchmate_core.backends.contracts`. Basic and Enhanced adapters
implement that contract. Enhanced NDJSON schemas, parsing, and command encoding
remain in `device_connection`; they are implementation details of the Enhanced
adapter. Shared `uart_capture`, `workflows`, and `session_store` modules must
depend on normalized contracts rather than `device_connection.messages`.

## Normalized Backend Contract

The shared capture workflow consumes normalized backend events, never Enhanced
wire models such as `UartMessage`, `HelloMessage`, or command responses. The
target Python contract is:

```python
from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

BackendMode: TypeAlias = Literal["basic", "enhanced"]
BackendCapability: TypeAlias = Literal[
    "uart_receive",
    "uart_send",
    "gpio_control",
    "gpio_events",
    "device_timestamp",
    "overflow_telemetry",
    "power_sense",
    "msgpack",
]


@dataclass(frozen=True, slots=True)
class BackendInfo:
    mode: BackendMode
    port: str
    device: str | None
    firmware: str | None
    capabilities: frozenset[BackendCapability]


@dataclass(frozen=True, slots=True)
class SegmentTimestamp:
    source: Literal["host", "device"]
    clock: Literal["monotonic", "rp2040_timer"]
    unit: Literal["us"]
    origin: Literal["segment_start"]
    source_origin_us: int
    observation_point: str
    event_granularity: str


@dataclass(frozen=True, slots=True)
class SegmentContext:
    segment_id: int
    timestamp: SegmentTimestamp


@dataclass(frozen=True, slots=True)
class UartReceiveEvent:
    segment_id: int
    timestamp_us: int
    channel: int
    data: bytes


@dataclass(frozen=True, slots=True)
class BufferOverflowEvent:
    segment_id: int
    timestamp_us: int
    channel: int
    dropped_bytes: int


@dataclass(frozen=True, slots=True)
class BufferStatusEvent:
    segment_id: int
    timestamp_us: int
    size_bytes: int
    used_bytes: int
    high_water_bytes: int
    dropped_bytes_total: int
    overflow_events: int


BackendEvent: TypeAlias = (
    UartReceiveEvent | BufferOverflowEvent | BufferStatusEvent
)


class BackendDisconnectedError(RuntimeError): ...


class BackendInputError(RuntimeError): ...


class BackendEventSource(Protocol):
    @property
    def info(self) -> BackendInfo: ...

    @property
    def segment_id(self) -> int: ...

    @property
    def segment(self) -> SegmentContext | None: ...

    async def receive_event(self, timeout_s: float | None = None) -> BackendEvent | None:
        """Return the next FIFO event, or None when the read timeout expires."""
```

`BackendInfo` is the complete Phase 1 backend identity. `mode` is the fixed
`basic`/`enhanced` enum. `port` is the exact active serial-port string: its
UTF-8 encoding is 1..4096 bytes, it has no leading/trailing Unicode
`White_Space` and no Unicode `Cc` control characters, and no layer trims,
truncates, Unicode-normalizes, or otherwise rewrites it. Internal non-control
whitespace is permitted. A user-configured invalid port is rejected before the
backend is opened; an unusable discovered value cannot be selected.

For Basic mode, `device` and `firmware` are null because a generic adapter has
no DUTchMate `hello` identity. For Enhanced mode, they are the exact accepted
`hello.device` and `hello.firmware` strings and use the 1..64-byte UTF-8,
no-Unicode-`Cc`, no-edge-`White_Space` wire contract. USB descriptions and
hardware IDs are discovery data, not Phase 1 session identity.

The Device Core connection/session coordinator assigns session-local
`segment_id` values and creates a new `SegmentContext` for each connection or
reconnect. The adapter establishes `source_origin_us`, normalizes its source
clock to segment-relative `timestamp_us`, and attaches the current segment ID
before publishing an event. If the first event establishes the origin,
`segment` may initially be null but must be available before that event is
returned.

`receive_event()` returns null only for an ordinary read timeout.
`BackendDisconnectedError` and `BackendInputError` distinguish disconnect and
invalid backend input from inactivity.

Each source owns one FIFO event queue, and one background serial reader owns all
reads from the selected physical backend. Enhanced mode parses NDJSON, routes
command responses to pending requests, and queues UART and telemetry events
without discarding or reordering them while a command is in flight. Basic mode
converts each delivered raw serial chunk directly to one `UartReceiveEvent`.

`UartReceiveEvent.data` is authoritative raw evidence. Display text and complete
lines are derived downstream. Timestamp provenance belongs to `SegmentContext`
rather than each event. JSON session files base64-encode data only at the
persistence boundary; `data_b64` is not an in-memory field.

This contract defines normalized evidence input, not the complete backend API.
UART send, control, and future GPIO event configuration are separate,
capability-gated interfaces owned by the same selected backend. Device Core
must not assemble them from different physical devices.

## Package Layout

```text
apps/
  cli/           Human-facing command-line client.
  service/       FastAPI Device Core Service; owns the serial port.
  mcp_server/    Phase 2 only.

core/
  src/dutchmate_core/
    backends/            Target backend-neutral contracts plus Basic/Enhanced adapters.
    device_connection/   Enhanced wire protocol parsing, commands, NDJSON framing, and serial primitives.
    uart_capture/        Backend-independent UART event processing and line buffering.
    gpio_config/         Debug Helper GPIO mode configuration workflow/state.
    session_store/       Debug session persistence and summaries.
    log_processing/      Pattern detection on completed UART lines.
    workflows/           Mock capture recording plus guarded reset/boot actions.

hardware/
  firmware/      RP2040 firmware.
  protocol/      Versioned protocol schemas, examples, and fixtures.
  schematics/    Debug Helper hardware design files.

tests/
  unit/          Parser, line-buffering, pattern, and session tests.
  integration/   Device Core Service tests using mock serial streams.
  fixtures/      Pre-recorded protocol streams and expected outputs.
```

## Enhanced Backend Hardware Mapping Contract

`docs/dutchmate_hardware_architecture.md` owns the Revision A voltage-domain
design, Pico pin map, provisional BOM, and electrical validation checklist.
Firmware board configuration, schematic capture, and mapping tests must preserve
that baseline; a pin or component substitution is a reviewed hardware revision.

`docs/gpio_configuration_semantics.md` owns the exact host identifier,
electrical-mode, state-transition, workflow, validation-order, and reporting
contract. This spec depends on that contract rather than restating it.

Phase 1 integration requirements are:

- Enhanced exposes generic `CTRL0` through `CTRL3`; Basic exposes no control or
  event channels.
- Enhanced reserves `EVENT0` through `EVENT3` for Phase 5 and must not advertise
  `gpio_events` before that implementation passes HIL acceptance.
- Users map physical channels to exact host-side role and DUT-signal metadata.
  Reset and boot are roles, not dedicated MCU pins or firmware capabilities.
- Exact lowercase `reset` is required by reset and boot-test. Exact lowercase
  `boot` is required only by boot-mode; plain boot-test does not change boot
  state.
- Firmware receives physical channel and electrical behavior, never user role
  or DUT schematic names.
- Until a mapping is fully validated and accepted, startup, unconfigured,
  voltage-invalid, rejected-without-prior-state, and fault paths keep the
  channel high impedance. Accepted mappings enter their configured idle state.
- Phase 1 has no persistent disable/unconfigure operation.
- If firmware does not measure `DUT_VIO`, the service may treat configured
  `dut_io_voltage` as a trusted user declaration without weakening output
  safety behavior.

The user-provided `.dutchmate/config.toml` hardware mapping should use this
shape:

```toml
[hardware]
dut_io_voltage = 1.8

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"

[hardware.control.boot]
channel = "CTRL1"
dut_signal = "BOOT0"
mode = "push_pull"
active_level = "high"
idle_level = "low"
```

Current implementation status:

- Runtime state is already channel-first, startup applies configured mappings
  after Enhanced `hello`, and rejected overrides preserve accepted state.
- One shared validator now enforces and preserves the exact 1..64-byte UTF-8
  role/DUT-signal contract across config, runtime, service, and CLI paths.
- Host validators and the v1 command schema enforce the complete
  open-drain/push-pull matrix; suggestions use `power_enable` while legacy
  `power_en` remains a valid custom role.
- Current wire schemas and encoders still send role-specific actions and a
  configuration `role`. Phase 1B migrates them atomically to the generic control
  contract below while preserving semantic host APIs.

## Enhanced Backend Protocol Contract

The Debug Helper host-device protocol is NDJSON over USB CDC serial. Each line
is one JSON message. The v1 schemas live under `hardware/protocol/v1/`. This
protocol belongs only to the Enhanced backend. The Basic backend reads and
writes raw UART bytes through the host serial API and does not send a DUTchMate
`hello` or NDJSON messages.

Each wire frame is one UTF-8 JSON object plus LF. The total maximum, including
LF and an optional accepted CR before it, is 65536 bytes device-to-host and 2048
bytes host-to-device. Writers emit compact UTF-8 JSON without BOM, outer
whitespace, ASCII escaping of non-ASCII text, or CR; receivers may remove only
one CR immediately before LF. After that removal, the body begins with `{` and
ends with `}`.

The host enforces its receive bound before decoding and permits at most 65535
pending bytes without LF. Another non-LF byte fails immediately as
`frame_too_large`. Empty/BOM-prefixed frames, invalid UTF-8/JSON, non-object JSON,
unknown or schema-invalid messages, invalid base64, and out-of-range fields are
fatal backend input errors. Valid earlier frames from the same serial read are
published in FIFO order; the offending frame and all later bytes from that read
produce no normalized event. Device Core closes that Enhanced event source and
fails pending command waiters.

Host command encoders measure the complete serialized frame before writing and
return `invalid_argument` with `actual_frame_bytes` and
`max_frame_bytes: 2048` if it is too large. Firmware bounds input independently,
executes no partial/oversized command, discards through LF to resynchronize, and
returns bounded `invalid_argument` when possible.

Decoded `hello.firmware` and `hello.device` are each 1..64 UTF-8 bytes; decoded
command-error `detail` is 1..256 UTF-8 bytes. None contains a Unicode `Cc`
control character; identity strings also have no leading/trailing Unicode
`White_Space`. Senders never truncate them. Enhanced `uart.data_b64` decodes to
1..32768 bytes;
firmware splits a larger available batch into ordered valid frames rather than
truncating it. These field limits are separate from escaped wire size, session
quota, and derived-line limits.

Because JSON Schema `maxLength` counts Unicode characters, the schema records
the byte ceilings in `$comment`; host and firmware runtime validation remains
authoritative for UTF-8 byte length and control-character rejection.

Only the following host-to-device command categories are in scope:

- channel-aware control configuration
- `pulse_control`
- `set_control_state`
- `uart_send`

Only the following device-to-host messages are in scope:

- `hello`
- `uart`
- `buffer_overflow`
- `buffer_status`
- command success response
- command error response

The Phase 1 `configure_gpio_mode` command is channel-aware so Device Core can
configure the physical channel resolved from a host role. The target wire
command carries:

- physical channel, such as `CTRL0`
- electrical mode, such as `open_drain`
- active level
- idle level, when required by push-pull behavior

`role` and `dut_signal` are host-side metadata for status, lookup, logs, and
reports. Neither is sent to firmware. Firmware stores accepted electrical
configuration by physical channel and does not interpret project/user names.

Firmware actions are generic and operate only on an already accepted channel
configuration:

```jsonl
{"cmd": "pulse_control", "channel": "CTRL0", "pulse_ms": 100}
{"cmd": "set_control_state", "channel": "CTRL1", "state": "active"}
```

`pulse_control` applies the configured active behavior for the validated 1..10000
ms duration and then restores idle behavior. `set_control_state` accepts only
`active` or `idle` and applies the configured behavior for that state. Firmware
does not assign semantics to `reset`, `boot`, or any custom role during an
action. Device Core resolves the exact host role to its accepted channel:
`POST /dut/reset` uses `pulse_control`, while boot mode `bootloader` uses active
and `normal` uses idle. These safe semantic host APIs remain unchanged and no
public raw-level GPIO operation is introduced.

The current draft command schema still requires `configure_gpio_mode.role`.
Phase 1B removes that property and rejects it as an extra field after migration.
The shared 1..64-byte identifier validation remains authoritative at every host
configuration/API boundary; firmware validates only channel and electrical
fields because neither host identifier consumes wire-frame space.

Protocol changes must update the schema files, examples, parser tests, and firmware handling in the same change.

The current parser has no frame limit, strips surrounding whitespace, and may
lose valid earlier frames from a chunk when a later frame fails. The current
schemas also omit the target maximum lengths. Framing, parser/encoder behavior,
schemas, examples, firmware, and tests must change atomically.

The current draft v1 schema advertises legacy `uart_capture`. Phase 1B must
rename this capability to `uart_receive`, consistent with `uart_send`, in one
atomic protocol change. The target Enhanced capability set is
`uart_receive`, `uart_send`, `gpio_control`, `device_timestamp`, and
`overflow_telemetry`. `gpio_events` remains Phase 5. Reset and boot are
configured roles, not capabilities.

The current draft v1 host-command schema likewise still contains legacy
`reset` and `set_boot_mode`. The same Phase 1B protocol migration must replace
them with `pulse_control` and `set_control_state` across schema, canonical
examples, encoders/parser models, tests, and firmware, while removing
`configure_gpio_mode.role`. Mixed old/new action/configuration vocabularies are
not supported.

## Device Core Requirements

The Device Core library must:

- Select exactly one Basic or Enhanced backend for a DUT connection; Hybrid
  composition is not supported.
- Expose the asynchronous `BackendEventSource` contract defined in this
  document, implemented by both backends.
- Run exactly one serial reader for the selected backend and preserve FIFO
  event order while Enhanced command requests are pending.
- Return `None` from `receive_event()` only for an ordinary timeout; represent
  disconnect and invalid backend input with `BackendDisconnectedError` and
  `BackendInputError`.
- Keep raw bytes authoritative in `UartReceiveEvent`; derive display text and
  complete lines only in the shared UART processing layer.
- Keep timestamp provenance in immutable per-segment context instead of
  repeating it on each event. Permit `BackendEventSource.segment` to remain
  `None` only until the first timestamped event establishes the source origin;
  it must be available before that event is returned.
- Own Enhanced-backend protocol parsing and validation without imposing that
  protocol on the Basic backend.
- Derive Basic `backend_capabilities` from its implementation and read Enhanced
  `backend_capabilities` from validated `hello`. Apply shared host policy to
  produce effective `capabilities`; `hardware.uart.tx_enabled` defaults false
  and removes `uart_send` for both backends when disabled.
- Decode Enhanced-backend `data_b64` payloads to raw bytes.
- Bound Enhanced NDJSON before decode, preserve valid preceding frames, and
  surface malformed/oversized input as fatal `BackendInputError` without
  publishing a partial normalized event.
- Preserve exactly all quota-admitted UART bytes in `uart_raw.log`; the first
  complete input unit rejected by the evidence cap is never partially stored and
  is reported by truncation metadata.
- Produce lossy UTF-8 display text with replacement characters for CLI display and pattern matching.
- Buffer UART bytes into complete lines before running pattern detection, with a
  fixed 65536-byte derived-line limit per segment/channel that never truncates
  stored raw UART artifacts.
- Reconstruct bounded recent-log views from a stable `uart_events.jsonl`
  snapshot, with independent buffers per segment/channel and exact
  `line_raw_b64` evidence. Never derive authoritative line bytes from stored
  display text or join a line across a reconnect.
- Select `first_error` from the earliest stored failure-pattern match in segment
  and event-ingestion order. The Phase 1 failure patterns are `ERROR`, `ASSERT`,
  `PANIC`, and `HardFault`; `BOOT_OK` is a success marker and is excluded.
- Record Enhanced-backend buffer overflow events.
- Start the Enhanced firmware with a 32 KiB UART RX ring buffer and expose
  buffer telemetry.
- Load and validate hardware channel mappings from `.dutchmate/config.toml`.
- Apply hardware channel mappings only to the Enhanced backend. With the Basic
  backend, control and event operations must return
  `unsupported_capability` without sending a hardware command.
- Check backend capabilities before required role mappings so an incapable
  backend is not misreported as merely unconfigured.
- Enforce accepted GPIO role modes before reset and boot-mode operations.
- Track each required GPIO role as `unconfigured`, `configured`, or `rejected`.
- Treat config-file GPIO modes as explicit configuration only after firmware accepts them.
- Preserve the previous accepted GPIO mode when a runtime override is rejected.
- Preserve `channel`, `role`, `dut_signal`, mode, source, and last rejection in
  status/reporting models.
- Track nullable `commanded_boot_mode` separately from configured GPIO state.
  Set it to `normal` after an accepted boot mapping, update it only after a
  successful boot-mode command, and clear it when disconnect or a safety fault
  invalidates the commanded state. Never present it as electrical readback.
- Keep plain boot-test reset-only. A caller that wants a bootloader test must
  explicitly select `bootloader`, run the test, and select `normal`; Device Core
  must not silently select or restore a boot mode.
- Implement wait-pattern as a standalone capture-like session with one
  waiter-local line buffer and an ingestion cursor. Use case-sensitive literal
  matching on complete lines received after the cursor; do not search stored or
  already-ingested history.
- Reject hardware-starting operations while any finite UART receive workflow
  owns the stream.
- Reject overlapping capture, boot-test, or wait-pattern workflows with
  `capture_active`. Reject UART send with that code while any of those sessions
  is active unless the request explicitly sets `force = true`. That flag
  bypasses only this ownership conflict and must never override validation,
  effective `uart_send` capability policy, connection state, or backend
  failures.
- For every forced in-session send, durably append `uart_tx_attempt` after all
  pre-dispatch checks and before backend dispatch, then append
  `uart_tx_result` after backend completion. Do not dispatch if the attempt
  cannot be stored, and treat an unmatched attempt as an explicitly unknown
  outcome. Keep transmitted bytes out of receive-only `uart_raw.log`.
- Expose UART send to service/CLI/MCP clients as UTF-8 text with
  `append_newline = true` by default. Append one LF only when the encoded bytes
  do not already end in LF; preserve existing LF/CRLF endings, and add nothing
  when disabled. Do not expose raw bytes or base64 through those public Phase 1
  interfaces.
- Limit the final encoded UART-send payload to 1..1024 bytes. Validate after
  optional LF insertion and before capability, policy, capture-ownership,
  connection, or transport checks. Require each backend to accept all bytes
  before success; retry Basic short writes to completion or return a transport
  error, and require Enhanced firmware to validate the decoded size before
  acknowledgement.
- Preserve backend identity, capabilities, timestamp provenance, and the
  `integrity` loss-observation object in normalized events and sessions.
- Remain independent from MCP and LLM frameworks.

## Session Storage Requirements

Every capture-like workflow creates a session under `.dutchmate/sessions/`.

Minimum Phase 1 files:

```text
metadata.json
uart_raw.log
uart_events.jsonl
hardware_events.jsonl
detected_patterns.json
```

An active session also has internal `.terminal-reserve`; it is removed during
terminalization and is not a user evidence artifact.

The configured session-store root also contains optional `baseline.json`, the
authoritative versioned pointer for the one project-wide baseline. It is store
metadata, not a per-session evidence artifact.

Each Phase 1 session directory is one versioned evidence-format unit.
`metadata.json` contains immutable integer `schema_version: 1`, which governs the
metadata and every artifact in that directory; individual event records do not
carry independent schema versions.

Writes must be incremental. A USB disconnect, process interruption, or capture
failure must not discard already admitted data. Quota rejection is the sole
planned omission and is explicit through terminal truncation metadata.

`metadata.json` must include at least:

- `schema_version`: integer `1`
- `session_id`
- `started_at`
- `state`: `active`, `completed`, `failed`, or `abandoned`
- `workflow`: `capture`, `boot_test`, or `wait_pattern`
- accepted `duration_s` for capture/boot-test; null for wait-pattern, whose
  accepted bound is stored separately as `timeout_s`
- accepted `reconnect_timeout_s` policy snapshot for all capture-like workflows
- nullable `ended_at`
- nullable `end_reason`
- nullable bounded `error` with `code`, `detail`, and `detail_truncated`
- bounded Device Core-generated `command`
- `backend_mode` and bounded `backend_identity`
- backend-reported/derived capabilities, effective capabilities, and applied
  capability-policy snapshot
- nullable `commanded_boot_mode` snapshot at session start
- per-segment timestamp provenance
- `integrity.loss_status`: `none_reported`, `loss_reported`, or `not_observable`
- `integrity.observation_scope`: observer name or `null`
- `integrity.dropped_bytes`: non-negative integer or `null`
- `line_processing.status`: `complete` or `limit_exceeded`
- `line_processing.max_line_bytes`: fixed at 65536
- `line_processing.oversized_line_count`: non-negative integer
- `storage.evidence_budget_bytes`
- `storage.evidence_bytes_written`
- `storage.metadata_max_bytes`: fixed at 262144
- `truncated`
- nullable bounded `truncation`
- `interrupted`
- `resumed`
- `segments`: 1..32 complete contiguous segment objects, IDs `0..31`

Native version `1` backend identity is exactly:

```json
{
  "backend_mode": "enhanced",
  "backend_identity": {
    "port": "/dev/ttyACM0",
    "device": "DUTchMate",
    "firmware": "0.1.0"
  }
}
```

`backend_identity.port` is the exact selected serial-port string, encoded as
1..4096 UTF-8 bytes, with no leading/trailing Unicode `White_Space` and no
Unicode `Cc` control. Preserve internal non-control whitespace; never trim,
truncate, normalize, or rewrite the value. Basic uses null `device` and
`firmware`; Enhanced snapshots the exact accepted 1..64-byte `hello` identity
values. Discovery-only USB descriptions/HWIDs are not copied into session
metadata. Native metadata does not duplicate `device` or `firmware` at top
level; those fields remain part of the unversioned legacy shape only.

`command` is a non-authoritative display value generated by Device Core after
request validation. Its UTF-8 encoding is 1..256 bytes, it contains no Unicode
`Cc` control, and it includes only the workflow name plus accepted
duration/timeout. The separately stored typed fields own semantics. Pattern
literals, UART payloads, backend ports, and arbitrary source/CLI command text
must not be embedded in `command` or shortened to fit it.

For a failed session, `error` is exactly `{"code", "detail",
"detail_truncated"}`. `code` comes from the fixed service error vocabulary,
including `internal_error`. `detail` is non-empty and at most 1024 UTF-8 bytes:
replace CR/LF/tab with one ASCII space and other Unicode `Cc` controls with
U+FFFD, use the code's canonical default if empty, then retain the longest
code-point-aligned prefix that fits. The required boolean is true exactly when
that final step omitted text; do not append an ellipsis. No raw frame, UART
payload, object representation, or complete filesystem content enters detail
or context. Active, completed, and abandoned sessions use null `error`.

Legacy version `0` compatibility validates `command` against the same 1..256
byte limit and nullable `firmware`/`device` against the same 1..64-byte identity
limits. Readers do not trim or truncate malformed stored values; they return
`persistence_fault` for that session.

An existing unversioned metadata file is recognized only as legacy
`schema_version: 0`. It remains read-only and may be exposed through bounded
identity/artifact-size compatibility projections, but Phase 1 must not infer or
backfill lifecycle, backend, integrity, timestamp-provenance, quota, or
truncation facts. Log replay, appends, startup recovery, baseline/comparison, and
Debug Agent packaging require native version `1`. `GET /sessions` can identify
legacy entries without pretending they have native summary fields.

There is no automatic or lossless Phase 1 `v0 -> v1` migration. Future migration
must require an explicit operation, preserve the source evidence, identify both
versions, and refuse when required facts would need inference. An unknown
well-formed integer version is preserved and returns
`unsupported_session_schema`; malformed version fields are
`persistence_fault`. Legacy sessions are protected from retention, and an
unknown version blocks the retention pass.

Session lifecycle is one-way. Creation initializes every required artifact and
durably writes metadata with `state: "active"` before the service publishes the
session as its active workflow owner. While active, `ended_at`, `end_reason`,
and `error` are null. A session transitions exactly once and is never reopened:

- `completed` uses expected `end_reason` values `duration_elapsed`,
  `pattern_matched`, `timeout`, `size_limit`, or `user_stop`; `error` is null.
- `failed` uses an operational reason such as `reconnect_timeout`,
  `reconnect_limit`, `backend_error`, `backend_input_error`,
  `persistence_error`, or `internal_error`; `error` contains the bounded
  code/detail/truncation shape above and uses a canonical service error code.
- `abandoned` uses `end_reason: "service_restart"` and null `error`. Its
  `ended_at` records when startup recovery observed the stale session, not when
  capture actually stopped.

An Enhanced fatal input error preserves every earlier admitted unit and ends an
active workflow as `failed` / `backend_input_error`. It does not itself set
`interrupted`, `truncated`, or UART `integrity`; those fields retain any earlier
facts. The offending frame is not evidence, the source is closed, and this
session cannot reconnect or resume.

Before opening a backend or accepting a workflow request, startup scans native
version `1` metadata and atomically changes every stale `active` session to
`abandoned`. It reports but does not mutate legacy or unknown-version
directories. It does not auto-resume native stale sessions or infer an
unobserved USB disconnect. A normal terminal transition flushes all accepted
evidence and atomically replaces terminal metadata before clearing the active
workflow owner.

Startup recovery removes and uses an existing `.terminal-reserve` before the
atomic abandoned-metadata replacement. Missing/malformed reserve state is a
persistence diagnostic; recovery still attempts the bounded replacement, and a
failed replacement is `persistence_fault`, not a silently completed recovery.

`sessions.max_size_mb` is a positive integer in MiB units despite the historical
name; booleans are invalid. The default 50 means 52428800 evidence bytes. Each
session snapshots the accepted budget. Count the current logical byte lengths of
`uart_raw.log`, `uart_events.jsonl`, `hardware_events.jsonl`, and
`detected_patterns.json`, including empty JSON/framing and duplicated
raw/base64 representations. Do not count filesystem blocks, temporary atomic
write files, `metadata.json`, `.terminal-reserve`, store-level `baseline.json`,
or future reports.

Serialize counted JSON deterministically as compact UTF-8 in schema key order,
without ASCII-escaping non-ASCII text, and with exactly one LF after each JSONL
record or complete JSON document. The initial `detected_patterns.json` is
`[]\n`, so an empty session starts with three counted evidence bytes. Admission
measures these exact candidate bytes.

Compact `metadata.json` is separately capped at 262144 bytes. Session creation
must create, physically allocate, and fsync a 262144-byte `.terminal-reserve`
before active metadata/ownership is published. Candidate active metadata updates
are accepted only when the metadata plus worst-case bounded terminal fields fit.
Terminalization removes the reserve, writes/fsyncs compact temporary metadata,
atomically replaces `metadata.json`, and fsyncs the directory. Reserve allocation
failure is `persistence_fault` before session publication.

The active-metadata fit check reserves the complete schema framing plus a
1024-byte terminal diagnostic and `detail_truncated`; it does not reserve an
unbounded exception string. Backend identity and generated command are
validated before active publication and remain immutable, so terminalization
must not trim either field to recover space.

One session contains at most 32 complete segment objects, including its initial
segment, and can therefore resume at most 31 times. Segment IDs are contiguous
`0..31`. Every segment retains its complete bounded backend identity,
capability/policy snapshot, timing provenance, and lifecycle fields; writers do
not drop or coalesce old segments. Before publishing a reconnected event source,
Device Core durably appends the new segment and rechecks metadata plus terminal
reserve. A schema-level worst-case serialization test must prove that all 32
maximum-size segments plus worst-case terminal fields fit within 262144 bytes.

Quota preflight serializes one complete input evidence unit before any counted
file mutation. A UART unit includes all raw bytes, one complete compact JSONL
record with LF, all bounded detected-pattern additions measured by the final
JSON-array length, and associated line-processing events. A hardware/session
event is one unit. Admit equality; if the projected final four-file sum exceeds
the budget, publish none of that unit.

The first rejected unit stops new evidence admission and yields successful
terminal `completed` / `size_limit` with `truncated: true`, null error, and
bounded `truncation` details: unit type, projected unit bytes, nullable rejected
UART payload bytes, available segment/channel/timestamp context, and RFC 3339
`occurred_at`. The persisted byte count remains the admitted file-size sum. An
exactly full session with no rejected unit is not truncated. Quota truncation is
independent from backend `integrity` and derived `line_processing`.

Bounded terminal metadata still applies summary facts directly reported by the
rejected unit. A rejected buffer-overflow event marks integrity as loss-reported,
and a rejected disconnect marks interruption, while the truncation object says
the detailed event artifact is absent. Rejected UART bytes are not submitted to
line or pattern processing.

The exact truncation fields are `reason: "size_limit"`,
`rejected_unit_type`, `rejected_unit_evidence_bytes`,
`projected_evidence_bytes`, nullable `rejected_uart_payload_bytes`, nullable
`segment_id`, `channel`, and `timestamp_us`, plus `occurred_at`. Unit type is
`uart_receive`, `hardware_event`, `session_event`, or `uart_tx_attempt`; unit
bytes are the positive final-size delta across counted files.

Actual serialization/write/fsync/rename/disk failure after admission is
`persistence_fault`, not `size_limit`; terminal state is failed with
`persistence_error` when terminal metadata remains writable. JSONL records and
JSON documents must never be deliberately cut to fit.

Admitting a forced `uart_tx_attempt` also reserves the maximum schema-valid
matching result size. All other admission checks subtract outstanding result
reservations. On size-limit detection, stop new receive evidence, allow bounded
in-flight forced sends to consume their result reservations, then terminalize.
Release unused reservation after the result. Process interruption can still
leave an unmatched attempt as unknown.

Target wait-pattern sessions additionally store the accepted literal pattern,
`match_mode: "literal"`, `case_sensitive: true`, accepted `timeout_s`, final
`matched` boolean, `end_reason`, and nullable `detected_pattern_index`.

Native session summaries and capture-like responses additionally expose `first_error`
as a reference-bearing view of one `detected_patterns.json` entry. The compact
list form contains pattern/index, segment/timestamp/channel, line event/byte
boundaries, total line bytes, and half-open raw match byte offsets. Detail and
capture-like forms add the stored `match_excerpt`, at most 4096 exact raw bytes
with start/end offsets, lossy text, base64, and `excerpt_truncated`. It is `null`
when no failure pattern matched. The response must include session `integrity`,
`line_processing`, and truncation state alongside it. Selection is by segment
order and then event ingestion order, never by comparing timestamps across
segments. The detected-pattern record remains the authoritative source.

All Phase 1 detector patterns use the same 1..256-byte UTF-8/no-CR-or-LF bound
as wait-pattern. One detected record per pattern/line references that pattern's
first occurrence. Lossy decoding retains a mapping to raw byte offsets. Excerpt
selection centers the complete matched span within a 4096-byte window where
possible, clamps to the line, and shifts at either end to consume the available
budget. Full source lines are located by event ingestion indexes and zero-based
event-byte offsets; end offsets are exclusive.

Derived line processing is bounded independently per `(segment_id, channel)`.
A normal complete or partial line contains at most 65536 exact bytes, including
LF when present. For an admitted input, on byte 65537 Device Core first ensures
the delivered UART event is persisted, discards only the derived buffered copy, marks
`line_processing.status: "limit_exceeded"`, increments the oversized-line count,
and counts in constant memory until LF or segment/session close. It never splits,
truncates, emits, or pattern-matches the oversized physical line. It appends a
`line_limit_exceeded` session event with line boundaries, exact byte count, and
termination state, then resumes normal assembly after LF. Raw logs/events remain
complete, so this does not alter UART integrity or session `truncated`.

The status/count update occurs once when byte 65537 is observed; the event is
finalized at LF or segment/session close. Every normal, partial, and oversized
derived record has `(ingestion_index, line_index_in_event)`, where the second
value gives byte order among records attributed to that UART event. Trailing
unterminated records are attributed to their last contributing event.
`*_event_offset` values index decoded UART-event payload bytes and use exclusive
end offsets; they are not JSONL file offsets.

Each segment must include:

```json
{
  "segment_id": 0,
  "started_at": "2026-08-11T12:00:00Z",
  "timestamp": {
    "source": "host",
    "clock": "monotonic",
    "unit": "us",
    "origin": "segment_start",
    "source_origin_us": 4812390123,
    "observation_point": "host_serial_read",
    "event_granularity": "serial_read_chunk"
  }
}
```

Normalized events store `segment_id` and segment-relative `timestamp_us`.
Normalization subtracts `source_origin_us` from the raw backend clock. If the
clock cannot be sampled at segment creation, the first timestamped event sets
the origin and receives timestamp zero.

Basic backends use `time.monotonic_ns()`, timestamp once per delivered serial
read chunk, and assign that timestamp to all bytes in the chunk. Enhanced
backends use the RP2040 timer and timestamp once per firmware UART event before
USB delivery. Neither backend may infer per-byte timing. A reconnect always
creates a new segment/origin, and timestamps are never compared across segments.
RFC 3339 wall-clock fields are descriptive metadata only.

The `integrity` object records UART loss observations, not global evidence
quality:

| Backend/result | `loss_status` | `observation_scope` | `dropped_bytes` |
|---|---|---|---:|
| Basic default | `not_observable` | `null` | `null` |
| Enhanced without reported overflow | `none_reported` | `debug_helper_rx_buffer` | `0` |
| Enhanced with reported overflow | `loss_reported` | `debug_helper_rx_buffer` | known count or `null` |

`none_reported` means only that the named observation scope reported no loss.
It must not be presented as proof that the complete UART path was lossless.
`truncated`, `interrupted`, and `resumed` remain independent session fields.

Reconnect and resume behavior is defined in
`docs/reconnect_session_semantics.md` for both backends. UART events written
after a reconnect must include `segment_id`; that segment selects the timestamp
origin and provenance.

Current implementation notes:

- `uart_raw.log` preserves bytes delivered to Device Core incrementally and
  exactly.
- `uart_events.jsonl` currently records raw device `timestamp_us`, base64 UART
  payloads, lossy display text, `segment_id`, and redundant `timestamp_epoch`.
- `hardware_events.jsonl` records `buffer_overflow` and `buffer_status` events.
  Target `uart_tx_attempt` / `uart_tx_result` perturbation recording is not
  implemented.
- `UartLineBuffer` enforces the 65536-byte derived-line limit independently per
  segment/channel. Byte 65537 discards only the derived copy, switches to
  constant-memory counting, and yields one exact boundary/count descriptor at
  LF or session close; raw logs and UART events remain complete. Persistent
  `line_processing` status/counts and `line_limit_exceeded` session events expose
  the limitation, and processing resumes after LF. Normal completed lines retain
  source event/byte boundaries; detected-pattern records retain first-occurrence
  raw offsets and at-most-4096-byte exact excerpts, and session summaries select
  the earliest failure by segment/event order while excluding `BOOT_OK`.
- Runtime-created capture/boot-test sessions with complete backend snapshots now
  write `schema_version: 1`, typed workflow/duration/reconnect policy, one-way
  active/terminal state, bounded failure details, storage accounting, and an
  allocated terminal reserve that is removed on atomic metadata replacement.
  Capture responses and CLI output expose lifecycle state/end reason. Direct
  store fixtures without workflow facts remain recognized unversioned v0 rather
  than receiving inferred lifecycle data. Before backend opening, startup scans
  stored metadata, atomically abandons stale native active sessions with
  `service_restart`, retains recovery diagnostics, and leaves terminal, legacy,
  malformed, and unsupported-schema evidence unmodified as appropriate. Removal
  of redundant `timestamp_epoch`, full identity validation, complete fsync
  guarantees, project baseline pointer, quota admission for future reconnect,
  control-action, and UART-TX evidence, and retention remain to be implemented.
  Native UART receive, buffer overflow/status, and finalized line-limit session
  events now preflight their exact whole-unit evidence bytes atomically.
  Equality is admitted; the first over-budget unit is omitted whole and
  completes the session as `size_limit` with bounded truncation context.
  Rejected overflow/status evidence still applies its bounded loss, overflow,
  and segment-timestamp summary facts in terminal metadata.
- Reconnect/resume mutation helpers are not implemented yet.
- Capture and boot-test reject non-numeric, boolean, non-finite, non-positive,
  and over-300-second durations consistently across core, service, and CLI.
  Native sessions persist and echo the accepted duration and reconnect policy.

## Device Core Service Requirements

The Device Core Service is a persistent FastAPI process that owns the selected
backend and serial port and exposes local HTTP endpoints. Basic startup opens a
user-selected serial port with explicit UART settings and does not wait for a
DUTchMate `hello`. Enhanced startup opens the Debug Helper transport, validates
the first `hello`, and applies configured hardware mappings. Without a selected
backend/port, the service runs in a disconnected state.

Currently implemented endpoints:

- `GET /status`
- `POST /dut/capture`
- `POST /dut/boot-test`
- `POST /gpio/mode`
- `POST /dut/reset`
- `POST /dut/boot-mode`

Remaining target Phase 1 endpoints:

- `GET /dut/logs`
- `POST /dut/wait-pattern`
- `POST /dut/uart/send`
- `GET /sessions`
- `GET /sessions/{id}`
- `POST /sessions/{id}/baseline`
- `DELETE /sessions/{id}/baseline`

All endpoints return JSON. Errors use:

```json
{"ok": false, "error": "<code>", "detail": "...", "detail_truncated": false, "context": {}}
```

`context` is optional for general errors. The canonical Phase 1 service errors
are:

- `invalid_argument` / HTTP 400 for malformed or invalid request parameters
- `not_found` / HTTP 404 for a well-formed missing session/resource or when no
  implicit session can be selected
- `unsupported_capability` / HTTP 409 when the selected backend lacks a
  required capability or explicit host policy disables it
- `not_configured` / HTTP 409 when the capability exists but a required user
  role has no accepted configuration
- `capture_active` / HTTP 409 for a transient operation-ownership conflict
- `invalid_session_state` / HTTP 409 when a session exists but its state,
  workflow, or evidence-quality facts make the requested session operation
  ineligible
- `unsupported_session_schema` / HTTP 409 when an operation requires native
  Phase 1 evidence but the selected session is legacy or declares an unsupported
  version
- `persistence_fault` / HTTP 500 when required session evidence cannot be
  durably written or safely read
- `internal_error` / HTTP 500 for an unexpected failure with no more specific
  public code
- `backend_input_error` / HTTP 502 when the selected backend emits malformed,
  oversized, or schema-invalid input
- `hardware_fault` or `timeout` / HTTP 502 after an attempted backend operation
- `service_unavailable` / HTTP 503 when no usable backend connection exists or
  an active workflow cannot resume before its reconnect deadline or because its
  32-segment maximum was reached

Every response uses the canonical non-empty 1..1024-byte sanitized diagnostic
projection and always includes `detail_truncated`. Schema-defined context is
bounded by its field contracts and never carries arbitrary exception text, a
wire frame, or a UART payload.

The current mapper already returns `internal_error` for otherwise unmapped
exceptions, but its payload contains only `ok`, `error`, and unbounded `detail`.
It does not yet apply the diagnostic projection, emit `detail_truncated`, or
return structured `context`.

`unsupported_session_schema` context contains `session_id`,
`detected_schema_version`, `supported_schema_versions: [1]`, and `operation`.
Recognized unversioned metadata reports detected version `0`; malformed version
fields use `persistence_fault` instead.

`backend_input_error` context includes `operation`, `backend_mode`, and
`input_error` (`frame_too_large`, `invalid_utf8`, `invalid_json`, or
`invalid_message`). Frame-size context adds `observed_frame_bytes` and
`max_frame_bytes`; no response or session metadata copies the offending frame or
UART payload.

An admitted disconnect while segment `31` is active closes that segment and
immediately fails the session with `end_reason: "reconnect_limit"` and error
code `service_unavailable`; Device Core does not attempt a 33rd connection. The
HTTP 503 context is exactly `operation`, `session_id`, `segment_count: 32`, and
`max_segments: 32`. The canonical detail is `Session reached the 32-segment
reconnect limit` with `detail_truncated: false`. Existing evidence remains
retrievable, `truncated` stays false, and UART integrity is unchanged. A quota
rejection of the disconnect remains `completed` / `size_limit`; a persistence
failure remains `persistence_error`.

`[backend].reconnect_timeout_s` defaults to 5.0 seconds and must be a finite
numeric value in the inclusive range 0.1..60.0; booleans are invalid. It is
validated before backend startup and snapshotted in every native capture-like
session. Each admitted disconnect starts a fresh host-monotonic reconnect
window, but never changes the original workflow deadline. The replacement
source must be ready strictly before both deadlines; a tie is resolved in favor
of the normal workflow deadline. Reconnect timeout fails as
`reconnect_timeout` / `service_unavailable` with canonical bounded detail and
HTTP context exactly `operation`, `session_id`, and `reconnect_timeout_s`.

For invalid `role` or `dut_signal`, `invalid_argument` context contains `field`,
`reason` (`invalid_type`, `invalid_length`, `edge_whitespace`, or
`control_character`), and `max_bytes: 64`. String inputs also report
`actual_bytes`; control-containing values are never echoed.

Capability checks precede role checks. `unsupported_capability` context includes
`operation`, `backend_mode`, `required_capabilities`, effective
`available_capabilities`, raw `backend_capabilities`, and
`disabled_by_policy`. Policy entries identify the capability and configuration
key that disabled it. `not_configured` context includes `operation`,
`required_role`, and `role_state`. The CLI must preserve the error code and a
useful detail message; future MCP tools must preserve the full structured
context.

`GET /status` must include GPIO/control mapping state so users and agents can
see which required roles are configured, rejected, or still unconfigured. The
status payload should include the role, physical channel, DUT signal name, mode,
source, and last rejection detail when present.

It must also include `connection_state`, nullable `active_workflow`, and
nullable `reconnect_remaining_s` so CLI status can report an active reconnect
window without inferring volatile state from persisted metadata. The existing
`connected` boolean remains true only when `connection_state` is `connected`.

`GET /status` must also expose nullable `commanded_boot_mode`. This is the last
state successfully commanded by Device Core, not measured DUT pin state. It is
`null` when the role is not configured, boot state is external/unknown, or the
connection/safety state invalidates the last command.

`GET /status` must also identify `basic` or `enhanced`, report the active serial
port, preserve pre-policy `backend_capabilities`, report filtered
`capabilities`, and include `capability_policy`. The policy object records
`uart_send.tx_policy_enabled` plus source `hardware.uart.tx_enabled`. This is
software permission, not physical TX state or readback. Operations gate only on
effective `capabilities`. Status omits or marks unsupported control/event state
for the Basic backend. The current status model implements the identity,
capability layers, TX-policy source, current segment provenance, and initial
backend-specific integrity. Connection-state/reconnect and commanded-boot-mode
fields above remain pending.

`GET /dut/logs` accepts optional `session_id` and integer `lines`, default 300,
in the inclusive range 1..1000. Booleans and path-unsafe IDs are
`invalid_argument`. Explicit selection wins; otherwise select the active
session, then the newest terminal session (`completed`, `failed`, or
`abandoned`). Return `not_found` for a well-formed
unknown ID or when implicit selection has no session. The response exposes
`session_selection` (`explicit`, `active`, or `latest_terminal`), selected
`session_id`, `schema_version: 1`, whether it was active, and
`snapshot_event_count`. Startup must
recover stale active metadata before implicit selection.

An active-session read captures the UART JSONL offset after the last durable
newline-terminated record and corresponding metadata under the session append
lock, releases the lock, and replays through that cursor. A write still in
progress is outside the snapshot; any malformed complete captured record is a
`persistence_fault`. Replay decodes `data_b64` and buffers per
`(segment_id, channel)`. A complete line retains LF, uses lossy UTF-8 only for
`line_text`, preserves exact bytes as `line_raw_b64`, and receives the timestamp
of the event containing LF. Normal complete and partial records are limited to
65536 exact bytes using the shared derived-line contract.

Each record exposes zero-based `ingestion_index` from the snapshotted UART JSONL
prefix and `line_index_in_event`. Complete, partial, and oversized arrays are
independently ordered by that tuple and can be merged without timestamp
comparison. A trailing record uses its last contributing event index and follows
normal or oversized records completed earlier in that event.

Return the newest requested complete lines oldest-to-newest plus
`partial_lines`, containing non-empty trailing buffers marked `partial: true`.
Partials use their last contributing event timestamp and never cross a segment
boundary. Lines exceeding the processing limit appear only as bounded
`oversized_lines` descriptors containing segment/channel, start/end event and
byte offsets, total bytes, termination state, and final timestamp; they contain
no invented text/raw line payload. Retain the newest at most `lines` normal
complete records and independently the newest at most `lines` oversized
descriptors using bounded candidate deques, returning both oldest-to-newest.
The compact UTF-8 JSON body is capped at 262144 bytes. Remove oldest
records/descriptors until it fits; never slice one.
Report `response_truncated`, `omitted_complete_lines`,
`omitted_partial_lines`, and `omitted_oversized_lines` independently from
session `truncated`. Include integrity, `line_processing`, reconnect facts, and
storage/truncation accounting plus timestamp provenance for referenced segments.
Unreadable or inconsistent required artifacts return `persistence_fault` rather
than selecting another session. Replay accepts only native schema version `1`.
An explicit legacy or unsupported-schema selection returns
`unsupported_session_schema`; implicit selection excludes non-native sessions.

`GET /sessions` accepts optional `limit`, default 50, as an integer from 1
through 100; booleans are invalid. It returns `{items, next_cursor}` ordered
descending by `(started_at, session_id)`. The cursor is opaque, versioned,
URL-safe, and represents an exclusive ordering boundary so sessions created
between page requests do not shift the continuation. Invalid or unsupported
cursors are `invalid_argument`; `next_cursor` is null after the last page.

Native list items contain only bounded summary fields: `session_id`,
`schema_version: 1`, `compatibility: "native"`, lifecycle state and workflow,
start/end metadata, backend mode, baseline/truncation/reconnect
facts, segment count, integrity, `line_processing`, and compact reference-only
`first_error` without `match_excerpt`. They do not contain raw logs or complete
event/pattern arrays. A syntactically valid session directory with unreadable,
corrupt, or inconsistent required metadata causes `persistence_fault` naming
that session instead of being skipped.

A recognized unversioned/legacy list item is a discriminated bounded projection:
`session_id`, `schema_version: 0`, `compatibility: "legacy_read_only"`,
`migration_required: true`, `migration_available: false`, and directly validated
`started_at`, `command`, `firmware`, and `device`. It has no synthesized native
lifecycle or evidence-quality fields. An unknown integer version returns
`unsupported_session_schema`; a malformed version is `persistence_fault`.

`GET /sessions/{id}` validates ID syntax before lookup and distinguishes
`invalid_argument` from `not_found`. It returns validated metadata,
`first_error` with its bounded `match_excerpt`, grouped
pattern-classification/count and hardware-event-count
summaries, unresolved forced-UART-attempt count, and an artifact manifest with
byte sizes and record counts. It omits complete UART logs, JSONL event arrays,
and the full detected-pattern array; callers use `GET /dut/logs`. Active detail
uses a stable metadata/artifact snapshot rather than reading a moving tail.
For legacy version `0`, it instead returns the bounded compatibility identity
projection plus artifact names/logical byte sizes without parsing event records
or deriving Phase 1 facts. Unknown versions return
`unsupported_session_schema`.

Retention runs after startup recovery and every terminal transition. It deletes
the oldest eligible terminal sessions by ascending `(started_at, session_id)`
until `sessions.max_count` is met. Active sessions, the session named by a valid
baseline pointer, and sessions held by in-progress readers are protected. If
protected sessions prevent enforcement, the service reports `retention_blocked`
in diagnostics/status and deletes no protected evidence.
Legacy version `0` sessions count toward the limit but are always protected;
unknown versions stop the retention pass rather than being classified or
deleted.

The session store has exactly one optional project-wide baseline pointer,
regardless of backend mode. `<sessions.path>/baseline.json` is authoritative and
contains a version plus `session_id` and RFC 3339 UTC `marked_at`. API/CLI
`baseline` booleans are derived from the pointer; the existing per-session
metadata boolean is legacy state and must not be used as Phase 1 authority.

`POST /sessions/{id}/baseline` requires a completed `capture` or `boot_test`
session with no truncation, interruption, or `loss_reported` integrity. Basic
sessions with `not_observable` integrity remain eligible and retain that warning.
`first_error` does not affect eligibility. Ineligible sessions return
`invalid_session_state` with one of `state_not_completed`,
`workflow_not_baseline_eligible`, `truncated`, `interrupted`, or `loss_reported`
using that validation order.
Non-native sessions return `unsupported_session_schema` before eligibility
checks and cannot be designated or compared.

Under one store-wide baseline/retention lock, marking durably atomically replaces
the pointer and returns `session_id`, nullable `previous_session_id`, `changed`,
and `marked_at`. Re-marking the current ID returns `changed: false`, reports the
same ID as previous, and retains its original timestamp. `DELETE
/sessions/{id}/baseline` first validates that the session exists, then removes
the pointer only if it names that ID; no pointer or a different current baseline
returns successful `changed: false`. Mark and clear work while disconnected and
during capture because they do not access hardware or workflow ownership.

A malformed, unreadable, dangling, or non-native-session pointer returns
`persistence_fault` from baseline-dependent reads or mutations. Retention
performs no deletion while pointer validity is unknown. After successful
replacement or clearing it runs again because an old baseline may now be
eligible.

Phase 4 comparison resolves the current pointer or returns `not_found` when no
baseline is designated. The subject must be a terminal `capture` or `boot_test`
session but need not satisfy baseline eligibility. Log/pattern comparison may
cross backend modes. Timing is comparable only for uninterrupted single-segment
sessions whose timestamp `source`, `clock`, `observation_point`, and
`event_granularity` are equal; otherwise the result reports
`timing_comparable: false` and a reason.

`POST /gpio/mode` is the Phase 1 runtime override endpoint for a configured
role. It must return the accepted role, channel, DUT signal name, mode, source,
RFC 3339 UTC `configured_at`, and optional raw firmware
`device_timestamp_us`. Reset and boot-mode responses return RFC 3339 UTC
`performed_at` and optional raw `device_timestamp_us`; boot-mode success also
echoes the accepted `mode`. Rejections must leave
prior accepted state unchanged. Current action endpoints expose the raw command
timestamp as legacy `timestamp_us`; this host API rename remains Phase 1 work.

Wire command acknowledgements retain raw `timestamp_us`. A control action
recorded in a session uses `segment_id` and normalized segment-relative
`timestamp_us` in `hardware_events.jsonl`; it may retain the raw value only as
explicit `device_timestamp_us`. A standalone action response has no normalized
session timestamp.

`POST /dut/reset` accepts optional `pulse_ms`, defaults it to 100, and validates
an integer range of 1 through 10000 ms inclusive. Booleans, fractional values,
and out-of-range values return `invalid_argument` before capability checks,
role checks, or transport dispatch. Success returns the accepted `pulse_ms`,
`performed_at`, and optional `device_timestamp_us`. A reset performed within a
boot-test session stores `pulse_ms` in its normalized control-action evidence.
Core command validation already enforces the numeric range; response echo and
session control-action persistence are not implemented yet.

`POST /dut/boot-mode` maps `normal` to the boot role's configured idle behavior
and `bootloader` to its active behavior. The accepted command persists until it
is changed, the mapping is replaced/reapplied, the backend disconnects, or a
safety fault forces high impedance. An accepted mapping starts in `normal`.
`POST /dut/boot-test` requires only `reset`, snapshots nullable
`commanded_boot_mode` in the session, and does not issue a boot-mode command.
Current code sends and role-gates boot-mode commands but does not yet echo the
mode, track/report commanded state, or store its session snapshot.

`POST /dut/wait-pattern` accepts a Unicode `pattern` and numeric `timeout_s`.
The UTF-8-encoded pattern must be 1..256 bytes and contain neither CR nor LF.
The timeout must be finite and satisfy `0 < timeout_s <= 300`; booleans are
invalid. Validation occurs before capability, connection, active-owner, or
session checks. The operation requires effective `uart_receive`, creates a new
session, and returns `capture_active` if capture, boot-test, or another wait
already owns the finite receive stream.

Phase 1 matching is a case-sensitive literal substring search on normal complete
lossy UTF-8 display lines. Regex, glob, and escape syntax are not interpreted.
The workflow registers an ingestion cursor and starts an empty local line
buffer; it never searches prior sessions, earlier events, or pre-cursor partial
line state. It combines the requested literal with default detector patterns
without duplicates, stores all matches, and returns the first requested match
by event-ingestion then line order. Oversized physical lines are excluded from
matching without affecting raw persistence; the session's `line_processing`
object makes that omission explicit. The detected record's exact bounded
`match_excerpt` is returned rather than duplicating the complete line.

On match, the response contains `ok: true`, `matched: true`, `session_id`,
`pattern`, `end_reason: "pattern_matched"`, `match_excerpt`,
`detected_pattern_index`, `channel`, `segment_id`, normalized `timestamp_us`,
and the capture-like integrity/line-processing fields. A monotonic deadline expiry returns
`ok: true`, `matched: false`, `end_reason: "timeout"`, and null match fields.
That outcome is distinct from the canonical HTTP 502 `timeout` error for
failed backend operations. The complete backend event that produced a match is
persisted before the workflow stops, even if it contains subsequent lines.

`POST /dut/uart/send` accepts string `cmd`, optional boolean `append_newline`
defaulting to `true`, and optional boolean `force` defaulting to `false`.
Device Core UTF-8 encodes `cmd`; when newline insertion is enabled it appends
one LF only if the encoded bytes do not already end in LF. Existing LF and CRLF
endings are preserved, while a trailing CR becomes CRLF. When disabled, the
encoded bytes are submitted unchanged. Public Phase 1 clients cannot submit
raw bytes or base64.

The resulting payload must contain 1..1024 bytes. An empty command is valid
with default newline insertion because its final payload is one LF; it is
invalid with `append_newline = false`. Device Core returns `invalid_argument`
before capability/policy, capture, connection, or transport work when the final
payload is empty or oversized. Oversize error context includes `actual_bytes`
and `max_bytes: 1024`.

With an active capture, boot-test, or wait-pattern session, `false` returns
`capture_active` and `true` permits the send. `force` has no additional effect
without an active session and cannot override invalid arguments,
`tx_enabled = false`, absent `uart_send`, disconnection, or backend faults.
Success returns RFC 3339 UTC
`performed_at`, optional raw `device_timestamp_us`, optional `attempt_id`, and
`perturbation_logged`. Outside a session, the last field is `false` and no
attempt ID is created. For a forced in-session success it is `true` only after
both perturbation records are durable.

After pre-dispatch checks pass, the in-session forced path durably appends a
`uart_tx_attempt` containing `attempt_id`, `segment_id`, host RFC 3339
`attempted_at`, exact backend-submitted `data_b64`, `payload_bytes`, and
`forced: true`. Failure to append returns `persistence_fault` without backend
dispatch. Validation, capability, policy, ownership, and connection failures
occur before the attempt record and therefore create no perturbation event.

After dispatch concludes, `uart_tx_result` stores the same `attempt_id` and
`segment_id`, host RFC 3339 `completed_at`, `outcome` (`success` or `failed`),
nullable canonical `error`, and nullable `bytes_accepted`. Success requires
`bytes_accepted` to equal `payload_bytes`. Basic records the accumulated serial
write count and a host-monotonic normalized completion `timestamp_us`.
Enhanced preserves firmware `bytes_accepted` and, when available, raw
`device_timestamp_us` plus its normalized session timestamp; successful
firmware acknowledgements require both the full accepted count and raw
`timestamp_us`. A failed operation may have a nonzero or unknown count and does
not imply electrical rollback.

If result persistence fails after dispatch, Device Core returns
`persistence_fault` with `attempt_id`; the durable unmatched attempt means the
completion is unknown. A failed dispatched request returns its canonical
backend error with `attempt_id` and `bytes_accepted` in `context`. The existing
core command helper already performs UTF-8 encoding, default LF insertion, and
explicit no-newline behavior. Service, CLI, backend workflow, and perturbation
recording remain unimplemented. The helper and current v1 wire schema do not
enforce the 1024-byte limit or accepted-byte response fields, and the current
serial command transport does not verify or complete short writes.

UART-send completion is all-or-error at the API boundary, not electrically
transactional. Basic loops until all final bytes are accepted by the serial
driver, returning `hardware_fault` or `timeout` on failure/no progress.
Enhanced firmware validates 1..1024 decoded bytes and acknowledges success only
after accepting the complete payload for UART transmission. Neither path may
return success for a short write, but bytes already placed on the physical line
cannot be rolled back.

Target capture-like responses must include `schema_version: 1`, `integrity`,
`line_processing`, `storage`, nullable `truncation`, accepted `duration_s`, `truncated`,
`interrupted`, `resumed`, integer `segments` in 1..32, and bounded `first_error`.
This response field remains a count for compatibility. Native
`metadata.json.segments` is the bounded object array; session list summaries
name its integer projection `segment_count`, while native session detail
includes the validated metadata array.
The current `overflow: bool` response field is replaced during the Phase 1A
metadata/API migration.

`POST /dut/capture` and `POST /dut/boot-test` require explicit numeric
`duration_s` with no default. It must be finite and satisfy
`0 < duration_s <= 300`; integers and fractional values are accepted, while
booleans, strings, null, zero, negatives, non-finite values, and values over 300
are `invalid_argument`. Core validation runs before capability/policy, required
role, connection, active-owner, reset, or session-storage work. In particular,
an invalid boot-test duration cannot dispatch reset or create a session.

Success echoes and persists the accepted numeric `duration_s`. Capture and
boot-test each compute one host-monotonic deadline from that value. Serial read
polling, quiet input, and reconnect handling do not reset or extend it. Deadline
arrival completes the session with `end_reason: "duration_elapsed"`; HTTP 502
`timeout` remains an operational backend failure, not a normal finite capture
result.

Buffer sizing and validation are defined in `docs/ring_buffer_sizing_plan.md`. Phase 1 firmware must make overflow observable and should expose high-water mark, dropped-byte count, and overflow-event count for validation.

## CLI Requirements

The CLI is a thin HTTP client. It must not import hardware transport code directly.

Minimum Phase 1 commands:

- `dutchmate start`
- `dutchmate stop`
- `dutchmate status`

Currently implemented startup/discovery behavior:

- `dutchmate devices [--all]` lists DUTchMate candidates or all serial ports.
- `dutchmate start --serial-port <device>` selects an explicit device.
- Without `--serial-port`, start auto-selects exactly one DUTchMate candidate,
  starts disconnected when there are none, and rejects ambiguous multiple
  candidates.

Target Phase 1 startup must require an explicit Basic or Enhanced backend mode
from CLI `--backend` or `[backend].mode`; there is no default. CLI values
override configuration. Basic mode requires `--serial-port` or
`[backend].serial_port`, opens that port as raw UART using `[hardware.uart]`
settings, and does not probe for or wait for a DUTchMate `hello`.

Enhanced mode accepts an explicit port or auto-selects exactly one strong
DUTchMate metadata match. No match leaves the service disconnected in Enhanced
mode; multiple matches require explicit selection. Every selected Enhanced port
must pass `hello` and protocol-version validation, and a validation failure must
not fall back to Basic. Startup selects only one backend and must not compose
capabilities from multiple serial devices.

Target CLI/config surface:

```text
dutchmate start --backend <basic|enhanced> [--serial-port <device>] [--baudrate <rate>]

[backend]
mode = "basic" | "enhanced"
serial_port = "..."       # required for Basic, optional for Enhanced
reconnect_timeout_s = 5.0 # finite 0.1..60.0; capture-like resume window

[hardware.uart]
baudrate = 115200       # Basic example; Enhanced Phase 1B uses 460800
data_bits = 8
parity = "none"
stop_bits = 1
tx_enabled = false
```

Phase 1 accepts 8-N-1 framing and rejects unsupported framing explicitly. The
effective default is backend-specific: Basic defaults to 115200 and opens the
DUT-facing adapter at the configured supported rate; Enhanced Phase 1B defaults
to and is fixed at 460800. Enhanced rejects another configured rate until a
reviewed firmware protocol supports runtime UART-rate configuration. The host
USB CDC protocol port is not the DUT UART and does not reinterpret this setting.
`tx_enabled` defaults to false and determines whether either backend exposes
effective `uart_send`. Basic derives pre-policy send support from its writable
serial implementation; this is not proof that adapter TX is connected or
electrically compatible. Enhanced must both advertise `uart_send` in `hello`
and have `tx_enabled = true`. DTR, RTS, and serial flow control are not used.

`tx_enabled` does not promise an electrically disabled or high-impedance TX
line. A Basic adapter may drive idle whenever its TX wire is connected. Users
requiring Basic receive-only electrical behavior leave TX disconnected.
Enhanced Revision A uses shared `DBG_UART_IF_EN` for both `TXU0202` directions,
so enabling receive also enables the debugger-to-DUT channel and may drive
UART idle. Independent Enhanced TX isolation requires a later hardware
revision; it is not a Phase 1 firmware behavior.

Target `dutchmate devices` lists all ports from metadata and never opens them.
It labels trusted DUTchMate USB identity matches as `enhanced_candidate` and all
others as unverified `generic`. Fixed VID/PID and finalized USB identity are the
long-term match; the current free-text hint is temporary.

Currently implemented hardware-control commands:

- `dutchmate gpio mode <channel> <role> <dut_signal> --mode <open_drain|push_pull> --active-level <low|high> [--idle-level <low|high>]`
- `dutchmate dut reset [--pulse-ms <ms>]`
- `dutchmate dut boot-mode <normal|bootloader>`

These commands require the Enhanced backend, `gpio_control`, and the relevant
configured role. With the Basic backend they return
`unsupported_capability`; with a capable Enhanced backend missing the relevant
accepted role mapping they return `not_configured`.

`dutchmate gpio mode` validates `role` and `dut_signal` locally using the shared
1..64 UTF-8 byte identifier contract before HTTP dispatch. It forwards and
prints the exact strings without trimming or normalization. Service and Device
Core repeat the validation and remain authoritative.

Currently implemented capture commands:

- `dutchmate capture --seconds <seconds>`
- `dutchmate boot-test --seconds <seconds>`

`capture` must work with either backend. `boot-test` requires the Enhanced
backend, `gpio_control`, and a configured `reset` role.

Both commands require `--seconds`; the CLI has no implicit duration. It accepts
finite numeric values in `0 < seconds <= 300` and rejects invalid values locally
before sending HTTP. The service remains authoritative and applies the same
validation. CLI request timeouts must cover the accepted duration plus a bounded
transport/completion grace period; they must not silently increase the Device
Core workflow deadline.

Remaining target Phase 1 commands:

- `dutchmate logs [--session <session_id>] --last <lines>`
- `dutchmate wait <pattern> --timeout <seconds>`
- `dutchmate send <cmd> [--no-newline] [--force]`
- `dutchmate sessions [--limit <count>] [--cursor <opaque>]`
- `dutchmate session <session_id>`
- `dutchmate mark-baseline <session_id>`
- `dutchmate clear-baseline <session_id>`

`dutchmate logs` defaults `--last` to 300 and preserves the service's active,
then latest-terminal implicit selection when `--session` is absent. It prints
the selected session ID, complete lines in returned evidence order, and partial
records with a visible partial marker. It prints oversized descriptors as
non-UART-text processing notices at their evidence positions and never invents
their content. It reports response/session truncation, integrity, and
line-processing warnings separately. Segment-transition separators are CLI-only
presentation derived from metadata; they must not be printed as though they
were DUT UART bytes or returned to other clients as line evidence.

`dutchmate sessions` forwards the bounded page arguments and prints the returned
summary page plus an opaque next cursor when present. `dutchmate session`
forwards one validated ID and prints the bounded detail response. Neither
command reads session files directly or expands complete evidence arrays.
Both display `schema_version` and `compatibility`; legacy version `0` output is
clearly read-only and omits unavailable native fields. Phase 1 intentionally has
no `migrate-session` command because the current unversioned format cannot be
converted losslessly. A future migration command must call an explicit service
operation and must never rewrite session files directly from the CLI.

`dutchmate mark-baseline` prints whether the designation changed, the retained
or new mark time, and the replaced session ID when present. It surfaces
eligibility reasons and integrity provenance without prompting or inferring
known-good status. `dutchmate clear-baseline` clears only the named current
baseline and reports an idempotent no-change result otherwise. Both commands use
the service API and remain available while the backend is disconnected.

`dutchmate wait` forwards the literal pattern without shell-style, regex, or
glob interpretation. It validates the 1..256 UTF-8 byte/no-line-break contract
and `0 < timeout <= 300`, then prints the session ID and bounded match excerpt
with line-byte offsets plus segment/timestamp provenance. A normal deadline prints `No match` and the
session ID and exits successfully; service, capability, connection, and
ownership errors remain nonzero failures. It does not search old sessions or
attach to an active capture.

`dutchmate send` defaults to `force = false`. If a session is active, the CLI
reports `capture_active` and does not suggest, infer, or automatically retry
with `--force`. An explicit `--force` sends during the active session and
reports the `attempt_id` and whether the complete perturbation pair was
recorded. On failure after dispatch, it reports the attempt ID, accepted-byte
count or `unknown`, and warns that bytes may have reached the DUT. Outside an
active session, `--force` has no additional effect.

The CLI UTF-8 encodes `cmd` and appends LF by default. `--no-newline` disables
only that insertion and composes independently with `--force`.

If the service is not running, commands must fail with:

```text
Error: Device Core Service is not running. Run 'dutchmate start' first.
```

## Testing Requirements

Any workflow exposed through the CLI must first pass through these layers:

1. Device Core unit tests using fake Basic/Enhanced backends and protocol fixtures.
2. Device Core Service integration tests using fake backends.
3. CLI tests against the service API.
4. Hardware smoke test, when hardware behavior is involved.

Minimum Phase 1 test coverage:

Shared/backend-independent coverage:

- Fake Basic and Enhanced sources satisfy the same `BackendEventSource`
  contract and drive the same capture workflow without Debug Helper message
  types crossing the boundary.
- `receive_event()` preserves FIFO ordering, returns `None` for timeout, and
  raises the specified distinct errors for disconnect and malformed input.
- Raw UART bytes cross the normalized boundary unchanged; lossy display text is
  derived downstream and is not part of `UartReceiveEvent`.
- The same receive -> line processing -> pattern detection -> session path runs
  for fake Basic and Enhanced backends.
- Backend mode, pre-policy backend capabilities, effective capabilities, and
  policy provenance are reported by status and stored in sessions.
- `tx_enabled` defaults false for both backends. Enhanced may advertise
  `uart_send` while effective capabilities omit it; Basic may derive write
  support while policy still disables it.
- Status/session policy uses `tx_policy_enabled` and never labels this value as
  physical TX state. Tests verify command dispatch is blocked, not that adapter
  or Revision A DUT RX is high impedance.
- Basic receive-only electrical use leaves adapter TX disconnected. Enhanced
  Revision A tests acknowledge that shared UART OE enables both translator
  directions; no Phase 1 test claims independent TX isolation.
- Setting `tx_enabled = true` makes `uart_send` effective only when raw backend
  support exists. Policy cannot manufacture a capability absent from Enhanced
  `hello`.
- A policy-disabled send returns `unsupported_capability` with
  `disabled_by_policy` identifying `hardware.uart.tx_enabled`.
- Every quota-admitted UART byte is preserved exactly for both backends; a
  rejected unit is omitted whole and reported as local truncation.
- Capture/boot-test duration accepts positive fractional values and exact upper
  boundary 300; it rejects booleans, strings, null, zero, negatives, non-finite
  values, and values above 300 as `invalid_argument`.
- Invalid duration is rejected before capability, role, connection, owner,
  reset, or session-store calls; tests specifically verify boot-test does not
  reset and neither workflow creates an artifact directory.
- Success echoes/persists the accepted duration. Quiet reads and reconnect do
  not extend the single monotonic deadline, and normal expiry is
  `completed`/`duration_elapsed`, not HTTP 502 `timeout`.
- UART payload containing invalid UTF-8.
- Pattern split across multiple UART receive events.
- Recent logs validate line count and session ID before lookup, select explicit
  then active/latest sessions as specified, and return `not_found` rather than
  an empty anonymous result when no session exists.
- Active log reads stop after the last durable complete JSONL record; an append
  still in progress is visible only later, while a malformed captured record
  returns `persistence_fault`.
- Log replay reconstructs exact LF-terminated lines per segment/channel,
  timestamps them from the completing event, retains same-event byte order, and
  returns the newest requested lines oldest-to-newest.
- Log replay exposes trailing bytes as partial records, never joins them across
  channels or reconnect segments, and preserves invalid UTF-8 in
  `line_raw_b64` while using replacement text for display.
- Exactly 65536 bytes is accepted as a normal partial line, and a complete line
  is accepted only when its LF is within that limit. Byte 65537 switches only
  derived state to oversized counting while raw event/log persistence remains
  exact.
- An oversized terminated or trailing physical line produces one ordered
  descriptor and one `line_limit_exceeded` session event with exact boundaries;
  it is never split, emitted as a normal/partial line, or pattern-matched.
- Recent replay retains at most the requested count of oversized descriptors
  without materializing all descriptors and reports count- and byte-budget
  omissions together in `omitted_oversized_lines`.
- After an oversized line's LF, the same event's following bytes start a fresh
  normal line. Separate channel and reconnect-segment limit state cannot mix.
- Complete, partial, and oversized arrays expose ingestion/line indexes so
  callers can merge them deterministically without timestamp comparison.
- The 262144-byte serialized response cap omits oldest whole records with
  explicit complete/partial/oversized counts; it never slices evidence and never
  aliases response limiting to session `truncated`; selected session storage and
  truncation accounting remain visible.
- Lifecycle creation publishes ownership only after all required artifacts and
  active metadata are durable; completion flushes accepted events before one
  atomic terminal transition and never reopens a terminal session.
- Startup converts stale active metadata to abandoned before backend/workflow
  startup, records recovery observation time, and neither resumes the old
  workflow nor invents disconnect evidence.
- Session listing validates limit/cursor types, orders by descending
  `(started_at, session_id)`, pages stably while newer sessions are created, and
  reports corrupt required metadata instead of silently skipping it.
- Session detail is bounded, snapshots active metadata/artifact counts, reports
  unresolved forced sends, and excludes full UART/event/pattern arrays.
- New sessions persist immutable integer `schema_version: 1`; event/artifact
  readers dispatch from the session version and reject malformed or unknown
  versions without mutating evidence.
- Unversioned version `0` sessions list/detail only through the bounded read-only
  compatibility shape, are excluded from replay/recovery/baseline/comparison,
  and remain protected from retention. Unknown versions stop retention.
- Startup performs no automatic migration. Tests confirm that no native
  lifecycle, provenance, integrity, or quota facts are inferred for legacy data.
- Backend identity accepts exact 1- and 4096-byte serial-port strings, including
  internal non-control whitespace, and rejects 4097 bytes, edge Unicode
  whitespace, and Unicode `Cc` before backend/session publication. Multibyte
  cases prove UTF-8 byte counting and round-trip preservation.
- Basic native metadata stores null backend `device`/`firmware`; Enhanced stores
  its exact accepted 1..64-byte, no-`Cc`, no-edge-whitespace hello labels. Native
  metadata has no duplicate
  top-level legacy identity fields and does not persist USB discovery text.
- Generated session `command` contains only workflow and accepted timing,
  remains within 1..256 UTF-8 bytes with no controls, and excludes wait-pattern
  literals, UART payloads, ports, and arbitrary caller command text.
- Service and failed-session diagnostic details accept exact 1024-byte output,
  truncate a 1025-byte or multibyte-crossing output only on a code-point
  boundary, set `detail_truncated` exactly, sanitize controls, and never copy
  rejected payloads/context. Empty upstream text uses the canonical fallback.
- Legacy projections accept boundary-valid command/identity strings and return
  `persistence_fault`, without rewriting, for an out-of-range or malformed
  required value.
- Sessions accept complete contiguous segments `0..31` and never create segment
  `32`. A worst-case 32-segment metadata document including terminal reserve
  fields fits within 262144 compact bytes without dropping identity or
  provenance.
- Disconnect from segment `31` is admitted and recorded before the session
  fails as `reconnect_limit`/`service_unavailable`; tests assert no reopen or
  reconnect/discontinuity event, no integrity/truncation mutation, and exact
  HTTP context. Quota and persistence failures retain their higher-priority
  outcomes.
- Default `max_size_mb: 50` yields 52428800 bytes; positive-integer config
  validation rejects booleans, and each session snapshots its accepted budget.
- Evidence accounting equals the current logical lengths of the four Phase 1
  evidence files, counts JSON/base64/framing and initial array bytes, and excludes
  metadata, reserve, temporary files, baseline pointer, and future reports.
- Exact-budget evidence units are admitted. A one-byte-over projected UART or
  hardware/session unit is rejected before any counted file changes; raw,
  JSONL, pattern JSON, and line-event artifacts remain structurally consistent.
- First quota rejection yields `completed`/`size_limit`, `truncated: true`, exact
  admitted-byte accounting, and bounded rejected-unit context. Filling the
  budget exactly without a later rejection leaves `truncated: false`.
- Rejected overflow/disconnect units still update bounded integrity/lifecycle
  summaries while their absent detailed record remains explicit; rejected UART
  bytes never create line or pattern evidence.
- Metadata stays within 262144 compact bytes and active session creation
  physically allocates/fsyncs `.terminal-reserve`; allocation failure publishes
  no active session. Terminalization removes the reserve and atomically replaces
  metadata. The fit check includes the full 1024-byte diagnostic projection and
  its truncation flag without trimming immutable command/backend identity.
- Injected serialization, short-write, fsync, rename, and disk-full failures are
  `persistence_fault`/`persistence_error`, never clean size-limit truncation, and
  leave no deliberately partial JSON/JSONL record.
- A forced-send attempt is admitted only with reserved worst-case matching-result
  space. Concurrent receive admission respects the reservation, and size-limit
  terminalization waits for the bounded result before releasing unused quota.
- Retention removes oldest eligible terminal sessions while protecting active,
  the designated baseline, and currently read sessions, and reports
  `retention_blocked` when protected sessions exceed the configured count.
- Baseline marking accepts eligible completed Basic `not_observable` and
  Enhanced sessions, rejects each ineligible lifecycle/evidence condition in a
  deterministic order, and does not treat `first_error` as an eligibility gate.
- Baseline replacement is atomic and idempotent under the retention lock;
  clearing only the named current pointer is idempotent, and both operations
  trigger retention after a change.
- Corrupt or dangling baseline pointers produce `persistence_fault` and suspend
  retention. Comparison resolves the one project pointer and suppresses timing
  comparison when provenance or segment shape is incompatible.
- Wait-pattern accepts a 1-byte and 256-byte UTF-8 literal and rejects empty,
  257-byte, CR/LF-containing, non-string, and byte-count-vs-character-count
  invalid cases before capability or session work.
- Wait timeout accepts finite numeric values above zero through 300 seconds and
  rejects booleans, zero, negatives, non-finite values, and values above 300.
- Regex/glob metacharacters are literal, matching is case-sensitive, prior
  events and pre-cursor partial lines are ignored, and a pattern split across
  post-cursor events matches only when its complete line arrives.
- Wait-pattern creates its own session, returns `capture_active` for overlap,
  persists the complete event containing the first requested match, and returns
  a reference to the authoritative detected-pattern entry.
- Wait-pattern does not match an oversized physical line even if the literal
  occurred before the limit; it can match a later normal line, and every result
  exposes the line-processing limitation.
- Wait deadline expiry returns a successful unmatched result with null match
  provenance and stored integrity facts; it is not mapped to HTTP 502 timeout.
- Deterministic `first_error` selects the earliest failure match, excludes
  `BOOT_OK`, retains its detected-pattern reference, and returns `null` when no
  failure pattern matched.
- Pattern records map lossy-text matches to half-open raw byte offsets, choose
  the first occurrence per pattern/line, and produce deterministic excerpts for
  valid, split, and invalid-UTF-8 input.
- A line at or below 4096 bytes yields a complete excerpt. Longer normal lines
  yield an exact at-most-4096-byte window containing the match, with correct
  line/excerpt offsets and `excerpt_truncated: true`.
- Session-list `first_error` omits `match_excerpt`; detail, capture-like, wait,
  and MCP projections preserve it without restoring a full-line duplicate.
- `first_error: null` remains accompanied by integrity, line-processing, and
  truncation state and is not converted into a global success claim.
- Disconnect marking `interrupted: true` for each backend.
- Reconnect before timeout appending a new session segment.
- Reconnect after timeout ending the interrupted session.
- Reconnect policy defaults to 5.0 seconds, validates finite numeric
  0.1..60.0 input without accepting booleans, and is snapshotted in metadata.
- Reconnect work does not extend the original workflow deadline, and a deadline
  tie resolves as normal workflow completion.
- Timestamp discontinuity creates a new segment with a new source origin and
  provenance object.
- GPIO-mode, reset, and boot-mode host responses distinguish RFC 3339
  `configured_at`/`performed_at` from raw `device_timestamp_us`; no host action
  response exposes the raw device clock as unqualified `timestamp_us`.
- Session control events normalize the device clock using the active segment
  and include `segment_id`; standalone actions do not claim a session-relative
  timestamp.
- Reset defaults to 100 ms; accepts only integer 1..10000 ms values; rejects
  booleans, fractional values, and values outside the range before capability,
  role, or transport work; and echoes/stores the accepted duration.
- Boot-mode `normal` drives the configured idle behavior and `bootloader` the
  configured active behavior for both open-drain and push-pull mappings;
  successful responses echo `mode` and status reports it only as commanded
  state.
- Commanded boot mode persists until explicitly changed or invalidated by a
  mapping replacement, disconnect, or safety fault; invalidation clears it
  rather than claiming a measured state.
- Plain boot-test requires only `reset`, sends no boot-mode command, and stores
  the nullable commanded-state snapshot. Explicit bootloader test orchestration
  selects `bootloader` before it and `normal` afterward.
- A capable Enhanced backend with a missing `reset` or `boot` role returns
  `not_configured` with role context instead of
  `unsupported_capability`.
- Capability gating happens before role checks and does not send a Debug Helper
  command for an unsupported operation.
- CLI selection overrides configuration; an absent backend mode is rejected.
- `dutchmate devices` lists all metadata-visible ports, labels them without
  opening them, and never sends probe bytes.
- Startup never combines UART, control, or event providers from separate ports.

Basic-backend coverage:

- Startup requires an explicit serial port and never auto-selects or waits for
  a `hello`.
- Basic UART configuration accepts supported baud rates with 8-N-1 framing and
  rejects unsupported framing values.
- Raw serial bytes are received without a DUTchMate `hello`.
- Host timestamp provenance is explicit, uses `time.monotonic_ns()`, and records
  `host_serial_read` / `serial_read_chunk` granularity.
- Missing upstream overflow telemetry produces `loss_status: not_observable`,
  `observation_scope: null`, and `dropped_bytes: null`.
- UART send works only when `uart_send` is enabled.
- UART send returns `unsupported_capability` when `uart_send` is absent.
- UART send during capture, boot-test, or wait-pattern returns `capture_active`
  by default; explicit `force = true` permits only that conflict override and
  cannot bypass `tx_enabled`, capability, validation, connection, or backend
  errors.
- A forced in-session send durably records `uart_tx_attempt` before dispatch
  and `uart_tx_result` after completion; it does not contaminate receive-only
  `uart_raw.log`. Failure to store the attempt prevents dispatch.
- Attempt/result records share a unique ID and preserve exact submitted bytes,
  segment, host audit times, outcome, canonical error, and known accepted-byte
  count. Basic results use a host-monotonic completion timestamp; Enhanced
  results normalize the firmware timestamp when available.
- Backend failure after partial acceptance stores `failed` with the known
  nonzero count; an unavailable count is `null`. A missing result is surfaced
  as an unknown outcome after process interruption or result-persistence
  failure, never silently treated as success or zero transmission.
- CLI and future MCP clients never retry `capture_active` with force
  automatically.
- UART text send uses UTF-8, appends exactly one LF by default, does not
  duplicate existing LF/CRLF endings, and submits no terminator with
  `append_newline = false` / `--no-newline`.
- Final UART-send payload accepts exactly 1..1024 bytes after encoding/newline
  handling. Empty-with-default-LF is valid; empty-with-no-newline and 1025-byte
  payloads are rejected before capability, capture, or transport checks, while
  a 1024-byte payload is accepted.
- Oversize errors report `actual_bytes` and `max_bytes`; multibyte UTF-8 cases
  prove the limit is byte-based rather than character-based.
- Basic short writes are completed in order or fail without success; Enhanced
  rejects invalid decoded sizes and acknowledges only complete payload
  acceptance. Tests do not claim electrical rollback after a partial failure.
- Public service, CLI, and MCP requests reject raw/base64 UART payload fields;
  backend protocol and session records preserve the final bytes as base64.
- GPIO mode, reset, boot-mode, and boot-test return
  `unsupported_capability` with capability context when their required
  capability is absent. GPIO event operation tests begin with the Phase 5 API.

Enhanced-backend coverage:

- Firmware/static mapping tests match every Revision A net-to-Pico assignment
  in the hardware architecture table.
- Schematic/BOM review matches every Revision A logic-device MPN and package;
  substitutions are rejected unless introduced as a reviewed hardware
  revision.
- An explicit port must validate `hello`; validation failure does not retry the
  port as Basic.
- Exactly one strong metadata match may be auto-selected, no match stays
  disconnected, and multiple matches require explicit selection.
- Valid `hello` handshake.
- Protocol version mismatch.
- Malformed JSON line.
- Device-to-host frames of exactly 65536 total bytes are accepted when otherwise
  valid; 65537-byte frames and a pending 65536th non-LF byte fail before decode
  without unbounded buffering.
- Host-to-device encoders accept an otherwise valid 2048-byte total frame and
  reject 2049 bytes before serial dispatch; firmware also executes no oversized
  command.
- Writers emit compact LF-only frames. Receivers accept one optional CR before
  LF but reject empty frames, BOM, outer whitespace, invalid UTF-8, and trailing
  bytes outside the JSON object.
- When one serial chunk contains valid frames followed by an invalid frame, all
  earlier normalized events retain FIFO order; the offending and later frames
  are not published, pending commands fail, and an active session ends as
  non-resumable `failed` / `backend_input_error` without changing independent
  integrity/truncation/interruption facts.
- `firmware`/`device` accept 1 and 64 UTF-8 bytes and reject 65 bytes, control
  characters in Unicode category `Cc`, and identity-edge `White_Space`. Error
  detail accepts 1 and 256 UTF-8 bytes and rejects 257 bytes or Unicode `Cc`;
  multibyte tests count encoded bytes rather than characters and accepted
  values round-trip without trimming or normalization.
- Enhanced UART frames accept 1 and 32768 decoded payload bytes, reject empty or
  32769-byte payloads, and firmware splitting preserves byte order without
  truncation.
- Unknown message type.
- Invalid base64 payload.
- Command responses are routed to the pending request while interleaved UART
  and telemetry events remain queued in FIFO order for `receive_event()`.
- Enhanced UART events use device timestamp provenance and are normalized
  relative to the segment origin before storage.
- Buffer overflow event propagation.
- Buffer telemetry records high-water mark and dropped-byte count.
- Deliberate overflow stress sets `loss_status: loss_reported`, identifies
  `debug_helper_rx_buffer` as the observation scope, and records the known
  dropped-byte count.
- Reset rejected before `reset` role mapping/mode configuration.
- Boot-mode rejected before `boot` role mapping/mode configuration.
- Invalid hardware mapping rejected: unknown channel, duplicate channel, wrong channel type, or empty `dut_signal`.
- `high_z` is rejected as a configuration mode, while startup/fault and
  open-drain-release tests verify the physical high-impedance drive state.
- Open-drain active-high/explicit-idle combinations and push-pull missing/same
  active-idle combinations are rejected before transport dispatch; equivalent
  malformed wire commands are rejected by firmware.
- Accepted configuration enters released state for open drain and the explicit
  idle level for push pull without a transient active drive.
- A well-formed custom control role is accepted and reported without gaining a
  built-in reset/boot workflow; blank or non-string role values are rejected.
- Role and DUT signal accept 1 and 64 UTF-8 bytes and reject 65 bytes. Tests use
  multibyte input to prove byte rather than character counting, and reject
  leading/trailing Unicode whitespace plus ASCII/Unicode `Cc` controls.
- Accepted identifiers round-trip byte-for-byte through config/runtime state,
  service responses, status, and session evidence. No layer trims, truncates,
  case-folds, Unicode-normalizes, or aliases them.
- Role lookup and movement are case-sensitive: exact lowercase `reset` and
  `boot` activate built-in workflows, while `Reset`/`Boot` remain distinct
  custom roles. Canonically equivalent Unicode spellings also remain distinct.
- Target Enhanced configuration commands omit both `role` and `dut_signal`;
  firmware validates the physical channel and electrical mode fields only.
- Moving a role at runtime leaves exactly one effective channel assignment.
- Config-file hardware control mode accepted after firmware `hello`.
- Startup GPIO mode rejection visible in service status.
- Runtime GPIO mode override leaves prior accepted mode unchanged if rejected.
- Reset resolves the exact `reset` role and emits `pulse_control` for its
  accepted channel; boot-mode resolves exact `boot` and emits
  `set_control_state` with `active` or `idle`. Firmware action handling does not
  branch on role names.
- Legacy `reset` and `set_boot_mode` wire commands are rejected after the
  atomic Phase 1B protocol migration.
- Hardware command rejected while capture, boot-test, or wait-pattern is active.
- `EVENTn` capture is not required until Phase 5.

### DUT Firmware Validation Fixture

The first real DUT fixture uses Zephyr and is separate from the Zephyr firmware
on the RP2040 Debug Helper. It provides deterministic modes for:

- successful boot with an unambiguous completion marker
- initialization failure with a stable first-error marker
- silent boot and capture timeout
- partial lines and non-UTF-8 UART bytes
- burst and sustained UART output for loss and truncation checks
- UART command/response when transmit is enabled
- repeated reset and boot-test cycles with the Enhanced backend

Validate the same fixture first through the Basic backend around a manual or
external reset, then through the Enhanced backend with configured control roles.
Assertions below the fixture layer use normalized bytes, events, capabilities,
timestamps, integrity metadata, and session artifacts. They do not depend on
Zephyr log prefixes unless a configured pattern explicitly requests one.

The HIL report records the Zephyr version, board, application commit, build ID,
configuration, and resulting DUTchMate session IDs. These are fixture
provenance, not inferred Phase 1 session fields. Flashing remains external.
Additional ecosystems may be added after this baseline is stable.

## Done Criteria

### Phase 1A Done: Basic Backend

- The Device Core exposes a normalized UART receive interface and shared
  capture/session pipeline.
- `dutchmate start` can select a generic USB-to-UART adapter explicitly without
  requiring DUTchMate identity metadata or a `hello` message.
- `dutchmate capture --seconds 15` receives real DUT UART through the Basic
  backend and creates a session after a manual/external reset.
- The session preserves all admitted raw UART bytes, parsed events, backend identity,
  capabilities, segment-relative host timestamp provenance, the `integrity`
  and `line_processing` objects, metadata, and detected patterns. Its
  Basic-backend loss status is `not_observable`.
- Capture-like responses expose deterministic `first_error` with evidence
  provenance or `null`, independently of backend mode.
- UART send works when enabled; control/event operations fail clearly as
  unsupported.
- Shared host unit/integration/CLI tests pass with a fake Basic backend.
- A real generic USB-to-UART adapter + Zephyr DUT fixture smoke test
  demonstrates UART receive, capture/session storage, and retrieval. Host
  assertions remain independent of Zephyr log syntax and tooling.

### Phase 1B Done: Enhanced Backend

- The Enhanced Debug Helper implements the same UART receive interface and uses
  the same downstream capture/session pipeline as Phase 1A.
- The schematic and firmware use the complete Phase 1 Revision A Pico mapping
  from `docs/dutchmate_hardware_architecture.md` section 10.1 without implicit
  channel swaps.
- The first prototype uses the Revision A provisional logic-device MPNs and
  records results for leakage, sequencing, isolation, voltage-level, and UART
  signal-integrity validation.
- The Debug Helper advertises `uart_receive` rather than legacy
  `uart_capture`, and protocol schemas/examples/parser/tests agree.
- Debug Helper actions use generic `pulse_control` and `set_control_state`
  channel commands; legacy role-specific `reset` and `set_boot_mode` wire
  commands are absent from schemas, examples, encoders, tests, and firmware.
- `.dutchmate/config.toml` can map `reset` to a physical `CTRLx` channel and DUT
  schematic signal.
- `dutchmate gpio mode CTRL0 reset RESET_N --mode open_drain --active-level low`
  configures the mapped reset role.
- `dutchmate boot-test --seconds 15` resets the DUT and creates a session with
  segment-relative device timestamp provenance and buffer-loss telemetry.
- Boot-test returns the same deterministic `first_error` contract used by Basic
  capture sessions; AI interpretation is not required.
- `hardware/validation/phase1_ring_buffer.md` records the Zephyr RAM report and
  HIL load measurements, then closes the UART RX buffer gate as `accepted_32k`
  or `revised_with_evidence`.
- Shared host unit/integration/CLI tests pass with a fake Enhanced backend and
  Debug Helper protocol fixtures.
- A real RP2040 + the same Zephyr DUT fixture smoke test demonstrates reset,
  UART receive, boot-test, overflow reporting, and session storage.
- `EVENTn` ownership is documented, but GPIO event capture is not required.

### Phase 1 Complete

Phase 1 is complete only when both Phase 1A and Phase 1B done criteria pass. In
addition:

- The CLI can retrieve bounded, provenance-bearing recent logs from an
  explicit, active, or latest terminal session, list/detail bounded session
  metadata, and mark, replace, or clear one project baseline from either backend.
- Capture and boot-test enforce and report the same explicit
  `0 < duration_s <= 300` contract across core, service, CLI, and MCP-facing
  responses.
- `dutchmate wait` applies the same bounded literal, new-evidence-only session
  contract for either backend and distinguishes no-match from an operation
  error.
- `truncated`, `interrupted`, `resumed`, segment count, timestamp provenance,
  the UART loss-observation object, and independent derived-line processing
  status, evidence-budget accounting, and quota-truncation detail are represented
  consistently in sessions and API responses.
- Every event timestamp is segment-relative, each segment stores immutable clock
  provenance, and no API or workflow compares timestamps across segments.
- Native sessions preserve at most 32 complete contiguous segments and fail
  explicitly as `reconnect_limit` without attempting a 33rd connection.
- Native capture-like sessions snapshot the validated reconnect timeout, and
  reconnect timeout/deadline precedence is identical for both backends.
- Switching backend modes changes capabilities and evidence quality, not the
  line-processing, pattern-detection, session-storage, service, or CLI
  architecture.
- No Hybrid configuration is accepted.
