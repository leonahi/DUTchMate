# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 7 Complete
> Stage 7 implementation baseline: `5643c65` (Stage 6 committed)
> Documentation state reviewed: 2026-10-26
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 7 is complete, covering explicit release/reacquire,
  intentional evidence gaps, same-session resume/new-session recovery, Basic
  DTR/RTS open provenance, and unique native-USB identity selection. Ownership
  arbitration preserves audited mutations, read-only Monitor settlement, and
  one authoritative RX reader; unknown cleanup remains a blocking fault.
- **Implementation status:** Stages 1–7 are complete. Service and CLI
  expose atomic release/reacquire; no optional raw or semantic serial-line
  control capability was added. Historical v0/v1 readers remain available.
- **Historical evidence:** Existing physical/backend/HIL results remain valid
  for what they tested; they do not establish final Phase 1 v2 acceptance.
- **Next step:** Stage 8 — Enhanced parity, cleanup, and CLI/HIL acceptance — is
  the next implementation slice and remains **Not started**. MCP migration
  remains deferred until after Phase 1 CLI acceptance. Existing physical/HIL
  acceptance work remains deferred to Stage 8.
- **Open blockers:** No new design blocker. Revision A physical evidence gaps
  remain deferred to Stage 8. MCP and Debug Agent contract migration remain deferred.

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
| Interact and audited actions | Exact-byte audited send, exclusive bounded Interact, and audited reset/boot/GPIO Control; higher-level reset/observe procedures are client-composed | Stage 5 complete at `857261b`; live boot-test removed |
| Follow and console | Durable cursor API plus HTTP-only follow and audited line console | Stage 6 complete at `5643c65` |
| Release and reacquire | Explicit ownership lifecycle, durable gaps, Basic line provenance, and safe USB identity matching | Stage 7 Complete |
| MCP target-contract migration | Existing MCP integration exposes pre-v2 service semantics | Deferred until after Phase 1 CLI acceptance |

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
| 5 — audited TX, Interact, Control | Complete | Atomic-capability review committed at `857261b` |
| 6 — durable cursor, follow, console | Complete | Durable snapshots, cursor continuity, and HTTP-only client views reviewed and validated |
| 7 — release/reacquire, DTR/RTS, native USB | Complete | Lifecycle arbitration, cleanup certainty, provenance, and selector behavior reviewed and validated |
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | Not started | Next implementation slice; includes deferred physical/HIL acceptance |
| Post-Phase-1 MCP migration | Deferred | After Phase 1 CLI acceptance |

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

Stage 7 validation, 2026-10-25: 830 focused tests and all 1,515 pytest tests
passed. Ruff, configured mypy (103 source files), lockfile check (66 packages),
and `git diff --check` passed. Import Linter is not configured; executable
architecture/import-boundary tests passed. The structural Graphify index was
refreshed with the existing partial-extraction warning for
`hardware/firmware/zephyr_dut/src/fixture_protocol.h` and a community-label notice.
No hardware was accessed. Detailed evidence is in
[Development History](development_history.md). Stage 7 is complete. Stage 8 is
next and has not started; MCP migration remains deferred until after Phase 1 CLI
acceptance. Existing physical/HIL acceptance work remains deferred to Stage 8.
