# DUTchMate

DUTchMate is an AI-assisted embedded debugging system. It receives real DUT
evidence through one selected device backend, stores structured debug sessions,
and exposes deterministic workflows to humans and coding agents.

Phase 1 supports two mutually exclusive backends:

- **Basic:** a user-selected generic TTL/logic-level USB-to-UART adapter for
  UART receive and optional UART send.
- **Enhanced:** an RP2040 DUTchMate Debug Helper for UART receive/send,
  device-side timestamps, buffer telemetry, and generic `CTRLn` control.

Both use one shared host processing and session pipeline. Hybrid operation is
not supported.

## Development

Always resume work from [`docs/development_status.md`](docs/development_status.md).
It is the only source for the active phase, completed work, and next step.

Durable requirements and architecture are intentionally separate from progress:

- [`docs/phase1_implementation_spec.md`](docs/phase1_implementation_spec.md)
  defines Phase 1 behavior and acceptance criteria.
- [`docs/software_architecture.md`](docs/software_architecture.md) defines code
  ownership and dependency direction.
- [`docs/developer_guide.md`](docs/developer_guide.md) defines setup, commands,
  and contribution workflow.

## Quick Start

Requirements are Python 3.10+ and `uv`.

```bash
uv sync
uv run pytest
uv run ruff check .
```

Run the CLI from the repository root:

```bash
uv run --package dutchmate-cli dutchmate --help
uv run --package dutchmate-cli dutchmate start --backend enhanced
uv run --package dutchmate-cli dutchmate status
uv run --package dutchmate-cli dutchmate stop
```

## Repository

```text
apps/          CLI, Device Core Service, and Phase 2 MCP package.
core/          Reusable protocol, capture, GPIO, session, and workflow logic.
hardware/      Firmware, protocol schemas/examples, schematics, and validation.
docs/          Architecture, implementation contracts, plans, and guides.
tests/         Cross-package unit tests, integration tests, and fixtures.
```

The repository is a `uv` workspace with one committed `uv.lock`.

## Documentation

| Document | Canonical purpose |
|---|---|
| `docs/development_status.md` | Only progress tracker: active phase, next step, completed work, and ordered queue. |
| `docs/project_context.md` | Durable product scope, safety, invariants, and phase definitions. |
| `docs/phase1_implementation_spec.md` | Normative Phase 1 backend/API/session/protocol requirements, tests, and done criteria. |
| `docs/software_architecture.md` | Python data flow, module ownership, and dependency boundaries. |
| `docs/developer_guide.md` | Workspace layout, setup, package boundaries, and contribution workflow. |
| `hardware/schematics/revision_a.md` | Revision A voltage-domain hardware, pin map, BOM, and validation checklist. |
| `docs/gpio_configuration_semantics.md` | Control-channel identifiers, electrical modes, state, workflows, and reporting. |
| `docs/reconnect_session_semantics.md` | Reconnect, segment, timestamp, resume, and restart behavior. |
| `docs/ring_buffer_sizing_plan.md` | Phase 1B buffer baseline, telemetry, and validation method. |
| `hardware/validation/phase1_ring_buffer.md` | Ring-buffer measurements and final empirical decision record. |
| `docs/mcp_integration_plan.md` | Phase 2 stateless MCP `2026-07-28` transport, tool set, responses, and tests. |
| `docs/debug_agent_context_contract.md` | Phase 4 bounded context, provider boundary, and report contract. |

`hardware/protocol/v1/` is the canonical Enhanced host-device wire contract.
Its schemas, examples, host models, tests, and firmware handling must change
together.
