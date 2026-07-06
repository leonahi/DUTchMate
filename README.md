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

See `docs/project_layout.md` for package boundaries and tooling details.

## Python Tooling

Use `uv`.

```bash
uv sync
uv run pytest
uv run ruff check .
```

The workspace is defined in `pyproject.toml`. Commit `uv.lock` once generated.
