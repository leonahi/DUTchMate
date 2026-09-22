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
- DTR must remain asserted for 100 ms before one connection epoch starts; the
  firmware publishes USB carrier-ready state and emits the exact v1 `hello`
  first and once, while DTR loss forces the GPIO safe state;
- the portable UART RX core defines exactly 32,768 raw bytes and 512 timestamp
  descriptors, preserves FIFO ordering across wrap, and drops oldest data on
  byte or descriptor exhaustion;
- boot-cumulative high-water and loss counters plus bounded overflow-episode
  state are available for the later telemetry adapter;
- UART0 uses GP0/GP1 at fixed 460800 baud, 8-N-1 with no flow control;
- one RP2350 64-bit microsecond timer value is sampled for every UART RX
  interrupt callback, and all bytes drained by that callback retain it;
- UART RX and its bidirectional translator start only after the connection
  epoch's `hello`; DTR loss or a UART driver API fault stops RX, disables the
  translator, and discards retained bytes while preserving boot counters;
  positive line-error flags such as break or framing are cleared without
  ending the epoch so DUT reset cannot prevent later boot bytes from arriving;
- the sole CDC writer drains at most 1,024 raw bytes per v1 `uart` event,
  preserves each callback timestamp, and emits exact compact JSON with base64
  payloads;
- the writer drains up to 32 immediately ready outputs per bounded batch and
  skips its 10 ms idle backoff while a full batch shows that output remains;
  DTR is still checked while every frame advances and again between batches;
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
- the CDC driver's 2,048-byte TX FIFO holds the largest 1,536-byte encoded
  evidence frame and lets adjacent frames pack into continuous 64-byte
  full-speed USB transfers instead of forcing a completion at every frame's
  first packet boundary;
- the Zephyr CDC callback performs FIFO writes while the main USB TX owner
  starts, polls, and cancels frames; zero, negative, or over-reported progress
  and 250 ms without progress end the epoch, while DTR loss discards staged
  suffix bytes without application-level replay;
- malformed, schema-invalid, and oversized frames produce one bounded existing
  v1 error; epoch end discards partial input, queued commands, and unsent
  responses.

The command path now consumes live CDC input and shares the sole output owner
with evidence. Complete CDC-driver acceptance, mid-frame failure semantics, and
bounded output-drain pacing are target-build verified. On the Pico 2, macOS
accepted two consecutive DTR
epochs and received the complete 175-byte `hello` in 98 ms and 104 ms; the real
CLI then started and reported the Enhanced backend connected. Remaining UART,
electrical, load, and active-workflow reconnect behavior still requires HIL, so
the application is not yet accepted as a complete Enhanced Debug Helper.

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

Run the build from a west workspace pinned to Zephyr 4.4.2 with SDK 1.0.1.
`west build` is unavailable from the DUTchMate repository itself unless that
repository is also inside a west workspace.

`PRODUCT_VERSION` is the authoritative Debug Helper product version. Release-grade
builds pass that value as `CONFIG_DUTCHMATE_FIRMWARE_VERSION`; it is independent
of the DUTchMate host-software version and Enhanced protocol version.

Zephyr 4.4.2 is the enforced minimum. Earlier releases leave RP2350 PL011 UART
error interrupts latched and can trap the MCU in an interrupt storm
([GHSA-36rp-2hcp-f5hv](https://github.com/zephyrproject-rtos/zephyr/security/advisories/GHSA-36rp-2hcp-f5hv)).
The firmware therefore retains UART error interrupt reporting and rejects an
affected Zephyr version at configure time.

```bash
repo_root=/absolute/path/to/DUTchMate
cd /absolute/path/to/zephyrproject
.venv/bin/west build \
  -b rpi_pico2/rp2350a/m33 \
  -s "$repo_root/hardware/firmware/rp2350_debug_helper" \
  -d "$repo_root/build/dutchmate-rp2350-debug-helper" \
  --pristine
```

The UF2 image is written to:

```text
/path/to/DUTchMate/build/dutchmate-rp2350-debug-helper/zephyr/zephyr.uf2
```

### USB-only stack measurement build

The production image has no console. For Phase 1 ring-buffer acceptance, use
the opt-in `stack_probe.conf` build with Zephyr 4.4.2, SDK 1.0.1, and only the
CMSIS 6 and Pico HAL modules. Keep it in a separate build directory:

```bash
ZEPHYR_BASE=/path/to/zephyrproject/zephyr-4.4.2 west build \
  -b rpi_pico2/rp2350a/m33 \
  -s "$repo_root/hardware/firmware/rp2350_debug_helper" \
  -d "$repo_root/build/dutchmate-rp2350-stack-probe" \
  --pristine -- \
  -DEXTRA_CONF_FILE="$repo_root/hardware/firmware/rp2350_debug_helper/stack_probe.conf" \
  '-DZEPHYR_MODULES=/path/to/zephyrproject/modules/hal/cmsis_6;/path/to/zephyrproject/modules/hal/rpi_pico' \
  -DUSER_CACHE_DIR="$repo_root/build/zephyr-cache"
```

Flash the diagnostic UF2 externally. Its first epoch reports firmware
`stackprobe-1` and runs the normal v1 workload. When DTR drops after that epoch,
Zephyr's Thread Analyzer freezes all thread and ISR high-water readings. Each
later CDC epoch reports one reading in the valid `hello.firmware` field as
`stack-<index>of<count>-<name>-<used>-<size>`; those retrieval epochs do not
resample or add DUT UART evidence. After the final retrieval epoch closes, the
next workload epoch again reports `stackprobe-1` and can collect another profile.

Stop Device Core after each boot, 500 ms backpressure, and deliberate-overflow
profile so DTR drops, then collect the frozen readings before restarting it:

```bash
"$repo_root/.venv/bin/python" \
  "$repo_root/hardware/firmware/rp2350_debug_helper/tools/collect_stack_probe.py" \
  /dev/cu.usbmodem11201 \
  --uf2 "$repo_root/build/dutchmate-rp2350-stack-probe/zephyr/zephyr.uf2" \
  --out "$repo_root/build/stack-probe-boot.json"
```

Use a different output file for each profile. Retain the diagnostic UF2 hash,
stack sizes and used/free bytes, session IDs, host load, and any reset, USB,
or session failure in `hardware/validation/phase1_ring_buffer.md`. This image
enables thread monitoring and adds diagnostic RAM, so record its separate static
footprint and compare the margins against the normal image before closing the
32 KiB decision. The collector holds DTR low through port opening and input
flushing so the one-shot `hello` is not discarded.

For the synthetic profiles, the helper below starts a 15 s capture, sends the
fixture command after 0.5 s, and (for the backpressure run) pauses the verified
Device Core Service process 1.5 s after send completion. It always resumes the
service if interrupted and records the measured monotonic pause and host load:

```bash
"$repo_root/.venv/bin/python" \
  "$repo_root/hardware/firmware/rp2350_debug_helper/tools/run_load_profile.py" \
  SUSTAIN --stall-ms 500 --out "$repo_root/build/stack-profile-500ms.json"

"$repo_root/.venv/bin/python" \
  "$repo_root/hardware/firmware/rp2350_debug_helper/tools/run_load_profile.py" \
  BURST --out "$repo_root/build/stack-profile-overflow.json"
```

Keeping the build at this repository-relative path also supplies the
`compile_commands.json` used by the root `.clangd` configuration. After the
first build, restart the clangd language server in VS Code so Zephyr headers,
generated devicetree macros, and target compiler flags are recognized.

Release builds set `CONFIG_DUTCHMATE_FIRMWARE_VERSION` from `PRODUCT_VERSION`.
Development and diagnostic identifiers remain limited to 1..64 bytes made from
ASCII letters, digits, `.`, `_`, `+`, and `-`. Production builds must also set
`CONFIG_DUTCHMATE_PRODUCTION_BUILD=y` and override both
`CONFIG_CDC_ACM_SERIAL_VID` and `CONFIG_CDC_ACM_SERIAL_PID` with an assigned
pair. A production build that retains `2E8A:000A` fails at compile time.

This build proves compilation, identity configuration, bounded command ingress,
command/control and USB-writer ownership, explicit CDC FIFO-acceptance logic,
epoch/control/UART TX logic, and devicetree mapping. USB enumeration, complete
multi-packet `hello` delivery, consecutive idle connection epochs, and real CLI
startup are verified on the Pico 2. Complete-write timing during physical
disconnect, active-workflow reconnect, UART TX completion, CTRL electrical
sequencing, startup voltage, translator-disable, and EVENT input state remain
Revision A prototype HIL checks defined by the approved firmware architecture.

## Hardware-independent verification

From the DUTchMate repository root, run:

```bash
uv run pytest -q tests/hardware/rp2350_debug_helper
```

The suite compiles the portable C modules with strict host-compiler warnings
and exercises these boundaries without Zephyr or a connected board:

| Boundary | Test coverage |
|---|---|
| Device identity and exact protocol output | `test_hello.py`, `test_uart_event.py`, `test_telemetry.py`, `test_command_response.py` |
| NDJSON framing, command validation, and bounded ingress | `test_ndjson_framer.py`, `test_command_decode.py`, `test_command_ingress.py` |
| RX adapter line-error recovery, ring ordering, loss accounting, and telemetry scheduling | `test_uart_rx_adapter.py`, `test_uart_rx_ring.py`, `test_telemetry.py` |
| CTRL transitions, pulses, command execution, and UART TX state | `test_control_state.py`, `test_command_executor.py`, `test_uart_tx_state.py` |
| Connection epochs, bounded output draining, and complete CDC frame acceptance | `test_connection_epoch.py`, `test_output_drain.py`, `test_cdc_tx_state.py` |

The target build verifies Zephyr adapter integration, compile-time devicetree
mapping checks, and static allocation. Focused Pico 2 HIL verifies USB startup,
packet-paced `hello`, and consecutive idle epochs; it does not prove UART
timing, GPIO voltage or sequencing, physical-disconnect behavior, stack margins,
or load behavior. Those remain Step 6 hardware-validation gates. EVENT pins
remain safely initialized and reserved, with no capture implementation or
advertised capability.
