# Phase 1B Revision A Prototype Validation Record

> Status: in_progress
> Scope: Phase 1B electrical, isolation, sequencing, and signal-integrity
> evidence for the first assembled Revision A translator prototype.

This record preserves measured prototype evidence for the checklist in
`hardware/schematics/revision_a.md` section 14. An observation is not an
acceptance result when its instrument, method, or numeric result is missing or
uncertain. Unresolved items remain unchecked in the normative checklist.

## Prototype And Run Identity

| Field | Result |
|---|---|
| Run date/time | 2026-09-10, Europe/Paris |
| Operator | Not recorded |
| Prototype | User-confirmed fully assembled Revision A translator prototype |
| BOM and exact Pico mapping audit | Not run |
| Debug Helper platform | Raspberry Pi Pico 2, non-wireless, RP2350A |
| Host OS | macOS 26.2, build 25C56 |
| USB identity | DUTchMate Debug Helper, VID:PID `2E8A:000A` |
| USB serial number | `FA63A4D787572B33` |
| Serial port | `/dev/cu.usbmodem11401` |
| Device protocol identity | `device = "dutchmate-rp2350"`, `firmware = "development"` |
| Advertised capabilities | `uart_receive`, `gpio_control`, `uart_send`, `device_timestamp`, `overflow_telemetry` |
| DUTchMate commit during run | `e0e75cad5a660b771ca6c5e18dad4c0183f2a4f5` |
| Flashed firmware commit/image | Not established; protocol build identifier alone is insufficient provenance |
| Reference Zephyr target | `rpi_pico2/rp2350a/m33` |
| Reference Zephyr version/SDK | Zephyr 4.4.2, SDK 1.0.1 |
| Reproduced reference UF2 SHA-256 | `db5ba9dfcbcc6d6bbfd83149dd9d5c1b8f206478ad2d7d6ef68f18b57dc16afe` |
| DMM | Older, uncalibrated unit; make/model and accuracy not recorded |
| Bench supply | Make/model and calibration not recorded |

The reference UF2 digest was reproduced from the tracked source before this
run, but the flashed image was not read back or otherwise proven to match it.
Do not use the reference digest as flashed-image provenance.

## Initial USB And Protocol Observation

With the DUT disconnected and `DUT_VIO` absent, macOS enumerated the prototype
at the recorded port. One direct adapter run received a valid `hello` and then
reported `BackendDisconnectedError`, rooted in pyserial
`SerialException: read failed: [Errno 6] Device not configured`; the USB device
re-enumerated at a new address. The failure was not reproduced afterward:

- one raw epoch remained healthy for 4.119 seconds and delivered one complete
  `hello` plus four complete one-second `buffer_status` frames;
- three subsequent consecutive epochs each delivered one complete `hello` and
  one complete `buffer_status` frame without an error;
- every observed status reported a 32,768-byte UART RX buffer, zero occupancy,
  zero high-water usage, zero dropped bytes, and zero overflow events.

This isolated reset remains a recorded transient observation. It does not fail
the prototype, but later reconnect and sustained-load runs must show whether it
recurs.

## USB-Powered, DUT_VIO-Absent Safe State

Setup:

- DUT disconnected and unpowered;
- `DUT_VIO` disconnected;
- prototype powered only through Pico 2 USB;
- control channels unconfigured and UART TX policy disabled.

Before DTR assertion, the operator reported `DUT_VIO`,
`DBG_UART_IF_EN`, `DBG_INPUT_IF_EN`, and all four `DBG_CTRL_ENn` test
points as approximately 0 V. Exact readings were not recorded.

During a live Enhanced epoch, Device Core reported a connected Enhanced
backend, all five device capabilities, no active workflow, no configured
control channels, UART TX policy disabled, and zero reported UART loss. The
operator reported:

- `DUT_VIO` remained approximately 0 V;
- `DBG_UART_IF_EN` was approximately 3.3 V as expected for active UART RX;
- `DBG_INPUT_IF_EN` and all four `DBG_CTRL_ENn` signals remained approximately
  0 V;
- the four DUT control outputs and both DUT UART pins showed no significant
  driven voltage.

After the service stopped and DTR was deasserted, the operator reported that
`DBG_UART_IF_EN` returned to approximately 0 V, the other enable signals
remained approximately 0 V, and no DUT-side output showed significant driven
voltage.

These observations are useful preliminary evidence, but they do not close the
missing-`DUT_VIO`, high-impedance, or safe-state checklist items because exact
numeric readings and calibrated instrument identity were not recorded. Static
voltage alone also does not prove high impedance.

## DUT-Powered, Debugger-Unpowered Leakage At 1.8 V

Setup:

- USB disconnected;
- DUT absent;
- bench supply connected from `DUT_VIO` to common ground;
- supply set to 1.80 V with a 1 mA current limit.

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_VIO` supply current | 25.2 uA | Below the documented 50 uA idle target |
| Pico `3V3(OUT)` | 0.13 V | Inconclusive due to uncalibrated DMM and missing load test |
| Pico `VSYS` | 0 V | No observed back-powering |
| Pico `VBUS` | 0 V | No observed back-powering |

The current-budget result passes its numeric target. The 0.13 V reading on
`3V3(OUT)` must not be dismissed as meter error or accepted as harmless
leakage without a source-impedance check. It is therefore deferred rather than
passed or failed.

## DUT-Powered-First Debugger Power-Up At 1.8 V

Setup:

- DUT disconnected;
- Device Core stopped and no serial client connected;
- USB initially disconnected;
- bench supply connected from `DUT_VIO` to common ground and set to 1.80 V
  with a 1 mA current limit;
- `DUT_VIO` applied before Pico USB was connected.

After USB enumeration, without starting the service, the following steady-state
measurements were recorded:

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_VIO` supply current | 28.93 uA | Below the documented 50 uA idle target |
| Pico `3V3(OUT)` | 3.3 V | Expected with debugger USB powered |
| `DBG_UART_IF_EN` | 0.0 V | Disabled as required |
| `DBG_INPUT_IF_EN` | 0.0 V | Disabled as required |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each | Disabled as required |

This passes the measured enable-state expectations for this one VIO-first
power-up sequence. It does not by itself prove that the translator outputs are
high impedance, verify the `SN74LV4T125PWR` `/OE` levels, or cover every
power-up and power-down ordering, so the corresponding checklist items remain
open.

## Deferred 3V3 Back-Power Check

Resume this exact check with USB disconnected and `DUT_VIO` supplied at
1.80 V:

1. Record the DMM or oscilloscope make/model, calibration status, input
   impedance, and the unloaded `3V3(OUT)` voltage.
2. Connect 10 kOhm from Pico `3V3(OUT)` physical pin 36 to ground. The resistor
   limits current to at most 0.33 mA at 3.3 V.
3. Record loaded `3V3(OUT)`, `DUT_VIO`, and supply current.
4. Remove the resistor and turn off `DUT_VIO`.

If the voltage collapses toward zero without a material supply-current
increase, record the result as high-impedance leakage or instrument offset. If
it remains above 0.10 V, investigate the back-power path before accepting the
power-isolation checklist item.

## Current Decision

`in_progress`

- The prototype identity and initial safe-state observations are recorded.
- The 1.8 V idle current is within budget.
- The VIO-first debugger power-up sequence retained the expected disabled
  interface and control enable states.
- Power isolation is not accepted while the loaded `3V3(OUT)` check is
  deferred.
- No item in the Revision A prototype checklist is closed by this record yet.
