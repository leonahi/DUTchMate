# GPIO Configuration Semantics

> Status: draft decision
> Scope: Device Core, Device Core Service, CLI, and Debug Helper firmware behavior for RESET and BOOT/control modes.

## Goal

GPIO configuration must make hardware control explicit without making every normal boot test repetitive. DUTchMate therefore treats both runtime CLI configuration and config-file configuration as explicit user decisions.

## Channel State Model

Phase 1 treats `CTRL0` to `CTRL3` as the primary configured DUT control
resources. The current host-side state model therefore keys state by physical
channel:

```text
CTRL0
CTRL1
CTRL2
CTRL3
```

The hardware channel mapping model is defined in
`docs/dutchmate_hardware_architecture.md`. In that model, physical channels
such as `CTRL0` are separate from workflow roles such as `reset` and DUT
schematic names such as `RESET_N`. Phase 1 host code accepts custom control
roles as project metadata, while built-in workflows only assign semantics to
known roles such as `reset` and `boot`.

Each configurable channel has one of these Device Core states:

| State | Meaning |
|---|---|
| `unconfigured` | No accepted mode exists for this channel. Hardware-starting operations using a missing role must fail with `not_configured`. |
| `configured` | The mode was accepted by firmware and may be used by workflows. |
| `rejected` | A requested mode was refused and no previous accepted mode exists for this channel. Hardware-starting operations using that role must fail with the rejection reason. |

Configured channels also track:

- `channel`: the physical DUTchMate control channel, such as `CTRL0`
- `role`: the user/project role, such as `reset`, `boot`, `wake`, or `power_en`
- `dut_signal`: the user's DUT schematic signal name, such as `RESET_N`
- `mode`: `open_drain` or `push_pull`
- `active_level`: `low` or `high`
- `idle_level`: optional `low` or `high`
- `source`: `config` or `runtime`
- `configured_at`: host timestamp
- `device_timestamp_us`: optional firmware timestamp from the accepted command response
- `last_rejected`: optional rejected request and error detail, if a later override failed

## Startup Behavior

On `dutchmate start`, the Device Core Service:

1. Loads `.dutchmate/config.toml`.
2. Connects to the Debug Helper.
3. Waits for and validates the `hello` message.
4. Applies configured GPIO modes from `[hardware.control.*]`.
5. Marks each channel `configured` only after firmware accepts the mode.

A mode loaded from `.dutchmate/config.toml` counts as explicit configuration because it represents a stored user decision. If a configured startup mode is rejected, the service remains running, the channel is marked `rejected`, and workflows using that role fail until a valid runtime mode is configured.

If a required role is omitted from `[hardware.control.*]`, it remains
`unconfigured`.

## Runtime Override Behavior

`dutchmate gpio-mode <role> <mode>` and `POST /gpio/mode` apply immediately.

Rules:

- Runtime configuration overrides config-file configuration for the current service process.
- Runtime overrides do not edit `.dutchmate/config.toml`.
- A successful runtime override updates the channel state to `configured` with `source: "runtime"`.
- A rejected runtime override must not change the previous accepted mode or `configured` state.
- Rejected mode requests must not change physical channel state.

## Validation Order

The Device Core validates before sending a command to firmware:

1. `channel` is one of `CTRL0` to `CTRL3`.
2. `role` is a non-empty project role name. Phase 1 workflows only attach
   built-in semantics to known roles such as `reset` and `boot`.
3. `dut_signal` is a non-empty DUT schematic signal name.
4. `mode` is one of `open_drain` or `push_pull`.
5. `active_level` and optional `idle_level` are `low` or `high`.
6. The requested mode is allowed by the connected firmware capabilities and hardware revision metadata, if known.
7. No capture or hardware-starting workflow is currently in a conflicting state.

Firmware remains the final authority. If firmware rejects the mode, the Device Core preserves the previous accepted channel state and returns the firmware error. If no previous accepted mode exists, the channel state becomes `rejected`.

The current host-side `gpio_config` package implements two pieces of this
boundary:

- config-file validation for `[hardware.control.*]`
- command/result handling for `configure_gpio_mode`

It validates channel, role, mode, level, DUT signal, DUT I/O voltage, and
duplicate channel assignments before startup integration code tries to apply the
mapping. It sends the encoded command through an injected transport and updates
the registry only after a command success or command error response. The real
serial transport is not implemented yet.

Recommended error mapping:

| Condition | Error |
|---|---|
| Unknown channel, role, mode, or level | `invalid_argument` |
| Mode is not implemented by this hardware revision | `invalid_argument` |
| Firmware attempted the mode but GPIO hardware failed | `hardware_fault` |
| Role required for workflow has no accepted mode | `not_configured` |

## Workflow Requirements

Before `reset_dut()`:

- `reset` must be `configured`.

Before `set_boot_mode()`:

- `boot` must be `configured`.

Before `run_boot_test()`:

- `reset` must be `configured`.
- `boot` must be `configured` only if the requested boot-test workflow changes BOOT/control state.

Read-only operations do not require GPIO configuration.

## Service API Reporting

`GET /status` should include channel-first GPIO mode state:

```json
{
  "connected": true,
  "port": "/dev/ttyACM0",
  "firmware": "0.1.0",
  "active_session_id": null,
  "control_channels": {
    "CTRL0": {
      "state": "configured",
      "role": "reset",
      "channel": "CTRL0",
      "dut_signal": "RESET_N",
      "mode": "open_drain",
      "source": "config",
      "last_rejected": null
    },
    "CTRL1": {
      "state": "unconfigured"
    }
  }
}
```

`POST /gpio/mode` success response:

```json
{
  "ok": true,
  "role": "reset",
  "channel": "CTRL0",
  "dut_signal": "RESET_N",
  "mode": "open_drain",
  "source": "runtime",
  "timestamp_us": 182334400
}
```

Rejected response:

```json
{
  "ok": false,
  "error": "invalid_argument",
  "detail": "push_pull is not supported for reset on this hardware revision"
}
```

## CLI Reporting

`dutchmate status` should show GPIO state in human-readable form:

```text
GPIO:
  CTRL0: reset RESET_N open_drain (config)
  CTRL1: unconfigured
```

`dutchmate gpio-mode reset open_drain` should print the accepted mode. Rejections should include the firmware or Device Core reason and leave the previous accepted mode visible in `dutchmate status`.

## Safety Rules

- Default physical channel state is high impedance or inactive.
- Configuration is accepted only after firmware acknowledgment.
- Configuration state is per service process and must be rebuilt on service start.
- Runtime overrides are intentionally non-persistent.
- Startup config failures must be visible in `status`.
- Hardware actions must be logged with the GPIO mode in effect at the time of action.
