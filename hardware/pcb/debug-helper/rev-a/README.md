# Debug Helper Revision A — KiCad source

This directory contains the current authoritative Rev-A KiCad design source
for the DUTchMate Debug Helper. The historical EAGLE prototype design record
is preserved separately under [legacy-eagle](../legacy-eagle/revision_a.md).
Its component references and connector assignments do not define this KiCad
implementation.

## Design sources

- `dutchmate_debug_helper.kicad_pro`: KiCad project and check settings.
- `dutchmate_debug_helper.kicad_sch`: schematic and embedded symbol definitions.
- `dutchmate_debug_helper.kicad_pcb`: board source.
- `dutchmate_debug_helper.kicad_dru`: project design rules.
- `libraries/symbols/dutchmate.kicad_sym`: project-owned logic and analog-switch
  symbol definitions, resolved through `sym-lib-table` using `${KIPRJMOD}`.

The sources use KiCad 10 format. Standard KiCad symbols and footprints must be
installed alongside the project-owned library. Keep editable sources and any
reviewed manufacturing outputs in version control; local settings, locks,
autosaves, backups, and scratch exports are ignored.

## Electrical architecture and agreed corrections

The helper uses a non-wireless Raspberry Pi Pico 2 / RP2350 module (`A1`),
with a 3.3 V helper domain, a DUT-supplied `DUT_VIO` reference of 1.8–5.0 V,
and common ground. `DUT_VIO` supplies the interface circuitry; it is not an
output for powering the DUT.

| Block | KiCad implementation |
|---|---|
| Four control outputs | `U1 SN74LV4T125`, VCC=`DUT_VIO`; `U7/U8 SN74LVC2G06` open-drain enable drivers powered by `+3.3V` |
| Control data defaults | `R14–R17`, 10 kΩ to GND on `DBG_CTRL_DATA0–3` |
| Control enable defaults | `R1–R4`, 4.7 kΩ to GND; active-low `DBG_CTRL_OE0_N–3_N` pulled to `DUT_VIO` by `R7/R6/R9/R8`, respectively, each 4.7 kΩ |
| Four event inputs | `U5 TXU0104PWR`, VCCA=`DUT_VIO`, VCCB=`+3.3V`; `R5=4.7 kΩ` pulls `DBG_INPUT_IF_EN` low |
| UART | `U2 TXU0202DCUR`, VCCA=`+3.3V`, VCCB=`DUT_VIO`; `R12=4.7 kΩ` pulls `DBG_UART_IF_EN` low |
| Series resistance | `RN3/RN4=180 Ω` for control/event channels; `RN5=22 Ω` for UART |
| Protection | `U6` on connector-side controls, `U4` on connector-side events/UART, `D1` between `DUT_VIO` and GND |

The 4.7 kΩ enable pull-downs retain compatibility with older RP2350 A2
silicon; the design does not require A4-only modules. Control data pull-downs
define the buffer inputs while Pico GPIOs are undriven. The independent `/OE`
paths determine DUT-facing Hi-Z, including open-drain release. Push-pull and
open-drain control modes still require the appropriate firmware data/enable
sequence.

### Hardware-defined DUT_VIO sense isolation

`U3 TMUX2819DSGR` is connected as follows:

| Pin | Connection |
|---|---|
| 1, SA | `DUT_VIO` |
| 2, NC | GND, as specified by the datasheet |
| 3, EN; 8, VDD | `+3.3V`, with `C16=100 nF` between VDD and GND |
| 4, GND; 9, exposed pad | GND |
| 5, SB | Intentionally unconnected |
| 6, D | `R10` divider input |
| 7, SEL | GND |

With helper power present, EN high and SEL low select SA. With VDD absent,
the switch provides powered-off isolation within its specified leakage limits.
No firmware GPIO controls this isolation. The selected switch supports DUT
signals above its 3.3 V supply within the specified signal range. See the
[TMUX2819 datasheet](https://www.ti.com/lit/ds/symlink/tmux2819.pdf).

The divider remains `R10=47 kΩ` and `R11=47 kΩ`, with `C7=10 nF` from
`DUT_VIO_SENSE` to `GNDA`. `R11` also returns to `GNDA`, connected to the
Pico's AGND pin 33. `DUT_VIO_SENSE` reaches GP28/ADC2, module pin 34. The Pico
module supplies the internal analog/common-ground connection; these are
distinct carrier-board net names, not galvanically isolated domains.

GP28 ADC sensing is provisioned in hardware but is not implemented in the
current helper firmware: there is no ADC channel setup or digital-input-buffer
configuration for GP28. Any future sensing implementation must disable its
digital input buffer. Do not infer measured voltage monitoring from this
schematic or from the hardware-defined switch enable.

### UART receive bias

```text
J1.7 / DUT_UART_TX -- RN5A 22 Ω (pad 4 → pad 1) -- U2.B2 (pin 1)
                                                     |
                                                 R13 10 kΩ
                                                     |
                                                  DUT_VIO
```

`R13` is on the translator-input side of the series resistor, on exported net
`Net-(RN5A-R1.1)`. It references `DUT_VIO`, not fixed `+3.3V`. The translated
output is `DBG_UART_RX`, from U2 pin 4 to Pico GP1. The opposite direction is
Pico GP0 / `DBG_UART_TX` to U2 pin 5, U2 pin 8 through RN5B, then
`DUT_UART_RX` at J1 pin 8. Both UART directions share U2 OE; software TX
permission does not provide independent electrical TX isolation.

## DUT connector and interface requirements

The single 2×8 `J1` is the authoritative Rev-A DUT connector. Direct legacy
EAGLE harness compatibility is not required; any legacy connection requires
an external adapter cable.

| J1 pin(s) | Net(s) | Direction relative to helper |
|---|---|---|
| 1, 2 | GND | Common |
| 3, 4, 5, 6 | `DUT_CTRL0`, `DUT_CTRL1`, `DUT_CTRL2`, `DUT_CTRL3` | Outputs |
| 7 | `DUT_UART_TX` | Input from DUT TX |
| 8 | `DUT_UART_RX` | Output to DUT RX |
| 9, 10 | `DUT_EVENT2`, `DUT_EVENT3` | Inputs |
| 11, 12 | `DUT_EVENT0`, `DUT_EVENT1` | Inputs |
| 13 | GND | Common |
| 14 | `DUT_VIO` | Reference/supply input from DUT |
| 15, 16 | GND | Common |

`DUT_CTRL0–3` must remain within the `DUT_VIO` voltage domain. In particular,
a released externally pulled-up control signal must not be pulled above
`DUT_VIO`. U1 remains the selected SN74LV4T125. Control outputs drive logic
inputs, not DUT supply loads.

`DUT_EVENT0–3` intentionally have **no helper-side pull-ups**. These temporary
debugging inputs are normally driven by spare DUT GPIOs. The DUT/developer
must supply valid logic levels. Open-drain/open-collector outputs require a
DUT-side pull-up, including an MCU internal pull-up where its electrical and
timing performance is adequate. A floating event input is not a valid event
source.

## Validation lifecycle and evidence boundaries

The KiCad Rev-A schematic/source review is complete. PCB layout, routing,
fabrication preparation, DFM checks, Gerber review and manufacturing submission
are handled manually by the hardware designer outside the coding-agent
workflow. No further repository-driven PCB/DFM review task or acceptance gate
is planned before fabrication. Source-review completion does not establish
hardware acceptance, fabrication acceptance, production readiness or Phase 1B
acceptance.

Formal hardware validation of this corrected design begins only after
manufactured KiCad Rev-A PCBs are physically available. Each manufactured-board
validation campaign must record its own board/assembly configuration, wiring,
firmware, methods and observed results. Use the same broad categories as the
historical Rev-A work, adapted to this implementation, where applicable:

- Visual inspection, board assembly/continuity checks and firmware/board
  pin-mapping consistency.
- Power rails, `DUT_VIO` checks and operation across the supported voltage range.
- Debugger-powered/DUT-unpowered and DUT-powered/debugger-unpowered behavior,
  including powered-off back-power/leakage checks.
- `U3 TMUX2819` isolation of the `DUT_VIO` sense path and its divider/filter.
- Control-channel safe startup/Hi-Z, open-drain assertion/release and push-pull
  output levels.
- Event-input behavior with valid DUT-provided levels and any DUT-side pull-ups
  required for open-drain/open-collector signals.
- UART TX/RX functionality, the corrected after-RN5A `R13` pull-up, and UART
  signal-integrity/oscilloscope measurements.
- Hot-plug/unplug behavior and translator enable/disable sequencing.
- ESD/protection-path sanity checks where measurable, and Enhanced-backend HIL
  workflows relevant to the manufactured board.

These are future validation categories, not completed checks or new acceptance
criteria. Use applicable existing specifications and procedures for limits and
acceptance conditions; do not infer results or tolerances from source review.
The GP28 firmware limitation above and deferred EVENT capture must be respected
when defining what a physical run can demonstrate.

Adapt procedural references to the single 2×8 J1 pinout, current component/net
references and corrected circuit documented above. In particular, test the
after-RN5A `R13` pull-up at `U2.B2` to `DUT_VIO`; do not copy the historical
two-connector arrangement, historical R16 references or before-R16 rework
location into a KiCad-board procedure.

The three evidence scopes remain separate:

- Historical EAGLE [validation records](../../../validation/phase1_revision_a.md)
  establish evidence only for the actual EAGLE/as-built prototype, wiring,
  parts and firmware tested. They remain useful procedural/reference material.
  Their UART oscilloscope gap remains unresolved. The legacy board may still
  serve as a functional Enhanced HIL/development fixture under
  [Phase 1 specification §4.1](../../../../docs/phase1_implementation_spec.md#41-software-sequencing-and-hardware-acceptance-boundaries);
  such use does not establish electrical acceptance. Current-board UART
  electrical follow-up belongs to the manufactured KiCad campaign above.
- The completed KiCad source review establishes that the corrected design
  source was reviewed; it is not physical-board validation.
- Future manufactured KiCad Rev-A validation supplies separate physical
  evidence required for that board. Historical acceptance is not inherited.

Current progress and the next formal hardware-validation step belong in
[development status](../../../../docs/development_status.md); dated decisions
and source-check results belong in
[development history](../../../../docs/development_history.md).

## Provenance

No CERN-OHL-P-2.0 grant applies to this directory until every symbol,
footprint, model, template, imported asset, and manufacturing output has passed
the planned provenance audit. Do not copy embedded EAGLE libraries or
third-party CAD assets into this project without that audit.
