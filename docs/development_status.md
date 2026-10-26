# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 8 software complete; HIL blocked
> Stage 8 base: `9a228fcc37d746241c4624469cf3d18b4a7fab4a` (pushed Stage 7)
> Reviewed fixture baseline: `746121a35633c070f4e7112010ce26b656d8ef1d` (pushed)
> Basic HIL code baseline: `ad8b63abc3c9330864eaa49cb48aab57cd03f2cd` (clean rerun)
> Test-isolation fix: `7f30a916a3033289dec6908ebeac17a687c0d806` (merged)
> Documentation state reviewed: 2026-10-26
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Stage 8 software acceptance has passed review on
  `stage8-phase1-acceptance`. Stage 8 itself
  and Phase 1A/1B/Phase 1 remain **Incomplete** because real v2 HIL is required.
  The clean Basic rerun passed ambient boot/INFO, follow, Monitor, audited TX,
  Interact/delayed fault, and console checks, then stopped on a release hang.
  Phase 1A is not accepted; the isolated software gate completed before service start.
- **Implementation status:** Enhanced continuous RX/telemetry, per-segment RP2350
  provenance, audited reset/boot, immediate boot preservation, and CLI parity
  pass deterministic acceptance. Obsolete production v0/v1 writers, finite
  reconnect/discard paths, legacy response fallbacks, and single-workflow status
  are removed. Historical read/replay and Debug Agent v1 compatibility remain.
- **Historical evidence:** The ring-buffer decision remains `accepted_32k` for
  its recorded measurements. Existing HIL records were not rewritten or treated
  as current v2 acceptance; Revision A measurement gaps remain open.
- **Next step:** Diagnose/fix the Basic release/drain failure in a separate
  software slice, then rerun full Basic HIL after its software gate. Preserve
  both diagnostic sessions; do not resume them as acceptance. Enhanced HIL,
  Revision A measurements, and MCP migration remain deferred.
- **Open blockers:** `dutchmate release` recorded intent at evidence sequence 57
  but timed out after 65.16 s without a released boundary. Status initially
  remained connected, then requests timed out. The serial descriptor closed,
  but the process stayed alive after graceful stop and required SIGKILL. No
  external owner was opened; handoff/reacquire and unexpected reconnect remain
  unproven. The earlier `E_COMMAND_001` did not recur in this run; its old
  evidence remains unchanged. Service, HTTP listener, and serial ownership are
  now stopped/released. Enhanced/Phase 4 blockers remain unchanged.

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
| MCP target-contract migration | Existing MCP integration exposes pre-v2 service semantics | Deferred until after Phase 1 CLI/HIL acceptance |

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
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | Software gate passed; HIL incomplete | Clean Basic HIL stopped on release failure; separate lifecycle fix and complete rerun required before Enhanced HIL |
| Post-Phase-1 MCP migration | Deferred | After Phase 1 CLI/HIL acceptance |

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

## Current Acceptance Gates

| Gate | Status |
|---|---|
| Phase 1A — Basic | Incomplete; clean HIL stopped on Basic release hang; handoff/reacquire and unexpected reconnect not accepted |
| Phase 1B — Enhanced | Software parity accepted; incomplete pending real Pico 2 + fixture v2 HIL and required Revision A physical evidence |
| Phase 1 shared done criteria | Software regressions pass; incomplete until both backend/physical gates pass |

## Current Validation Requirements

Clean Basic HIL, 2026-10-26: all software validation finished before physical
service startup. Full pytest: 1,499 passed in 35.84 s; Ruff, mypy (103 source
files), offline lockfile check (66 packages), and preflight diff check passed.
No pytest/runtime/store construction occurred afterward. New schema-v2 session
`20261026T175336Z-3d1dd5a9` retained 590 RX bytes, 16 RX records, 13 audited
TX attempts/results, and seven completed operations. Delayed-fault terminal
47 precedes fault RX 48; ACK→fault is 10.034749 s. Release intent 57 has no
completed handoff boundary. Evidence and process sample are preserved; forced
cleanup verified no service or port owner remains. Metadata is preserved as
stale `active` after forced shutdown, not rewritten as accepted/complete.

Only new HIL documentation is uncommitted; no production/fixture/test fix was
made. Final `git diff --check` and preservation hashes passed. Both this run
and the unchanged older diagnostic session are recorded in
[Basic HIL validation](../hardware/validation/phase1_basic_hil.md).

Stage 8 software validation, 2026-10-26: all 1,491 pytest tests passed (39.58 s),
including the firmware harness and architecture/dependency checks. The focused
acceptance/cleanup/Debug Agent gate passed 23 tests. Ruff, configured mypy (103
source files), offline lockfile check (66 packages), core and Debug Agent sdist/
wheel builds, and `git diff --check` passed. Production wheels exclude test-only
legacy fixture builders. Graphify was refreshed with its existing partial
extraction warning for `fixture_protocol.h` and community-label notice. Discovery
ran only after the software gate passed; no serial connection was opened and no
firmware was flashed. Detailed commands/results live in
[Development History](development_history.md).
