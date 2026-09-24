# Development Status

> Active phase: Repository documentation cleanup — complete
> Code baseline reviewed: `618a8576db7b87fa71629110269d235d9799d7ef` on 2026-09-23
> Hardware evidence reviewed: 2026-09-17
> Authority: the only source for current progress, active phase, blockers, and next step
> History: completed slices and dated validation live in [Development History](development_history.md)

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Repository documentation cleanup is complete. Local and
  generated Graphify artifacts are untracked, completed working plans are removed,
  the repository entry point and documentation navigation are streamlined, and
  completed progress is separated from current status. Delivery Infrastructure is
  complete and the five-distribution `v0.1.0` release is published.
- **Active phase:** No development slice is active. The remaining Phase 1 hardware
  work is deferred by the user; Phase 4 evidence packaging is paused after VS Code
  host acceptance; the Debug Agent's public distribution remains deferred to
  `v0.2.0`.
- **Next step:** When the user resumes Phase 1 hardware work, add the replacement
  KiCad design under `hardware/pcb/debug-helper/rev-a/`, carry the 10 kOhm
  `UART_TX`-to-`DUT_VIO` correction into its schematic and BOM, audit all design
  assets, and verify the resulting artifacts.
- **Open blockers:** The populated-part and continuity audit, loaded hot-plug
  acceptance, pre-test baseline rejection, and 75 uA current correlation remain
  open. Analog UART edge and series-resistor waveform measurements require an
  oscilloscope. Claude Code host validation requires an authenticated subscription.

Update the review date, current milestone, next step, checklist, and concise
validation result in the same commit as each completed development slice. Add
detailed completed-slice and dated validation evidence to
`docs/development_history.md`; do not create another progress tracker.

`docs/phase1_implementation_spec.md` remains the normative source for Phase 1
behavior and done criteria. Reference documents define durable contracts; they
must not duplicate this progress checklist.

## Phase 1 Assessment

Phase 1 is not complete. Phase 1A is accepted on the real Basic hardware path.
Phase 1B protocol, async host ownership, continuous ingestion, reconnect behavior,
RP2350 firmware, 32 KiB ring-buffer acceptance, configured reset/boot-test,
UART-send, boot-mode, and shared evidence-shape gates pass. The Enhanced stack is
async-only and production startup/replacement owns exactly one host connection.

The remaining Phase 1 gate is physical Revision A prototype acceptance. Committed
evidence covers supported-voltage UART loopback and controls, supply ordering,
missing-supply isolation, control high impedance, representative reset behavior,
ring-buffer load profiles, and real Basic/Enhanced workflows. It does not replace
the outstanding populated-part/continuity, corrected-board, loaded-hot-plug,
current-correlation, and analog signal-integrity evidence required by the
normative done criteria.

| Delivery area | Current status | Remaining gate |
|---|---|---|
| Phase 1A Basic backend | Accepted | None. |
| Shared sessions, workflows, control, and reconnect | Implemented | Final Phase 1 audit after physical gates. |
| Phase 1B Enhanced host and firmware | Implemented; real workflow HIL passed | Revision A physical acceptance. |
| RP2350 32 KiB ring buffer | `accepted_32k` | None. |
| Revision A prototype | In progress and deferred | Corrected design plus remaining electrical evidence. |

Automated coverage is necessary evidence, but it cannot substitute for a done
criterion that explicitly requires real hardware measurements.

## Ordered Work Queue

No deferred item becomes active without user approval. If work resumes, use this
order unless the user explicitly selects a different milestone.

### 1. Deferred Phase 1 Hardware

1. Add and audit the replacement KiCad schematic, PCB, and BOM with the accepted
   10 kOhm `UART_TX`-to-`DUT_VIO` correction; keep EVENT pins reserved.
2. Inspect populated U1/U2/U3/U5/U6 markings and verify unpowered physical
   Pico-pin/net continuity.
3. Repeat loaded UART hot-plug acceptance on the corrected design and resolve the
   pre-test baseline rejection.
4. Correlate the unexplained 75 uA reading; perform analog UART cable/edge and
   series-resistor measurements when an oscilloscope is available.
5. Map every remaining physical criterion, run the final Phase 1 validation gate,
   remove any stale migration wording, and declare Phase 1 complete only if no
   criterion remains open.

### 2. Paused Phase 4 Evidence Packaging

- Review model-suggested source areas against the repository.
- Validate the Debug Agent CLI from Claude Code if an authenticated subscription
  becomes available. VS Code host invocation and local Ollama analysis already pass.

### 3. Deferred `v0.2.0` Debug Agent Distribution

1. Reconfirm whether the public interface remains a host CLI or adds an optional
   MCP analysis server without changing the deterministic Device Core MCP boundary.
2. Restore an aggregator extra or launcher only if that access model requires it.
3. Publish `dutchmate-debug-agent` with clean-install and provider-disabled-default
   acceptance as part of the coordinated `v0.2.0` host release.

### 4. Later Phase Roadmap

| Phase | Status | Resume condition |
|---|---|---|
| Phase 3 — hardware/protocol refinement | Deferred | Phase 1 measurements identify concrete refinements. |
| Phase 4 — AI debug reports | Paused | Source-area review or authenticated Claude Code host becomes available. |
| Phase 5 — advanced hardware evidence | Not started | Earlier phases are accepted and a concrete evidence requirement is approved. |

Phase 2 MCP integration and Delivery Infrastructure are complete; neither closes
nor waives a deferred Phase 1 hardware criterion.

## Current Validation Requirements

For every development slice, run Ruff, mypy, the full pytest suite, and
`git diff --check`. Use focused tests and source checks where the change requires
them. Record the concise current result here and append detailed dated evidence to
[Development History](development_history.md).

Repository documentation cleanup Task 4 migration checks, reviewed 2026-09-24:

- The pre-task committed status contained 2,580 lines. Five inventoried historical
  blocks—detailed validation, delivery infrastructure, completed Phase 4 work,
  Phase 2, and the already-complete summary—were mechanically compared and appear
  exactly once, byte-for-byte, in Development History.
- Rewritten current prose is limited to the former `Resume Here`, `Phase 1
  Assessment`, paused/deferred queues, and later-phase roadmap. Their active state,
  open blockers, ordering, and next step are represented above.
- Ruff passed; mypy reported no issues in 89 source files; all 1,435 pytest tests
  passed; and `git diff --check` passed.
