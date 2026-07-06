# GPIO Configuration Semantics

> Status: draft decision
> Scope: Device Core, Device Core Service, CLI, and Debug Helper firmware behavior for RESET and BOOT/control modes.

## Goal

GPIO configuration must make hardware control explicit without making every normal boot test repetitive. DUTchMate therefore treats both runtime CLI configuration and config-file configuration as explicit user decisions.

## Pin State Model

Each controllable pin has one of these Device Core states:

| State | Meaning |
|---|---|
| `unconfigured` | No accepted mode exists for this pin. Hardware-starting operations using the pin must fail with `not_configured`. |
| `configured` | The mode was accepted by firmware and may be used by workflows. |
| `rejected` | A requested mode was refused and no previous accepted mode exists for this pin. Hardware-starting operations using the pin must fail with the rejection reason. |

Configured pins also track:

- `pin`: `reset` or `boot`
- `mode`: `open_drain` or `push_pull`
- `source`: `config` or `runtime`
- `configured_at`: host timestamp
- `device_timestamp_us`: optional firmware timestamp from the accepted command response
- `last_rejected`: optional rejected request and error detail, if a later override failed

## Startup Behavior

On `dutchmate start`, the Device Core Service:

1. Loads `.dutchmate/config.toml`.
2. Connects to the Debug Helper.
3. Waits for and validates the `hello` message.
4. Applies configured GPIO modes from `[gpio]`.
5. Marks each pin `configured` only after firmware accepts the mode.

A mode loaded from `.dutchmate/config.toml` counts as explicit configuration because it represents a stored user decision. If a configured startup mode is rejected, the service remains running, the pin is marked `rejected`, and workflows using that pin fail until a valid runtime mode is configured.

If a pin is omitted from `[gpio]`, it remains `unconfigured`.

## Runtime Override Behavior

`dutchmate gpio-mode <pin> <mode>` and `POST /gpio/mode` apply immediately.

Rules:

- Runtime configuration overrides config-file configuration for the current service process.
- Runtime overrides do not edit `.dutchmate/config.toml`.
- A successful runtime override updates the pin state to `configured` with `source: "runtime"`.
- A rejected runtime override must not change the previous accepted mode or `configured` state.
- Rejected mode requests must not change physical pin state.

## Validation Order

The Device Core validates before sending a command to firmware:

1. `pin` is one of `reset` or `boot`.
2. `mode` is one of `open_drain` or `push_pull`.
3. The requested mode is allowed by the connected firmware capabilities and hardware revision metadata, if known.
4. No capture or hardware-starting workflow is currently in a conflicting state.

Firmware remains the final authority. If firmware rejects the mode, the Device Core preserves the previous accepted pin state and returns the firmware error. If no previous accepted mode exists, the pin state becomes `rejected`.

Recommended error mapping:

| Condition | Error |
|---|---|
| Unknown pin or mode | `invalid_argument` |
| Mode is not implemented by this hardware revision | `invalid_argument` |
| Firmware attempted the mode but GPIO hardware failed | `hardware_fault` |
| Pin required for workflow has no accepted mode | `not_configured` |

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

`GET /status` should include GPIO mode state:

```json
{
  "connected": true,
  "port": "/dev/ttyACM0",
  "firmware": "0.1.0",
  "active_session_id": null,
  "gpio_modes": {
    "reset": {
      "state": "configured",
      "mode": "open_drain",
      "source": "config",
      "last_rejected": null
    },
    "boot": {
      "state": "unconfigured"
    }
  }
}
```

`POST /gpio/mode` success response:

```json
{
  "ok": true,
  "pin": "reset",
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
  reset: open_drain (config)
  boot: unconfigured
```

`dutchmate gpio-mode reset open_drain` should print the accepted mode. Rejections should include the firmware or Device Core reason and leave the previous accepted mode visible in `dutchmate status`.

## Safety Rules

- Default physical pin state is high impedance or inactive.
- Configuration is accepted only after firmware acknowledgment.
- Configuration state is per service process and must be rebuilt on service start.
- Runtime overrides are intentionally non-persistent.
- Startup config failures must be visible in `status`.
- Hardware actions must be logged with the GPIO mode in effect at the time of action.
