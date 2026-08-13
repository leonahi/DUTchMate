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

## Current Status

The repository currently contains the first host-side Phase 1 foundation:

- Enhanced v1 NDJSON schemas, examples, parser, command encoders, discovery,
  and synchronous serial transport
- exact UART byte preservation, complete-line reconstruction, and keyword
  pattern detection
- filesystem sessions, incremental evidence writes, summaries, and discovery
- GPIO control-channel configuration state and guarded reset/boot actions
- finite capture and reset-triggered boot-test orchestration
- FastAPI endpoints and CLI commands for service lifecycle, device listing,
  status, capture, boot-test, GPIO mode, reset, and boot mode

The normalized backend package, Basic adapter, background ingestion/reconnect,
versioned session lifecycle and retention, bounded log/session retrieval,
wait-pattern, UART-send service/CLI exposure, generic Enhanced control actions,
RP2040 firmware, MCP runtime, and HIL validation are not implemented yet.

The ordered Phase 1 backlog and acceptance criteria are in
`docs/phase1_implementation_spec.md`.

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
uv run --package dutchmate-cli dutchmate start
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
| `docs/project_context.md` | Product architecture, scope, safety, roadmap, and known limitations. |
| `docs/phase1_implementation_spec.md` | Normative Phase 1 order, backend/API/session/protocol requirements, tests, and done criteria. |
| `docs/software_architecture.md` | Current Python data flow, module ownership, and migration boundaries. |
| `docs/developer_guide.md` | Workspace layout, setup, package boundaries, and contribution workflow. |
| `docs/dutchmate_hardware_architecture.md` | Revision A voltage-domain hardware, pin map, BOM, and validation checklist. |
| `docs/gpio_configuration_semantics.md` | Control-channel identifiers, electrical modes, state, workflows, and reporting. |
| `docs/reconnect_session_semantics.md` | Reconnect, segment, timestamp, resume, and restart behavior. |
| `docs/ring_buffer_sizing_plan.md` | Phase 1B buffer baseline, telemetry, and validation method. |
| `hardware/validation/phase1_ring_buffer.md` | Measurement record; currently an unvalidated template. |
| `docs/mcp_integration_plan.md` | Phase 2 MCP transport, tool set, responses, and tests. |
| `docs/debug_agent_context_contract.md` | Phase 4 bounded context, provider boundary, and report contract. |

`hardware/protocol/v1/` is the canonical Enhanced host-device wire contract.
Its schemas, examples, host models, tests, and firmware handling must change
together.
