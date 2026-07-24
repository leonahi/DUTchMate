# DUTchMate

DUTchMate is an AI-assisted embedded debugging system. A small RP2040-based Debug Helper captures real DUT evidence, while host-side Python services expose structured debug workflows to humans and coding agents.

## Repository Layout

This is a monorepo containing hardware, protocol contracts, core Python libraries, and host apps.

```text
apps/
  cli/          Human command-line interface.
  service/      Device Core Service.
  mcp_server/   MCP adapter for coding agents.

core/           Reusable Python core library.
hardware/       Firmware, protocol schemas, and schematics.
docs/           Project context and implementation specs.
tests/          Cross-package tests and fixtures.
```

See `docs/project_layout.md` for package boundaries and tooling details,
`docs/software_architecture.md` for the current host-side Python architecture,
`docs/developer_guide.md` for contribution workflow, and
`docs/dutchmate_hardware_architecture.md` for the proposed voltage-domain
GPIO/UART interface.

## Python Tooling

Use `uv`.

```bash
uv sync
uv run pytest
uv run ruff check .
```

The workspace is defined in `pyproject.toml`. Commit `uv.lock` once generated.

## Current Implementation Status

The current codebase contains the first host-side Phase 1 core pieces plus a
local FastAPI service shell and a CLI HTTP client. It does not yet include real
serial-port integration, RP2040 firmware, long-running capture endpoints, log
retrieval endpoints, session-listing endpoints, or the Phase 2 MCP server.

Implemented in `core/src/dutchmate_core/`:

```text
device_connection/   v1 protocol models, parsers, command encoders, NDJSON stream parsing
uart_capture/        UART byte buffering, complete-line extraction, capture processing
log_processing/      Keyword pattern detection on completed UART lines
session_store/       Filesystem-backed sessions, UART evidence, telemetry, summaries
workflows/           Mock capture recorders and guarded reset/boot action workflows
gpio_config/         Hardware GPIO mapping validation plus reset/boot mode state
```

Implemented in `apps/`:

```text
service/      FastAPI app with GET /status, POST /gpio/mode,
              POST /dut/reset, and POST /dut/boot-mode.
cli/          `dutchmate`/`dm` commands for start, stop, status,
              `gpio mode`, `dut reset`, and `dut boot-mode`.
mcp_server/   Package scaffold only; MCP runtime is not implemented yet.
```

The current host-side capture path is:

```text
NDJSON bytes
  -> NdjsonStreamParser
  -> parse_device_message
  -> CaptureStreamRecorder
  -> UartCaptureProcessor
  -> PatternDetector
  -> SessionStore
  -> SessionSummary
```

Sessions are written under `.dutchmate/sessions/<session_id>/` and include:

```text
metadata.json
uart_raw.log
uart_events.jsonl
hardware_events.jsonl
detected_patterns.json
```

Useful focused test command while Phase 1 core is being built:

```bash
uv run pytest tests/unit/gpio_config tests/unit/workflows tests/unit/session_store tests/unit/log_processing tests/unit/uart_capture tests/unit/protocol
```

Known next areas:

- Real command transport and higher-level boot-test workflow.
- Real serial-port integration in the Device Core Service.
- Capture/log/session HTTP endpoints and matching CLI commands.
- Startup application of `.dutchmate/config.toml` hardware mappings.
- Phase 2 MCP server implementation.
- RP2040 firmware implementation.
