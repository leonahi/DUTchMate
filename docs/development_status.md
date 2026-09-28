# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 3 continuous evidence
> recorder implemented and review-corrected; Stage 4 is next
> Repository baseline reviewed: `f0cf53d3b3abbee38b1e6ed8e96eb20ce76029cc`
> on 2026-09-28
> Stage 3 working tree: uncommitted
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 3 replaces service-owned idle drain/discard with
  one core-owned recorder. Connected Basic/Enhanced startup creates an active
  v2 session, continuously persists ambient UART and telemetry, maintains
  line/pattern/integrity projections, publishes only durable tails, and keeps
  one ownership interval across profile-bounded reconnect segments and linked
  rollover sessions. Disconnect, rollover, and shutdown boundaries flush line
  state, and shutdown drains already-normalized backend events—including an
  Enhanced event blocked on bounded FIFO admission—before terminalizing.
- **Implementation status:** The Phase 1 v2 migration is **partially
  implemented through Stage 3 only**. Production runtime ownership now uses
  schema v2 and continuous acquisition. Monitor/Interact, audited action
  migration, follow/console, and release/reacquire are not implemented.
- **Historical evidence:** Existing Basic, Enhanced, firmware, ring-buffer, and
  HIL results remain valid evidence for the physical/backend behavior they tested.
  They do not establish the new continuous ambient recording, schema-v2,
  Monitor, Interact, follow/console, or release/reacquire requirements.
- **Next step:** Execute migration **Stage 4 only**: implement Monitor as a
  bounded operation over durable evidence. Do not begin Stage 5 action/Interact
  migration in that slice.
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
| Native session schema v2 | Deterministic v2 store/recovery/retrieval/retention is implemented | Stage 2 complete; production runtime ownership adopted in Stage 3 |
| Continuous ambient evidence recording | One core recorder owns backend receive, durable admission, projections, reconnect transfer, and shutdown/fault terminalization | Stage 3 complete |
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
| 3 — authoritative continuous recorder | Complete | Profile-bounded reconnect, provenance, capacity-blocked shutdown drain, boundary-flush, and queue review findings resolved |
| 4 — Monitor | Not started | **Next development slice** |
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

Stage 3 validation, 2026-09-28: focused recorder/backend/service tests passed;
the lockfile check passed; Ruff passed; configured mypy reported no issues in
93 source files; all 1,441 pytest tests passed; `git diff --check` passed; and
the structural Graphify index was refreshed with its reported partial-extraction
warning for `hardware/firmware/zephyr_dut/src/fixture_protocol.h`. Detailed
evidence is recorded in [Development History](development_history.md).
