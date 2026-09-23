# DUTchMate Revision A Voltage-Domain GPIO and UART Interface

> Legacy EAGLE design record. The historical board and schematic sources are
> retained under `hardware/pcb/debug-helper/legacy-eagle/revision_a/eagle/`.
> The replacement KiCad design will live under
> `hardware/pcb/debug-helper/rev-a/` after its provenance audit.

**Revision:** 1.0<br>
**Date:** 2026-08-11<br>
**Scope:** Four debugger-to-DUT control signals, four DUT-to-debugger event signals, and one UART pair across different logic-voltage domains.

## 1. Purpose

DUTchMate uses a 3.3 V debugger MCU, while a connected device under test (DUT) may use a different digital-I/O voltage such as 1.8 V, 2.5 V, 3.3 V, or 5 V.

This document specifies the translated electrical interface of the Enhanced
DUTchMate Debug Helper backend. Generic USB-to-UART adapters are the Basic
backend and are outside this hardware design. DUTchMate software supports
user-selected TTL/logic-level adapters that appear as standard host serial
ports, but it does not detect or validate their electrical compatibility. The
user is responsible for compatible adapter and DUT TX/RX logic levels, correct
wiring, common ground, and any required voltage translation. RS-232-level
adapters must not be connected directly to DUT logic pins and require external
RS-232-to-logic-level translation.

The interface must allow the user to read the DUT schematic and configure DUTchMate appropriately. Automatic detection of DUT pin direction or electrical mode is not required.

The agreed simplified interface provides:

- Four fixed-direction control channels from DUTchMate to the DUT.
- Four fixed-direction event channels from the DUT to DUTchMate.
- One full-duplex UART interface with one channel in each direction.
- Per-channel `push_pull` or `open_drain` configuration, with a hardware
  high-impedance drive state available for safety and open-drain release.
- Capture of push-pull or open-drain DUT event outputs on the four event channels.
- A common ground between DUTchMate and the DUT.

Revision A physically provisions the `EVENTn` paths, but event-capture firmware,
host APIs, and the `gpio_events` capability are deferred to Phase 5. Their
presence in this electrical baseline does not make event observation a Phase 1
software feature.

## 2. System requirements

### 2.1 Debugger domain

- Debugger MCU I/O voltage: **3.3 V**.
- The debugger MCU controls all output modes in software.
- Debugger pins must default to a state that does not accidentally reset, boot, wake, or otherwise control the DUT during startup.

### 2.2 DUT domain

- Target DUT digital-I/O voltage: **1.8 V to 5.0 V** for the complete Revision A interface.
- The DUT must expose its I/O reference voltage as `DUT_VIO` on the DUTchMate connector.
- `DUT_VIO` is used as a translator reference/supply. It is not intended to power the DUT.
- The DUT and DUTchMate must share a common ground.

### 2.3 Supported signal types

The interface is intended for normal digital logic signals:

- Reset
- Boot or strap control
- Wakeup
- Power-enable or load-switch enable
- Interrupts
- Power-good signals
- Status and handshake signals
- UART TX and RX

It is not intended for:

- Analog signals
- Negative-voltage signals
- 12 V or 24 V industrial control signals
- Direct switching of a DUT power rail
- Galvanically isolated communication
- High-current loads

A control signal named `POWER` must drive a logic-level power-enable input or an external load switch. It must not directly source DUT power.

## 3. Selected architecture

| Interface block | Quantity | Selected IC | Direction |
|---|---:|---|---|
| Control GPIO translator | 1 | `SN74LV4T125PWR` | Debugger to DUT |
| Control enable driver | 2 | `SN74LVC2G06DBVR` | MCU enable to active-low buffer `/OE` |
| Event GPIO translator | 1 | `TXU0104PWR` | DUT to debugger |
| UART translator | 1 | `TXU0202DCUR` | One channel in each direction |

These exact orderable MPNs are the Phase 1 Revision A provisional logic BOM.
They are frozen for schematic capture and prototype assembly. Replacing one
requires an electrical review and a new hardware revision; package-compatible
or same-family substitutions are not automatic.

```text
                              DUTchMate
                         Debugger MCU, 3.3 V
                                  |
            +---------------------+---------------------+
            |                     |                     |
      4 x CTRL_DATA         4 x EVENT_IN          UART TX / RX
      4 x CTRL_EN                 |                     |
            |                     |                     |
   +----------------+    +----------------+    +----------------+
   | SN74LV4T125    |    | TXU0104       |    | TXU0202       |
   | VCC = DUT_VIO  |    | A = DUT_VIO   |    | A = 3.3 V     |
   |                |    | B = 3.3 V     |    | B = DUT_VIO   |
   +-------+--------+    +--------^-------+    +-------+--------+
           |                      |                    |
     CTRL_OUT[0:3]          EVENT_IN[0:3]        DUT UART RX/TX
           |                      |                    |
           +----------------------+--------------------+
                              DUT connector
```

This architecture intentionally uses fixed-direction paths. It avoids automatic-direction translators and avoids the complexity of providing independent drive and sense paths on every external GPIO.

### 3.1 Net naming and hardware-to-software mapping

The prototype schematic uses three naming layers:

| Layer | Example nets | Meaning |
|---|---|---|
| Connector side | `DUT_CTRL0`, `DUT_EVENT0`, `DUT_UART_TX` | External DUT header nets, protected by ESD parts. |
| Translator side | `CTRL0`, `EVENT0`, `UART_TX` | Internal nets after the series-resistor arrays. |
| Debugger side | `DBG_CTRL_DATA0`, `DBG_EVENT0`, `DBG_UART_RX` | Raspberry Pi Pico 2 / 3.3 V domain nets. |

The software-facing channel names remain `CTRL0` through `CTRL3` and `EVENT0`
through `EVENT3`. In the schematic these channel names correspond to the
internal translator-side nets, while the connector pins use the explicit
`DUT_*` prefix.

The hardware exposes generic physical channels. Software assigns meaning to
those channels using user configuration. The user is responsible for mapping
physical DUTchMate channels to the DUT schematic signals they actually wired.

| Hardware concept | Software concept | Meaning |
|---|---|---|
| `CTRL0` to `CTRL3` | Control channel or line | Physical DUTchMate-to-DUT output channels, exposed on connector nets `DUT_CTRL0` through `DUT_CTRL3`. |
| Control role | `reset`, `boot`, `wake`, `power_enable`, or another configured role | The workflow meaning DUTchMate should assign to that channel. |
| DUT signal name | `RESET_N`, `BOOT0`, `WAKE`, `PGOOD`, or another schematic name | The exact net or pin name from the user's DUT schematic. |
| Configured control mode | `open_drain` or `push_pull` | The Phase 1 behavior authorized for the assigned control channel. |
| Control drive state | high impedance, driven low, or driven high | The instantaneous electrical output state selected by firmware within the configured mode and safety rules. |
| `EVENT0` to `EVENT3` | Event channel or line | Physical DUT-to-DUTchMate input channels, exposed on connector nets `DUT_EVENT0` through `DUT_EVENT3`. |
| Event role | `interrupt`, `power_good`, `status`, or another configured role | The workflow/reporting meaning DUTchMate should assign to that event channel. |
| UART pair | UART interface | Fixed debugger TX-to-DUT RX and DUT TX-to-debugger RX connection. |

The listed role names are an advisory catalog, not a hardware or protocol
enumeration. Configuration interfaces may suggest control roles `reset`,
`boot`, `power_enable`, and `wake`, and future event roles `interrupt`,
`power_good`, and `status`. Custom names remain valid and are stored exactly;
aliases such as `power_en` are not silently rewritten to `power_enable`.

Software bounds both `role` and `dut_signal` to exact case-sensitive Unicode
strings of 1..64 UTF-8 bytes, rejects leading/trailing whitespace and Unicode
control characters, and performs no trimming, truncation, case folding, Unicode
normalization, or aliasing. Only exact lowercase `reset` and `boot` select those
built-in workflows. These are software metadata rules and do not change the
generic electrical channel design.

The intended software model separates:

- `channel`: the physical DUTchMate connector line, such as `CTRL0` or `EVENT1`
- `role`: the software/workflow meaning, such as `reset`, `boot`, or `power_good`
- `dut_signal`: the user's DUT schematic signal name, such as `RESET_N` or `BOOT0`
- `mode`: `open_drain` or `push_pull`, the configured electrical behavior
  DUTchMate is allowed to use on a control channel

High impedance is an instantaneous drive state, not a Phase 1 configuration
mode. Unconfigured, rejected, startup, unpowered-domain, and fault conditions
keep the channel high impedance. Releasing an `open_drain` channel also enters
the high-impedance drive state without changing its configured mode.

Phase 1 semantic workflows expose `reset` and `boot` as configured DUT
signal roles. That is a role-level API, not a hardware limitation. The hardware
model should remain channel-based so later software can represent mappings such
as:

```text
channel = "CTRL0"
role = "reset"
dut_signal = "RESET_N"
mode = "open_drain"
```

The same distinction applies to event inputs: `EVENT0` is the physical line;
`power_good` or `interrupt_n` is the user-assigned role.

## 4. Four debugger-to-DUT control outputs

### 4.1 Device

Use one `SN74LV4T125PWR`:

- Four independent non-inverting buffers.
- One active-low output-enable input per channel.
- Three-state output when the corresponding output-enable input is high.
- Single supply connected to `DUT_VIO`.
- Output voltage is referenced to `DUT_VIO`.
- Accepts a 3.3 V debugger input for the intended 1.8 V, 2.5 V, 3.3 V, and 5 V output domains.

### 4.2 Logical connection

```text
SN74LV4T125

VCC  = DUT_VIO
GND  = common ground

1A   <- DBG_CTRL_DATA0
1OE  <- DBG_CTRL_nOE0
1Y   -> CTRL0 -> series resistor -> DUT_CTRL0

2A   <- DBG_CTRL_DATA1
2OE  <- DBG_CTRL_nOE1
2Y   -> CTRL1 -> series resistor -> DUT_CTRL1

3A   <- DBG_CTRL_DATA2
3OE  <- DBG_CTRL_nOE2
3Y   -> CTRL2 -> series resistor -> DUT_CTRL2

4A   <- DBG_CTRL_DATA3
4OE  <- DBG_CTRL_nOE3
4Y   -> CTRL3 -> series resistor -> DUT_CTRL3
```

The debugger MCU does not drive the `SN74LV4T125` active-low output-enable pins
directly. Each MCU-side `DBG_CTRL_ENx` signal drives one channel of a
`SN74LVC2G06` open-drain inverter. The inverter output pulls the corresponding
`SN74LV4T125` `/OE` pin low only when the MCU requests that channel to drive.
Each `/OE` net has a pull-up to `DUT_VIO`, so the default state remains disabled
even if the DUT is powered while the debugger 3.3 V rail is absent.

The schematic may label these nets as `DBG_CTRL_OEx`; this document writes them
as `DBG_CTRL_nOEx` only to make the active-low polarity explicit.

```text
DBG_CTRL_ENx -> SN74LVC2G06 input
SN74LVC2G06 open-drain output -> DBG_CTRL_nOEx
DBG_CTRL_nOEx -- 47 kOhm -- DUT_VIO
DBG_CTRL_ENx -- 100 kOhm -- GND
```

For the selected `SN74LV4T125PWR` TSSOP-14 package:

| Channel | IC pin | IC signal | Net |
|---|---:|---|---|
| Supply | 14 | `VCC` | `DUT_VIO` |
| Ground | 7 | `GND` | Common ground |
| `CTRL0` | 2 | `1A` | `DBG_CTRL_DATA0` |
| `CTRL0` | 1 | `1OE` | `DBG_CTRL_nOE0` |
| `CTRL0` | 3 | `1Y` | `CTRL0` |
| `CTRL1` | 5 | `2A` | `DBG_CTRL_DATA1` |
| `CTRL1` | 4 | `2OE` | `DBG_CTRL_nOE1` |
| `CTRL1` | 6 | `2Y` | `CTRL1` |
| `CTRL2` | 9 | `3A` | `DBG_CTRL_DATA2` |
| `CTRL2` | 10 | `3OE` | `DBG_CTRL_nOE2` |
| `CTRL2` | 8 | `3Y` | `CTRL2` |
| `CTRL3` | 12 | `4A` | `DBG_CTRL_DATA3` |
| `CTRL3` | 13 | `4OE` | `DBG_CTRL_nOE3` |
| `CTRL3` | 11 | `4Y` | `CTRL3` |

For the selected `SN74LVC2G06DBVR` SOT-23-6 package:

| IC | IC pin | IC signal | Net |
|---|---:|---|---|
| `U5` | 5 | `VCC` | Debugger 3.3 V |
| `U5` | 2 | `GND` | Common ground |
| `U5` | 1 | `1A` | `DBG_CTRL_EN1` |
| `U5` | 6 | `1Y` | `DBG_CTRL_nOE1` |
| `U5` | 3 | `2A` | `DBG_CTRL_EN0` |
| `U5` | 4 | `2Y` | `DBG_CTRL_nOE0` |
| `U6` | 5 | `VCC` | Debugger 3.3 V |
| `U6` | 2 | `GND` | Common ground |
| `U6` | 1 | `1A` | `DBG_CTRL_EN3` |
| `U6` | 6 | `1Y` | `DBG_CTRL_nOE3` |
| `U6` | 3 | `2A` | `DBG_CTRL_EN2` |
| `U6` | 4 | `2Y` | `DBG_CTRL_nOE2` |

The four buffers are electrically equivalent, but Revision A fixes their
logical `CTRL0` through `CTRL3` assignments. PCB routing must preserve the net,
package-pin, and Pico-pin mapping rather than permuting channels.

### 4.3 Configured modes and output drive states

Each control channel uses two debugger MCU signals:

- `CTRL_DATAx`: value presented to the translator input.
- `CTRL_ENx`: active-high firmware enable for the open-drain inverter stage.

| Firmware drive state | `CTRL_DATAx` | `CTRL_ENx` | SN74 `/OE` | DUT-side electrical state |
|---|---:|---:|---:|---|
| High impedance | X | 0 | 1 | Released / Hi-Z |
| Push-pull low | 0 | 1 | 0 | Actively driven low |
| Push-pull high | 1 | 1 | 0 | Actively driven to `DUT_VIO` |
| Open-drain asserted | 0 | 1 | 0 | Actively pulled low |
| Open-drain released | 0 | 0 | 1 | Released / Hi-Z |

Open-drain operation is implemented by the translator output-enable control,
not by configuring the debugger MCU pin itself as open-drain. For open-drain
mode, firmware holds `CTRL_DATAx = 0` at all times. Assertion drives
`CTRL_ENx = 1`, causing the open-drain inverter to pull the `SN74LV4T125` `/OE`
pin low so the DUT line is pulled low. Release drives `CTRL_ENx = 0`, allowing
the `/OE` pull-up to disable the translator output so the DUT line becomes
high-impedance and the DUT-side pull-up defines the high level.

Phase 1 configuration uses this mode/level matrix:

| Configured mode | Active level | Idle behavior |
|---|---|---|
| `open_drain` | `low` only | Released/high impedance; `idle_level` is omitted |
| `push_pull` | `low` or `high` | Explicit opposite `idle_level` is required |

Firmware keeps the channel high impedance while validating or replacing a
mapping. Once accepted, it enters the mode's idle behavior before the mapping
is made available to workflows. Active-high open drain is unsupported because
the circuit does not implement open-source/high-side-only drive.

For a channel assigned the `boot` role, `set_boot_mode("normal")` selects this
configured idle behavior and `set_boot_mode("bootloader")` selects the active
behavior. Replacing/reapplying the mapping returns the channel to idle. A
disconnect or safety fault forces high impedance regardless of the last
command. Device Core's `commanded_boot_mode` status is therefore command-state
bookkeeping, not electrical feedback from the DUT-side signal.

### 4.4 Reset example

For a DUT reset pin with an existing pull-up to `DUT_VIO`:

```text
Initial configuration:
    CTRL_DATA_RESET = 0

Assert reset:
    CTRL_EN_RESET = 1

Release reset:
    CTRL_EN_RESET = 0
```

When released, the translator output is high-impedance and the DUT's reset pull-up determines the line voltage.

### 4.5 Push-pull example

For a normal active-high wakeup input:

```text
Drive wakeup low:
    CTRL_DATA_WAKE = 0
    CTRL_EN_WAKE   = 1

Drive wakeup high:
    CTRL_DATA_WAKE = 1
    CTRL_EN_WAKE   = 1

Disconnect from wakeup pin:
    CTRL_EN_WAKE   = 0
```

### 4.6 Safe startup state

Each `DBG_CTRL_nOEx` net must have an external pull-up to `DUT_VIO`:

```text
DBG_CTRL_nOE0 -- 47 kOhm -- DUT_VIO
DBG_CTRL_nOE1 -- 47 kOhm -- DUT_VIO
DBG_CTRL_nOE2 -- 47 kOhm -- DUT_VIO
DBG_CTRL_nOE3 -- 47 kOhm -- DUT_VIO
```

Each `DBG_CTRL_ENx` input to the `SN74LVC2G06` stage must have an external
pull-down to ground:

```text
DBG_CTRL_EN0 -- 100 kOhm -- GND
DBG_CTRL_EN1 -- 100 kOhm -- GND
DBG_CTRL_EN2 -- 100 kOhm -- GND
DBG_CTRL_EN3 -- 100 kOhm -- GND
```

Together these keep every DUT control output high-impedance while the debugger
MCU is in reset, unconfigured, starting firmware, or unpowered while `DUT_VIO`
is present.

Each `CTRL_DATAx` input should also have a weak pull-down, for example 100 kOhm
to ground, so the SN74LV4T125 inputs do not float while the debugger MCU pins
are high-impedance during reset. The `DBG_CTRL_nOEx` pull-ups still define the
DUT-facing safe state.

Recommended firmware sequence:

1. Keep `CTRL_EN` low.
2. Configure `CTRL_DATA` to the required value.
3. Configure the channel mode in software.
4. Drive `CTRL_EN` high only when the signal must be actively driven.
5. Return `CTRL_EN` low before reconfiguring the channel.

### 4.7 Control-channel limitations

- These four channels are output-only from DUTchMate's perspective.
- The simplified design does not read back the actual electrical state of a control channel.
- A user must not configure a channel as an active output if the DUT is also driving that net.
- Open-drain operation supports pull-low and release. It does not implement open-source or high-side-only behaviour.
- Control channels are logic signals only. A role such as `power_enable` may
  drive a regulator-enable input or an external load-switch enable pin, but
  DUTchMate must not route DUT supply current through a `CTRLx` pin.
- Connector labels and silkscreen should prefer unambiguous names such as
  `POWER_EN` or `LOAD_SWITCH_EN` instead of `POWER` when the signal is only a
  logic-level enable.

## 5. Four DUT-to-debugger event inputs

### 5.1 Device

Use one `TXU0104PWR`:

- Four fixed-direction, non-inverting channels.
- Dual supply.
- `VCCA = DUT_VIO`.
- `VCCB = 3.3 V`.
- Direction from the DUT-side A port to the debugger-side B port.
- Schmitt-trigger inputs for improved tolerance of slower or noisy digital transitions.
- Active-high global output enable.
- High-impedance outputs when disabled or when either supply is disconnected or below the device's disconnect threshold.

### 5.2 Logical connection

```text
TXU0104

VCCA = DUT_VIO
VCCB = 3.3 V
GND  = common ground

A1 <- EVENT0 <- series resistor <- DUT_EVENT0     B1 -> DBG_EVENT0
A2 <- EVENT1 <- series resistor <- DUT_EVENT1     B2 -> DBG_EVENT1
A3 <- EVENT2 <- series resistor <- DUT_EVENT2     B3 -> DBG_EVENT2
A4 <- EVENT3 <- series resistor <- DUT_EVENT3     B4 -> DBG_EVENT3

OE <- DBG_INPUT_IF_EN
```

For the selected `TXU0104PWR` TSSOP-14 package:

| Channel | IC pin | IC signal | Net |
|---|---:|---|---|
| Supply | 1 | `VCCA` | `DUT_VIO` |
| Supply | 14 | `VCCB` | Debugger 3.3 V |
| Ground | 7 | `GND` | Common ground |
| Enable | 8 | `OE` | `DBG_INPUT_IF_EN` |
| No connect | 6 | `NC` | Leave unconnected |
| No connect | 9 | `NC` | Leave unconnected |
| `EVENT0` | 2 | `A1` | `EVENT0` |
| `EVENT0` | 13 | `B1Y` | `DBG_EVENT0` |
| `EVENT1` | 3 | `A2` | `EVENT1` |
| `EVENT1` | 12 | `B2Y` | `DBG_EVENT1` |
| `EVENT2` | 4 | `A3` | `EVENT2` |
| `EVENT2` | 11 | `B3Y` | `DBG_EVENT2` |
| `EVENT3` | 5 | `A4` | `EVENT3` |
| `EVENT3` | 10 | `B4Y` | `DBG_EVENT3` |

The debugger MCU configures `DBG_EVENT[0:3]` as digital inputs, interrupt inputs, edge-capture inputs, or timer-capture inputs according to the required function.

### 5.3 Supported DUT event outputs

#### Push-pull DUT output

No external pull-up is normally required. The TXU0104 translates the DUT's low and high output levels into the debugger's 3.3 V domain.

#### Open-drain DUT output

The DUT-side event line requires a pull-up to `DUT_VIO`.

If the DUT board already contains the correct pull-up, the DUTchMate pull-up must remain disconnected.

Provide an optional resistor footprint or solder-bridge-selectable pull-up on each event line:

```text
DUT_EVENT0 -- optional 10 kOhm -- DUT_VIO
DUT_EVENT1 -- optional 10 kOhm -- DUT_VIO
DUT_EVENT2 -- optional 10 kOhm -- DUT_VIO
DUT_EVENT3 -- optional 10 kOhm -- DUT_VIO
```

Default assembly state: **not fitted or disconnected**.

The final pull-up value must consider DUT requirements, cable capacitance, event frequency, and the DUT output's sink-current capability.

### 5.4 Event interface enable

Use a 10 kOhm pull-down on `DBG_INPUT_IF_EN`, keeping the translator disabled during debugger startup.

Firmware enables the event translator only after the 3.3 V rail and `DUT_VIO` are valid.

If GPIO count is constrained, the event translator and UART translator may share a common active-high interface-enable signal, provided their startup and operating requirements remain compatible.

### 5.5 Event-channel limitations

- These channels are input-only from DUTchMate's perspective.
- DUTchMate cannot drive an event line through this block.
- An open-drain event requires a valid pull-up to `DUT_VIO`.
- Unknown floating DUT outputs must not be treated as valid events.

## 6. UART interface

### 6.1 Device

Use one `TXU0202DCUR`:

- Two fixed-direction non-inverting channels.
- The two channels face in opposite directions.
- Dual supply from 1.1 V to 5.5 V on either side.
- Schmitt-trigger inputs.
- Active-high global output enable.
- High-impedance outputs when disabled or when either supply is absent.

### 6.2 Logical connection

Use the debugger as the A-side voltage domain and the DUT as the B-side voltage domain:

```text
TXU0202

VCCA = 3.3 V
VCCB = DUT_VIO
GND  = common ground

Debugger UART_TX -> A-to-B channel -> UART_RX -> series resistor -> DUT UART_RX
Debugger UART_RX <- B-to-A channel <- UART_TX <- series resistor <- DUT UART_TX

OE <- DBG_UART_IF_EN
```

For the selected `TXU0202DCUR` VSSOP-8 package:

| Direction | IC pin | IC signal | Net |
|---|---:|---|---|
| Ground | 2 | `GND` | Common ground |
| Supply | 3 | `VCCA` | Debugger 3.3 V |
| Supply | 7 | `VCCB` | `DUT_VIO` |
| Enable | 6 | `OE` | `DBG_UART_IF_EN` |
| Debugger to DUT | 5 | `A1` | `DBG_UART_TX` |
| Debugger to DUT | 8 | `B1Y` | `UART_RX` |
| DUT to debugger | 1 | `B2` | `UART_TX` |
| DUT to debugger | 4 | `A2Y` | `DBG_UART_RX` |

### 6.3 UART recommendations

- Default `DBG_UART_IF_EN` low using a 10 kOhm pull-down.
- Enable the translator only after both voltage domains are valid.
- Use `R16` as the 22 Ohm UART series-resistor array between the connector-side
  `DUT_UART_RX` / `DUT_UART_TX` nets and the translator-side `UART_RX` /
  `UART_TX` nets.
- Revision A validation requires the next board revision to add 10 kOhm from
  translator input `UART_TX` (`U1.B2`, pin 1, after `R16`) to `DUT_VIO`. This
  holds the DUT-to-debugger receive path at the UART idle-high level when the
  DUT transmitter or cable is absent. Existing Revision A prototypes require
  the equivalent helper-side rework for loaded UART hot-plug testing.
- Validate UART operation at the maximum intended baud rate and cable length.

Revision A has one `TXU0202` OE shared by both fixed-direction channels.
Enabling `DBG_UART_IF_EN` to receive DUT UART therefore also enables the
debugger-to-DUT channel. The debugger TX output may actively present the normal
UART idle level at `DUT_UART_RX`; receive-enabled operation is not an
electrically receive-only or high-impedance TX mode.

Host configuration `hardware.uart.tx_enabled` is deliberately a software-send
permission. Setting it false prevents DUTchMate from submitting UART bytes but
does not deassert shared `DBG_UART_IF_EN`, provide electrical readback, or
guarantee high impedance at DUT RX. Independent electrical TX disable would
require a reviewed hardware revision with separate direction enables or an
additional isolation stage.

No required helper-side pull-up is added to `DUT_UART_RX`: it is the
debugger-to-DUT push-pull output while the translator is enabled. A DUT that
must remain quiet with the cable removed must bias its own UART RX input high,
using an internal pull-up or a local external resistor. Other UART pull-ups or
pull-downs remain application-specific.

## 7. Power and sequencing

### 7.1 DUT_VIO

`DUT_VIO` must be supplied by the DUT and connected to:

- `SN74LV4T125.VCC`
- `TXU0104.VCCA`
- `TXU0202.VCCB`
- `DBG_CTRL_nOE[0:3]` pull-ups
- Optional DUT-side event pull-ups

The debugger's 3.3 V rail connects to:

- Debugger MCU I/O
- `SN74LVC2G06.VCC`
- `TXU0104.VCCB`
- `TXU0202.VCCA`

Firmware or the Device Core Service must treat `DUT_VIO` as valid before
enabling translated interfaces or allowing control-output actions. Valid means
the DUT has supplied a reference voltage inside the supported interface range,
currently **1.8 V to 5.0 V**, either by direct measurement or by another
explicitly trusted board/configuration signal.

If `DUT_VIO` is missing, below range, above range, or unknown, DUTchMate must
keep control outputs high-impedance, keep event/UART translators disabled, and
reject hardware actions with a clear fault. `DUT_VIO` is only a reference/supply
input for translators and optional pull-ups; it must not be used to power the
DUT.

### 7.2 DUT_VIO current budget

With the recommended `DUT_VIO_SENSE` divider of 47 kOhm from `DUT_VIO` to the
ADC node and 47 kOhm from the ADC node to ground, the divider is the dominant
idle load on `DUT_VIO`.

Approximate static `DUT_VIO` current, with event pull-ups not fitted and all
control outputs released:

| `DUT_VIO` | Sense-divider current | Approximate total idle current |
|---:|---:|---:|
| 1.8 V | 19 uA | less than 50 uA |
| 2.5 V | 27 uA | less than 60 uA |
| 3.3 V | 35 uA | less than 70 uA |
| 5.0 V | 53 uA | less than 100 uA |

The total idle estimate includes the `SN74LV4T125`, `TXU0104`, and `TXU0202`
DUT-side supply currents plus the 47 kOhm + 47 kOhm sense divider. It does not
include optional DUTchMate event pull-ups, external DUT pull-ups, control
`DBG_CTRL_nOE` pull-up current while a channel is actively enabled, ESD
leakage, or transient switching current.

Each enabled control channel also sinks its `DBG_CTRL_nOEx` pull-up current
through the `SN74LVC2G06` output:

```text
I_nOE_pullup = DUT_VIO / 47 kOhm
```

This is about 38 uA at 1.8 V or 106 uA at 5.0 V per enabled control channel.

Any optional pull-up connected to `DUT_VIO` adds current when its line is driven
low:

```text
I_pullup = DUT_VIO / R_pullup
```

For a 10 kOhm pull-up, budget 180 uA at 1.8 V, 330 uA at 3.3 V, or 500 uA at
5.0 V per asserted low line. Use **1 mA minimum available from DUT_VIO** as a
practical connector requirement for the prototype, and increase that budget if
multiple optional pull-ups may be fitted and held low at the same time.

### 7.3 Decoupling

Use a 100 nF ceramic decoupling capacitor at every translator supply pin, placed close to the IC:

- SN74LV4T125: one 100 nF capacitor.
- SN74LVC2G06: one 100 nF capacitor per package.
- TXU0104: one 100 nF capacitor on VCCA and one on VCCB.
- TXU0202: one 100 nF capacitor on VCCA and one on VCCB.

Additional local bulk capacitance may be added if the board's power-distribution analysis requires it.

### 7.4 Default state

At hardware reset or debugger power-up:

- All four control outputs: high-impedance.
- Event translator: disabled.
- UART translator: disabled.
- No DUT control line is actively driven until firmware has loaded the user's configuration.

### 7.5 DUT removal or missing DUT power

The selected devices provide partial-power-down or supply-disconnect behaviour appropriate to mixed-power-domain use. Nevertheless, the design must be validated for leakage and connector hot-plug behaviour across all expected combinations:

- Debugger powered, DUT unpowered.
- DUT powered, debugger unpowered.
- Both powered.
- DUT disconnected while debugger remains powered.

## 8. Connector proposal

A minimum DUT interface may expose:

| Signal | Direction relative to DUTchMate | Description |
|---|---|---|
| `DUT_VIO` | Input | DUT digital-I/O reference voltage |
| `GND` | Common | Shared signal ground |
| `DUT_CTRL0` | Output | Configurable control output |
| `DUT_CTRL1` | Output | Configurable control output |
| `DUT_CTRL2` | Output | Configurable control output |
| `DUT_CTRL3` | Output | Configurable control output |
| `DUT_EVENT0` | Input | DUT event/status input |
| `DUT_EVENT1` | Input | DUT event/status input |
| `DUT_EVENT2` | Input | DUT event/status input |
| `DUT_EVENT3` | Input | DUT event/status input |
| `DUT_UART_RX` | Output | Debugger UART TX to DUT RX |
| `DUT_UART_TX` | Input | DUT UART TX to debugger RX |

Multiple ground pins are recommended when the signals are carried through a cable. Interleaving grounds with faster signals can improve return paths and signal integrity.

The connector should clearly distinguish `DUT_VIO` from any optional DUT power-supply output.

Prototype connector assignment:

| Connector | Pin | Net | Notes |
|---|---:|---|---|
| `J1` | 1 | `GND` | Common ground |
| `J1` | 2 | `DUT_CTRL0` | Protected external control output |
| `J1` | 3 | `DUT_CTRL2` | Protected external control output |
| `J1` | 4 | `DUT_UART_TX` | DUT TX into DUTchMate |
| `J1` | 5 | `DUT_EVENT2` | Protected external event input |
| `J1` | 6 | `DUT_EVENT0` | Protected external event input |
| `J1` | 7 | `GND` | Common ground |
| `J1` | 8 | `GND` | Common ground |
| `J3` | 1 | `GND` | Common ground |
| `J3` | 2 | `DUT_CTRL1` | Protected external control output |
| `J3` | 3 | `DUT_CTRL3` | Protected external control output |
| `J3` | 4 | `DUT_UART_RX` | DUT RX from DUTchMate |
| `J3` | 5 | `DUT_EVENT3` | Protected external event input |
| `J3` | 6 | `DUT_EVENT1` | Protected external event input |
| `J3` | 7 | `GND` | Common ground |
| `J3` | 8 | `DUT_VIO` / `VCC` | DUT I/O reference voltage |

## 9. Protection and signal integrity

Recommended provisions:

- Series-resistor footprints on every externally connected digital signal.
- Low-capacitance ESD protection near the DUT connector.
- A common-ground connection with sufficiently low impedance.
- Short translator-to-connector routing where practical.
- Clear silkscreen indicating voltage-domain and direction.

Prototype series-resistor values:

| Signal class | Schematic ref. | Selected value | Part marking |
|---|---|---:|---|
| Control GPIO outputs | `R15` | 180 Ohm | `EXB-V8V181JV` |
| Event GPIO inputs | `R13` | 180 Ohm | `EXB-V8V181JV` |
| UART TX/RX | `R16` | 22 Ohm | `EXB-V4V220JV` |

The 180 Ohm control and event resistors are intentionally conservative for the
first prototype. They reduce edge rate, limit transient current during mistakes
or ESD events, and are acceptable for low-to-moderate-speed GPIO control/status
signals. The UART pair uses 22 Ohm because it is a push-pull serial interface
where excessive series resistance can unnecessarily slow edges at higher baud
rates. Final values should still be validated with the intended cable length,
load capacitance, signal rates, and oscilloscope measurements.

ESD protection must be selected for the maximum supported DUT voltage and must
not add excessive capacitance to UART or event signals. `DUT_VIO` should use a
low-leakage TVS/ESD part with a working voltage compatible with 5.0 V operation.

Prototype schematic implementation:

| Ref. | Function | Protected or damped signals |
|---|---|---|
| `R15` | 4-channel isolated 180 Ohm series resistor array | `DUT_CTRL0` through `DUT_CTRL3` |
| `R13` | 4-channel isolated 180 Ohm series resistor array | `DUT_EVENT0` through `DUT_EVENT3` |
| `R16` | 2-channel isolated 22 Ohm series resistor array | `DUT_UART_TX`, `DUT_UART_RX` |
| `D11`, `D13` through `D15` | Single-channel low-capacitance ESD diode | `DUT_CTRL0` through `DUT_CTRL3` |
| `D16` through `D19` | Single-channel low-capacitance ESD diode | `DUT_EVENT0` through `DUT_EVENT3` |
| `D20`, `D21` | Single-channel low-capacitance ESD diode | `DUT_UART_TX`, `DUT_UART_RX` |
| `D12` | Single-channel low-leakage TVS/ESD diode | `DUT_VIO` / connector `VCC` |

The signal ESD diodes should connect to the connector-side `DUT_*` nets. The
series resistor arrays should sit between those protected `DUT_*` nets and the
translator-side `CTRLx`, `EVENTx`, or `UART_x` nets. `D12` should connect from
the connector-side `DUT_VIO` / `VCC` node to ground.

Prototype protection and series-resistor net map:

| External connector net | ESD part | Series path | Translator-side net | Translator pin |
|---|---|---|---|---|
| `DUT_CTRL0` | `D11` pin 1 to GND | `R15`, 180 Ohm | `CTRL0` | `U3.1Y`, pin 3 |
| `DUT_CTRL1` | `D14` pin 1 to GND | `R15`, 180 Ohm | `CTRL1` | `U3.2Y`, pin 6 |
| `DUT_CTRL2` | `D13` pin 1 to GND | `R15`, 180 Ohm | `CTRL2` | `U3.3Y`, pin 8 |
| `DUT_CTRL3` | `D15` pin 1 to GND | `R15`, 180 Ohm | `CTRL3` | `U3.4Y`, pin 11 |
| `DUT_EVENT0` | `D19` pin 1 to GND | `R13`, 180 Ohm | `EVENT0` | `U2.A1`, pin 2 |
| `DUT_EVENT1` | `D17` pin 1 to GND | `R13`, 180 Ohm | `EVENT1` | `U2.A2`, pin 3 |
| `DUT_EVENT2` | `D18` pin 1 to GND | `R13`, 180 Ohm | `EVENT2` | `U2.A3`, pin 4 |
| `DUT_EVENT3` | `D16` pin 1 to GND | `R13`, 180 Ohm | `EVENT3` | `U2.A4`, pin 5 |
| `DUT_UART_RX` | `D21` pin 1 to GND | `R16` pin 1 to pin 4, 22 Ohm | `UART_RX` | `U1.B1Y`, pin 8 |
| `DUT_UART_TX` | `D20` pin 1 to GND | `R16` pin 2 to pin 3, 22 Ohm | `UART_TX` | `U1.B2`, pin 1 |
| `DUT_VIO` / `VCC` | `D12` to GND | Direct | `DUT_VIO` / `VCC` | Translator DUT-side supplies and sense divider |

Detailed signal paths from the DUT connector to the active devices:

| Channel | Connector net | Protection and damping | Active device connection |
|---|---|---|---|
| Control 0 | `DUT_CTRL0` | `D11` ESD to GND, then `R15` 180 Ohm to `CTRL0` | `CTRL0` driven by `U3.1Y`, pin 3 |
| Control 1 | `DUT_CTRL1` | `D14` ESD to GND, then `R15` 180 Ohm to `CTRL1` | `CTRL1` driven by `U3.2Y`, pin 6 |
| Control 2 | `DUT_CTRL2` | `D13` ESD to GND, then `R15` 180 Ohm to `CTRL2` | `CTRL2` driven by `U3.3Y`, pin 8 |
| Control 3 | `DUT_CTRL3` | `D15` ESD to GND, then `R15` 180 Ohm to `CTRL3` | `CTRL3` driven by `U3.4Y`, pin 11 |
| Event 0 | `DUT_EVENT0` | `D19` ESD to GND, then `R13` 180 Ohm to `EVENT0` | `EVENT0` read by `U2.A1`, pin 2 |
| Event 1 | `DUT_EVENT1` | `D17` ESD to GND, then `R13` 180 Ohm to `EVENT1` | `EVENT1` read by `U2.A2`, pin 3 |
| Event 2 | `DUT_EVENT2` | `D18` ESD to GND, then `R13` 180 Ohm to `EVENT2` | `EVENT2` read by `U2.A3`, pin 4 |
| Event 3 | `DUT_EVENT3` | `D16` ESD to GND, then `R13` 180 Ohm to `EVENT3` | `EVENT3` read by `U2.A4`, pin 5 |
| UART DUT RX | `DUT_UART_RX` | `D21` ESD to GND, then `R16` 22 Ohm to `UART_RX` | `UART_RX` driven by `U1.B1Y`, pin 8 |
| UART DUT TX | `DUT_UART_TX` | `D20` ESD to GND, then `R16` 22 Ohm to `UART_TX` | `UART_TX` read by `U1.B2`, pin 1 |

## 10. Debugger MCU resource estimate

| Function | MCU pins |
|---|---:|
| Four control data pins | 4 |
| Four control enable pins | 4 |
| Four event inputs | 4 |
| UART TX/RX | 2 |
| Shared or separate TXU output enables | 1 or 2 |
| Optional DUT_VIO ADC measurement | 1 |

The Revision A baseline uses **17 MCU pins**: separate UART/event interface
enables and the provisioned `DUT_VIO_SENSE` ADC input are included.

### 10.1 Phase 1 Revision A Raspberry Pi Pico 2 pin assignment

This table is the normative Phase 1 Revision A mapping for schematic capture,
PCB net assignment, firmware pin configuration, and hardware tests. It targets
a non-wireless Raspberry Pi Pico 2 or Pico 2 H with the RP2350A MCU. The board
retains the 40-pin Pico form factor used by this mapping. Translators are
optimized for placement between the Pico 2's two header rows, as shown in the
preliminary PCB placement:

```text
Pico 2 USB end
             |    SN74LVC2G06DBVR x2   |
pin 1-20 row |     SN74LV4T125PWR      | pin 40-21 row
             |       TXU0202DCUR       |
             |       TXU0104PWR        |
Pico 2 bottom end
```

This allocation intentionally uses both Pico header rows. Component rotation,
footprint mirroring, and exact pad escape direction remain PCB-layout choices,
but they must preserve every logical-net-to-Pico-pin assignment in the table.

The `TXU0202` uses the primary `UART0` pair on `GP0/GP1`, with its interface
enable on `GP2`. The five `TXU0104` debugger-side event signals are placed on a
left-row group so the DUT-side `DUT_EVENTx` nets can escape toward the DUT
connector cleanly. The `SN74LV4T125` control signals are split between nearby
left-row and right-row Pico GPIOs, with the `SN74LVC2G06` devices converting
active-high MCU enable signals into safe active-low `SN74LV4T125` output
enables.

| DUTchMate net | Pico GPIO | Pico physical pin | Connects to |
|---|---|---:|---|
| `DBG_UART_TX` | `GP0` / `UART0_TX` | 1 | `TXU0202.A1`, pin 5 |
| `DBG_UART_RX` | `GP1` / `UART0_RX` | 2 | `TXU0202.A2Y`, pin 4 |
| `DBG_UART_IF_EN` | `GP2` | 4 | `TXU0202.OE`, pin 6; 10 kOhm pull-down to ground |
| `DBG_CTRL_EN1` | `GP7` | 10 | `SN74LVC2G06.U5.1A`, pin 1; 100 kOhm pull-down to ground |
| `DBG_CTRL_EN0` | `GP8` | 11 | `SN74LVC2G06.U5.2A`, pin 3; 100 kOhm pull-down to ground |
| `DBG_CTRL_DATA0` | `GP9` | 12 | `SN74LV4T125.1A`, pin 2 |
| `DBG_CTRL_DATA1` | `GP10` | 14 | `SN74LV4T125.2A`, pin 5 |
| `DBG_INPUT_IF_EN` | `GP11` | 15 | `TXU0104.OE`, pin 8; 10 kOhm pull-down to ground |
| `DBG_EVENT3` | `GP12` | 16 | `TXU0104.B4Y`, pin 10 |
| `DBG_EVENT2` | `GP13` | 17 | `TXU0104.B3Y`, pin 11 |
| `DBG_EVENT1` | `GP14` | 19 | `TXU0104.B2Y`, pin 12 |
| `DBG_EVENT0` | `GP15` | 20 | `TXU0104.B1Y`, pin 13 |
| `DBG_CTRL_DATA2` | `GP20` | 26 | `SN74LV4T125.3A`, pin 9 |
| `DBG_CTRL_DATA3` | `GP21` | 27 | `SN74LV4T125.4A`, pin 12 |
| `DBG_CTRL_EN3` | `GP22` | 29 | `SN74LVC2G06.U6.1A`, pin 1; 100 kOhm pull-down to ground |
| `DBG_CTRL_EN2` | `GP26` | 31 | `SN74LVC2G06.U6.2A`, pin 3; 100 kOhm pull-down to ground |
| `DUT_VIO_SENSE` | `GP28_ADC2` | 34 | Divider from `DUT_VIO` for valid-voltage detection |

`CTRL0` through `CTRL3` are physical channels. No Pico pin is intrinsically a
reset or boot pin for the DUT; user configuration assigns roles such as
`reset`, `boot`, `wake`, or `power_enable` to these channels.

Reserved resources:

- `GP3` through `GP6`, `GP16` through `GP19`, and `GP27` remain
  available for future functions.
- `GP4/GP5` remain a complete `UART1` TX/RX pair and may be used for a separate
  hardware diagnostic UART while the DUT UART uses `UART0` on `GP0/GP1`.

Channel numbers must not be silently swapped to simplify routing. Any mapping
change requires the architecture table, schematic/net labels, firmware pin
configuration, and mapping tests to change together and creates a new hardware
revision.

### 10.2 Other required Raspberry Pi Pico 2 connections

| Net | Pico pin or rail | Notes |
|---|---|---|
| Debugger 3.3 V | `3V3(OUT)`, physical pin 36 | Powers `SN74LVC2G06.VCC`, `TXU0104.VCCB`, and `TXU0202.VCCA`. Confirm total load remains inside the Pico 2 regulator budget. |
| Common ground | Any Pico `GND`; use several pins for cable return | Connect to translator grounds and DUT connector ground. Interleave ground pins with UART and event/control signals on the external connector where practical. |
| `DUT_VIO_SENSE` divider | `GP28_ADC2`, physical pin 34 | Use 47 kOhm from `DUT_VIO` to ADC and 47 kOhm from ADC to ground, plus an optional small capacitor at the ADC node. This maps 5.0 V to about 2.5 V and draws about 53 uA from `DUT_VIO` at 5.0 V. |
| `ADC_VREF` | Physical pin 35 | Keep decoupled and quiet. Use the firmware's measured/calibrated 3.3 V reference tolerance when validating `DUT_VIO`. |
| Pico 2 `RUN` | Physical pin 30 | Optional local reset control for DUTchMate itself only; do not connect to DUT reset. |
| `VBUS` / `VSYS` | Physical pins 40 / 39 | Use according to the Pico 2 power design. Do not connect either rail to `DUT_VIO`. |

## 11. Suggested firmware model

### 11.1 Control-channel configuration

```c
typedef enum {
    DUT_CTRL_HIGH_Z,
    DUT_CTRL_PUSH_PULL_LOW,
    DUT_CTRL_PUSH_PULL_HIGH,
    DUT_CTRL_OPEN_DRAIN_ASSERT,
    DUT_CTRL_OPEN_DRAIN_RELEASE,
} dut_ctrl_drive_state_t;
```

Expected implementation:

```text
DUT_CTRL_HIGH_Z:
    EN = 0

DUT_CTRL_PUSH_PULL_LOW:
    EN = 0
    DATA = 0
    EN = 1

DUT_CTRL_PUSH_PULL_HIGH:
    EN = 0
    DATA = 1
    EN = 1

DUT_CTRL_OPEN_DRAIN_ASSERT:
    EN = 0
    DATA = 0
    EN = 1

DUT_CTRL_OPEN_DRAIN_RELEASE:
    DATA = 0
    EN = 0
```

### 11.2 User configuration example

```toml
[hardware]
dut_io_voltage = 1.8

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"
active_level = "low"

[hardware.control.boot]
channel = "CTRL1"
dut_signal = "BOOT0"
mode = "push_pull"
active_level = "high"
idle_level = "low"

[hardware.control.wake]
channel = "CTRL2"
dut_signal = "WAKE"
mode = "push_pull"
active_level = "high"
idle_level = "low"

[hardware.control.power_enable]
channel = "CTRL3"
dut_signal = "PMIC_EN"
mode = "push_pull"
active_level = "high"
idle_level = "low"

# Phase 5 examples below; not parsed or applied by Phase 1 software.
[hardware.event.interrupt]
channel = "EVENT0"
dut_signal = "IRQ_N"
active_edge = "falling"
dut_output_type = "open_drain"
debugger_pullup = "disabled"

[hardware.event.power_good]
channel = "EVENT1"
dut_signal = "PGOOD"
active_edge = "rising"
dut_output_type = "push_pull"

[hardware.event.status]
channel = "EVENT2"
dut_signal = "STATUS"
active_edge = "both"
dut_output_type = "push_pull"

[hardware.uart]
baudrate = 460800
data_bits = 8
parity = "none"
stop_bits = 1
```

### 11.3 Configuration validation rules

Software must reject structural conflicts it can prove from configuration, such
as assigning a control role to an `EVENTn` channel or assigning one physical
channel more than once. Configuration does not carry authoritative DUT net
direction and cannot prove that a schematic signal is safe to drive. The user
remains responsible for mapping `CTRLn` only to DUT inputs or safely drivable
open-drain nets and `EVENTn` only to DUT outputs; configuration tools must show
this requirement without claiming automatic electrical validation.

Required validation rules:

- Unknown control channels must be rejected. Phase 1 control channels are
  `CTRL0`, `CTRL1`, `CTRL2`, and `CTRL3`.
- When Phase 5 event configuration is implemented, unknown event channels must
  be rejected. Revision A physically provides `EVENT0`, `EVENT1`, `EVENT2`, and
  `EVENT3`.
- A control role must map to a `CTRLx` channel, not an `EVENTx` channel.
- A Phase 5 event role must map to an `EVENTx` channel, not a `CTRLx` channel.
- Control roles and DUT signal identifiers must satisfy the shared exact 1..64
  UTF-8 byte contract; Phase 5 event identifiers will use the same rule. Role
  equality and workflow lookup are case-sensitive.
- Each physical channel may be assigned at most once in the active
  configuration.
- Required workflow roles, such as `reset` for reset actions, must be mapped
  before that workflow can run.
- Custom roles are accepted as exact project metadata. Only a workflow that
  explicitly recognizes a role may assign behavior to it; built-in Phase 1
  behavior recognizes exact lowercase `reset` and `boot` only.
- Configured control modes are exactly `open_drain` and `push_pull` in Phase 1.
  Firmware uses the high-impedance drive state for startup, unconfigured,
  rejected, disabled-by-safety, and fault handling, and when an open-drain
  output is released.
- Open drain is active-low and has no configured `idle_level`; release is the
  high-impedance idle state. Push pull requires different explicit active and
  idle levels.
- `power_enable` and similar roles are logic-level enables only. They must not
  be interpreted as DUT power-output channels.

Phase 1 does not define a persistent disable/unconfigure API. A future command
may remove an accepted mapping and leave its channel high impedance, but it
must be specified as a state-transition operation rather than adding `high_z`
to the `configure_gpio_mode` mode vocabulary.

## 12. Design decisions and rationale

### 12.1 Why fixed-direction blocks are used

The user already knows the DUT pin function from the DUT schematic. Automatic direction detection is unnecessary and introduces additional electrical restrictions. Fixed-direction translators provide deterministic behaviour and a simpler validation path.

### 12.2 Why control and event GPIOs are separate

Separating four outputs from four inputs eliminates per-channel direction switching and avoids a complex independent drive-and-sense architecture.

The trade-off is that a control output cannot also be captured, and an event input cannot also be driven.

### 12.3 Why the control translator uses independent output enables

Independent output enables allow every control channel to implement:

- Push-pull high
- Push-pull low
- Open-drain low
- Open-drain release
- Fully disconnected high-impedance state

This is required for reset and boot signals that are normally pulled up on the DUT.

### 12.4 Why UART uses a dedicated device

UART is a fixed-direction push-pull interface with simultaneous traffic in opposite directions. TXU0202 directly matches this topology and avoids the loading and edge-behaviour concerns associated with auto-direction translators.

### 12.5 Why control enable uses an open-drain logic driver

Revision A uses two `SN74LVC2G06DBVR` dual open-drain inverters, not discrete
transistors. Each channel converts an active-high 3.3 V MCU enable into a
pull-low action on one `SN74LV4T125` active-low `/OE` input. The `/OE` pull-up to
`DUT_VIO` keeps the control output disabled when the MCU-side driver is
unpowered or inactive and avoids a direct push-pull connection between the
3.3 V and DUT voltage domains.

## 13. Known limitations

1. The complete design is specified for DUT logic domains from 1.8 V to 5.0 V.
2. The DUT and DUTchMate are not galvanically isolated.
3. Control outputs do not have voltage readback in the simplified architecture.
4. DUT signal electrical mode must be configured by the user from the DUT schematic.
5. Open-drain DUT event outputs require a pull-up to `DUT_VIO`.
6. Unknown industrial, analog, or high-voltage signals must not be connected directly.
7. The interface does not automatically protect against every possible user misconfiguration or output contention.
8. The interface does not implement open-source outputs.
9. Final passive values, ESD protection, connector pinout, and maximum cable length require prototype validation. The Revision A logic-device MPNs are fixed unless validation forces a new hardware revision.

## 14. Prototype validation checklist

- [ ] Verify correct operation at `DUT_VIO = 1.8 V`.
- [ ] Verify correct operation at `DUT_VIO = 2.5 V`.
- [ ] Verify correct operation at `DUT_VIO = 3.3 V`.
- [ ] Verify correct operation at `DUT_VIO = 5.0 V`.
- [ ] Verify missing `DUT_VIO` keeps all control outputs high-impedance and event/UART translators disabled.
- [ ] Verify below-range and above-range `DUT_VIO` are rejected before any hardware action.
- [ ] Confirm every control output is high-impedance during debugger reset.
- [ ] Confirm open-drain reset assertion and release against representative DUT pull-ups.
- [ ] Confirm push-pull control high and low levels at every supported voltage.
- [ ] Capture push-pull DUT event outputs at low and high transition rates.
- [ ] Capture open-drain DUT events with DUT-side and optional DUTchMate pull-ups.
- [ ] Verify UART at all required baud rates and cable lengths.
- [ ] Test debugger-powered/DUT-unpowered leakage.
- [ ] Test DUT-powered/debugger-unpowered leakage.
- [ ] Verify `SN74LVC2G06DBVR` leaves every `SN74LV4T125PWR` `/OE` pulled high and disabled through all debugger/DUT power-up and power-down orderings.
- [ ] Verify `SN74LV4T125PWR` input thresholds and output levels at every supported `DUT_VIO` using 3.3 V Pico 2 control inputs.
- [ ] Verify `TXU0104PWR` and `TXU0202DCUR` isolation/high-impedance behavior when either supply is absent.
- [ ] Test hot-plug and unplug behaviour.
- [ ] Check for back-powering through every external signal.
- [ ] Validate series-resistor values using oscilloscope measurements.
- [ ] Validate ESD protection capacitance, leakage, and clamping behaviour.
- [ ] Verify firmware prevents outputs from being enabled before configuration is loaded.
- [ ] Verify firmware/service rejects invalid channel mappings, duplicate channel assignments, and known contention cases.

## 15. Revision A provisional BOM

| Ref. | Component | Revision A part | Notes |
|---|---|---|---|
| U1 | Opposite-direction dual translator | `TXU0202DCUR` | Full-duplex UART |
| U2 | Four-channel fixed-direction translator | `TXU0104PWR` | Four DUT event inputs |
| U3 | Quad translating three-state buffer | `SN74LV4T125PWR` | Four independent control outputs |
| U5, U6 | Dual open-drain inverter | `SN74LVC2G06DBVR` | Safe active-high MCU enable to active-low control `/OE` |
| D11, D13-D21 | Single-channel low-capacitance ESD diode | `TPD1E05U06DPYR-X1SON-2N` | Connector-side ESD protection for control, UART, and event signals |
| D12 | Single-channel low-leakage TVS/ESD diode | `TPD1E10B06DPYR` | Connector-side `DUT_VIO` / `VCC` ESD protection |
| C1, C2 | 100 nF ceramic | — | U1 VCCA/VCCB decoupling |
| C3, C4 | 100 nF ceramic | — | U2 VCCA/VCCB decoupling |
| C5 | 100 nF ceramic | — | U3 decoupling |
| C7, C8 | 100 nF ceramic | — | U5/U6 decoupling |
| R1 | 10 kOhm | — | Pull U2 OE low |
| R2 | 10 kOhm | — | Pull U1 OE low, unless shared |
| R3–R6 | 47 kOhm | — | Pull `DBG_CTRL_nOE[0:3]` high to `DUT_VIO` |
| R7, R8 | 47 kOhm | — | `DUT_VIO_SENSE` divider |
| R9–R12 | 100 kOhm | — | Pull `DBG_CTRL_EN[0:3]` low |
| R15 | 4-channel isolated resistor array, 180 Ohm | `EXB-V8V181JV` | Series resistors for `DUT_CTRL0` through `DUT_CTRL3` |
| R13 | 4-channel isolated resistor array, 180 Ohm | `EXB-V8V181JV` | Series resistors for `DUT_EVENT0` through `DUT_EVENT3` |
| R16 | 2-channel isolated resistor array, 22 Ohm | `EXB-V4V220JV` | Series resistors for `DUT_UART_TX` and `DUT_UART_RX` |
| R17–R20 | 10 kOhm, optional | — | DUT-side event pull-ups; DNP by default |
| C6 | 10 nF to 100 nF, optional | — | Optional `DUT_VIO_SENSE` ADC-node filter |

`U1`, `U2`, `U3`, `U5`, and `U6` are frozen orderable MPNs for the Revision A
prototype. The BOM remains provisional because the validation checklist can
still require a controlled Revision B change. Passive values, ESD parts, and
optional pull-ups remain subject to measurement and layout review.

## 16. Source documents

- Raspberry Pi, **Raspberry Pi Pico 2 datasheet**:
  <https://datasheets.raspberrypi.com/pico/pico-2-datasheet.pdf>
- Zephyr Project, **Raspberry Pi Pico 2 board documentation**:
  <https://docs.zephyrproject.org/latest/boards/raspberrypi/rpi_pico2/doc/index.html>
- Texas Instruments, **SN74LV4T125 product page and datasheet**:  
  <https://www.ti.com/product/SN74LV4T125>
- Texas Instruments, **SN74LVC2G06 product page and datasheet**:  
  <https://www.ti.com/product/SN74LVC2G06>
- Texas Instruments, **TPD1E05U06 product page and datasheet**:  
  <https://www.ti.com/product/TPD1E05U06>
- Texas Instruments, **TPD1E10B06 product page and datasheet**:  
  <https://www.ti.com/product/TPD1E10B06>
- Texas Instruments, **TXU0104 product page and datasheet**:  
  <https://www.ti.com/product/TXU0104>
- Texas Instruments, **TXU0202 product page and datasheet**:  
  <https://www.ti.com/product/TXU0202>
- Texas Instruments, **Schematic Checklist — A Guide to Designing With Fixed or Direction Control Translators**:  
  <https://www.ti.com/lit/pdf/spradm1>

## 17. Revision A Recommendation

Proceed with the following five-IC implementation and the Revision A Pico 2 pin
mapping in section 10.1 for the first DUTchMate prototype:

```text
4 x configurable control outputs: SN74LV4T125PWR
4 x safe control-enable drivers:   2 x SN74LVC2G06DBVR
4 x fixed DUT event inputs:        TXU0104PWR
1 x full-duplex UART pair:         TXU0202DCUR
Supported DUT_VIO:                 1.8 V to 5.0 V
```

This is a deliberately simplified design. It retains the key required behaviour—push-pull and true high-impedance/open-drain control outputs, fixed event-input paths, and reliable UART translation—without implementing a universal bidirectional cell on every GPIO.
