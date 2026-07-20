# DUTchMate Voltage-Domain GPIO and UART Interface

**Status:** Proposed hardware architecture  
**Revision:** 0.1  
**Date:** 2026-07-16  
**Scope:** Four debugger-to-DUT control signals, four DUT-to-debugger event signals, and one UART pair across different logic-voltage domains.

## 1. Purpose

DUTchMate uses a 3.3 V debugger MCU, while a connected device under test (DUT) may use a different digital-I/O voltage such as 1.8 V, 2.5 V, 3.3 V, or 5 V.

The interface must allow the user to read the DUT schematic and configure DUTchMate appropriately. Automatic detection of DUT pin direction or electrical mode is not required.

The agreed simplified interface provides:

- Four fixed-direction control channels from DUTchMate to the DUT.
- Four fixed-direction event channels from the DUT to DUTchMate.
- One full-duplex UART interface with one channel in each direction.
- Per-channel push-pull, open-drain, or high-impedance operation on the four control channels.
- Capture of push-pull or open-drain DUT event outputs on the four event channels.
- A common ground between DUTchMate and the DUT.

## 2. System requirements

### 2.1 Debugger domain

- Debugger MCU I/O voltage: **3.3 V**.
- The debugger MCU controls all output modes in software.
- Debugger pins must default to a state that does not accidentally reset, boot, wake, or otherwise control the DUT during startup.

### 2.2 DUT domain

- Target DUT digital-I/O voltage: **1.8 V to 5.0 V** for the complete proposed interface.
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
| Event GPIO translator | 1 | `TXU0104PWR` | DUT to debugger |
| UART translator | 1 | `TXU0202DCUR` | One channel in each direction |

```text
                              DUTchMate
                         Debugger MCU, 3.3 V
                                  |
            +---------------------+---------------------+
            |                     |                     |
      4 x CTRL_DATA         4 x EVENT_IN          UART TX / RX
      4 x CTRL_nOE                |                     |
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

### 3.1 Hardware-to-software mapping

The hardware exposes generic physical channels. Software assigns meaning to
those channels using user configuration. The user is responsible for mapping
physical DUTchMate channels to the DUT schematic signals they actually wired.

| Hardware concept | Software concept | Meaning |
|---|---|---|
| `CTRL0` to `CTRL3` | Control channel or line | Physical DUTchMate-to-DUT output channels. |
| Control role | `reset`, `boot`, `wake`, `power_enable`, or another configured role | The workflow meaning DUTchMate should assign to that channel. |
| DUT signal name | `RESET_N`, `BOOT0`, `WAKE`, `PGOOD`, or another schematic name | The exact net or pin name from the user's DUT schematic. |
| Control mode | `high_z`, `open_drain`, or `push_pull` | How DUTchMate may drive or release the assigned control channel. |
| `EVENT0` to `EVENT3` | Event channel or line | Physical DUT-to-DUTchMate input channels. |
| Event role | `interrupt`, `power_good`, `status`, or another configured role | The workflow/reporting meaning DUTchMate should assign to that event channel. |
| UART pair | UART interface | Fixed debugger TX-to-DUT RX and DUT TX-to-debugger RX connection. |

The intended software model separates:

- `channel`: the physical DUTchMate connector line, such as `CTRL0` or `EVENT1`
- `role`: the software/workflow meaning, such as `reset`, `boot`, or `power_good`
- `dut_signal`: the user's DUT schematic signal name, such as `RESET_N` or `BOOT0`
- `mode`: the electrical behavior DUTchMate is allowed to use on a control channel

Phase 1 host software currently exposes `reset` and `boot` as configured DUT
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
1Y   -> DUT_CTRL0

2A   <- DBG_CTRL_DATA1
2OE  <- DBG_CTRL_nOE1
2Y   -> DUT_CTRL1

3A   <- DBG_CTRL_DATA2
3OE  <- DBG_CTRL_nOE2
3Y   -> DUT_CTRL2

4A   <- DBG_CTRL_DATA3
4OE  <- DBG_CTRL_nOE3
4Y   -> DUT_CTRL3
```

The exact pin numbers must be taken from the selected package datasheet during schematic capture.

### 4.3 Supported output modes

Each control channel uses two debugger MCU signals:

- `CTRL_DATAx`: value presented to the translator input.
- `CTRL_nOEx`: active-low output enable.

| Software mode | `CTRL_DATAx` | `CTRL_nOEx` | DUT-side electrical state |
|---|---:|---:|---|
| High impedance | X | 1 | Released / Hi-Z |
| Push-pull low | 0 | 0 | Actively driven low |
| Push-pull high | 1 | 0 | Actively driven to `DUT_VIO` |
| Open-drain asserted | 0 | 0 | Actively pulled low |
| Open-drain released | 0 | 1 | Released / Hi-Z |

Open-drain operation is implemented by the translator output-enable control,
not by configuring the debugger MCU pin itself as open-drain. For open-drain
mode, firmware holds `CTRL_DATAx = 0` at all times. Assertion enables the
translator output so the DUT line is pulled low. Release disables the translator
output so the DUT line becomes high-impedance and the DUT-side pull-up defines
the high level.

### 4.4 Reset example

For a DUT reset pin with an existing pull-up to `DUT_VIO`:

```text
Initial configuration:
    CTRL_DATA_RESET = 0

Assert reset:
    CTRL_nOE_RESET = 0

Release reset:
    CTRL_nOE_RESET = 1
```

When released, the translator output is high-impedance and the DUT's reset pull-up determines the line voltage.

### 4.5 Push-pull example

For a normal active-high wakeup input:

```text
Drive wakeup low:
    CTRL_DATA_WAKE = 0
    CTRL_nOE_WAKE  = 0

Drive wakeup high:
    CTRL_DATA_WAKE = 1
    CTRL_nOE_WAKE  = 0

Disconnect from wakeup pin:
    CTRL_nOE_WAKE  = 1
```

### 4.6 Safe startup state

Each `CTRL_nOEx` input must have an external pull-up to the debugger 3.3 V rail:

```text
CTRL_nOE0 -- 10 kOhm -- 3.3 V
CTRL_nOE1 -- 10 kOhm -- 3.3 V
CTRL_nOE2 -- 10 kOhm -- 3.3 V
CTRL_nOE3 -- 10 kOhm -- 3.3 V
```

This keeps every DUT control output high-impedance while the debugger MCU is in reset, unconfigured, or starting firmware.

Recommended firmware sequence:

1. Keep `CTRL_nOE` high.
2. Configure `CTRL_DATA` to the required value.
3. Configure the channel mode in software.
4. Pull `CTRL_nOE` low only when the signal must be actively driven.
5. Return `CTRL_nOE` high before reconfiguring the channel.

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

A1 <- DUT_EVENT0     B1 -> DBG_EVENT0
A2 <- DUT_EVENT1     B2 -> DBG_EVENT1
A3 <- DUT_EVENT2     B3 -> DBG_EVENT2
A4 <- DUT_EVENT3     B4 -> DBG_EVENT3

OE <- DBG_INPUT_IF_ENABLE
```

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

Use a 10 kOhm pull-down on `DBG_INPUT_IF_ENABLE`, keeping the translator disabled during debugger startup.

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

Debugger UART_TX -> A-to-B channel -> DUT UART_RX
Debugger UART_RX <- B-to-A channel <- DUT UART_TX

OE <- DBG_UART_IF_ENABLE
```

Verify the exact channel and pin mapping from the TXU0202 package datasheet during schematic capture.

### 6.3 UART recommendations

- Default `DBG_UART_IF_ENABLE` low using a 10 kOhm pull-down.
- Enable the translator only after both voltage domains are valid.
- Place optional series-resistor footprints close to the driving outputs.
- A starting value of 22 to 47 Ohm may be evaluated for edge damping.
- Validate UART operation at the maximum intended baud rate and cable length.

Do not use UART pull-ups or pull-downs unless required by the DUT or startup behaviour.

## 7. Power and sequencing

### 7.1 DUT_VIO

`DUT_VIO` must be supplied by the DUT and connected to:

- `SN74LV4T125.VCC`
- `TXU0104.VCCA`
- `TXU0202.VCCB`
- Optional DUT-side event pull-ups

The debugger's 3.3 V rail connects to:

- Debugger MCU I/O
- `TXU0104.VCCB`
- `TXU0202.VCCA`
- Control-output-enable pull-ups

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

### 7.2 Decoupling

Use a 100 nF ceramic decoupling capacitor at every translator supply pin, placed close to the IC:

- SN74LV4T125: one 100 nF capacitor.
- TXU0104: one 100 nF capacitor on VCCA and one on VCCB.
- TXU0202: one 100 nF capacitor on VCCA and one on VCCB.

Additional local bulk capacitance may be added if the board's power-distribution analysis requires it.

### 7.3 Default state

At hardware reset or debugger power-up:

- All four control outputs: high-impedance.
- Event translator: disabled.
- UART translator: disabled.
- No DUT control line is actively driven until firmware has loaded the user's configuration.

### 7.4 DUT removal or missing DUT power

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
| `CTRL0` | Output | Configurable control output |
| `CTRL1` | Output | Configurable control output |
| `CTRL2` | Output | Configurable control output |
| `CTRL3` | Output | Configurable control output |
| `EVENT0` | Input | DUT event/status input |
| `EVENT1` | Input | DUT event/status input |
| `EVENT2` | Input | DUT event/status input |
| `EVENT3` | Input | DUT event/status input |
| `UART_TX_TO_DUT` | Output | Debugger UART TX to DUT RX |
| `UART_RX_FROM_DUT` | Input | DUT UART TX to debugger RX |

Multiple ground pins are recommended when the signals are carried through a cable. Interleaving grounds with faster signals can improve return paths and signal integrity.

The connector should clearly distinguish `DUT_VIO` from any optional DUT power-supply output.

## 9. Protection and signal integrity

Recommended provisions:

- Series-resistor footprints on every externally connected digital signal.
- Low-capacitance ESD protection near the DUT connector.
- A common-ground connection with sufficiently low impedance.
- Short translator-to-connector routing where practical.
- Clear silkscreen indicating voltage-domain and direction.

Provisional resistor values for prototype evaluation:

| Signal class | Initial series-resistor range |
|---|---:|
| Control GPIO outputs | 47 to 220 Ohm |
| Event GPIO inputs | 47 to 220 Ohm |
| UART TX/RX | 22 to 47 Ohm |

These values are starting points, not final requirements. Final values should be selected after checking edge rate, trace/cable impedance, capacitive loading, and maximum baud/event rate.

ESD arrays must be selected for the maximum supported DUT voltage and must not add excessive capacitance to UART or event signals.

## 10. Debugger MCU resource estimate

| Function | MCU pins |
|---|---:|
| Four control data pins | 4 |
| Four control output-enable pins | 4 |
| Four event inputs | 4 |
| UART TX/RX | 2 |
| Shared or separate TXU output enables | 1 or 2 |
| Optional DUT_VIO ADC measurement | 1 |

Expected total: approximately **15 to 17 MCU pins**, depending on whether enable signals are shared and whether `DUT_VIO` is measured.

## 11. Suggested firmware model

### 11.1 Control-channel configuration

```c
typedef enum {
    DUT_CTRL_HIGH_Z,
    DUT_CTRL_PUSH_PULL_LOW,
    DUT_CTRL_PUSH_PULL_HIGH,
    DUT_CTRL_OPEN_DRAIN_ASSERT,
    DUT_CTRL_OPEN_DRAIN_RELEASE,
} dut_ctrl_mode_t;
```

Expected implementation:

```text
DUT_CTRL_HIGH_Z:
    nOE = 1

DUT_CTRL_PUSH_PULL_LOW:
    nOE = 1
    DATA = 0
    nOE = 0

DUT_CTRL_PUSH_PULL_HIGH:
    nOE = 1
    DATA = 1
    nOE = 0

DUT_CTRL_OPEN_DRAIN_ASSERT:
    nOE = 1
    DATA = 0
    nOE = 0

DUT_CTRL_OPEN_DRAIN_RELEASE:
    DATA = 0
    nOE = 1
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
baudrate = 115200
data_bits = 8
parity = "none"
stop_bits = 1
```

### 11.3 Configuration validation rules

The software must reject configurations that could create known contention, such
as assigning a control output to a net documented as a DUT push-pull output. It
must also reject duplicate physical channel assignments unless the specific
hardware feature explicitly supports sharing that line.

Required validation rules:

- Unknown control channels must be rejected. Phase 1 control channels are
  `CTRL0`, `CTRL1`, `CTRL2`, and `CTRL3`.
- Unknown event channels must be rejected. Phase 1 event channels are `EVENT0`,
  `EVENT1`, `EVENT2`, and `EVENT3`.
- A control role must map to a `CTRLx` channel, not an `EVENTx` channel.
- An event role must map to an `EVENTx` channel, not a `CTRLx` channel.
- Each physical channel may be assigned at most once in the active
  configuration.
- Required workflow roles, such as `reset` for reset actions, must be mapped
  before that workflow can run.
- A role may be custom only when the workflow treats it as a named signal and
  does not assume reset/boot semantics.
- Control modes must match the channel type and supported hardware behavior:
  `high_z`, `open_drain`, or `push_pull`.
- `power_enable` and similar roles are logic-level enables only. They must not
  be interpreted as DUT power-output channels.

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

## 13. Known limitations

1. The complete design is specified for DUT logic domains from 1.8 V to 5.0 V.
2. The DUT and DUTchMate are not galvanically isolated.
3. Control outputs do not have voltage readback in the simplified architecture.
4. DUT signal electrical mode must be configured by the user from the DUT schematic.
5. Open-drain DUT event outputs require a pull-up to `DUT_VIO`.
6. Unknown industrial, analog, or high-voltage signals must not be connected directly.
7. The interface does not automatically protect against every possible user misconfiguration or output contention.
8. The interface does not implement open-source outputs.
9. Final component values, ESD protection, connector pinout, and maximum cable length require prototype validation.

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
- [ ] Test hot-plug and unplug behaviour.
- [ ] Check for back-powering through every external signal.
- [ ] Validate series-resistor values using oscilloscope measurements.
- [ ] Validate ESD-array capacitance and clamping behaviour.
- [ ] Verify firmware prevents outputs from being enabled before configuration is loaded.
- [ ] Verify firmware/service rejects invalid channel mappings, duplicate channel assignments, and known contention cases.

## 15. Preliminary BOM

| Ref. | Component | Suggested part | Notes |
|---|---|---|---|
| U1 | Quad translating three-state buffer | `SN74LV4T125PWR` | Four independent control outputs |
| U2 | Four-channel fixed-direction translator | `TXU0104PWR` | Four DUT event inputs |
| U3 | Opposite-direction dual translator | `TXU0202DCUR` | Full-duplex UART |
| C1 | 100 nF ceramic | — | U1 decoupling |
| C2, C3 | 100 nF ceramic | — | U2 VCCA/VCCB decoupling |
| C4, C5 | 100 nF ceramic | — | U3 VCCA/VCCB decoupling |
| R1–R4 | 10 kOhm | — | Pull `CTRL_nOE[0:3]` high |
| R5 | 10 kOhm | — | Pull U2 OE low |
| R6 | 10 kOhm | — | Pull U3 OE low, unless shared |
| R7–R10 | 10 kOhm, optional | — | DUT-side event pull-ups; DNP by default |
| RSx | Series resistors | — | Fit after signal-integrity validation |
| D1… | ESD protection | TBD | Select for voltage and capacitance |

## 16. Source documents

- Texas Instruments, **SN74LV4T125 product page and datasheet**:  
  <https://www.ti.com/product/SN74LV4T125>
- Texas Instruments, **TXU0104 product page and datasheet**:  
  <https://www.ti.com/product/TXU0104>
- Texas Instruments, **TXU0202 product page and datasheet**:  
  <https://www.ti.com/product/TXU0202>
- Texas Instruments, **Schematic Checklist — A Guide to Designing With Fixed or Direction Control Translators**:  
  <https://www.ti.com/lit/pdf/spradm1>

## 17. Current recommendation

Proceed with the following three-IC architecture for the first DUTchMate prototype:

```text
4 x configurable control outputs: SN74LV4T125
4 x fixed DUT event inputs:       TXU0104
1 x full-duplex UART pair:        TXU0202
Supported DUT_VIO:                1.8 V to 5.0 V
```

This is a deliberately simplified design. It retains the key required behaviour—push-pull and true high-impedance/open-drain control outputs, fixed event capture inputs, and reliable UART translation—without implementing a universal bidirectional cell on every GPIO.
