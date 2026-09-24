# DUTchMate

DUTchMate helps embedded developers turn UART output and hardware-control
actions into reproducible debug sessions that humans and coding agents can
inspect. It runs a local Device Core Service, records bounded evidence from a
selected hardware backend, and exposes the same deterministic workflows through
a CLI and a tools-only MCP server.

## What it looks like

Connect an RP2350-based Debug Helper, then let the Enhanced backend discover and
open it during service startup. Configure the DUT reset signal and run a bounded
boot test:

```bash
dutchmate devices
dutchmate start --backend enhanced
dutchmate gpio mode CTRL0 reset RESET_N \
  --mode open_drain --active-level low
dutchmate boot-test --seconds 15
```

With deterministic fixture data, the current CLI formatter renders the session
summary like this:

```text
Boot test complete: 20260924T120000Z-demo0001 (backend=enhanced, state=completed, end=duration_elapsed, loss=none_reported, timestamp=device/rp2350_timer:debug_helper_uart_receive/uart_event, first_error=HardFault@segment:0/event:12, lines=complete/oversized:0, segments=1, overflow=no, interrupted=no, resumed=no, truncated=no)
```

The `first_error` coordinate points back into stored session evidence. A coding
agent can launch `dutchmate mcp` and call tools such as `get_debug_session`,
`get_recent_uart_log`, or `run_boot_test` against the same local service.

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
