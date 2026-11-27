<p align="center">
  <img
    src="assets/branding/dutchmate_rectangle_logo_web.svg"
    alt="DUTchMate"
    width="600"
  />
</p>

<p align="center">
  Connect your coding agent to your embedded device.
</p>

# DUTchMate

DUTchMate gives your coding agent access to UART logs, firmware commands, and
configured reset and boot controls through MCP. Your agent can investigate
device behavior alongside your source code, using recorded evidence.

Use your coding agent's existing model. The separate DUTchMate Debug Agent
package is not required.

## 1. Install DUTchMate

Requires **Python 3.10+** and **uv**:

```bash
uv tool install dutchmate==0.2.0
```

If the installed commands are not on your PATH, run `uv tool update-shell` and
reopen your terminal. See the [v0.2.0 release notes](docs/releases/v0.2.0.md)
for upgrade guidance, or the [setup guide](docs/developer_guide.md#local-setup)
to run from a repository checkout.

## 2. Connect your device

| Connection | Available capabilities |
|---|---|
| TTL USB-to-UART adapter (Basic) | UART logs and optional firmware commands |
| RP2350 Pico 2 Debug Helper (Enhanced) | UART plus configured reset, boot and GPIO control |

Connect your adapter and configure the matching baud rate and wiring. See the
[setup guide](docs/developer_guide.md#local-setup) for configuration. Replace
`YOUR_UART_PORT` with your adapter's actual serial port:

```bash
dutchmate start --backend basic --serial-port YOUR_UART_PORT
dutchmate status
```

For the Debug Helper, use `dutchmate start --backend enhanced` instead. Follow
the [wiring guide](hardware/firmware/rp2350_debug_helper/README.md#revision-a-mapping)
to connect its DUT_VIO reference to the DUT's logic supply.

## 3. Connect your coding agent

Find the MCP launcher's absolute path:

```bash
command -v dutchmate-mcp
```

Register a local MCP server in your coding agent with these settings:

| Setting | Value |
|---|---|
| Name | `dutchmate` |
| Transport | `stdio` |
| Command | The absolute launcher path printed above |
| Arguments | `--service-url http://127.0.0.1:2040` |

See the [agent-specific configuration examples](docs/developer_guide.md#register-mcp-with-a-coding-agent)
for the format your host expects. Your coding agent launches the MCP process.
**The Device Core Service must already be running; MCP does not start it.**

Verify that the agent lists the DUTchMate tools, then ask it to check the device
connection before debugging.

## 4. Start debugging

Try these prompts in your coding agent:

> Check the device connection and summarize the latest UART logs.

> Observe UART for 15 seconds and identify errors or unexpected behavior.

> Investigate this boot failure using the UART evidence and this repository.
> Propose a fix, and ask before resetting the board or sending commands.

DUTchMate records UART continuously while the service owns the connection, so
your agent can retrieve evidence between requests. Sending commands requires
UART TX to be enabled; reset and boot actions require configured control mappings.

When finished:

```bash
dutchmate stop
```

## Further information

- [Configuration and CLI workflows](docs/developer_guide.md) — also run `dutchmate --help`.
- [Debug Helper wiring and firmware](hardware/firmware/rp2350_debug_helper/README.md).
- [Milestone overview and validation boundaries](docs/development_status.md).
- [Contributing](CONTRIBUTING.md) and the [documentation index](docs/README.md).

## Licensing

Software, firmware and documentation use the [MIT License](LICENSE), unless
otherwise noted. DUTchMate-authored hardware design files under `hardware/pcb/`
use [CERN-OHL-P-2.0](LICENSES/CERN-OHL-P-2.0.txt). Legacy EAGLE and third-party
assets retain their existing terms; see [LICENSE.md](LICENSE.md) and
[third-party notices](THIRD_PARTY_NOTICES.md).

The DUTchMate name, logo and branding are excluded from these grants; they do
not authorize presenting derivative products as official DUTchMate products.
Contributions require DCO 1.1 sign-off; see [CONTRIBUTING.md](CONTRIBUTING.md).
