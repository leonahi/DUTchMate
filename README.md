# DUTchMate

DUTchMate helps embedded developers turn UART output and hardware-control
actions into durable evidence that humans and coding agents can inspect. Its
local Device Core Service continuously records UART while it owns a connected
backend. The CLI and service expose deterministic atomic capabilities;
clients and coding agents compose higher-level debug procedures from them.

- **Continuous evidence recording** preserves UART between client requests.
- **Audited Control** provides configured reset, boot-mode, and GPIO actions,
  with durable attempt evidence before physical dispatch.
- **Monitor** observes new evidence for a bounded duration or until a condition.
- **Interact** sends exact UART bytes once and observes a bounded response window.
- **Audited UART TX** sends standalone payloads with explicit line-ending behavior.

## What it looks like

Configure the DUT I/O voltage in the project profile and connect an RP2350-based
Debug Helper. The Enhanced backend can discover and open it during startup.
Configure the reset signal, then use separate Control and observation requests:

```bash
dutchmate devices
dutchmate start --backend enhanced
dutchmate gpio mode CTRL0 reset RESET_N \
  --mode open_drain --active-level low
dutchmate dut reset
dutchmate monitor --seconds 15
dutchmate logs --last 100
```

An illustrative Monitor result identifies its bounded evidence window:

```text
Monitor elapsed
Operation: monitor-00000000-0000-4000-8000-000000000001
Evidence: 20261025T120000Z-demo0001:0..12
```

Recording is already active before reset. A later Monitor observes only evidence
after its own start; immediate boot output remains in the session and is available
through log retrieval. These are independent atomic requests, with no dedicated
reset-and-observe workflow in Device Core.

With `[hardware.uart].tx_enabled = true`, ordinary UART interaction uses the
same service-owned connection and evidence journal:

```bash
dutchmate monitor --until BOOT_OK --timeout 10
dutchmate send PING --line-ending lf
dutchmate send --data-b64 AP8=
dutchmate interact INFO --line-ending lf --until 'DMF/1 INFO' --timeout 5
dutchmate follow                  # Ctrl-C detaches the view; recording continues
dutchmate console --line-ending lf
dutchmate sessions
dutchmate session SESSION_ID
dutchmate release                 # external same-port tool may now open the port
# Close the external tool before reacquiring.
dutchmate reacquire
```

Monitor/Interact return operation IDs and evidence ranges; finishing an operation
leaves the continuous session active. Release/reacquire records the unobserved
interval and opens a fresh timestamp segment. `capture` and `wait` are thin
Monitor aliases. New evidence uses schema v2; historical v0/v1 sessions remain
readable. The Debug Agent currently accepts schema-v1 evidence only.

Coding agents can use the CLI or service to compose procedures from Monitor,
Interact, audited UART TX, and audited reset/boot/GPIO Control. UART TX requires
the profile's TX policy to be enabled. The local stdio MCP adapter exposes the
[twelve-tool v2 catalog](docs/mcp_integration_plan.md#target-tool-catalog), including
Monitor, Interact, configured reset/boot Control and evidence retrieval. It is a
thin HTTP client of the already-running Device Core Service; it never starts the
service or acquires the serial port. Register the installed `dutchmate-mcp` or
`dutchmate mcp` command using the [developer guide](docs/developer_guide.md#register-mcp-with-a-coding-agent).

## Install

DUTchMate requires Python 3.10 or newer. The examples on this page describe the
current checkout. Install its workspace and make its commands available in the
current shell:

```bash
uv sync --all-packages
export PATH="$PWD/.venv/bin:$PATH"
```

For the published `v0.1.0` release, use either isolated-tool installer below.
That release predates the Phase 1/MCP v2 migrations; its original surface is
described in the [historical release notes](docs/releases/v0.1.0.md). The workspace
package version alone does not mean these checkout changes have been published.

```bash
uv tool install dutchmate==0.1.0
# or
pipx install dutchmate==0.1.0
```

## Quick Start

For Enhanced, set `[hardware].dut_io_voltage` in `.dutchmate/config.toml` to
the actual DUT logic voltage before opening the Debug Helper. List candidate
devices, start one backend, inspect it, and stop the service:

```bash
dutchmate devices
dutchmate start --backend enhanced
dutchmate status
dutchmate stop
```

Basic mode requires a user-selected generic USB-to-UART port. Enhanced mode can
auto-select one metadata-hinted Debug Helper; multiple candidates require an
explicit port. Run `dutchmate --help` for the complete command surface and see
the [developer guide](docs/developer_guide.md) for configuration and MCP host
registration.

For Basic, replace the start command with
`dutchmate start --backend basic --serial-port /dev/cu.EXAMPLE`, using the
actual adapter path. Select one backend at a time.

## Hardware

The **Basic** backend uses a generic TTL/logic-level USB-to-UART adapter for UART
receive and optional UART send. The **Enhanced** backend uses the RP2350-based
Raspberry Pi Pico 2 Debug Helper for UART receive/send, device timestamps,
buffer telemetry, and generic `CTRLn` control. Both feed the same host session
pipeline, but they are mutually exclusive selections; hybrid operation is not
supported.

## Contributing / Development

Start with the [current development status](docs/development_status.md), which
owns active progress and next steps. Completed work is preserved in the
[development history](docs/development_history.md). Setup and validation live
in the [developer guide](docs/developer_guide.md); the full
[documentation index](docs/README.md) and [glossary](docs/glossary.md) cover the
remaining project contracts.

The repository is a `uv` workspace. From a checkout:

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
```

## Licensing and contributions

DUTchMate uses licenses appropriate to each kind of material: Apache-2.0 for
host software and firmware, CC-BY-4.0 for general documentation, and a future
CERN-OHL-P-2.0 grant for audited KiCad hardware-design material. The legacy
EAGLE files are excluded from the new grants. See [LICENSE.md](LICENSE.md) for
the authoritative scope map.

Future pull-request commits require DCO 1.1 sign-off. See
[CONTRIBUTING.md](CONTRIBUTING.md) for the contribution and validation workflow.
