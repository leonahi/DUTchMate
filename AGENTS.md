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

## Development Status

- Read `docs/development_status.md` before selecting development work.
- `docs/development_status.md` is the only source for progress, active phase,
  completed slices, and the next step.
- Update its review date, current milestone, next step, checklist, and
  validation evidence in the same commit as each completed development slice.
  Reconcile its code-baseline reference after commits are created.
- Requirements, architecture, plans, and validation records must not maintain
  competing progress summaries or next-step lists.

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

When the user types `/graphify`, use the installed graphify skill or instructions before doing anything else.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- Dirty graphify-out/ files are expected after hooks or incremental updates; dirty graph files are not a reason to skip graphify. Only skip graphify if the task is about stale or incorrect graph output, or the user explicitly says not to use it.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).

## DUTchMate Graphify Usage Policy

Graphify is an architectural navigation and impact-analysis tool, not a
replacement for reading source code.

Use Graphify first when the task involves:
- architecture or subsystem exploration;
- cross-module dependency analysis;
- impact analysis before a refactor;
- tracing relationships between CLI, API, application, domain, and
  infrastructure layers;
- understanding an unfamiliar subsystem;
- identifying architectural boundary violations;
- changes to shared interfaces or abstractions.

Do not require Graphify for:
- small localized implementation changes;
- fixing an isolated failing test;
- literal text or symbol searches;
- changes confined to a single well-understood module;
- formatting, comments, or documentation-only changes.

For architectural decisions or refactors, treat Graphify results as navigation
evidence. Verify relevant relationships against the actual source code and
tests before changing interfaces or architecture.

Update the Graphify graph after meaningful structural changes such as:
- adding, removing, or moving modules;
- changing shared interfaces or ports;
- changing dependencies between architectural layers;
- significant multi-module refactoring.

Do not update the graph after every trivial localized edit.