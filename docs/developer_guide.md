# Developer Guide

> Status: current implementation guide
> Scope: local development workflow, package boundaries, and contribution patterns.

This guide is for contributors working on the current Python workspace. It
describes what exists now, not the full Phase 1 roadmap.

## Local Setup

DUTchMate uses a `uv` workspace with one lockfile at the repository root.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Run package entrypoints from the repository root:

```bash
uv run --package dutchmate-cli dutchmate --help
uv run --package dutchmate-service dutchmate-service --help
```

The current service can be started through the CLI:

```bash
uv run --package dutchmate-cli dutchmate start
uv run --package dutchmate-cli dutchmate status
uv run --package dutchmate-cli dutchmate stop
```

Use `dutchmate devices` to inspect detected serial ports. `dutchmate start`
uses an explicit `--serial-port` when provided, otherwise it auto-selects one
DUTchMate candidate. Multiple candidates require `--serial-port`; no candidates
starts the service in a disconnected state.

Candidate matching currently depends on serial metadata containing
`DUTchMate`. Fixed USB VID/PID matching can be added after the firmware USB
identity is finalized.

## Repository Boundaries

Keep dependencies flowing in one direction:

- `core` contains reusable protocol, capture, GPIO, workflow, runtime, and
  session logic. It must not import CLI, service, MCP, or AI packages.
- `apps/service` exposes selected `core` behavior over FastAPI. It owns runtime
  orchestration and the selected serial port.
- `apps/cli` is a thin HTTP client for the Device Core Service. It must not
  open serial ports or import low-level transport code.
- `apps/mcp_server` is a Phase 2 scaffold. When implemented, it should call the
  Device Core Service API and avoid direct serial/protocol ownership.
- `hardware/protocol/v1` is the host-device contract. Protocol changes require
  schemas, examples, parser/encoder tests, and firmware handling to move
  together.

## Current Implemented Surface

Current service endpoints:

- `GET /status`
- `POST /dut/capture`
- `POST /dut/boot-test`
- `POST /gpio/mode`
- `POST /dut/reset`
- `POST /dut/boot-mode`

Current CLI commands:

- `dutchmate start`
- `dutchmate stop`
- `dutchmate devices [--all]`
- `dutchmate status`
- `dutchmate capture --seconds <seconds>`
- `dutchmate boot-test --seconds <seconds>`
- `dutchmate gpio mode <channel> <role> <dut_signal> --mode <mode> --active-level <level>`
- `dutchmate dut reset`
- `dutchmate dut boot-mode <normal|bootloader>`

The core runtime implements finite transport-backed capture plus reset-triggered
boot-test orchestration and rejects overlapping hardware-changing operations
with `capture_active`. Boot-test first-error extraction, log retrieval,
wait-pattern, UART-send, session-listing HTTP/CLI exposure, background serial
ingestion/reconnect, RP2040 firmware, and MCP runtime are not implemented yet.

## Adding a Service Endpoint

Use this path for new HTTP behavior:

1. Add or extend core behavior first, usually under `core/src/dutchmate_core/`.
2. Cover the core behavior with unit tests under `tests/unit/...`.
3. Add request/response models or serializers in
   `apps/service/src/dutchmate_service/schemas.py`.
4. Register the route in `apps/service/src/dutchmate_service/app.py`.
5. Map expected exceptions in `apps/service/src/dutchmate_service/errors.py`.
6. Add service tests under `apps/service/tests/`.
7. Update docs that list current endpoints.

Keep endpoint handlers thin. Validation and state transitions should live in
core or in small service serialization helpers, not as inline route logic.

## Adding a CLI Command

Use this path after the service endpoint exists:

1. Add an HTTP client helper in `apps/cli/src/dutchmate_cli/client.py`.
2. Add output formatting in a focused module such as `status.py`, `gpio.py`, or
   `dut.py`.
3. Register the Typer command in `apps/cli/src/dutchmate_cli/main.py`.
4. Add CLI/client tests under `apps/cli/tests/`.
5. Update docs that list current commands.

The CLI should preserve service error messages. If the service cannot be
reached, commands should fail with:

```text
Error: Device Core Service is not running. Run 'dutchmate start' first.
```

## Protocol Changes

For host-device protocol changes, update all of these in the same change:

- `hardware/protocol/v1/*.schema.json`
- `hardware/protocol/v1/examples/*.json`
- `core/src/dutchmate_core/device_connection/messages.py`
- `core/src/dutchmate_core/device_connection/parser.py`
- `core/src/dutchmate_core/device_connection/commands.py`, when host commands change
- protocol parser/encoder/example tests under `tests/unit/protocol/`
- firmware handling, once firmware exists

Do not add protocol fields that are accepted by code but absent from schemas or
examples.

## Test Expectations

Use focused tests while developing, then run the full suite before committing:

```bash
uv run pytest tests/unit/protocol
uv run pytest apps/service/tests
uv run pytest apps/cli/tests
uv run pytest
```

For behavior exposed through the CLI, expected coverage is:

- core unit tests for deterministic behavior
- service tests for HTTP request/response and error mapping
- CLI tests for request shape, formatting, and unavailable-service behavior

Hardware smoke tests are future work and should not be the first place workflow
correctness is established.

## Documentation Rules

Keep docs explicit about implementation state:

- Use "current" for runnable behavior in this repository.
- Use "target" or "planned" for Phase 1/Phase 2 behavior that is not
  implemented.
- Update command and endpoint lists in the same change that changes code.
- Keep `docs/project_context.md` broad and roadmap-oriented.
- Keep `README.md`, `docs/software_architecture.md`, and this guide aligned
  with the current implementation.
