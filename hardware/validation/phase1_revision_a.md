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
| Run date/time | 2026-09-10 through 2026-09-11, Europe/Paris |
| Operator | Not recorded |
| Prototype | User-confirmed fully assembled Revision A translator prototype |
| BOM and exact Pico mapping audit | Source-level schematic/board/firmware audit passed 2026-09-15; populated-part and physical-continuity audit not run |
| Debug Helper platform | Raspberry Pi Pico 2, non-wireless, RP2350A |
| Host OS | macOS 26.2, build 25C56 |
| USB identity | DUTchMate Debug Helper, VID:PID `2E8A:000A` |
| USB serial number | `FA63A4D787572B33` |
| Serial port | `/dev/cu.usbmodem11401` |
| Device protocol identity | `device = "dutchmate-rp2350"`, `firmware = "development"` |
| Advertised capabilities | `uart_receive`, `gpio_control`, `uart_send`, `device_timestamp`, `overflow_telemetry` |
| DUTchMate commit during run | `e0e75cad5a660b771ca6c5e18dad4c0183f2a4f5` |
| Flashed firmware commit/image | Commit `8bf0a03783c31232095dc00a14b783889f6efa57`; UF2 SHA-256 `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc` |
| Reference Zephyr target | `rpi_pico2/rp2350a/m33` |
| Reference Zephyr version/SDK | Zephyr 4.4.2, SDK 1.0.1 |
| Reproduced reference UF2 SHA-256 | `db5ba9dfcbcc6d6bbfd83149dd9d5c1b8f206478ad2d7d6ef68f18b57dc16afe` |
| DMM | Older, uncalibrated unit; make/model and accuracy not recorded |
| 5.0 V source/current monitor | Nordic PPK2; calibration status not recorded |
| Bench supply | Make/model and calibration not recorded |

The reference UF2 digest was reproduced from the tracked source before this
run, but the flashed image was not read back or otherwise proven to match it.
Do not use the reference digest as flashed-image provenance.

## 2026-09-15 Source Mapping And Configured Rejection Audit

An exact parser comparison of `hardware/schematics/revision_a.md` section 10.1,
the committed Eagle schematic `U4` net pinrefs, and the Eagle board `U4`
contact pads found all 17 Revision A net-to-GPIO and physical-pin assignments
identical. The Eagle schematic devicesets and board element values also match
the provisional logic-device references: U1 `TXU0202DCUR`, U2
`TXU0104PWR`, U3 `SN74LV4T125PWR`, and U5/U6 `SN74LVC2G06DBVR`. The RP2350
devicetree overlay agrees with the 14 assigned UART/event/control GPIOs,
including the exact `CTRL0`–`CTRL3` enable/data array order, and selects UART0
at 460800 baud. This checks committed design files; it cannot identify the
parts soldered to the prototype or prove its physical net continuity.

With the user-confirmed 3.3 V Pico 1 fixture still connected (`DUT_CTRL0` to
`RUN`, `DUT_CTRL1` to GP2), a local Enhanced service epoch on Pico 2
`/dev/cu.usbmodem11201` accepted `CTRL0` as released open-drain active-low
`reset` and `CTRL1` as push-pull active-high/idle-low `boot`. Public status
showed a connected `dutchmate-rp2350` firmware `development` backend and
commanded mode `normal`. The following negative requests all failed before
an accepted mode change:

| Request | Observed result |
|---|---|
| CLI `CTRL4` push-pull | Exit 2; invalid control channel |
| CLI `CTRL0` open-drain active-high | Exit 2; active level must be low |
| CLI `CTRL1` push-pull active-high/idle-high | Exit 2; idle must oppose active |
| Direct local service POST of each malformed request | HTTP 400 `invalid_argument` for all three |
| Config-file parser assigning both `reset` and `boot` to `CTRL0` | `GpioConfigError`: channel assigned to both roles |

The service remained connected, and its accepted CTRL0/CTRL1 states and
commanded boot mode matched the pre-request snapshot. It was stopped after
the probes. No control-line voltage or impedance was measured in this run;
the result supports host/service validation and configuration assignment
rejection, not an independent physical no-glitch or contention test. Runtime
movement of a role between channels is intentionally accepted by the Phase 1
contract and was not treated as a duplicate assignment.

The same acceptance audit found that the validated `dut_io_voltage` value was
not consumed after TOML parsing. Consequently, an Enhanced service with a
configured serial port could open the Debug Helper with no trusted voltage
declaration, and a runtime GPIO-mode request could reach the transport in that
state. Two focused regression tests reproduced those paths before correction.
The service composition now requires `hardware.dut_io_voltage` before opening
a configured Enhanced serial port, and `DeviceCoreRuntime` rejects GPIO-mode
configuration before transport dispatch when the declaration is absent. The
existing configuration parser rejects declarations below 1.8 V, above 5.0 V,
non-finite, boolean, or nonnumeric. This closes the host's trusted-declaration
gate allowed by `docs/phase1_implementation_spec.md`; it does not claim that
firmware measures the physical rail or detects a mismatch between declared and
actual voltage. A short positive Pico 2 check then started the Enhanced service
with the local trusted declaration set to 3.3 V, reported the expected
`dutchmate-rp2350` development identity and all five capabilities with zero
reported loss, and stopped cleanly. No control mapping was applied in that
positive startup check.

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

## Loaded Missing-DUT_VIO Isolation Sweep

On 2026-09-16, the missing-supply check was repeated with a defined load and
all DUT connections removed. Pico 1 UART, controls, and common-ground wiring
were disconnected; external pull-ups and the normal `DUT_VIO` source were
removed. Pico 2 remained USB-powered, and Device Core remained stopped.

Initial DMM readings relative to prototype ground were:

| Point | Reading |
|---|---:|
| Pico 2 `3V3(OUT)` | 3.3 V |
| `DUT_VIO` | 0.0 V |
| `DBG_UART_IF_EN` | 0.0 V |
| `DBG_INPUT_IF_EN` | 0.0 V |
| `DBG_CTRL_EN0`–`DBG_CTRL_EN3` | 0.0 V each |

A current-limited 1.80 V source was then connected through a 10 kOhm series
resistor to one external signal at a time. A separate 10 kOhm resistor loaded
`DUT_VIO` to ground, and the DMM black lead remained on J1 pin 1 ground. The
first unloaded attempt put both `DUT_CTRL0` and the otherwise floating
`DUT_VIO` rail at 1.8 V; both returned to 0.0 V when the source was removed.
That floating-rail observation was treated as inconclusive and replaced by the
loaded method rather than accepted as a back-power result.

Under the loaded method, every external signal below remained at 1.8 V while
`DUT_VIO` remained at 0.0 V:

| Translator path | External signals checked |
|---|---|
| `SN74LV4T125PWR` control outputs | `DUT_CTRL0`, `DUT_CTRL1`, `DUT_CTRL2`, `DUT_CTRL3` |
| `TXU0104PWR` DUT-side inputs | `DUT_EVENT0`, `DUT_EVENT1`, `DUT_EVENT2`, `DUT_EVENT3` |
| `TXU0202DCUR` opposite-direction UART channels | `DUT_UART_RX`, `DUT_UART_TX` |

No injected line showed a reported voltage drop through its 10 kOhm source
resistor, no loaded `DUT_VIO` rise was observed, and the debugger 3.3 V rail
remained present. Together with the exact-low enable readings, this passes the
missing-`DUT_VIO` high-impedance/disabled-interface checklist item for all ten
external signal lines and supplies loaded evidence for the DUT-side-supply-
absent half of the translator isolation check. Measurement resolution and DMM
calibration remain unrecorded, and source current was not measured. This result
does not close debugger-3.3-V-absent isolation, all-order power sequencing,
hot-plug, ESD clamping, or absolute leakage-current checks.

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
| Pico `3V3(OUT)` | 0.13 V | Initially inconclusive; resolved by the later loaded check |
| Pico `VSYS` | 0 V | No observed back-powering |
| Pico `VBUS` | 0 V | No observed back-powering |

The current-budget result passes its numeric target. The 0.13 V reading on
`3V3(OUT)` was initially deferred rather than dismissed as meter error. The
later 10 kOhm source-impedance check resolves this specific observation while
retaining the instrument limitations.

## DUT-Powered, Debugger-Unpowered Pulled-Control Isolation At 1.8 V

Setup:

- Pico USB disconnected and Device Core stopped;
- Pico 1, UART, and event connections disconnected;
- bench supply connected from `DUT_VIO` to common ground and set to 1.80 V
  with a 1 mA current limit;
- each of `DUT_CTRL0` through `DUT_CTRL3` pulled up to `DUT_VIO` through its
  own 10 kOhm resistor.

| Measurement | Result | Assessment |
|---|---:|---|
| `DUT_VIO` | 1.8 V | Expected |
| `DUT_CTRL0`-`DUT_CTRL3` | Approximately 1.8 V each | Every disabled control output retained the external pull-up level |
| Pico `3V3(OUT)` | Approximately 0.0 V | No measurable debugger-rail back-power |
| Pico `VSYS` | Approximately 0.0 V | No measurable debugger-rail back-power |
| Pico `VBUS` | Approximately 0.0 V | No measurable debugger-rail back-power |

This passes the static debugger-3.3-V-absent isolation check for all four
control outputs at the representative 1.8 V point: every output remained
externally pullable high while none of the measured Pico power rails rose. It
does not capture insertion/removal transients, directly load the UART or event
signals in this supply direction, or replace the remaining all-order power-
sequencing and hot-plug checks.

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

## UART Loopback At 2.5 V And 460800 Baud

With the service stopped and the UART loopback unchanged, the bench supply was
turned off, set to 2.50 V with its 1 mA current limit retained, and turned back
on. `DUT_VIO` measured 2.5 V and the settled idle current measured 39.96 uA,
below the documented 60 uA target.

A fresh command-ingress probe passed before the active run. A TX-enabled
Enhanced epoch then sent the 33-byte payload
`DUTCHMATE_LOOPBACK_2V5_460800_A5\n`. The device reported success with all 33
bytes accepted and device completion timestamp 979438617 us. Capture
`20260910T193944Z-07bc3bc9` stored an exact 33-byte match, including the final
LF, and completed with:

- `loss_status = none_reported` and zero dropped bytes;
- no overflow, interruption, resume, or truncation;
- one Enhanced segment with RP2350 device-timer provenance; and
- a 33-byte RX high-water mark that returned to zero occupancy.

This passes one functional transmit/receive integrity check at 2.5 V and
460800 baud. It does not validate electrical margins, cable-length limits,
other baud rates, or the remaining 3.3 V and 5.0 V operating points.

## UART Loopback At 3.3 V And 460800 Baud

With the service stopped and the UART loopback unchanged, the bench supply was
turned off, set to 3.30 V with its 1 mA current limit retained, and turned back
on. `DUT_VIO` measured 3.3 V and the settled idle current measured 54.47 uA,
below the documented 70 uA target.

A TX-enabled Enhanced epoch sent the 33-byte payload
`DUTCHMATE_LOOPBACK_3V3_460800_A5\n`. The device reported success with all 33
bytes accepted and device completion timestamp 1420220290 us. Capture
`20260910T194704Z-334fb7df` stored an exact 33-byte match, including the final
LF, and completed with:

- `loss_status = none_reported` and zero dropped bytes;
- no overflow, interruption, resume, or truncation; and
- one Enhanced segment with RP2350 device-timer provenance.

This passes one functional transmit/receive integrity check at 3.3 V and
460800 baud. It does not validate electrical margins, cable-length limits,
other baud rates, or the remaining 5.0 V operating point.

## UART Loopback At 5.0 V And 460800 Baud

With the service stopped and the UART loopback unchanged, the bench supply was
turned off, set to 5.00 V with its 1 mA current limit retained, and turned back
on. `DUT_VIO` measured 5.0 V and the settled idle current measured 79.66 uA,
below the documented 100 uA target.

A TX-enabled Enhanced epoch sent the 33-byte payload
`DUTCHMATE_LOOPBACK_5V0_460800_A5\n`. The device reported success with all 33
bytes accepted and device completion timestamp 1728627013 us. Capture
`20260910T195209Z-b9518e95` stored an exact 33-byte match, including the final
LF, and completed with:

- `loss_status = none_reported` and zero dropped bytes;
- no overflow, interruption, resume, or truncation; and
- one Enhanced segment with RP2350 device-timer provenance.

This passes one functional transmit/receive integrity check at 5.0 V and
460800 baud. Together with the preceding runs, the short-jumper functional
loopback passes at all four supported `DUT_VIO` points. Electrical margins,
cable-length limits, and other required baud rates remain unvalidated.

## Push-Pull Control Sweep At 1.8 V

With `DUT_VIO` supplied at 1.80 V with a 1 mA current limit, the DUT-side UART
loopback installed, and UART TX policy disabled, each physical control channel
was configured in turn as push-pull, active-high, and idle-low. For every
channel, Device Core successfully configured idle-low, asserted active-high,
returned to idle-low, and ended the Enhanced epoch. Target-channel measurements
were:

| Channel | State | Supply current | `DBG_CTRL_ENn` | `DBG_CTRL_nOEn` | `DBG_CTRL_DATAn` | `DUT_CTRLn` |
|---|---|---:|---:|---:|---:|---:|
| `CTRL0` | Idle-low | 68.44 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL0` | Active-high | 68.44 uA | 3.3 V | 0.0 V | 3.3 V | 1.8 V |
| `CTRL0` | Returned idle-low | 68.69 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL0` | Epoch ended | 28.93 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL1` | Idle-low | 68.59 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL1` | Active-high | 68.72 uA | 3.3 V | 0.0 V | 3.3 V | 1.8 V |
| `CTRL1` | Returned idle-low | 68.60 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL1` | Epoch ended | 28.95 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL2` | Idle-low | 68.66 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL2` | Active-high | 68.60 uA | 3.3 V | 0.0 V | 3.3 V | 1.8 V |
| `CTRL2` | Returned idle-low | 68.76 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL2` | Epoch ended | 28.95 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL3` | Idle-low | 68.59 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL3` | Active-high | 68 uA | 3.3 V | 0.0 V | 3.3 V | 1.8 V |
| `CTRL3` | Returned idle-low | 68.54 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| `CTRL3` | Epoch ended | 28.90 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |

Unrelated control enables were measured at 0.0 V during representative checks
of `CTRL1`, `CTRL2`, and `CTRL3`, confirming the expected physical channel
selection. During the controlled `CTRL0` rerun, `DUT_UART_TX` measured 1.8 V
through the installed loopback, Device Core reported zero loss, and the
configured idle-low state remained connected for a five-minute hold.

Two earlier `CTRL0` attempts ended with the firmware in its safe-disabled state
and a raw command-ingress probe receiving no `hello` until USB power was
cycled. The operator later reported removing the UART loopback during the
measurement. That action leaves the enabled `DUT_UART_TX` receiver floating and
can produce a UART error that deliberately ends the firmware epoch. The
successful five-minute run with the loopback continuously installed supports
this explanation, but the exact firmware fault source was not telemetered, so
the correlation is recorded as likely rather than conclusive. In both cases,
all observed control signals returned safely to 0.0 V.

This completes the 1.8 V push-pull low/high and epoch-disable sweep across all
four physical control channels. Push-pull levels at 2.5 V, 3.3 V, and 5.0 V,
open-drain behavior, and loaded high-impedance verification remain open.

## Push-Pull Control At 2.5 V

With the service stopped and the UART loopback retained, `DUT_VIO` was changed
to 2.50 V with the 1 mA current limit retained. The disabled baseline measured
39.99 uA, and all four `DBG_CTRL_ENn` signals were approximately 0.0 V.

`CTRL0` was then configured as push-pull, active-high, and idle-low through a
TX-disabled Enhanced epoch. The RP2350 remained connected and reported zero
loss. Measurements were:

| State | Supply current | `DBG_CTRL_EN0` | `DBG_CTRL_nOE0` | `DBG_CTRL_DATA0` | `DUT_CTRL0` |
|---|---:|---:|---:|---:|---:|
| Idle-low | 93.71 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| Active-high | 94 uA | 3.3 V | 0.0 V | 3.3 V | 2.5 V |
| Returned idle-low | 93.98 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| Epoch ended | 39.98 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |

This passes the representative push-pull low/high and epoch-disable check at
2.5 V. The four-channel 1.8 V sweep already established physical channel
mapping; no result here indicated a channel-specific problem.

## Push-Pull Control At 3.3 V

With the service stopped and the UART loopback retained, `DUT_VIO` was changed
to 3.30 V with the 1 mA current limit retained. The disabled baseline measured
54.43 uA, and all four `DBG_CTRL_ENn` signals measured 0.0 V.

`CTRL0` was then configured as push-pull, active-high, and idle-low through a
TX-disabled Enhanced epoch. The RP2350 remained connected and reported zero
loss. Measurements were:

| State | Supply current | `DBG_CTRL_EN0` | `DBG_CTRL_nOE0` | `DBG_CTRL_DATA0` | `DUT_CTRL0` |
|---|---:|---:|---:|---:|---:|
| Idle-low | 122.60 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| Active-high | 122.62 uA | 3.3 V | 0.0 V | 3.3 V | 3.3 V |
| Returned idle-low | 122.70 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| Epoch ended | 54.60 uA | 0.0 V | 0.0 V | 0.0 V | 0.0 V |

This passes the representative push-pull low/high and epoch-disable check at
3.3 V. The enabled current is consistent with the expected 47 kOhm `/OE`
pull-up load within component and instrument tolerance.

## Push-Pull Control At 5.0 V

The Nordic PPK2 supplied `DUT_VIO` at 5.0 V, measured its current, and retained
the 1 mA current limit. With the service stopped and the UART loopback retained,
the disabled baseline measured 79.75 uA and all interface/control enables
measured 0.0 V.

`CTRL0` was then configured as push-pull, active-high, and idle-low through a
TX-disabled Enhanced epoch. Measurements were:

| State | Supply current | `DBG_CTRL_EN0` | `DBG_CTRL_nOE0` | `DBG_CTRL_DATA0` | `DUT_CTRL0` |
|---|---:|---:|---:|---:|---:|
| Idle-low | 184.12 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |
| Active-high | 243.26 uA | 3.3 V | 0.0 V | 3.3 V | 5.0 V |
| Returned idle-low | 183.96 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V |

The approximately 59 uA active-high increase remained at 243 uA with the DMM
completely disconnected. To distinguish a `CTRL0` path fault from translator
input behavior, `CTRL1` was configured identically in a fresh epoch. Its
idle-low current measured 183.44 uA and active-high current measured 243.13 uA.
The repeat therefore reproduced the state-dependent increase on a second U3
channel rather than following the DMM or `CTRL0` ESD/output path. This is
consistent with the
[TI `SN74LV4T125` datasheet](https://www.ti.com/lit/ds/symlink/sn74lv4t125.pdf)
additional-static-supply-current behavior when a 3.3 V input drives high while
U3 is supplied at 5 V; TI specifies up to 1.5 mA per input at the nearby 3.4 V
input/5.5 V supply test point.

During the `CTRL1` discriminator, one return-to-normal command was issued from
a sandbox that could not reach the already running local service and therefore
did not reach the device. The measured state correctly remained active-high at
243.10 uA, 3.3 V on `DBG_CTRL_DATA1`, and 5.0 V on `DUT_CTRL1`. Reconnecting
through the service and reapplying the mapping restored idle-low: current
measured 183.78 uA, `DBG_CTRL_EN1` remained 3.3 V, and both
`DBG_CTRL_DATA1` and `DUT_CTRL1` measured 0.0 V. This was a host test-control
mistake, not a firmware rejection or unexplained electrical transition.

After the final clean epoch shutdown, current returned to 79.79 uA and
`DBG_CTRL_EN1`, `DBG_CTRL_nOE1`, `DBG_CTRL_DATA1`, `DUT_CTRL1`, and every
unrelated enable measured 0.0 V.

This passes the representative push-pull low/high and epoch-disable check at
5.0 V. Together with the four-channel 1.8 V sweep and representative 2.5 V and
3.3 V checks, push-pull control levels now pass across all supported
`DUT_VIO` points.

## Open-Drain Reset With A Representative Pull-Up

With the Enhanced service stopped, the Nordic PPK2 supplied `DUT_VIO` at
1.80 V with a 1 mA current limit. The UART loopback remained installed, and an
external 10 kOhm resistor connected `DUT_CTRL0` to `DUT_VIO` to represent a DUT
reset pull-up. A Saleae logic analyzer observed `DUT_CTRL0` during the dynamic
checks.

The initial disabled baseline measured 28.95 uA, `DUT_VIO = 1.8 V`, and
`DUT_CTRL0 = 1.8 V`. All unrelated enables measured 0.0 V. The first reported
`DBG_CTRL_nOE0 = 0.0 V` was inconsistent with both the pulled-up DUT output and
the later repeatable `/OE` measurements, so that isolated reading is not used
as acceptance evidence.

`CTRL0` was configured as active-low `open_drain` through a TX-disabled
Enhanced epoch. Configuration entered the released state without a transient
assertion:

| State | Supply current | `DBG_CTRL_EN0` | `DBG_CTRL_nOE0` | `DBG_CTRL_DATA0` | `DUT_CTRL0` | `DBG_UART_IF_EN` |
|---|---:|---:|---:|---:|---:|---:|
| Configured release | 29.34 uA | 0.0 V | 1.8 V | 0.0 V | 1.8 V | 3.3 V |
| Held assertion | 239.44 uA | 3.3 V | 0.0 V | 0.0 V | 0.0 V | 3.3 V |
| Returned release | 30 uA | 0.0 V | 1.8 V | 0.0 V | 1.8 V | 3.3 V |
| Epoch ended | 29.87 uA | 0.0 V | 1.8 V | 0.0 V | 1.8 V | 0.0 V |

Every unrelated enable measured 0.0 V in each representative state. A
temporary `boot` role mapping held the identical open-drain electrical states
long enough for static measurement. The Saleae showed both assertion and
release transitions as qualitatively clean; rise time was not available.

After restoring the `reset` role, a commanded 250 ms reset pulse measured
250.853 ms on the Saleae, transitioned cleanly from 1.8 V to 0.0 V and back,
averaged 240 uA while asserted, and returned to 30 uA after release. The host
received the successful response with a device completion timestamp.

An earlier pre-fix 10,000 ms reset attempt did not provide pulse evidence. The
public validation and service schema accepted 1 through 10,000 ms, but the
Enhanced control adapter used a fixed 1.0-second response timeout. The host
returned HTTP 502 `timeout`, terminated that transport epoch, and reconnected
in the released state before a manual reading was obtained. The first host-side
correction made the Enhanced adapter wait for the pulse duration plus a bounded
0.5-second completion margin. A 2,000 ms HIL retry then exposed the independent
fixed 2.0-second CLI-to-service HTTP timeout while the service and Enhanced
transport correctly remained connected.

The CLI correction now waits for the pulse duration plus a bounded 1.0-second
margin, retaining its existing 2.0-second minimum. With both timeout layers
corrected, a 2,000 ms command completed successfully, measured 2.000 seconds on
the Saleae, held `DUT_CTRL0` at 0.0 V with approximately 240 uA asserted
current, returned to 1.8 V and approximately 30 uA, and retained the same
connected Enhanced epoch. The maximum 10,000 ms command then also completed
successfully: the Saleae measured 10.00 seconds with clean 1.8 V-to-0.0 V-to-
1.8 V transitions, PPK2 current measured approximately 240 uA asserted and
30 uA released, and a following status request confirmed the transport remained
connected with `CTRL0` still configured.

This passes representative 1.8 V open-drain reset assertion, release, and
loaded high-impedance behavior against a 10 kOhm DUT-side pull-up. Broader
high-impedance, power-isolation, and voltage-margin checks remain open.

## Control High Impedance During Debugger Reset

With the Enhanced service stopped, the Nordic PPK2 continued to supply
`DUT_VIO = 1.8 V` with a 1 mA current limit. Pico USB and the UART loopback
remained connected. The external 10 kOhm pull-up and Saleae input were moved
across `DUT_CTRL0` through `DUT_CTRL3` one channel at a time. For each channel,
the Pico 2 `RUN` input was held at ground for approximately one second and then
released.

| Channel | DUT output during reset | Target enable/data | Other enables | Supply current | USB after release |
|---|---:|---:|---:|---:|---|
| `CTRL0` | 1.8 V, no low glitch | 0.0 V | 0.0 V | 30 uA | Reappeared |
| `CTRL1` | 1.8 V, no low glitch | 0.0 V | 0.0 V | 30 uA | Reappeared |
| `CTRL2` | Same passing behavior | 0.0 V | 0.0 V | 30 uA | Reappeared |
| `CTRL3` | Same passing behavior | 0.0 V | 0.0 V | 30 uA | Reappeared |

For `CTRL0`, the target measurements explicitly covered `DBG_CTRL_EN0` and
`DBG_CTRL_DATA0`; `CTRL1` explicitly covered the corresponding two target
signals. For `CTRL2` and `CTRL3`, the operator reported the same behavior as
the preceding explicitly enumerated check. The externally pulled-up DUT output
remaining continuously at 1.8 V without pull-up current appearing in the PPK2
reading demonstrates that the corresponding translator output did not pull the
line low during debugger reset.

This passes the section 14 requirement that every control output remain
high-impedance during debugger reset at the representative 1.8 V operating
point and 10 kOhm load. It does not replace the remaining missing-supply,
hot-plug, or cross-voltage isolation checks.

## Loaded 3V3 Back-Power Check At 1.8 V

The deferred source-impedance check was repeated with Pico USB disconnected,
the Saleae signal leads disconnected, common ground retained, and the Nordic
PPK2 supplying `DUT_VIO = 1.8 V` with a 1 mA current limit. Pico `VSYS` and
`VBUS` were first verified at 0.0 V. The DMM remained the older, uncalibrated
unit whose make/model, accuracy, and input impedance are unknown.

| Measurement | Unloaded | 10 kOhm from Pico pin 36 to ground | Assessment |
|---|---:|---:|---|
| `DUT_VIO` | Not re-recorded | 1.8 V | Supply remained stable under load |
| PPK2 average current | 75 uA | 75 uA | No material load-correlated increase |
| PPK2 maximum current | 85 uA | 82 uA | No material load-correlated increase |
| Pico `3V3(OUT)` | 0.13 V | 0.02 V | Collapsed below the 0.10 V investigation threshold |
| Pico `VSYS` | 0.0 V | 0.0 V | No observed back-powering |
| Pico `VBUS` | 0.0 V | 0.0 V | No observed back-powering |

The loaded voltage corresponds to approximately 2 uA through 10 kOhm. Its
collapse from 0.13 V to 0.02 V without a material change in PPK2 current passes
this debugger-unpowered back-power check as high-impedance leakage or instrument
offset. The result is explicitly instrument-limited because the DMM identity,
calibration, accuracy, and input impedance remain unknown.

The absolute 75 uA current did not reproduce the earlier 25.2 uA idle result.
That difference was not isolated during this source-impedance check. It does
not change the no-load versus loaded conclusion, but it remains evidence to
correlate during later controlled idle/load measurements.

## Current Decision

`in_progress`

- The prototype identity and initial safe-state observations are recorded.
- The committed Revision A table, Eagle schematic/board, and RP2350 overlay
  agree on all 17 mappings, and the design files contain the five provisional
  logic-device references. Populated-device markings and physical continuity
  remain unaudited and were explicitly deferred by the user on 2026-09-16.
- Missing/out-of-range trusted voltage declarations and malformed/duplicate
  control mappings are rejected before opening the Enhanced device or changing
  accepted control state, as applicable. No physical voltage/glitch measurement
  was made during the configured-rejection run.
- With debugger USB powered and `DUT_VIO` absent, exact enable readings were
  low and a loaded 1.8 V/10 kOhm injection sweep covered every control, event,
  and UART external signal. Each line retained 1.8 V while a separate 10 kOhm
  load held `DUT_VIO` at 0.0 V. This passes the loaded missing-supply safe-state
  gate; absolute leakage remains open.
- With debugger USB absent and `DUT_VIO` supplied at 1.8 V, all four control
  outputs retained their individual external 10 kOhm pull-ups at approximately
  1.8 V while Pico `3V3(OUT)`, `VSYS`, and `VBUS` remained approximately
  0.0 V. This passes the static debugger-supply-absent control-output isolation
  check. Transition sequencing and direct UART/event loading in this supply
  direction remain open.
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
- The same loopback passed an exact 33-byte check at 2.5 V and 460800 baud with
  zero reported loss or overflow; 39.96 uA idle current was within budget.
- The same loopback passed an exact 33-byte check at 3.3 V and 460800 baud with
  zero reported loss or overflow; 54.47 uA idle current was within budget.
- The same loopback passed an exact 33-byte check at 5.0 V and 460800 baud with
  zero reported loss or overflow; 79.66 uA idle current was within budget.
- All four control channels passed configured push-pull idle-low, active-high,
  return-to-idle, and epoch-disable checks at 1.8 V. Representative unrelated
  enables remained at 0.0 V, and the controlled `CTRL0` run stayed connected
  with zero reported loss for five minutes.
- Two safe-disabled `CTRL0` interruptions correlate with removing the UART
  loopback during an active epoch. The continuously installed-loopback rerun
  did not reproduce the interruption; the exact firmware fault source was not
  telemetered.
- Representative `CTRL0` push-pull idle-low, active-high, return-to-idle, and
  epoch-disable checks passed at 2.5 V. The high output measured 2.5 V, enabled
  current remained at 93.71–94 uA, and the disabled current returned to
  39.98 uA.
- Representative `CTRL0` push-pull idle-low, active-high, return-to-idle, and
  epoch-disable checks passed at 3.3 V. The high output measured 3.3 V, enabled
  current remained at 122.60–122.70 uA, and the disabled current returned to
  54.60 uA.
- Representative `CTRL0` push-pull idle-low, active-high, and return-to-idle
  checks passed at 5.0 V. A second-channel discriminator confirmed that the
  roughly 59 uA increase when the 3.3 V translator input was high followed U3's
  expected state-dependent supply current rather than the DMM or one physical
  channel. The high output measured 5.0 V, and the final clean shutdown returned
  current to 79.79 uA with all measured control and unrelated enable signals at
  0.0 V.
- At 1.8 V, `CTRL0` passed representative open-drain assertion and release
  against an external 10 kOhm DUT-side pull-up. Released current measured
  29.34–30 uA with `DUT_CTRL0 = 1.8 V`; asserted current measured
  239.44–240 uA with `DUT_CTRL0 = 0.0 V`. A 250 ms reset command measured
  250.853 ms with clean edges, and final shutdown returned to 29.87 uA with all
  enables low. A pre-fix 10-second attempt exposed fixed timeout layers in both
  the Enhanced adapter and CLI HTTP client. After duration-aware timeout fixes,
  2.000-second and maximum 10.00-second pulses completed successfully with
  clean edges, approximately 240 uA asserted current, return to approximately
  30 uA, and no Enhanced transport disconnect.
- All four DUT control outputs remained at the externally pulled-up 1.8 V level
  without a low glitch while the Pico 2 was held in reset through `RUN`.
  Target enable/data signals and every unrelated enable remained 0.0 V, PPK2
  current stayed near 30 uA, and the RP2350 USB device reappeared after each
  release. This passes the every-control-output debugger-reset high-impedance
  item at the representative 1.8 V operating point and 10 kOhm load.
- The debugger-unpowered `3V3(OUT)` source-impedance check passed at 1.8 V:
  loading the 0.13 V observation through 10 kOhm collapsed it to 0.02 V while
  average PPK2 current remained 75 uA. This result remains instrument-limited,
  and broader power-isolation checks remain open.
- This record now supports the section 14 push-pull high/low-level item across
  every supported `DUT_VIO` and representative open-drain reset assertion and
  release against a DUT-side pull-up. It also supports every control output
  remaining high-impedance during debugger reset at the representative 1.8 V
  point. The remaining Revision A prototype checklist items remain open.
