# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 4 bounded Monitor
> implemented; Stage 5 is next
> Repository baseline reviewed: Stage 4 completion commit (current `HEAD`)
> on 2026-09-28
> Stage 4 state: committed; Stage 5 has not started
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 4 adds bounded duration/condition Monitor
  operations over the Stage 3 durable stream. Monitor records globally unique
  operation IDs, accepted parameters, cursors, rollover-spanning ranges,
  terminal outcomes, exact requested matches, line-limit quality, and
  cancellation. Matching reads no pre-start history or pre-cursor partial line,
  lifecycle rollover flushes continuous line state, reconnect preserves one
  operation while both deadlines remain valid, and failed reconnect produces a
  durable `disconnected` outcome. Incremental seek cursors read only newly
  admitted UART evidence outside the store mutation lock. Results aggregate
  integrity from exact half-open evidence ranges and timestamp provenance across
  every range. A bounded reader lease protects rollover predecessors through
  terminal result construction. Service/CLI expose Monitor; legacy capture/wait
  always require and delegate to Monitor.
- **Implementation status:** The Phase 1 v2 migration is **partially
  implemented through Stage 4**. Production runtime ownership uses schema v2,
  continuous acquisition, and bounded Monitor. Interact, audited action
  migration, follow/console, and release/reacquire are not implemented.
- **Historical evidence:** Existing Basic, Enhanced, firmware, ring-buffer, and
  HIL results remain valid evidence for the physical/backend behavior they tested.
  They do not establish the new continuous ambient recording, schema-v2,
  Monitor, Interact, follow/console, or release/reacquire requirements.
- **Next step:** Execute migration **Stage 5 only**: make UART TX always audited,
  add Interact, and migrate Control/boot-test auditing. Do not begin Stage 6
  durable-cursor/follow/console work in that slice.
- **Open blockers:** No contradiction requiring a new design decision was found
  between the two normative documents. Previously recorded Revision A physical
  evidence gaps remain deferred acceptance work for Stage 8; they do not change
  the Stage 4 scope.

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
| Native session schema v2 | Deterministic v2 store/recovery/retrieval/retention is implemented | Stage 2 complete; production runtime ownership adopted in Stage 3 |
| Continuous ambient evidence recording | One core recorder owns backend receive, durable admission, projections, reconnect transfer, and shutdown/fault terminalization | Stage 3 complete |
| Monitor | Bounded duration/condition observation uses the continuous durable stream with v2 operation lifecycle evidence | Stage 4 complete |
| Interact and audited actions | Existing send/Control/boot-test paths retain pre-Stage-5 semantics | Not implemented |
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
| 3 — authoritative continuous recorder | Complete | Profile-bounded reconnect, provenance, capacity-blocked shutdown drain, boundary-flush, and queue review findings resolved |
| 4 — Monitor | Complete | Review fixes validated; rollover-safe lifecycle, deterministic terminalization, exact-range quality, leased incremental reads, and Monitor-only aliases |
| 5 — audited TX, Interact, Control/boot-test | Not started | **Next development slice** |
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

Stage 4 review-fix validation, 2026-09-28: 79 focused Monitor, persistence, and
status regressions passed; the lockfile check and Ruff passed; configured mypy
reported no issues in 94 source files; all 1,488 pytest tests passed; and
`git diff --check` passed. Graphify was refreshed with its existing partial
extraction warning for `hardware/firmware/zephyr_dut/src/fixture_protocol.h`.
Detailed evidence is recorded in [Development History](development_history.md).
