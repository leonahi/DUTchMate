# Development Status

> Active phase: Phase 1 v2 semantic migration — Stage 8 software complete; HIL blocked
> Stage 8 base: `9a228fcc37d746241c4624469cf3d18b4a7fab4a` (pushed Stage 7)
> Reviewed fixture baseline: `746121a35633c070f4e7112010ce26b656d8ef1d` (pushed)
> Basic HIL code baseline: `21991fa403ad39f3100a24259b6f31a4c8ac1756` (pushed release-fix rerun)
> Test-isolation fix: `7f30a916a3033289dec6908ebeac17a687c0d806` (merged)
> Basic release fix branch base: `b4ad4f32c138a42f255110dc222c1258723cc138`
> Accepted Basic release fix: `df3ca29` (merged into the HIL baseline)
> CLI loss fix branch base: `acffad49ec63765d827f83f2921a61a6a5220bab`
> Accepted CLI loss fix: `ff8cc51` (merged); reconnect diagnostic HEAD: `7d6cac3764176820f6dc62f79f2d705749735b24`
> Documentation state reviewed: 2026-10-27
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** The reviewed CLI loss fix is merged into pushed
  `stage8-phase1-acceptance`. Focused Basic reconnect diagnostic
  `20261027T064604Z-7239cdfe` succeeded inside the unchanged 5-second window,
  continuing the same session in segment 1 with a durable gap and resumed RX.
  This was not full Basic HIL. Stage 8 and Phase 1A/1B/Phase 1 remain
  **Incomplete**; prior timeouts are not retroactively classified.
- **Implementation status:** Enhanced continuous RX/telemetry, per-segment RP2350
  provenance, audited reset/boot, immediate boot preservation, and CLI parity
  pass deterministic acceptance. Obsolete production v0/v1 writers, finite
  reconnect/discard paths, legacy response fallbacks, and single-workflow status
  are removed. Historical read/replay and Debug Agent v1 compatibility remain.
- **Historical evidence:** The ring-buffer decision remains `accepted_32k` for
  its recorded measurements. Existing HIL records were not rewritten or treated
  as current v2 acceptance; Revision A measurement gaps remain open.
- **Next step:** Review the focused diagnostic and investigate the recurring
  `E_COMMAND_001` command-path anomaly separately. Rerun full Basic HIL from the
  beginning with continuous reconnect timing observation and all software checks
  finished before physical startup. Preserve all failed runs. Enhanced HIL,
  Revision A, and MCP remain deferred.
- **Open blockers:** Full Basic acceptance is still outstanding. The measured
  reconnect succeeded in about 1.545 s; neither a reconnect defect nor the cause
  of earlier timeouts was established. An initial diagnostic attempt missed host
  transitions after its observer wait expired and remains unclassified.
  `E_COMMAND_001` recurred before and after the successful reconnect; separate
  explicit INFO retests matched. Its cause is unknown, not attributed to product
  or fixture. Enhanced/Phase 4 blockers remain unchanged.

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
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | HIL incomplete | CLI loss fix merged; focused reconnect passed; recurring command anomaly and full Basic acceptance remain open |
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
| Phase 1A — Basic | Incomplete; focused reconnect passed, prior timeout cause unclassified; recurring E_COMMAND_001 and full Basic HIL remain open |
| Phase 1B — Enhanced | Software parity accepted; incomplete pending real Pico 2 + fixture v2 HIL and required Revision A physical evidence |
| Phase 1 shared done criteria | Software regressions pass; incomplete until both backend/physical gates pass |

## Current Validation Requirements

Focused Basic reconnect diagnostic, 2026-10-27: clean pushed HEAD `7d6cac3`.
All software checks completed before startup: 1,514 tests passed in 36.83 s,
Ruff, mypy (103 files), offline lock check (66 packages), and diff check passed.
No tests or additional runtime/store ran during either physical service interval.
Two fresh diagnostic sessions are preserved: incompletely observed timeout
`20261027T063720Z-2c95d57d` and fully observed success
`20261027T064604Z-7239cdfe`. Timeout configuration remained 5.0 s throughout.

In the successful repeat, durable disconnect/start 11/12 were observed at
06:51:47.546443 UTC, FTDI USB again at 06:51:48.560095, serial node again at
06:51:48.565031, and segment-open/success 13/14 at 06:51:49.091107. Observed
start-to-success delta: 1.544660 s. Same ownership session, fresh segment 1,
gap count 1, resumed RX and responsive service were verified. Failed individual
open attempts are not exposed by existing logs; external probes did not compete
with automatic reconnect. Operator markers and poll bounds are preserved.

Exact audited INFO received `E_COMMAND_001` at RX 4/18; separate explicit INFO
retests returned the reviewed build at RX 9/23. No cause or fix is claimed.
Graceful stop released PID 18348, TCP 2040 and both FTDI paths. Original sessions
and configuration are unchanged. Only Basic validation/status/history changed;
no production patch, full Basic HIL, Enhanced HIL or MCP work occurred. Detailed
timings and limitations are in the [Basic report](../hardware/validation/phase1_basic_hil.md).

CLI v2 loss-display fix, 2026-10-27: four list/detail regression cases failed
RED with `none` or the obsolete projection, then passed GREEN using
`evidence_quality.backend_integrity.loss_status`. Ten formatter/command cases
passed, including v1 integrity and v0 read-only compatibility. Focused CLI,
session-store, session-endpoint and architecture gate: 368 passed in 3.62 s.
Full pytest: 1,514 passed in 36.46 s. Ruff, mypy (103 source files), offline
lockfile check (66 packages), and `git diff --check` passed. Offline formatting
of the preserved HIL API payload now shows `not_observable` in both views.
All 641 local `.dutchmate` file hashes are unchanged. No hardware was accessed;
no persistence, API schema, backend, reconnect or firmware behavior changed.

Basic physical rerun, 2026-10-27 IST (2026-10-26 UTC): clean pushed HEAD
`21991fa403ad39f3100a24259b6f31a4c8ac1756`; all software checks completed before
service startup: 1,509 pytest tests passed in 36.77 s, Ruff, mypy (103 files),
offline lockfile check (66 packages), and diff check passed. No tests or second
runtime/store ran during HIL. Fresh native-v2 session `20261026T185908Z-a2a4fdef`
retains 725 raw bytes, 17 RX records, 15 audited TX pairs, eight completed
operations and contiguous sequences 0..71. Ambient boot/INFO, follow/detach,
Monitor, all Interact outcomes, live console and post-exit RX passed. Delayed
ACK 44 → durable terminal 45 → ambient fault 46, 10.028466 s after ACK.

Release returned in 0.696 s; final RX 58, intent 59, released 60, gap/segment
closure, real external ownership and reacquire 61..63/fresh segment 1 passed.
Unexpected reconnect instead terminalized at `reconnect_timeout`; CLI session/list
also reads the obsolete top-level integrity field. API/metadata/log warning
retain truthful `not_observable`. No fixes were made during HIL. Graceful stop
removed PID 5444, its listener and serial ownership. Historical reports and
preserved failed-run copies remain unchanged; normal startup recovered the old
stale active session to `abandoned/service_restart` without changing its RX/action
evidence. Detailed provenance, limitations and hashes are in the
[Basic HIL report](../hardware/validation/phase1_basic_hil.md).

Basic release fix, 2026-10-26: three source regressions failed RED on stranded
wakeups; the real HTTP/Basic-source/recorder regression failed RED with release
blocked after physical close and final RX drain. Ten new hardware-free cases
now pass, including cancellation, concurrent shutdown, and close/persistence
errors. Focused lifecycle/backend/recorder/service/architecture gate: 345 passed
in 8.37 s. Full pytest: 1,509 passed in 37.62 s. Ruff, mypy (103 source files),
offline lockfile check (66 packages), and `git diff --check` passed. All 521 real
`.dutchmate` file hashes and prior HIL documentation are unchanged.

No timeout, ownership arbitration, recorder settlement, session persistence,
or interface contract was weakened. Only Basic FIFO consumption, regressions,
and status/history changed. The software fix is reviewed and accepted. Hardware
was not accessed; historical physical evidence remains in
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
