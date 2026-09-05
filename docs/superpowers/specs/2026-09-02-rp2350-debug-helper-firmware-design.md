# RP2350 Debug Helper Firmware Design

> Status: approved architecture
> Target: non-wireless Raspberry Pi Pico 2, RP2350A Cortex-M33,
> `rpi_pico2/rp2350a/m33`

## Authority And Scope

This design defines firmware ownership and concurrency for the Phase 1B
Enhanced Debug Helper. It does not redesign the host architecture or replace
existing contracts. Normative behavior remains in:

- `docs/phase1_implementation_spec.md`
- `hardware/protocol/v1/*.schema.json`
- `docs/gpio_configuration_semantics.md`
- `docs/ring_buffer_sizing_plan.md`
- `hardware/schematics/revision_a.md`, especially section 10.1

The firmware provides USB CDC NDJSON, identity, UART RX/TX, RP2350 timestamps,
buffer telemetry, a 32 KiB UART RX ring, and generic `CTRL0` through `CTRL3`.
It initializes and reserves `EVENT0` through `EVENT3`, but Phase 1 does not
capture event edges or advertise `gpio_events`.

## Component Boundaries

The Zephyr application contains these cohesive components:

- **Platform:** initializes the RP2350 timer, USB CDC, UART0, GPIO, translators,
  and watchdog using the Revision A mapping.
- **Protocol:** bounds and frames NDJSON, validates v1 commands, and encodes
  exact v1 responses and events. It contains no GPIO or UART policy.
- **Identity:** supplies build-configurable USB identity and immutable `hello`
  values. The Phase 1 development default is VID/PID `2E8A:000A`, manufacturer
  `DUTchMate`, product `Debug Helper`, `device = "dutchmate-rp2350"`, and a
  build-provided firmware version. The USB serial descriptor uses the stable
  board identifier exposed by Zephyr hardware information; it is omitted when
  that API returns no identifier. Production builds must override the
  development VID/PID with an assigned pair.
- **UART ring:** implements the hardware-independent raw-byte ring, timestamp
  descriptors, loss accounting, and transactional drain staging.
- **UART port:** adapts Zephyr UART callbacks to the ring and implements fixed
  Phase 1 DUT UART settings: 460800 baud, 8 data bits, no parity, one stop bit.
- **Control:** owns accepted electrical configuration and state transitions for
  `CTRL0` through `CTRL3`; it never interprets host roles or DUT signal names.
- **Telemetry:** produces internally consistent `buffer_status` and
  `buffer_overflow` records from ring snapshots.
- **Event reservation:** configures EVENT MCU pins as inputs without pulls and
  holds the EVENT translator disabled throughout Phase 1.

Zephyr drivers remain adapters around hardware-independent protocol, ring,
control, and telemetry logic. These inner components receive explicit clock,
UART, GPIO, and transport ports so `native_sim` tests can substitute them.

## Existing Contract Alignment

The normative Phase 1 capability set is:

```text
uart_receive
uart_send
gpio_control
device_timestamp
overflow_telemetry
```

The device-to-host schema, canonical `hello`, host `KNOWN_CAPABILITIES`, parser
fixtures, and tests must include all five values before firmware advertises
them. Keeping these artifacts aligned is contract maintenance, not a new host
architecture.

Host-to-device frames remain limited to 2,048 bytes including LF.
Device-to-host frames remain limited to 65,536 bytes including LF. One complete
JSON object occupies one line. Firmware returns exactly one ordered response
for each complete command frame; the existing host permits only one outstanding
command.

## Concurrency And Interrupt Ownership

Ownership is strict:

| Context | Sole responsibility |
|---|---|
| UART RX ISR/callback | Sample one 64-bit RP2350 microsecond timestamp per received callback; admit its bytes and descriptor; update ring-loss state. |
| USB RX thread | Read CDC bytes, enforce bounded framing, decode one typed command, and submit it to the command queue. |
| Command/control thread | Validate and execute commands serially; own every CTRL configuration/state transition and UART TX request. |
| USB TX thread | Be the sole output scheduler and complete-frame owner; select and encode `hello`, responses, UART events, and telemetry. |
| Driver/timer callbacks | Advance only an already armed frame through a driver-required FIFO callback or timestamp/enqueue compact completion records; never select output, encode JSON, block, or change control state. |

The command/control thread polls normal commands, pulse deadlines, UART TX
completion, and connection-fault signals. Disconnect and fault signals preempt
normal work. Pulse expiry returns to idle in this owner context; no timer
callback mutates GPIO.

The USB TX thread has a response lane and one logical evidence lane. It is the
only context that selects or arms a frame. The Zephyr CDC ACM interrupt API
requires `uart_fifo_fill` to run in its workqueue callback, so that callback may
advance only the immutable frame already owned by the USB TX thread and report
exact acceptance or failure. Responses may interleave with evidence but cannot
reorder UART and telemetry observations.
Every UART descriptor, overflow episode, and telemetry snapshot receives an
internal monotonic observation sequence. The TX scheduler uses that sequence
to preserve evidence FIFO order; it is not added to the v1 wire format.

All queues are statically allocated and bounded. A full command queue applies
USB receive backpressure. UART reception never waits on USB, JSON encoding,
commands, or control transitions. Relative scheduling priority is: hardware
interrupts, command/control safety, USB drain, then periodic telemetry. Exact
Zephyr priority numbers are selected from measured stack and scheduling
evidence rather than fixed by this architecture.

## UART Ring And Telemetry Invariants

The raw RX ring capacity is exactly 32,768 bytes. A separate bounded descriptor
ring maps every retained byte to exactly one UART channel and receive timestamp.
Descriptors contain metadata only; the 32 KiB ring contains raw DUT bytes.

Required invariants:

- `0 <= used <= 32768` and `used <= high_water <= 32768`.
- Retained bytes remain FIFO-ordered.
- Every retained byte is covered by exactly one descriptor; descriptors have no
  gaps or overlaps.
- One UART callback produces one timestamp. Splitting its bytes across wire
  frames preserves that timestamp; batches never infer a later drain timestamp.
- Byte-space or descriptor-space exhaustion applies the same drop-oldest rule.
  Dropping bytes trims or removes corresponding descriptors atomically.
- `dropped_bytes_total` and `overflow_events` never decrease between MCU boots.
- Telemetry snapshots observe mutually consistent ring and counter values.
- Encoding and CDC writes occur outside the ring critical section.

Short spinlocked sections protect byte, descriptor, and counter mutation. USB
TX copies a bounded event into statically allocated staging storage, transfers
ownership out of the ring, releases the lock, then encodes and writes it. The
staging buffer owns those bytes until the complete frame is accepted by the CDC
driver or the connection epoch fails. Zero, negative, or over-reported FIFO
progress is a CDC fault. A 250 ms interval with no accepted bytes is also a CDC
fault; every positive partial acceptance restarts that interval.

Consecutive drops form one overflow episode. Firmware retains the first-drop
timestamp and exact cumulative byte count in bounded state. Claiming the
episode for USB transmission closes it; a later drop starts another episode.
Thus an indefinite USB stall cannot create an unbounded telemetry queue. One
`buffer_overflow` record reports each closed episode, while periodic
`buffer_status` records expose the current cumulative counters.

Device frames split before exceeding the 65,536-byte wire limit and never
truncate retained bytes merely to fit a frame. Periodic status records may
coalesce to the newest untransmitted snapshot; UART data and overflow records
do not silently coalesce or reorder.

## Safe-State Lifecycle

Revision A hardware pull-downs hold UART and EVENT translator enables inactive
before software runs. Firmware establishes these states before initializing
higher-level services:

- all CTRL output enables inactive, leaving DUT controls high impedance;
- UART translator disabled;
- EVENT MCU pins configured as inputs without pulls;
- EVENT translator disabled.

A CDC connection with DTR asserted starts one firmware connection epoch. The
firmware emits `hello` as its first frame, then enables the initialized UART
interface. CTRL channels remain high impedance until individually configured;
an accepted configuration enters its defined idle state.

USB reset, DTR loss, watchdog reset, or fatal internal fault ends the epoch.
Firmware preempts commands, cancels pulse and UART TX activity, disables UART
and EVENT translators, and forces every CTRL channel high impedance. Partial
protocol input, staged output, ring contents, and accepted CTRL configurations
are discarded. Buffer counters remain boot-cumulative. A later connection
starts with a new `hello`, and the host reapplies its CTRL configuration.

Clearing undelivered data on physical disconnect is transport interruption, not
ring overflow. Device Core already records the interrupted connection and does
not claim that bytes inside the failed transport epoch reached host storage.

Control GPIO sequencing prevents output glitches: disabling a channel clears
its enable before changing data; enabling sets the intended data level before
asserting enable. Open-drain release and every unconfigured, rejected-without-
prior-state, disconnect, and safety-fault path use high impedance.

## Failure Semantics

- A complete command is validated before side effects.
- Malformed, unknown, and invalid complete frames return one bounded existing
  v1 error. Oversized input is discarded through its terminating LF and returns
  one bounded error. Parsing then resumes with the next frame. No invalid
  command changes hardware.
- A failed reconfiguration preserves the previous accepted configuration and
  physical state. Without a previous configuration, the channel remains high
  impedance.
- `pulse_control` responds successfully only after the configured active period
  completes and idle behavior is restored. Disconnect or hardware fault during
  a pulse forces high impedance and cannot produce success.
- `set_control_state` responds successfully only after the requested configured
  behavior is applied.
- `uart_send` responds successfully only after all 1..1024 bytes complete UART
  transmission and returns that exact `bytes_accepted`. Timeout or driver fault
  does not retry because some bytes may already have reached the DUT.
- A recoverable control hardware fault forces the affected channel high
  impedance and returns `hardware_fault`; its accepted configuration remains
  available for an explicit retry. A systemic safety fault ends the connection
  epoch.
- Ring overflow is normal evidence loss, not a parser or connection failure.
  Firmware preserves newest bytes, reports the episode, and continues capture.
- CDC failure ends the connection epoch. Firmware never replays a response or
  partially written frame into the next epoch, preventing ambiguous duplicate
  command completion.

## Test Boundary And Milestone Evidence

Hardware-independent components use Zephyr `ztest` on `native_sim`, with fake
clock, UART, GPIO, and transport ports. Development follows strict red-green-
refactor: each behavioral test must fail for the expected missing behavior
before production logic is added.

TDD covers NDJSON framing and limits, exact protocol messages, capability
alignment, ring wrap/drop/descriptor invariants, overflow coalescing, telemetry
snapshots, CTRL state transitions, pulse timing and cancellation, disconnect
safety, and UART TX completion/partial/timeout outcomes.

Straightforward peripheral initialization uses target builds and focused HIL
rather than artificial test doubles. Required hardware evidence includes the
Pico 2 build, devicetree pin-map checks, CDC connect/reconnect and first-frame
`hello`, UART fixture loads, oscilloscope checks of CTRL startup/disconnect safe
states, and proof that the EVENT translator remains disabled.

Implementation proceeds as small vertical slices, not one large firmware drop.
Each meaningful milestone runs focused firmware tests, relevant Python contract
tests, the repository validation gate, and `git diff --check` before completion.
Systematic debugging is reserved for reproducible failures whose cause remains
unexplained.
