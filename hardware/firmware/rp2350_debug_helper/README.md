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
  `hello` first and once; DTR loss forces the GPIO safe state.

USB command parsing, UART transfer, control commands, timestamps, ring
buffering, and telemetry remain later vertical slices. This application is
therefore not yet usable as a complete Enhanced Debug Helper.

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

This build proves compilation, identity configuration, protocol-independent
epoch logic, and devicetree mapping only. USB enumeration/descriptor behavior,
CDC reconnect behavior, startup voltage, translator-disable, and EVENT input
state require the Revision A prototype HIL checks defined by the approved
firmware architecture.
