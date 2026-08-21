# Developer Guide

> Status: current implementation guide
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
  mcp_server/      Phase 2 MCP stdio adapter scaffold.

core/
  src/             Reusable Python library.

hardware/
  firmware/        RP2040/Zephyr firmware location.
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
| `apps/mcp_server/` | `dutchmate-mcp-server` | Phase 2 scaffold; runtime is not implemented. |

Current core modules:

| Module | Ownership |
|---|---|
| `backends` | Backend-neutral identity/contracts, Basic raw serial event/send adapter, and interim Enhanced wire adapters. |
| `device_connection` | Enhanced v1 protocol, framing, discovery, and synchronous transport. |
| `diagnostics.py` | Shared sanitized, UTF-8-safe, 1024-byte diagnostic projection. |
| `uart_capture` | Backend-independent bounded UART buffering by segment/channel, complete-line boundaries, and oversized-line descriptors. |
| `log_processing` | Case-sensitive bounded-literal detection with first raw-byte match offsets. |
| `session_store` | Filesystem sessions, crash-recoverable evidence units, bounded reconnect segments, stable paginated list/detail projections, bounded native UART replay, pattern/line-limit evidence, and discovery. |
| `gpio_config` | Control-channel mapping, validation, and accepted state. |
| `workflows` | Shared normalized-event capture and guarded reset/boot actions. |
| `runtime.py` | Service-facing state, active workflow coordination, and boot-test orchestration. |
| `validation.py` | Shared public input contracts and application validation errors. |

See `docs/software_architecture.md` for current data flow and ownership details.

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

## Current Surface

Service endpoints:

- `GET /status`
- `POST /dut/capture`
- `POST /dut/boot-test`
- `POST /gpio/mode`
- `POST /dut/reset`
- `POST /dut/boot-mode`

CLI commands:

- `dutchmate start`, `stop`, `devices [--all]`, and `status`
- `dutchmate capture --seconds <seconds>`
- `dutchmate boot-test --seconds <seconds>`
- `dutchmate gpio mode <channel> <role> <dut_signal> ...`
- `dutchmate dut reset`
- `dutchmate dut boot-mode <normal|bootloader>`
- `dutchmate sessions`, `session <session_id>`, and
  `logs [--session <session_id>] --last <lines>`
- `dutchmate wait <pattern> --timeout <seconds>`

The runtime performs finite transport-backed capture and reset-triggered
boot-test orchestration, with active-workflow conflict guards. Backend-neutral
contracts and shared event processing now exist; Enhanced wire messages are
translated only by the Enhanced backend adapter. The core capture workflow now
coordinates disconnect/resume deadlines and segment-bound source replacement;
service composition now retries the configured Basic port or validates an exact
Enhanced identity/hello before publishing a prepared replacement. Major
remaining Phase 1 areas are the full asynchronous Enhanced adapter, background
ingestion outside active workflows, retention, UART-send public workflows,
generic Enhanced control
actions, RP2040 firmware, and real HIL tests.

## Adding A Service Endpoint

1. Add or extend core behavior under `core/src/dutchmate_core/`.
2. Cover deterministic behavior with core unit tests.
3. Add request/response models in
   `apps/service/src/dutchmate_service/schemas.py`.
4. Register the route in `apps/service/src/dutchmate_service/app.py`.
5. Map expected failures in `apps/service/src/dutchmate_service/errors.py`.
6. Add service tests under `apps/service/tests/`.
7. Update documents that list the current endpoint surface.

Validation order and state transitions belong in core. Service handlers own
HTTP serialization, not a parallel behavior implementation.

## Adding A CLI Command

1. Add an HTTP helper in `apps/cli/src/dutchmate_cli/client.py`.
2. Add focused output formatting in the relevant CLI module.
3. Register the Typer command in `apps/cli/src/dutchmate_cli/main.py`.
4. Add CLI/client tests under `apps/cli/tests/`.
5. Update documents that list current commands.

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
Phase 1B rename to `uart_receive` and migration to generic channel actions must
be atomic across this set.

## Testing

Use focused tests while developing, then run the full suite:

```bash
uv run pytest tests/unit/protocol
uv run pytest tests/unit/uart_capture tests/unit/log_processing
uv run pytest tests/unit/session_store tests/unit/workflows tests/unit/runtime
uv run pytest apps/service/tests
uv run pytest apps/cli/tests
uv run pytest
```

For CLI-visible behavior, expected coverage is core unit behavior, service
request/response and error mapping, and CLI request/formatting behavior.
Hardware smoke tests validate physical integration after deterministic behavior
passes through fake backends.

## Documentation

- `README.md` is the entry point and current status summary.
- `docs/project_context.md` owns product architecture, scope, and roadmap.
- `docs/software_architecture.md` owns current code structure and migration
  boundaries.
- `docs/phase1_implementation_spec.md` owns Phase 1 requirements and done
  criteria.
- Focused contract documents own their named subsystem and are referenced
  rather than copied into broader documents.
- Use **current** only for runnable repository behavior and **target** or
  **planned** for unimplemented work.
- Update current endpoint/command lists in the same change as code.
- Keep links and protocol examples valid when moving or renaming content.
