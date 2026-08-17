# Architecture Audit

> Date: 2026-08-17
> Baseline: `d534038 Enforce hardware evidence quotas`
> Scope: host-side Python production code, tests, package boundaries, public
> exports, compatibility surfaces, and current architecture documentation.

## Executive Conclusion

The repository does not have an excessive number of production files. It has
50 production Python files and approximately 8320 production lines, supported
by 43 test files and approximately 10250 test lines. Most small modules express
useful protocol, adapter, application, or delivery boundaries.

A broad file-merging exercise would increase coupling without materially
reducing complexity. The recommended cleanup is targeted:

1. split the `session_store` monolith behind its existing public facade;
2. establish one owner for capture lifecycle orchestration;
3. remove wire-protocol and filesystem construction from application policy;
4. retire test-only compatibility surfaces and redundant type aliases;
5. make the supported public API explicit;
6. align test placement and current-status documentation with reality.

No production code was moved, removed, or behaviorally changed during this
audit.

## Audit Method

The audit used:

- tracked-file and line-count inventories;
- Python import analysis across all four workspace packages;
- import-cycle analysis;
- public re-export and internal-reference searches;
- responsibility and call-site review of every production package;
- test-file size and placement review;
- current architecture, developer, Phase 1, and MCP documentation;
- recent co-change history from the last 20 commits;
- the existing Ruff, Mypy, and pytest baseline.

Neither `vulture` nor coverage tooling is installed. Dead-code findings are
therefore based on repository references and documented consumers, not on a
claim that an untracked third-party consumer cannot exist.

## What Is Already Healthy

- `dutchmate_core` does not import CLI, service, or MCP packages.
- Core contains no FastAPI, Typer, httpx, or MCP framework imports.
- There are no Python import cycles.
- FastAPI routes and Pydantic models remain in `apps/service`.
- Typer and HTTP client behavior remain in `apps/cli`.
- Basic and Enhanced UART input converge on normalized backend events before
  shared capture processing.
- UART line processing, pattern detection, and filesystem persistence are
  separate responsibilities.
- Domain modelling is lightweight: typed aliases, frozen dataclasses, explicit
  state, and validation are used without DDD ceremony.
- External serial dependencies are loaded only by concrete serial/discovery
  adapters.
- The service startup module acts as an identifiable composition root.
- The test-to-production ratio is healthy and the suite protects persistence,
  protocol, workflow, service, and CLI behavior.

## Ranked Findings

### A1 — High: `session_store/store.py` is a multi-responsibility monolith

Evidence:

- 1804 lines and 71 top-level or class definitions;
- owns public models, schema-v0/v1 compatibility, metadata construction and
  validation, lifecycle transitions, startup recovery, catalog reads, evidence
  serialization, quota admission, pattern projection, first-error selection,
  filesystem I/O, and timestamp formatting;
- changed in seven of the last 20 commits;
- its main test file is 1483 lines.

Decision: **split**, while keeping `SessionStore` as the stable public facade.

Recommended initial structure:

```text
session_store/
  __init__.py       intentional public exports
  models.py         public session/path/summary/recovery value types
  metadata.py       schema construction, parsing, validation, and projections
  evidence.py       exact evidence serialization and quota-unit preparation
  store.py          filesystem facade, lifecycle, recovery, and catalog actions
```

Do not create separate files for every model or helper. Recovery can remain in
`store.py` until it has an independently changing contract.

### A2 — High: application policy still depends on concrete adapters

Evidence:

- `DeviceCoreRuntime` imports `Path` and `SessionStore` and constructs the
  filesystem adapter when one is not injected;
- `workflows.capture` accepts the concrete `SessionStore` rather than a focused
  application-facing port;
- `DeviceCoreRuntime.record_hello` accepts the Enhanced wire-level
  `HelloMessage`, although the architecture document says only the Enhanced
  adapter should translate wire messages;
- `DeviceActionRunner` and `GpioConfigurator` encode protocol commands and
  inspect `CommandSuccessMessage` / `CommandErrorMessage` directly.

Decision: **restructure**, because these are concrete dependency problems where
ports provide deterministic value.

Recommended direction:

- let `apps/service/startup.py` construct and inject `SessionStore`;
- introduce one focused capture-session storage protocol owned by the capture
  application boundary, rather than a generic repository abstraction;
- make runtime connection updates consume normalized backend identity/snapshot
  values rather than `HelloMessage`;
- expose semantic device-control operations to GPIO/action workflows and keep
  NDJSON command/response translation in the Enhanced adapter.

Do not add repositories, aggregates, buses, factories, or interfaces for pure
functions. Introduce only the ports required to remove the concrete leaks above.

### A3 — High: capture lifecycle has more than one owner

Evidence:

- `DeviceCoreRuntime._run_capture_workflow` creates, finalizes, completes, and
  fails sessions;
- `workflows.capture.run_transport_capture` independently performs a similar
  lifecycle;
- the free function is used by tests but not by a production application;
- `CaptureRecorder.record_event` repeats quota-terminal handling for three
  event branches, with a fourth copy in `finalize`;
- capture, runtime, and session store are the three most frequently co-changed
  production modules in recent history.

Decision: **consolidate behavior**, not necessarily files.

Choose one application service as the lifecycle owner. Runtime should provide
locking, connection state, and action hooks; the capture application service
should own recorder creation, event-loop completion, terminal priority, and
failure mapping. Remove `run_transport_capture` after its Basic/integration
tests use the single production path.

### A4 — Medium: compatibility and fixture helpers are exposed as production API

Evidence:

- `workflows/enhanced_capture.py` describes itself as compatibility code;
- `CaptureStreamRecorder` and `run_mock_capture` are consumed only by tests and
  architecture documentation;
- `GpioModeRegistry.require_configured` is an explicit compatibility wrapper
  used by one compatibility test;
- `GpioRoleState` is an alias exported but not consumed;
- `DeviceCoreTransport`, `DeviceCommandTransport`, and `GpioCommandTransport`
  are aliases of the same `CommandTransport` and add names without distinct
  contracts.

Decision: **move/delete after migration**.

- Move Enhanced byte-chunk fixture composition into test helpers or test the
  normalized Enhanced adapter plus the shared application path directly.
- Migrate the one `require_configured` test and remove the wrapper.
- Remove unused aliases or replace them with genuinely semantic ports as part
  of A2.
- Update current-flow documentation in the same commits.

### A5 — Medium: supported public APIs are broader than actual application use

Evidence:

- package `__init__.py` files re-export large surfaces from backends,
  `device_connection`, GPIO, workflows, and session storage;
- production code generally imports the defining submodule directly;
- most barrel-import consumers are repository tests;
- compatibility helpers and aliases are included in `__all__`.

Decision: **define and trim**, but do not remove exports blindly.

Before moving modules, record which names are intentionally supported outside
the repository. Prefer a small stable facade for runtime and normalized backend
contracts. Tests for internal modules should import those modules directly
rather than accidentally defining a broad package API.

### A6 — Medium: session configuration contains accepted but inert settings

Evidence:

- CLI configuration parses `sessions.max_count` and `sessions.max_size_mb`;
- only `sessions.path` is passed when starting the service;
- service startup always constructs `SessionStore` with its default evidence
  budget;
- a configured `max_size_mb` is therefore validated but ignored;
- `max_count` has no retention implementation yet.

Decision: **wire or remove from the current surface**.

Wire `max_size_mb` through CLI lifecycle, service startup, and `SessionStore` in
one contract change. Keep `max_count` explicitly planned without accepting it as
effective configuration, or implement retention before advertising it as
active behavior.

Implemented: `max_size_mb` now reaches `SessionStore` as an exact byte budget,
and CLI configuration rejects `max_count` until retention is implemented.

### A7 — Medium: the largest tests mirror production monoliths

Evidence:

- `test_store.py`: 1483 lines;
- `test_device_core_runtime.py`: 879 lines;
- `test_capture_recorder.py`: 579 lines;
- `core/tests` is documented and configured as a test root but contains no
  tracked tests; core tests actually live under top-level `tests/unit`.

Decision: **split by behavior and standardize placement**.

Recommended test boundaries:

- session creation/lifecycle;
- UART evidence and quota;
- hardware/session evidence and quota;
- metadata projection/compatibility;
- runtime connection/control;
- runtime capture lifecycle;
- capture recorder;
- backend integration.

Keep top-level `tests/` as the core/cross-package test root and remove the empty
`core/tests` configuration/documentation entry, unless the team deliberately
chooses to move all core tests instead.

### A8 — Medium: current-status documentation has drifted

Evidence:

- the developer guide still lists native session quota enforcement as
  remaining despite the implemented UART, hardware, and final session-event
  admission paths;
- it documents `core/tests` as the core test location although it is empty;
- current data-flow documents still make test-only Enhanced compatibility
  helpers appear like production application flow.

Decision: **correct during the corresponding refactors**. Avoid a standalone
large wording rewrite that can drift again before module changes land.

### A9 — Low: CLI registration is concentrated but not fundamentally bloated

Evidence:

- `apps/cli/main.py` is 372 lines;
- most of it is declarative Typer parameter and command registration;
- command formatting and HTTP calls are already separated;
- service-error handling is repeated across commands;
- four formatter modules repeat a trivial private `_display` helper.

Decision: **restructure in place, do not merge formatter modules for size**.

Move command registration/handlers into the existing concern modules if CLI
growth makes `main.py` harder to navigate. A small shared command-error wrapper
may remove repetition. Do not centralize tiny display helpers unless a real
formatting contract emerges.

### A10 — Low: Phase 2 MCP is an intentional scaffold, not current complexity

Evidence:

- MCP production source is six lines plus package metadata;
- the CLI `mcp` command always reports that Phase 2 is not implemented;
- documentation explicitly labels the package as a scaffold;
- it contributes almost no code complexity, though it does expose a dead
  executable surface and workspace dependency.

Decision: **product decision, not architecture cleanup priority**.

Either retain the scaffold explicitly or remove the package and failing CLI
command until Phase 2 begins. Do not merge MCP into the service or CLI.

## Module Classification

| Area | Classification | Rationale |
|---|---|---|
| `backends/contracts.py` | Keep | Stable normalized boundary and lightweight domain values. |
| `backends/basic.py` | Keep; later internal split only if async work demands it | Cohesive Basic connection/event adapter despite its size. |
| `backends/enhanced.py` | Keep; replace interim synchronous pieces during reconnect work | Correct adapter ownership. |
| `backends/settings.py` | Keep | Config parsing and resolution change together today. |
| `device_connection/messages.py` | Keep | Wire DTOs have a distinct contract. |
| `device_connection/parser.py` | Keep | Protocol parsing is independently testable and schema-coupled. |
| `device_connection/commands.py` | Keep | Host encoding is the inverse wire adapter. |
| `device_connection/stream.py` | Keep | Framing state is separate from message validation. |
| `device_connection/transport.py` | Keep | Small, meaningful transport port/error boundary. |
| `device_connection/serial_transport.py` | Keep | Concrete Enhanced serial adapter. |
| `device_connection/discovery.py` | Keep | Separate host discovery adapter. |
| `device_connection/errors.py` | Keep | Small shared wire-error vocabulary. |
| `uart_capture/line_buffer.py` | Keep | Cohesive bounded state machine. |
| `uart_capture/processor.py` | Keep | Coordinates line and pattern derivation without persistence. |
| `log_processing/patterns.py` | Keep | Pure independently tested domain logic. |
| `gpio_config/config.py` | Keep | Cohesive project-config parser; reconsider only with broader config redesign. |
| `gpio_config/modes.py` | Keep; delete compatibility names | Owns accepted/rejected GPIO state. |
| `gpio_config/configurator.py` | Keep behavior; invert wire dependency | Valid workflow, wrong current adapter boundary. |
| `workflows/device_actions.py` | Keep behavior; invert wire dependency | Valid workflow, wrong current adapter boundary. |
| `workflows/capture.py` | Restructure | One lifecycle owner and focused storage port are needed. |
| `workflows/enhanced_capture.py` | Move/delete | Test-only compatibility surface. |
| `runtime.py` | Restructure | Retain service-facing state/locking; move composition and wire DTOs outward. |
| `session_store/store.py` | Split | Primary responsibility hotspot. |
| `validation.py` | Keep | Shared boundary validation is deliberate, not duplicate business logic. |
| Service `app/schemas/errors/startup/main` | Keep | Cohesive delivery, mapping, composition, and process responsibilities. |
| CLI `client/config/lifecycle/formatters` | Keep | Distinct delivery responsibilities. |
| CLI `main.py` | Reorganize if commands grow | Registration concentration, not domain complexity. |
| MCP scaffold | Keep or remove as one product decision | Do not merge with another deployable. |

## Code That Should Not Be Merged

The following small files are useful boundaries and should not be merged merely
to reduce file count:

- protocol messages, parser, framing stream, command encoder, and transport;
- UART line buffering and pattern detection;
- service HTTP schemas and error mapping;
- CLI HTTP client and process lifecycle;
- Basic and Enhanced backend adapters;
- MCP and service delivery applications.

Their responsibilities, dependencies, and tests are independently meaningful.

## Recommended Refactoring Sequence

Each numbered item should be independently reviewed, validated, and committed.

1. **Add architecture enforcement tests.** Check that core never imports apps or
   delivery frameworks. Add narrow temporary allowlists for the concrete leaks
   identified in A2, then remove allowlist entries as boundaries improve.
   Implemented in `tests/architecture/test_dependencies.py`; its exception set
   must shrink as A2/A4 refactors land and must never grow without an explicit
   architecture decision.
2. **Split oversized tests by behavior.** This lowers refactoring risk without
   changing production behavior.
3. **Split `session_store/store.py` behind the unchanged facade.** Move models,
   metadata/schema code, and evidence serialization without changing persisted
   bytes or public responses.
4. **Make capture lifecycle single-owner.** Consolidate runtime/free-function
   behavior, centralize quota-terminal handling, and migrate Basic integration
   coverage to the production path.
5. **Move composition and protocol translation outward.** Inject session
   storage from service startup, normalize hello/connection updates in the
   adapter, and introduce semantic device-control operations.
6. **Remove compatibility/test-only surfaces and trim exports.** Do this only
   after callers and intended external API are documented.
   Implemented by moving Enhanced byte-chunk composition into test support,
   removing obsolete GPIO compatibility names, defining the runtime and
   normalized-backend facades, and reducing application adapter exceptions to
   an empty set.
7. **Resolve inert session configuration.** Wire effective limits or remove
   them from the accepted current configuration surface.
   Implemented by wiring `max_size_mb` end to end and rejecting `max_count`.
8. **Reorganize CLI registration only if still useful.** Reuse existing concern
   modules; do not optimize for fewer files.
9. **Update architecture/developer/current-status documentation.** Reflect the
   final module map and remove obsolete migration descriptions.
10. **Resume feature work.** Persistence durability/fault handling remains the
    recommended next functional increment after the structural work is stable.

## Refactoring Guardrails

- Preserve schema-v0 read compatibility and schema-v1 persisted bytes.
- Preserve public HTTP and CLI output unless explicitly versioned.
- Do not combine a module move with new feature behavior.
- Use the existing full test suite after every structural commit.
- Add characterization tests before changing a boundary that is not already
  directly covered.
- Prefer a small concrete improvement over introducing a general architecture
  framework.
