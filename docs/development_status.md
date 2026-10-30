# Development Status

> Active phase: MCP v2 migration Complete; Phase 1A Complete; Stage 8/Phase 1B/Phase 1 incomplete
> Stage 8 base: `9a228fcc37d746241c4624469cf3d18b4a7fab4a` (pushed Stage 7)
> Reviewed fixture baseline: `746121a35633c070f4e7112010ce26b656d8ef1d` (pushed)
> Basic HIL code baseline: `31b14a4de28c3713fbb8451f31520600917616dc` (pushed; Phase 1A accepted after contract audit)
> Test-isolation fix: `7f30a916a3033289dec6908ebeac17a687c0d806` (merged)
> Basic release fix branch base: `b4ad4f32c138a42f255110dc222c1258723cc138`
> Accepted Basic release fix: `df3ca29` (merged into the HIL baseline)
> CLI loss fix branch base: `acffad49ec63765d827f83f2921a61a6a5220bab`
> Accepted CLI loss fix: `ff8cc51` (merged); reconnect diagnostic HEAD: `7d6cac3764176820f6dc62f79f2d705749735b24`
> Command anomaly diagnostic HEAD: `04f2ff28e47248bead99e9e3dc67d1af34bb693b`
> Fixture byte-diagnostic source base: `6c908f79f1a0a4e636a45cbd70576666e2ad5cac`
> Committed fixture / physical diagnostic HEAD: `69a0980e1c7ced2cfcf053ebdd95e7b8dcc16df4` (pushed)
> Bounded overflow enhancement source base: `68ae39714fb5ebfd55ec970e2709d29561c822e9` (pushed)
> Bounded overflow fixture / physical diagnostic HEAD: `4692444f771f33b6d27994e03f2722c268e3f43a` (pushed)
> Enhanced HIL code baseline: `887768c2e10da1ba8ae9c323474fad86648a7d34` (failed HIL evidence committed at `90c744f`)
> Enhanced control fix base: `90c744fe97ed3af2224989a954261bef42797b45`; accepted fix/focused HIL baseline: `6d0c1a87b8867d6ea0741b90a9e6d90cb9fc7ce8`; focused HIL documentation: `df8e7a6` (pushed)
> Enhanced cleanup fix base: `df8e7a6b45a5a92d8e1a545c04d893c8e87df34d`; accepted fix/automatic USB HIL baseline: `14e6717554e76444a6b9bc21dbf257a0e51d1efe` (pushed code/HIL baseline on `fix/enhanced-terminal-read-cleanup`)
> Pushed evidence-audit baseline: `9ff33c10858d5e040688e895b9d201cae70bcf71` (automatic USB reconnect HIL documentation; independently verified by HTTPS remote lookup)
> Revision A pull-up validation base: `4c87383038377401da785fdf22a5527031e8f97c` (updated pushed `main`); working branch `validation/phase1b-revision-a`
> MCP readiness-audit baseline: `2b7c89a0830c32da5ea9bbc293d8f4b6fc83e243` (pushed `main` at the readiness audit, independently verified over HTTPS)
> Accepted MCP Slice 1: `22cbd11` (pushed on `mcp/v2-service-client`); original implementation base `9c0e0f9`
> Accepted MCP Slice 2: `6497f85` (pushed on `mcp/v2-service-client`); original implementation base `22cbd11`
> Accepted MCP Slice 3: `c119532` (pushed on `mcp/v2-service-client`); original implementation base `6497f85`
> Accepted MCP Slice 4: `71a43f0` (pushed on `mcp/v2-service-client`); original implementation base `c119532`
> Accepted MCP Slice 5: `664615a`; merged into `main` via PR #5 at `5c517ad`; original implementation base `71a43f0`
> Cleanup source base: `5c517ad`; current branch `refactor/stale-code-cleanup`, cleanup uncommitted
> KiCad corrections/source review: merged into `main` via PR #3 at `f1c61d1` (correction commit `a837f4b`)
> Documentation state reviewed: 2026-10-30
> Authority: the only source for current progress, active phase, blockers, and
> next step
> History: completed slices and dated validation live in
> [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** MCP v2 migration **Complete** under the approved scoped
  policy; repository stale-code cleanup validated, with optional host UI gaps below.
- **Design authority:** [Current KiCad source](../hardware/pcb/debug-helper/rev-a/README.md)
  uses one 2×8 J1, TMUX2819 sense isolation, an after-RN5A 10 kΩ UART pull-up
  and corrected bias networks. Source review establishes no physical acceptance.
- **Development policy:** [Phase 1 specification §4.1](phase1_implementation_spec.md#41-software-sequencing-and-hardware-acceptance-boundaries)
  permits continued software/behavioral work with the legacy EAGLE board as a
  functional Enhanced HIL fixture. Historical electrical gaps remain unresolved.
- **MCP acceptance:** Strict Inspector and applicable pinned conformance pass;
  VS Code registration saved; VS Code tool use and Claude Code host checks unavailable.
- **Next software step:** Optional named-host discovery/read-only call checks when
  authenticated sessions are available; no required MCP implementation slice remains.
- **Hardware step:** Run fresh corrected-design physical/electrical validation
  once manufactured KiCad Rev-A boards are available.
- **Hardware gate:** Phase 1A stays Complete; Phase 1B, Stage 8 and Phase 1 stay
  incomplete until required manufactured KiCad Rev-A physical validation passes.
- **Manual hardware work:** Layout/routing, DFM, fabrication preparation, Gerber
  review and manufacturing submission remain hardware-designer activities
  outside the agent workflow; no repository-driven PCB/DFM task or gate.
- **Historical prototype:** Pull-up blocker #1 stays **Satisfied**: nominal
  10 kΩ axial resistor/jumper, approximately 9.9 kΩ, from DUT_VIO (J3 pin 8)
  to DUT_UART_TX (J1 pin 4), before historical R16. UART electrical/oscilloscope
  evidence remains unresolved; functional HIL does not close that gap.
- **Evidence boundary:** Legacy functional HIL, historical EAGLE validation,
  KiCad source review and manufactured-board acceptance remain distinct (§4.1).
- **GP28 firmware boundary:** ADC sensing is not implemented; future ADC use
  must disable the digital-input buffer. Firmware remains unchanged.
- **Closed evidence:** Existing Basic/Enhanced workflow acceptance is unchanged.
- **Deferred:** Phase 5 EVENT capture remains deferred under existing criteria.
- **Validation:** Cleanup focused 184/450, architecture/packaging 30, full 1,872;
  build/install smoke, Ruff, mypy/103, interfaces and links/diff pass; no hardware/HIL.
- **Other boundaries:** Basic anomaly non-blocking; Phase 4 remains paused.

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
| Basic and Enhanced physical adapters | Existing backend/protocol/firmware baseline and historical EAGLE evidence retained; KiCad physical acceptance requires fresh evidence | Basic v2 accepted; historical Enhanced workflows/pull-up evidence retained; Phase 1B awaits manufactured KiCad Rev-A physical validation |
| DUT Profile and effective serial provenance | One immutable resolved profile owns backend, selector/topology, UART policy, DTR/RTS request, GPIO config, projection, and digest | Stage 1 complete; exposed through runtime/service/CLI status without v2 storage |
| Native session schema v2 | Deterministic v2 store/recovery/retrieval/retention is implemented | Stage 2 complete; production runtime ownership adopted in Stage 3 |
| Continuous ambient evidence recording | One core recorder owns backend receive, durable admission, projections, reconnect transfer, and shutdown/fault terminalization | Stage 3 complete |
| Monitor | Bounded duration/condition observation uses the continuous durable stream with v2 operation lifecycle evidence | Stage 4 complete |
| Interact and audited actions | Exact-byte audited send, exclusive bounded Interact, and audited reset/boot/GPIO Control; higher-level reset/observe procedures are client-composed | Stage 5 complete at `857261b`; live boot-test removed |
| Follow and console | Durable cursor API plus HTTP-only follow and audited line console | Stage 6 complete at `5643c65` |
| Release and reacquire | Explicit ownership lifecycle, durable gaps, Basic line provenance, and safe USB identity matching | Stage 7 Complete |
| MCP target-contract migration | Twelve tools accepted through real service/runtime, installed stdio, strict Inspector and scoped conformance; registration docs refreshed | Complete through Slice 5 under the scoped policy; VS Code tool use/Claude Code host UI remain unavailable, not passed |

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
| 8 — Enhanced parity, cleanup, CLI/HIL acceptance | Incomplete | Phase 1A Complete; Phase 1B awaits fresh manufactured KiCad Rev-A physical validation, including UART oscilloscope evidence; legacy EAGLE UART gap remains historically unresolved |
| MCP v2 migration | Complete; Slices 1–5 accepted under the scoped policy | Optional named-host follow-up: VS Code discovery/read-only call and Claude Code registration/discovery/call when host sessions are available; no remaining required migration slice |

Implementation details, invariants, tests, and exit criteria for each stage live
only in the migration plan and normative specification. This checklist records
progress; it does not redefine either document.

## Deferred Work Outside the Active Slice

- Final current-hardware physical/electrical acceptance awaits manufactured
  KiCad Rev-A boards. This does not defer legacy EAGLE functional Enhanced HIL
  or independent MCP software work permitted by specification §4.1. The
  historical EAGLE electrical/oscilloscope gap remains unresolved.
- Phase 4 Debug Agent evidence packaging remains paused after VS Code host
  acceptance; authenticated Claude Code host validation remains unavailable.
- Public `dutchmate-debug-agent` distribution remains deferred to `v0.2.0`.
- Delivery Infrastructure and the five-distribution `v0.1.0` release remain
  completed historical work; they do not satisfy any Phase 1 v2 semantic gate.

## Current Acceptance Gates

| Gate | Status |
|---|---|
| Phase 1A — Basic | Complete; fresh session 20261027T073956Z-7c038da2 satisfies normative criteria; E_COMMAND_001 unresolved/unclassified/non-blocking |
| Phase 1B — Enhanced | Incomplete until required manufactured KiCad Rev-A physical validation is performed and accepted; includes fresh UART electrical/oscilloscope evidence under existing criteria; legacy EAGLE functional HIL cannot satisfy this hardware gate |
| Phase 1 shared done criteria | Shared §35 behavioral evidence is retained; Phase 1 remains incomplete pending accepted current-board physical validation, without transferring EAGLE acceptance to KiCad |

## MCP v2 Start Prerequisite Audit

**Disposition: Satisfied**, audited 2026-10-30 at pushed `main` `2b7c89a`.

| Prerequisite | Disposition/evidence |
|---|---|
| Required Device Core/service/CLI software baseline accepted | Satisfied at readiness-audit base `2b7c89a`: Stage 8 software acceptance and subsequent lifecycle fixes/gates were committed; `core/`, `apps/`, `tests/`, `uv.lock` and root `pyproject.toml` were unchanged from accepted `14e6717` |
| Functional Enhanced HIL available | Satisfied: retained EAGLE functional runs cover v2 operations/evidence, explicit handoff/control and automatic USB reconnect; no physical rerun needed under §4.1 |

Evidence references and limits are in the
[dated audit](development_history.md#mcp-v2-start-prerequisite-and-contract-audit--2026-10-30).
The [MCP plan](mcp_integration_plan.md#independently-testable-implementation-sequence)
defines five testable implementation slices and the
[scoped acceptance policy](mcp_integration_plan.md#test-and-acceptance-matrix).
All five slices are accepted: actual-service integration and modern installed
stdio, strict Inspector, applicable pinned conformance and registration docs.
Named host checks are required only when available: VS Code CLI registration
was exercised, but VS Code discovery/call and Claude Code host checks were not.
Those optional follow-ups remain distinct from a full host pass and from the
unchanged manufactured KiCad Rev-A acceptance gates above.

## Current Rev-A KiCad Source Checklist

| Check | Result |
|---|---|
| TMUX2819 hardware-defined isolation, divider and GNDA | Verified from schematic/netlist; powered-off behavior cross-checked against datasheet |
| UART bias, control defaults and A2-safe enable biasing | Agreed resistor values and connections verified |
| Single J1 mapping, fixed directions and PCB pad-net consistency | Verified; no placement/routing change during review |
| Symbols, metadata and intentional unused pins | Verified; reusable TMUX metadata completed |
| ERC | 0 errors, 1 reviewed warning: bidirectional analog SA on an externally supplied power net; no exclusions added |
| GP28 ADC input-buffer setting | Not applicable to an active ADC path: sensing is not implemented; firmware unchanged |
| Source/schematic review | Complete; no hardware validation or fabrication acceptance established |
| PCB/DFM/fabrication preparation | Manual hardware-designer work outside the agent workflow; no repository review task or acceptance gate |
| Manufactured KiCad Rev-A validation | Waiting for physical boards; fresh evidence required using the README's adapted validation categories |

## Current Validation Requirements

Repository stale/dead-code audit, 2026-10-30: removed one unreferenced internal
GPIO-role constant and five uncalled test helpers after mapping source, test,
packaging, export and compatibility consumers. Corrected stale deferred-MCP
wording in the retained wire-encoder helper and architecture description. No
test cases or supported paths removed. Before/after CLI commands/options,
service OpenAPI, MCP twelve-tool schemas/order, package metadata and facade
exports/signatures are unchanged. Schema-v0/v1 readers/fixtures, deferred Debug
Agent behavior, capture/wait compatibility aliases and public backend methods
remain intact. Focused groups: **184 passed in 0.47 s**, **450 passed in 9.40 s**;
architecture/packaging: **30 passed in 1.22 s**; full pytest: **1,872 passed in
59.66 s**; Ruff, mypy/103, six wheel/sdist builds, isolated installed smoke,
links/preservation and `git diff --check` passed. No hardware/HIL, commit or push.
MCP/Phase 1 acceptance and optional host gaps are unchanged; details are in history.

MCP v2 Slice 5, 2026-10-30: MCP migration **Complete under the approved scoped
policy**. Current Inspector **2.13.0**, supported Node **22.19.0**, strict modern
stdio `tools/list` through the absolute installed `dutchmate-mcp`: exit 0,
exact twelve-tool order, empty stderr/no portability findings. Pinned conformance
**0.2.0-alpha.11**, frozen `2026-07-28`: stateless 23/25 (only the two documented
synthetic sampling exclusions fail), tools-list 3/3, required tools-cache/TTL/
scope/wire-schema 4/4. Full fixture run: 104 passed/61 failed across 50 scenarios,
including 13 unscored scenarios (11 failing); optional-feature results are not
product passes or newly added requirements. No runner-policy discrepancy found.
Temporary loopback projection of the same composition was stopped; port closure
verified. No product HTTP transport, Device Core process or hardware was used.
VS Code **1.141.0** registration saved in an isolated temporary profile; its UI/
discovery/read-only call were unavailable and not performed. Claude Code absent
from PATH/checked install locations; authenticated host checks unavailable.
These optional host gaps are not inferred passes. Developer guide uses separate
VS Code/portable formats, installed placeholders and explicit service startup.
Focused MCP/CLI/architecture/packaging: **372 passed in 11.35 s**; full pytest:
**1,872 passed in 58.24 s**; six wheel/sdist pairs and isolated install smoke,
Ruff, mypy/103, links, preservation and `git diff --check` passed. Documentation
only; production contracts and historical evidence unchanged. No commit/push.
Detailed commands, scoped exceptions and host dispositions are in history.

MCP v2 Slice 4, 2026-10-30: both installed entrypoints pass raw stdio discovery,
ordered twelve-tool listing/cache, URL precedence/rejection, bounded errors,
stderr-only logging and clean EOF outside the repository without venv PATH or
PYTHONPATH. Default URL and all log levels remain unchanged. Six wheel/sdist
pairs built; isolated wheel-installed commands, dependency/entrypoint metadata
and SDK stdio smoke passed. The smoke script's stale nine-tool expectation was
captured by a failing regression and refreshed; no production defect or change.
AST boundary checks constrain MCP to HTTP/SDK and pure Core contracts, excluding
hardware/service ownership, persistence, LLM/Debug Agent and hosted transports.
Focused MCP/CLI/architecture/packaging: **372 passed in 11.32 s**; full pytest:
**1,872 passed in 56.22 s**; Ruff, mypy/103 files, local links, preservation and
`git diff --check` passed. No hardware/HIL, listener, service process, commit or
push. Detailed commands and scope are in development history.

MCP v2 Slice 3, 2026-10-30: twelve actual-service integration cases pass through
modern MCP, the real client, injected ASGI transport, FastAPI routes/validation/
serialization, Device Core/recorder/store and deterministic fake physical ports.
Operation outcomes and exact TX, cursors/pages, v2 sessions/segments/gaps,
configured Control, error projection and cancellation/EOF are covered. The
`invalid_session_state` case explicitly injects a real store state-guard failure
at the test-owned runtime boundary; no public tool/contract is added. Cancellation
persists `cancelled` while retaining successful TX audit; MCP EOF leaves service
ownership/recording active. No production defect found or production code changed.
Focused ASGI: **12 passed in 1.45 s**; MCP/launch: **323 passed in 4.88 s**;
full pytest: **1,850 passed in 49.21 s**; Ruff, mypy/103 files, local links,
preservation and `git diff --check` passed. No physical HIL, listener, commit or
push. Detailed evidence/commands are in development history.

MCP v2 Slice 2, 2026-10-30: exactly twelve ordered public tools registered;
eight retired client/server paths and their positive tests removed. Strict raw
argument validation prevents SDK JSON-string reinterpretation and rejects extra
fields; results/errors remain bounded and service-owned. SDK 2.x metadata,
cache hints, cancellation/EOF and installed stdio/launcher checks pass.
Focused MCP/launch: **311 passed in 3.44 s**; full pytest: **1,838 passed in
48.25 s**; Ruff, mypy/103 files, retired-reference, documentation link,
preservation and `git diff --check` checks passed. Device Core, service API,
launcher and hardware/evidence files are unchanged. No physical HIL, commit or
push. Detailed commands and scope are in development history.

Earlier dated entries retain the scope/status of their own completed slice.

MCP v2 Slice 1, 2026-10-30: twelve service-client operations implemented with
exact request forwarding, shared validation, operation/evidence-aware timeouts
and canonical error/context preservation, including HTTP 410. Noncanonical
service diagnostic text is rejected as a bounded protocol error. Public server,
CLI/entrypoints, service API and Device Core semantics are unchanged. Retained
old client methods serve the pre-v2 catalog until Slice 2. Client tests:
**155 passed**; MCP/server/protocol/launch: **182 passed in 2.40 s**; full pytest:
**1,709 passed in 47.24 s**; Ruff, mypy/103 files, documentation links,
preservation and `git diff --check` passed. No hardware/HIL, commit or push.
Detailed commands, retained consumers and scope are in development history.

MCP readiness/contract audit, 2026-10-30: three documentation files only.
Existing committed software/HIL evidence establishes start readiness under
specification §4.1; no physical HIL or electrical acceptance was rerun/inferred.
Focused offline service/CLI/MCP checks: **75 passed in 3.31 s**, including modern
protocol baseline and installed stdio launch. Local links/anchors, source/tool
mapping, evidence preservation, documentation-only scope and `git diff --check`
passed. No production code, tests, firmware, hardware design or historical
validation changes; no commit/push. Detailed evidence/commands are in history.

The [Phase 1 specification §4.1](phase1_implementation_spec.md#41-software-sequencing-and-hardware-acceptance-boundaries)
owns the functional-HIL and MCP sequencing policy. While manufactured boards
are pending, legacy EAGLE functional Enhanced HIL may support behavioral work;
it supplies no electrical acceptance or KiCad-specific feature validation.

Required manufactured KiCad Rev-A physical/electrical validation remains open.
It must use fresh evidence against the corrected design and the applicable
[KiCad README categories](../hardware/pcb/debug-helper/rev-a/README.md#validation-lifecycle-and-evidence-boundaries).
Phase 1B, Stage 8 and Phase 1 remain incomplete until it passes. Manual PCB/DFM/
fabrication work remains outside the coding-agent workflow. The historical
EAGLE UART electrical/oscilloscope gap is still unresolved.

Documentation policy update, 2026-10-30: six documentation/specification files
only; history extended without changing earlier entries, and historical HIL,
physical validation and dated source/test results preserved. Scope/preservation,
local links/anchors, sequencing/evidence-boundary checks and `git diff --check`
passed. No new software-suite, CAD or hardware result is claimed; no commit or
push performed. Detailed checks are in development history.

Rev-A KiCad correction review, 2026-10-29: worked from `e8ce97c` with manual
schematic/project/PCB/library edits preserved. Confirmed TMUX pinout, hardware
EN/SEL, NC/EP handling, C16 bypass, GNDA divider, after-RN5A 10 kΩ UART bias,
10 kΩ control-data pull-downs, all agreed 4.7 kΩ networks and J1 mapping.
Added an explicit DUT_VIO PWR_FLAG for the external supply and filled only
missing reusable TMUX description/datasheet fields. No electrical pin/net
connection changed during cleanup; PCB, project settings, firmware, tests and
historical validation files were not edited by this review. KiCad 10.0.5 ERC
with errors/warnings/exclusions included reports **0 errors, 1 warning**:
TMUX SA is typed bidirectional on the externally supplied power net. This is
intentional analog connectivity, not a second digital power driver; no rule
severity or exclusion was changed. Source assertions: **309 passed**, covering
all **47 components** against PCB values/pad nets. Focused firmware suite:
**97 passed in 19.47 s**; full pytest: **1,569 passed in 49.22 s**; Ruff, mypy
(103 source files), offline lock (66 packages) and `git diff --check` passed.
The firmware has no GP28 ADC sensing implementation, so no existing ADC-mode
buffer-disable configuration is claimed. Source status does not alter Phase
1 acceptance or constitute physical measurements or fabrication acceptance.

The earlier dated records below retain their historical scope and wording;
references to future/unavailable KiCad files or legacy-prototype follow-up
describe those earlier slices, not current tasks. The EAGLE UART evidence gap
remains unresolved; current functional-HIL permission is defined in §4.1 above.

Rev A pull-up documentation closure, 2026-10-28: blocker #1 **Satisfied** using
operator-confirmed nominal 10 kΩ axial leaded resistor, approximately 9.9 kΩ
measured, attached by jumper wire as DUT_VIO (J3 pin 8) ↔ 10 kΩ ↔ DUT_UART_TX
(J1 pin 4). Incorrect 11.88 kΩ part replaced; previous measurements retained.
Fresh XML inspection of both accepted EAGLE sources confirms J1 pin 4→R16
pad 2, and R16 pad 3→U1.B2/pin 1. The Rev A pull-up is before R16; future
KiCad after-R16 intent is outside this repository. No additional physical
continuity check is needed to establish this documented relationship. No
unreported contact measurement or new hardware result is claimed. Only UART
electrical signal-integrity/oscilloscope acceptance remains open; Phase 1B
is incomplete. Four allowed docs only, unstaged/uncommitted; no hardware access,
oscilloscope work, software/test/firmware or PCB design changes.
Fresh offline gate: **1,569 passed in 46.68 s**; Ruff passed; mypy passed/103
source files; lock check passed/66 packages. XML mapping, new links/anchors,
branch/four-file scope, empty staging and `git diff --check` passed. Removing
only the new closure additions reproduces every prior physical/HIL/history
section byte-for-byte; earlier dated status validation records and all 1,281
other snapshotted files remain unchanged. Complete working-tree diff retained
for review; no commit or push performed.

The dated entries below preserve earlier readings and dispositions. The current
as-built closure above supersedes their open/pending pull-up interpretations;
it does not rewrite their historical measurement results.

Rev A replacement follow-up, 2026-10-28: current validation branch remains at
`4c87383` with prior unstaged documentation preserved. Operator identifies the
11.88 kΩ part as incorrect and replaced, and reports nominal 10 kΩ replacement
measured approximately 9.9 kΩ, power removed. Final endpoint, pad/input and
R16 non-bridge measurements are not supplied. The operator now confirms all
three R16/receiver points accessible and the resistor's own supply lead unplugged
for the 9.9 kΩ reading, setup otherwise unchanged. Further report: A→B 9.91 kΩ,
two initially unspecified A→R16 entries 9.94 kΩ each, R16 pads 2→3 22.4 Ω.
Operator subsequently clarifies A→pad 2 9.91 kΩ and A→pad 3 9.94 kΩ; earlier
reports are retained. Subsequent shorted probes read 0.1 Ω; latest isolated
value 9.90 kΩ with the J3 pin 8 resistor lead unplugged. Operator identifies
installed endpoints as J3 pin 8/J1 pin 4. Value accepted; four direct endpoint/
node/U1.B2 readings remain missing. The A→DUT_VIO connection check is being
guided with the resistor restored, power removed and both probes on that
supply-side connection. Its reply 9.45 kΩ was clarified as J3 pin 8→J1 pin 4,
so no direct supply-contact result exists. Physical probing is paused while
separate access to the correct two contact surfaces is clarified; no fault
is inferred from the connector-to-connector reading. Both blockers remain
open. Follow-up preservation snapshot includes the prior unstaged stopped-check
and history sections. Fresh documentation checks passed: all pre-follow-up
physical/HIL/history sections remain byte-for-byte outside new additions;
1,281 other snapshot files unchanged; four-file scope/staging/link/diff checks
passed. No software/hardware run or design change performed for this follow-up.
No physical acceptance is inferred from these documentation checks.

Revision A pull-up check, 2026-10-28: `validation/phase1b-revision-a` starts
from clean main `4c87383`, independently verified pushed before branch creation.
Themisto TH-M100 operator readings: pull-up supply→GND 0.0 V; DUT_VIO→GND
0.0 V; isolated external resistor **11.88 kΩ**, with DUT-TX-side lead unplugged
and all power connections removed. Operator identifies supply as DUT_VIO.
No numeric endpoint-continuity result; R16 pads and receiver-side alternatives
are not safely accessible. Physical check stopped, blocker #1 kept open; scope
work not performed. No resistor replacement or firmware/product/test/design
change; restoring the disconnected lead has not been reported. Nominal value,
marking/tolerance and exact R16 relationship remain unverified.
Preparation software gate (before these later operator replies): **1,569 passed
in 47.03 s**; Ruff passed; mypy passed/103 source files; offline lock passed/66
packages. No source/test changes followed; these software results are not a
physical pass. Fresh final documentation checks passed: baseline historical
sections preserved byte-for-byte outside new additions; all 1,281 other snapshot
files unchanged; exactly four allowed documentation files, staging empty;
new links/anchors and `git diff --check` passed. Complete diff retained for review.

Evidence-only reconciliation, 2026-10-28: clean `9ff33c1` matched the pushed
branch by independent HTTPS lookup (SSH authentication unavailable). No hardware
access, flashing, service startup or product/test/firmware/design/specification
edits. Exact §34 mapping/logic consistency and recorded-measurement requirements
were evaluated separately from the wider legacy checklist. The dated Revision A
reconciliation identifies the two unresolved evidence criteria and each deferred
qualification item; existing measurements are not upgraded to broader claims.
Fresh offline validation: **1,569 passed in 48.31 s**; Ruff passed; mypy
passed/103 source files; lock check passed/66 packages. Source comparison passed
17 pin assignments, five logic references and ordered firmware GPIOs/UART.
Preservation checks passed: original history and both HIL records remain
byte-for-byte outside new addenda; all 1,281 other snapshotted evidence files
are unchanged. Exactly four permitted documentation files changed, staging
empty; reconciliation links/anchors and final `git diff --check` passed.

The dated entries below retain their original validation and historical gap
wording; use Resume Here and the reconciliation for the current disposition.

Automatic-only Enhanced USB reconnect HIL, 2026-10-27: clean latest pushed
`14e6717` verified independently. Fresh gate **1,569 passed in 47.60 s**, Ruff,
mypy/103 files, offline lock/66 packages, architecture and diff/clean checks
finished before hardware startup. Sole service PID 5775, fresh native-v2 session
`20261027T180121Z-9ea027ae`; startup identity/config/telemetry/reset passed.
Automatic sequence **100 → 101 → 102 → 104 → 106 → 107 → 111** retains original
read failure, reconnect start, fresh segment/CTRL1+CTRL0 ACKs, success and one
immediate reset. Observer upper bound 4.579836 s < unchanged 5.0 s policy;
reset dispatch 0.379 ms after connected status. Positive old cleanup follows
the reviewed code gate; private flag/raw error-object snapshots are not exposed.
Fresh status, telemetry and normal boot RX resumed. Public APIs/CLI retrieval
passed; saved cursor 6..137/132 records matches native data. Clean stop verified
completed/service_shutdown and no PID/file/listener/serial owner or application
error. Final native 0..144/145 records, 126 RX bytes/13 RX records, six successful
control pairs, 115 ambient telemetry records, two segments/one gap; all 463 prior
session/config hashes preserved. No tests/second runtime/store while active.
Only startup/automatic path exercised; other accepted evidence reused. Current
unexpected USB reconnect criterion passed; Phase 1B/Stage 8/Phase 1 remain
incomplete for §34/Revision A gaps. Only report/status/history changed,
unstaged/uncommitted; final diff check passed. Full evidence/limits are in the
[Enhanced HIL report](../hardware/validation/phase1_enhanced_hil.md).

Enhanced terminal-read/cleanup software fix, 2026-10-27: branch
`fix/enhanced-terminal-read-cleanup` from latest pushed HIL-doc `df8e7a6`.
Installed Python 3.10 / pyserial 3.5 / pyserial-asyncio 0.6 traced and reproduced
with actual stream/serial transport code over test-owned pipes. Initial RED:
5 failed/7 passed; physical closure was mistaken for uncertainty, while normal
waiter success could falsely confirm incomplete close. Exact read-error identity
plus both serial-closed and transport-released checks distinguish cleanup facts.
14 new cases cover confirmed, failed, incomplete/unknown close, error preservation,
idempotence and the existing segment/configuration/success path. Focused
40 passed/0.49 s; broader Enhanced/backends/reconnect/ownership/runtime/recorder/
GPIO/protocol/service/CLI/architecture gate 925 passed/17.79 s. Full gate:
**1,569 passed in 47.42 s**; Ruff passed; mypy/103 files passed; offline lock/66
packages passed; final diff check passed. No hardware or unrelated behavior work.
Failed physical HIL report/session are unchanged; no physical pass is inferred.
Software/tests/status/history/reconnect clarification were accepted/pushed at
`14e6717`; the subsequent automatic USB physical result is recorded above.

Focused Enhanced physical control-generation HIL, 2026-10-27: clean latest
pushed `6d0c1a8` independently fetched before startup. Fresh software gate:
**1,555 passed in 46.31 s**, Ruff, mypy/103 files, offline lock/66 packages,
architecture and diff/clean checks passed before the sole hardware service.
Session `20261027T165848Z-b9a62f0b`: startup ACKs 3/5 and reset 6/8 passed;
release/external owner/reacquire staged segment 1 at 38, fresh ACKs 40/42,
success 43, immediate reset 45/47 passed. Automatic Pico 2 USB disconnect/start
303/304 faulted `cleanup_unconfirmed` before replacement; terminal metadata
retains `backend_input_error`, `read failed: [Errno 6] Device not configured`.
No third segment, automatic ACKs/success or reset; no retry/timeout change/fix.
CLI stop acknowledged but application shutdown logged the retained serial error;
PID/file/listener/serial ownership absent afterward. Native 0..304 reconciles
126 RX bytes/12 RX records, six successful control pairs, 273 ambient telemetry
records, two segments/two gaps. All 456 prior session/config hashes preserved.
No tests/second runtime/store during HIL; other accepted checks reused. Only
HIL report/status/history changed then and were committed at `df8e7a6`.
Phase 1B/Stage 8/Phase 1 remain incomplete. Full evidence and limits are in the
[Enhanced HIL report](../hardware/validation/phase1_enhanced_hil.md).

Enhanced control-generation software fix, 2026-10-27: branch
`fix/enhanced-reacquire-control-config` from latest pushed `90c744f`; no physical
hardware access. RED reproduced exact post-reacquire HTTP 409 `not_configured`
and automatic-reconnect failure, stale status and false successful initialization.
Review corrections add rollback of commanded boot mode after partial failure
and final-ACK readiness expiry, plus exactly one rejected-candidate cleanup owner.
GREEN covers 22 epoch/ordering/failure/deadline/cleanup/Interact cases;
ownership/runtime/Enhanced/GPIO/protocol/service/CLI/architecture suites:
911 passed in 18.33 s (including recorder), final lifecycle run 22 passed in 4.94 s.
Full gate: 1,555 passed in 46.89 s; Ruff passed; mypy passed/103 files; offline
lock passed/66 packages; architecture tests included; final diff check passed.
Graphify updated once (5,887 nodes); unchanged fixture header parser limitation
is recorded in history. No generated graph artifacts are included in the diff.
Failed HIL report/session remain unchanged; Phase 1B/Stage 8/Phase 1 remain
incomplete pending physical validation and required evidence. Software fix is
accepted/pushed at `6d0c1a8`; the subsequent focused physical result is above.

Enhanced real-hardware HIL, 2026-10-27: clean latest pushed `887768c` verified
again after exact accepted helper/DUT reference flashes. Separate Enhanced
profile resolved CTRL0/RUN and CTRL1/GP2; Basic config preserved. Fresh full gate
finished before service start: 1,533 passed in 43.44 s, Ruff, mypy/103 files,
offline lock/66 packages, architecture and diff checks passed. No tests/second
runtime/store ran while the service owned hardware. Session
`20261027T114440Z-7db24eae` passed continuous RX, initial first-byte retention,
Monitor/Interact/follow/console, boot-mode control, scoped telemetry and retrieval.
Release/external ownership/same-session reacquire produced one gap and segment 1,
but status still said CTRL0/1 configured while reset 739/740 returned
`not_configured`. Stopped without retry, GPIO reapplication or fix; unexpected USB
reconnect untested. Graceful stop/PID/listener/serial cleanup verified. Final
0..866 reconciles 510 raw bytes/47 RX records, eight TX pairs, six control pairs,
six bounded operations and 774 status records. All 448 earlier session files and
Basic config unchanged; `accepted_32k` and bounded physical evidence reused,
not repeated. Full evidence/limits/§34 disposition are in the
[Enhanced HIL report](../hardware/validation/phase1_enhanced_hil.md). Only that
report/status/history changed then; failed-run evidence committed at `90c744f`.

Bounded overflow physical diagnostic, 2026-10-27: clean `4692444`, independently
verified pushed before startup. Full software gate completed first: 1,533 tests
in 42.52 s, Ruff, mypy/103 files, lock/66 packages, diff check. No pytest or second
runtime/store ran during the service. FTDI identity/ownership/settings verified;
UF2 hash matched; first INFO confirmed `basic-ovf-20261027-3cbe8d2ee291`.
Fresh `20261027T105245Z-a78a6741`: initial INFO matched; one automatic reconnect
continued that session with segment 1/gap 1 within unchanged 5.0 s timeout.
Single post-reconnect INFO audit 11/12 accepted 5 bytes; RX 13 reported
line_len=90, prefix 29 `00`/3 `ff`, overflow=00, discarded_count=58,
suffix=`000000ff494e464f` ending in INFO; counts_overflow absent. Complete fields
and all 32 prefix bytes are in the Basic report. Terminal 14 timed out; no retry.
Stopped at trial 1/3 maximum, with no new product failure established or fix.
Graceful stop verified PID 44442 absent, no listener/serial owner; all 441 prior
session-file hashes/configuration unchanged. Native 0..14 reconciles 303 raw RX
bytes; saved-cursor retrieval preserved 6..14. Only diagnostic report/status/
history changed, uncommitted for review; `git diff --check` passed. Phase 1A
remains accepted; root cause and uncaptured middle bytes remain unknown.

Bounded overflow fixture preparation (before this physical run), 2026-10-27:
RED 7 failed/29 passed on
missing diagnostics; GREEN 36 focused cases passed in 9.73 s. Full pytest:
1,533 passed in 43.29 s, including architecture checks. Ruff, mypy (103 files),
offline lock check (66 packages) and `git diff --check` passed. Zephyr 4.4.0 /
SDK 1.0.1 cross-build `basic-ovf-20261027-3cbe8d2ee291` passed for `rpi_pico`,
115200/no flow control/no overlays. ARM compile confirms 16-byte added state;
UF2 structure/payload validated. New fields are overflow-only; valid and existing
non-overflow output is unchanged. Counts never wrap; inexact counts are omitted
with an explicit flag. No hardware, flash, service or new physical session was
used. At that stage reproduction awaited review/commit/push; this was not a
physical result or anomaly fix. Phase 1A remains accepted. Details/hashes are in
development history and the [Basic diagnostic record](../hardware/validation/phase1_basic_hil.md).

Instrumented physical diagnostic, 2026-10-27: clean pushed `69a0980`; full
software gate finished before service startup (1,527 tests in 39.73 s, Ruff,
mypy/103 files, lock/66 packages, diff check). No tests or other runtime/store
ran while the service was live. Operator confirmed externally flashed build
`basic-diag-20261027-d406684c5dff`; UF2 hash matched and initial INFO confirmed it.
Session `20261027T100353Z-1d5cd35f`: first INFO matched; one automatic reconnect
continued the same session with segment 1 and a durable gap, within unchanged
5.0 s timeout. Its single INFO then returned the complete diagnostic line with
`command_len=0 command_hex= discard=1` (RX 14); timeout terminal 15, no retry.
Ambient host RX 6 also contains NUL in the opposite direction to command ingress.
The observed path is known; discarded byte values/source and root cause are not.
Stopped for review after 1/5 maximum trials; no new product failure established.
Graceful stop verified PID 41181 absent, no listener or serial owner; all 434
earlier session-file hashes and configuration bytes unchanged. Native evidence
0..15 reconciles 153 raw RX bytes. Phase 1A remains accepted; diagnostic docs
only changed, uncommitted for review. `git diff --check` passed. Details are in
the [Basic diagnostic record](../hardware/validation/phase1_basic_hil.md).

Fixture byte diagnostics, 2026-10-27: 10 assertions failed RED on missing fields;
30 focused fixture tests passed GREEN, including the actual UART loop with host
I/O stubs. Full pytest: 1,527 passed in 42.33 s; Ruff, mypy (103 files), offline
lock check (66 packages) and `git diff --check` passed. Zephyr 4.4.0 / SDK 1.0.1
cross-build `basic-diag-20261027-d406684c5dff` passed for `rpi_pico`, 115200 baud,
no flow control/overlay. Unknown commands now report full handler bytes in hex
and assembler discard state; valid output and parsing semantics are unchanged.
No raw-line capture, hardware access, flash or new HIL occurred. The anomaly
remains unresolved/unclassified/non-blocking and Phase 1A remains accepted.
Detailed checks, artifact hashes and limits are in development history.

Acceptance contract audit, 2026-10-27: specification §§13.6, 14.2, 21.5 and 33
and the Stage 8 Basic HIL/exit criteria require successful reconnect and v2
acquisition/provenance, not a successful post-reconnect INFO. Existing evidence
shows reconnect success 76 in 3.138501 s, the same ownership session, fresh
segment 2, durable second gap, resumed RX 80 and responsive service. The extra
INFO's timeout is a truthful bounded result, not a failed reconnect gate.
All §33 criteria map to the fresh physical run plus its pre-start software gate;
default TX policy and bounded rollover are software-validated, not physically
forced. **Phase 1A Complete**; Stage 8/Phase 1B/Phase 1 remain incomplete.
This documentation-only audit ran no code tests or hardware and changed no raw
evidence, settings, timeouts or acceptance criteria. `git diff --check` passed.

Fresh Basic acceptance, 2026-10-27: clean pushed HEAD `31b14a4`; all software
checks finished before startup: 1,514 tests passed in 36.18 s, Ruff, mypy (103
files), offline lock check (66 packages), and diff check passed. No pytest,
additional runtime/store, or production/fixture patch occurred during HIL.
Operator reconfirmed Pico 1/H, build and wiring; reviewed UF2 hash matched.
Actual boot/INFO in new session `20261027T073956Z-7c038da2` identified the exact
reviewed build. Ambient RX, follow/detach, both Monitors, matched/elapsed/timeout
Interact, unrelated async RX, live console/post-exit RX and retrieval passed.

Dedicated delayed fault: ACK RX 48, durable terminal 49, ambient fault RX 50
outside `[45,50)`, 10.040059 s after ACK. Release completed in 0.673635 s:
final RX 62, intent 63, released 64, intentional gap; external PARTIAL exchange
and 6-second ownership hold passed. Reacquire 65..67 created segment 1 and its
first INFO matched. Unexpected disconnect/start 73/74, segment-open/success
75/76 established automatic reconnect in 3.138501 s with timeout still 5.0.

Additional post-reconnect INFO `[77,82)` timed out: exact 5-byte audit 78/79, RX 80
`E_COMMAND_001`, timeout terminal 81. No second INFO was sent. Cause remains
unclassified. Final CLI session/list, API and log warning all reported
`not_observable`. Native journal: 781 raw bytes, 20 RX records, 16 TX pairs,
10 completed operations, 3 segments, 2 gaps, contiguous evidence 0..81, raw
reconciled byte-for-byte. Journal ended normally as `completed/service_shutdown`;
the contract audit above establishes acceptance from the full evidence mapping.
Graceful stop released PID 33018/listener/serial
ownership. Prior evidence and configuration remain unchanged; only Basic HIL
report/status/history changed, uncommitted for review. Details are in the
[Basic HIL record](../hardware/validation/phase1_basic_hil.md).

Focused command diagnostic, 2026-10-27: clean pushed HEAD `04f2ff2`. Before
physical startup, 1,514 tests passed in 37.39 s; Ruff, mypy (103 files), offline
lock check (66 packages), and diff check passed. No tests or second runtime/store
ran during the physical service. Session `20261027T071337Z-3be5f126` contains
exactly two INFO Interacts, each one audited `494e464f0a` / 5-byte successful
acceptance. Both matched the reviewed build; first request was 72.269 ms after
the Basic source origin and the second began 0.576 ms after the first HTTP result.
No in-operation retry occurred. Native evidence is contiguous 0..10, with 148 raw
response bytes reconciled to two RX records. No earlier audited TX or host RX
was present in this fresh session; that does not establish Pico ingress state.

At that diagnostic, reviewed fixture code retained non-CR bytes until LF, then
cleared command state; unknown/overflow-discarded lines could emit `E_COMMAND_001`.
It provided no ingress echo or parser-state telemetry. Operator confirmed no
logic analyzer; actual wire bytes and earlier Pico RX/parser state remain unknown.
Host audit/acceptance does not prove wire bytes. No root cause or fix is claimed. Graceful stop released
PID 32203, listener and FTDI ownership. Configuration, production/fixture code
and prior sessions are unchanged. Details are in the
[Basic HIL record](../hardware/validation/phase1_basic_hil.md).

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
