# Manufactured KiCad Rev-A Validation Evidence

This record covers the manufactured KiCad board identified by the operator as
fully assembled, using the Pico 2 reused from the legacy EAGLE fixture. It does
not transfer acceptance from that fixture. Design authority is the
[current KiCad source](../pcb/debug-helper/rev-a/README.md); acceptance remains
governed by [Phase 1 §34](../../docs/phase1_implementation_spec.md#34-phase-1b-done--enhanced).
Current progress and next actions belong only in
[development status](../../docs/development_status.md).

## Initial inspection, power and sense observations — 2026-11-18

### Setup and evidence limits

- Operator reports a fully assembled board, fitted Pico 2, clear visual
  inspection, and identified J1 pin 1. Independent assembly/BOM verification
  and the fabrication-source revision were not supplied.
- Meter: Mastech MAS830L. Voltage readings below are operator-reported; meter
  range, input impedance, calibration and photographs were not supplied.
- DUT_VIO source/current measurement: Nordic PPK2, Source Meter mode, set to
  1.8 V. Software version, capture files, averaging window and a configured
  current limit were not recorded. No separate bench supply or oscilloscope
  was available. No DUT was connected during these checks.
- The working checkout's PCB already had an operator-owned modification;
  it was not changed by this diagnostic work or assumed to identify the
  manufactured board's exact source.

### Operator-reported observations

| Setup | Observation |
|---|---|
| All power disconnected | J1 pin 1↔16 reported shorted/common ground; DUT_VIO↔GND and 3V3↔GND reported no short. Numeric resistances and shorted-probe resistance were not supplied. |
| Pico USB only; DUT_VIO disconnected | Pico pin 36/3V3 = **3.3 V**; J1 pin 14/DUT_VIO = **0.0 V**; no smell reported. No temperature measurement supplied. |
| PPK2 disconnected from board | Output verified at **1.8 V**. No-load current initially transcribed as 0.2 pA, later clarified as **200 pA**; retained as a displayed no-load baseline, not board leakage evidence. |
| PPK2 supplies DUT_VIO; Pico USB disconnected | J1 pin 14 = **1.8 V**; Pico pin 36/3V3 = **0.0 V**; PPK2 average current = **0.4 µA**; Pico pin 34/GP28 = **0.0 V**. |
| PPK2 supplies 1.8 V DUT_VIO; Pico USB connected | Pico pin 36/3V3 = **3.3 V**; Pico pin 34/GP28 = **0.42 V**; PPK2 average current = **29 µA**. DUT_VIO was not independently remeasured in this state. |

The operator explicitly corrected an initial transcription of the last setup's
3V3 reading from 0.0 V to **3.3 V**. That corrected value is used above; no
USB-powered rail failure is established. The 0.42 V sense reading remains an
observation, not an accepted divider result or a diagnosed meter fault.
Unloaded zero-voltage observations do not prove loaded powered-off isolation.

### USB startup observation

Host enumeration found `/dev/cu.usbmodem11401`, manufacturer `DUTchMate`, product
`Debug Helper`, VID/PID `2E8A:000A`, serial **FA63A4D787572B33**, matching the
recorded legacy fixture module. No serial owner or TCP 2040 listener was found
before the check. An initial sandbox serial-open attempt was denied; the
authorized device-access retry succeeded. The startup frame was:

```json
{"type":"hello","v":1,"firmware":"development","device":"dutchmate-rp2350","capabilities":["uart_receive","gpio_control","uart_send","device_timestamp","overflow_telemetry"]}
```

The check asserted DTR to receive the startup frame, sent no protocol, DUT UART
or control commands, then deasserted DTR and closed the port. A subsequent
ownership check found no serial owner. This identifies USB/protocol behavior,
not the exact flashed image: the installed UF2 hash was not established.

### GP28 diagnostic rationale

The application does not configure GP28 in normal initialization. Installed
RP2350 pad definitions show reset pull-down enabled and digital input disabled;
running register values have not been read. Therefore an enabled digital input
buffer is not an established cause. Pin pulls/digital configuration, meter
loading, component values and assembly remain hypotheses for the low reading.

The opt-in diagnostic uses Zephyr 4.4.2's `GPIO_DISCONNECTED` behavior to disable
GP28 pulls, digital input/output and set digital pad isolation. Its matched
baseline preserves normal GP28 behavior. Neither image implements ADC sensing.
Build evidence is recorded in
[development history](../../docs/development_history.md); no new-image flash
or A/B physical measurement is claimed by this preparation record.

## Matched baseline flash and USB verification — 2026-11-18

After the operator reported the BOOTSEL drive present, the host verified
`/Volumes/RP2350/INFO_UF2.TXT`: UF2 Bootloader v1.0, model Raspberry Pi RP2350,
board ID RP2350. Only one UF2 bootloader volume was found. The operator had been
instructed to keep the PPK2 and DUT disconnected for flashing.

The source UF2 was 104,448 bytes with SHA-256
`4f3c600a896a4d4c3f0fc6e36ada6abe52a6402abdd4b77c8dda9527d7835fd4`.
It was copied to `/Volumes/RP2350/DUTchMate-sensebase-1.uf2` using authorized
external-volume access. The boot volume disappeared and the expected helper
re-enumerated at `/dev/cu.usbmodem11401`, serial `FA63A4D787572B33`.

With no serial owner or TCP 2040 listener found, a bounded exclusive serial read
verified firmware **`sensebase-1`**, device `dutchmate-rp2350`, protocol v1 and
the same five capabilities recorded above. DTR was deasserted and the port
closed after the startup frame; no protocol, UART TX or control commands were
sent. The [machine-readable USB/flash record](evidence/20261118-kicad-rev-a-sensebase-usb.json)
retains the image hash, port, serial, parsed startup frame and close state.

This establishes the copied baseline image and its live USB identity. It does
not supply new GP28/current readings, read back flash contents, or establish
electrical acceptance. The earlier `development` image remains unidentified
by exact hash; its operator readings are not relabelled as `sensebase-1` data.

## Matched baseline measurements at 1.8 V — 2026-11-18

After the baseline flash/USB verification above, the operator reported these
measurements with Pico USB connected, no DUT attached, PPK2 in Source Meter
mode at 1.8 V, and the Mastech MAS830L referenced to J1 pin 1:

| Measurement | Operator-reported result |
|---|---|
| J1 pin 14 / DUT_VIO | **1.8 V** |
| Pico pin 36 / 3V3 | **3.3 V** |
| Pico pin 34 / GP28 | **0.42 V** |
| PPK2 average current while probing GP28 | **29.46 µA** |
| PPK2 average current with meter probes removed | **29.46 µA** |

The known `sensebase-1` image reproduces the low sense voltage reported on the
unidentified `development` image. No change in average DUT_VIO current was
reported at the displayed precision when the meter probes were removed.
Averaging windows, uncertainty and meter input impedance were not supplied;
this comparison does not independently rule out meter effects or identify
the load. No diagnostic-image comparison or electrical acceptance is claimed.

## GP28 diagnostic flash and USB verification — 2026-11-18

Following instructions to disable/disconnect PPK2 and keep the DUT disconnected,
the operator reported the BOOTSEL drive present. The host verified the sole
`/Volumes/RP2350` volume, bootloader v1.0, model Raspberry Pi RP2350 and board ID
RP2350. The prepared diagnostic UF2 was 104,448 bytes with SHA-256
`5e2597ecad980e4020bbccca8d2b1d581641977e41f5159244b9b3330510cf64`.
Resolved build configuration enabled `DUTCHMATE_SENSE_PIN_PROBE`, reported
`senseprobe-1`, and did not enable ADC.

The image was copied to `/Volumes/RP2350/DUTchMate-senseprobe-1.uf2` with
authorized device-volume access. The boot volume disappeared and the expected
serial `FA63A4D787572B33` returned at `/dev/cu.usbmodem11401`.
With no serial owner or TCP 2040 listener found, a bounded exclusive startup
read verified firmware **`senseprobe-1`**, protocol v1, device
`dutchmate-rp2350` and the same five capabilities as the baseline. No protocol,
UART TX or control commands were sent. DTR was deasserted and the port closed.
The [machine-readable diagnostic USB/flash record](evidence/20261118-kicad-rev-a-senseprobe-usb.json)
retains the image identity and observed startup frame.

The source/build was unchanged from the validated preparation. This flash and
USB check supplies no diagnostic GP28/current measurements or flash readback;
it does not yet establish an A/B electrical result or a cause for the low voltage.

## GP28 diagnostic measurements and A/B comparison — 2026-11-18

With the verified `senseprobe-1` image, the operator reported the same setup
and measurements as the known baseline: Pico USB connected, no DUT attached,
PPK2 Source Meter at 1.8 V, Mastech MAS830L in DC voltage mode referenced to
J1 pin 1. These are operator-reported values, not automated instrument captures.

| Measurement | `sensebase-1` | `senseprobe-1` |
|---|---|---|
| DUT_VIO / J1 pin 14 | **1.8 V** | **1.8 V** |
| Helper 3V3 / Pico pin 36 | **3.3 V** | **3.3 V** |
| GP28 / Pico pin 34 | **0.42 V** | **0.42 V** |
| PPK2 average current while probing GP28 | **29.46 µA** | **29.46 µA** |
| PPK2 average current with meter probes removed | **29.46 µA** | **29.46 µA** |

No change was reported at the supplied precision after the diagnostic disabled
GP28 pulls, digital input/output and set digital pad isolation. This A/B result
does not support the tested pin configuration as the explanation for the low
voltage; it does not establish the alternative cause. Running pad registers,
meter input impedance and independent lab-meter readings remain unmeasured.
No permanent firmware correction or board acceptance follows from this result.

Source inspection confirms R10=47 kΩ, pad 1=`Net-(U3-D)` and
pad 2=`DUT_VIO_SENSE`; R11=47 kΩ, pad 1=`DUT_VIO_SENSE` and pad 2=`GNDA`.
The switch-output voltage, both resistor-terminal voltages, actual populated
resistor values and return continuity were not measured in this A/B result.

## Divider-terminal readings with Pico 2 removed — 2026-11-18

The operator supplied the following terminal voltages, then clarified that
**Pico 2 had been removed from the helper and the helper was supplied external
3.3 V**. These readings are not an in-place `senseprobe-1` measurement:

| Point labelled by operator | Reported voltage |
|---|---|
| R10 end A | **1.8 V** |
| R10 end B | **0.9 V** |
| R11 end A | **0.9 V** |
| R11 end B | **0.0 V** |

The external 3.3 V source, injection/return points, DUT_VIO source/wiring and
GNDA/common-ground connections for this altered setup were not supplied.
In particular, GNDA normally connects to common ground through the fitted
Pico module; removing it changes that return topology unless the bench wiring
provides a replacement path. No replacement GNDA connection is assumed here.

These terminal readings match the intended static 1:2 divider in the reported
Pico-removed setup. They do not establish 0.9 V at fitted Pico GP28 or isolate
firmware as a cause. The contrast with the earlier 0.42 V readings motivates
checking module connections/loading and controlling the changed supply/ground
setup. No continuity, populated-resistor-value or additional powered test was
performed by the host after this clarification.

## Pico-removed wiring clarification and resistance observation — 2026-11-18

The operator clarified that the external helper supply was taken from the
removed Pico 2's physical pin 36 to helper A1 socket pin 36. Ground was
connected to J1 GND, and helper A1 socket pin 33 was additionally jumpered to
J1 GND. PPK2 continued to supply DUT_VIO at 1.8 V. The explicit pin-33 ground
jumper provides the reported GNDA return for the Pico-removed divider setup;
it was not present in the earlier description of that setup.

The operator reported **46.9 kΩ** between the divider midpoint and the point
identified as helper Pico socket physical pin 34. The source assigns that
socket pad and the R10/R11 midpoint to the same `DUT_VIO_SENSE` net, so direct
continuity close to probe resistance is expected. A reading close to one
nominal 47 kΩ resistor does not establish that direct connection. Test-point
identity, power removal during the resistance reading and actual board/socket
continuity require verification; no trace defect, wrong component, firmware
cause or Pico damage is established from this observation.

## Qualitative R11/socket continuity follow-up — 2026-11-18

The operator subsequently described R11 end A→socket pin 34 and R11 end B→socket
pin 34 as both "shorted", while socket pin 34→J1 GND was "not shorted".
Shorted-probe resistance, numerical readings, meter mode/range and stabilization
time were not supplied. The pin-33→J1-ground jumper had been requested to remain
in place; its continuity was not independently measured in this follow-up.

These qualitative statements do not establish stable zero-ohm connections or
a shorted resistor. Both R11 ends cannot be directly connected to the same
socket pad without also being connected to each other. Under the intended
mapping, one R11 end directly joins socket pin 34 and the other returns to
GNDA through the resistor. Numeric resistance and physical-point verification
are required before concluding that either a PCB or measurement fault exists.

## Fluke 115 resistance measurements — 2026-11-19

The operator changed to a **Fluke 115**, resistance mode with automatic range,
and reported the following numeric measurements after the power-off/Pico-removed
instructions. Current jumper presence and shorted-probe resistance were not
explicitly supplied for this run:

| Measurement | Operator-reported result |
|---|---|
| Across R11, end A↔end B | **46.94 kΩ** |
| R11 end A↔helper socket pin 34 | **46.94 kΩ** |
| R11 end B↔helper socket pin 34 | **1 Ω** |
| Helper socket pin 33↔J1 GND | **Open** |

These readings are consistent with the intended nominal 47 kΩ R11 and a
low-resistance connection from the end currently labelled **B** to socket
pin 34. They do not support the earlier qualitative claim that both ends were
shorted to pin 34. Under the source mapping, current end B is the sense end and
end A is the GNDA end. The earlier powered run used end labels in the opposite
voltage order; its measurements are retained as reported, without assuming
that A/B labels identify fixed physical pads across runs.

The pin-33→J1-ground open reading is expected without a ground jumper while
Pico is removed, because the carrier's GNDA/common-ground join normally uses
the module. If the previously requested jumper remained fitted, the reading
instead requires checking its contacts/pin identity. The run does not establish
which condition applied, or demonstrate that fitted-Pico ground is open.
R11 end A→socket pin 33 was not measured in this numeric run. No new powered
readings, flash, firmware correction or hardware acceptance is established.

## Additional resistance and jumper-presence report — 2026-11-19

The operator then reported **93.9 kΩ** between the point currently labelled
"R11 end A" and helper socket pin 33, and confirmed the pin-33→J1-ground
jumper was fitted. Under the source mapping, the actual R11 GNDA terminal
should directly join socket pin 33. This measured resistance does not verify
that direct connection. The earlier pin-33→J1-ground Open reading also remains
unresolved despite the reported jumper presence.

93.9 kΩ is close to the sum of the two nominal 47 kΩ divider resistors.
One hypothesis consistent with the numeric pattern is that the component
labelled R11 during this run is actually R10: its switch-side terminal would
reach socket pin 34 through one resistor and socket pin 33 through both.
This is a test-point identification hypothesis, not a confirmed finding.
Physical photographs/component identification and jumper endpoints have not
been verified; no resistor replacement, trace repair or firmware change is
justified by this reading alone. The operator's A/B labels remain local to
each run rather than verified KiCad pad identities.

## Corrected R11 test points and ground-jumper continuity — 2026-11-19

Following the component-location discussion, the operator supplied an updated
R11 end A→socket pin 33 reading of **46.94 kΩ**, then confirmed the following
with Pico removed and all power disconnected, using the Fluke 115:

| Measurement with the corrected R11 labels | Reported resistance |
|---|---|
| R11 end A↔socket pin 34 | **0 Ω** |
| R11 end B↔socket pin 33 | **0 Ω** |
| Socket pin 33↔J1 GND, jumper connected | **0 Ω** |

These observations identify current R11 end A as the sense midpoint and end B
as GNDA, and establish the reported direct socket connections and jumper
continuity at the meter's displayed precision. The 46.94 kΩ A→pin-33 reading
is consistent with the intended nominal 47 kΩ R11 between those nodes.
Earlier conflicting A/B descriptions and measurements are retained above;
they are not independently verified physical-pad identities.

This closes the specific continuity/test-point ambiguity for the reported
Pico-removed setup. It does not establish fitted-Pico ground continuity or
repeat the GP28 voltage using the Fluke with Pico fitted. No soldering,
component replacement or additional firmware change was performed.

## Fitted-Pico Fluke voltage repeat — 2026-11-19

After instructions to remove the external supply/jumper wires, refit Pico with
all power off, verify its ground path, and restore USB plus 1.8 V PPK2 DUT_VIO,
the operator supplied these Fluke 115 observations:

| Measurement | Operator-reported result |
|---|---|
| Fitted Pico pin 33↔J1 GND, power off | **0 Ω** |
| DUT_VIO | **1.8 V** |
| Pico 3V3 | **3.3 V** |
| Corrected R11 end A / sense midpoint | **0.424 V** |
| Pico physical pin 34 / GP28 | **0.424 V** |
| PPK2 average current, meter probes removed | **28.47 µA** |

The Fluke confirms the same low voltage at both directly connected sense
points, with reported fitted-module ground continuity. The previously used
meter or a simple mismatch between those two measurement points does not
explain this repeat. The switch-output/R10-input voltage was not measured with
Pico fitted during this run; reduced upstream feed and sense-node loading
remain distinct hypotheses. No cause or permanent firmware fix is established.

At the host check after this report, serial enumeration returned no USB serial
devices, so the last verified `senseprobe-1` identity was not read again for
this run. The Pico's USB power/computer connection was requested for clarification.
Source inspection confirms the prepared image enables the probe and the pinned
driver disables pulls/input/output and sets pad isolation, but actual running
pad registers have not been read. No new source/image change or flash occurred.

## USB identity recheck after moving from the other Mac — 2026-11-19

The operator clarified that the fitted Fluke measurements used another Mac
for Pico USB power, then connected the fitted Pico to this host following
instructions to keep PPK2 output disabled and the DUT disconnected.
Enumeration found the same serial **FA63A4D787572B33**, VID/PID `2E8A:000A`,
product `Debug Helper`, now at `/dev/cu.usbmodem101`.

No serial owner or TCP 2040 listener was found. A bounded exclusive startup
read verified firmware **`senseprobe-1`**, protocol v1, expected device and five
capabilities. No protocol, UART TX or control commands were sent; DTR was
deasserted and the port closed. The prepared probe UF2 hash still matched
`5e2597ecad980e4020bbccca8d2b1d581641977e41f5159244b9b3330510cf64`.
The [machine-readable recheck](evidence/20261119-kicad-rev-a-usb-recheck.json)
records the observed identity and explicitly excludes flash readback and
pad-register reads. No firmware/source/image change, flash or new electrical
measurement occurred in this recheck.

## Fitted-board rail and ground-end check; R10 access limitation — 2026-11-19

After the fresh `senseprobe-1` USB identity check on this Mac, the operator
reported DUT_VIO=**1.8 V**, Pico 3V3=**3.3 V**, and the confirmed R11 GNDA end
(connected to socket pin 33)=**0.0 V**, referenced to J1 GND. Both R10 ends were
inaccessible because the fitted Pico covers the component. No R10 voltage is
inferred from these rail measurements; the upstream-feed-versus-midpoint-load
question remains open.

An off-board Pico wiring comparison was selected as the accessible diagnostic
method: module pin 36 supplies carrier socket pin 36, module pin 38 grounds to
J1 pin 1, and carrier socket pin 33 is jumpered to J1 pin 1. PPK2 retains the
separate 1.8 V DUT_VIO supply. Keeping module GP28 disconnected provides a
baseline with R10 exposed; a subsequent comparison can add only the GP28 wire
with all power removed between wiring changes. No off-board rewiring or
measurement is claimed by this setup preparation.

## Off-board Pico supply baseline, GP28 disconnected — 2026-11-19

Following the explicit off-board wiring instructions above (Pico pin 36→carrier
socket 36, Pico pin 38→J1 pin 1, carrier socket 33→J1 pin 1, and PPK2 supplying
J1 pin 14 with common J1 ground), the operator reported the following with
Pico GP28 left disconnected from the carrier and all other Pico signal pins
disconnected. Pico USB used this Mac; PPK2 was set to Source Meter 1.8 V.

| Measurement | Operator-reported result |
|---|---|
| Carrier A1 socket pin 36 / helper 3V3 | **3.3 V** |
| R10 end A | **1.75 V** |
| R10 end B / divider midpoint | **0.868 V** |
| PPK2 average current, meter probes removed | **20 µA** |

The midpoint is approximately half the measured R10 feed in this setup.
The actual J1 DUT_VIO voltage was not independently supplied in this report;
the 1.8 V source setting is not substituted for the observed 1.75 V feed.
This baseline keeps the Pico as the helper's 3V3 source while leaving GP28
electrically separate. No GP28-connected off-board comparison, runtime pad
read, firmware change or hardware acceptance is established by these values.

## Off-board comparison with only GP28 added — 2026-11-19

After instructions to remove both power sources, add only Pico physical pin
34→carrier socket pin 34, retain the previous off-board supply/ground wiring,
and restore USB plus the same PPK2 setting, the operator reported:

| Measurement | GP28 disconnected baseline | GP28 connected |
|---|---|---|
| Actual J1 pin 14 / DUT_VIO | Not supplied | **1.725 V** |
| R10 end A / switch-side feed | **1.75 V** | **1.725 V** |
| R10 end B / sense midpoint | **0.868 V** | **0.426 V** |
| Pico physical pin 34 | Disconnected | **0.426 V** |
| PPK2 average current, meter probes removed | **20 µA** | **28.56 µA** |

Connecting the GP28 branch lowers the midpoint while the measured switch-side
feed remains at measured DUT_VIO. The small feed-voltage difference between
runs does not explain the midpoint reduction. This isolates a load associated
with the GP28 connection in the reported controlled setup; it does not identify
the internal mechanism or establish a damaged Pico. The first `senseprobe-1`
diagnostic did not distinguish physical latched pulls from register settings.

## Pad-isolation interpretation and readback preparation — 2026-11-19

The [RP2350 datasheet §9.7](https://pip-assets.raspberrypi.com/categories/1214-rp2350/documents/RP-008373-DS-2-rp2350-datasheet.pdf?disposition=inline)
states that ISO holds existing pad output and pull-enable controls until
isolation is cleared. On reset, the pull-down control is enabled and ISO is set.
The pinned Zephyr `GPIO_DISCONNECTED` path writes cleared pull controls and
sets ISO without first clearing it. Therefore the earlier claim that this API
alone guarantees removal of the physical pull was incomplete. Retained pull
state is a concrete hypothesis for the no-effect first diagnostic, not yet a
confirmed mechanism on this Pico. Historical descriptions above remain as
dated investigation records and are qualified by this finding.

The default-off `DUTCHMATE_SENSE_PAD_REPORT` diagnostic keeps the first probe's
initialization unchanged and reads GP28's pad-control word at each USB epoch,
before UART starts. It reports that word as `sensepad-1-pXXXXXXXX` in the
existing firmware identifier. No ADC, register-write experiment, new wire
field or capability was added. Stack and pad-report diagnostics are exclusive.

Zephyr 4.4.2 / SDK 1.0.1 readback image:
`build/dutchmate-rp2350-sense-state-probe/zephyr/zephyr.uf2`, **109,056 bytes**,
SHA-256 **`ee8cfaa41c2fe85a317fad650eded50b4f689af5db4f457c7cb4b803ea460132`**.
The [build manifest](evidence/20261119-kicad-rev-a-pad-readback-build.json)
retains source and artifact hashes, including preserved baseline/probe images.
Target disassembly confirms the read at `0x40038074`; no live value was obtained
and this new image was not flashed during preparation.

Host tests validate fresh raw-pad reads, pad selection, read-only behavior and
bounded identifier output using controlled register values. The first link
attempt found the missing API; the minimal scaffold then compiled and failed
the expected report behavior before implementation. Focused tests **5 passed
in 1.71 s**; fresh full pytest **1,877 passed in 54.48 s**, Ruff and mypy/103
passed. Readback, baseline and existing stack diagnostic target builds pass;
the rebuilt baseline UF2 is byte-identical to the preserved baseline. These
software/build checks establish no electrical fix or board acceptance.

## Pad-readback flash and live GP28 register — 2026-11-19

With the operator reporting the sole RP2350 BOOTSEL volume present after
instructions to keep PPK2 off and Pico isolated from helper jumpers, the host
verified the prepared readback UF2 hash
`ee8cfaa41c2fe85a317fad650eded50b4f689af5db4f457c7cb4b803ea460132`
(109,056 bytes), UF2 bootloader v1.0 and board/model RP2350. Authorized copy to
`/Volumes/RP2350/DUTchMate-sensepad-1.uf2` returned successfully. The volume
disappeared and helper serial `FA63A4D787572B33` returned at `/dev/cu.usbmodem101`.

After checking no serial owner/TCP 2040 listener, a bounded exclusive USB read
received firmware **`sensepad-1-p00000192`**, expected device/protocol and all
five existing capabilities. GP28 pad control at `0x40038074` was therefore
reported as **`0x00000192`**:

| Control | Observed register bit |
|---|---|
| ISO | **Set** |
| Output disable | **Set** |
| Digital input enable | **Clear** |
| Pull-up enable | **Clear** |
| Pull-down enable | **Clear** |

No protocol/UART TX/control commands were sent; DTR was deasserted and the
port closed, with no owner afterward. The
[USB/register evidence](evidence/20261119-kicad-rev-a-sensepad-usb.json) retains
the exact startup frame and decoded bits, and explicitly excludes flash
readback and physical latched-pull readout. The register confirms ISO remains
set despite cleared pull-control bits; it supports but does not electrically
prove the retained-pull hypothesis. No new voltage measurement was obtained.

## Controlled isolation-release image preparation — 2026-11-19

Added default-off `DUTCHMATE_SENSE_RELEASE_ISOLATION`, dependent on pad readback.
After the same successful GPIO-disconnect configuration, the diagnostic clears
only `PADS_BANK0_GPIO28_ISO_BITS` via the hardware atomic-clear alias. A failed
GPIO configuration returns before release. Input/output/pull controls and all
other GPIO behavior remain as in the readback image; ADC remains disabled.
`sense_iso_probe.conf` reports `senseiso-1-pXXXXXXXX`. With other pad controls
unchanged, `0x92` is the expected register word, not an observed result here.

Tests first reported **1 failed / 6 passed** because the requested release left
pad 28 at `0x192`; after implementation **7 passed in 1.60 s**. Controlled
register fixtures verify only bit `0x100` clears, adjacent pad state is retained,
and failed GPIO configuration does not release ISO. Fresh full pytest:
**1,879 passed in 63.55 s**; Ruff and mypy/103 passed.

Zephyr 4.4.2 / SDK 1.0.1 build:
`build/dutchmate-rp2350-sense-iso-probe/zephyr/zephyr.uf2`, **109,056 bytes**,
SHA-256 **`be6ce0f72e0eb0701fb5a6eb9496514988eaac25eafbd084403a94912573b2f3`**,
FLASH **54,460 B**, RAM **81,040 B**. Disassembly confirms the `0x100` write
to the pad-28 atomic-clear alias at `0x4003b074` occurs only after configuration
success. Fresh baseline and readback-only target builds are byte-identical to
their preserved images. Resolved readback/release configs differ only in the
release option and firmware identifier. The
[build manifest](evidence/20261119-kicad-rev-a-iso-release-build.json) retains
artifact/source identities and explicitly records that the release image was
not flashed and no post-release register/voltage was observed in preparation.
No permanent normal-firmware fix or hardware acceptance is established.

## Isolation-release flash and live register verification — 2026-11-19

After the operator reported the RP2350 bootloader drive present with Pico
instructed to remain isolated from the helper and PPK2 off, the host verified
UF2 bootloader v1.0, model/board RP2350, and the prepared `senseiso-1` UF2:
109,056 bytes, SHA-256
`be6ce0f72e0eb0701fb5a6eb9496514988eaac25eafbd084403a94912573b2f3`.
Authorized copy to `/Volumes/RP2350/DUTchMate-senseiso-1.uf2` succeeded; the
volume disappeared and serial `FA63A4D787572B33` returned at `/dev/cu.usbmodem101`.

No serial owner/TCP 2040 listener was found before a bounded exclusive read.
The live startup firmware identifier was **`senseiso-1-p00000092`**, with the
expected device/protocol and five capabilities. Relative to the readback-only
image's `0x192`, the reported GP28 pad word is **`0x92`**: ISO is clear, OD is
set, and IE/PUE/PDE are clear. Only ISO changed in the observed control word.
No protocol, UART TX or control commands were sent; DTR was deasserted and
the port closed. The
[live ISO-release evidence](evidence/20261119-kicad-rev-a-senseiso-usb.json)
preserves the exact frame, decoded controls, source image identity and scope.

This verifies the intended register transition on the actual Pico. No helper
voltage/current was measured after release, no physical latched-pull state or
flash contents were read back, and no electrical fix or acceptance is claimed.
The normal firmware remains unchanged; the released state is diagnostic-only.

## Off-board electrical result after ISO release — 2026-11-19

After restoring the same off-board 3V3/common-ground/GNDA/GP28-connected wiring
with both sources removed during wiring, the operator supplied these Fluke 115
measurements using verified `senseiso-1` and PPK2 Source Meter at the same
nominal 1.8 V setting:

| Measurement | Before ISO release, GP28 connected | After ISO release, GP28 connected |
|---|---|---|
| Actual DUT_VIO | **1.725 V** | **1.738 V** |
| Helper 3V3 | Not repeated in that report | **3.277 V** |
| R10 switch-side feed | **1.725 V** | **1.738 V** |
| R10 midpoint | **0.426 V** | **0.867 V** |
| Pico pin 34 / GP28 | **0.426 V** | **0.867 V** |
| PPK2 average current, meter probes removed | **28.56 µA** | **19.36 µA** |

After release, midpoint/feed is approximately 0.499, consistent with the
intended 1:2 divider at this operating point. Current returns close to the
20 µA GP28-disconnected baseline. With only the ISO-release option and firmware
identifier differing between the controlled images, this demonstrates that
releasing ISO after setting disabled pad controls resolves the observed
off-board loading. The supported mechanism is retention of the earlier pull
control by the RP2350 isolation latch; its physical latch state was not read
directly. No component rework was performed.

A subsequent host USB check, with no competing owner/service listener found,
again received **`senseiso-1-p00000092`** from serial `FA63A4D787572B33` at
`/dev/cu.usbmodem101`, then deasserted DTR and closed the port without protocol,
UART TX or control commands. The
[post-voltage USB evidence](evidence/20261119-kicad-rev-a-senseiso-post-voltage-usb.json)
is a host identity/register observation, separate from the operator measurements.

This closes the specific off-board loading experiment for this module/board
and nominal 1.8 V setup. It does not establish a fitted-module repeat, a change
to normal firmware, ADC sampling/accuracy, the full supported-voltage range,
powered-off isolation or complete manufactured-board acceptance.

## Fitted-Pico ISO-release electrical repeat — 2026-11-19

After instructions to remove temporary jumpers and refit the `senseiso-1` Pico
with all power off, then restore USB and PPK2 Source Meter at nominal 1.8 V,
the operator reported:

| Measurement | Operator-reported result |
|---|---|
| Actual DUT_VIO | **1.736 V** |
| Helper 3V3 | **3.277 V** |
| Fitted Pico pin 34 / GP28 | **0.866 V** |
| PPK2 average current, meter probes removed | **19.36 µA** |

The fitted pin-33→J1-ground resistance field was left blank in this report;
no fresh resistance reading is inferred. Earlier fitted-ground continuity
observations remain separate. The powered midpoint/feed ratio is about 0.499,
and current matches the off-board release result at reported precision.
The loaded-divider recovery is reproduced with Pico fitted at this operating
point using the diagnostic image. This is not yet a normal-firmware flash or
full voltage-range/isolation/UART acceptance.

## Promotion into normal GP28 startup — 2026-11-19

Normal initialization now always programs GP28 digital input/output and pulls
disabled, returns on configuration error, then clears ISO. The sequence is the
one verified in the controlled diagnostic; ADC channel setup/sampling remains
absent. Optional pad readback remains default-off and reports `sensepad-2`.
The temporary initial-probe/release switches and three obsolete baseline/probe/
release configs were removed after mapping their source/test/README consumers.

The firmware-only [diagnostic source patch](evidence/20261119-gp28-diagnostic-sources.patch)
and [archive manifest](evidence/20261119-gp28-diagnostic-source-archive.json)
preserve the prior experiments against base `9914d6298479b116c4b797e6cf4cfdb1e4788ec0`.
The archive patch SHA-256 is
`d7542d6481429665bb1a3e62de6759ceeed03d118880a5b3f1da650ef6060aae`.
It was checked against the pre-cleanup files and applied to a temporary base
reconstruction; every archived source/config hash matched. Earlier UF2 files,
numeric records and wire evidence were retained.

Tests requiring safe initialization without experimental flags initially gave
**3 failed / 2 passed**, then **5 passed in 1.30 s** after promotion. The two
obsolete experimental-mode cases were retired while normal/readback startup,
configuration-error handling and bounded fresh register reporting remain
covered. Fresh full pytest: **1,877 passed in 62.07 s**; Ruff and mypy/103 passed.
Stale removed-option/config searches in current firmware/tests returned no
matches. Normal, optional-readback and stack-diagnostic target builds passed
without warning/error findings in their logs.

The standard firmware was built without extra diagnostic configuration, with
only an explicit development identity override `gp28safe-1`. Image:
`build/dutchmate-rp2350-gp28-safe/zephyr/zephyr.uf2`, **104,448 bytes**, SHA-256
**`876365369ab5af87977322cb2019e1465db87ad62e752af8f45eb6329198095c`**,
FLASH **52,124 B**, RAM **81,040 B**. Readback and stack reporting are disabled,
and ADC is disabled. Target disassembly confirms the normal initializer's
GPIO-28 configuration followed by the guarded atomic ISO clear.

The [normal-build manifest](evidence/20261119-kicad-rev-a-normal-gp28-build.json)
retains source/artifact hashes, optional-mode build identities and the exact
version override. No normal image was flashed during preparation, no normal-
firmware electrical result is claimed yet, and no commit/push occurred.

## Normal firmware flash and USB verification — 2026-11-19

With Pico left fitted and the operator reporting BOOTSEL ready after
instructions to disconnect PPK2 and DUT, the host verified the sole RP2350
volume, bootloader v1.0 and standard UF2 hash
`876365369ab5af87977322cb2019e1465db87ad62e752af8f45eb6329198095c`
(104,448 bytes). Build configuration confirmed the `gp28safe-1` development
identity, with pad reporting, stack reporting and ADC disabled and obsolete
mode switches absent.

Authorized copy to `/Volumes/RP2350/DUTchMate-gp28safe-1.uf2` succeeded. The
volume disappeared and the same helper serial `FA63A4D787572B33` returned at
`/dev/cu.usbmodem101`. With no serial owner/TCP 2040 listener found, a bounded
exclusive startup read verified **`gp28safe-1`**, protocol v1, expected device
and exactly the existing five capabilities. No protocol, UART TX or control
commands were sent; DTR was deasserted and the port closed.

The [normal firmware USB evidence](evidence/20261119-kicad-rev-a-gp28safe-usb.json)
retains image/hash/identity and explicitly excludes flash readback, live pad
reporting and a normal-firmware voltage result. The fitted normal image is
now USB-verified; its electrical repeat was not performed by this flash check.

## Normal firmware fitted-board electrical verification — 2026-11-19

With fitted Pico running the verified normal `gp28safe-1` image, no DUT attached,
USB powered, and PPK2 Source Meter set to nominal 1.8 V, the operator reported
these Fluke 115 measurements referenced to J1 pin 1:

| Measurement | Normal-firmware result |
|---|---|
| Actual DUT_VIO | **1.736 V** |
| Helper 3V3 | **3.277 V** |
| Pico physical pin 34 / GP28 | **0.867 V** |
| PPK2 average current, meter probes removed | **19.34 µA** |

Half the measured DUT_VIO is 0.868 V; the observed GP28 value is consistent
with the intended divider ratio at this operating point. Current is close to
the prior fitted diagnostic's 19.36 µA. Together with the hash-identified normal
flash/USB evidence and source/build checks, this verifies that the permanent
normal startup sequence resolves the observed GP28 loading on this fitted
board/module/setup. The initial 0.424/0.426 V loading does not recur in this run.

The closed item is GP28 startup/loading at the recorded actual supply voltage.
The normal build still implements no ADC sampling or voltage telemetry. The
measured **1.736 V** is below the documented **1.8 V** lower operating endpoint;
it is not relabelled as an exact 1.8 V acceptance measurement merely because
the source setting was 1.8 V. An unloaded source check is needed before using
the setting for the remaining voltage-range campaign. No PPK2 calibration,
wire-drop diagnosis, full supported-range acceptance, new source change,
commit or push is established by this electrical result.

## PPK2 source-setting and unloaded output check — 2026-11-19

With PPK2 disconnected from the helper, the operator reported Source Meter
supply setting **1800 mV** and Fluke VOUT↔PPK2 GND reading **1.756 V**.
The output is therefore already 44 mV below the requested setting without
the board. The latest loaded board voltage was 1.736 V at 19.34 µA, a further
20 mV below this unloaded observation. These readings do not assign that
additional difference solely to external wiring.

[Nordic's Power Profiler serial-device source](https://raw.githubusercontent.com/NordicSemiconductor/pc-nrfconnect-ppk/main/src/device/serialDevice.ts)
contains a default first-range measurement resistance of 1031.64 Ω and applies
device metadata calibration. At 19.34 µA that nominal resistance predicts
about 19.95 mV burden, consistent with the observed additional 20 mV. This is
an inference from manufacturer source and the supplied readings: this PPK2's
actual calibrated resistance, active range, firmware/app version and regulator
accuracy were not measured. No PPK2 fault, calibration result or wire defect
is established.

An **1865 mV** source-setting trial was selected as an estimate to obtain
approximately 1.8 V at the connected board, based on the observed offset and
load-dependent difference. It is not a calibrated correction or a measured
1865 mV result. Actual board voltage must be recorded independently for the
supported-range campaign. Firmware and the verified GP28 fix were unchanged.

## PPK2 1865 mV setting trial — 2026-11-19

With normal `gp28safe-1`, fitted Pico/USB, no DUT and PPK2 set to **1865 mV**,
the operator reported actual DUT_VIO=**1.793 V**, GP28=**0.895 V** and average
current without meter probes=**19.96 µA**. The midpoint remains close to half
the measured supply (half is 0.8965 V). The supply is 7 mV below the documented
1.8 V lower endpoint; the estimate did not establish an actual 1.8 V point.
No exact source-offset correction is inferred from these two settings.

A small further trial at **1875 mV** was proposed with the same wiring and
measurement method to put actual VIO slightly above 1.8 V. No exact 1.800 V
adjustment or new calibration requirement is introduced. No firmware/image
change, flash or new acceptance conclusion occurred in the 1865 mV trial.

## Low-voltage point at PPK2 setting 1875 mV — 2026-11-19

With normal fitted `gp28safe-1` and the same USB/PPK2/Fluke setup, the operator
reported source setting **1875 mV**, actual DUT_VIO=**1.811 V**, GP28=**0.895 V**,
and average current without meter probes=**20.20 µA**. Actual VIO is now within
the documented 1.8–5.0 V range. All values are retained as reported; half of
1.811 V is 0.9055 V, so the GP28 result is not relabelled as an exact half-ratio.
No precision/calibration acceptance limit is introduced from this observation.

This is a low-voltage rail/sense observation, not an all-channel functionality
or complete board-acceptance result. A nominal approximately 2.5 V board point
was selected for the continuing range campaign, using an initial **2575 mV**
PPK2 setting estimate and independent actual-VIO measurement. No 2.5 V result,
new firmware/image change, flash, calibration, commit or push is claimed here.

## Approximately 2.5 V rail/sense point — 2026-11-19

With normal fitted `gp28safe-1`, USB powered, no DUT and PPK2 Source Meter set
to **2575 mV**, the operator reported:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **2.499 V** |
| Helper 3V3 | **3.277 V** |
| GP28 | **1.233 V** |
| PPK2 average current, meter probes removed | **27.84 µA** |

The helper rail remains at the prior measured value. GP28 is recorded as
measured, not substituted with the ideal half-supply value (1.2495 V). This
observation does not establish calibrated divider/ADC accuracy or all-channel
operation at 2.5 V. An approximately 3.3 V point was selected using an initial
**3385 mV** source setting estimate with the same measurement method. No
source/image change, flash, new accuracy limit or complete board acceptance
is established by this rail/sense observation.

## Approximately 3.3 V rail/sense point — 2026-11-19

With normal fitted `gp28safe-1`, USB powered, no DUT and the same measurement
setup, the operator increased the initial source estimate to **3400 mV** to
obtain approximately 3.3 V at the board and reported:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **3.304 V** |
| Helper 3V3 | **3.277 V** |
| GP28 | **1.640 V** |
| PPK2 average current, meter probes removed | **36.75 µA** |

Half the measured DUT_VIO is 1.652 V; GP28 is 12 mV below that ideal ratio.
The helper rail remains at the prior reported value. These are rail/sense
observations, without calibrated divider/ADC accuracy or all-channel acceptance.

[Nordic's PPK2 power-supply documentation](https://docs.nordicsemi.com/r/bundle/ug_ppk2/page/ug/ppk/ppk_power_supply.html)
specifies a Source Meter adjustment range of 0.8–5.0 V. The upper-voltage
observation therefore uses a **5000 mV** setting with independently measured
actual board voltage, without attempting compensation above that maximum.
A setting of 5000 mV alone will not establish an actual 5.000 V endpoint.
No firmware/image change or flash occurred in this observation.

## Upper-voltage rail/sense point at PPK2 maximum — 2026-11-19

With normal fitted `gp28safe-1`, USB powered, no DUT and PPK2 Source Meter
set to **5000 mV**, the operator reported:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **4.932 V** |
| Helper 3V3 | **3.277 V** |
| GP28 | **2.452 V** |
| PPK2 average current, meter probes removed | **56.29 µA** |

Half the measured DUT_VIO is 2.466 V; GP28 is 14 mV below that ideal ratio.
The helper rail remains at the prior reported value. This supplies an upper-
voltage rail/sense observation at actual 4.932 V, not an exact 5.000 V endpoint
or calibrated divider/ADC accuracy. The collected powered observations span
actual 1.811–4.932 V without establishing all-channel functionality or full
manufactured-board acceptance. No firmware/image change or flash occurred.

The documented hardware-powered-off sense isolation can be examined with
PPK2 output first disabled, Pico USB disconnected, and then PPK2 output
re-enabled at the unchanged 5000 mV setting. Actual VIO, unpowered helper 3V3,
GP28 and average current must be recorded separately from this powered result.
No USB-disconnected result or loaded isolation acceptance is inferred here.

## USB-disconnected upper-voltage isolation observation — 2026-11-19

After the powered upper-voltage measurement, with Pico still fitted, USB
disconnected, no DUT and PPK2 supplying J1 pin 14 at the unchanged setting,
the operator reported:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO, J1 pin 14 | **4.936 V** |
| Helper 3V3, Pico pin 36 | **0.002 V** |
| GP28, Pico pin 34 | **0.001 V** |
| PPK2 average current, meter probes removed | **0.97 µA** |

Compared with the USB-powered result, GP28 falls from 2.452 V to 1 mV and
the measured current falls from 56.29 µA to 0.97 µA. Helper 3V3 is 2 mV.
These settled observations support U3's powered-off sense isolation and show
no substantial debugger-rail rise at this operating point. The current is
total current from DUT_VIO, not isolated U3 leakage or a per-pin result.
Meter resolution/calibration and the PPK2 averaging interval are not newly
established. No loaded channel, hot-plug transient or full board acceptance
is inferred; no firmware/image change or flash occurred.

The reverse static setup uses Pico USB power with PPK2 output off and its
VOUT lead physically disconnected from J1 pin 14, keeping the DUT absent.
Initial unloaded voltage readings on 3V3, DUT_VIO, GP28, J1 pins 3–6 controls
and J1 pin 8 UART output describe startup voltages only; they cannot alone
establish high impedance or loaded missing-supply isolation.

## USB-only unloaded startup voltage observation — 2026-11-19

With normal fitted `gp28safe-1`, Pico USB connected, DUT absent and PPK2
output off with its VOUT lead disconnected from J1 pin 14, the operator
reported the following DC readings relative to J1 GND:

| Measurement | Reported result |
|---|---|
| Helper 3V3, Pico pin 36 | **3.276 V** |
| DUT_VIO, J1 pin 14 | **0.0 V** |
| GP28, Pico pin 34 | **0.011 V** |
| DUT_CTRL0, J1 pin 3 | **0.004 V** |
| DUT_CTRL1, J1 pin 4 | **0.004 V** |
| DUT_CTRL2, J1 pin 5 | **0.004 V** |
| DUT_CTRL3, J1 pin 6 | **0.004 V** |
| DUT_UART_RX, J1 pin 8 | **0.010 V** |

No DUT_VIO rise is observed at reported precision, and each measured signal
is within 11 mV of ground in this unloaded setup. These static voltages do
not distinguish high impedance from an actively driven low output. No loaded
missing-supply or channel-isolation acceptance follows from this observation.
The historical loaded method uses two separate 10 kΩ resistors: a series
source resistor and a DUT_VIO-to-GND load. Availability was requested before
adapting that method to the current single-J1 board. No firmware/image change,
flash, loaded result or complete board acceptance occurred.

## Loaded missing-DUT_VIO check setup, CTRL0 — 2026-11-19

The operator confirmed two loose 10 kΩ resistors. The first loaded setup
adapts the historical method to current KiCad J1, without transferring its
acceptance results:

- Normal fitted `gp28safe-1`, helper USB powered, DUT absent, no control
  commands or live workflow.
- PPK2 output off while changing wiring; reset Source Meter from its prior
  5000 mV setting to **1800 mV** before enabling. Record actual source voltage
  rather than treating the requested setting as a calibrated 1.800 V source.
- PPK2 GND to J1 pin 1; PPK2 VOUT through one loose 10 kΩ resistor to
  **CTRL0/J1 pin 3**.
- The second loose 10 kΩ resistor connects **DUT_VIO/J1 pin 14 to J1 pin 1**.
  No direct VOUT-to-DUT_VIO connection remains.
- Fluke DC voltage readings, black probe on J1 pin 1: PPK2 VOUT before the
  series resistor, CTRL0 after it, DUT_VIO, and helper 3V3/Pico pin 36.
  Record PPK2 average current with meter probes removed; disable output
  after measurement and before moving the injection lead.

This fixture checks whether CTRL0 can remain externally pulled high while
DUT_VIO is loaded toward ground. A substantial source-to-CTRL0 voltage drop
or DUT_VIO rise requires review before proceeding to another channel. No
numeric leakage acceptance threshold or physical result is introduced by
preparing this fixture.

## CTRL0 loaded-test readings pending source clarification — 2026-11-19

For the prepared USB-powered, DUT_VIO-absent CTRL0 fixture, the operator
reported:

| Measurement | Reported result |
|---|---|
| PPK2 VOUT before series resistor | **0.0 V** |
| CTRL0, J1 pin 3, after series resistor | **1.723 V** |
| DUT_VIO, J1 pin 14 | **0.001 V** |
| Helper 3V3, Pico pin 36 | **3.277 V** |
| PPK2 average current, meter probes removed | **6.37 nA** |

The source/CTRL0 voltages do not establish the intended steady externally
pulled-high condition: the source is reported at zero while CTRL0 is high.
Whether readings were taken before/after disabling output, on different
nodes, or transcribed incorrectly has not been established. The low current
is retained with its supplied nA unit, without treating it as a calibrated
per-pin leakage measurement or confirmation of a valid fixture.

A repeat source/CTRL0/DUT_VIO voltage set during one continuously enabled
PPK2 interval, unchanged wiring and fixed J1-ground reference was requested.
No channel pass/fail, hardware fault, wiring change, firmware/image change
or flash is inferred from this unresolved measurement set.

## CTRL0 loaded-test consistent voltage repeat — 2026-11-19

In response to the request for readings during one continuously enabled PPK2
interval, with the same USB-powered helper, two-resistor fixture and no DUT,
the operator reported:

| Measurement | Reported result |
|---|---|
| PPK2 VOUT before series resistor | **1.756 V** |
| CTRL0, J1 pin 3, after series resistor | **1.748 V** |
| Loaded DUT_VIO, J1 pin 14 | **0.002 V** |

CTRL0 is 8 mV below the measured source while DUT_VIO remains at 2 mV with
its separate 10 kΩ ground load. This consistent repeat supports the static
externally pulled-high isolation check for CTRL0 at this operating point.
It resolves the missing valid source/CTRL0 voltage pair, without diagnosing
why the earlier source reading was reported as zero. No fresh current or
3V3 value was supplied; the prior 6.37 nA is not transferred to this repeat.
The resistor drop alone is not labelled calibrated per-pin leakage, since
measurement loading and component tolerances are not separately established.

The same fixture can check CTRL1–3 individually at J1 pins 4–6, with output
disabled before each lead move and the 10 kΩ DUT_VIO-to-GND load retained.
No results for those channels, firmware changes, flash, all-channel acceptance
or complete manufactured-board acceptance are established by this repeat.

## CTRL1–3 loaded missing-DUT_VIO observations — 2026-11-19

For the same USB-powered, no-DUT fixture, PPK2 set to 1800 mV through a
10 kΩ series resistor to one control at a time and a separate 10 kΩ load
from DUT_VIO to ground, the operator supplied:

| Channel | J1 pin | Source voltage | Channel voltage | Loaded DUT_VIO | PPK2 average current, probes removed |
|---|---|---|---|---|---|
| CTRL1 | 4 | **1.756 V** | **1.750 V** | **0.002 V** | **10 nA** |
| CTRL2 | 5 | **1.757 V** | **1.754 V** | **0.005 V** | **14 nA** |
| CTRL3 | 6 | **1.756 V** | **1.754 V** | **0.001 V** | **12 nA** |

Source-to-channel differences are 6, 3 and 2 mV respectively. Each channel
remains close to its external source while loaded DUT_VIO remains at 1–5 mV.
Together with CTRL0's consistent repeat, this supports static control-channel
isolation for the missing-DUT_VIO condition at the measured operating point.
Reported nA readings were obtained with meter probes removed, rather than
simultaneously with each channel-voltage reading; resistor-drop estimates
and these current readings are not treated as calibrated per-pin leakage.
No new numeric acceptance limit, all-supply-order, transient, other-channel
or full manufactured-board acceptance is established by these observations.

The same fixture applies individually to DUT_UART_RX/J1.8 and the event
inputs: EVENT2/J1.9, EVENT3/J1.10, EVENT0/J1.11 and EVENT1/J1.12. DUT_UART_TX
at J1.7 requires separate interpretation: R13 intentionally connects its
after-RN5A translator-input node to DUT_VIO through 10 kΩ, so injected
current can raise the loaded rail through that passive path. A blanket
near-zero-VIO expectation must not be applied to that pin. No measurements
of these remaining channels, firmware/image change or flash occurred here.

## UART RX and EVENT2–3 loaded missing-DUT_VIO observations — 2026-11-19

For the same USB-powered, no-DUT fixture, PPK2 set to 1800 mV through a
10 kΩ series resistor to one signal at a time and a separate 10 kΩ load
from DUT_VIO to ground, the operator supplied:

| Signal | J1 pin | Source voltage | Signal voltage | Loaded DUT_VIO | PPK2 average current, probes removed |
|---|---|---|---|---|---|
| DUT_UART_RX | 8 | **1.756 V** | **1.750 V** | **0.002 V** | **0.35 µA** |
| EVENT2 | 9 | **1.756 V** | **1.745 V** | **0.001 V** | **0.35 µA** |
| EVENT3 | 10 | **1.755 V** | **1.752 V** | **0.001 V** | **0.32 µA** |

The UART RX signal value was supplied as `1.750` in the voltage field and
is interpreted in volts consistent with the requested column order.
Source-to-signal differences are 6, 11 and 3 mV respectively, with loaded
DUT_VIO at 1–2 mV. These readings support static externally pulled-high
isolation for these three signals under the tested missing-DUT_VIO condition.
Currents retain the reported µA units and probes-removed method; no calibrated
per-pin leakage or new numeric acceptance criterion is assigned. Active UART
function, event capture, remaining channel results, transient behavior and
full board acceptance are not established. No firmware/image change or flash
occurred.

## EVENT0–1 loaded missing-DUT_VIO observations — 2026-11-19

With the same USB-powered, no-DUT fixture, PPK2 set to 1800 mV through one
10 kΩ series resistor and a second 10 kΩ resistor loading DUT_VIO to ground,
the operator supplied:

| Signal | J1 pin | Source voltage | Signal voltage | Loaded DUT_VIO | PPK2 average current, probes removed |
|---|---|---|---|---|---|
| EVENT0 | 11 | **1.756 V** | **1.749 V** | **0.001 V** | **0.36 µA** |
| EVENT1 | 12 | **1.756 V** | **1.746 V** | **0.001 V** | **0.35 µA** |

Source-to-signal differences are 7 and 10 mV, with loaded DUT_VIO at 1 mV.
These support the same static externally pulled-high isolation behavior seen
on the other event inputs at the tested operating point. Measurements now
cover all four controls, four event inputs and DUT_UART_RX in this supply
condition. They do not establish active event capture, UART functionality,
calibrated per-pin leakage or full board acceptance.

For DUT_UART_TX/J1.7, the same fixture must be interpreted with the intentional
R13 10 kΩ path from the after-RN5A signal node to DUT_VIO. Injected current
through this resistor can raise the loaded rail. Record source, J1.7, VIO
and probes-removed current before drawing a conclusion; a nonzero VIO reading
alone does not identify a translator-isolation failure on this path. No result
for that pin or firmware/image change or flash is established here.

## UART TX passive supply coupling with missing DUT_VIO — 2026-11-19

With the same USB-powered, no-DUT fixture, PPK2 set to 1800 mV through an
external 10 kΩ resistor to DUT_UART_TX/J1.7 and a second external 10 kΩ
resistor loading DUT_VIO/J1.14 to ground, the operator supplied:

| Measurement | Reported result |
|---|---|
| PPK2 VOUT before series resistor | **1.749 V** |
| DUT_UART_TX, J1 pin 7 | **1.136 V** |
| Loaded DUT_VIO, J1 pin 14 | **0.536 V** |
| PPK2 average current, meter probes removed | **62 µA** |

The external source resistor drop is 0.613 V, implying approximately 61.3 µA
using its nominal 10 kΩ value, close to the reported probes-removed current.
The approximately 0.600 V signal-to-VIO difference is consistent with about
60 µA through fitted R13 and the small RN5A series resistance. At VIO=0.536 V,
the nominal external ground load draws 53.6 µA and the enabled 94 kΩ sense
divider draws approximately 5.7 µA, explaining most of that current path.
These are circuit estimates, not calibrated or simultaneous current readings.

This is observed passive back-feed into DUT_VIO through the fitted UART
pull-up, consistent with the documented topology. It must not be labelled
zero-back-feed acceptance for J1.7 or attributed to a translator fault from
these readings alone. A floating DUT rail can settle differently from this
defined 10 kΩ loaded rail. No hardware redesign, firmware change or full
manufactured-board acceptance is established by this observation.

The reverse-supply fixture begins with PPK2 output off and Pico USB removed.
Remove both prior resistor connections, supply DUT_VIO/J1.14 directly from
PPK2 set to 1875 mV, connect one 10 kΩ resistor from VIO to CTRL0/J1.3,
and connect the other from helper 3V3/Pico pin 36 to J1 ground. Record actual
VIO, CTRL0, loaded 3V3, GP28 and probes-removed current; source setting alone
does not establish the actual low-voltage operating point. No reverse loaded
result or flash occurred in this observation.

## Reverse-supply fixture access limitation — 2026-11-19

The operator reported that Pico pin 36 cannot easily accept a jumper wire.
Inspection of the current PCB's +3.3V pads found the A1 through-hole socket
pad 36 and small SMD device/capacitor pads, without a dedicated 3V3 test point
or separate header. The underside socket-pad solder joint is electrically
equivalent, but access for a secure load connection was not confirmed.
The current source does not independently identify the manufactured revision.

The initial reverse-supply CTRL0 observation is therefore adapted to omit
the external 10 kΩ 3V3-to-GND load. With all power off while rewiring, remove
the previous VIO-to-ground resistor and J1.7 injection connection. Keep Pico
USB disconnected; connect PPK2 VOUT directly to J1.14, GND to J1.1, and one
10 kΩ pull-up from J1.14 to CTRL0/J1.3. PPK2 setting remains the proposed
1875 mV; record actual VIO, CTRL0, DMM-measured 3V3 and GP28 plus current.

This retains an externally pulled-up CTRL0 check but measures the debugger
rail without a defined external load. Results must not be labelled completion
of the proposed loaded debugger-rail isolation test. No new measurements,
firmware/image change or flash occurred while adapting the fixture.

## Reverse CTRL0 preliminary readings pending fixture verification — 2026-11-19

For the USB-disconnected reverse fixture with the external 3V3 load omitted,
the operator supplied:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.832 V** |
| CTRL0, J1 pin 3 | **0 V** |
| Helper 3V3, Pico pin 36, DMM only | **0.001 V** |
| GP28, Pico pin 34 | **0.002 V** |
| PPK2 average current, meter probes removed | **0.40 µA** |

If a nominal 10 kΩ pull-up continuously connects the measured 1.832 V VIO
to CTRL0 at 0 V, its current alone would be approximately 183.2 µA. This
does not match the supplied 0.40 µA average under the intended steady setup.
The fixture connections, resistor value, measured nodes, output-enable timing
and averaging interval have not been independently verified. The readings
therefore do not establish a driver pulling CTRL0 low or a valid isolation
result. Low 3V3/GP28 observations are retained without upgrading them to the
still-unperformed externally loaded debugger-rail check.

Requested verification with USB and PPK2 VOUT disconnected and rails discharged:
numeric resistance from the intended VIO-side resistor lead to J1.14, from
the CTRL0-side lead to J1.3, and across the resistor. Also requested whether
the reported current was taken while output remained enabled. No diagnosis,
firmware/image change, flash or further channel measurement occurred here.

## Reverse CTRL0 pull-up continuity confirmation — 2026-11-19

In response to the power-off fixture check, the operator reported:

| Measurement or condition | Reported result |
|---|---|
| VIO-side resistor lead to J1 pin 14 | **0 Ω** |
| CTRL0-side resistor lead to J1 pin 3 | **0 Ω** |
| Across the resistor | **10 kΩ** |
| Earlier 0.40 µA recorded with PPK2 output on | **Yes; Pico USB disconnected** |

These checks support the intended 10 kΩ pull-up connection at the time of
the resistance measurement. USB disconnected is correct for the reverse
supply test. They do not yet resolve the earlier powered voltage/current
mismatch. A powered repeat will measure VIO and CTRL0 relative to J1 ground,
then directly across the resistor (red at the VIO end, black at the CTRL0 end)
without moving fixture connections. After removing meter probes, a fresh
PPK2 recording of the continuously enabled steady state will establish the
current for that repeat, rather than assigning a cause to the earlier result.
No new powered readings, fault diagnosis, firmware/image change or flash
occurred in this confirmation.

## Reverse CTRL0 powered voltage repeat — 2026-11-19

For the unchanged reverse fixture, Pico USB disconnected, source applied
directly to VIO and a 10 kΩ pull-up from VIO to CTRL0, the operator supplied:

| Measurement | Reported result |
|---|---|
| J1 pin 14 to GND | **1.86 V** |
| J1 pin 3 to GND | **1.83 V** |
| Direct resistor drop, red at VIO end and black at CTRL0 end | **approximately 0.0 V** |

CTRL0 now follows VIO through the pull-up; the earlier 0 V CTRL0 result is
not reproduced. Preserve the reported precision: the two node readings
differ by 30 mV, while the separate direct reading was supplied only as
approximately zero. No exact drop, calibrated leakage or cause of the earlier
reading is inferred. Fresh current and 3V3/GP28 readings were not included
in this reply and are requested to complete this repeat; older readings are
not reassigned to it. The external 3V3 load remains omitted for access reasons.
No isolation acceptance, firmware/image change or flash occurred here.

## Reverse CTRL0 fresh current and rail readings — 2026-11-19

The operator completed the same unchanged reverse CTRL0 fixture measurement
set with Pico USB disconnected, source applied directly to DUT_VIO, a 10 kΩ
VIO-to-CTRL0 pull-up, and no external 3V3 load:

| Measurement | Reported result |
|---|---|
| Helper 3V3, Pico pin 36 | **0.0 V** |
| GP28, Pico pin 34 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **0.33 µA** |

Together with the preceding powered repeat (VIO 1.86 V, CTRL0 1.83 V and
direct resistor drop approximately zero), these support the preliminary
externally pulled-high CTRL0 check with debugger USB absent. Neither measured
debugger node shows a reported voltage rise. The original zero CTRL0 result
is not reproduced and its cause remains unestablished; this set does not
silently replace it or transfer its measurements to a different setup.

The externally loaded debugger-rail isolation check remains unperformed due
to access limitations. Current is total VIO input current, not calibrated
per-pin leakage. CTRL1–3 can be checked individually using the same fixture,
with output disabled before moving the pull-up. No other reverse channel
result, full isolation acceptance, firmware/image change or flash occurred.

## Reverse CTRL1–3 preliminary observations — 2026-11-19

With Pico USB disconnected, PPK2 set to 1875 mV directly supplying DUT_VIO,
one 10 kΩ pull-up from VIO to the selected control and no external debugger
3V3 load, the operator supplied:

| Channel | J1 pin | Actual DUT_VIO | Control voltage | Pico 3V3, DMM only | Fresh PPK2 average current, probes removed |
|---|---|---|---|---|---|
| CTRL1 | 4 | **1.874 V** | **1.846 V** | **0.0 V** | **0.35 µA** |
| CTRL2 | 5 | **1.874 V** | **1.848 V** | **0.0 V** | **0.36 µA** |
| CTRL3 | 6 | **1.875 V** | **1.850 V** | **0.0 V** | **0.34 µA** |

All three controls follow their external pull-up and 3V3 shows no reported
rise. Values retain their reported precision. Separate node-voltage and
probes-removed current observations are not used to infer exact per-pin
leakage or a calibrated resistor-drop/current relationship. Together with
CTRL0's repeat, these support the preliminary USB-absent control sweep at
the measured operating points. The intended externally loaded 3V3 isolation
check remains pending; no full acceptance is established.

The same preliminary fixture applies individually to UART TX/J1.7, UART
RX/J1.8 and EVENT2/3/0/1 at J1.9/10/11/12. Retain the direct source on VIO
and move only the signal end of the 10 kΩ pull-up with output disabled.
No measurements for those reverse channels, firmware/image change or flash
occurred in this observation.

## Reverse UART/event preliminary observations — 2026-11-19

With Pico USB disconnected, PPK2 set to 1875 mV directly supplying DUT_VIO,
one external 10 kΩ pull-up from VIO to the selected signal, and no external
debugger 3V3 load, the operator supplied:

| Signal | J1 pin | Actual DUT_VIO | Signal voltage | Pico 3V3, DMM only | Fresh PPK2 average current, probes removed |
|---|---|---|---|---|---|
| DUT_UART_TX | 7 | **1.874 V** | **1.862 V** | **0.0 V** | **0.30 µA** |
| DUT_UART_RX | 8 | **1.875 V** | **1.855 V** | **0.0 V** | **0.33 µA** |
| EVENT2 | 9 | **1.874 V** | **1.850 V** | **0.0 V** | **0.70 µA** |
| EVENT3 | 10 | **1.875 V** | **1.849 V** | **0.0 V** | **0.70 µA** |
| EVENT0 | 11 | **1.875 V** | **1.849 V** | **0.0 V** | **0.70 µA** |
| EVENT1 | 12 | **1.875 V** | **1.846 V** | **0.0 V** | **0.70 µA** |

All six signals follow VIO and Pico 3V3 shows no reported rise. Together
with the preceding control repeats, the preliminary USB-absent sweep covers
all ten external digital signals at the recorded low-voltage points. This
does not establish the omitted externally loaded 3V3 check, calibrated
per-pin leakage, other voltage points, active UART/event functionality,
power-transition waveforms or full manufactured-board acceptance.

The next procedural observation retains a single external pull-up on
CTRL0/J1.3, moved with PPK2 output off, and applies VIO before debugger USB.
With PPK2 setting 1875 mV retained, record settled VIO/CTRL0/3V3/GP28 and
fresh current with USB absent, then connected, then absent again. Keep DUT
disconnected and send no control/UART commands. This is a DC supply-order
observation; it cannot capture brief startup glitches or establish safe
behavior for every channel/order. No sequencing result, firmware/image
change or flash occurred in this observation.

## VIO-first CTRL0 settled supply sequence — 2026-11-19

With direct PPK2 supply to DUT_VIO at setting 1875 mV, a 10 kΩ pull-up from
VIO/J1.14 to CTRL0/J1.3, no DUT or commands and no external 3V3 load,
the operator performed the requested USB sequence and supplied:

| Ordered state | Actual DUT_VIO | CTRL0 | Pico 3V3 | GP28 | Fresh PPK2 average current |
|---|---|---|---|---|---|
| Enable PPK2, USB disconnected | **1.875 V** | **1.850 V** | **0.0 V** | **0.0 V** | **0.33 µA** |
| Connect Pico USB, leave PPK2 on | **1.855 V** | **1.835 V** | **3.277 V** | Not reported | **20.76 µA** |
| Disconnect Pico USB, leave PPK2 on | **1.875 V** | **1.850 V** | **0.0 V** | Not reported | **0.34 µA** |

The last two supplied rows contain only three voltages followed by current;
no GP28 value is inferred or substituted from earlier observations. CTRL0
remains close to VIO in all three settled states; debugger 3V3 rises with
USB and returns to a reported zero after removal. These are bounded settled
DC observations on CTRL0, not transient capture, direct enable-/OE-node
measurements, all-channel/order acceptance or full hardware acceptance.

The complementary USB-first procedure retains the same wiring and source
setting, with PPK2 output initially off and VOUT still attached. Connect USB,
record settled VIO/CTRL0/3V3/GP28, enable PPK2 and repeat the four voltages plus
fresh current, then disable PPK2 and repeat the four voltages. Current with
output disabled is not requested as a board leakage measurement. Since the
disabled source remains attached, its output impedance may influence the
off-state voltages; this procedure does not replace the physically
disconnected-source or defined-load isolation checks. No complementary
sequence result, firmware/image change or flash occurred here.

## Completed sequence data and GP28 startup-order difference — 2026-11-19

The operator resupplied the VIO-first sequence with the missing GP28 values
and supplied the complementary USB-first sequence. Wiring and requested
setting remain the same CTRL0 pull-up fixture at PPK2 setting 1875 mV,
without an external 3V3 load:

| VIO-first ordered state | Actual DUT_VIO | CTRL0 | Pico 3V3 | GP28 | PPK2 average current |
|---|---|---|---|---|---|
| Enable PPK2, USB disconnected | **1.875 V** | **1.850 V** | **0.0 V** | **0.0 V** | **0.33 µA** |
| Connect Pico USB, PPK2 on | **1.855 V** | **1.835 V** | **3.277 V** | **0.0 V** | **20.76 µA** |
| Disconnect Pico USB, PPK2 on | **1.875 V** | **1.850 V** | **0.0 V** | **0.0 V** | **0.34 µA** |

| USB-first ordered state | Actual DUT_VIO | CTRL0 | Pico 3V3 | GP28 | Supplied PPK2 current |
|---|---|---|---|---|---|
| USB on, PPK2 off | **0.0 V** | **0.0 V** | **3.277 V** | **0.0 V** | **0.99 nA** |
| USB on, PPK2 on | **1.860 V** | **1.840 V** | **3.277 V** | **0.911 V** | **20 µA** |
| USB on, PPK2 off again | **0.0 V** | **0.0 V** | **3.277 V** | **0.0 V** | **1 nA** |

The original omitted GP28 entries are retained above as historical report
scope; the resupplied entries are explicit operator observations. Source-off
currents were not requested and are retained as displayed values, not board
leakage measurements with a disabled source attached.

CTRL0 follows VIO and 3V3 follows USB in both sequences. However, the reported
GP28=0 V when VIO precedes USB differs from GP28=0.911 V when USB precedes
VIO. With VIO and 3V3 present, the intended enabled divider should produce
approximately half VIO regardless of order. The reported difference therefore
requires reproduction before concluding sense-path sequencing is verified.
No measurement error, hardware fault or firmware cause is assigned.

Requested a minimal VIO-first repeat from both supplies off, with the same
wiring and source setting: enable PPK2, then connect USB, wait for settling,
measure VIO, 3V3 and GP28 at Pico physical pin 34 relative to J1.1, and obtain
fresh probes-removed current. No new firmware, flash or acceptance conclusion
is introduced by this request.

## VIO-first GP28 repeat from both supplies off — 2026-11-19

The operator repeated the requested VIO-first sequence with unchanged wiring
and source setting: both supplies off for 10 seconds, PPK2 on for 10 seconds,
then USB connected and settled for 10 seconds. Supplied readings were:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.855 V** |
| Pico 3V3, physical pin 36 | **3.277 V** |
| GP28, physical pin 34 | **0.907 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **20 µA** |

GP28 is approximately half VIO and is no longer reported at zero in this
VIO-first repeat. The preceding USB-first result was 0.911 V at VIO 1.860 V.
The original zero reading is preserved but not reproduced; its cause remains
unassigned. These observations do not justify a new firmware change or
establish precise divider accuracy, transient behavior or all-channel/order
sequencing acceptance.

## Active CTRL0 open-drain bench setup and command acknowledgements — 2026-11-19

With the same direct VIO supply and 10 kΩ VIO-to-CTRL0 pull-up retained,
USB connected and DUT absent, a direct exclusive serial bench session was
started after finding no serial owner or TCP 2040 service listener. The
known helper enumerated at `/dev/cu.usbmodem11201`, serial FA63A4D787572B33.
Live hello verified normal `gp28safe-1`, protocol v1 and the exact five
existing capabilities. The bench session asserted DTR, which starts normal
UART acquisition/translator behavior, but sent no UART payload commands.

Commands and acknowledgements:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL0","mode":"open_drain","active_level":"low"}
{"ok":true,"timestamp_us":786171293}
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":786181312}
```

The session holds CTRL0 commanded low for the physical measurement; an ACK
alone does not establish the output voltage or electrical acceptance. Other
controls were not configured by this bench session. The temporary script
accepts only open-drain configure/state operations on CTRL0–3, forbids changing
selected channel while active, and requests firmware safe state by dropping
DTR on close/error or after a 30-minute hold deadline. Release and close
must be recorded after the measurement; they have not yet occurred here.

The script syntax check passed before execution; its exact source and hash,
UTC records, command bytes, responses and received telemetry are preserved in
[the bench JSONL evidence](evidence/20261119-kicad-rev-a-control-bench.jsonl).
This direct electrical fixture does not create v2 Device Core session evidence
or establish functional HIL acceptance. No firmware/image change or flash
occurred.

## CTRL0 asserted measurement and release acknowledgement — 2026-11-19

With the direct bench session holding CTRL0 open-drain active low and the
external 10 kΩ VIO-to-CTRL0 pull-up retained, the operator supplied:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.870 V** |
| CTRL0, J1 pin 3 | **0.37 V** |
| Pico 3V3, physical pin 36 | **3.277 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

At nominal 10 kΩ, the pull-up current from the measured node voltages is
approximately 150 µA. The board additionally sinks the active-low /OE pull-up
through U7: at nominal 4.7 kΩ this contributes roughly 0.4 mA when asserted.
Total VIO current therefore cannot be attributed solely to the external load.
These are circuit estimates, without per-path current or simultaneous voltage
measurement. The UART translator is enabled by this DTR-active bench epoch.

[TI SN74LV4T125 datasheet §6.5](https://www.ti.com/lit/ds/symlink/sn74lv4t125.pdf)
specifies buffer-pin VOL under defined VCC/load/temperature conditions. The
observed 0.37 V is at the connector, after the nominal 180 Ω control-series
path, whose drop at the estimated 150 µA is about 27 mV. This first reading
requires review of the active path before asserting electrical acceptance;
it is not declared a pass or a diagnosed buffer/firmware fault.

The same bench session then sent:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":1092460518}
```

The session now holds CTRL0 released while awaiting physical VIO/CTRL0/fresh
current readings. The ACK alone does not establish release voltage. No wiring
change, next-channel test, firmware change, flash or session close occurred.

## CTRL0 physical release and accessible-header diagnostic setup — 2026-11-19

After the idle acknowledgement, with the same powered fixture and external
10 kΩ pull-up retained, the operator supplied:

| Released-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.855 V** |
| Released CTRL0, J1 pin 3 | **1.838 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **20 µA** |

CTRL0 returns close to VIO through its pull-up and current returns to 20 µA.
This supports physical release at this operating point; it does not resolve
the first asserted 0.37 V reading or complete control-level acceptance.

Source inspection verified CTRL0 enable GP8/Pico physical pin 11 and data
GP9/physical pin 12 in both the firmware overlay and carrier A1 net mapping.
U1 output pin 3 routes to RN3C pad 3, with RN3 pad 6 on DUT_CTRL0/J1.3;
RN3's design value is 180 Ω. These are source relationships, not independent
assembly/value measurements. Fine pad probing may be obstructed by the Pico,
so accessible enable/data header readings are requested first with an exact
repeat of connector voltage and fresh current.

The same bench session reasserted CTRL0:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":1446313910}
```

Expected commanded header levels are enable approximately 3.3 V and data
near ground. Physical readings are pending; no enable/data fault, firmware
cause, wiring change, firmware/image change or flash is inferred here.

## CTRL0 decimal correction, repeat assertion and CTRL1 setup — 2026-11-19

In the repeated asserted state, the operator supplied:

| Measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.868 V** |
| CTRL0, J1 pin 3 | **0.037 V** |
| CTRL0 enable, Pico physical pin 11 / GP8 | **3.3 V** |
| CTRL0 data, Pico physical pin 12 / GP9 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

The operator explicitly corrected the earlier 0.37 V report as a decimal
transcription of 0.037 V. That original report and the resulting investigation
remain recorded above; the corrected value is used for interpretation. At
nominal 10 kΩ, the repeated pull-up current is about 183 µA. Its drop across
the nominal 180 Ω control-series resistor is about 33 mV, consistent with
the 37 mV connector reading and a small buffer output low voltage. This is
a circuit-consistency inference, not an independent resistor/value or buffer
pin measurement. The commanded enable/data header levels are observed.

Together with the prior physical release (VIO 1.855 V, CTRL0 1.838 V,
current 20 µA), these support static open-drain assertion and release for
CTRL0 at this supply/load point. The 690 µA is total VIO current, including
the enable pull-up path, and is not calibrated per-path/current-budget proof.
No hardware or firmware fix is indicated by the corrected output level.

The bench session then acknowledged these commands in order:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":1734071521}
{"cmd":"configure_gpio_mode","channel":"CTRL1","mode":"open_drain","active_level":"low"}
{"ok":true,"timestamp_us":1737973009}
{"cmd":"set_control_state","channel":"CTRL1","state":"active"}
{"ok":true,"timestamp_us":1741623812}
```

CTRL0 is released; CTRL1 is commanded low in preparation for moving only
the pull-up signal end from J1.3 to J1.4 with PPK2 output off. Keep USB
connected so the bench epoch persists, then restore the unchanged 1875 mV
source setting and record VIO/CTRL1/fresh current. No physical CTRL1 result,
firmware/image change, flash, session close or full board acceptance occurred.

## CTRL1 assertion and release acknowledgement — 2026-11-19

After moving the pull-up signal end to J1.4 with output off and restoring
PPK2 at the unchanged 1875 mV setting, USB/bench epoch retained, the operator
supplied:

| Asserted-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.868 V** |
| Asserted CTRL1, J1 pin 4 | **0.037 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

This matches the corrected CTRL0 assertion at the same reported supply/load
point. Physical release must be measured separately before completing the
channel's assertion/release observation. The same bench session then sent:

```json
{"cmd":"set_control_state","channel":"CTRL1","state":"idle"}
{"ok":true,"timestamp_us":1892276941}
```

CTRL1 is held released awaiting voltage/current readings, with the 10 kΩ
pull-up retained and no subsequent wiring change. No next-channel measurement,
firmware/image change, flash, session close or full board acceptance occurred.

## CTRL1 physical release and renewed CTRL2 bench session — 2026-11-19

With CTRL1 commanded idle and the same pull-up/wiring retained, the operator
reported VIO=**1.856 V**, released CTRL1/J1.4=**1.834 V**, and fresh current
without meter probes=**20 µA**. Together with its prior assertion at 37 mV,
this supports CTRL1 static open-drain assertion/release at this supply/load
point, without full channel-range or manufactured-board acceptance.

The first bench session briefly configured/asserted CTRL2 in preparation,
then returned it idle and closed to renew its measurement window before the
30-minute hold deadline. Command success timestamps were configure=2146848543,
active=2150532756 and idle=2202146231 µs. DTR was deasserted, the port closed,
and no serial owner remained. The frozen first log verifies 1,443 JSON records,
11 commands with 11 successful responses, matching archived source hash and
the final port-closed record. Its SHA-256 is
`21247ee39a836635d0e55f9dd812c129a52720225309542b2678a46246310fa5`.
No physical CTRL2 measurement is assigned to that initial preparation.

The temporary bench script gained initial-channel/run arguments to start the
renewed session directly on CTRL2 and use a separate evidence file. Syntax
check passed; exact source and hash are archived in
[bench run 2](evidence/20261119-kicad-rev-a-control-bench-2.jsonl). Renewed
exclusive session 40845 reverified the same USB serial and `gp28safe-1` hello,
then acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL2","mode":"open_drain","active_level":"low"}
{"ok":true,"timestamp_us":2216045725}
{"cmd":"set_control_state","channel":"CTRL2","state":"active"}
{"ok":true,"timestamp_us":2216055728}
```

CTRL2 is held active awaiting the external pull-up move from J1.4 to J1.5
with PPK2 output off, USB retained, followed by voltage/current measurement.
The renewed epoch starts other controls unconfigured/high impedance. No
firmware/image change, flash, physical CTRL2 result or full acceptance occurred.

## CTRL2 assertion and release acknowledgement — 2026-11-19

After moving the pull-up to CTRL2/J1.5 with PPK2 off, USB retained, and
restoring output at the unchanged 1875 mV setting, the operator supplied:

| Asserted-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.868 V** |
| Asserted CTRL2, J1 pin 5 | **0.037 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

This matches the corrected CTRL0 and CTRL1 assertions at the same reported
supply/load point. Bench session 40845 then acknowledged release:

```json
{"cmd":"set_control_state","channel":"CTRL2","state":"idle"}
{"ok":true,"timestamp_us":2421483459}
```

CTRL2 remains commanded released with unchanged wiring pending physical
VIO/CTRL2/fresh-current readings. No next-channel measurement, firmware/image
change, flash, session close or full board acceptance occurred.

## CTRL2 physical release and CTRL3 setup — 2026-11-19

With CTRL2 commanded idle and the same pull-up/wiring retained, the operator
reported VIO=**1.856 V**, released CTRL2/J1.5=**1.835 V**, and fresh current
without meter probes=**20 µA**. Together with its prior 37 mV assertion,
this supports CTRL2 static open-drain assertion/release at this supply/load
point. No full channel-range or manufactured-board acceptance is inferred.

The same bench session then acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL3","mode":"open_drain","active_level":"low"}
{"ok":true,"timestamp_us":2539177777}
{"cmd":"set_control_state","channel":"CTRL3","state":"active"}
{"ok":true,"timestamp_us":2542774180}
```

CTRL2 is released and CTRL3 commanded low, awaiting movement of the pull-up
signal end J1.5 to J1.6 with output off and USB retained, followed by fresh
voltage/current readings. No physical CTRL3 result, firmware/image change,
flash, session close or full board acceptance occurred.

## CTRL3 assertion and release acknowledgement — 2026-11-19

After moving the pull-up to CTRL3/J1.6 with PPK2 off, USB retained, and
restoring output at the unchanged 1875 mV setting, the operator supplied:

| Asserted-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.868 V** |
| Asserted CTRL3, J1 pin 6 | **0.037 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

All four controls have matching asserted measurements at this supply/load
point. The same bench session then acknowledged CTRL3 release:

```json
{"cmd":"set_control_state","channel":"CTRL3","state":"idle"}
{"ok":true,"timestamp_us":2692985968}
```

CTRL3 is held released awaiting physical VIO/CTRL3/current readings, with
unchanged wiring. Its released measurement and session close remain pending;
no firmware/image change, flash or full board acceptance occurred.

## CTRL3 physical release, consolidated open-drain observations and bench stop — 2026-11-19

With CTRL3 commanded idle and the same pull-up/wiring retained, the operator
reported VIO=**1.857 V**, released CTRL3/J1.6=**1.834 V**, and fresh current
without meter probes=**20 µA**. The operator then requested stopping bench
work until tomorrow. Consolidated latest valid observations are:

| Channel | J1 pin | Asserted VIO | Asserted output | Asserted current | Released VIO | Released output | Released current |
|---|---|---|---|---|---|---|---|
| CTRL0 | 3 | **1.868 V** | **0.037 V** | **690 µA** | **1.855 V** | **1.838 V** | **20 µA** |
| CTRL1 | 4 | **1.868 V** | **0.037 V** | **690 µA** | **1.856 V** | **1.834 V** | **20 µA** |
| CTRL2 | 5 | **1.868 V** | **0.037 V** | **690 µA** | **1.856 V** | **1.835 V** | **20 µA** |
| CTRL3 | 6 | **1.868 V** | **0.037 V** | **690 µA** | **1.857 V** | **1.834 V** | **20 µA** |

Method: normal fitted `gp28safe-1`, USB powered, no DUT, PPK2 Source Meter
setting 1875 mV, nominal 10 kΩ VIO-to-selected-control pull-up, Fluke 115 DC
volts relative to J1.1, fresh 10-second current averages with probes removed.
CTRL0's earlier 0.37 V report was explicitly corrected by the operator to
0.037 V; the original and correction remain preserved above. These complete
the four-channel static open-drain observations at the recorded supply/load
points, without establishing all-voltage/temperature behavior, transient
glitches, calibrated leakage, push-pull behavior, v2 service/HIL or full
manufactured-board acceptance. The external 3V3-load access limitation remains.

Bench session 40845 closed normally after the physical release report. DTR
was deasserted, the port closed, and no serial owner or TCP 2040 listener
remained. Both bench logs were parsed and verified for exact hello identity,
matching archived source hash, command bytes, one successful response per
command in order, and final DTR-low/port-closed records. Run 1 has 1,443 JSON
records and 11 commands; run 2 has 627 records and six commands. Log hashes:

- Run 1: `21247ee39a836635d0e55f9dd812c129a52720225309542b2678a46246310fa5`.
- Run 2: `ea2499eb5ab9d8390ee1ca41ec95303c208f12e608d4334b3a47a7272becd7e4`.

[The machine-readable open-drain summary](evidence/20261119-kicad-rev-a-open-drain-summary.json)
contains measurements, scope, source/log hashes and host close checks. Host
cleanup is verified; the operator was instructed to turn PPK2 output off
and disconnect Pico USB, but physical shutdown has not yet been confirmed.
No further actuation, firmware/image change or flash occurred during stop.

## Push-pull CTRL0 fixture preparation on resume — 2026-11-20

The operator requested resuming work. The saved next test is push-pull control
voltage behavior, beginning with CTRL0 near the low supported voltage point.
Existing firmware, physical evidence and operator-owned CAD changes remain
preserved; no new firmware or hardware fix is proposed for this test.

Prepared fixture, pending operator confirmation:

- PPK2 output off while removing yesterday's external VIO-to-control pull-up.
- One external 10 kΩ resistor from CTRL0/J1.3 to GND/J1.1, loading a driven
  high output toward ground; second loose resistor unused.
- PPK2 VOUT directly to DUT_VIO/J1.14, PPK2 GND to J1.1, setting 1875 mV;
  output remains off pending the configured state and measurement instruction.
- Pico fitted and USB connected; DUT absent. Meter is Fluke 115 DC volts
  relative to J1.1; current uses a fresh 10-second probes-removed interval.

Source inspection confirms push-pull active high/idle low is an existing
supported configuration. Both states actively drive the selected output;
idle low is not the open-drain released state. The temporary single-channel
bench script syntax check passed. A fresh USB epoch per channel avoids
retaining other push-pull outputs enabled during subsequent measurements.
It verifies the known serial, `gp28safe-1` hello and five capabilities before
sending commands, archives its exact source/bytes/responses, and drops DTR
on close/error or a 30-minute hold deadline. This direct electrical test does
not establish v2 Device Core/HIL acceptance.

Enumeration found the known serial at `/dev/cu.usbmodem11401`, with no serial
owner or TCP 2040 listener. No port was opened, no command was sent and no
new push-pull physical result, firmware/image change or flash occurred in
this preparation. The prior external-3V3-load access limitation remains.

## CTRL0 push-pull confirmed load and HIGH command — 2026-11-20

The operator confirmed the prepared external 10 kΩ load from CTRL0/J1.3
to GND/J1.1, with PPK2 output off, Pico USB connected and no DUT. Enumeration
and ownership checks were repeated: known serial FA63A4D787572B33 at
`/dev/cu.usbmodem11401`, no serial owner or TCP 2040 listener.

Exclusive bench session 22724 asserted DTR and verified the exact normal
`gp28safe-1` hello, protocol v1, device `dutchmate-rp2350` and five existing
capabilities. This starts the normal UART epoch/translator, without sending
UART payloads. It then sent:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL0","mode":"push_pull","active_level":"high","idle_level":"low"}
{"ok":true,"timestamp_us":316679583}
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":316688497}
```

CTRL0 is held commanded HIGH, pending enabling PPK2 at the unchanged 1875 mV
setting and measuring actual VIO, loaded CTRL0 voltage, Pico 3V3 and fresh
10-second probes-removed current. An ACK is not physical voltage evidence.
No other control is configured in this fresh epoch. Exact source/hash, command
bytes, responses and telemetry are preserved in
[the push-pull bench log](evidence/20261120-kicad-rev-a-push-pull-bench.jsonl).
The session remains open for HIGH/LOW measurements; no physical HIGH result,
session close, firmware/image change or flash occurred here.

## CTRL0 push-pull HIGH observation and LOW command — 2026-11-20

With USB connected, no DUT, the external 10 kΩ CTRL0-to-GND load retained,
and PPK2 output enabled at setting 1875 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.866 V** |
| CTRL0 HIGH, J1 pin 3 | **1.827 V** |
| Pico 3V3, physical pin 36 | **3.277 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

The supply-to-output difference is 39 mV. At nominal 10 kΩ, output load
current is about 183 µA, producing approximately 33 mV across the nominal
180 Ω series resistor. This is consistent with the observed HIGH voltage,
without independently measuring the buffer pin or component values or
establishing all-voltage/load/temperature acceptance. Current is total VIO
input current, including the active control enable path.

The same bench session commanded the actively driven LOW state:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":490996555}
```

In this push-pull configuration, idle means actively driven LOW, with /OE
still asserted; it does not mean the open-drain released state. The 20 µA
open-drain released baseline is therefore not a required LOW-state current.
Physical LOW/VIO/fresh-current readings remain pending with unchanged wiring.
No session close, firmware/image change, flash or full acceptance occurred.

## CTRL0 push-pull LOW observation, closed epoch and CTRL1 setup — 2026-11-20

With the same external 10 kΩ CTRL0-to-GND load, USB connected and PPK2
setting 1875 mV, the operator supplied:

| LOW-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.833 V** |
| CTRL0 LOW, J1 pin 3 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **416 µA** |

Together with HIGH=1.827 V at VIO=1.866 V/current=690 µA, these record CTRL0
static HIGH/LOW voltages under the defined ground load at the measured supply
points. LOW remains actively configured, and its current includes the /OE
pull-up sink path. This is not a separate pull-up-loaded push-pull LOW test,
all-voltage/temperature/current characterization or full board acceptance.

Session 22724 then closed normally: DTR deasserted and port released, with
no serial owner or TCP 2040 listener found. The frozen first push-pull log
contains 321 valid JSON records, matching archived source hash, three command
byte sequences with three successful replies in order and final close record.
Its SHA-256 is
`55832e4538e97e8db839eb2659cb3b09f946b171667f27e693836ff57657abfc`.

Fresh exclusive session 56584 reverified the same normal `gp28safe-1` hello
and known serial, clearing prior control configuration through the closed
epoch. It acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL1","mode":"push_pull","active_level":"high","idle_level":"low"}
{"ok":true,"timestamp_us":641872446}
{"cmd":"set_control_state","channel":"CTRL1","state":"active"}
{"ok":true,"timestamp_us":641882444}
```

CTRL1 is held commanded HIGH pending movement of the load signal end from
J1.3 to J1.4 with PPK2 off, retaining the ground end on J1.1 and USB power,
then restoring output at setting 1875 mV. Physical VIO/CTRL1/current readings
are pending. Exact source and frames are in
[push-pull run 2](evidence/20261120-kicad-rev-a-push-pull-bench-2.jsonl).
No firmware/image change or flash occurred.

## CTRL1 push-pull HIGH observation and LOW command — 2026-11-20

With the external 10 kΩ load moved to CTRL1/J1.4-to-GND/J1.1, USB retained
and PPK2 output restored at setting 1875 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.867 V** |
| CTRL1 HIGH, J1 pin 4 | **1.827 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

This matches CTRL0's loaded HIGH output voltage, with a reported 40 mV
source-to-output difference. The same bench session then acknowledged the
actively driven LOW state:

```json
{"cmd":"set_control_state","channel":"CTRL1","state":"idle"}
{"ok":true,"timestamp_us":767674180}
```

Physical LOW/VIO/fresh-current readings remain pending with unchanged wiring.
The selected output stays enabled in LOW. No new channel result, session
close, firmware/image change, flash or full acceptance occurred.

## CTRL1 push-pull LOW observation, closed epoch and CTRL2 setup — 2026-11-20

With the same 10 kΩ CTRL1/J1.4-to-GND load, USB connected and PPK2 setting
1875 mV, the operator supplied:

| LOW-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.833 V** |
| CTRL1 LOW, J1 pin 4 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **415 µA** |

Together with HIGH=1.827 V at VIO=1.867 V/current=690 µA, these record the
static CTRL1 HIGH/LOW pair under the defined ground load at measured supply
points. No all-voltage/load/temperature or full board acceptance is inferred.

Session 56584 closed normally with DTR low and port released. No serial owner
or TCP 2040 listener was found before the next open. Frozen run 2 verifies
297 JSON records, archived source hash, three command byte sequences with
three successful replies in order and the final closed-port record. SHA-256:
`cd9a84e075e69b91e2f2bdbc3d111ec09855c0c6c5f4da119694d51b8f8a9c04`.

Fresh exclusive session 79413 reverified the normal `gp28safe-1` hello and
known serial, then acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL2","mode":"push_pull","active_level":"high","idle_level":"low"}
{"ok":true,"timestamp_us":939169677}
{"cmd":"set_control_state","channel":"CTRL2","state":"active"}
{"ok":true,"timestamp_us":939179672}
```

CTRL2 is held commanded HIGH pending movement of the load signal end from
J1.4 to J1.5 with PPK2 off, retaining the ground end on J1.1 and USB power,
then restoring output at setting 1875 mV. Physical VIO/CTRL2/current readings
are pending. Exact source and frames are in
[push-pull run 3](evidence/20261120-kicad-rev-a-push-pull-bench-3.jsonl).
No firmware/image change or flash occurred.

## CTRL2 push-pull HIGH observation and LOW command — 2026-11-20

With the external 10 kΩ load moved to CTRL2/J1.5-to-GND/J1.1, USB retained
and PPK2 output restored at setting 1875 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.867 V** |
| CTRL2 HIGH, J1 pin 5 | **1.827 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

This matches the preceding channels' loaded HIGH voltage/current at the
reported supply points. The same bench session then acknowledged the
actively driven LOW state:

```json
{"cmd":"set_control_state","channel":"CTRL2","state":"idle"}
{"ok":true,"timestamp_us":1045454464}
```

Physical LOW/VIO/fresh-current readings remain pending with unchanged wiring.
The selected output stays enabled in LOW. No new channel result, session
close, firmware/image change, flash or full acceptance occurred.

## CTRL2 push-pull LOW observation, closed epoch and CTRL3 setup — 2026-11-20

With the same 10 kΩ CTRL2/J1.5-to-GND load, USB connected and PPK2 setting
1875 mV, the operator supplied:

| LOW-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.833 V** |
| CTRL2 LOW, J1 pin 5 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **415 µA** |

Together with HIGH=1.827 V at VIO=1.867 V/current=690 µA, these record the
static CTRL2 HIGH/LOW pair under the defined ground load at measured supply
points. No all-voltage/load/temperature or full board acceptance is inferred.

Session 79413 closed normally with DTR low and port released. No serial owner
or TCP 2040 listener was found before the next open. Frozen run 3 verifies
205 JSON records, archived source hash, three command byte sequences with
three successful replies in order and the final closed-port record. SHA-256:
`58681fd6aab28f07db190a67faccc6528365265c52f9b1c9ecc4dce6561d03c0`.

Fresh exclusive session 48715 reverified the normal `gp28safe-1` hello and
known serial, then acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL3","mode":"push_pull","active_level":"high","idle_level":"low"}
{"ok":true,"timestamp_us":1146770402}
{"cmd":"set_control_state","channel":"CTRL3","state":"active"}
{"ok":true,"timestamp_us":1146780591}
```

CTRL3 is held commanded HIGH pending movement of the load signal end from
J1.5 to J1.6 with PPK2 off, retaining the ground end on J1.1 and USB power,
then restoring output at setting 1875 mV. Physical VIO/CTRL3/current readings
are pending. Exact source and frames are in
[push-pull run 4](evidence/20261120-kicad-rev-a-push-pull-bench-4.jsonl).
No firmware/image change or flash occurred.

## CTRL3 push-pull HIGH observation and LOW command — 2026-11-20

With the external 10 kΩ load moved to CTRL3/J1.6-to-GND/J1.1, USB retained
and PPK2 output restored at setting 1875 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **1.869 V** |
| CTRL3 HIGH, J1 pin 6 | **1.827 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **690 µA** |

All four channels have the same reported loaded HIGH voltage/current at
their recorded supply points. The same bench session then acknowledged the
actively driven LOW state:

```json
{"cmd":"set_control_state","channel":"CTRL3","state":"idle"}
{"ok":true,"timestamp_us":1302716769}
```

Physical LOW/VIO/fresh-current readings remain pending with unchanged wiring.
The selected output stays enabled in LOW. No session close, firmware/image
change, flash or full acceptance occurred.

## Four low-voltage push-pull pairs, closed epochs and representative range setup — 2026-11-20

The operator supplied CTRL3 LOW=**0.0 V** at DUT_VIO=**1.833 V**, with fresh
probes-removed current=**415 µA**. Consolidated static observations are:

| Channel | J1 pin | HIGH VIO | HIGH output | HIGH current | LOW VIO | LOW output | LOW current |
|---|---|---|---|---|---|---|---|
| CTRL0 | 3 | **1.866 V** | **1.827 V** | **690 µA** | **1.833 V** | **0.0 V** | **416 µA** |
| CTRL1 | 4 | **1.867 V** | **1.827 V** | **690 µA** | **1.833 V** | **0.0 V** | **415 µA** |
| CTRL2 | 5 | **1.867 V** | **1.827 V** | **690 µA** | **1.833 V** | **0.0 V** | **415 µA** |
| CTRL3 | 6 | **1.869 V** | **1.827 V** | **690 µA** | **1.833 V** | **0.0 V** | **415 µA** |

Method: one selected control per fresh USB epoch, normal `gp28safe-1`,
push-pull active high/idle low, nominal external 10 kΩ signal-to-ground load,
Pico USB connected, DUT absent, PPK2 setting 1875 mV, Fluke 115 DC voltages
relative to J1.1 and fresh 10-second probes-removed current averages. These
complete the four static HIGH/LOW pairs at the recorded supply/load points,
without establishing a separate pull-up-loaded LOW test, all-voltage/load/
temperature behavior, calibrated leakage, transients, v2 service/HIL or full
manufactured-board acceptance.

Session 48715 closed normally with DTR low/port released; no serial owner
or TCP 2040 listener was found before reopening. All four frozen logs verify
exact hello identity, archived source hashes, correct per-channel configuration
and active/idle command sequence, 12 total successful responses and final
close records. Run 4 has 354 JSON records; its SHA-256 is
`264a70a7030eee2b41f30015f1b9cc4893f34d1420e6e6c0020b447a36d5b7ca`.
[The machine-readable summary](evidence/20261120-kicad-rev-a-push-pull-low-voltage-summary.json)
preserves all measurements, scope, source/log hashes and closed-epoch checks.

The historical representative CTRL0 2.5/3.3/5.0 V procedure is used as a
reference for fresh current-board range observations, without transferring
historical acceptance or introducing an all-channel characterization matrix.
Fresh session 41713 reverified the same normal hello and serial, then ACKed:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL0","mode":"push_pull","active_level":"high","idle_level":"low"}
{"ok":true,"timestamp_us":1503803687}
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":1503813683}
```

CTRL0 is held HIGH pending movement of the 10 kΩ load signal end from J1.6
to J1.3 with PPK2 off, retaining its ground end at J1.1 and Pico USB power.
Initial source setting **2575 mV** is an estimate for an approximately 2.5 V
board point; actual VIO must be measured independently. Exact source and
frames are in [run 5](evidence/20261120-kicad-rev-a-push-pull-bench-5.jsonl).
No higher-voltage control result, firmware/image change or flash occurred.

## CTRL0 push-pull HIGH at actual VIO 2.55 V and LOW command — 2026-11-20

With the 10 kΩ ground load moved back to CTRL0/J1.3, Pico USB retained,
no DUT and the requested source setting increased to 2575 mV, the operator
supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **2.55 V** |
| CTRL0 HIGH, J1 pin 3 | **2.50 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **900 µA** |

The actual rail is recorded as 2.55 V, not relabelled as exactly 2.50 V from
either the target or output reading. The 50 mV rail-to-output difference
is consistent with the nominal 10 kΩ load current of about 250 µA and
approximately 45 mV drop across nominal 180 Ω series resistance. This is
circuit consistency, not independent component characterization or complete
voltage-range acceptance. The same bench session then commanded LOW:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":1702668179}
```

Physical LOW/VIO/fresh-current readings remain pending at unchanged wiring
and source setting. No session close, firmware/image change or flash occurred.

## CTRL0 LOW at actual VIO 2.56 V and ~3.3 V setup — 2026-11-20

With the same 10 kΩ CTRL0-to-GND load, USB connected and PPK2 setting
2575 mV, the operator supplied:

| LOW-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **2.56 V** |
| CTRL0 LOW, J1 pin 3 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **665 µA** |

Together with the prior HIGH=2.50 V at VIO=2.55 V/current=900 µA, these
record the static CTRL0 pair at these measured supply/load points, without
relabelling either rail as an exact 2.500 V endpoint or establishing full
range/load/temperature acceptance.

The same session then acknowledged HIGH again:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":1841642752}
```

The next procedural point retains wiring/USB and uses initial source setting
**3325 mV** for approximately 3.3 V, with output off before changing the
setting and actual VIO measured independently. This is a starting estimate,
not calibrated compensation or an exact requested board voltage. No ~3.3 V
control result, session close, firmware/image change or flash occurred here.

## CTRL0 push-pull HIGH at actual VIO 3.31 V and LOW command — 2026-11-20

With the same 10 kΩ CTRL0/J1.3-to-GND load, USB connected, no DUT and
the requested source setting increased to 3325 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **3.31 V** |
| CTRL0 HIGH, J1 pin 3 | **3.24 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **1.14 mA** |

Actual rail/output values and the supplied mA current unit are preserved.
The 70 mV rail-to-output difference is consistent with a nominal 324 µA
ground-load current, about 58 mV of nominal 180 Ω series drop and a small
buffer/trace contribution. No exact component characterization or complete
range acceptance is inferred. The same session then commanded LOW:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":2007533315}
```

Physical LOW/VIO/current readings remain pending at unchanged wiring and
source setting. No session close, firmware/image change or flash occurred.

## CTRL0 LOW at actual VIO 3.31 V and upper-voltage setup — 2026-11-20

With the same 10 kΩ CTRL0-to-GND load, USB connected and PPK2 setting
3325 mV, the operator supplied:

| LOW-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **3.31 V** |
| CTRL0 LOW, J1 pin 3 | **0.0 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **832 µA** |

Together with the prior HIGH=3.24 V/current=1.14 mA at the same reported
VIO, these record the representative static CTRL0 pair at this supply/load
point. The same session then acknowledged HIGH again:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":2140612932}
```

The upper-voltage procedure retains the ground load and USB, with no DUT.
Disable PPK2 output before selecting its documented maximum **5000 mV**,
then enable and record actual VIO, CTRL0 HIGH, helper 3V3 and fresh current.
Do not increase the source above 5.0 V to compensate for measured voltage
drop; a maximum source setting alone does not establish an actual 5.000 V
endpoint. No upper-voltage control result or full range acceptance is inferred.

The operator also confirmed a Zephyr DUT fixture or spare Pico is available
for later UART checks; no connection, identity, fixture firmware or UART
functionality is established by availability alone. No UART payload, session
close, firmware/image change or flash occurred here.

## CTRL0 push-pull HIGH at actual VIO 4.94 V and LOW command — 2026-11-20

With the same 10 kΩ CTRL0/J1.3-to-GND load, USB connected, no DUT and
PPK2 set to its maximum 5000 mV, the operator supplied:

| HIGH-state measurement | Reported result |
|---|---|
| Actual DUT_VIO | **4.94 V** |
| CTRL0 HIGH, J1 pin 3 | **4.84 V** |
| Pico 3V3, physical pin 36 | **3.277 V** |
| Fresh PPK2 average over 10 seconds, probes removed | **1.73 mA** |

The 100 mV rail-to-output difference is consistent with nominal 484 µA
ground-load current, about 87 mV across the nominal 180 Ω series path and
a small buffer/trace contribution. Helper 3V3 remains at the prior reported
value. This is an upper-voltage observation at actual 4.94 V, not an exact
5.000 V endpoint or complete range/load/temperature acceptance.

The same session acknowledged LOW:

```json
{"cmd":"set_control_state","channel":"CTRL0","state":"idle"}
{"ok":true,"timestamp_us":2428682667}
```

Physical LOW/VIO/current readings remain pending at unchanged load and
5000 mV source setting. DUT/fixture remains disconnected. No UART payload,
session close, firmware/image change or flash occurred here.

## Final representative push-pull LOW and closed range epoch — 2026-11-20

The operator supplied CTRL0 LOW=**0.0 V** at actual VIO=**4.95 V**, fresh
probes-removed current=**1.20 mA**, at the unchanged 5000 mV source setting.
Consolidated representative range observations under the 10 kΩ ground load:

| Source setting | HIGH VIO | HIGH output | HIGH current | LOW VIO | LOW output | LOW current |
|---|---|---|---|---|---|---|
| 2575 mV | **2.55 V** | **2.50 V** | **900 µA** | **2.56 V** | **0.0 V** | **665 µA** |
| 3325 mV | **3.31 V** | **3.24 V** | **1.14 mA** | **3.31 V** | **0.0 V** | **832 µA** |
| 5000 mV | **4.94 V** | **4.84 V** | **1.73 mA** | **4.95 V** | **0.0 V** | **1.20 mA** |

These complete the representative static pairs at the recorded actual
supply/load points. Exact target endpoints, pull-up-loaded push-pull LOW,
all-channel voltage/load/temperature coverage, calibrated leakage, transients
and full manufactured-board acceptance are not established. Helper 3V3 at the
upper HIGH point was 3.277 V, as recorded above.

Session 41713 closed normally, DTR deasserted and port released; no serial
owner or TCP 2040 listener remained. Frozen range log verifies 1,073 valid JSON
records, exact source hash, seven command/reply pairs in order and final close.
SHA-256: `4b6de4a3641f71c9cb2f898eb5bc028b5192e2c4ac9d11b458cf70dfb09bb71b`.
[The range summary](evidence/20261120-kicad-rev-a-push-pull-range-summary.json)
contains measurements, limits and hashes. No firmware/image change or flash.

## UART loopback fixture and first three bounded runs — 2026-11-20

The operator confirmed removal of the external control load and a direct
jumper between current-board J1.7/DUT_UART_TX and J1.8/DUT_UART_RX. Helper
USB stayed connected; DUT/spare Pico stayed disconnected. PPK2 VOUT remained
on J1.14 and GND on J1.1. Before each run, output was disabled for setting
change, then enabled and allowed to settle for 10 seconds. The Fluke preflight
voltage was reported before UART transmission, not measured continuously.

The temporary bounded UART script was syntax checked and confirmed source/
protocol mapping before execution. Each fresh exclusive epoch verifies known
serial FA63A4D787572B33 and the exact normal `gp28safe-1` hello/capabilities,
captures baseline status, sends only two `uart_send` commands and compares
the decoded RX stream byte-for-byte. Payloads are a 33-byte point-labelled
`DUTCHMATE_LOOPBACK_<POINT>_460800_A5` line including LF and all 256 binary byte
values 0x00–0xFF. Command acceptance length, exact echo, extra-byte absence,
post-send zero occupancy and zero reported drops/overflows are checked.
The fixed DUT UART is configured at 460800 baud/8N1; the host CDC baud argument
115200 is not the DUT UART baud. No control commands or DUT actions are sent.

| Label | PPK2 setting | Operator preflight VIO | Text echo | Binary echo | Reported drops/overflows | Final RX occupancy |
|---|---|---|---|---|---|---|
| 1V8 | 1875 mV | **1.858 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |
| 2V5 | 2575 mV | **2.53 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |
| 3V3 | 3325 mV | **3.28 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |

Every run closed normally with DTR deasserted and port released. Logs archive
exact script source/hash, operator preflight voltage, source setting, command
bytes, raw/parsed frames, device timestamps and match results:

- [1V8 log](evidence/20261120-kicad-rev-a-uart-loopback-1v8.jsonl).
- [2V5 log](evidence/20261120-kicad-rev-a-uart-loopback-2v5.jsonl).
- [3V3 log](evidence/20261120-kicad-rev-a-uart-loopback-3v3.jsonl).

First-run raw-frame reconstruction independently verified both payloads,
command bytes/accepted lengths, archived source hash and close record: 303
JSON records, SHA-256
`a54cd0b87a1ca2ff2d30885ac7789cc527fadcd9d3b90845a3282eb8d6494526`.
Boot-cumulative RX high-water was 256 bytes after each run; it is not a
separately reset per-run measurement.

These are bounded direct functional loopbacks at operator preflight voltages.
They do not establish oscilloscope signal integrity, independently verified
absolute baud accuracy, external-DUT clock interoperability, cable/load margins,
sustained stress, v2 Device Core/HIL acceptance or full board acceptance. The
operator was asked for the upper preflight voltage at PPK2 setting 5000 mV,
keeping the jumper and no DUT; that run has not yet occurred here.

## Upper UART loopback and independently verified four-point results — 2026-11-20

The operator reported upper preflight VIO=**4.96 V** at PPK2 setting 5000 mV,
retaining the J1.7↔J1.8 jumper, helper USB and no DUT. A fresh exclusive
epoch reverified normal `gp28safe-1` and sent the same two bounded payloads:

- 33-byte text: exact echo, `bytes_accepted=33`, completion timestamp
  **3290414360 µs**.
- Binary values 0x00–0xFF: exact 256-byte echo, `bytes_accepted=256`, completion
  timestamp **3290663935 µs**.
- Final buffer status: zero occupancy, zero reported dropped bytes and zero
  overflow events; boot-cumulative high-water 256 bytes.
- DTR deasserted and port closed normally, with no serial owner or TCP 2040
  listener remaining.

Consolidated bounded loopback observations at configured 460800 baud/8N1:

| Label | PPK2 setting | Operator preflight VIO | Text echo | Binary echo | Reported drops/overflows | Final occupancy |
|---|---|---|---|---|---|---|
| 1V8 | 1875 mV | **1.858 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |
| 2V5 | 2575 mV | **2.53 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |
| 3V3 | 3325 mV | **3.28 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |
| 5V0 | 5000 mV | **4.96 V** | **33/33 exact** | **256/256 exact** | **0 / 0** | **0 bytes** |

All 1,156 echo bytes were independently reconstructed from the archived raw
frames and compared with transmitted command payloads, including point-labelled
text and all 256 binary values. Each log verifies the known serial/normal
hello, exact command bytes, accepted lengths, archived source hash, final
counters/occupancy and DTR-low/closed-port record. Each has 303 JSON records.
SHA-256 values:

- 1V8: `a54cd0b87a1ca2ff2d30885ac7789cc527fadcd9d3b90845a3282eb8d6494526`.
- 2V5: `18654175265eae4c007e58278f27029e1b34509093667bd90d67738d1ab4abf7`.
- 3V3: `f3f7eca46488a9ef86a3acdfc0d8d83d0a0d1b459554f05eec0f3b33d1b949fd`.
- 5V0: `463ca71c42620a563b7278723607df27c2882a5ae3fdce2f66bdefba93c008d2`.

[The aggregate UART summary](evidence/20261120-kicad-rev-a-uart-loopback-summary.json)
preserves individual results, counters, timestamps and source/log hashes.
Voltages are operator preflight readings rather than continuously recorded
rails. These results do not establish exact nominal endpoints, waveform/
absolute baud accuracy, external-DUT clock interoperability, cable/load margin,
sustained stress, v2 Device Core/HIL or complete board acceptance.

## Existing Zephyr fixture selected; four-wire setup pending — 2026-11-20

The operator selected the existing, already-flashed Zephyr DUT fixture.
Repository documentation and retained Enhanced records identify the baseline
as Pico 1/Pico H (`rpi_pico`), with UART0 TX GP0/physical 1, RX GP1/physical 2,
GND physical 3 and 3V3 physical 36. Basic firmware defaults to 115200 baud;
the accepted Enhanced fixture uses the opt-in 460800 overlay. No live fixture
build identity or baud is yet inferred from the operator's availability report.

Prepared wiring, requiring both USB supplies disconnected and PPK2 output off
while changing connections:

| DUT fixture Pico pin | Helper connector |
|---|---|
| GP0 TX, physical 1 | J1.7 / DUT_UART_TX |
| GP1 RX, physical 2 | J1.8 / DUT_UART_RX |
| GND, physical 3 | J1.1 / GND |
| DUT 3V3 OUT, physical 36 | J1.14 / DUT_VIO |

Remove PPK2 VOUT from J1.14 before attaching the DUT rail, and remove the
J1.7↔8 loopback jumper. PPK2 stays off/disconnected from VIO; the DUT's own
USB-regulated 3V3 supplies the interface reference. This does not connect the
two Pico 3V3 outputs together. Leave helper controls J1.3–6 and fixture mode
straps GP2/GP3 (physical 4/5) unconnected for the initial normal-boot UART
check. After wiring, reconnect helper USB only; fixture USB remains off until
the host is ready to capture boot bytes. Wiring confirmation, passive boot
capture and live INFO identity remain pending. No reflash or DUT command
was performed during this preparation.

## CTRL0 reset chosen for real-DUT boot capture — 2026-11-20

The operator confirmed the prepared four-wire fixture setup, then asked why
CTRL0 could not reset the DUT for the boot message. It can: the documented
fixture RUN/physical pin 30 is active low and must be driven through released
open-drain control. The preceding separate power-on capture was a setup choice,
not a technical restriction. No powered-DUT capture had yet been performed.

Prepared additional fixture connections, pending confirmation:

- Helper CTRL0/J1.3 to fixture RUN/physical pin 30.
- Temporary external 10 kΩ pull-up from helper J1.14 (DUT-supplied 3V3/VIO)
  to J1.3. This provides a defined reset pull-up/test load; it is not board
  rework or a newly discovered design correction.
- Retain the confirmed UART, common ground and DUT-3V3-to-VIO connections.
  PPK2 stays off with VOUT physically removed. Fixture USB stays disconnected
  while adding wiring; helper USB may remain connected with no active epoch.
  Leave fixture GP2/GP3 mode straps open for normal boot.

After wiring confirmation, the prepared host sequence configures only CTRL0
open-drain active-low and holds it asserted while arming UART capture. The
operator then powers the fixture by USB; its regulator supplies the VIO domain
while RUN remains low. Releasing CTRL0 lets the powered fixture boot without
requiring repeated USB unplugging. Actual held/reset levels and decoded boot/
INFO will establish the physical result and fixture identity/baud.

The temporary reset/UART bench script was syntax checked. It archives exact
source and raw frames when run, logs complete decoded UART lines without
discarding raw data, allows INFO/PING only after a fixture BOOT OK marker has
been observed, and uses existing GPIO/protocol operations. Close/error or a
30-minute deadline deasserts DTR to request safe high impedance. No serial
port, reset assertion, DUT payload, physical reset measurement, new firmware
or flash occurred in this preparation.

## Real-DUT reset wiring confirmed and capture armed — 2026-11-20

The operator confirmed reset wiring ready with DUT USB still disconnected:
CTRL0/J1.3 to fixture RUN/physical pin 30, temporary 10 kΩ J1.14-to-J1.3
pull-up, retained four-wire UART/reference connections, helper USB connected
and PPK2 VOUT removed. Known helper serial FA63A4D787572B33 enumerated at
`/dev/cu.usbmodem11401`; no serial owner or TCP 2040 listener found before open.
The temporary reset bench script passed syntax check before execution.

Exclusive session 27438 asserted DTR, reverified normal `gp28safe-1`, protocol
v1/device/capabilities and acknowledged:

```json
{"cmd":"configure_gpio_mode","channel":"CTRL0","mode":"open_drain","active_level":"low"}
{"ok":true,"timestamp_us":4733203787}
{"cmd":"set_control_state","channel":"CTRL0","state":"active"}
{"ok":true,"timestamp_us":4733213885}
```

The host now captures UART with CTRL0 commanded LOW, awaiting DUT USB power
and physical DUT_VIO/RUN readings. The ACK alone does not establish the held
reset level. No fixture boot/INFO identity or 460800 compatibility is yet
verified; no UART payload is sent before an observed valid fixture boot marker.
Exact script source/hash, command bytes, raw frames and decoded lines are
archived in [the reset bench log](evidence/20261120-kicad-rev-a-dut-reset-bench.jsonl).
Session remains open. No measured reset result, firmware/image change or
flash occurred here.

## Real-DUT held reset, boot identity, UART exchange and controlled pulse — 2026-11-20

The operator connected fixture USB with CTRL0 commanded active and reported
actual DUT_VIO/J1.14=**3.3 V**, fixture RUN/physical pin 30=**0.0 V**. This
is the first measured held reset on the real fixture at this supply point.
The external 10 kΩ reset pull-up and all UART/reference wiring were retained;
PPK2 remained off with VOUT removed.

Bench session 27438 released CTRL0 and received `ok=true` at **4942969157 µs**.
The captured 62-byte boot banner was exactly:

```text
DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001
```

With fixture identity observed, the guarded bench sent `INFO\n`, then `PING\n`,
commanded one `pulse_control` on CTRL0 for 250 ms, and sent another `PING\n`
after the second boot. Helper command results:

| Command | Helper response timestamp_us | Accepted UART bytes |
|---|---|---|
| `uart_send` INFO LF | **5056826230** | **5** |
| `uart_send` PING LF | **5060521048** | **5** |
| `pulse_control` CTRL0, 250 ms | **5066295592** | Not a UART send |
| `uart_send` PING LF after reset | **5298505819** | **5** |

All responses were `ok=true`. Raw UART reconstruction verified exactly
216 bytes, in this order with LF terminating every line:

```text
DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001
DMF/1 INFO board=rpi_pico build=phase1-enhanced-460800-001 protocol=1
DMF/1 PONG
DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001
DMF/1 PONG
```

No other UART bytes preceded or appeared between these lines. Latest status
at helper timestamp **5299557429 µs** reports zero occupancy, zero dropped
bytes and zero overflow events; boot-cumulative high-water remains 256 bytes.
This establishes readable real-fixture UART at the helper's configured
460800 baud and the expected fixture build identity, plus reset-triggered
boot reacquisition and post-reset response without USB power cycling.

The pulse's 250 ms is the commanded duration, not an oscilloscope-measured
physical waveform. The original held RUN voltage is retained at the operator's
reported precision. Released RUN voltage was requested and is pending while
the same epoch remains open with CTRL0 released. This direct bench record
does not establish v2 Device Core workflow/HIL acceptance, timing margins,
analog signal integrity or full board acceptance. No firmware/image change
or flash occurred.

## Released RUN reading, closed epoch and later boot banners — 2026-11-20

The operator reported released RUN/fixture physical pin 30=**3.277 V**.
Together with held RUN=0.0 V at VIO=3.3 V, this records the reported static
reset levels. Session 27438 then closed normally, DTR deasserted and port
released; no serial owner or TCP 2040 listener remained.

The final capture includes additional UART received after the earlier verified
216-byte snapshot. The initial expected sequence remains exact, followed by
**ten additional exact 62-byte BOOT OK banners**, giving **836 UART bytes**
and **12 total boot banners**. These additional banners occurred between
**18:31:54.352670 and 18:32:00.506386 Europe/Paris** (17:31:54–17:32:00 UTC).
Intervals between the additional banners range from approximately 37 ms to
2.23 seconds; no source cause is inferred from that pattern alone.

The complete host command log has seven acknowledged commands: configure
CTRL0, hold, release, INFO, PING, one commanded 250 ms reset, then PING.
The single pulse was sent at 18:25:19 Paris time; the final PING at 18:29:11.
No further helper reset command appears before the additional boot banners.
Latest status remains zero occupancy, zero reported dropped bytes and zero
overflow events. This is not transport-loss evidence; the cause/context of
the additional boot banners remains unassigned.

The operator was asked whether deliberate reset/power actions or possible
RUN probe/wire contact occurred while measuring the released level. No
automatic-reset, probe-contact, board-defect or firmware diagnosis is made
before that context/reproduction. The expected reset/UART exercise is retained,
but no unattended-stability or overall hardware acceptance is claimed.

The frozen log verifies archived source hash, all command bytes and seven
successful replies, the entire exact UART trace and final closed-port record.
It contains 862 JSON records; SHA-256:
`c8dc068bc87896d60f2c5fa9b004ee312aaf4fdb1bf045f528f1af20369024df`.
[The observation summary](evidence/20261120-kicad-rev-a-dut-reset-observations.json)
preserves the earlier exercise, later banners/timestamps, static readings,
counter state and pending operator context. No subsequent actuation,
firmware/image change or flash occurred in this close/inspection step.

## Possible RUN probe contact and hands-off recurrence-check preparation — 2026-11-20

The operator replied to the additional-boot question: **“Probe or wiring
contact may have disturbed RUN.”** This is evidence of possible measurement
interaction, not a confirmed cause. The original raw log and earlier pending-
context observation file remain unchanged; the later statement is preserved
in [a separate context note](evidence/20261120-kicad-rev-a-reset-probe-context.json).

Prepared repeat keeps the actual fixture, both USB supplies, UART/reset
wiring and external 10 kΩ pull-up unchanged, with PPK2 off/VOUT removed.
After confirmation that both meter probes are removed and the setup will
remain untouched, a fresh exclusive epoch will configure CTRL0 open-drain
idle, collect a short baseline, issue one 250 ms reset and observe 30 seconds
after the expected boot without further commands or DUT UART payloads.
Raw bytes, command/reply trace and all banners will be retained; close/error
deasserts DTR. The temporary script passed syntax inspection and its expected
boot marker was verified as 62 bytes terminated by LF.

No recurrence during this short interval would not prove probe causality,
absence of transient glitches or long-term stability. Readiness confirmation
and actual repeat result remain pending. No new port open, actuation,
firmware/image change or flash occurred in this preparation.


## Probes-off reset and 30-second quiet observation — 2026-11-20

The operator confirmed both meter probes removed and the setup untouched,
with both USB supplies connected, UART/RUN wiring and the external 10 kΩ
pull-up unchanged, PPK2 off and VOUT disconnected. A fresh exclusive helper
epoch configured only CTRL0 open-drain active-low at idle, collected a short
baseline, then commanded exactly one 250 ms reset pulse. No UART send or
further control command occurred during the observation.

Baseline contained zero UART bytes. Reset produced exactly the expected
62-byte `phase1-enhanced-460800-001` BOOT OK line; the following **30.051448 s**
contained **zero UART bytes and zero additional boot banners**. Both helper
commands acknowledged successfully. Final telemetry reports zero occupancy,
zero dropped bytes and zero overflow events; high-water remains the existing
boot-cumulative 256 bytes. DTR was deasserted and the port closed normally.

Archived source hash, command bytes/replies, exact UART trace and close were
verified. [Raw log](evidence/20261120-kicad-rev-a-dut-hands-off-bench.jsonl)
contains 45 JSON records, SHA-256
`e1be5977024afdd2e7dc27bd0aca59dbaa5788100023537322c3826a31e230a6`.
[Result and provenance](evidence/20261120-kicad-rev-a-dut-hands-off-result.json)
retain source SHA-256
`9a82836656beb9cc93b1d4db24c5565739217786d929f2fd771cfbfbcdaa5c73`.

The earlier extra boots did not recur during this bounded hands-off interval.
Possible probe/contact disturbance remains plausible, not causally proven.
This does not establish long-term stability, reset waveform timing or full
manufactured-board acceptance. No firmware/image change or flash occurred.


## Device Core functional, stream and ownership checks — 2026-11-20

Fresh pre-start software gate: 1,877 pytest tests passed in 49.22 s, Ruff
passed, mypy passed for 103 files, offline lock check passed/66 packages and
`git diff --check` passed. No tests ran while the physical service owned USB.
Code HEAD was `9914d6298479b116c4b797e6cf4cfdb1e4788ec0`, with the uncommitted
GP28 fix, documentation and operator-owned CAD edits; this is a dirty working
baseline, not a committed release. No source, firmware or fixture change occurred
in this functional interval. The old fixture is `rpi_pico`, build
`phase1-enhanced-460800-001`; retained Zephyr 4.4.0/SDK 1.0.1 provenance and
artifact hashes are recorded, not represented as a physical flash readback.

An isolated configuration declared 3.3 V, Enhanced 460800 8-N-1, no flow
control, explicit TX enable, exact helper port, unchanged 5.0 s reconnect
policy and CTRL0/RUN open-drain active-low. Only reset was mapped; boot straps
were open. PPK2 was off/VOUT removed; both USB supplies were connected and
meter probes removed. Known helper serial `FA63A4D787572B33` and live
`gp28safe-1` hello/status matched. Sole service PID was 6107, session
`20261120T175235Z-2809c3f3`. Profile digest:
`006e4c4988c8b26c5f35fb62e004ea42d30e0e9196263e785d4fd8dd3132e4dc`.

| Check | Result and scope |
|---|---|
| Audited reset and INFO | One 250 ms commanded pulse; exact expected BOOT and fixture INFO. First BOOT overlaps the following INFO operation; later reacquire reset below proves ambient boot before Interact. |
| Monitor | 0.3 s elapsed, unmatched literal/0.3 s timeout, and PONG matched after one standalone audited send. |
| Interact | INFO/PING matched, PING/0.3 s elapsed, PARTIAL/unmatched literal timeout; exact payloads/acceptance retained. |
| CLI follow and console | Actual follow displayed complete split PARTIAL; SIGINT detached. Actual console sent one LF PING/displayed PONG; detach left recording active and later INFO matched. |
| Binary UART | Exact `DMF/1 BINARY ` followed by bytes `f0 28 8c 28 ff fe 0a` retained. |
| DELAYFAULT | One exact audited send accepted 11 bytes, fixture returned `E_COMMAND_001`, Interact timed out. Existing fixture predates this command, as historical source `203649f` and Enhanced HIL record confirm. No retry/flash; scheduled delayed-fault behavior unavailable in this fixture. |
| Maximum-speed BURST | Expected 43,081 bytes; retained 17,832 plus 25,249 explicitly dropped in seven overflow episodes reconciles exactly. END/checksum survives. This is the existing deliberate-overflow profile, not a lossless-throughput claim. |
| SUSTAIN | Exactly 94,299 bytes: BEGIN, all 4,096 ordered sequence lines and END/checksum 8,386,560. SHA-256 matches historical deterministic payload, with no additional reported drops. |
| Release/external/reacquire | Intentional gap recorded; external exclusive serial open verified known hello while service remained released, then DTR low/closed before reacquire. Same session, fresh segment 1, reset mapping re-applied. |
| Post-reacquire ambient boot | Reset attempt/result 14026/14027, exact BOOT RX 14028–14031 before INFO operation 14032. INFO then matched; recording stayed continuous while connected. |
| Retrieval/shutdown | CLI status/list/detail/logs exercised. Graceful stop completed session as `completed/service_shutdown`; PID, TCP 2040 and serial ownership absent afterward. |

The initial temporary harness incorrectly expected BURST to be lossless and
stopped after a byte comparison. Its original source, failed assertion and
bytes remain archived. Review of the prescribed deliberate-overflow criterion
corrected the interpretation; BURST was not resent and no acceptance criterion
was changed. The earlier DELAYFAULT timeout is likewise preserved, not hidden
by the continuation. SUSTAIN was sent once as a separate supported-rate check.

Independent native-journal audit reconciled **112,614 raw bytes** to every RX
record/offset, **14,067 contiguous evidence records**, 13 UART attempt/result
pairs, four control attempt/result pairs, 13 terminal operations and two
RP2350 timestamp segments with one explicit gap. Final integrity truthfully
remains `loss_reported`, scope `debug_helper_rx_buffer`, **25,249 dropped bytes**
from BURST; successful later SUSTAIN does not clear that history. Its exact
payload SHA-256 is
`efd834a49a58d2658dd2e4ca509fbdd677894242740b4c3391b5c2559eb8f4f8`.
All 843 pre-existing `.dutchmate` files hashed before this run remain unchanged.

[Machine summary](evidence/20261120-kicad-rev-a-device-core-summary.json) and
[closed evidence archive](evidence/20261120-kicad-rev-a-device-core-evidence.tar.gz)
retain configuration, native session, exact API/CLI traces, executed script
sources, failed harness outcomes, build provenance and file manifest. Archive
SHA-256: `e5334d5a1454ea6b047bb46718641f7c2c6053381bf7191913a4b540487ba9a4`;
571,877 bytes, 20 member hashes independently verified. Original local working
records remain in `.dutchmate/hil/kicad-rev-a-20261120/`.

The operator reconfirmed no oscilloscope or logic analyzer is available today.
This record adds manufactured-board functional evidence; it does not close
UART waveform/signal-integrity, loaded debugger-rail isolation, remaining
physical sequencing or full Phase 1B acceptance. Boot-role and unexpected
reconnect checks were not exercised in this interval.


## Boot-role wiring and unpowered selection — 2026-11-20

After the previous service closed, the operator disconnected both USB supplies,
added helper J1.4/CTRL1 to fixture GP2/physical4, retained UART/GND/VIO/RUN and
10 kΩ reset pull-up wiring, then reconnected helper USB only. DUT USB remained
disconnected; PPK2 stayed off/VOUT removed. This satisfies the fixture rule that
mode strap changes occur only unpowered or held reset.

A fresh isolated profile adds CTRL1 boot/GP2 push-pull active-high/idle-low to
the unchanged reset/UART settings. Profile digest:
`8e427e14e277bca0ab14695284e54e513e60402d81b12b519c7512108b5baf90`.
Known normal helper verified; sole service PID 6649, native session
`20261120T180241Z-21d9dc70`. With DUT still unpowered, actual CLI
`dut boot-mode bootloader` acknowledged at **7323047804 µs**, performed_at
**2026-11-20T18:02:56.067441Z**. Status commanded boot mode is bootloader;
this is command acceptance, not physical GP2 readback.

The operator was asked to connect DUT USB and leave the setup untouched.
Expected result is the fixture's synthetic `E_INIT_001` boot line, not a ROM
BOOTSEL drive. Power confirmation/capture remains pending at this snapshot.
The live service alone owns serial; source/build images remain unchanged.
Configuration, selection trace/status and pre-action cursor are retained under
`.dutchmate/hil/kicad-rev-a-boot-20261120/`.


## Boot-role alternate-mode response — 2026-11-20

The operator connected DUT USB and left the setup untouched. Continuous
session `20261120T180241Z-21d9dc70` captured exactly **81 bytes**:

```text
DMF/1 ERROR INIT code=E_INIT_001 board=rpi_pico build=phase1-enhanced-460800-001
```

CTRL1 boot-mode control attempt/result are evidence **20/21**; the complete
synthetic error is UART RX **79–84**, outside every bounded operation.
No extra UART byte was present in the retained pre-action-to-tail interval.
Status still commands bootloader, no active operation, zero reported drops.
Exact payload, pages/cursor and status are saved in
`.dutchmate/hil/kicad-rev-a-boot-20261120/bootloader-powered-capture.json`.
This is expected fixture test behavior, not an unexpected DUT fault or ROM
USB bootloader result. No firmware/image change or flash occurred.

The operator was asked to disconnect DUT USB, retaining helper USB and all
wiring, before the normal-mode GP2 change. No normal-mode command was issued
while awaiting that required unpowered-state confirmation.


## Boot-role normal return and reconnect observation preparation — 2026-11-20

The operator disconnected DUT USB while keeping helper USB/wiring unchanged.
With the DUT confirmed unpowered, actual CLI `dut boot-mode normal` ACKed
at **7449559678 µs**, performed_at **2026-11-20T18:05:02.581282Z**. The operator
then reconnected DUT USB without disturbing wiring. Continuous acquisition
captured exactly the expected **62-byte BOOT OK** line, and one LF INFO
Interact matched the exact fixture build/protocol; zero reported drops.
Both alternate and normal GP2 selections therefore occurred only while the
fixture was unpowered. No firmware/image change or flash occurred.

A bounded 180 s read-only HTTP/USB-metadata observer was armed with the same
live service/session and default **5.0 s** reconnect policy. The operator was
asked to unplug/replug helper USB only into the same Mac port, keeping DUT
USB/wiring unchanged and without BOOTSEL/reset. No competing serial reader
or second runtime was opened. Actual disconnect/reconnect result remains
pending in this preparation snapshot.


## Automatic reconnect, 250 ms pause and closed-session audit — 2026-11-20

The operator unplugged/reconnected only helper USB while DUT USB and all
wiring remained connected, without BOOTSEL/reset. The read-only observer saw
helper USB absent/reappearing and connection state reconnecting→connected.
Its first reconnecting-to-connected response interval was **4.518491 s**;
this is an observed response interval, not exact driver or USB-wire latency.
The unchanged policy was **5.0 s**. Device Core automatically continued in
session `20261120T180241Z-21d9dc70`, fresh RP2350 timestamp segment 1, with one
explicit observation gap. Both CTRL0/reset and CTRL1/boot configurations were
re-applied. Boot command status becoming unknown after disconnect does not
constitute GP2 electrical readback; no boot-mode state change was requested
on the powered fixture.

A subsequent audited 250 ms reset retained the exact **62-byte BOOT OK**
line before a new INFO Interact matched. Zero reported dropped bytes or
overflow events; no additional boot banners or reset command inferred.

For the buffer profile, one read-only condition Monitor was started before
one audited `SUSTAIN` send. Service PID 6649 was SIGSTOP/SIGCONT paused for
**255.072916 ms** (requested 250 ms), with resume guaranteed in the harness's
finally block. This measures a process-signal interval, not an independent USB
bus stall. The native journal ultimately retained the entire deterministic
**94,299-byte** output, all **4,096** ordered sequence lines and checksum
**8,386,560**. No reported drop/overflow occurred; high-water was **490 bytes**.

The initial harness expected Monitor to match its END condition within 20 s
and stopped on the returned timeout. Inspection showed the END line was
admitted **after** the durable operation terminal: terminal sequence **12345**,
END's final RX sequence **12512**. The source stream spans **8.606316 s** in
helper timestamps, while host recorded_at spans approximately **20 s**.
Thus the matcher timeout is consistent with its durable evidence window;
no matcher defect or physical UART loss is inferred. Downstream admission
lag is observed. Source inspection shows one v2 transaction per UART event;
that is a candidate cost, not a profiled causal diagnosis. The earlier no-
stall SUSTAIN also took **19.775641 s** for its Interact to match.

The original source/timeout/result remain archived. The 500 ms profile was
not run; no deadline, implementation, firmware or acceptance criterion was
changed to conceal the timing observation. The 250 ms byte-integrity/loss
result is retained separately from its bounded Monitor outcome.

The operator requested stopping here and continuing tomorrow. Service closed
gracefully as `completed/service_shutdown`, PID 6649 absent, serial and TCP
2040 released. Native audit verified **94,644 raw bytes**, **12,662 contiguous
evidence records**, seven successful control attempt/result pairs, three
successful UART attempt/result pairs, three terminal operations, two timestamp
segments and one gap. The entire raw stream equals, byte-for-byte: synthetic
E_INIT banner, normal BOOT, INFO, post-reconnect BOOT, INFO, SUSTAIN. Final
integrity is `none_reported` with zero dropped bytes, local recording complete.
All 843 pre-existing local files remain unchanged.

[Machine summary](evidence/20261120-kicad-rev-a-boot-reconnect-summary.json) and
[closed archive](evidence/20261120-kicad-rev-a-boot-reconnect-evidence.tar.gz)
retain actual selection/capture/API/CLI/observer traces, temporary harness
sources including the timeout, native journal, config, provenance and manifest.
Archive: **224,181 bytes**, SHA-256
`b9184d7407d37e52a4984f0ca62dc4d7220dfcb40362a28b908c05e14a93eb8f`;
all **20** member hashes independently verified. No product source change,
firmware rebuild/flash, commit or push occurred in these Nov-20 functional
checks. Scope/analyzer unavailable; UART waveform/signal-integrity, loaded
helper-rail isolation, remaining physical sequencing and full board/Phase 1B
acceptance remain unresolved.
