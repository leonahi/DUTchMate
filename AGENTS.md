# DUTchMate Engineering Constraints

## Architecture

DUTchMate's Device Core Service is a modular monolith built using
Ports-and-Adapters principles and lightweight domain modelling.

The repository is a monorepo containing:

- `core/`: shared domain, application, protocol, and adapter code
- `apps/service/`: Device Core Service and composition root
- `apps/cli/`: thin CLI delivery adapter
- `apps/mcp_server/`: thin MCP delivery adapter
- `hardware/`: firmware, protocol schemas, schematics, and validation assets

## Dependency Direction

- Application and domain policy must not depend on FastAPI, Typer, HTTP clients,
  serial libraries, filesystem details, or MCP frameworks.
- Delivery applications may depend on `dutchmate_core`.
- `dutchmate_core` must never import from `apps/`.
- External systems such as serial devices, filesystems, clocks, and service
  transports should be isolated behind clear boundaries when substitution or
  deterministic testing provides concrete value.
- Do not create interfaces or abstractions solely for architectural symmetry.

## Domain Modelling

- Prefer typed values, dataclasses, explicit state transitions, and validation
  close to the invariant they protect.
- Do not introduce aggregates, repositories, domain services, factories,
  commands, events, or other DDD patterns unless they solve a demonstrated
  domain or dependency problem.
- Avoid framework-shaped domain models.

## Source Structure

- Organize modules around cohesive responsibilities and reasons to change.
- File count and file length are signals, not architectural goals.
- Split a module when it owns multiple independently changing responsibilities.
- Merge modules only when they have no meaningful independent contract and are
  consistently changed, tested, and consumed together.
- Do not introduce one-class-per-file structure by default.
- Keep public APIs intentionally small; prefer private implementation helpers.
- Remove obsolete compatibility layers once their consumers have migrated.

## Refactoring

- Structural refactors must preserve externally observable behavior unless a
  behavior change is explicitly requested.
- Map callers, imports, persistence formats, and public exports before moving or
  deleting code.
- Do not combine architectural restructuring with unrelated feature changes.
- Refactor one subsystem at a time and keep each commit independently testable.
- Preserve session evidence formats and compatibility behavior unless a
  migration has been explicitly designed.

## Validation

Before completing a structural change, run:

- Ruff
- Mypy
- Full pytest suite
- `git diff --check`

Update architecture documentation when module ownership or dependency direction
changes.
