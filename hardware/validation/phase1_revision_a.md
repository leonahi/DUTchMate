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
| Flashed firmware commit/image | Corrected command-ingress working tree; UF2 SHA-256 `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc` |
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

## VIO-First Debugger Power-Down At 1.8 V

Starting from the preceding powered state, Device Core remained stopped,
`DUT_VIO` remained supplied at 1.80 V with a 1 mA current limit, and Pico USB
was disconnected. After a settling interval, the operator reported that the
following measurements were as expected:

| Measurement | Result |
|---|---|
| Settled `DUT_VIO` supply current | Reported near the preceding debugger-unpowered state; exact value not recorded |
| `DUT_VIO` | Reported approximately 1.8 V; exact value not recorded |
| `DBG_UART_IF_EN` | Reported approximately 0 V; exact value not recorded |
| `DBG_INPUT_IF_EN` | Reported approximately 0 V; exact value not recorded |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | Reported approximately 0 V; exact values not recorded |

This is qualitative evidence that the interface and control enables remained
disabled after debugger power-down while VIO stayed present. The sequence is
not accepted as a reproducible numeric result, and it does not close the
all-orderings, `/OE`, output-high-impedance, or back-power checklist items.

## Debugger-Powered-First DUT_VIO Power-Up At 1.8 V

Setup:

- DUT disconnected;
- Device Core stopped and no serial client connected;
- `DUT_VIO` initially off;
- Pico USB connected first;
- bench supply set to 1.80 V with a 1 mA current limit, then enabled after the
  debugger was powered.

The following steady-state measurements were recorded after `DUT_VIO` was
applied:

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_VIO` supply current | 28.96 uA | Below the documented 50 uA idle target |
| Pico `3V3(OUT)` | 3.3 V | Expected with debugger USB powered |
| `DBG_UART_IF_EN` | 0.0 V | Disabled as required |
| `DBG_INPUT_IF_EN` | 0.0 V | Disabled as required |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each | Disabled as required |

This passes the measured enable-state expectations for this one debugger-first
power-up sequence. It closely reproduces the 28.93 uA VIO-first powered result.
The broader `/OE`, output-high-impedance, and all-orderings checklist items
remain open.

## Debugger-First DUT_VIO Power-Down At 1.8 V

Starting from the preceding powered state, Device Core remained stopped and
Pico USB remained connected. The bench supply was turned off and its positive
lead was disconnected from `DUT_VIO` while common ground remained connected.
After a settling interval, the following measurements were recorded:

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 0.0 V | No static debugger-to-VIO back-power observed |
| Pico `3V3(OUT)` | 3.3 V | Debugger supply remained present |
| `DBG_UART_IF_EN` | 0.0 V | Disabled as required |
| `DBG_INPUT_IF_EN` | 0.0 V | Disabled as required |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each | Disabled as required |

This passes the measured rail and enable-state expectations for this one
debugger-first VIO power-down sequence. It does not prove output high
impedance, quantify leakage under load, or cover every power ordering, so the
broader checklist items remain open.

## Active Enhanced UART Idle Path At 1.8 V

Setup:

- DUT disconnected;
- Pico USB connected at `/dev/cu.usbmodem11201`;
- `DUT_VIO` supplied at 1.80 V with a 1 mA current limit;
- Enhanced Device Core epoch active at 460800 baud;
- UART TX policy disabled and all control channels unconfigured.

During the active epoch, Device Core reported the expected RP2350 identity and
capabilities, no workflow or session, and
`none_reported` UART loss with zero dropped bytes. The following steady-state
measurements were recorded:

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_VIO` supply current | 28.93 uA | Below the documented 50 uA idle target |
| Pico `3V3(OUT)` | 3.3 V | Expected |
| `DBG_UART_IF_EN` | 3.3 V | UART translator enabled during the epoch |
| `DBG_INPUT_IF_EN` | 0.0 V | Event translator remained disabled |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each | Controls remained disabled |
| Connector-side `DUT_UART_RX` | 1.8 V | UART idle-high translated to the VIO domain |

The service was then shut down cleanly while both rails remained powered. After
a settling interval, the following post-epoch measurements were recorded:

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_VIO` supply current | 28.96 uA | Below the documented 50 uA idle target |
| Pico `3V3(OUT)` | 3.3 V | Expected |
| `DBG_UART_IF_EN` | 0.0 V | UART translator disabled after epoch end |
| `DBG_INPUT_IF_EN` | 0.0 V | Event translator remained disabled |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each | Controls remained disabled |
| Connector-side `DUT_UART_RX` | 0.0 V | No static driven voltage observed after epoch end |

This passes the static UART-enable, VIO-domain idle-level, unrelated-enable,
and post-epoch voltage expectations at 1.8 V. It does not prove post-epoch high
impedance.

## CDC Command-Ingress Diagnosis And Corrected Image

With both rails off, the DUT-side UART pins were looped from J3 pin 4
`DUT_UART_RX` to J1 pin 4 `DUT_UART_TX`. After restoring USB and 1.80 V
`DUT_VIO`, the first TX-enabled Enhanced run failed before UART signaling:

- `uart_send` timed out;
- capture `20260910T184808Z-21b9fe4e` contained no UART bytes;
- a raw invalid-command write also received no response while `hello` and
  periodic `buffer_status` frames continued normally.

The repeatable asymmetry isolated the failure to host-to-device CDC command
ingress. The firmware had installed a CDC interrupt callback for TX while its
command thread tried to receive with `uart_poll_in`. The Zephyr 4.4.2
next-generation CDC sample instead drains RX readiness with `uart_fifo_read`
inside the registered callback. Merely enabling CDC RX per epoch did not fix
the hardware result. The corrected implementation now:

- enables CDC RX only during an active connection epoch;
- handles RX and TX readiness in the shared CDC callback;
- drains RX with `uart_fifo_read` in the USB workqueue context;
- transfers those bytes through a bounded static queue to the existing command
  framing thread; and
- disables RX and purges queued bytes at epoch end.

`probe_rp2350_command_ingress.py` reproduces the original failure by requiring
one `invalid_command` response after `hello`. It failed against both the
original image and the enable-only attempt, then passed against the corrected
image. The corrected `rpi_pico2/rp2350a/m33` Zephyr 4.4.2 build used 52,012
bytes of flash and 78,032 bytes of RAM. Its 104,448-byte UF2 has SHA-256
`c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`.

## UART Loopback At 1.8 V And 460800 Baud

After the corrected image passed command ingress, the UART loopback remained
installed and `DUT_VIO` was restored at 1.80 V with a 1 mA current limit.
Before the active run, `DUT_VIO` measured 1.8 V and steady current measured
28.94 uA.

A TX-enabled Enhanced epoch sent the 33-byte payload
`DUTCHMATE_LOOPBACK_1V8_460800_A5\n`. The device reported success with all 33
bytes accepted and device completion timestamp 363127095 us. Capture
`20260910T192926Z-033765ed` stored an exact 33-byte match in `uart_raw.log`,
including the final LF. Its completed metadata reports:

- `loss_status = none_reported` and zero dropped bytes;
- no overflow, interruption, resume, or truncation;
- one Enhanced segment with RP2350 device-timer provenance; and
- a 33-byte RX high-water mark that returned to zero occupancy.

This passes one functional transmit/receive integrity check at 1.8 V and
460800 baud. It does not validate electrical margins, cable-length limits,
other baud rates, or the remaining 2.5 V, 3.3 V, and 5.0 V operating points.

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
- The paired debugger power-down retained the expected enable states, but only
  qualitative results were recorded.
- The debugger-first `DUT_VIO` power-up sequence retained the expected disabled
  enable states and remained within the 1.8 V idle-current budget.
- The paired `DUT_VIO` power-down left the VIO rail at 0.0 V and retained the
  expected disabled enable states while debugger power remained present.
- An active Enhanced epoch enabled only the UART interface, produced the
  expected 1.8 V DUT-side idle-high level with zero reported loss, and returned
  all measured enable/output voltages to 0.0 V after clean shutdown.
- Corrected command ingress and the DUT-side UART loopback passed an exact
  33-byte transmit/receive check at 1.8 V and 460800 baud with zero reported
  loss or overflow.
- Power isolation is not accepted while the loaded `3V3(OUT)` check is
  deferred.
- No item in the Revision A prototype checklist is closed by this record yet.
