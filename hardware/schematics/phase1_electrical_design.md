# Phase 1 Electrical Design

> Status: draft decision
> Scope: RP2040 Debug Helper MVP signal interface to one DUT.

## Decision Summary

Phase 1 separates signal classes instead of using one generic bidirectional voltage translator for every line.

- UART uses a fixed-direction, dual-supply level translator.
- RESET uses an open-drain low-side pull-down stage.
- BOOT/control supports open-drain low-side pull-down in MVP; push-pull BOOT/control is optional and must be explicitly populated, enabled, and advertised by the firmware.
- DUTchMate requires a `VREF_DUT` input from the target for translated signal levels.
- All DUT-facing outputs default to high impedance until the Device Core configures the pin mode.

This keeps reset behavior compatible with common active-low reset pins and avoids driving target-owned pull-ups or supervisor circuits high.

## Electrical Interface

Minimum Phase 1 connector signals:

```text
GND
VREF_DUT
DUT_UART_TX  -> DUTchMate UART RX
DUT_UART_RX  <- DUTchMate UART TX
DUT_RESET_N  <- DUTchMate open-drain pull-down
DUT_BOOT_CTL <- DUTchMate open-drain pull-down or optional push-pull path
```

`VREF_DUT` is the DUT logic reference voltage. Supported target range for Phase 1 is 1.8V, 3.3V, or 5V nominal, subject to the selected translator's data sheet limits.

The Debug Helper and DUT share common ground in Phase 1. Galvanic isolation is not part of MVP.

## UART Translation

Use a fixed-direction dual-supply translator for UART, not an auto-direction part.

Recommended part class:

- TI TXU0304/TXU0204 family or equivalent fixed-direction translator
- Schmitt-trigger inputs preferred
- Both voltage rails must support the required RP2040 and DUT logic levels
- Direction must match the UART/control mapping

Recommended mapping for TXU0304-class parts:

```text
VCCA = RP2040 3.3V
VCCB = VREF_DUT

RP2040_UART_TX -> A-to-B channel -> DUT_UART_RX
DUT_UART_TX    -> B-to-A channel -> RP2040_UART_RX
```

TXU0304 has a useful 3-forward/1-reverse shape for a debug-helper interface, but the exact final part should be selected during schematic capture based on package availability and channel count.

## RESET Control

RESET is open-drain only in Phase 1.

Recommended circuit:

```text
RP2040 GPIO -> gate resistor -> small N-MOSFET gate
N-MOSFET source -> GND
N-MOSFET drain  -> DUT_RESET_N through optional series resistor
DUT_RESET_N pull-up -> supplied by DUT
```

Rules:

- DUTchMate only pulls RESET low or releases it.
- DUTchMate does not drive RESET high in Phase 1.
- If the DUT does not provide a reset pull-up, use an optional weak pull-up to `VREF_DUT`, disabled by default or clearly marked as a board option.
- Firmware must keep the RESET control GPIO inactive/high-Z during boot until configured.
- `configure_gpio_mode("reset", "push_pull")` must return `invalid_argument` or `hardware_fault` on hardware revisions that do not implement a safe push-pull reset path.

## BOOT/Control Pin

BOOT/control pins vary by target. Some are active-low straps, some are active-high, and some are sampled only around reset.

Phase 1 default:

- Support BOOT/control as an open-drain pull-down path.
- Use it for active-low bootloader straps such as "hold low during reset".
- Do not assume that DUTchMate can drive an active-high BOOT pin unless the optional push-pull path is present.

Optional push-pull BOOT/control path:

- May be implemented through a fixed-direction translator powered by `VREF_DUT`.
- Must default to high impedance or inactive during Debug Helper boot.
- Must be protected by explicit `configure_gpio_mode("boot", "push_pull")`.
- Should be documented per hardware revision because it can actively drive target state.

## Parts To Avoid As Defaults

Do not use TXB0108-style auto-direction translators as the default interface for RESET, BOOT, or open-drain control lines.

Reasons:

- Auto-direction translators are intended for push-pull logic.
- They can interact badly with external pull-ups, strong drivers, or target reset supervisors.
- They do not provide the deterministic "pull low or release" behavior expected from reset control.

TXS0102-style translators can support open-drain and UART-class signals, but they include internal pull-ups and one-shot edge acceleration. They are acceptable only after validating line capacitance, pull-up interactions, and reset/boot behavior on the target interface. They are not the default Phase 1 reset-control choice.

## Firmware and Software Semantics

At power-up:

- RP2040 control pins must be inputs or otherwise inactive.
- Translator outputs must be disabled or benign where possible.
- The host must receive a `hello` message before issuing hardware commands.

Mode configuration:

- The Device Core still requires `configure_gpio_mode` before reset or boot-mode workflows.
- A mode loaded from `.dutchmate/config.toml` counts as explicit configuration because it represents a stored user decision.
- Firmware may reject a requested mode if the connected hardware revision cannot implement it safely.
- Rejected mode requests must not change pin state.

Capability reporting:

- `gpio_control` means basic safe GPIO workflows are available.
- Future hardware revisions that support actively driven control pins should add a more specific capability instead of changing `gpio_control` semantics silently.

## Protection

Minimum Phase 1 breadboard/prototype protection:

- Series resistors on UART TX/RX lines.
- Gate resistors on MOSFET-controlled reset/boot lines.
- Clear `VREF_DUT` labeling and no-drive behavior when `VREF_DUT` is absent.

Recommended before shared or production-adjacent use:

- TVS diodes on DUT-facing signal lines.
- Current-limited or protected `VREF_DUT` sense path.
- Connector pinout that prevents accidental 5V injection into RP2040 GPIO.

## Validation Checklist

Before treating a hardware revision as supported:

- Confirm no DUT-facing line drives high during Debug Helper boot.
- Confirm RESET low pulse width at the DUT pin.
- Confirm RESET release edge reaches the DUT's required high level through the DUT pull-up.
- Confirm UART RX into RP2040 never exceeds RP2040 IO limits.
- Confirm 1.8V DUT UART high is read correctly after translation.
- Confirm 5V DUT UART high is translated down before reaching RP2040.
- Confirm BOOT/control behavior on at least one active-low boot strap.
- Record oscilloscope captures for reset pulse, boot-control assertion, and UART at 460800 baud.

## References

- TI TXU0304 data sheet: https://www.ti.com/lit/ds/symlink/txu0304.pdf
- TI TXS0102 data sheet: https://www.ti.com/lit/ds/symlink/txs0102.pdf
- TI TXB0108 data sheet: https://www.ti.com/lit/ds/symlink/txb0108.pdf
- Raspberry Pi RP2040 data sheet: https://datasheets.raspberrypi.com/rp2040/rp2040-datasheet.pdf
