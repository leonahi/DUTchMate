# Phase 1 Implementation Specification

> Scope: deterministic DUT interaction through the Device Core library, Device
> Core Service, CLI, Basic generic serial backend, and Enhanced RP2350 Debug
> Helper backend.
>
> Product authority: `docs/project_context.md` defines what DUTchMate is and why
> its boundaries exist. This document defines the normative Phase 1 behavior
> needed to implement and accept that product definition.

## 1. Purpose and Normative Language

Phase 1 proves DUTchMate as a useful embedded-development tool independently of
MCP or AI. A human developer must be able to use the CLI to:

1. continuously preserve UART evidence while DUTchMate owns a connected DUT;
2. observe that evidence live and through bounded Monitor operations;
3. interact bidirectionally with firmware through bounded Interact operations;
4. send explicit standalone UART payloads when policy permits;
5. perform configured deterministic Control operations when the selected backend
   provides them;
6. inspect durable evidence, provenance, connection boundaries, and evidence
   quality after the fact;
7. explicitly release and reacquire a serial transport when an external tool
   needs the same physical port.

The key architectural rule is:

> **Connection/evidence lifetime is continuous; operation lifetime is bounded.**

While DUTchMate owns a connected backend, exactly one authoritative UART receive
path remains active whether or not a Monitor or Interact operation is running.
Monitor and Interact are bounded windows/actions over that continuously acquired
stream. They never create competing serial readers.

The words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are
normative in the RFC 2119 sense.

Progress is not tracked in this document. `docs/development_status.md` is the
only progress/next-step authority.

## 2. Phase 1 Goal

Phase 1 validates one backend-independent Device Core pipeline with two physical
backend implementations:

```text
Basic
  generic host serial device
       |
       +-- continuous UART RX
       +-- policy-gated UART TX
       +-- optional configured serial-line control when explicitly supported

Enhanced
  RP2350/Pico 2 DUTchMate Debug Helper
       |
       +-- continuous UART RX
       +-- policy-gated UART TX
       +-- RP2350 timestamps
       +-- receive-buffer telemetry
       +-- configured CTRL0..CTRL3 control
```

Both backends feed the same evidence, Monitor, Interact, session, retrieval,
service, and CLI layers. Backend-specific framing terminates at the normalized
backend boundary.

Phase 1 is divided into two acceptance milestones:

- **Phase 1A — Basic:** prove continuous evidence acquisition, follow, bounded
  Monitor, policy-gated TX, bounded Interact, durable sessions, reconnect,
  release/reacquire, and CLI retrieval using a generic serial adapter or native
  serial console.
- **Phase 1B — Enhanced:** put the RP2350 Debug Helper behind the same host
  contracts and add device timestamp provenance, overflow telemetry, generic
  configured control, firmware validation, and HIL acceptance.

Phase 1 completes only after both milestones pass shared mocked tests and their
real-hardware acceptance paths.

## 3. Non-Goals

The following are explicitly outside Phase 1 unless required only as an external
integration boundary:

- MCP acceptance; MCP is Phase 2 and must consume the already-proven Device Core
  semantics rather than define them;
- LLM or AI analysis inside Device Core;
- firmware flashing implementation;
- JTAG/SWD/GDB debugging implementation;
- vendor-specific crash-dump or shell protocol decoding;
- an MCUmgr, AT-command, bootloader, or other protocol implementation inside
  Device Core;
- arbitrary public pin-level GPIO commands;
- GPIO `EVENTn` capture implementation; Enhanced owns the future event interface,
  but Phase 5 implements it;
- power/current/voltage sensing;
- Hybrid composition of UART from one physical device and control/events from
  another;
- multi-DUT ownership in one service instance;
- GUI;
- Wi-Fi/BLE transport;
- custom USB vendor protocol;
- terminal emulation beyond the Phase 1 line-oriented human console defined in
  this document;
- replacing oscilloscopes or logic analyzers.

External flash tools such as `esptool`, STM32 UART bootloaders, or MCUboot serial
recovery are not DUTchMate features. Phase 1 only provides an explicit
release/reacquire boundary so such tools can temporarily own the same port.

## 4. Required Implementation Order

The following order is a dependency order, not a progress report:

1. Adopt the Phase 1 contracts in this document and the approved
   `project_context.md`.
2. Introduce the DUT Profile/effective serial-provenance model without changing
   physical behavior yet.
3. Introduce native session schema v2 and continuous evidence persistence.
4. Convert finite receive workflows into bounded Monitor operations over the
   continuous stream.
5. Implement exact-byte audited UART TX and bounded Interact.
6. Implement the CLI `follow` view and line-oriented `console` without direct
   serial ownership in the CLI.
7. Implement explicit release/reacquire, Basic DTR/RTS open semantics, and
   native-USB reconnect identity rules.
8. Migrate Enhanced and configured control to the same v2 evidence/action model;
   retain the existing safe generic channel semantics.
9. Validate all Device Core/service/CLI tests, then run Basic and Enhanced HIL
   acceptance.
10. Only after Phase 1 CLI acceptance, migrate Phase 2 MCP tools to the same
    contracts.

No permanent compatibility path may preserve an obsolete runtime ownership or
session model solely for MCP or other higher-level clients.

## 5. Runtime Architecture

Phase 1 uses one persistent Device Core Service instance for at most one active
DUT/backend:

```text
CLI
 |
 | local service API
 v
Device Core Service
 |
 | one active DUT Profile
 v
Device Core library
 |
 | exactly one selected backend
 v
Basic serial device OR Enhanced Debug Helper
 |
 v
DUT
```

The service is the sole physical owner while `connection_state` is `connected`
or `reconnecting`. The CLI, future MCP server, Debug Agent, and other clients
MUST NOT independently open the same serial device.

The runtime has four distinct concepts:

```text
physical connection
    -> continuous authoritative evidence stream
        -> bounded operations (Monitor / Interact / Control)
        -> live views (follow / console)
        -> durable sessions and retrieval
```

A bounded operation never owns the physical UART reader.

## 6. DUT Profile

### 6.1 Role

Phase 1 MUST have one first-class host-side DUT Profile representing the
configuration required to interact with one DUT consistently. The profile is
configuration, not evidence.

The resolved profile MUST contain or resolve at least:

- optional human-readable profile name;
- backend mode: `basic` or `enhanced`;
- device/port selection and reconnect matching strategy;
- reconnect timeout;
- UART configuration;
- UART TX permission policy;
- Basic DTR/RTS open behavior where applicable;
- optional Basic serial-line semantic-control mapping if supported;
- Enhanced `CTRLn` role mappings and electrical configuration;
- optional default human text line ending;
- connection topology information needed to interpret reconnect behavior.

The file-backed Phase 1 profile remains `.dutchmate/config.toml`. CLI startup
arguments MAY override supported profile fields, but the service MUST resolve one
complete validated effective profile before opening a backend.

### 6.2 Profile snapshot and immutability

Every native v2 session MUST snapshot the bounded effective profile information
that materially affects evidence interpretation. The snapshot MUST include a
stable SHA-256 digest of the canonical resolved profile projection.

Historical evidence MUST NOT be reinterpreted from the current mutable TOML
file. Changing the project profile later cannot change an existing session's
provenance.

Backend/serial/device-selector changes require a new physical ownership interval
and therefore a new session. Runtime Enhanced GPIO-mode overrides are action
records and current runtime state; they do not rewrite the original profile
snapshot.

### 6.3 Phase 1 profile shape

The exact parser implementation may evolve, but the effective model MUST support
at least the semantics illustrated here:

```toml
[profile]
name = "example-dut"

[backend]
mode = "basic"
serial_port = "/dev/cu.usbserial-example"
reconnect_timeout_s = 5.0
topology = "external_uart" # or "native_usb_console"

[hardware.uart]
baudrate = 115200
data_bits = 8
parity = "none"
stop_bits = 1
rtscts = false
xonxoff = false
tx_enabled = false
default_line_ending = "none"

[hardware.uart.control_lines]
dtr_on_open = "deasserted"
rts_on_open = "deasserted"
```

Enhanced control mappings continue to use the semantic contract owned by
`docs/gpio_configuration_semantics.md`, for example:

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

### 6.4 Device selection and native USB

Phase 1 MUST support exact-path selection. For a native USB console that may
re-enumerate under a different host path, automatic reconnect MAY use a stable
USB identity selector based on discovery metadata such as VID/PID plus a unique
serial number.

Automatic reconnect MUST NOT guess between multiple matching devices. Ambiguous
matching leaves the service disconnected and reports a bounded
`service_unavailable` diagnostic with reason `ambiguous_device`.

If a native USB device exposes no safely unique identity, the profile may use an
exact path, but a path change requires explicit reacquire/reconfiguration rather
than unsafe guessing.

## 7. Serial Configuration and Provenance

### 7.1 Basic UART settings

Basic mode MUST support and snapshot effective serial settings. At minimum the
model contains:

- baud rate;
- data bits;
- parity;
- stop bits;
- hardware flow control (`rtscts`);
- software flow control (`xonxoff`);
- DTR requested behavior;
- RTS requested behavior;
- UART TX policy.

Phase 1 Basic accepts the following framing/flow-control contract:

- `baudrate`: positive integer; default 115200;
- `data_bits`: exactly 8;
- `parity`: exactly `none`;
- `stop_bits`: exactly 1;
- `rtscts`: exactly false;
- `xonxoff`: exactly false.

Unsupported values are rejected before opening the serial device. These fields
exist in the profile and segment provenance even when Phase 1 fixes them to one
accepted value, so future framing/flow-control expansion does not require a new
evidence model.

### 7.2 Enhanced UART settings

The Enhanced Debug Helper DUT-facing UART baseline remains 460800 8N1 with no
flow control unless the firmware/protocol contract is revised atomically. USB
CDC host line coding is transport metadata and is not the DUT UART baud.

### 7.3 Wrong settings are still provenance

DUTchMate MUST NOT claim that a configured baud/framing choice is physically
correct for the DUT merely because the host accepted it. Bytes captured using an
incorrect configuration remain observed bytes; the effective configuration that
produced them MUST be visible in provenance.

### 7.4 DTR/RTS open behavior

Opening a serial device can change DTR/RTS and therefore can reset or alter some
boards. Basic Monitor is therefore **receive-only at the UART payload level**;
it is not guaranteed electrically passive merely because UART TX is disabled.

For Basic mode:

- requested DTR/RTS open behavior MUST be explicit in the resolved profile;
- the implementation MUST configure the requested state before physical open
  when the host serial API safely permits it;
- the segment snapshot MUST record the requested state and whether RTS is instead
  owned by hardware flow control;
- the implementation MUST NOT claim glitch-free electrical behavior when the OS,
  driver, or adapter cannot guarantee it;
- a bounded provenance field MUST describe the open-transition guarantee, for
  example `preconfigured`, `best_effort`, or `driver_managed`;
- if `rtscts = true`, RTS cannot simultaneously be used as a semantic control
  line or fixed application-driven state;
- DTR/RTS state is configuration/command intent, not electrical readback.

## 8. Policy and Capabilities

### 8.1 Conservative defaults

A new/unconfigured DUT Profile uses these defaults:

| Capability/policy | Default |
|---|---|
| UART receive | enabled when the backend physically supports it |
| Continuous recording | enabled while connected |
| UART TX | disabled |
| Basic semantic DTR/RTS control | unavailable until explicitly configured and supported |
| Enhanced `CTRLn` control | unavailable until an accepted mapping exists |
| Arbitrary raw GPIO control | unavailable |

Policy is human-owned configuration. A CLI or future coding agent may operate
inside policy but MUST NOT silently broaden it.

### 8.2 Capability vocabulary

The normalized capability vocabulary is:

```python
BackendCapability = Literal[
    "uart_receive",
    "uart_send",
    "serial_line_control",
    "gpio_control",
    "gpio_events",
    "device_timestamp",
    "overflow_telemetry",
    "power_sense",
    "msgpack",
]
```

`serial_line_control` is distinct from generic `gpio_control`.

Basic derives physical capability from the selected host serial implementation.
Enhanced reads physical capability from a validated `hello`. Device Core then
applies host policy/configuration to produce effective capabilities.

`hardware.uart.tx_enabled = false` removes effective `uart_send` even if the
backend can physically transmit.

Policy MUST NOT manufacture a physical capability the backend does not have.

### 8.3 Roles

Capabilities describe physical support. Roles describe project/user meaning.
Exact lowercase `reset` and `boot` retain built-in Phase 1 workflow meaning.
Other valid role names remain custom metadata.

Enhanced roles resolve to configured `CTRLn` channels. Firmware never receives
or interprets role or DUT signal names.

If Basic semantic serial-line control is implemented, its roles resolve to an
explicit bounded DTR/RTS action definition. Basic MUST NOT advertise generic
`gpio_control` merely because DTR/RTS exist.

Capability checks precede role/configuration checks.

## 9. Normalized Backend Contract

Backend-specific framing terminates below Device Core evidence processing. The
target normalized receive contract is:

```python
from dataclasses import dataclass
from typing import Literal, Protocol, TypeAlias

BackendMode: TypeAlias = Literal["basic", "enhanced"]
BackendCapability: TypeAlias = Literal[
    "uart_receive",
    "uart_send",
    "serial_line_control",
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
    clock: Literal["monotonic", "rp2350_timer"]
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

    async def receive_event(
        self,
        timeout_s: float | None = None,
    ) -> BackendEvent | None:
        """Return the next FIFO event, or None for an ordinary read timeout."""
```

`BackendInfo.port` is the exact active serial-port string. Its UTF-8 encoding is
1..4096 bytes, it has no leading/trailing Unicode `White_Space` and no Unicode
`Cc` control characters, and no layer trims, truncates, Unicode-normalizes, or
otherwise rewrites it. Internal non-control whitespace is permitted.

Basic uses null `device` and `firmware` because a generic adapter has no DUTchMate
`hello` identity. Enhanced uses the exact validated `hello.device` and
`hello.firmware` strings, each 1..64 UTF-8 bytes with no Unicode `Cc` and no
edge Unicode `White_Space`.

`receive_event()` returns `None` only for an ordinary backend read timeout.
Disconnect and malformed backend input use distinct exceptions.

Each selected source owns one FIFO event queue and exactly one physical serial
reader. Enhanced command responses are routed to pending command waiters while
UART/telemetry events remain FIFO-ordered and continue to flow to the normalized
queue.

`UartReceiveEvent.data` is authoritative raw evidence. JSON/base64 is a
persistence/API encoding, not the in-memory UART representation.

The receive contract does not define the complete backend interface. UART send,
serial-line control, generic GPIO control, and future event configuration are
separate capability-gated interfaces implemented by the same selected physical
backend.

## 10. Basic Backend Contract

### 10.1 General serial behavior

Basic is any user-selected TTL/logic-level serial device exposed through the host
serial API. It MUST NOT require a DUTchMate `hello`, vendor ID, or proprietary
protocol.

The user remains responsible for electrical compatibility, common ground, and
voltage translation. Software TX disablement is permission policy, not proof
that an attached adapter TX pin is electrically high impedance.

Each successful host serial read chunk becomes one `UartReceiveEvent`. Basic
uses one host monotonic timestamp per delivered serial-read chunk; it does not
infer per-byte timing.

Basic UART loss is normally not directly observable. Unless a supported adapter
provides an explicit trusted loss observer, native v2 evidence reports:

```text
loss_status       = not_observable
observation_scope = null
dropped_bytes     = null
```

### 10.2 Basic TX

If policy enables TX and the host serial adapter supports writes, Basic exposes
`uart_send`. A successful send means all requested bytes were accepted by the
host serial API. Positive short writes MUST be retried in order until complete
or a bounded transport error occurs.

### 10.3 Basic DTR/RTS control

Phase 1 MUST model DTR/RTS open behavior even if semantic reset/boot control is
not implemented for a given adapter/profile.

A Basic backend MAY expose `serial_line_control` when the host API, adapter, DUT
wiring, and profile explicitly support deterministic bounded actions. Such an
implementation MUST:

- use semantic host operations rather than an unrestricted public raw-line API;
- record an action attempt before changing line state;
- bound pulse/hold durations;
- restore the configured terminal state;
- record the result;
- reject conflicts with RTS hardware flow control;
- never advertise `gpio_control` for DTR/RTS.

Basic serial-line control is optional for Phase 1A completion. DTR/RTS open-state
provenance is mandatory.

## 11. Enhanced Backend Hardware Mapping Contract

`hardware/pcb/debug-helper/legacy-eagle/revision_a.md` remains the preserved
Revision A electrical/pin authority until a replacement KiCad revision is
explicitly audited and adopted.

`docs/gpio_configuration_semantics.md` owns the exact identifier, electrical
mode, safety-state, validation-order, and reporting contract. This specification
depends on it.

Phase 1 requirements are:

- Enhanced exposes generic `CTRL0` through `CTRL3`.
- Enhanced reserves `EVENT0` through `EVENT3` for Phase 5 and MUST NOT advertise
  `gpio_events` before that implementation passes its HIL acceptance.
- Users map generic physical channels to host-side role and DUT-signal metadata.
- Exact lowercase `reset` is required by reset and boot-test.
- Exact lowercase `boot` is required only by boot-mode operations.
- Firmware receives channel and electrical behavior, never role or schematic
  signal names.
- Startup, unconfigured, voltage-invalid, rejected-without-prior-state, and fault
  paths keep affected channels high impedance until a mapping is accepted.
- Accepted open-drain mappings enter released idle state; accepted push-pull
  mappings enter their explicit idle level.
- Phase 1 has no persistent public disable/unconfigure workflow.
- If firmware does not measure `DUT_VIO`, configured `dut_io_voltage` may remain
  a trusted user declaration without weakening safe output behavior.

## 12. Enhanced Backend Protocol Contract

The Debug Helper host-device protocol remains NDJSON over USB CDC serial. Each
line is one JSON message. Versioned schemas live under `hardware/protocol/v1/`.
This protocol is private to Enhanced; Basic never sends these messages.

The Phase 1 helper target is the non-wireless Raspberry Pi Pico 2 / RP2350A in
Arm Cortex-M33 mode using the Zephyr `rpi_pico2/rp2350a/m33` target. The firmware
MUST use Zephyr 4.4.2 or newer for the Phase 1 acceptance build because the
RP2350 PL011 UART error-interrupt handling required by this design is corrected
there; affected earlier releases are not accepted for HIL sign-off.

The initial DUT-facing UART RX ring-buffer baseline is 32 KiB. Buffer size is a
measured design gate owned by `docs/ring_buffer_sizing_plan.md`; the accepted
Phase 1 value may change only with recorded RAM/stack/load/overflow evidence.

Each device-to-host wire frame is at most 65536 bytes including LF and one
optional accepted CR immediately before LF. Each host-to-device frame is at most
2048 bytes. Writers emit compact UTF-8 JSON plus LF with no BOM, outer
whitespace, ASCII escaping of non-ASCII text, or CR.

The host enforces receive bounds before decode and permits at most 65535 pending
bytes without LF. Another non-LF byte fails as `frame_too_large`. Empty,
BOM-prefixed, invalid UTF-8/JSON, non-object JSON, unknown/schema-invalid
messages, invalid base64, and out-of-range fields are fatal `BackendInputError`.
Valid earlier frames from the same serial read remain published in FIFO order;
the offending frame and later bytes from that read produce no normalized event.
Pending command waiters fail.

Host encoders measure the complete serialized frame before write and reject an
oversized frame before dispatch. Firmware independently bounds input, executes no
partial/oversized command, discards through LF to resynchronize, and returns a
bounded `invalid_argument` response when possible.

Enhanced host writes retry positive short writes in ordered suffixes and wait for
a command response only after the complete frame has been accepted and flushed.
Internal USB frame-byte counts MUST NOT be misreported as DUT UART payload bytes.

Validated identity fields remain:

- `hello.device`: 1..64 UTF-8 bytes;
- `hello.firmware`: 1..64 UTF-8 bytes;
- command-error `detail`: 1..256 UTF-8 bytes;
- no Unicode `Cc` in any of these;
- no edge Unicode `White_Space` in identity fields.

Enhanced `uart.data_b64` decodes to 1..32768 bytes. Firmware splits larger
available batches into ordered valid frames rather than truncating.

Phase 1 host-to-device command categories remain:

- channel-aware GPIO mode configuration;
- `pulse_control`;
- `set_control_state`;
- `uart_send`.

Phase 1 device-to-host messages remain:

- `hello`;
- `uart`;
- `buffer_overflow`;
- `buffer_status`;
- command success response;
- command error response.

Firmware actions remain generic:

```jsonl
{"cmd":"pulse_control","channel":"CTRL0","pulse_ms":100}
{"cmd":"set_control_state","channel":"CTRL1","state":"active"}
```

`pulse_control` accepts 1..10000 ms and restores idle behavior. `set_control_state`
accepts only `active` or `idle`. Firmware does not assign semantics to `reset`,
`boot`, or custom host roles.

The v1 Enhanced physical capability set is:

```text
uart_receive
uart_send
gpio_control
device_timestamp
overflow_telemetry
```

Legacy `uart_capture`, role-bearing GPIO wire commands, legacy `reset`, and
legacy `set_boot_mode` are invalid. Protocol schemas, examples, encoders,
parsers, firmware, and tests MUST change atomically when this private wire
protocol changes.

## 13. Connection Ownership and Lifecycle

### 13.1 Connection states

The service exposes one of these Phase 1 connection states:

```text
disconnected
connecting
connected
reconnecting
released
reacquiring
faulted
```

`connected: true` is a derived compatibility/status value only when
`connection_state == "connected"`.

### 13.2 Ownership rule

At any instant exactly one owner may hold the physical serial transport.
DUTchMate owns it while connected/reconnecting. An external process may own it
only after successful explicit release.

### 13.3 Connection establishment

Before starting authoritative RX, Device Core MUST:

1. validate the complete effective profile;
2. prepare persistence so connection/action evidence can be recorded;
3. open the selected backend with the configured serial/control-line behavior;
4. validate Enhanced `hello` when applicable;
5. establish one immutable segment context;
6. durably record/publish the connection segment;
7. start exactly one background receive path.

No client operation may use the connection before these steps complete.

### 13.4 Connection segments

A segment is one uninterrupted backend connection/timestamp origin. Each segment
stores at least:

- contiguous session-local `segment_id`;
- `started_at` and nullable `ended_at`;
- start/end reason;
- exact active port/path;
- backend identity;
- raw backend capabilities and effective capabilities;
- policy snapshot;
- effective serial settings;
- DTR/RTS requested/management/open-transition provenance where applicable;
- timestamp provenance;
- reconnect/reacquire origin.

Segment IDs within one v2 session are contiguous starting at zero. One session
contains at most 32 complete segment records. Hitting that storage limit triggers
session rollover before another segment is published; it MUST NOT permanently
stop reconnect solely because the old session already has 32 segments.

### 13.5 Timestamp provenance

Basic uses `time.monotonic_ns()` sampled once per delivered serial-read chunk.
Enhanced uses the RP2350 timer sampled once per firmware UART event before USB
delivery. Timestamps are normalized to a segment-local origin and MUST NOT be
compared across segments.

Neither backend may infer per-byte timing.

Wall-clock RFC 3339 fields describe host lifecycle/action times only and are not
precision UART timing.

### 13.6 Unexpected disconnect and reconnect

An unexpected disconnect:

1. durably closes the current segment when possible;
2. records a connection event;
3. changes state to `reconnecting`;
4. starts a fresh host-monotonic reconnect deadline using the profile snapshot;
5. does not stop the active session merely because the old physical connection
   ended;
6. creates a new segment if a replacement source is safely identified and opened
   before the reconnect deadline.

`reconnect_timeout_s` defaults to 5.0 s and MUST be a finite numeric value in the
inclusive range 0.1..60.0. Booleans are invalid.

If reconnect fails before the deadline, active bounded operations terminate with
a connection-related outcome, the active evidence session terminalizes failed
with `reconnect_timeout`, and the service becomes `disconnected`. A later manual
reacquire/start creates a new native session.

### 13.7 Native USB console behavior

A DUT using a native USB serial console may disappear when the DUT resets. For a
profile declared `native_usb_console`, an expected reset-triggered disconnect is
still a real segment boundary.

Device Core MAY automatically reconnect using the configured safe selector. A
successful reconnect creates a new segment. Evidence produced by firmware before
USB re-enumeration is physically unobservable through that console and MUST NOT
be invented or presented as lossless continuity.

The session continuity summary records the resulting observation gap. A bounded
Monitor/Interact/boot-test operation may continue across the reconnect only while
both its own deadline and the reconnect deadline remain valid.

### 13.8 Explicit release

`release` is an intentional ownership transfer, not an unexpected disconnect.
A successful release MUST:

1. record the release request/intent before closing the backend;
2. stop publishing new physical RX only after all already-received admitted
   evidence has been flushed;
3. close the physical transport;
4. close the current connection segment;
5. record an explicit intentional observation-gap boundary;
6. change state to `released`;
7. suppress automatic reconnect while released.

A release MAY terminate active read-only Monitor operations with outcome
`released`. It MUST NOT silently interrupt an active Interact or in-flight
Control/TX action; such a release is rejected with `operation_active` until the
conflicting action ends.

Live `follow` subscribers may remain connected to the service and observe the
release marker; they receive no UART evidence while the transport is released.

### 13.9 Reacquire

`reacquire` is valid only from `released` or `disconnected`. It uses the same
resolved profile unless the service has explicitly loaded a new profile while no
backend is owned.

A successful reacquire creates a new connection segment. If it follows an
explicit release in the same active session, the session remains the same and
the intentional unobserved interval remains explicit. If the old session was
terminalized by restart, persistence failure, reconnect timeout, or profile
change, reacquire creates a new session.

### 13.10 Service shutdown and restart

Clean service shutdown terminalizes the active v2 session with
`end_reason: "service_shutdown"` after flushing admitted evidence and closing the
backend.

On startup, a stale v2 `active` session from a prior process is never silently
resumed. Recovery marks it `abandoned` with bounded recovery metadata. A later
connection starts a new session.

## 14. Continuous Evidence Ingestion

### 14.1 One authoritative reader

While connected, exactly one background reader owns backend receive. It runs
continuously even when there is no bounded Monitor/Interact operation and no live
CLI subscriber.

The old behavior "drain while idle but discard" is invalid for native v2.

### 14.2 Ambient UART is evidence

Every quota-admissible UART receive event delivered by the backend while
DUTchMate owns the connection MUST enter the authoritative evidence stream,
including bytes that arrive:

- before a Monitor starts;
- after an Interact completes;
- while all clients are idle;
- while a different read-only retrieval request runs;
- immediately after a reset/control action;
- during reconnect segments after the new backend is established.

### 14.3 Single evidence serialization order

Device Core MUST serialize admitted primary evidence units through one session
recorder that assigns a strictly increasing session-local `evidence_seq`.
Primary units include at least:

- UART RX events;
- UART TX attempts/results;
- Control attempts/results;
- connection/reconnect/release/reacquire events;
- operation lifecycle events;
- Enhanced buffer telemetry.

`evidence_seq` provides deterministic observed/recorded ordering. It does not
claim simultaneous physical timing across different clocks.

### 14.4 Persist before success publication

A client-visible operation result MUST NOT claim success for evidence/action
that could not be admitted to durable session storage.

In particular:

- a UART/Control attempt record is durably admitted before the physical action is
  dispatched;
- a terminal action/result record is admitted after backend completion;
- a Monitor/Interact match is not returned until the matched UART evidence and
  terminal operation record are durably committed;
- if the attempt cannot be stored, the action MUST NOT be dispatched;
- if the process dies after an attempt but before a result, retrieval reports an
  unresolved/unknown outcome rather than fabricating success or failure.

### 14.5 Internal queue overflow

Device Core MUST NOT silently drop normalized backend events because an internal
recorder/subscriber queue is full. A local ingestion overflow is a fatal evidence
fault: mark the session evidence quality explicitly, fail the active session when
possible, stop state-changing operations, and close/relinquish the backend rather
than continue claiming authoritative recording.

Slow `follow` subscribers are not authoritative. Their client-view buffers may be
bounded; a subscriber that falls behind must receive a cursor/gap indication and
backfill from durable evidence rather than causing physical evidence loss.

## 15. Native Session Schema v2

### 15.1 Meaning

A v2 session is a bounded durable interval of DUTchMate ownership/evidence. It is
not equivalent to one Monitor or Interact request.

One v2 session may contain:

- ambient UART RX;
- many Monitor operations;
- many Interact operations;
- standalone UART TX actions;
- many configured Control actions;
- multiple reconnect segments;
- explicit release/reacquire gaps;
- live follow/console activity;
- Enhanced buffer telemetry;
- derived pattern detections.

### 15.2 Required artifacts

A native v2 session directory under `.dutchmate/sessions/` contains:

```text
metadata.json
uart_raw.log
uart_events.jsonl
operation_events.jsonl
hardware_events.jsonl
connection_events.jsonl
detected_patterns.json
```

An active session also contains internal `.terminal-reserve`. The reserve is not
a user evidence artifact and is removed during terminalization.

The store root may also contain `baseline.json`, which is project-store metadata,
not session evidence.

### 15.3 Schema versioning

New sessions written after this migration MUST use immutable integer
`schema_version: 2`.

The session directory is one versioned evidence unit; individual event records
do not carry independent schema versions.

Existing schema v1 sessions remain read-only compatible. Recognized unversioned
legacy sessions remain compatibility version 0. Device Core MUST NOT rewrite,
upgrade, or infer new v2 facts into historical v0/v1 evidence during startup.

### 15.4 Session lifecycle

V2 states are:

```text
active
completed
failed
abandoned
```

A terminal session never becomes active again.

Common successful terminal reasons include:

```text
service_shutdown
explicit_detach
profile_changed
rollover_size
rollover_segments
```

Common failed reasons include:

```text
reconnect_timeout
backend_input_error
persistence_error
local_ingestion_overflow
```

A session rolled over for size/segment bounds is `completed`, not `truncated`.
Its successor/predecessor linkage explains continuity.

### 15.5 Required metadata

`metadata.json` MUST contain at least:

- `schema_version: 2`;
- `session_id`;
- `started_at`;
- `state`;
- nullable `ended_at`;
- nullable `end_reason`;
- nullable bounded `error` with `code`, `detail`, `detail_truncated`;
- `profile_name` when configured;
- `profile_digest_sha256`;
- bounded effective profile snapshot;
- `backend_mode`;
- accepted reconnect policy snapshot;
- storage accounting;
- evidence-quality summaries;
- line-processing summary;
- continuity/observation-gap summary;
- operation summary counts;
- 1..32 complete contiguous segment objects while a connected segment exists;
- nullable predecessor/successor session IDs for rollover chains.

Metadata MUST remain compact UTF-8 JSON and is capped at 262144 bytes.

### 15.6 Evidence records and global ordering

Every primary JSONL evidence record contains:

- `evidence_seq`;
- an event `type`;
- applicable `segment_id`;
- applicable normalized `timestamp_us`;
- bounded RFC 3339 host `recorded_at`;
- type-specific bounded fields.

Sequence values start at zero and increase by exactly one for every admitted
primary evidence unit in that session. Derived detected-pattern records reference
their source UART `evidence_seq` and do not create a second primary physical
event order.

### 15.7 UART artifacts

`uart_raw.log` contains exact admitted RX bytes only, concatenated in UART-event
admission order. It contains no TX bytes.

Each `uart_events.jsonl` record contains at least:

- `evidence_seq`;
- `segment_id`;
- normalized `timestamp_us`;
- `channel`;
- `data_b64`;
- half-open `raw_offset_start` / `raw_offset_end` into `uart_raw.log`.

The decoded `data_b64` MUST equal the exact raw byte range.

### 15.8 UART TX evidence

Every standalone or Interact/console TX produces at least:

1. `uart_tx_attempt` in `operation_events.jsonl` before dispatch;
2. `uart_tx_result` after completion when the process remains able to record it.

The attempt includes exact transmitted `data_b64`, byte length, owning
operation ID when any, transformation metadata for text convenience, and the
active segment/session context.

The result includes accepted byte count when known and terminal transport status.
An attempt without a matching result is explicitly unresolved/unknown.

### 15.9 Control evidence

Configured hardware/serial-line control produces attempt/result records in
`hardware_events.jsonl`. Records include semantic role, resolved physical
provider/channel or serial-line action identifier, bounded action parameters,
and result. Enhanced acknowledgements may additionally retain raw firmware
`device_timestamp_us`; when safely normalizable to the current segment clock,
Device Core may also record normalized `timestamp_us`.

### 15.10 Connection evidence

`connection_events.jsonl` stores bounded lifecycle facts including:

- connected/segment opened;
- unexpected disconnect;
- reconnect started/succeeded/failed;
- explicit release;
- reacquire started/succeeded/failed;
- segment closed;
- rollover linkage where applicable.

Released intervals and native-USB re-enumeration gaps are explicit unobserved
intervals, not fabricated UART silence.

### 15.11 Operation evidence

`operation_events.jsonl` stores lifecycle records for bounded Monitor, Interact,
and composite boot-test operations. Each operation has a unique ID and at least:

- operation type;
- start record with accepted validated request parameters;
- start evidence cursor;
- terminal record;
- terminal outcome;
- end evidence cursor;
- one or more evidence ranges if the operation crosses session rollover;
- matched completion condition/reference where applicable;
- bounded error data where applicable.

Operation parameters are typed fields; arbitrary payload/pattern text MUST NOT
be copied into an unbounded display `command` string.

### 15.12 Evidence cursor and range

The public logical cursor is opaque to clients but represents a precise position
in durable evidence. Internally it is sufficient to identify a session and the
next `evidence_seq` position.

An operation result references one or more half-open ranges:

```text
(session_id, start_evidence_seq, end_evidence_seq_exclusive)
```

An operation MAY cross connection segments and MAY cross session rollover. If it
crosses rollover, the successor session records an `operation_continued` event
for the same operation ID and the terminal result contains multiple ranges.

### 15.13 Storage budget and rollover

`sessions.max_size_mb` remains a positive integer in MiB; booleans are invalid.
Default 50 means 52428800 evidence bytes.

For v2, reaching the per-session evidence budget MUST normally trigger rollover,
not truncation and not stopped acquisition:

1. preflight the complete next primary evidence unit;
2. if it fits, admit it atomically;
3. if it would exceed the current session budget, terminalize the current session
   as `completed/rollover_size` before that unit;
4. create/publish a linked successor session while preserving physical ownership;
5. admit the complete unit to the successor;
6. continue recording.

No evidence unit may be intentionally cut to fit.

The minimum allowed budget MUST be large enough for the maximum schema-valid
single evidence unit plus metadata/terminal reserves. Configuration that cannot
meet that invariant is invalid before connection.

The same principle applies to the 32-segment metadata bound: roll over before a
33rd segment is published.

### 15.14 Evidence accounting

The evidence budget counts the logical byte lengths of:

- `uart_raw.log`;
- `uart_events.jsonl`;
- `operation_events.jsonl`;
- `hardware_events.jsonl`;
- `connection_events.jsonl`;
- `detected_patterns.json`.

It excludes:

- `metadata.json`;
- `.terminal-reserve`;
- temporary atomic-write/recovery files;
- store-level `baseline.json`;
- future generated reports.

JSONL uses compact deterministic UTF-8 plus exactly one LF per record.
`detected_patterns.json` starts as `[]\n`.

### 15.15 Metadata terminal reserve

The session store MUST preserve the existing terminal-safety principle:

- create, physically allocate, and fsync a 262144-byte `.terminal-reserve` before
  publishing active ownership;
- ensure active metadata plus worst-case bounded terminal fields fit in the
  262144-byte metadata cap;
- on terminalization, remove the reserve, write/fsync compact terminal metadata,
  atomically replace `metadata.json`, and fsync the directory;
- reserve allocation or required persistence failure is a `persistence_fault`.

### 15.16 Rollover atomicity

Rollover MUST NOT create an unrecorded physical RX interval. The recorder owns
rollover coordination while the backend reader continues feeding a bounded
backpressure-safe path. The successor session must be ready before the first unit
that does not fit the predecessor is committed.

If successor creation fails, Device Core enters a persistence fault, stops
state-changing operations, closes the backend, and reports evidence uncertainty
rather than discarding bytes and continuing silently.

### 15.17 Startup recovery

Startup scans native sessions before backend ownership. Stale v2 `active`
metadata becomes `abandoned`; no previous operation or connection is resumed.
Unmatched TX/Control attempts remain explicit unknown outcomes.

Recovery MUST NOT invent disconnect bytes/events that were never durably
observed.

### 15.18 Retention

Retention runs after startup recovery, v2 rollover, and terminal transitions.
It deletes oldest eligible terminal sessions by ascending `(started_at,
session_id)` until `sessions.max_count` is met.

Protected sessions include:

- the active session;
- sessions referenced by an active operation spanning rollover;
- the valid baseline session;
- sessions held by in-progress readers.

If protection prevents enforcement, status reports `retention_blocked`; no
protected evidence is deleted.

Recognized compatibility sessions count toward the limit but retain the safety
rules defined for their schema. Unknown/corrupt versions stop destructive
retention rather than being guessed.

## 16. Evidence Quality

Evidence-quality facts MUST remain separate rather than collapsing into one
"good/bad" flag.

### 16.1 UART loss observer

The UART loss observer retains these semantics:

| Backend/result | `loss_status` | `observation_scope` | `dropped_bytes` |
|---|---|---|---:|
| Basic default | `not_observable` | `null` | `null` |
| Enhanced with no reported helper overflow | `none_reported` | `debug_helper_rx_buffer` | `0` |
| Enhanced with overflow | `loss_reported` | `debug_helper_rx_buffer` | known count or `null` |

`none_reported` means only that the named observer reported no loss. It MUST NOT
be presented as proof that the entire UART path was lossless.

### 16.2 Continuity

Continuity separately records connection observation gaps, including:

- unexpected disconnect/reconnect gaps;
- expected native-USB reset/re-enumeration gaps;
- intentional release/reacquire gaps.

A gap describes a period DUTchMate could not observe the physical stream. It is
not a dropped-byte count unless a trusted observer supplies one.

### 16.3 Local recording

Local persistence/ingestion failures are separate from backend loss. If Device
Core cannot maintain the authoritative record, it must fault/close rather than
continue silently.

### 16.4 Derived line completeness

Derived line processing status remains independent of raw UART preservation and
physical UART loss.

## 17. Line Reconstruction and Pattern Detection

### 17.1 Authoritative bytes and lossy text

Raw UART bytes are authoritative. Text is a lossy UTF-8 projection using
replacement characters for invalid sequences.

Line reconstruction is independent per `(segment_id, channel)` and MUST NOT join
across reconnect/rollover segment boundaries.

### 17.2 Derived line bound

A normal complete or partial derived line contains at most 65536 exact bytes,
including LF when present.

On byte 65537 of one physical line, Device Core:

1. preserves the UART event/raw bytes normally;
2. stops buffering the derived line payload;
3. marks `line_processing.status = "limit_exceeded"`;
4. counts bytes in constant memory until LF or segment/session boundary;
5. emits one bounded `line_limit_exceeded` derived/session fact;
6. never pattern-matches or invents truncated text for that oversized physical
   line;
7. resumes normal assembly after LF.

Raw evidence is unaffected by this derived limit.

### 17.3 Default failure patterns

Phase 1 default failure detectors remain:

```text
ERROR
ASSERT
PANIC
HardFault
```

`BOOT_OK` is a success marker and is excluded from `first_error`.

The global detector processes complete bounded lines continuously, including
ambient lines outside explicit operations. `first_error` for a v2 session is the
earliest stored default failure match by `evidence_seq` and then line order, not
by comparing timestamps across segments.

### 17.4 Requested completion conditions

Monitor/Interact requested text conditions use Phase 1 matching semantics:

- case-sensitive literal substring;
- no regex/glob/escape interpretation;
- each pattern encodes to 1..256 UTF-8 bytes;
- CR and LF are forbidden in a pattern;
- at most 8 completion conditions per operation;
- each optional condition name is 1..64 UTF-8 bytes with no Unicode `Cc` and no
  edge Unicode whitespace.

Requested matchers are operation-local. They begin with an empty local line
buffer at the operation start cursor and MUST NOT search earlier durable history
or pre-cursor partial-line state.

If multiple conditions match, select the earliest matching line by evidence
order, then the earliest byte offset within that line, then request-list order as
a deterministic tie-breaker.

Oversized physical lines are excluded from requested matching and the operation
result exposes the relevant line-processing limitation.

### 17.5 Match evidence

A detected match record references:

- source UART `evidence_seq`;
- segment/channel;
- normalized timestamp;
- line/event byte boundaries;
- matched pattern/condition;
- exact raw match offsets;
- a bounded exact raw excerpt of at most 4096 bytes plus lossy text and base64;
- whether the excerpt was truncated.

## 18. Common Bounded Operation Contract

### 18.1 Operation identity

Every bounded Monitor, Interact, and composite boot-test has a unique operation
ID. The ID and accepted parameters are recorded before the operation can produce
a successful response.

### 18.2 Bounds

Every autonomous wait is finite. Phase 1 timing bounds are finite numbers in
seconds; booleans are invalid.

For duration-based observation:

```text
0 < duration_s <= 300
```

For condition waits:

```text
0 < timeout_s <= 300
```

Validation occurs before capability checks, connection checks, physical actions,
or operation publication.

### 18.3 Completion modes

A Monitor/Interact completion request uses exactly one of:

1. **duration mode** — complete after accepted `duration_s`;
2. **conditions mode** — wait for one of 1..8 accepted conditions until
   `timeout_s`.

An operation with no finite completion bound is invalid.

### 18.4 Terminal outcomes

The normalized Phase 1 operation outcome vocabulary is:

```text
elapsed
matched
timeout
disconnected
released
cancelled
error
```

`elapsed` is normal duration completion. `timeout` means the finite condition
deadline expired without a match; it is an operation result, not an HTTP
transport failure. `disconnected` means reconnection could not preserve the
operation before its deadline. `released` applies when an intentional ownership
transfer terminalizes a read-only operation.

### 18.5 Evidence ranges

Every terminal result includes the operation ID and authoritative evidence range
references. Results also expose the relevant session/segment provenance,
evidence-quality summaries, and requested/matched condition information.

### 18.6 Cancellation

Client/request cancellation does not undo an action already dispatched. If a
bounded Monitor/Interact HTTP request is cancelled while its server operation is
still active, Device Core MUST terminalize that operation as `cancelled` as soon
as safely possible, persist the terminal record, and release its operation lease.
Any TX/Control action already dispatched remains recorded with its real/unknown
result; cancellation never fabricates rollback.

A separate public cancel-by-ID API is not required for Phase 1.

## 19. Monitor

### 19.1 Meaning

Monitor is a bounded read-only observation window over the continuous evidence
stream. Starting/stopping Monitor MUST NOT start/stop backend RX.

### 19.2 Start boundary

Device Core durably records `monitor_started` and establishes the start cursor
before any post-start evidence is eligible for requested completion matching.

### 19.3 Duration Monitor

A duration Monitor completes `elapsed` when the monotonic duration expires.
Quiet UART reads do not extend its deadline.

### 19.4 Condition Monitor

A condition Monitor completes `matched` on the deterministic first requested
match or `timeout` when its deadline expires.

### 19.5 Disconnect behavior

If the backend disconnects, Monitor may remain pending during automatic
reconnect while both:

- its own operation deadline remains valid; and
- the reconnect deadline remains valid.

If the connection safely resumes, Monitor continues with a new segment and the
same operation ID. It never joins a physical line across segments.

## 20. UART Transmission

### 20.1 Byte-first semantics

Device Core fundamentally transmits exact bytes. Text is a convenience input
that is transformed explicitly before validation/dispatch.

### 20.2 Public payload forms

The service/core Phase 1 TX request accepts exactly one of:

- `data_b64` for arbitrary bytes; or
- `text` plus explicit `line_ending`.

`line_ending` is one of:

```text
none
lf
cr
crlf
profile_default
```

`profile_default` resolves to the validated profile setting. No other invisible
payload transformation is permitted.

The response/evidence exposes the exact final `data_b64` bytes actually
requested for transmission.

### 20.3 Size bound

The final transformed TX payload MUST be 1..1024 bytes. Validate after explicit
text transformation and before capability, policy, connection, operation-lock,
or backend dispatch checks.

### 20.4 Auditing

Every send attempt is recorded before dispatch. Every available result is
recorded afterward. TX bytes never enter receive-only `uart_raw.log`.

### 20.5 Policy

TX requires effective `uart_send`. Policy-disabled TX returns
`unsupported_capability` with structured context identifying
`hardware.uart.tx_enabled` as the disabling source.

## 21. Interact

### 21.1 Meaning

Interact is a bounded bidirectional UART operation over the same continuously
recorded stream.

### 21.2 Ordering

A valid Interact executes in this order:

1. validate the complete request and completion bound;
2. acquire the Interact exclusivity lease;
3. durably record `interact_started` and establish its start cursor;
4. durably record `uart_tx_attempt`;
5. dispatch the exact bytes;
6. record `uart_tx_result` when known;
7. continue observing continuously recorded RX evidence after the start cursor;
8. evaluate the accepted completion mode;
9. durably record terminal Interact outcome;
10. return result/evidence references;
11. release the exclusivity lease.

The reader is already active before step 3 and remains active after step 11.

### 21.3 Asynchronous output

Interact MUST NOT fabricate a synthetic clean command response by deleting UART
that appears unrelated. Periodic logs, command echo, warnings, and prompt output
inside the operation window remain real evidence.

### 21.4 Duration Interact

A duration-mode Interact sends once, then observes until `duration_s` expires and
returns `elapsed`.

### 21.5 Condition Interact

A conditions-mode Interact sends once, then returns `matched` on the first
deterministic requested match or `timeout` at the finite deadline.

### 21.6 Disconnect behavior

Interact may remain pending during an automatic reconnect under the same dual
operation/reconnect deadline rule as Monitor. No TX is silently retried after a
disconnect unless a future protocol-specific contract explicitly defines
idempotent retry. The result exposes that the original TX outcome may be unknown
if no result record was obtained.

## 22. Standalone UART Send

Standalone send remains a useful human primitive. It is an audited action, not a
session-creating workflow.

It uses the same payload validation, TX policy, exact-byte evidence, and action
serialization as Interact. It does not create a completion matcher or finite RX
window; ambient RX continues to be recorded independently.

There is no Phase 1 `force` bypass. Observation does not own the reader, so a
read-only Monitor/follow is not itself a reason to reject send. Sends are
rejected only for actual action/exclusivity conflicts, policy/capability,
connection state, or backend/persistence errors.

## 23. Control

### 23.1 Common semantics

Public Control is semantic, configured, bounded, capability-gated, and audited.
There is no arbitrary raw public pin-level API.

A Control attempt is persisted before physical dispatch. If the attempt cannot
be recorded, Device Core MUST NOT actuate hardware.

### 23.2 Enhanced reset

`reset` resolves exact lowercase role `reset` to an accepted Enhanced control
mapping and uses `pulse_control`.

`pulse_ms` defaults to 100 and MUST be an integer 1..10000 inclusive. Booleans,
fractional values, and out-of-range values are invalid before capability/role or
transport checks.

### 23.3 Enhanced boot mode

`bootloader` maps the configured boot role to active state; `normal` maps to idle
state. `commanded_boot_mode` is the last state successfully commanded by Device
Core, not electrical readback. It becomes unknown when disconnect/safety state
invalidates the command.

### 23.4 GPIO mode override

Runtime Enhanced GPIO mode override retains the existing contract from
`docs/gpio_configuration_semantics.md`. A rejection leaves the previous accepted
state unchanged.

### 23.5 Optional Basic semantic serial-line control

If implemented and advertised, Basic reset/boot through DTR/RTS follows the same
public semantic APIs but resolves through `serial_line_control`, not
`gpio_control`. The action definition must be explicit in the profile and cannot
conflict with flow-control ownership.

## 24. Boot-Test Composite Workflow

Phase 1 retains boot-test as a convenience composite built from the new
primitives rather than as a separate receive architecture.

A boot-test:

1. validates the Monitor completion request and reset parameters;
2. records a boot-test operation start cursor while RX is already active;
3. performs the configured semantic reset as an audited Control action;
4. observes the same continuous evidence stream using Monitor completion rules;
5. returns operation outcome and evidence ranges.

There is no capture gap between reset and observation because acquisition
predates the reset action.

Plain boot-test is reset-only and MUST NOT silently change boot mode. A caller
that needs bootloader mode explicitly selects it, runs the desired test, and
restores normal mode explicitly.

For native USB consoles, reset may intentionally cause disconnect/re-enumeration;
boot-test follows the reconnect semantics defined above and reports the
unobservable gap.

## 25. Concurrency and Arbitration

### 25.1 Physical reader

There is always at most one physical backend reader.

### 25.2 Read-only concurrency

The following MAY coexist:

- continuous recording;
- any number of bounded read-only Monitor operations subject to configured
  resource limits;
- session/log retrieval;
- multiple `follow` subscribers.

A Monitor does not block standalone Control/TX merely because it is observing.

### 25.3 Interact exclusivity

Only one Interact may be active at a time. While Interact is active, other
client-originated UART TX, console TX, and semantic Control actions are rejected
with `operation_active` so the bounded interaction cannot be silently perturbed
by another mutating client.

Read-only Monitor/follow/retrieval may continue.

### 25.4 Action serialization

Outside Interact, standalone TX and Control actions are serialized through one
mutating-action lock. Their persisted attempt order defines dispatch order.

### 25.5 Release exclusivity

Release/reacquire/profile replacement are connection-ownership mutations and are
serialized against TX/Control/Interact. Release may intentionally terminalize
read-only Monitor operations as specified, but never silently steals ownership
from an in-flight mutating action.

## 26. Follow

### 26.1 Semantics

`follow` is a live human view of the authoritative evidence stream. It is not a
physical capture operation and does not create/own a UART reader.

Starting or stopping follow MUST NOT change backend acquisition or session
lifecycle.

### 26.2 Cursor API

The service MUST expose a bounded cursor-based evidence-tail API usable by the
CLI. The concrete HTTP contract is:

```text
GET /dut/evidence
```

Query parameters:

- optional opaque `cursor`;
- `limit`, integer 1..500, default 100;
- `wait_s`, finite 0..30, default 1.0.

With no cursor, the response establishes a cursor at the current durable tail
and returns no historical evidence by default. Historical logs are retrieved
through session/log APIs.

With a cursor, the service returns admitted primary evidence after that position,
up to limits, plus `next_cursor`. Long-polling may wait up to `wait_s` for new
evidence.

The response is capped at 262144 compact UTF-8 bytes and never slices an evidence
unit. It reports omitted whole records if the byte cap is hit.

If a cursor points into a session that retention has deleted and no safe
successor position can be established, return `cursor_expired` rather than
silently jumping forward.

The cursor follows explicit v2 rollover successor links and can therefore keep a
CLI follow session alive across normal storage rollover.

### 26.3 Follow projections

UART RX projections include exact `data_b64`, lossy display text, evidence
sequence, segment/channel/timestamp provenance, and session ID. Connection,
action, and operation markers are bounded projections and MUST NOT echo arbitrary
untrusted exception text.

## 27. Console

Phase 1 `console` is a line-oriented human UART console built entirely through
Device Core Service APIs. It is not a raw local serial terminal and does not
open the port directly.

The CLI console:

1. starts the same cursor-based live evidence view used by `follow`;
2. reads human input lines;
3. sends each line through the normal audited standalone UART-send API using an
   explicit/profile-default line ending;
4. displays TX/RX/action markers from authoritative service evidence;
5. exits on EOF/Ctrl-C without stopping physical acquisition.

Console requires effective `uart_send`. Phase 1 does not promise full terminal
escape-sequence handling or character-by-character TTY emulation.

Console TX is rejected while an Interact operation holds exclusivity.

## 28. Device Core Service

### 28.1 General

The service is a persistent local FastAPI process. It owns the selected backend,
active v2 session, connection lifecycle, action arbitration, and durable evidence
recorder.

Without a usable selected backend it may run in `disconnected` state and still
serve historical retrieval/configuration-safe endpoints.

### 28.2 Required endpoints

Phase 1 requires:

```text
GET    /status
GET    /dut/evidence
POST   /dut/monitor
POST   /dut/interact
POST   /dut/uart/send
POST   /dut/boot-test
POST   /dut/reset
POST   /dut/boot-mode
POST   /gpio/mode
POST   /connection/release
POST   /connection/reacquire
GET    /sessions
GET    /sessions/{id}
GET    /sessions/{id}/compare
GET    /dut/logs
POST   /sessions/{id}/baseline
DELETE /sessions/{id}/baseline
```

Legacy `/dut/capture` and `/dut/wait-pattern` MAY exist temporarily during
repository migration but are not the target Phase 1 contract. They MUST be
implemented only as compatibility wrappers over Monitor semantics if retained;
they may not own separate readers/session lifecycles.

### 28.3 Error envelope

All JSON errors use:

```json
{
  "ok": false,
  "error": "<code>",
  "detail": "...",
  "detail_truncated": false,
  "context": {}
}
```

Canonical Phase 1 public errors are:

- `invalid_argument` / HTTP 400;
- `not_found` / HTTP 404;
- `cursor_expired` / HTTP 410;
- `unsupported_capability` / HTTP 409;
- `not_configured` / HTTP 409;
- `operation_active` / HTTP 409;
- `invalid_connection_state` / HTTP 409;
- `invalid_session_state` / HTTP 409;
- `unsupported_session_schema` / HTTP 409;
- `persistence_fault` / HTTP 500;
- `internal_error` / HTTP 500;
- `backend_input_error` / HTTP 502;
- `hardware_fault` / HTTP 502;
- `timeout` / HTTP 502 only for backend action/transport timeout, not a normal
  Monitor/Interact completion timeout;
- `service_unavailable` / HTTP 503 for no usable backend, reconnect/reacquire
  failure, or ambiguous discovery.

Diagnostic detail uses one shared bounded sanitized projection: non-empty,
1..1024 UTF-8 bytes after projection, control-safe, with `detail_truncated`
always present. Arbitrary wire frames, UART payloads, secrets, or exception dumps
MUST NOT be copied into detail/context.

### 28.4 Capability error context

`unsupported_capability` includes:

- operation;
- backend mode;
- required capabilities;
- effective available capabilities;
- raw backend capabilities;
- capabilities disabled by policy and their configuration source.

`not_configured` includes operation, required role, and current role state.

### 28.5 Status

`GET /status` includes at least:

- `connection_state` and derived `connected`;
- active backend mode and current exact port when any;
- raw `backend_capabilities`;
- effective `capabilities`;
- capability-policy projection;
- active profile name/digest and bounded effective UART settings;
- DTR/RTS management/open-provenance summary where applicable;
- nullable active v2 `session_id`;
- zero or more active bounded operation summaries;
- nullable reconnect/reacquire remaining time;
- Enhanced GPIO/control mapping states;
- nullable `commanded_boot_mode`;
- retention/persistence diagnostics;
- current evidence-quality summary.

Status MUST distinguish `released` from unexpected `disconnected`.

### 28.6 Monitor request/response

`POST /dut/monitor` accepts one completion mode as defined in section 18. It
requires effective `uart_receive` and a usable connected/reconnecting state.

A normal `matched`, `elapsed`, or `timeout` completion returns HTTP 200 with
`ok: true`, operation ID, outcome, accepted completion parameters, evidence
ranges, matched condition when any, and evidence-quality/provenance summaries.

### 28.7 Interact request/response

`POST /dut/interact` accepts one exact payload form plus one completion mode. It
requires effective `uart_receive` and `uart_send` and Interact exclusivity.

Normal match/elapsed/condition-timeout returns HTTP 200 with operation ID,
outcome, exact TX bytes, TX result when known, matched condition when any,
evidence ranges, and quality/provenance summaries.

### 28.8 UART send

`POST /dut/uart/send` uses the common payload contract, records attempt/result,
and returns the exact final transmitted bytes plus accepted byte count/status.
It creates no separate session.

### 28.9 Control endpoints

`POST /dut/reset`, `POST /dut/boot-mode`, and `POST /gpio/mode` preserve the
validated role/electrical contracts defined earlier. Every standalone action is
recorded in the active v2 session.

### 28.10 Release/reacquire

`POST /connection/release` and `/connection/reacquire` implement section 13.
Release succeeds only after evidence/action ordering is durable and returns the
session/segment boundary it created. Reacquire returns the new segment and
current connection state.

### 28.11 Recent logs

`GET /dut/logs` accepts optional `session_id` and integer `lines`, default 300,
range 1..1000. Explicit selection wins; otherwise select the active v2 session,
then newest compatible terminal session.

For v2, replay uses a stable durable snapshot of `uart_events.jsonl`, reconstructs
per-segment/channel bounded lines, and returns newest requested complete lines
oldest-to-newest plus partial/oversized descriptors using the line contract in
section 17.

The compact body is capped at 262144 bytes; omit oldest whole returned records
with explicit omission counts rather than slicing evidence.

V1 replay remains read-only compatible according to its historical schema.
Unknown/malformed required session data returns the appropriate schema or
persistence error rather than silently selecting another session.

### 28.12 Session list/detail

`GET /sessions` uses `limit` default 50, range 1..100, and a stable opaque
exclusive cursor ordered descending by `(started_at, session_id)`.

V2 list items contain bounded summary fields only: lifecycle, profile/backend,
start/end, rollover chain, segment count, evidence quality, line-processing,
operation counts, storage/retention facts, baseline, and compact `first_error`.
They contain no full UART/event arrays.

`GET /sessions/{id}` validates ID syntax, returns bounded metadata/detail,
artifact manifest, operation/action counts, unresolved action-attempt counts,
quality summaries, and `first_error` excerpt. Full UART/event arrays are not
embedded.

V1/v0 compatibility remains read-only and explicitly discriminated by
`schema_version`/`compatibility`; unknown versions are never guessed.

### 28.13 Baseline and compare

The store retains exactly one optional project-wide baseline pointer.

A new v2 baseline designation requires a terminal completed session with:

- no local evidence truncation/loss;
- no `loss_reported` backend integrity;
- no unexpected or intentional observation gap if the baseline is intended for
  whole-session comparison.

Basic `not_observable` UART loss remains eligible but must remain visible as a
warning. Existing compatible v1 baseline behavior may remain readable.

Comparison stays bounded and evidence-based. It may compare log/pattern identity
across backend modes, but timing is comparable only when the relevant sessions
have one uninterrupted segment and identical timestamp provenance fields.

## 29. CLI

### 29.1 General

The CLI is a thin service client. It MUST NOT open the physical serial device for
normal DUTchMate workflows.

Human-facing CLI commands are the first Phase 1 acceptance surface.

### 29.2 Required commands

The final Phase 1 CLI provides concepts equivalent to:

```text
dutchmate status

dutchmate follow

dutchmate console

dutchmate monitor --seconds <duration>
dutchmate monitor --until <pattern> --timeout <seconds>

dutchmate interact <text> --line-ending <none|lf|cr|crlf> \
    --until <pattern> --timeout <seconds>

dutchmate send <text> --line-ending <none|lf|cr|crlf|profile_default>

dutchmate reset [--pulse-ms N]
dutchmate boot-mode <normal|bootloader>
dutchmate boot-test ...
dutchmate gpio mode ...

dutchmate release
dutchmate reacquire

dutchmate sessions ...
dutchmate logs ...
dutchmate baseline ...
dutchmate compare ...
```

Exact Typer spelling may preserve existing command groups, but the semantics
must match this specification.

### 29.3 Follow behavior

`dutchmate follow` starts at the current durable tail unless explicitly asked for
historical lines through a separate option/API. It prints live UART RX and
bounded lifecycle/action markers. Ctrl-C exits only the view; Device Core keeps
recording.

### 29.4 Console behavior

`dutchmate console` combines follow plus line-oriented audited send. It never
owns the serial port. Ctrl-C exits the console client only.

### 29.5 Text line endings

CLI text TX always makes line-ending choice visible. It MUST NOT silently append
LF merely because a command is named `send` or `interact`.

The profile default is allowed only when explicitly selected or documented as
the command default and is still returned in the response as the resolved
transformation/exact bytes.

### 29.6 Error handling

CLI preserves the service error code and useful bounded detail. It must clearly
distinguish:

- normal Monitor/Interact `timeout` outcome returned with `ok: true`;
- backend action timeout returned as an error;
- released/disconnected state;
- unsupported vs unconfigured capabilities;
- cursor expiry;
- persistence/evidence fault.

## 30. Package/Ownership Boundaries

The exact file layout may be refactored, but ownership must remain equivalent to:

```text
apps/
  cli/          human CLI client only
  service/      service/API/process lifecycle; owns one Device Core runtime
  mcp_server/   Phase 2 client of service semantics

core/src/dutchmate_core/
  backends/          normalized backend contracts + Basic/Enhanced adapters
  profile/           DUT Profile parsing/resolution/provenance
  evidence/          continuous recorder, cursors, derived views
  operations/        Monitor / Interact / Control orchestration
  connection/        ownership/reconnect/release/reacquire lifecycle
  gpio_config/       Enhanced role/mode configuration semantics
  session_store/     v2 persistence, compatibility readers, retention/baseline
  log_processing/    bounded line/pattern logic

hardware/
  firmware/      RP2350/Pico 2 helper firmware
  protocol/      versioned Enhanced protocol schemas/examples/fixtures
  pcb/           current hardware workspace and preserved design records
```

Device Core MUST NOT import FastAPI, Typer, MCP, or AI-provider frameworks.

## 31. Testing Requirements

Any workflow exposed through the CLI must pass, in order:

1. Device Core unit tests with fake Basic/Enhanced backends;
2. session/evidence persistence tests;
3. Device Core Service integration tests;
4. CLI tests against the service API;
5. real hardware acceptance when physical behavior is involved.

### 31.1 Shared continuous-evidence tests

At minimum test:

- exactly one backend reader remains active while connected;
- idle UART is persisted rather than discarded;
- UART emitted with no Monitor/Interact client is retrievable later;
- an Interact completes and a HardFault emitted 30 seconds later is still stored
  in the same active evidence session unless rollover/ownership termination
  occurred;
- a reset action performed before a later Monitor cannot lose early boot bytes
  merely because Monitor had not started;
- start/stop follow does not change backend acquisition;
- slow follow subscriber behavior cannot drop authoritative stored evidence;
- all primary evidence receives contiguous increasing `evidence_seq`;
- attempt records are durable before mutating dispatch;
- unresolved attempts survive restart as unknown rather than fabricated results;
- no competing physical reader is introduced by Monitor, Interact, follow, or
  console.

### 31.2 Session v2 tests

At minimum test:

- new writes use schema version 2 only;
- existing v1 and recognized v0 remain read-only without automatic migration;
- active creation reserves terminal metadata space before ownership publication;
- process restart marks stale active v2 sessions abandoned;
- continuous evidence session contains multiple operations/actions;
- size equality is admitted;
- the next whole evidence unit triggers `rollover_size`, linked successor
  creation, and whole-unit admission in the successor without truncation;
- failure to create the successor becomes persistence fault and closes ownership;
- 32 segments fit; another required segment triggers `rollover_segments` and a
  new session rather than permanent reconnect failure;
- active operations crossing rollover retain one operation ID and multiple
  evidence ranges;
- retention protects active sessions, baseline, active-operation ranges, and
  in-progress readers;
- corrupt/unknown schema stops destructive retention;
- metadata always remains under 262144 bytes with worst-case terminal fields.

### 31.3 Raw UART and line tests

Retain/extend coverage for:

- invalid UTF-8 raw preservation;
- event split lines;
- exact raw offsets/base64 equivalence;
- independent segment/channel buffers;
- no line joining across reconnect/rollover;
- 65536-byte derived-line boundary;
- byte 65537 oversized behavior;
- oversized line termination/trailing descriptors;
- post-LF recovery within the same UART event;
- default failure patterns;
- exact raw match offsets/excerpts;
- continuous `first_error` detection on ambient logs.

### 31.4 Monitor tests

At minimum:

- duration accepts positive fractional values and 300 exactly;
- invalid duration/timeout is rejected before connection/operation/persistence
  side effects;
- condition patterns validate UTF-8 byte length/CR/LF/name/count;
- operation-local matching never searches pre-start history;
- a pre-cursor partial line does not become a requested match merely by
  completing after operation start;
- deterministic multiple-condition tie-break rules;
- condition timeout is HTTP-success operation outcome `timeout`;
- disconnect/reconnect can continue one Monitor within both deadlines;
- failed reconnect produces deterministic disconnected outcome/evidence.

### 31.5 UART send and Interact tests

At minimum:

- TX policy defaults false;
- effective capability filtering does not mutate raw backend capabilities;
- `data_b64` and text payload forms are mutually exclusive;
- explicit `none/lf/cr/crlf/profile_default` transforms produce exact expected
  bytes;
- no silent LF append exists;
- final 1/1024 byte payloads accepted; empty/1025 rejected before dispatch;
- Basic short writes retry in order;
- Enhanced firmware validates decoded payload bounds;
- every attempt precedes dispatch in durable evidence;
- every available result is recorded;
- TX never appears in `uart_raw.log`;
- standalone send is allowed during read-only Monitor/follow when no mutating
  conflict exists;
- `force` is absent from the target contract;
- one Interact holds exclusivity against other TX/Control/console TX;
- Interact start cursor is established before TX attempt;
- async unrelated output inside Interact remains evidence;
- duration and condition completion modes work;
- no automatic TX retry occurs across disconnect;
- operation result exposes exact TX bytes and evidence ranges.

### 31.6 Follow/console tests

At minimum:

- initial no-cursor follow establishes current tail rather than replaying all
  history;
- cursor paging/long-poll preserves order across session rollover;
- byte cap omits whole records only;
- retention-deleted cursor returns `cursor_expired`;
- Ctrl-C/client disconnect does not stop physical recording;
- console uses service send API and never direct serial open;
- console TX line ending is explicit and audited;
- console TX is rejected while Interact exclusivity is active.

### 31.7 Connection ownership tests

At minimum:

- release records intent/boundary before closing transport;
- automatic reconnect is disabled while state is `released`;
- released interval is represented as unobserved gap;
- reacquire creates a new segment and resumes same session when allowed;
- service restart while released abandons stale active session and later creates a
  new session;
- unexpected disconnect and explicit release remain distinguishable;
- exact-path reconnect behavior is deterministic;
- native USB selector safely follows path change when identity is unique;
- ambiguous discovery never guesses;
- operation/reconnect deadline precedence is deterministic;
- DTR/RTS requested state/provenance is recorded;
- RTS flow-control conflict is rejected before open/control dispatch.

### 31.8 Basic backend tests

Retain/extend:

- explicit Basic selection without hello;
- Basic host-chunk timestamp provenance;
- Basic loss `not_observable` semantics;
- TX support/policy filtering;
- serial configuration validation and provenance;
- DTR/RTS open behavior through mock serial resource;
- Basic receive-only policy does not falsely claim physical TX high impedance;
- optional `serial_line_control` never appears as `gpio_control`.

### 31.9 Enhanced backend tests

Retain/extend all existing protocol/hardware safety coverage, including:

- wire bounds and malformed frames;
- strict identity byte limits;
- 1..32768 decoded UART frame payload;
- command-response routing while UART/telemetry stays FIFO;
- device timestamp normalization;
- overflow/status telemetry;
- deliberate ring-buffer overflow and loss status;
- GPIO role/mode validation and safe idle behavior;
- generic `pulse_control` / `set_control_state` actions;
- no role metadata on the wire;
- legacy wire command rejection;
- reset/boot exact lowercase role semantics;
- runtime mapping rejection preserving prior accepted state;
- `EVENTn` not advertised in Phase 1.

### 31.10 Persistence fault injection

Inject serialization, short-write, fsync, rename, reserve-allocation, successor
rollover creation, and disk-full failures. Required behavior is explicit
`persistence_fault`/failed evidence state; never deliberately partial JSON/JSONL
and never silent continued ownership after authoritative recording is lost.

## 32. DUT Firmware Validation Fixture

The first real DUT fixture remains a Zephyr application on the existing
first-generation Raspberry Pi Pico 1 and is separate from the RP2350 Debug
Helper firmware.

It provides deterministic modes for:

- successful boot with an unambiguous marker;
- initialization failure with a stable first-error marker;
- silent operation/timeout;
- partial lines and non-UTF-8 bytes;
- burst and sustained UART output;
- UART command/response when TX is enabled;
- asynchronous log output after a command has completed;
- a delayed fault emitted while no bounded operation is running;
- repeated reset/boot-test cycles through Enhanced control;
- native-USB-like disconnect/reconnect behavior in a dedicated fixture/path if
  available.

Validate the same UART semantics first through Basic, then Enhanced. Assertions
below the fixture layer use normalized bytes/events/capabilities/timestamps,
evidence quality, and session artifacts rather than depending on Zephyr log
prefixes except when a test explicitly requests a pattern.

The HIL report records Zephyr version, board, application commit, build ID,
configuration, backend hardware identity, and resulting DUTchMate session IDs.
Firmware flashing remains external.

## 33. Phase 1A Done — Basic

Phase 1A is done only when all of the following are true:

- Device Core continuously acquires and persists UART from a real generic serial
  backend while connected, including ambient UART between operations.
- `dutchmate follow` displays the same stream without owning/stopping the reader.
- bounded Monitor works for duration and literal completion conditions.
- UART TX is disabled by default and works with exact auditable bytes when
  explicitly enabled.
- bounded Interact sends exact bytes and returns matched/elapsed/timeout outcomes
  with durable evidence ranges, without client-managed sleep/read loops.
- the line-oriented DUTchMate console can be used instead of opening the serial
  port directly for ordinary human UART interaction.
- native schema v2 sessions contain ambient RX plus multiple operation/action
  records and preserve effective serial/DTR/RTS provenance.
- size/segment bounds roll to linked sessions without silently stopping capture.
- Basic reports UART loss as `not_observable` unless a trusted observer exists.
- release/reacquire gives external same-port tools an explicit ownership escape
  hatch and records the observation gap.
- unexpected reconnect works through the same v2 evidence model.
- shared fake-backend unit/service/CLI tests pass.
- a real generic USB-UART + Zephyr fixture HIL test proves continuous capture,
  follow, Monitor, TX/Interact, delayed-fault capture, retrieval, and handoff.

Optional Basic DTR/RTS semantic reset/boot control is not required to declare
Phase 1A done, but DTR/RTS open behavior/provenance is required.

## 34. Phase 1B Done — Enhanced

Phase 1B is done only when all Phase 1A host semantics also work through
Enhanced and:

- the RP2350 Debug Helper implements the same normalized receive/send contracts;
- firmware/protocol advertise `uart_receive`, not legacy `uart_capture`;
- generic channel actions use `pulse_control` and `set_control_state`;
- role/DUT-signal metadata remains host-side;
- the accepted Revision A/current-adopted hardware mapping and provisional/current
  adopted logic-device choices are consistent across schematic, firmware, tests,
  and validation records, with leakage, sequencing, isolation, voltage-level,
  and UART signal-integrity measurements recorded for the prototype;
- configured `reset` and `boot` workflows are capability/configuration-gated and
  auditable in v2 evidence;
- boot-test uses continuous pre-existing acquisition and therefore does not lose
  boot bytes because the operation starts after reset;
- Enhanced session segments use RP2350 timestamp provenance;
- buffer status/overflow telemetry is recorded continuously, not only inside a
  finite capture;
- `hardware/validation/phase1_ring_buffer.md` closes the 32 KiB baseline gate as
  accepted or revised with measurement evidence;
- deliberate overflow reports the correct loss observer scope/count;
- `EVENTn` ownership is documented but not advertised/implemented;
- fake Enhanced integration/CLI tests pass;
- a real RP2350 Pico 2 Debug Helper + the same Zephyr DUT fixture demonstrates
  continuous RX, Interact, reset/boot-test, timestamps, telemetry, session v2,
  and retrieval.

## 35. Phase 1 Complete

Phase 1 is complete only when both 1A and 1B are done and all of these shared
criteria hold:

1. **Continuous evidence:** a DUT fault/log emitted while no bounded operation is
   running remains durably retrievable while DUTchMate owns the connection.
2. **No reset/capture race:** reset/control can occur without losing the first
   UART bytes merely because a later Monitor starts afterward.
3. **Live human monitoring:** follow can attach/detach without affecting physical
   acquisition.
4. **Bounded Monitor:** duration/condition observation has explicit deterministic
   outcome, deadline, cursor, and evidence range.
5. **Bounded Interact:** exact TX plus observation completes without client-side
   sleep/poll orchestration and preserves asynchronous output.
6. **Human console:** a developer can perform ordinary line-oriented UART shell
   interaction while Device Core remains the serial owner and evidence remains
   recorded.
7. **Configured Control:** Enhanced reset/boot actions are bounded, auditable,
   role-resolved, and safe; Basic serial-line control, if present, is explicitly
   distinct.
8. **Ownership handoff:** external same-port tools can use explicit
   release/reacquire and the observation gap is represented honestly.
9. **Provenance:** every connected segment preserves effective serial settings,
   backend identity/capabilities, timestamp source, policy, and relevant control
   line behavior.
10. **Evidence quality:** UART loss observation, connection continuity, local
    recording status, line-processing completeness, and storage/retention facts
    remain distinct.
11. **Backend independence:** Basic/Enhanced differences change capability and
    provenance, not the Monitor/Interact/evidence/session architecture.
12. **One physical owner:** no CLI/service workflow introduces a second reader or
    direct serial open while Device Core owns the backend.
13. **Schema discipline:** all new writes are v2; v0/v1 remain explicit read-only
    compatibility; no startup auto-migration invents v2 facts.
14. **Bounded storage without silent gaps:** rollover continues acquisition;
    persistence failure faults ownership rather than silently dropping data.
15. **CLI first:** all Phase 1 acceptance is demonstrated through Device Core,
    service, and CLI without requiring MCP or AI.

Only after these criteria pass should Phase 2 expose the same proven semantics to
coding agents through MCP.
