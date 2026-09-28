# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 2 session persistence
> implemented; Stage 3 is next
> Repository baseline reviewed: `a0f38618f8c18d37792088435ee926e80a597193`
> on 2026-09-28
> Stage 2 working tree: uncommitted
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 2 implements deterministic schema-v2 session
  creation, mutation, rollover, recovery, bounded retrieval/replay,
  baseline/comparison, and retention while preserving v0/v1 readers. The Stage
  2 review findings for rollover ownership, record rebasing, stable retrieval,
  rollover retention/lifecycle evidence, terminal ownership cleanup,
  cross-rollover attempt/result matching (including crash recovery), bounded
  operation-ID collision handling, and consistent operation-count projections
  are resolved.
- **Implementation status:** The Phase 1 v2 migration is **partially
  implemented through Stage 2 only**. Runtime ownership still creates v1
  sessions and retains the existing finite workflows and idle drain/discard
  behavior. The authoritative continuous recorder, Monitor/Interact,
  follow/console, and release/reacquire are not implemented.
- **Historical evidence:** Existing Basic, Enhanced, firmware, ring-buffer, and
  HIL results remain valid evidence for the physical/backend behavior they tested.
  They do not establish the new continuous ambient recording, schema-v2,
  Monitor, Interact, follow/console, or release/reacquire requirements.
- **Next step:** Execute migration **Stage 3 only**: introduce the authoritative
  continuous recorder and switch runtime session ownership to schema v2. Do not
  begin Stage 4 Monitor behavior in that slice.
- **Open blockers:** No contradiction requiring a new design decision was found
  between the two normative documents. Previously recorded Revision A physical
  evidence gaps remain deferred acceptance work for Stage 8; they do not change
  the Stage 3 scope.

Update the review date, current milestone, next step, checklist, and concise
validation result in the same commit as each completed development slice. Add
detailed completed-slice and dated validation evidence to
`docs/development_history.md`; do not create another progress tracker.

## Phase 1 v2 Baseline

The approved Phase 1 contract changes the product semantics, so completion under
the earlier contract cannot be carried forward as current Phase 1A/1B acceptance.
The implementation starts from proven components, but target completion must be
demonstrated again against the new normative done criteria.

| Area | Current baseline | Phase 1 v2 status |
|---|---|---|
| Basic and Enhanced physical adapters | Existing backend, protocol, firmware, and HIL evidence is reusable | Historical evidence only; final v2 acceptance remains open |
| DUT Profile and effective serial provenance | One immutable resolved profile owns backend, selector/topology, UART policy, DTR/RTS request, GPIO config, projection, and digest | Stage 1 complete; exposed through runtime/service/CLI status without v2 storage |
| Native session schema v2 | Deterministic v2 store/recovery/retrieval/retention is implemented; runtime ownership still writes v1 | Stage 2 complete; runtime adoption waits for Stage 3 |
| Continuous ambient evidence recording | Current idle path drains/discards rather than recording all admissible UART | Not implemented |
| Monitor and Interact | Existing capture/wait/send workflows use pre-v2 semantics | Not implemented |
| Follow and console | Target durable-cursor views do not exist | Not implemented |
| Release and reacquire | Target explicit ownership handoff does not exist | Not implemented |
| MCP target-contract migration | Existing MCP integration exposes pre-v2 service semantics | Deferred until Phase 1 CLI acceptance |

Historical sessions and validation records must not be rewritten as though they
never existed. Schema-v0/v1 evidence remains read-only compatibility data under
the new contract.

## Migration Checklist

| Stage | Status | Exit/next action |
|---|---|---|
| 0 — normative baseline and truthful status | Complete | Superseded working baseline retained in history |
| 1 — DUT Profile and provenance | Complete | Effective profile and digest exposed; physical behavior preserved |
| 2 — session schema v2 persistence | Complete | Review findings resolved; deterministic storage contract and compatibility readers validated |
| 3 — authoritative continuous recorder | Not started | **Next development slice** |
| 4 — Monitor | Not started | Wait for Stage 3 |
| 5 — audited TX, Interact, Control/boot-test | Not started | Wait for Stage 4 |
| 6 — durable cursor, follow, console | Not started | Wait for Stage 5 |
| 7 — release/reacquire, DTR/RTS, native USB | Not started | Wait for Stage 6 |
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | Not started | Wait for Stage 7 |
| Post-Phase-1 MCP migration | Not started | Wait for Stage 8 acceptance |

Implementation details, invariants, tests, and exit criteria for each stage live
only in the migration plan and normative specification. This checklist records
progress; it does not redefine either document.

## Deferred Work Outside the Active Slice

- Revision A corrected-design and remaining physical measurements are preserved
  as open Phase 1 acceptance evidence for Stage 8.
- Phase 4 Debug Agent evidence packaging remains paused after VS Code host
  acceptance; authenticated Claude Code host validation remains unavailable.
- Public `dutchmate-debug-agent` distribution remains deferred to `v0.2.0`.
- Delivery Infrastructure and the five-distribution `v0.1.0` release remain
  completed historical work; they do not satisfy any Phase 1 v2 semantic gate.

## Current Validation Requirements

Stage 2 validation, 2026-09-28: session-store tests passed (181 tests),
configured mypy reported no issues in 92 source files, Ruff passed, the lockfile
check passed, all 1,482 pytest tests passed, and `git diff --check` passed. The
Stage 2 structural Graphify index remains current because the review fixes did
not add, remove, or move modules or change layer dependencies. Detailed evidence
is recorded in [Development History](development_history.md).

For Stage 3, run focused recorder/runtime tests during development and the
repository-required Ruff, mypy, full pytest, and `git diff --check` gate before
declaring the stage complete.
