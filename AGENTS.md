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

## Graphify Usage

Graphify is an architectural navigation and impact-analysis tool. It is not the default mechanism for understanding every code change.

Use Graphify when the task involves:

* architecture or subsystem exploration;
* cross-module dependency or impact analysis;
* changes to shared interfaces, ports, or abstractions;
* significant multi-module refactoring;
* tracing relationships across architectural layers;
* understanding an unfamiliar subsystem;
* identifying architectural boundary violations.

Do not use Graphify by default for:

* localized implementation changes;
* isolated test failures;
* known symbols or literal reference searches;
* changes within a single well-understood module;
* dead-code removal after consumers have already been identified;
* formatting, configuration, comments, or documentation-only changes.

For straightforward code navigation, prefer direct source inspection and `rg`.

### Query Policy

When Graphify is appropriate:

1. Prefer one focused `graphify query`, `graphify path`, or `graphify explain` call.
2. Keep queries narrowly scoped to the architectural question being answered.
3. Prefer a modest query budget when sufficient.
4. Verify important Graphify relationships against actual source code and tests.
5. Do not repeatedly query Graphify during routine implementation once the relevant impact area is understood.

Do not read `graphify-out/graph.json` directly.

Do not read `graphify-out/GRAPH_REPORT.md` unless performing a broad architecture review or targeted Graphify queries are insufficient.

Avoid including generated `graphify-out/` artifacts in broad source searches unless they are specifically being inspected.

### Graph Updates

Run `graphify update .` only after meaningful structural changes such as:

* adding, removing, or moving modules;
* changing shared interfaces or ports;
* changing dependencies between architectural layers;
* significant multi-module refactoring.

Do not update Graphify after routine localized edits.

Run the update once near completion of the structural development slice rather than repeatedly during implementation.

## Development Workflow

Match development process and planning effort to the risk of the change. Do not apply heavyweight planning or workflow ceremony to every task.

### General Rule

Prefer the simplest workflow that preserves correctness.

For localized, well-specified changes:

* Inspect the relevant code and existing specification.
* Do not create a separate design document.
* Do not create a large implementation-plan document.
* State a short implementation approach when useful.
* Implement in small coherent changes.
* Run focused tests while developing.
* Run the required final validation before completion.

Use a structured workflow only when the change materially affects architectural boundaries, concurrency, ownership, lifecycle, reconnect behavior, persistence/schema compatibility, protocol compatibility, public interfaces, or multiple subsystems.

Do not redesign an established architecture unless the task explicitly requires it or a concrete correctness problem makes the existing design invalid.

### Existing Specifications Are Authoritative

Before proposing new architecture or creating new design documents:

* Check whether the required behavior is already defined in existing project specifications, architecture documents, protocol documents, or `development_status.md`.
* Reference existing normative documents instead of restating them.
* Do not create another design document when the required behavior is already specified.
* Do not repeat large amounts of existing specification content in implementation plans.

When continuing an existing implementation:

* Inspect `git status` and relevant diffs first.
* Understand the intent of existing in-progress changes.
* Preserve established architecture and conventions.
* Do not rewrite working changes merely because another implementation style is preferred.

## Planning Policy

Use a written implementation plan only for genuinely cross-cutting or high-risk changes.

A plan should normally:

* contain approximately 5–10 meaningful implementation steps;
* identify the components or files likely to change;
* identify important invariants and compatibility constraints;
* identify the critical tests or acceptance criteria;
* reference existing specifications rather than duplicating them;
* avoid large blocks of anticipated implementation code;
* avoid decomposing routine work into minute-by-minute steps.

For migration or cleanup work, prefer an inventory of affected consumers and compatibility paths over a large design document.

Example:

```text
Legacy component        Consumer(s)        Action
-------------------------------------------------
Old transport path      service A          migrate
Compatibility adapter   tests B/C          remove
Legacy reconnect path   none               delete
```

## Selective Skill Usage

Superpowers skills are optional tools, not the default workflow.

### systematic-debugging

Use `systematic-debugging` when:

* a failure is reproducible but its root cause is unclear;
* there is a race condition or timing-dependent failure;
* reconnect, UART, USB, persistence, or lifecycle behavior is inconsistent;
* an attempted fix does not explain the underlying failure.

Do not use systematic debugging for obvious, localized corrections where the cause is already known.

### test-driven-development

Use `test-driven-development` when changing behavior where regression risk matters, especially:

* state machines;
* concurrency and ownership behavior;
* reconnect semantics;
* protocol parsing;
* persistence invariants;
* externally visible behavior.

Do not manufacture failing tests purely to justify deleting clearly dead code or making mechanical changes.

For dead-code removal, existing coverage, reference search, and final validation are sufficient when behavior is unchanged.

### verification-before-completion

Use `verification-before-completion` for development slices before declaring them complete.

Completion claims must be backed by fresh validation evidence.

Run the smallest relevant tests during implementation and the complete required validation gate once before completion.

Do not repeatedly run the full suite after every small edit unless required to diagnose a failure.

### brainstorming

Use `brainstorming` only when a genuine design decision remains open, such as:

* introducing a new subsystem;
* choosing between materially different architectures;
* defining a new protocol or hardware/software boundary;
* resolving requirements with multiple viable designs.

Do not use brainstorming for migrations, cleanup, implementation of already-specified behavior, or routine bug fixes.

## Validation Strategy

During implementation:

1. Run focused tests for the code being changed.
2. Use targeted static analysis, searches, or diagnostics as needed.
3. Resolve failures before broadening validation.

Before completing a development slice:

* run the required full test suite;
* run Ruff or equivalent lint checks;
* run mypy or the project's required type checks;
* verify relevant stale/legacy references are removed;
* review the final diff;
* update architecture documentation when architecture actually changed;
* update `development_status.md` when project status changed;
* update Graphify when required by the repository's Graphify policy.

Do not claim completion when required validation has not been run or when failures remain.

## Token-Efficient Tool Usage

### RTK

When RTK (`rtk`) is available, prefer RTK-wrapped commands for supported development tools to reduce unnecessary terminal output sent to the model.

Examples:

```bash
rtk git status
rtk git diff
rtk git log
rtk pytest
rtk cargo test
rtk rg <pattern>
```

General rules:

* Prefer `rtk <command>` over the equivalent raw command when RTK supports it.
* Use RTK especially for commands that may produce large output, such as tests, Git diffs/logs, searches, linters, and build tools.
* Do not use RTK when exact, unfiltered command output is required for debugging or verification.
* If RTK output omits information needed to diagnose a problem, rerun the relevant command without RTK.
* Do not change command semantics merely to use RTK.
* Do not suppress errors or failures for the sake of reducing output.
* Validation and correctness take priority over token reduction.

### Communication

Keep progress updates and final responses concise and information-dense.

* Avoid repeating information already established in the conversation.
* Avoid narrating trivial implementation steps.
* Report important architectural decisions, assumptions, failures, and trade-offs.
* Include enough explanation to make non-obvious changes understandable.
* Preserve exact code, commands, identifiers, paths, error messages, and technical values when they matter.
* Do not sacrifice technical completeness or correctness merely to shorten a response.
