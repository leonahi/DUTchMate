# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 8 software complete; HIL blocked
> Stage 8 base: `9a228fcc37d746241c4624469cf3d18b4a7fab4a` (pushed Stage 7)
> Reviewed fixture baseline: `746121a35633c070f4e7112010ce26b656d8ef1d` (local; push blocked)
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
  The reviewed Basic fixture is committed locally. The operator confirms it is
  flashed and wired correctly; HIL is paused pending the operator's branch push.
- **Implementation status:** Enhanced continuous RX/telemetry, per-segment RP2350
  provenance, audited reset/boot, immediate boot preservation, and CLI parity
  pass deterministic acceptance. Obsolete production v0/v1 writers, finite
  reconnect/discard paths, legacy response fallbacks, and single-workflow status
  are removed. Historical read/replay and Debug Agent v1 compatibility remain.
- **Historical evidence:** The ring-buffer decision remains `accepted_32k` for
  its recorded measurements. Existing HIL records were not rewritten or treated
  as current v2 acceptance; Revision A measurement gaps remain open.
- **Next step:** The operator will push the existing branch. After that push,
  verify the actual boot/INFO identity through the Basic acceptance path and
  perform Basic HIL. Operator-confirmed firmware/wiring do not require another
  flash. Enhanced HIL and Revision A measurements remain pending; MCP migration
  remains deferred.
- **Open blockers:** The latest SSH push retry still failed with
  `Permission denied (publickey)`; the operator requested waiting for their push.
  At 2026-10-26 19:08:29 IST, FTDI FT231X `0403:6015`, serial `D358SG6A`, was
  present at `/dev/cu.usbserial-D358SG6A`, and the reviewed UF2 hash matched.
  The operator confirmed Pico 1/H identity, reviewed firmware, Basic wiring,
  3.3 V logic, separate USB power, disconnected FTDI VCC, and open GP2/GP3.
  No serial port has been opened; actual runtime identity and HIL remain
  unverified. Enhanced/Revision A and Phase 4 blockers remain unchanged.

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
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | Software complete; HIL blocked | Operator confirmed reviewed fixture flash/wiring; awaiting operator push before real Basic HIL |
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
| Phase 1A — Basic | Software accepted; incomplete pending real USB-UART + fixture v2 HIL |
| Phase 1B — Enhanced | Software parity accepted; incomplete pending real Pico 2 + fixture v2 HIL and required Revision A physical evidence |
| Phase 1 shared done criteria | Software regressions pass; incomplete until both backend/physical gates pass |

## Current Validation Requirements

Operator setup confirmation, 2026-10-26: reviewed fixture flash and all required
Basic wiring/settings confirmed by the operator. Read-only discovery and UF2
hash check at 19:08:29 IST passed; CLI help/current configuration inspected;
`lsof` listed no owner for the FTDI cu/tty paths. No serial open, service start,
or HIL occurred. Acceptance was paused at the operator's request pending push.
Only documentation changed; `git diff --check` passed, software tests not rerun.

Reviewed-fixture finalization/preflight, 2026-10-26 19:02:24 IST:
`git diff --check` and reviewed-source comparison passed; commit `746121a` was
created but both push authentication paths failed. Independent UF2 SHA-256
matches `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`.
FTDI is identifiable, but BOOTSEL volume and wiring verification are absent.
Stopped without flashing, opening serial, or starting HIL; no session exists.
The dated blocker record is retained below the later setup confirmation.
Acceptance gates are unchanged.

Basic fixture preparation, 2026-10-26: 17 host fixture tests and all 1,496 pytest
tests passed (39.83 s); Ruff and configured mypy (103 files) passed. Zephyr
v4.4.0/SDK 1.0.1 produced the normal `rpi_pico` UF2 with verified 115200 8-N-1,
no flow control/overlay, delayed-fault poll integration, and exact build ID in
host-exercised boot/INFO output. UF2 payload/artifact checks and
`git diff --check` passed. No serial port was opened, hardware flashed, or HIL
started; no session or acceptance result exists. FTDI discovery evidence is
preserved in [Basic HIL validation](../hardware/validation/phase1_basic_hil.md).
Exact commands, source/artifact identities, and limits are in development history.

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
