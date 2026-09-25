# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 1 DUT Profile and
> effective serial provenance implemented
> Repository baseline reviewed: `efe93060c4a4c3733d1f32b53c75f4f5d4c55c26`
> on 2026-09-25
> Stage 1 working tree: uncommitted
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 1 implements one resolved immutable DUT Profile,
  effective serial/GPIO provenance, a bounded canonical projection and SHA-256
  digest, CLI-to-service profile startup, and service/CLI status exposure.
- **Implementation status:** The Phase 1 v2 migration is **partially
  implemented through Stage 1 only**. Physical backend behavior, schema-v1
  persistence, finite workflows, and service-owned idle ingestion remain
  unchanged. No session-v2, recorder, Monitor/Interact, follow/console, or
  release/reacquire work has begun.
- **Historical evidence:** Existing Basic, Enhanced, firmware, ring-buffer, and
  HIL results remain valid evidence for the physical/backend behavior they tested.
  They do not establish the new continuous ambient recording, schema-v2,
  Monitor, Interact, follow/console, or release/reacquire requirements.
- **Next step:** Execute migration **Stage 2 only**: build session schema-v2
  persistence before runtime migration. Do not begin the Stage 3 continuous
  recorder in that slice.
- **Open blockers:** No contradiction requiring a new design decision was found
  between the two normative documents. Previously recorded Revision A physical
  evidence gaps remain deferred acceptance work for Stage 8; they do not change
  the Stage 2 scope.

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
| Native session schema v2 | New writes use the pre-v2 session model | Not implemented |
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
| 2 — session schema v2 persistence | Not started | **Next development slice** |
| 3 — authoritative continuous recorder | Not started | Wait for Stage 2 |
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

Stage 1 validation, 2026-09-25: profile, CLI configuration/lifecycle/status, and
service startup/status focused tests passed (105 tests); Ruff passed; mypy
reported no issues in 92 source files; all 1,432 pytest tests passed; the
structural Graphify index was refreshed; and `git diff --check` passed. Detailed
evidence is recorded in [Development History](development_history.md).

For Stage 2, run focused persistence tests during development and the
repository-required Ruff, mypy, full pytest, and `git diff --check` gate before
declaring the stage complete.
