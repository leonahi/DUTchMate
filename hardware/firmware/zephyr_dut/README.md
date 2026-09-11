# DUTchMate Zephyr DUT Fixture

The Zephyr DUT fixture is a controlled device under test for DUTchMate hardware-in-the-loop
(HIL) validation. It runs on a first-generation Raspberry Pi Pico or Pico H and produces known
UART and boot behaviour. It is deliberately separate from the DUTchMate RP2040 Debug Helper:
the fixture is the target being observed, while the Debug Helper is one of the transports used
to observe and control it.

The same fixture validates both Phase 1 paths:

```text
Basic:    DUTchMate host -> generic 3.3 V USB-to-UART adapter -> Zephyr DUT
Enhanced: DUTchMate host -> DUTchMate Debug Helper             -> Zephyr DUT
```

Host assertions must use the bytes, events, timestamps, integrity metadata, and session
artifacts captured by DUTchMate. They must not depend on Zephyr console or log prefixes. The
fixture therefore disables Zephyr console, `printk`, and logging and owns UART0 directly.

## Supported baseline

- Board: Raspberry Pi Pico 1 or Pico H, non-wireless, RP2040
- Zephyr board target: `rpi_pico`
- Reference Zephyr release: `v4.4.0`
- Verified Zephyr SDK: `1.0.1`
- UART: 115200 baud, 8 data bits, no parity, 1 stop bit, no flow control
- Fixture protocol: `DMF/1`

The 115200-baud default remains the Phase 1A Basic baseline. Enhanced
ring-buffer validation uses the opt-in `boards/rpi_pico_460800.overlay`; do not
assume that the Basic acceptance image runs at the Enhanced rate.

The HIL report must record the exact Zephyr revision actually used. A newer Zephyr release is
not accepted implicitly merely because the application builds.

## Wiring and electrical safety

Power the Pico through its Micro-USB connector. Connect only a 3.3 V TTL UART adapter or a
correctly translated DUTchMate interface. Do not connect RS-232 voltage levels or 5 V UART
logic directly to the Pico, and do not connect the adapter VCC pin when the Pico is powered by
USB.

| Purpose | Pico signal | Physical pin | Connect to |
|---|---|---:|---|
| Fixture UART transmit | GP0 / UART0 TX | 1 | Adapter or Debug Helper RX |
| Fixture UART receive | GP1 / UART0 RX | 2 | Adapter or Debug Helper TX |
| Common reference | GND | 3 | Adapter or Debug Helper GND |
| Boot-mode bit 0 | GP2 | 4 | Open for 0; Pico 3V3 for 1 |
| Boot-mode bit 1 | GP3 | 5 | Open for 0; Pico 3V3 for 1 |
| Hardware reset | RUN | 30 | Momentary GND or open-drain reset control |
| Strap reference only | 3V3(OUT) | 36 | GP2/GP3 mode strap source |

GP2 and GP3 use internal pull-downs and are sampled once during firmware startup. Change the
straps only while the Pico is unpowered or held in reset. The RUN pin is active low; Enhanced
validation must drive it through an open-drain control and release it to high impedance.

## Boot modes

| GP3 bit 1 | GP2 bit 0 | Behaviour | Expected boot evidence |
|---:|---:|---|---|
| 0 | 0 | Successful boot | `DMF/1 BOOT OK ...` |
| 0 | 1 | Initialization failure | `DMF/1 ERROR INIT code=E_INIT_001 ...` |
| 1 | 0 | Silent boot | No UART bytes until reset |
| 1 | 1 | Invalid fixture configuration | `DMF/1 ERROR MODE code=E_MODE_001 ...` |

The successful and failure markers include `board=rpi_pico` and the configured fixture build
identifier. Silent boot intentionally emits no banner, Zephyr prefix, or acknowledgement.

## UART commands

Commands are uppercase ASCII terminated by LF. CRLF is accepted because CR bytes are ignored.
The input line is bounded to 32 bytes. An empty, oversized, lowercase, or unknown command gets
the same stable command error and never echoes the rejected input.

| Command | Deterministic behaviour | Validation purpose |
|---|---|---|
| `PING` | Emits `DMF/1 PONG` | UART transmit and response path |
| `INFO` | Emits board, build ID, and protocol version | Fixture identity and provenance |
| `PARTIAL` | Writes one line in two chunks separated by 50 ms | Partial-line buffering |
| `BINARY` | Emits a fixed line containing invalid UTF-8 bytes | Raw-byte preservation |
| `BURST` | Emits 2,048 numbered lines and a checksum immediately | Loss, overflow, and truncation |
| `SUSTAIN` | Emits 4,096 numbered lines at 2 ms intervals and a checksum | Sustained-load behaviour |
| `SILENT` | Acknowledges once and suppresses later output until reset | Capture timeout after command |

The burst checksum is the sum of sequence values `0..2047` (`2096128`). The sustained checksum
is the sum of `0..4095` (`8386560`). Sequence gaps, a missing end marker, a wrong count, or a
wrong checksum are objective evidence of missing or altered UART data.

## Create a Zephyr 4.4 workspace

Install the Zephyr prerequisites and SDK for the host platform by following the official Zephyr
getting-started guide. The following creates a workspace pinned to the reference release:

```bash
west init -m https://github.com/zephyrproject-rtos/zephyr --mr v4.4.0 zephyr-workspace
cd zephyr-workspace
west update
west zephyr-export
python3 -m pip install -r zephyr/scripts/requirements.txt
```

The Zephyr SDK/toolchain must also be installed and discoverable by Zephyr. This fixture is
cross-build verified with Zephyr SDK `1.0.1`. Keep the Zephyr workspace outside this
repository; downloaded Zephyr modules are dependencies, not DUTchMate source.

## Build

From the Zephyr workspace, replace `/path/to/DUTchMate` and choose a short, immutable build ID:

```bash
west build \
  -b rpi_pico \
  -s /path/to/DUTchMate/hardware/firmware/zephyr_dut \
  -d build/dutchmate-zephyr-dut \
  --pristine \
  -- -DCONFIG_DUTCHMATE_FIXTURE_BUILD_ID=\"phase1-pico-001\"
```

The UF2 image is written to:

```text
build/dutchmate-zephyr-dut/zephyr/zephyr.uf2
```

Do not use the default `development` build ID for an acceptance run.

For the Phase 1B Enhanced and ring-buffer runs, keep the same fixture source and
select its 460800-baud overlay explicitly:

```bash
west build \
  -b rpi_pico \
  -s /path/to/DUTchMate/hardware/firmware/zephyr_dut \
  -d build/dutchmate-zephyr-dut-460800 \
  --pristine \
  -- \
  -DDTC_OVERLAY_FILE=boards/rpi_pico_460800.overlay \
  -DCONFIG_DUTCHMATE_FIXTURE_BUILD_ID=\"phase1-enhanced-460800-001\"
```

Before flashing, verify that generated `zephyr.dts` records
`current-speed = < 0x70800 >` for UART0, record the immutable build ID and UF2
digest, and keep the 115200-baud Basic image separately identifiable.

## Flash

For UF2 flashing without an SWD probe:

1. Disconnect the Pico USB cable.
2. Hold BOOTSEL while reconnecting USB.
3. Release BOOTSEL after the `RPI-RP2` mass-storage device appears.
4. Copy `zephyr.uf2` to that device, or run `west flash --runner uf2` from the build directory.
5. Reconnect the UART adapter and reset the fixture with the required mode straps.

Flashing is external to DUTchMate. SWD flashing through OpenOCD, pyOCD, or J-Link is also valid,
but the selected method and probe identity belong in the HIL report.

## Local protocol verification

The deterministic protocol engine is portable C and is compiled with the host C compiler by
the repository test suite:

```bash
uv run pytest tests/hardware/zephyr_dut/test_fixture_protocol.py -q
```

This verifies exact boot markers, command responses, raw invalid UTF-8 bytes, partial writes,
sequence counts, pacing requests, checksums, silence, and bounded error behaviour. It does not
replace a Zephyr cross-build or a real adapter/Pico HIL run.

## HIL provenance

Record all of the following with every Basic or Enhanced acceptance run:

- Zephyr version and exact source revision;
- `rpi_pico` board target;
- DUTchMate application commit and dirty/clean state;
- configured fixture build ID;
- generated Zephyr `.config`;
- UF2 SHA-256 digest;
- adapter or Debug Helper identity and serial port;
- boot-mode strap state;
- DUTchMate session IDs for every scenario;
- expected and observed sequence counts, checksums, first error, timeout, and integrity result.

The reproducible Basic acceptance procedure and report template are maintained in
[`hardware/validation/phase1_basic_hil.md`](../../validation/phase1_basic_hil.md). Use that
procedure to record the real adapter/Pico session evidence required for Phase 1A acceptance.
