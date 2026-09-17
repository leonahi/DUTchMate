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

## Pulled-Control Supply-Order Sequence At 1.8 V

The preceding setup was retained with one 10 kOhm pull-up from each DUT control
output to `DUT_VIO`. Device Core remained stopped throughout. The operator
performed both supply orders and reported these settled post-transition levels:

| Ordered state or transition | `DUT_VIO` | `DUT_CTRL0`-`DUT_CTRL3` | Pico rails | Measured enables |
|---|---:|---:|---:|---:|
| VIO on, debugger off | 1.8 V | Approximately 1.8 V each | `3V3(OUT)`, `VSYS`, and `VBUS` approximately 0.0 V | Not re-recorded |
| Connect debugger USB with VIO on | 1.8 V | Approximately 1.8 V each | `3V3(OUT)` 3.3 V | All 0.0 V |
| Disconnect debugger USB with VIO on | 1.8 V | Approximately 1.8 V each | `3V3(OUT)`, `VSYS`, and `VBUS` 0.0 V | Not re-recorded |
| Debugger USB on, VIO off | 0.0 V | 0.0 V each | `3V3(OUT)` approximately 3.3 V | All approximately 0.0 V |
| Apply VIO with debugger USB on | Approximately 1.8 V | Approximately 1.8 V each | `3V3(OUT)` approximately 3.3 V | All approximately 0.0 V |
| Remove VIO with debugger USB on | Approximately 0.0 V | Approximately 0.0 V each | `3V3(OUT)` approximately 3.3 V | All approximately 0.0 V |

These results pass the settled rail, external pull-up, and measured-enable
expectations for both power-up and power-down orders. They do not constitute a
transient waveform capture. The reported enable set covered `DBG_CTRL_EN0`
through `DBG_CTRL_EN3`, `DBG_UART_IF_EN`, and `DBG_INPUT_IF_EN`; it did not
include the four active-low `DBG_CTRL_nOE0` through `DBG_CTRL_nOE3` nodes.
Direct `/OE` measurements through both power orders were therefore performed
in the following follow-up.

### Active-Low Control `/OE` Follow-Up

The same sequence was repeated while directly measuring all four
`DBG_CTRL_nOE0` through `DBG_CTRL_nOE3` nodes:

| Ordered state or transition | `DBG_CTRL_nOE0`-`DBG_CTRL_nOE3` | `DUT_CTRL0`-`DUT_CTRL3` | Pico/debugger state |
|---|---:|---:|---|
| Debugger USB on, then apply VIO | Approximately 1.8 V each | Approximately 1.8 V each | `3V3(OUT)` approximately 3.3 V |
| Remove VIO with debugger USB on | Approximately 0.0 V each | Approximately 0.0 V each | `3V3(OUT)` 3.3 V |
| Debugger USB off, then apply VIO | Approximately 1.8 V each | Approximately 1.8 V each | All Pico power rails approximately 0.0 V |
| Connect debugger USB with VIO on | Approximately 1.8 V each | Approximately 1.8 V each | `3V3(OUT)` approximately 3.3 V and all MCU control enables approximately 0.0 V |
| Disconnect debugger USB with VIO on | Approximately 1.8 V each | Approximately 1.8 V each | All Pico power rails approximately 0.0 V |

These settled measurements pass the section 14 requirement that the
`SN74LVC2G06DBVR` stages leave every `SN74LV4T125PWR` `/OE` pulled high and
every control output disabled through both debugger/VIO power-up and power-down
orders. The active-low nodes correctly fell to 0.0 V only when their VIO
pull-up rail was absent. This result does not replace transient waveform or
hot-plug capture.

## DUT-Powered, Debugger-Unpowered UART/Event Isolation At 1.8 V

Setup:

- Pico USB disconnected and Device Core stopped;
- `DUT_VIO` supplied at 1.80 V with a 1 mA current limit;
- control pull-ups removed;
- 10 kOhm load connected from Pico `3V3(OUT)` to ground;
- a second 10 kOhm resistor moved from `DUT_VIO` to each UART and event
  connector signal in turn.

| Externally pulled-up signal | Signal result | Loaded Pico `3V3(OUT)` |
|---|---:|---:|
| `DUT_EVENT0` | Approximately 1.8 V | Approximately 0.0 V |
| `DUT_EVENT1` | Approximately 1.8 V | Approximately 0.0 V |
| `DUT_EVENT2` | Approximately 1.8 V | Approximately 0.0 V |
| `DUT_EVENT3` | Approximately 1.8 V | Approximately 0.0 V |
| `DUT_UART_TX` | Approximately 1.8 V | Approximately 0.0 V |
| `DUT_UART_RX` | Approximately 1.8 V | Approximately 0.0 V |

After the sweep, Pico `VSYS` and `VBUS` also measured approximately 0.0 V.
This passes the static debugger-supply-absent isolation check for the UART and
event connector paths at 1.8 V. Combined with the preceding four-control
pull-up sweep, every external digital signal has now been loaded high with the
debugger supply absent without a measurable rise on the Pico rails; the UART/
event portion additionally applied a defined 10 kOhm load to `3V3(OUT)`. This
does not replace hot-plug/transient capture, absolute leakage measurement, or
ESD validation.

## Repeated Unloaded Supply Hot-Plug At 1.8 V

All external digital signals and temporary resistors were disconnected and
Device Core remained stopped. Common ground was retained throughout.

For the VIO hot-plug half, Pico USB remained connected and the 1.80 V source
remained enabled with a 1 mA current limit. Only the positive `DUT_VIO` lead
was connected and disconnected five times, with approximately two seconds in
each state. The operator reported identical behavior in all five cycles:

| State | `DUT_VIO` | Pico `3V3(OUT)` | All interface/control enables |
|---|---:|---:|---:|
| VIO connected | Approximately 1.8 V | Approximately 3.3 V | Approximately 0.0 V |
| VIO disconnected | Approximately 0.0 V | Approximately 3.3 V | Approximately 0.0 V |

For the debugger hot-plug half, `DUT_VIO` remained continuously supplied at
1.80 V while Pico USB was disconnected and reconnected five times. Every
connection enumerated normally, and all five cycles behaved identically:

| State | `DUT_VIO` | Pico rails | All interface/control enables | `DBG_CTRL_nOE0`-`DBG_CTRL_nOE3` |
|---|---:|---:|---:|---:|
| USB connected | Approximately 1.8 V | `3V3(OUT)` approximately 3.3 V | Approximately 0.0 V | Approximately 1.8 V each |
| USB disconnected | Approximately 1.8 V | `3V3(OUT)`, `VSYS`, and `VBUS` approximately 0.0 V | Unpowered; not re-recorded | Approximately 1.8 V each |

This passes repeated unloaded 1.8 V supply insertion and removal in both
orders using settled voltage and enumeration observations. No current-limit
activation or abnormal condition was reported. The test did not capture
transition waveforms or exercise hot-plug with external signal loads or an
active DUT cable, so those broader connector cases remain open.

## Loaded UART Signal Hot-Plug At 3.3 V (2026-09-16)

The Pico 1 `phase1-enhanced-460800-001` fixture and normal Pico 2 Debug Helper
were USB powered, with common ground and external `DUT_VIO = 3.3 V` retained.
Pico 1 GP0 connected to J1 pin 4 (`DUT_UART_TX`), and GP1 to J3 pin 4
(`DUT_UART_RX`). Only those two signal wires were disconnected/reconnected;
this was not a whole-connector or ground-disconnection test. Enhanced service
used `/dev/cu.usbmodem11201` at 460800 baud with UART TX enabled.

| Cycle | Session | Observed result |
|---|---|---|
| 1 | `20260916T213110Z-dbeb6b07` | Baseline PONG, transition bytes, first post-reconnect PING returned `E_COMMAND_001`, second returned PONG without reset |
| 2 | Same session | Additional transition bytes retained; recovery sends occurred after the capture ended, so recovery timing is inconclusive |
| 3 | `20260916T214409Z-5fedcd96` | Baseline PONG, five NUL bytes, first post-reconnect PING returned `E_COMMAND_001`, second returned PONG without reset |

Cycle 3's baseline send was acknowledged at 21:44:15.602950 UTC; its two
recovery sends were acknowledged at 21:45:29.212392 and 21:45:35.662501 UTC.
All three five-byte `PING\n` payloads have recorded forced-send attempts and
successful results in that session. The raw received sequence was:

```text
DMF/1 PONG\n
\x00\x00\x00\x00\x00DMF/1 ERROR COMMAND code=E_COMMAND_001\n
DMF/1 PONG\n
```

The Debug Helper remained connected with zero reported receive-buffer loss.
Cycle 3 completed at 21:47:09 UTC with one segment, 66 raw UART bytes, no
interruption, overflow, or truncation, and the detected `ERROR` at segment 0 /
event 9. Local ignored artifacts are retained under
`.dutchmate/sessions/20260916T214409Z-5fedcd96/`:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `0116bc6622bac996e34be291fb37eb5728c018c4547ebfe70b1ad7b88f88ea71` |
| `uart_raw.log` | `219c31663e0eddac4b4e15ea4c6b6cd771b6974db607ad290e03e33887cda661` |
| `uart_events.jsonl` | `995c7e89812461131b436ad567372c4085f24ba4ac4eddc88881dc11848aa99f` |
| `hardware_events.jsonl` | `82f58d6577db3f07ab68485c2eb4612c3ab828195a7d91d1a52aadae5a62b580` |

Exact raw bytes, three send attempts/results, and terminal metadata were
verified from these artifacts. Device Core was stopped after retrieval.

This demonstrates recovery after one rejected command, not corruption-free
hot-plug. The fixture's newline-delimited command loop clears its buffer after
each newline; the observed rejection/recovery is consistent with extra bytes
preceding the first command. The exact bytes entering Pico 1 RX and their
electrical source were not captured, so this remains a hypothesis rather than
a confirmed floating-input or firmware fault. Raw transition bytes must remain
in DUTchMate evidence; zero buffer loss does not imply uncorrupted UART data.

After cycle 2, the user connected `DUT_CTRL0` to Pico 1 RUN. Runtime `CTRL0`
was configured as `reset`, open-drain, active-low. Standalone reset during a
capture was correctly rejected with HTTP 409 `capture_active`; the dedicated
boot-test `20260916T214156Z-ad4b412e` then captured the reset-leading NUL and
exact 62-byte boot marker. Cycle 3 retained this reset wiring but needed no
reset during recovery. CTRL1-3 remained unconfigured.

### Correction Of Capture-Timing Interpretations

Several earlier empty captures were incorrectly described during the bench
session as missing responses or a recurring first-command fault. Their send
acknowledgements were outside their capture windows:

| Session | Capture end (UTC) | Send acknowledgement (UTC) |
|---|---|---|
| `20260916T212316Z-603b59ec` | 21:23:21 | 21:23:21.730258 |
| `20260916T213110Z-dbeb6b07` (cycle 2 retries) | 21:36:10 | 21:36:19.301966 and 21:36:22.842077 |
| `20260916T213642Z-ae2d3714` | 21:36:48 | 21:36:50.905055 |
| `20260916T214232Z-e4258b21` | 21:42:39 | 21:42:54.031973 |

The affected sessions have no corresponding `uart_tx_attempt` records for
those late sends. Empty evidence cannot establish no response, failed wiring,
or a reset requirement. The later in-window retry in
`20260916T214324Z-47d83c37` contains exact `DMF/1 PONG\n`. This corrects those
earlier interpretations without discarding the actual cycle 1/3 hot-plug
corruption or the separate earlier first-command anomaly.

## RX-Only Hot-Plug With Continuous Digital Trace (2026-09-17)

The same 3.3 V/460800-baud fixture setup was retained. Pico 2 enumerated at
`/dev/cu.usbmodem1301` with unchanged serial `FA63A4D787572B33`. CTRL0 remained
physically connected to Pico 1 RUN but was unconfigured in the new service
epoch; no reset was issued. Saleae D1 (`PICO1_RX`) probed Pico 1 GP1 and D2
(`PICO1_TX`) probed GP0. Only J3 pin 4 to GP1 was disconnected/reconnected;
D1 stayed attached to GP1 and the GP0 return path stayed connected.

The operator supplied a continuous 25 MS/s digital export covering baseline,
wire movement, and both recovery commands. The unchanged CSV is retained at
`evidence/20260917-rx-only-hotplug-digital.csv`, SHA-256
`549555376fc0c5e2e46cf8fe05312382fc0c69267b949c1a922d6df9cfb2507c`.
It contains 5,134 timestamp/state rows for both channels, from 0 to
244.310343680 seconds. Sampling UART bit centers at 460800, 8-N-1 gives:

| Trace time (s) | Pico 1 RX (D1) | Pico 1 TX (D2) |
|---|---|---|
| 42.079215000 / 42.080219480 | Clean `PING\n` | `DMF/1 PONG\n` |
| 172.295236280-173.358330840 | Irregular transitions and extended low intervals during the wire-change interval | Stayed idle-high |
| 214.910277520 / 214.911095400 | Clean `PING\n` | `DMF/1 ERROR COMMAND code=E_COMMAND_001\n` |
| 221.776993400 / 221.777749160 | Clean `PING\n` | `DMF/1 PONG\n` |

Both post-reconnect command frames have valid stop bits, as do all response
frames. Noise-interval decoder output is not a reliable count of bytes accepted
by the RP2040 UART; the exported logic transitions do not reveal analog voltage
or the exact contact-open/contact-close instants.

Session `20260917T084116Z-b6095f44` recorded all three forced `PING\n` attempts
and the matching 61-byte response sequence. The corresponding send completion
times were 08:41:22.361955, 08:44:15.191065, and 08:44:22.065929 UTC. It
completed at 08:46:16 UTC with one segment, zero reported buffer loss, no
overflow/interruption, and a detected fixture command error.

This isolates the reproduced command rejection to disturbing the fixture RX
connection: GP1 had spurious digital activity before a clean command, while
the untouched return path carried clean responses. The fixture accumulates
bytes until newline (or discards an overlong command until newline), then
clears that state. Accumulated/discarded input therefore explains the observed
single rejection followed by recovery. An undriven RX input is the leading
electrical hypothesis; a controlled bias test is needed to distinguish it from
contact effects and probe/loading influences. This is not evidence that the
Debug Helper transmitted a malformed recovery command.

## RX-Only Hot-Plug With Fixture-Side Pull-Up (2026-09-17)

For the controlled comparison, the operator installed 10 kOhm from Pico 1
GP1 to Pico 1 `3V3(OUT)`. This pull-up and Saleae D1 stayed attached to GP1
while only the J3 pin 4 UART wire was disconnected/reconnected. D2 remained on
GP0, the return path stayed connected, and CTRL0-to-RUN remained unconfigured.
The service was stopped for setup and restarted on `/dev/cu.usbmodem1301`.
The operator confirmed the pull-up was ready but did not supply the requested
numeric GP1 DMM reading; no measured idle voltage is inferred here.

The continuous 25 MS/s export is retained unchanged as
`evidence/20260917-rx-only-hotplug-with-pullup-digital.csv`, SHA-256
`508947e3eb0635f6b68ad50cf66560a50f89b85742d37eeea773919bc5a19a15`.
It has 574 timestamp/state rows, spanning 0 to 201.371156480 seconds.
Bit-center decoding at 460800, 8-N-1 gives:

| Trace time, RX / TX start (s) | Command at GP1 | Response at GP0 |
|---|---|---|
| 41.924846360 / 41.926054680 | `PING\n` (initial baseline) | `DMF/1 ERROR COMMAND code=E_COMMAND_001\n` |
| 62.629883480 / 62.630426760 | `PING\n` (baseline retry) | `DMF/1 PONG\n` |
| 164.448071240 / 164.448775240 | `PING\n` (first after wire change) | `DMF/1 PONG\n` |
| 170.777861600 / 170.778159280 | `PING\n` (second after wire change) | `DMF/1 PONG\n` |

Every one of the 128 RX transitions falls inside those four five-byte command
windows. RX stays digitally high between packets, including the interval in
which the operator reported the disconnect/reconnect. All 20 command bytes
and 72 response bytes have valid stop-bit samples. In contrast, the earlier
no-pull-up trace recorded 4,657 RX transitions in its wire-change interval.
The CSV has no separate contact-state marker, so precise unplug/replug times
are not independently measured.

Session `20260917T085816Z-5c60e312` records the same 72 response bytes and four
successful forced sends. Completion acknowledgements are at 08:58:25.352884,
08:58:46.061847, 09:00:27.881417, and 09:00:34.208825 UTC. Both recovery
commands were inside the active session; no reset or USB reconnect was needed.
The session completed at 09:03:16 UTC with one segment, zero reported buffer
loss, no overflow/interruption, and the baseline error retained. Device Core
was stopped after verification. Local session artifact SHA-256 digests are:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `1dbb281eb9b6250ca6c8cf050a2cf4d550371390dd60d86ee2f6ce4af8129ddf` |
| `uart_raw.log` | `816a35264a40101f1be90427ca2dd1e1f03cb441b5aabd32484ae2d6d6c7dd0f` |
| `uart_events.jsonl` | `952721661b7dcf5868fa9772c402cec9e38be5671ae2ad3af11780b48efd5c87` |
| `hardware_events.jsonl` | `71729138bbe6cd2f9e7b09364b65a0e9a54e74700a5bee3ba7c199f9939a3afb` |

This single comparison strongly supports an undriven fixture RX input as the
cause of the prior RX-only hot-plug disturbance: with the local pull-up, no
extra digital transitions were captured and the first recovery command
succeeded. It is a verified diagnostic mitigation for this setup, not a
production hardware/firmware change or complete hot-plug acceptance. The
initial baseline error persists before wire movement, despite a clean first
PING in this trace; input history before recording and startup behavior remain
unresolved. The opposite UART direction is not covered by this comparison.

## TX-Only Hot-Plug: Digital Trace / Receive Evidence Mismatch (2026-09-17)

The fixture GP1 pull-up remained installed and the GP1 command wire remained
connected. Only Pico 1 GP0 to J1 pin 4 (`DUT_UART_TX`) was disconnected and
reconnected. The intended Saleae D2 placement was directly on J1 pin 4 so it
would remain on the Debug Helper side of the open connection; D1 stayed on
Pico 1 GP1. The exported D2 column retains the name `PICO1_TX`, which does not
independently establish the physical probe location during disconnection.
The operator subsequently confirmed that D2 remained attached to board-side
J1 pin 4 throughout the open-wire interval. The next comparison therefore
adds the translator output at Pico 2 GP1 to observe both ends of this path.

The unchanged supplied export is retained as
`evidence/20260917-tx-only-hotplug-digital.csv`, SHA-256
`e653744327b9336660687037c5754a4e8e9249c054f2944b442035c5f6fb2086`.
It contains 296 timestamp/state rows spanning 0 to 170.427678720 seconds.
Decoding at 460800, 8-N-1 yields only three clean exchanges:

| Command start, D1 (s) | Response start, D2 (s) | Result |
|---|---|---|
| 38.863149000 | 38.864284760 | Baseline PING / PONG |
| 103.365294640 | 103.365652880 | First post-reconnect PING / PONG |
| 109.539601560 | 109.539827600 | Second post-reconnect PING / PONG |

D1 has 96 transitions and D2 has 198; every decoded frame has a valid stop
bit and D2 shows no extra transitions between the three response packets.
Session `20260917T090848Z-ebdef0d3`, however, contains 50 received bytes:
three exact 11-byte PONG responses plus 17 bytes between the baseline and
first recovery response (`00` four times, `FF`, then `00` twelve times).
All three PING sends have successful forced-send records; both recovery
responses arrived without reset or fixture command rejection.

Aligning the first PONG between the two clocks places those extra receive
events at approximately 62.320-69.066 seconds in the CSV. D2 has no transitions
anywhere in 60-90 seconds. The later PONG alignments differ by less than
0.6 ms, so a large capture-window mismatch does not explain the discrepancy.
This does not prove a firmware defect or absence of an electrical disturbance:
probe attachment, thresholds, and behavior across the translator remain
unresolved. No bytes were removed or reclassified as valid fixture output.

The session subsequently recorded `usb_disconnect` at 09:13:27 UTC and ended
at 09:13:32 UTC as `failed`, `reconnect_timeout`, `interrupted=true`, with
`service_unavailable`. The cause/intent of that later disconnection is not
established. The earlier three exchanges and extra bytes remain usable partial
evidence, but this is not a completed uninterrupted acceptance run. There is
one segment, no truncation or overflow, and zero reported receive-buffer loss.
Device Core was found stopped when the investigation resumed.

Local session artifact SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `e601c0e5f1615aaf1a02ea5980490e222f33b27457c0dd1a108487e70b27c6fd` |
| `uart_raw.log` | `e87976b60787c3e5ffd7c055d276a953070f267b34ce0845e1e6603d7fe6d205` |
| `uart_events.jsonl` | `093edec710cca49211f7555e6a3cac2364a35c640b2689c2ea7cb5dc85aeefc7` |
| `hardware_events.jsonl` | `9c74d0d2b208edc7f9089b97b5dc627cd06d3273437ad20b0a894ab7108f084b` |

### Paired-probe retry interrupted before the wire cycle

On 2026-09-17 the operator confirmed probes ready with D1 on Pico 2 GP1
(`DBG_UART_RX`) and D2 retained on J1 pin 4. Session
`20260917T143554Z-0dbaf328` retained exactly `DMF/1 PONG\n`, but the operator
reported that analyzer recording had not started for that baseline and
requested a repeat. No paired trace has been supplied for this attempt.

The 300-second capture started at 14:35:54 UTC and was still reported active
at 14:41:47. Device Core was stopped to restart the capture. Its shutdown log
contains `ValueError: session lifecycle transition requires active state`.
The stored session is `abandoned`, ending at 14:42:19 with
`end_reason=service_restart`. Subsequent Enhanced starts on
`/dev/cu.usbmodem1401` failed with `Timed out waiting for Enhanced hello`.
The cause of these lifecycle and handshake failures is not established.
No fresh baseline or wire-cycle acceptance result was obtained after the
operator started recording again.

### Supplied paired-probe export has unresolved channel mapping

Pico 2 USB power cycling restored the Enhanced handshake. The next capture,
`20260917T144831Z-0f9b7835`, completed its 300-second duration normally.
The supplied `digital_tx_paired.csv` is preserved unchanged as
`evidence/20260917-tx-paired-hotplug-digital.csv`, SHA-256
`913570d658ae8ed7cceeaf21c7d0f2ba7635c7924950b63427b636d2826e97b2`.
Its 296 data rows span 0–190.704517120 seconds; headers remain
`Time [s],PICO1_RX,PICO1_TX`.

| Exchange | First signal: PING start (s) | Second signal: PONG start (s) |
|---|---|---|
| Baseline | 39.657943680 | 39.658149080 |
| First recovery | 141.294255840 | 141.294812760 |
| Second recovery | 151.906170160 | 151.907257760 |

At 460800 8-N-1, the first signal has 96 transitions encoding only three
`PING\n` commands; the second has 198 transitions encoding only three
`DMF/1 PONG\n` responses. All decoded stop bits are valid. There are no
transitions outside those packets. This conflicts with the intended D1
Pico 2 GP1 (`DBG_UART_RX`) / D2 J1 pin 4 receive-path comparison: both ends
should show the fixture replies. The operator subsequently confirmed that D1
had remained on Pico 1 GP1, explaining the command/reply channel difference.
The corrected probe setup was then reported ready with D1 moved to Pico 2 GP1
(physical pin 2) and D2 retained on J1 pin 4. This does not resolve the extra
host receive bytes; the supplied export did not observe Pico 2 GP1.

Host raw evidence contains 39 bytes: the baseline PONG, six bytes
`00 00 00 00 F8 00`, then two recovery PONGs. All three forced sends have
successful attempt/result records. Anchoring the first PONG places the six
extra bytes at approximately CSV seconds 81.232–91.513, when both exported
signals remain high. Later PONG alignment differs by less than 0.9 ms.
The completed session has one segment, zero reported buffer loss, no
overflow, interruption, or truncation. Those flags do not erase the six
unexpected bytes or establish a clean UART wire cycle. This export does not
yet distinguish translator behavior from downstream reception or probing.

### Corrected-probe baseline timeout

With D1 reported moved to Pico 2 GP1 and D2 retained on J1 pin 4, the supplied
`digital_paired_baseline_timeout.csv` contains only its initial and final state:
both channels high at 0 and 94.841077760 seconds, with no transitions.
The unchanged file is retained as
`evidence/20260917-paired-baseline-timeout-digital.csv`, SHA-256
`932f4f76dfa67610c08998da97b3ea5dca09260d704af887fea97d9abd3b21eb`.
Headers still use the older `PICO1_RX,PICO1_TX` labels. Both reported physical
probes monitor the fixture-reply path, so a flat trace cannot establish whether
the outgoing PING reached Pico 1. There is no shared edge for clock alignment.

Session `20260917T151535Z-d8c07406` started at 15:15:35 UTC. Its sole PING
attempt began at 15:15:53.846459 and failed at 15:15:54.952793 with `timeout`
and `bytes_accepted=null`. It recorded `usb_disconnect` at 15:15:55 and ended
at 15:16:00 as `failed`, `reconnect_timeout`, `interrupted=true`. Both UART
artifacts are empty. No UART wire cycle was requested or performed in this
attempt. The session is failed diagnostic evidence, not an acceptance pass.

On review, Device Core remained disconnected while OS serial enumeration still
listed `/dev/cu.usbmodem1401`, serial `FA63A4D787572B33`. A service stop/start
then failed with `Timed out waiting for Enhanced hello`. This does not identify
the cause of the loss of protocol responsiveness or prove a physical USB
disconnect. Device Core was stopped after the failed startup.

Local failed-session SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `022d1aa992c9f92b1b0bc2e697654e28b12c3511b63d7bd987e9c78677372944` |
| `uart_raw.log` and `uart_events.jsonl` (both empty) | `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` |
| `hardware_events.jsonl` | `4b104dfcbc57bea9394a8a806db811404d677f775d42fccd464ea6847b2592f2` |

### Corrected paired-probe TX cycle: receive-pin disturbances captured

After another Pico 2 USB power cycle, the Enhanced handshake succeeded and
passive session `20260917T152150Z-ff5f724f` completed normally in 10 seconds.
It retained ten buffer-status events with advancing timestamps and no reported
loss. The operator then confirmed matching baseline PONGs with D1 on Pico 2
GP1 (physical pin 2, `DBG_UART_RX`) and D2 on J1 pin 4 (`DUT_UART_TX`).
Both probes stayed on the helper side during the reported GP0 wire cycle;
the fixture GP1 pull-up and other UART wire stayed connected.

The supplied `digital_tx_paired_corrected.csv` is preserved unchanged as
`evidence/20260917-tx-paired-corrected-digital.csv`, SHA-256
`fc5b6189da28d24a0c3153fbc1c486e4149953233561d602c7ff96988b827b30`.
Its 224 data rows span 0–316.454993920 seconds. Old column names remain
`PICO1_RX,PICO1_TX`; the physical mapping above is operator-confirmed.
Both channels decode exact `DMF/1 PONG\n` replies near 92.311541,
269.620098, and 297.826016 seconds, all with valid stop bits.

D2 has only the 198 transitions belonging to those replies. D1 has 206
transitions, including these four additional low intervals while D2 stays high:

| D1 falling edge (CSV s) | D1 rising edge (CSV s) | Low duration |
|---|---|---|
| 215.555238360 | 215.555500760 | 262.40 us |
| 215.559416360 | 215.559424640 | 8.28 us |
| 215.559911520 | 233.149373880 | 17.58946236 s |
| 233.225111200 | 233.267936200 | 42.825 ms |

Sampling each falling edge as an 8-N-1 start at 460800 baud produces
`00 F8 00 00`; the three zero candidates have low/invalid stop samples.
These are abnormal waveforms, not four valid UART frames. Their value/order
and relative timing agree with the extra host bytes. The measured low durations
do not independently establish the operator's exact unplug/replug times.

Session `20260917T152349Z-8e3cd93e` ran 15:23:49–15:28:49 UTC and completed
with `duration_elapsed`. Its raw 37 bytes are the baseline PONG, `00 F8 00 00`,
and two recovery PONGs. All three forced-send attempts succeeded. It has one
segment, zero reported receive-buffer loss, and no overflow, interruption,
or truncation. Device Core was stopped after evidence review.

This locates observable disturbances at the MCU receive pin and explains why
raw bytes can appear while the connector probe reports no extra edges. It does
not prove a faulty translator: analog levels/thresholds, the connector-to-input
series path, input bias, and other translator conditions are not distinguished.
The separate USB/protocol responsiveness failure also remains unexplained.

The specified TXU0202 has typical 5 MOhm input pull-downs; TI permits external
pull-ups no greater than 1 MOhm (data sheet section 9.3.1.1). A temporary
10 kOhm pull-up from the helper-side connector input to its existing 3.3 V
`DUT_VIO` is a diagnostic input-bias comparison, not an accepted hardware change.
Populated-part identity remains deferred. Source:
[TI TXU0202 data sheet](https://www.ti.com/lit/ds/symlink/txu0202.pdf).

Local session SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `76cc0cc0b4c148735bd252add5a82111cc3b42522807334d2ae67da321ba310e` |
| `uart_raw.log` | `43853f2145ac3ff984ae1857e4530f047dcc36b6fd3dd479f35222a44e0696dd` |
| `uart_events.jsonl` | `e21bbabf81d65eb3d5ee71172eb87b475d35e9b9555ddf84e27e89c866ea5a2f` |
| `hardware_events.jsonl` | `7d9d780d0bb5099ac56c23fda25a635900a518431eefcee56a3463979adf2ebc` |

### Helper-side 10 kOhm TX pull-up comparison

The operator installed the proposed temporary 10 kOhm resistor from helper J1
pin 4 (`DUT_UART_TX`) to the existing 3.3 V `DUT_VIO`. D1 remained on Pico 2
GP1, D2 remained on J1 pin 4, the fixture GP1 pull-up remained installed, and
both UART wires were initially connected. Device Core opened the same Debug
Helper identity at its re-enumerated `/dev/cu.usbmodem11401` path with all
control channels unconfigured.

During continuous Saleae and host capture, the operator disconnected only Pico
1 GP0 from J1 pin 4, leaving D2 and the added pull-up on the helper side, waited
approximately two seconds, and reconnected GP0. Baseline and both immediate
recovery commands returned exact PONG responses.

The supplied `digital_tx_paired_with_pullup.csv` is preserved unchanged as
`evidence/20260917-tx-paired-with-pullup-digital.csv`, SHA-256
`16efaba3c6e633db20ce5e389c3ee21c7d90ba59851c1c25ed33a9dcf544597f`.
Its 232 data rows span 0–138.529996800 seconds; the older exported column names
remain. D1 and D2 each contain 198 transitions forming only three exact
`DMF/1 PONG\n` packets at approximately 26.049807, 102.942523, and
119.171079 seconds. Every decoded stop bit is valid. Corresponding D1/D2 edge
times differ by no more than 40 ns, and neither channel contains any transition
outside the three replies.

Session `20260917T195304Z-a810227d` ran 19:53:04–19:58:04 UTC and completed
with `duration_elapsed`. It contains exactly 33 raw bytes: the same three
PONGs. All three forced-send attempt/result pairs report success and five
accepted command bytes. No unexpected receive byte is present. It has one
segment, zero reported receive-buffer loss, and no overflow, interruption,
resumption, or truncation.

This controlled one-variable comparison supports disconnected-input bias as the
cause of the previous receive-pin disturbances: adding the pull-up eliminated
both the long/short low intervals and the resulting extra host bytes. It does
not by itself establish repeatability, select a production resistor value, or
close the hardware change. Multiple continuous cycles and a schematic/BOM
decision remain required.

Local session SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `359b56b25092093c65ecfa9d55b73388b114841779b1c542a139da117428bf44` |
| `uart_raw.log` | `4b455288d0c7a2620b46fe31aa1d3a4d644c432be6884532b0d524bd30d2c729` |
| `uart_events.jsonl` | `b53107b6b0a89abe2416eafcf4c4b0c1635e0fd61af4cbf5060bb22cd35718dd` |
| `hardware_events.jsonl` | `233e9ce42e6400740936ed124eaf66c1ed345bef901a0bf1a58c81fc0b68f7fe` |

### Five-cycle helper-side TX pull-up repeatability

The same paired-probe setup and temporary helper-side 10 kOhm pull-up were
retained for five consecutive Pico 1 GP0 to J1 pin 4 disconnect/reconnect
cycles. One continuous Saleae recording covered a baseline command and one
immediate recovery command after each reported cycle. The supplied
`digital_tx_pullup_5cycles.csv` is preserved unchanged as
`evidence/20260917-tx-pullup-five-cycles-digital.csv`, SHA-256
`cdcbdc2109b6e3eec034888d12d605b1b49407aedea90bfa73b43ada3b9da362`.
Its 456 data rows span 0–300.812861440 seconds; the old exported channel labels
remain, while the physical D1/D2 mapping is unchanged from the preceding run.

D1 and D2 each have 396 transitions grouped into exactly six packets:

| Exchange | D1/D2 packet start (CSV s) | Decoded result |
|---|---:|---|
| Baseline | 37.808920800 | `DMF/1 PONG\n` |
| Cycle 1 recovery | 91.735273120 | `DMF/1 PONG\n` |
| Cycle 2 recovery | 154.259665880 | `DMF/1 PONG\n` |
| Cycle 3 recovery | 202.196747720 | `DMF/1 PONG\n` |
| Cycle 4 recovery | 239.492758360 | `DMF/1 PONG\n` |
| Cycle 5 recovery | 277.114590480 | `DMF/1 PONG\n` |

All 66 decoded frames per channel have valid stop bits. There are no other
transitions, and corresponding D1/D2 edge timestamps differ by at most 40 ns.

Session `20260917T200511Z-b56c8116` ran 20:05:11–20:10:11 UTC and completed
with `duration_elapsed`. All six forced-send attempt/result pairs succeeded.
Its 66 raw bytes are exactly six `DMF/1 PONG\n` replies. It has one segment,
zero reported receive-buffer loss, and no overflow, interruption, resumption,
or truncation.

Local session SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `c211122140b018ae893fc3226a7fb0adeed8ff30b701d7c6fa8d39c9ff85fd64` |
| `uart_raw.log` | `635303336c221f1dbfa1b9b9a68774d6ecc3469de39dd90161cc23d5dfb61a60` |
| `uart_events.jsonl` | `78c4b7f555535a93086ea26a9b759d039d8c2149007dbd16a5f7be845313b1a0` |
| `hardware_events.jsonl` | `2fd19f4ac39fa41642917cb6ad881bd66510009863e129b76ad11bc4f674b2ef` |

Together with the failing no-pull-up capture and the clean one-cycle pull-up
comparison, this establishes the helper-side disconnected-input bias as the
cause of the reproduced TX-wire disturbance. The external 10 kOhm idle-high
bias is effective and repeatable at 3.3 V in this fixture. The result does not
select a final production value across every supported `DUT_VIO`, amend the
schematic/BOM, or address a DUT's own RX input when the debugger-to-DUT wire is
removed. Those are separate design responsibilities.

The user subsequently accepted the next-revision correction: retain the
fixed-direction `TXU0202DCUR` and add 10 kOhm from translator-side `UART_TX`
(`U1.B2`, pin 1, after `R16`) to `DUT_VIO`. No required helper-side pull-up is
added to the debugger-to-DUT `DUT_UART_RX` output. A DUT that requires clean
behavior with its cable removed must provide local idle-high bias on its own
UART RX input. This records the design decision; the next-revision schematic
and BOM have not yet been supplied or verified.

## Deferred Analog UART Cable/Edge Validation

On 2026-09-16, the user confirmed that no analog oscilloscope is available and
explicitly deferred the UART cable/edge and series-resistor waveform test. The
available 25 MS/s Saleae can verify digital decoding and timing, but it cannot
measure the analog rise/fall shape, overshoot, undershoot, ringing, or voltage
margin required to accept the selected series-resistor values. The existing
short-jumper 460800-baud loopbacks therefore remain functional evidence only;
the section 14 cable-length, analog edge, and series-resistor validation items
remain open and deferred.

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
  check. Direct UART/event loading in this supply direction remains open.
- Both supply orders passed direct measurement of all four active-low control
  `/OE` nodes. Each node remained at approximately 1.8 V whenever VIO was
  present, including after debugger USB insertion and removal, and fell to
  approximately 0.0 V with VIO absent. The four pulled-up DUT controls remained
  released throughout every VIO-present state. This passes the settled all-
  order control-disable requirement; transient capture remains open.
- With debugger USB absent, `DUT_VIO` at 1.8 V, and Pico `3V3(OUT)` loaded to
  ground through 10 kOhm, each of the four event and two UART connector signals
  retained an individual 1.8 V/10 kOhm pull-up while `3V3(OUT)`, `VSYS`, and
  `VBUS` remained approximately 0.0 V. Together with the control sweep, this
  passes static debugger-supply-absent isolation for every external digital
  signal. Hot-plug/transient behavior and absolute leakage remain open.
- Five VIO-positive-lead insertion/removal cycles with debugger USB held on and
  five debugger-USB insertion/removal cycles with VIO held at 1.8 V behaved
  identically. Settled rails and enables remained correct, every USB insertion
  enumerated, and all four `/OE` nodes remained at 1.8 V whenever VIO was
  present. This passes repeated unloaded supply hot-plug at 1.8 V. Loaded DUT-
  cable hot-plug and transition waveform capture remain open.
- The user explicitly deferred analog UART cable/edge and series-resistor
  validation because no analog oscilloscope is available. Existing Saleae and
  loopback results remain digital functional evidence and do not close those
  section 14 items.
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
