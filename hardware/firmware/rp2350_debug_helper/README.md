# DUTchMate RP2350 Debug Helper Firmware

Phase 1B firmware target for the non-wireless Raspberry Pi Pico 2 with the
RP2350A MCU.

## Current slice

The application owns the Revision A GPIO mapping, establishes startup safe
states, and exposes its initial USB CDC identity:

- `CTRL0` through `CTRL3` enables are inactive, so every DUT control is high
  impedance;
- UART and EVENT translator enables are inactive;
- `EVENT0` through `EVENT3` are inputs without internal pulls;
- EVENT interrupt capture is absent and `gpio_events` is not advertised;
- the development USB identity is VID/PID `2E8A:000A`, manufacturer
  `DUTchMate`, and product `Debug Helper`;
- the USB serial descriptor uses the stable board identifier supplied by
  Zephyr hardware information when available;
- each DTR assertion starts one connection epoch and emits the exact v1
  `hello` first and once; DTR loss forces the GPIO safe state;
- the portable UART RX core defines exactly 32,768 raw bytes and 512 timestamp
  descriptors, preserves FIFO ordering across wrap, and drops oldest data on
  byte or descriptor exhaustion;
- boot-cumulative high-water and loss counters plus bounded overflow-episode
  state are available for the later telemetry adapter;
- UART0 uses GP0/GP1 at fixed 460800 baud, 8-N-1 with no flow control;
- one RP2350 64-bit microsecond timer value is sampled for every UART RX
  interrupt callback, and all bytes drained by that callback retain it;
- UART RX and its bidirectional translator start only after the connection
  epoch's `hello`; DTR loss or a UART driver fault stops RX, disables the
  translator, and discards retained bytes while preserving boot counters;
- the sole CDC writer drains at most 1,024 raw bytes per v1 `uart` event,
  preserves each callback timestamp, and emits exact compact JSON with base64
  payloads;
- internal 64-bit observation sequences keep retained UART chunks and overflow
  episodes ordered without changing the v1 wire format.
- each closed overflow episode emits one exact v1 `buffer_overflow` record
  before any later UART data;
- a boot-cumulative `buffer_status` snapshot is scheduled every second, with at
  most one pending snapshot coalesced to the newest sample;
- UART, overflow, and status evidence share one sequence-ordered CDC writer;
  encoding and USB output remain outside the RX ring spinlock.
- the hardware-independent host-command framer retains at most 2,047 bytes,
  accepts exact 2,048-byte LF or CRLF frames, removes only one final CR, returns
  one frame at a time, and discards oversized input through LF before resuming.
- the portable v1 decoder validates all four command shapes, rejects extra or
  duplicate fields, enforces CTRL, pulse, and base64 bounds, and produces typed
  command values without hardware side effects;
- exact compact success, timestamp, UART-acceptance, and bounded error response
  encoders validate wire limits, UTF-8 details, and JSON escaping.
- the hardware-independent control owner stores accepted electrical modes for
  `CTRL0` through `CTRL3`, applies active/idle behavior, runs wrap-safe bounded
  pulses, and cancels to high impedance on channel faults or epoch end;
- every driven transition disables output before changing data, then enables
  only the requested low/high drive; the Revision A adapter maps those ordered
  operations onto the fixed CTRL enable/data GPIO arrays;
- the portable UART TX owner copies exactly 1..1024 bytes, advances through
  partial FIFO fills, waits for physical completion, and terminalizes timeout,
  cancellation, or driver faults without retrying an ambiguous transmission;
- the RP2350 UART0 adapter shares the existing interrupt callback, protects TX
  state from ISR/thread races, and uses a work item to keep the PL011 software
  kick from blocking the command/control owner;
- the hardware-independent command executor routes typed configure, state,
  pulse, and UART-send commands through the existing owners, permits exactly
  one command or response at a time, and emits the exact v1 response only after
  the requested operation reaches its defined completion point;
- epoch cancellation discards pending work and staged responses, cancels UART
  TX without retry, returns every CTRL channel to high impedance, and forgets
  accepted CTRL configuration;
- a dedicated CDC RX thread feeds bounded chunks into the framer and decoder,
  then applies backpressure through one statically allocated command slot;
- a higher-priority command/control thread owns the executor, CTRL state, pulse
  expiry, and UART TX completion while the main USB TX owner serializes complete
  responses with ordered evidence;
- command responses take the response lane before the next evidence frame;
  evidence observation ordering remains unchanged, and every epoch starts with
  `hello` before command ingress becomes active;
- one portable CDC TX owner copies each complete frame into a bounded
  1,536-byte staging buffer, advances only by exact driver FIFO acceptance,
  and acknowledges responses or evidence only after the full frame is
  accepted;
- the Zephyr CDC callback performs FIFO writes while the main USB TX owner
  starts, polls, and cancels frames; zero, negative, or over-reported progress
  and 250 ms without progress end the epoch, while DTR loss discards staged
  suffix bytes without application-level replay;
- malformed, schema-invalid, and oversized frames produce one bounded existing
  v1 error; epoch end discards partial input, queued commands, and unsent
  responses.

The command path now consumes live CDC input and shares the sole output owner
with evidence. Complete CDC-driver acceptance and mid-frame failure semantics
are target-build verified. Real USB timing and disconnect behavior still
require hardware validation, so the application is not yet accepted as a
complete Enhanced Debug Helper.

## Revision A mapping

The devicetree overlay preserves the normative mapping from
`hardware/schematics/revision_a.md` section 10.1:

| Function | Pico 2 GPIOs |
|---|---|
| UART translator enable | GP2 |
| CTRL0..CTRL3 enable | GP8, GP7, GP26, GP22 |
| CTRL0..CTRL3 data | GP9, GP10, GP20, GP21 |
| EVENT translator enable | GP11 |
| EVENT0..EVENT3 input | GP15, GP14, GP13, GP12 |

## Build

Use the pinned Zephyr 4.4.0 workspace and SDK 1.0.1:

```bash
west build \
  -b rpi_pico2/rp2350a/m33 \
  -s /path/to/DUTchMate/hardware/firmware/rp2350_debug_helper \
  -d /path/to/DUTchMate/build/dutchmate-rp2350-debug-helper \
  --pristine
```

The UF2 image is written to:

```text
/path/to/DUTchMate/build/dutchmate-rp2350-debug-helper/zephyr/zephyr.uf2
```

Keeping the build at this repository-relative path also supplies the
`compile_commands.json` used by the root `.clangd` configuration. After the
first build, restart the clangd language server in VS Code so Zephyr headers,
generated devicetree macros, and target compiler flags are recognized.

Set `CONFIG_DUTCHMATE_FIRMWARE_VERSION` to a 1..64-byte build identifier made
from ASCII letters, digits, `.`, `_`, `+`, and `-`. Production builds must also
set `CONFIG_DUTCHMATE_PRODUCTION_BUILD=y` and override both
`CONFIG_CDC_ACM_SERIAL_VID` and `CONFIG_CDC_ACM_SERIAL_PID` with an assigned
pair. A production build that retains `2E8A:000A` fails at compile time.

This build proves compilation, identity configuration, bounded command ingress,
command/control and USB-writer ownership, explicit CDC FIFO-acceptance logic,
epoch/control/UART TX logic, and devicetree mapping only. USB enumeration,
complete-write timing during disconnect, reconnect behavior, UART TX
completion, CTRL electrical sequencing, startup voltage, translator-disable,
and EVENT input state require the Revision A prototype HIL checks defined by
the approved firmware architecture.
