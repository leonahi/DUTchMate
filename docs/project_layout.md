# Project Layout

> Status: initial scaffold
> Scope: monorepo structure for hardware, Python core, host apps, and tests.

## Python Tooling Decision

Use **uv workspaces** for Python.

Reasons:

- DUTchMate is a monorepo with multiple related Python packages.
- `core` should be testable independently from CLI, service, and MCP.
- Apps can depend on `dutchmate-core` as an editable workspace package.
- The workspace gets one lockfile, so CLI/service/MCP resolve against the same dependency set.
- `uv run --package <name>` supports running a specific package from the repo root.

Poetry remains a good single-package project tool, but it is a weaker fit here because DUTchMate needs first-class multi-package workspace behavior. PDM is also viable, but `uv` gives the best mix of speed, workspace support, and packaging workflow for this repo.

## Top-Level Layout

```text
apps/
  cli/             Human CLI package; owns the `dutchmate` and `dm` entrypoints.
  service/         Device Core Service package; owns the local FastAPI process.
  mcp_server/      Phase 2 MCP stdio adapter package.

core/
  src/             Reusable Python library code.
  tests/           Core unit tests.

hardware/
  firmware/        RP2040/Zephyr firmware.
  protocol/        Versioned host-device protocol schemas and examples.
  schematics/      Electrical design notes and future schematic files.

docs/              Durable design context and implementation specs.

tests/
  unit/            Cross-package unit tests.
  integration/     Service/API integration tests.
  fixtures/        Protocol streams and expected session outputs.
```

## Python Packages

| Path | Package | Purpose |
|---|---|---|
| `core/` | `dutchmate-core` | Protocol parsing, serial transport, session storage, workflows. |
| `apps/cli/` | `dutchmate-cli` | Human-facing command-line client. |
| `apps/service/` | `dutchmate-service` | FastAPI Device Core Service; current endpoints cover status, GPIO mode, reset, and boot-mode. |
| `apps/mcp_server/` | `dutchmate-mcp-server` | Phase 2 MCP adapter scaffold; runtime not implemented yet. |

## Current Core Modules

The Phase 1 host-side core currently contains:

| Module | Purpose |
|---|---|
| `device_connection` | v1 message models, parser, command encoders, and NDJSON stream parser. |
| `uart_capture` | Raw UART byte buffering, complete-line extraction, and UART capture processing. |
| `log_processing` | Case-sensitive keyword pattern detection on completed UART lines. |
| `session_store` | Filesystem session creation, incremental evidence writes, telemetry events, and summaries. |
| `workflows` | Mock capture recorders and guarded reset/boot action workflows. |
| `gpio_config` | GPIO mode configuration workflow/state for Debug Helper lines used as DUT control signals. |

Higher-level boot-test orchestration has not been implemented yet.

See `docs/software_architecture.md` for current dependency direction, module
responsibilities, and capture data flow.

See `docs/developer_guide.md` for local setup, contribution workflow, and
testing expectations.

## Common Commands

Install/sync the workspace:

```bash
uv sync
```

Run tests:

```bash
uv run pytest
```

Run linting:

```bash
uv run ruff check .
```

Run a package command:

```bash
uv run --package dutchmate-cli dutchmate --help
```

Generate or refresh the lockfile:

```bash
uv lock
```

`uv.lock` should be committed once generated.

## Boundary Rules

- `core` must not import CLI, service, MCP, or AI packages.
- `apps/cli` calls the Device Core Service API; it must not own serial transport directly.
- `apps/service` is intended to own the serial port at runtime by importing and orchestrating `core`; the current default runtime still uses an unavailable transport stub.
- `apps/mcp_server` will call the Device Core Service API when implemented; it must not import serial transport modules.
- `hardware/protocol/v1` is the contract between firmware and host parser tests.
