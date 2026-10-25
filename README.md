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
dutchmate logs --lines 100
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

Coding agents can use the CLI or service to compose procedures from Monitor,
Interact, audited UART TX, and audited reset/boot/GPIO Control. UART TX requires
the profile's TX policy to be enabled. The separate MCP adapter's contract and
migration scope are tracked in the [development status](docs/development_status.md).

## Install

DUTchMate requires Python 3.10 or newer. Install the `v0.1.0` release with one
of these isolated-tool installers:

```bash
uv tool install dutchmate==0.1.0
# or
pipx install dutchmate==0.1.0
```

## Quick Start

List candidate devices, start one backend, inspect it, and stop the service:

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
