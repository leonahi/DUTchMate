# Developer Guide

> Scope: workspace layout, local development, package boundaries, and contribution patterns.

This guide is for contributors working on the current Python repository. Target
Phase 1 behavior is defined in `docs/phase1_implementation_spec.md` rather than
repeated here.

## Workspace

DUTchMate uses a `uv` workspace with one root lockfile. This keeps the core,
CLI, service, MCP, and Debug Agent packages independently testable while
resolving them from one dependency set. Run package entrypoints from the
repository root.

```text
apps/
  cli/             Human CLI; owns `dutchmate` and `dm`.
  service/         Local FastAPI Device Core Service.
  mcp_server/      MCP stdio delivery adapter.
  debug_agent/     Optional bounded evidence assembly and analysis adapters.

core/
  src/             Reusable Python library.

hardware/
  firmware/        RP2350/Pico 2 Zephyr firmware location.
  protocol/        Versioned wire schemas and examples.
  schematics/      Electrical design notes and schematic files.
  validation/      Hardware acceptance records and unrun templates.

docs/              Architecture, contracts, plans, and guides.

tests/
  unit/            Core and cross-package unit tests.
  integration/     Service/API integration tests.
  fixtures/        Protocol streams and expected session outputs.
```

Python packages:

| Path | Package | Purpose |
|---|---|---|
| `core/` | `dutchmate-core` | Protocol, capture, GPIO, sessions, runtime, and workflows. |
| `apps/cli/` | `dutchmate-cli` | Human-facing HTTP client and process commands. |
| `apps/service/` | `dutchmate-service` | FastAPI service and selected-serial ownership. |
| `apps/mcp_server/` | `dutchmate-mcp-server` | MCP `2026-07-28` stdio delivery adapter and Device Core HTTP client. |
| `apps/debug_agent/` | `dutchmate-debug-agent` | Optional bounded Debug Agent context, local Ollama adapter, and reviewed analysis CLI; no provider enabled by default. |

See `docs/software_architecture.md` for module ownership and data flow.

## Local Setup

Requirements are Python 3.10+ and `uv`.

```bash
uv sync --all-packages
uv run pytest
uv run ruff check .
```

Run package commands from the repository root:

```bash
uv run --package dutchmate-cli dutchmate --help
uv run --package dutchmate-service dutchmate-service --help
uv run --package dutchmate-mcp-server dutchmate-mcp --help
uv run --package dutchmate-debug-agent dutchmate-debug --help
```

To analyze a completed native session with a locally running Ollama model,
first review the manifest returned by `preview`. Then pass its
`manifest_digest` to `analyze` using the same arguments. Both commands read
selected sessions through `SessionStore`; `preview` does not call the model.

```bash
uv run --package dutchmate-debug-agent dutchmate-debug preview \
  --session-id SESSION_ID --provider ollama --model MODEL_ID
uv run --package dutchmate-debug-agent dutchmate-debug analyze \
  --session-id SESSION_ID --provider ollama --model MODEL_ID \
  --approved-digest MANIFEST_DIGEST
```

Use `--session-root` for a nondefault session directory, repeat `--session-id`
for additional sessions, and pass `--context-file` only for an explicit,
validated Coding Agent context JSON package. A changed session or model
requires a new preview. Ollama is reached at `http://127.0.0.1:11434`; remote
URLs are rejected by the adapter. Analysis failures return an error without a
partial report or provider fallback.
The adapter requests an 8,192-token context, disables model thinking, and caps
generation at 2,048 tokens; responses stopped by that cap are rejected as
incomplete. Choose a local model that supports Ollama structured output and
fits the selected evidence within that context.

`dutchmate-debug` is a host-facing CLI, not an MCP server. A coding agent in
VS Code, Claude Code, or another terminal-capable host invokes the same command;
there is no host-specific Debug Agent registration. Ollama is optional for the
rest of the coding workflow: `preview` does not contact it, and the coding agent
may skip `analyze` when no local model is installed. The MCP registrations below
expose Device Core tools and are independent of Debug Agent analysis.

Start and inspect the current local service:

```bash
uv run --package dutchmate-cli dutchmate start --backend enhanced
uv run --package dutchmate-cli dutchmate status
uv run --package dutchmate-cli dutchmate stop
```

Run the MCP stdio adapter after starting the Device Core Service:

```bash
uv run --package dutchmate-cli dutchmate mcp
uv run --package dutchmate-cli dutchmate mcp \
  --service-url http://127.0.0.1:2040 \
  --log-level info
```

`DUTCHMATE_SERVICE_URL` supplies the service URL when `--service-url` is
omitted. The command replaces the CLI process with the separately packaged
`dutchmate-mcp` executable so stdin and stdout remain dedicated to MCP stdio;
process logs go to stderr.

### Register MCP with a coding agent

Install the workspace with `uv sync --all-packages`, start the Device Core
Service separately, then resolve the absolute launcher path with
`realpath .venv/bin/dutchmate`.
Use that absolute path in a host that does not inherit the shell's virtual
environment. The launcher finds its sibling `dutchmate-mcp` executable in the
same environment. Each host launches its own stdio process; there is no MCP
HTTP endpoint to configure.

For [VS Code](https://code.visualstudio.com/docs/agents/reference/mcp-configuration),
put this in `.vscode/mcp.json` and replace the example command path with the
resolved path on that machine:

```json
{
  "servers": {
    "dutchmate": {
      "type": "stdio",
      "command": "/absolute/path/to/DUTchMate/.venv/bin/dutchmate",
      "args": ["mcp"],
      "env": {
        "DUTCHMATE_SERVICE_URL": "http://127.0.0.1:2040"
      }
    }
  }
}
```

For [Claude Code](https://code.claude.com/docs/en/mcp), register the same
absolute launcher as a local stdio server:

```bash
claude mcp add --transport stdio dutchmate -- \
  /absolute/path/to/DUTchMate/.venv/bin/dutchmate mcp
```

The default service URL is `http://127.0.0.1:2040`. For a different address,
add `--service-url URL` after `mcp` in either registration. A host can list the
nine fixed tools while Device Core is stopped; calls that need the service then
return structured errors.

`dutchmate start` requires `--backend basic|enhanced` or `[backend].mode`.
Basic also requires an explicit/configured serial port and opens it directly as
validated 8-N-1 UART without waiting for a DUTchMate `hello`. Enhanced accepts
an explicit port or auto-selects one metadata-hinted DUTchMate candidate;
multiple candidates require an explicit port, while no candidate starts the
service disconnected in Enhanced mode.

Use `uv lock` after dependency declarations change. Commit the shared
`uv.lock` update with those declarations.

## Package Boundaries

- `core` contains reusable protocol, capture, GPIO, workflow, runtime, and
  session logic. It must not import CLI, service, MCP, or AI packages.
- `apps/service` composes `core`, owns the selected serial connection, and
  exposes HTTP. Endpoint handlers remain thin.
- `apps/cli` calls the service over HTTP and launches the separately packaged
  MCP executable without importing it. It must not own serial transport.
- `apps/mcp_server` calls the same service over HTTP. It must not own
  serial transport, session persistence, or AI logic.
- `apps/debug_agent` assembles bounded native session context through `core`
  query APIs. Provider adapters stay in this package and are disabled by
  default; Device Core does not depend on it.
- `hardware/protocol/v1` is the Enhanced firmware/host wire contract. Its
  schemas, examples, parser/encoder models, tests, and firmware change together.

## Adding A Service Endpoint

1. Add or extend core behavior under `core/src/dutchmate_core/`.
2. Cover deterministic behavior with core unit tests.
3. Add request/response models in
   `apps/service/src/dutchmate_service/schemas.py`.
4. Register the route in `apps/service/src/dutchmate_service/app.py`.
5. Map expected failures in `apps/service/src/dutchmate_service/errors.py`.
6. Add service tests under `apps/service/tests/`.
7. Update the owning contract and `docs/development_status.md` when the slice
   changes milestone progress.

Validation order and state transitions belong in core. Service handlers own
HTTP serialization, not a parallel behavior implementation.

## Adding A CLI Command

1. Add an HTTP helper in `apps/cli/src/dutchmate_cli/client.py`.
2. Add focused output formatting in the relevant CLI module.
3. Register the Typer command in `apps/cli/src/dutchmate_cli/main.py`.
4. Add CLI/client tests under `apps/cli/tests/`.
5. Update the owning contract and `docs/development_status.md` when the slice
   changes milestone progress.

Preserve service errors. When the service is unavailable, commands fail with:

```text
Error: Device Core Service is not running. Run 'dutchmate start' first.
```

## Protocol Changes

Update these as one coherent change:

- `hardware/protocol/v1/*.schema.json`
- `hardware/protocol/v1/examples/*.json`
- `core/src/dutchmate_core/device_connection/messages.py`
- `core/src/dutchmate_core/device_connection/parser.py`
- `core/src/dutchmate_core/device_connection/commands.py`, when commands change
- protocol parser, encoder, and canonical-example tests
- firmware handling, once firmware exists

Do not accept fields in code that are absent from schemas and examples. The
canonical Enhanced receive capability is `uart_receive`; do not reintroduce a
legacy wire alias. The canonical Enhanced control actions are `pulse_control`
and `set_control_state`; do not reintroduce role-specific wire actions.
`configure_gpio_mode` carries only channel and electrical behavior; keep host
role and DUT-signal metadata out of firmware commands.

## Testing

Use focused tests while developing, then run the full suite:

```bash
uv run pytest tests/unit/protocol
uv run pytest tests/unit/uart_capture tests/unit/log_processing
uv run pytest tests/unit/session_store tests/unit/workflows tests/unit/runtime
uv run pytest apps/service/tests
uv run pytest apps/cli/tests
uv run pytest apps/mcp_server/tests
uv run pytest
```

For CLI-visible behavior, expected coverage is core unit behavior, service
request/response and error mapping, and CLI request/formatting behavior.
Hardware smoke tests validate physical integration after deterministic behavior
passes through fake backends.

## Documentation

- `README.md` is the short repository entry point.
- `docs/development_status.md` is the only progress tracker and next-step queue.
- `docs/project_context.md` owns durable product scope, safety, invariants, and
  phase definitions.
- `docs/software_architecture.md` owns code structure and dependency boundaries.
- `docs/phase1_implementation_spec.md` owns Phase 1 requirements and done
  criteria.
- Focused contract documents own their named subsystem and are referenced
  rather than copied into broader documents.
- Only `docs/development_status.md` may contain progress markers, completed
  slices, or the next implementation step.
- Keep links and protocol examples valid when moving or renaming content.
