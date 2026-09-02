# Developer Guide

> Scope: workspace layout, local development, package boundaries, and contribution patterns.

This guide is for contributors working on the current Python repository. Target
Phase 1 behavior is defined in `docs/phase1_implementation_spec.md` rather than
repeated here.

## Workspace

DUTchMate uses a `uv` workspace with one root lockfile. This keeps the core,
CLI, service, and MCP packages independently testable while resolving them from
one dependency set. Run package entrypoints from the repository root.

```text
apps/
  cli/             Human CLI; owns `dutchmate` and `dm`.
  service/         Local FastAPI Device Core Service.
  mcp_server/      MCP stdio delivery adapter.

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

See `docs/software_architecture.md` for module ownership and data flow.

## Local Setup

Requirements are Python 3.10+ and `uv`.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Run package commands from the repository root:

```bash
uv run --package dutchmate-cli dutchmate --help
uv run --package dutchmate-service dutchmate-service --help
```

Start and inspect the current local service:

```bash
uv run --package dutchmate-cli dutchmate start --backend enhanced
uv run --package dutchmate-cli dutchmate status
uv run --package dutchmate-cli dutchmate stop
```

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
- `apps/cli` calls the service over HTTP. It must not own serial transport.
- `apps/mcp_server` will call the same service in Phase 2. It must not own
  serial transport, session persistence, or AI logic.
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
