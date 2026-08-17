# GPIO Configuration Semantics

> Status: accepted Phase 1 target contract
> Scope: Device Core, Device Core Service, CLI, and Debug Helper firmware behavior for generic CTRLn modes and configured control roles.

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
the recognized Phase 1 roles `reset` and `boot`. Recognition by a built-in
workflow is not a prerequisite for configuring another role.

Suggested role names are advisory conveniences for configuration interfaces:

- control: `reset`, `boot`, `power_enable`, `wake`
- event (Phase 5): `interrupt`, `power_good`, `status`

These suggestions are not an enum. DUTchMate stores a custom role exactly as
entered and does not silently alias, normalize, or rewrite names such as
`power_en` to `power_enable`.

## Role And Signal Identifier Contract

`role` and `dut_signal` are case-sensitive Unicode strings whose UTF-8 encoding
is 1..64 bytes. They must not begin or end with a character in the Unicode
`White_Space` property and must not contain a Unicode control character
(General Category `Cc`, including ASCII control characters and DEL). Internal
non-control whitespace is permitted and preserved. Validation counts encoded
UTF-8 bytes, not characters.

Device Core stores and compares the decoded string exactly. It does not trim,
truncate, lowercase, case-fold, apply Unicode normalization, or substitute an
alias. Consequently `reset`, `Reset`, and canonically equivalent but differently
encoded Unicode strings are distinct roles. Built-in Phase 1 workflow semantics
apply only to exact ASCII `reset` and `boot`; another valid spelling remains a
custom role with no built-in workflow.

For TOML, the role is the final key in `[hardware.control.<role>]`; quoted TOML
keys may be used when the identifier is not a valid bare key. The decoded key is
validated by the same rule. Runtime API/CLI arguments and config values use the
same contract. Both `role` and `dut_signal` remain Device Core metadata and are
not sent to Phase 1 firmware. The Debug Helper configures physical `CTRLn`
channels and does not interpret user role names.

Each configurable channel has one of these Device Core states:

| State | Meaning |
|---|---|
| `unconfigured` | No accepted mode exists for this channel. Hardware-starting operations using a missing role must fail with `not_configured`. |
| `configured` | The mode was accepted by firmware and may be used by workflows. |
| `rejected` | A requested mode was refused and no previous accepted mode exists for this channel. Hardware-starting operations using that role must fail with the rejection reason. |

Configured channels also track:

- `channel`: the physical DUTchMate control channel, such as `CTRL0`
- `role`: the user/project role, such as `reset`, `boot`, `wake`, or
  `power_enable`
- `dut_signal`: the user's DUT schematic signal name, such as `RESET_N`
- `mode`: `open_drain` or `push_pull`
- `active_level`: `low` or `high`
- `idle_level`: optional `low` or `high`
- `source`: `config` or `runtime`
- `configured_at`: RFC 3339 UTC host timestamp recording when Device Core
  accepted the configuration result
- `device_timestamp_us`: optional raw RP2040 timer value from the accepted
  firmware command response; it is not session-relative
- `last_rejected`: optional rejected request and error detail, if a later override failed

## Startup Behavior

Target startup behavior for `dutchmate start` with the Enhanced backend:

1. Loads `.dutchmate/config.toml`.
2. Connects to the Debug Helper.
3. Waits for and validates the `hello` message.
4. Applies configured GPIO modes from `[hardware.control.*]`.
5. Marks each channel `configured` only after firmware accepts the mode.

Basic startup still validates the config-file structure and identifier syntax,
but it does not connect to a Debug Helper or apply `CTRLn` mappings. Control
operations remain gated by the absent `gpio_control` capability and return
`unsupported_capability`.

A mode loaded from `.dutchmate/config.toml` counts as explicit configuration because it represents a stored user decision. If a configured startup mode is rejected, the service remains running, the channel is marked `rejected`, and workflows using that role fail until a valid runtime mode is configured.

If a required role is omitted from `[hardware.control.*]`, it remains
`unconfigured`.

Current implementation note: service startup loads `[hardware.control.*]` and,
when connected to a selected Debug Helper, applies each mapping after validating
the firmware `hello`. Without a selected device, the service starts disconnected
and leaves the mappings unapplied.

## Runtime Override Behavior

`dutchmate gpio mode <channel> <role> <dut_signal> --mode <mode> --active-level <level>`
and `POST /gpio/mode` apply immediately when the service is connected to a
Debug Helper.

Rules:

- Runtime configuration overrides config-file configuration for the current service process.
- Runtime overrides do not edit `.dutchmate/config.toml`.
- A successful runtime override updates the channel state to `configured` with `source: "runtime"`.
- A rejected runtime override must not change the previous accepted mode or `configured` state.
- Rejected mode requests must not change physical channel state.

## Validation Order

The Device Core validates before sending a command to firmware:

1. `channel` is one of `CTRL0` to `CTRL3`.
2. `role` satisfies the 1..64-byte exact identifier contract above. There is no
   fixed role allow-list. Phase 1 workflows attach built-in semantics only to
   exact `reset` and `boot`; other valid names remain configuration/status
   metadata.
3. `dut_signal` satisfies the same 1..64-byte lexical contract and remains the
   exact DUT schematic signal name supplied by the user.
4. `mode` is one of `open_drain` or `push_pull`.
5. Level fields satisfy the Phase 1 mode matrix:

   | `mode` | `active_level` | `idle_level` |
   |---|---|---|
   | `open_drain` | required `low` | must be omitted; idle means released/Hi-Z |
   | `push_pull` | required `low` or `high` | required and opposite `active_level` |

6. The requested mode is allowed by the connected firmware capabilities and hardware revision metadata, if known.
7. No capture or hardware-starting workflow is currently in a conflicting state.

Firmware remains the final authority. If firmware rejects the mode, the Device Core preserves the previous accepted channel state and returns the firmware error. If no previous accepted mode exists, the channel state becomes `rejected`.

`high_z` is not a valid Phase 1 `mode`. High impedance is the physical drive
state used before configuration, after a rejection with no prior accepted
state, during safety/fault handling, and for open-drain release. Entering that
state does not change an accepted channel's configured mode. Phase 1 has no
persistent disable/unconfigure operation; such an operation may be specified
later without expanding the mode enum.

Device Core rejects an invalid mode/level combination with `invalid_argument`
before sending a firmware command. Firmware validates the same matrix as
defense in depth. While applying an accepted configuration, firmware keeps the
channel high impedance until all fields are validated; it then enters
open-drain release or the explicit push-pull idle level.

The current host-side `gpio_config` package implements two pieces of this
boundary:

- config-file validation for `[hardware.control.*]`
- semantic control/result handling for `configure_gpio_mode`

It validates channel, role, mode, level, DUT signal, DUT I/O voltage, and
duplicate channel assignments before startup integration code tries to apply the
mapping. It calls an injected backend-neutral device-control port and updates
the registry only after the operation succeeds or returns a device-control
error. The Enhanced adapter owns command encoding and response translation;
service startup supplies that adapter when a device is selected. The
service-facing runtime rejects GPIO configuration with
`capture_active` while a finite capture, boot-test, or target wait-pattern
session owns the serial message stream.

Current host implementation: one shared validator enforces the identifier and
electrical contracts above for config loading, runtime state, command encoding,
service requests, and CLI dispatch. The v1 host-to-device JSON Schema enforces
the same electrical matrix. Accepted identifiers remain byte-for-byte exact;
no layer trims or normalizes them.

Recommended error mapping:

| Condition | Error |
|---|---|
| Selected backend does not provide `gpio_control` | `unsupported_capability` |
| Unknown physical channel; invalid role/DUT signal identifier; invalid mode or level | `invalid_argument` |
| Well-formed custom role without a built-in Phase 1 workflow | Accept configuration; expose it in status |
| Mode is outside the Phase 1 GPIO mode vocabulary | `invalid_argument` |
| Firmware attempted the mode but GPIO hardware failed | `hardware_fault` |
| Role required for workflow has no accepted mode | `not_configured` |

Identifier `invalid_argument` context contains `field` (`role` or
`dut_signal`), `reason` (`invalid_type`, `invalid_length`, `edge_whitespace`, or
`control_character`), and `max_bytes: 64`. For a string value it also includes
`actual_bytes`; it never echoes a control-containing input. Config-file errors
identify the TOML field/table and the same reason before any backend is opened.

Backend capability gating happens before role-state validation. A Basic backend
therefore returns `unsupported_capability` for reset or boot-mode requests even
though it has no control-role registry. `not_configured` applies only after the
selected backend has demonstrated `gpio_control`. These service-level errors use
HTTP 409 and the structured context defined under "Device Core Service
Requirements" in `docs/phase1_implementation_spec.md`.

One effective role maps to at most one physical channel. Config-file validation
rejects conflicting channel assignments. A successful runtime request that
moves a role to another channel replaces its prior role assignment atomically;
it must not leave the role active on both channels. An unrecognized custom role
is never rejected merely because Device Core has no built-in workflow for it.
Role equality for duplicate detection, movement, and lookup is exact and
case-sensitive; `reset` and `Reset` do not collide.

## Workflow Requirements

Host workflows resolve an exact configured role to its physical `CTRLn`
channel before dispatch. Firmware action commands remain role-neutral:
`pulse_control(channel, pulse_ms)` applies configured active then idle behavior,
and `set_control_state(channel, active|idle)` selects one configured behavior.
The public reset and boot-mode APIs remain semantic safety boundaries; Phase 1
does not expose arbitrary raw levels. Current draft protocol files still use
legacy `reset` and `set_boot_mode` action names and a wire `role` field. Phase
1B must remove that field and migrate the actions atomically with their schemas,
examples, encoders, tests, and firmware.

Before `reset_dut()`:

- `reset` must be `configured`.
- Omitted `pulse_ms` defaults to 100 ms. An explicit value must be an integer
  from 1 through 10000 ms inclusive; booleans and fractional values are
  invalid. Argument validation occurs before backend capability and role-state
  validation.

Before `set_boot_mode()`:

- `boot` must be `configured`.
- `normal` selects the boot role's configured idle behavior: release/high
  impedance for `open_drain`, or `idle_level` for `push_pull`.
- `bootloader` selects the boot role's configured active behavior: driven low
  for `open_drain`, or `active_level` for `push_pull`.
- A successful command remains in effect until another boot-mode command is
  accepted, the boot mapping is replaced/reapplied, the backend disconnects,
  or a safety fault forces the channel high impedance. An accepted boot mapping
  starts in `normal`; disconnect and safety-fault paths make the commanded mode
  unknown until configuration is accepted again.

Before `run_boot_test()`:

- `reset` must be `configured`.
- The plain Phase 1 workflow uses the current or externally selected boot state
  and must not issue a boot-mode command. It therefore does not require a
  configured `boot` role.
- A bootloader test is an explicit three-step workflow: select `bootloader`, run
  the boot test, then select `normal`. `run_boot_test()` does not silently
  select or restore either mode.

Read-only operations do not require GPIO configuration.

A successful reset response echoes the accepted `pulse_ms`. A reset recorded
inside a boot-test session stores that value with the normalized control-action
event. Current reset execution validates the range, but response echo and
control-action persistence remain Phase 1 implementation work.

## Service API Reporting

This GPIO-focused excerpt of the target `GET /status` response shows the
channel-first mode state; the complete status contract also includes backend,
capability, and reconnect fields defined in the Phase 1 implementation spec:

```json
{
  "connected": true,
  "connection_state": "connected",
  "reconnect_remaining_s": null,
  "port": "/dev/ttyACM0",
  "firmware": "0.1.0",
  "active_session_id": null,
  "active_workflow": null,
  "commanded_boot_mode": "normal",
  "control_channels": {
    "CTRL0": {
      "state": "configured",
      "role": "reset",
      "channel": "CTRL0",
      "dut_signal": "RESET_N",
      "mode": "open_drain",
      "active_level": "low",
      "idle_level": null,
      "source": "config",
      "configured_at": "2026-08-12T10:15:30Z",
      "device_timestamp_us": 182334400,
      "last_rejected": null
    },
    "CTRL1": {
      "state": "unconfigured"
    }
  }
}
```

`commanded_boot_mode` is `"normal"`, `"bootloader"`, or `null`. It reports
only the last state successfully commanded by Device Core; it is not an
electrical readback of the DUT pin. It is `null` when the boot role is not
configured, the boot state is externally controlled or otherwise unknown, or
the connection/safety state invalidates the last command. Capture-like session
metadata snapshots this nullable value when the session begins.

Current implementation note: boot-mode commands are sent and role-gated, but
Device Core does not yet retain `commanded_boot_mode`, expose it in status, or
store its session-start snapshot.

`POST /gpio/mode` success response:

```json
{
  "ok": true,
  "role": "reset",
  "channel": "CTRL0",
  "dut_signal": "RESET_N",
  "mode": "open_drain",
  "active_level": "low",
  "idle_level": null,
  "source": "runtime",
  "configured_at": "2026-08-12T10:15:30Z",
  "device_timestamp_us": 182334400
}
```

Status, success responses, rejection state, session control events, and reports
preserve the exact accepted `role` and `dut_signal`; display layers do not
normalize them. The CLI may quote or escape a value for unambiguous presentation
but must not alter the underlying returned string.

The current endpoint implementation still names the last field
`timestamp_us`; Phase 1 must complete the host API rename shown above. The
Debug Helper wire response continues to use `timestamp_us` for the raw device
timer. If configuration is recorded as part of a session, its hardware event
uses `segment_id` and normalized segment-relative `timestamp_us`, while the raw
value may be retained only as explicitly named `device_timestamp_us`.

Rejected response:

```json
{
  "ok": false,
  "error": "invalid_argument",
  "detail": "push_pull is not supported for reset on this hardware revision",
  "detail_truncated": false
}
```

## CLI Reporting

`dutchmate status` should show GPIO state in human-readable form:

```text
GPIO:
  CTRL0: reset RESET_N open_drain (config)
  CTRL1: unconfigured
```

`dutchmate gpio mode CTRL0 reset RESET_N --mode open_drain --active-level low`
should print the accepted mode. Rejections should include the firmware or
Device Core reason and leave the previous accepted mode visible in
`dutchmate status`.

## Safety Rules

- Default physical channel state is high impedance or inactive.
- Configuration is accepted only after firmware acknowledgment.
- Configuration state is per service process and must be rebuilt on service start.
- Runtime overrides are intentionally non-persistent.
- Startup config failures must be visible in `status`.
- Hardware actions must be logged with the GPIO mode in effect at the time of action.
- Host API timestamps must distinguish RFC 3339 host time from raw firmware
  time; unqualified `timestamp_us` is reserved for normalized session events.
