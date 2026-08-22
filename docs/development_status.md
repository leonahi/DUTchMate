# Development Status

> Active phase: Phase 1
> Code baseline reviewed: `8346c5b` on 2026-08-22
> Authority: the only project progress tracker and next-step queue

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Phase 1A completion and acceptance preparation.
- **Next step:** close the shared control and reporting contracts in checklist
  step 1 below.
- **First implementation slice:** audit the canonical Phase 1 service-error
  vocabulary against current core contexts and delivery projections, then
  implement the first missing error-specific structured context.
- **Do not start:** additional MCP/Phase 2 work while Phase 1 is the active
  phase, unless the user explicitly changes the priority.

Update the review date, current milestone, next step, checklist, and validation
evidence in the same commit as every completed development slice. Reconcile the
code-baseline reference after commits are created.
No other document owns progress or next-step status.

`docs/phase1_implementation_spec.md` remains the normative source for Phase 1
behavior and done criteria. Reference documents define durable contracts; they
must not duplicate this progress checklist.

## Phase 1 Assessment

Phase 1 is not complete. The shared host pipeline and most Phase 1A software are
implemented and covered by fake-backend tests, but Phase 1A has no recorded
real-hardware acceptance result. Phase 1B is partial: its host path still uses
an interim synchronous compatibility adapter, the target wire migration is not
complete, RP2040 firmware is absent, and prototype/ring-buffer/HIL validation
has not run.

| Delivery area | Status | Evidence or remaining gate |
|---|---|---|
| Shared normalized host pipeline | Implemented | Basic and Enhanced fake sources use shared processing, workflow, and session boundaries. |
| Phase 1A Basic host adapter | Implemented, acceptance open | Raw receive/send, provenance, reconnect, sessions, service, and CLI are tested; real generic-adapter HIL is not recorded. |
| Shared sessions and evidence access | Implemented | Lifecycle, quotas, recovery, reconnect segments, retention, logs, wait-pattern, baseline designation/comparison, and UART send are tested. |
| Shared control/status contract | Partial | Remaining error-specific structured contexts must be reconciled with the Phase 1 API contract. |
| Phase 1B Enhanced host adapter | Partial | Parser and finite synchronous adapter exist; target protocol and continuous asynchronous reader remain. |
| RP2040 Debug Helper firmware | Not started | `hardware/firmware/` contains no firmware implementation. |
| Revision A prototype validation | Not run | Electrical design is documented; physical validation evidence is absent. |
| Ring-buffer acceptance | Not run | The decision record remains `selected_unvalidated`. |
| Basic and Enhanced HIL acceptance | Not run | No reproducible fixture report or accepted real-hardware run is committed. |

The passing mocked/unit suite is necessary evidence, but it cannot substitute
for the real-hardware gates in the Phase 1 done criteria.

## Latest Validation

Working tree based on `8346c5b`:

- Ruff: passed
- Mypy: passed across 69 source files
- Pytest: 836 passed
- `git diff --check`: passed
- Basic HIL: no committed run
- Enhanced HIL: no committed run
- Ring-buffer decision: `selected_unvalidated`

## Already Complete — Do Not Reimplement

The following items are no longer backlog work:

- backend-neutral events, capabilities, timestamp provenance, and integrity;
- Basic raw UART receive and policy-gated complete UART send;
- shared capture, boot-test, literal wait-pattern, and UART-send workflows;
- native session lifecycle, bounded evidence, recovery, and reconnect segments;
- session list/detail, recent logs, stable pagination, and legacy read-only views;
- count-based retention with active and baseline protection;
- project baseline mark/replace/clear and bounded comparison;
- finite-workflow reconnect coordination and live reconnect status;
- deterministic line processing, pattern detection, and `first_error`;
- explicit public `device_timestamp_us` action fields plus accepted reset pulse,
  boot mode, and RFC 3339 action completion reporting;
- nullable commanded boot state with accepted-mapping initialization,
  certainty-aware invalidation, status/CLI reporting, and session snapshots.
- normalized boot-test reset evidence, including accepted pulse duration,
  segment timestamp provenance, atomic quota admission, and crash rollback.
- native-v1 evidence and log replay using `segment_id` as the sole timestamp
  epoch selector while retaining the recognized unversioned legacy shape.

## Active Queue — Phase 1

Work proceeds in this order. A step is complete only when its listed exit gate
passes and the evidence is committed.

### 1. Close Shared Control And Reporting Contracts

- [x] Replace legacy action/API `timestamp_us` fields with explicit
  `device_timestamp_us` while retaining raw wire naming inside the Enhanced
  protocol adapter.
- [x] Return accepted reset `pulse_ms`, boot `mode`, and RFC 3339
  `performed_at` values from Device Core, service, and CLI responses.
- [x] Track nullable `commanded_boot_mode`, invalidate it on disconnect or
  unknown/external state, expose it in status, and snapshot it at session start.
- [x] Persist the boot-test reset action, including `pulse_ms`, as normalized
  session control evidence.
- [x] Admit control-action evidence as one atomic quota unit.
- [x] Remove the redundant native-v1 `timestamp_epoch` compatibility field
  after all native readers and fixtures use `segment_id` exclusively.
- [ ] Complete remaining error-specific structured contexts identified by the
  Phase 1 API contract.

Exit gate: focused core/service/CLI tests and the full suite prove identical
validation order and response semantics for both backend modes.

### 2. Establish The Zephyr DUT Fixture And Accept Phase 1A

- [ ] Add the small deterministic Zephyr DUT fixture firmware/configuration and
  document its supported board, build, flash, and UART scenarios.
- [ ] Add a reproducible Basic HIL procedure and report template without making
  host assertions depend on Zephyr log formatting.
- [ ] Run the real generic USB-to-UART receive/send, capture, storage, and
  retrieval smoke test.
- [ ] Record adapter identity, DUT build provenance, DUTchMate session IDs, and
  results.

Exit gate: every Phase 1A done criterion has committed evidence; Phase 1A can be
marked accepted independently of Phase 1B.

### 3. Perform The Atomic Enhanced Protocol Migration

- [ ] Rename `uart_capture` to `uart_receive` across schemas, examples, host
  models, parser, fixtures, tests, and future firmware handling.
- [ ] Replace role-specific `reset` and `set_boot_mode` wire actions with
  generic `pulse_control` and `set_control_state` channel actions.
- [ ] Remove host role and DUT signal metadata from firmware commands; those
  remain host-side policy/configuration data.
- [ ] Enforce target NDJSON frame, decoded payload, whitespace, and validation
  limits consistently.
- [ ] Prove that the host transport retries short writes to complete acceptance
  or reports known partial acceptance.

Exit gate: schemas, canonical examples, encoders, parser, protocol tests, and
firmware-facing contract fixtures change together with no legacy wire command
remaining.

### 4. Implement Continuous Ingestion And The Asynchronous Enhanced Adapter

- [ ] Replace the interim synchronous message source with one owned
  `pyserial-asyncio` reader and bounded framing.
- [ ] Route command responses to pending requests while publishing UART and
  telemetry events in FIFO order.
- [ ] Add one service-owned continuous ingestion coordinator for the selected
  backend. It may consume the Basic adapter's existing async FIFO boundary but
  must not create a second Basic serial reader.
- [ ] Continuously ingest and monitor connection state outside finite workflows
  for either backend.
- [ ] Coordinate reconnect, hello/identity validation, source replacement, and
  segment origins without creating a second processing pipeline.
- [ ] Remove the obsolete synchronous compatibility path after all production
  consumers migrate.

Exit gate: shared fake-backend and transport tests cover interleaving,
cancellation/shutdown, malformed input, disconnect/reconnect, and bounded
queues; no production workflow imports Enhanced wire DTOs.

### 5. Implement RP2040 Debug Helper Firmware

- [ ] Add the Zephyr RP2040 application using the normative Revision A pin map.
- [ ] Finalize and implement the Enhanced USB VID/PID and identity used for
  host discovery.
- [ ] Implement USB protocol handling, UART receive/send, device timestamps,
  the 32 KiB drop-oldest RX ring, and buffer telemetry.
- [ ] Implement generic `CTRLn` configuration, pulse, and active/idle actions
  with safe startup/disconnect states.
- [ ] Enforce the final protocol limits and complete-write acknowledgements.
- [ ] Add build instructions and automated firmware-level tests where hardware
  is not required.

Exit gate: a reproducible firmware build implements the exact committed v1
schema and exposes the required identity/capabilities.

### 6. Validate The Revision A Prototype And Ring Buffer

- [ ] Build the first prototype with the documented provisional logic devices
  and exact Pico mapping.
- [ ] Record leakage, sequencing, isolation, voltage-level, UART signal
  integrity, and safe-state results.
- [ ] Record Zephyr RAM/stack usage and every load profile required by
  `docs/ring_buffer_sizing_plan.md`.
- [ ] Close `hardware/validation/phase1_ring_buffer.md` as `accepted_32k` or
  `revised_with_evidence`; do not waive failed criteria.

Exit gate: the prototype electrical checklist and ring-buffer decision contain
reproducible measured evidence.

### 7. Accept Phase 1B On Real Hardware

- [ ] Run the RP2040 Debug Helper against the same Zephyr DUT fixture used for
  Phase 1A.
- [ ] Demonstrate configured reset, boot-test, UART receive/send, device
  timestamps, overflow telemetry, reconnect behavior, and session retrieval.
- [ ] Confirm Basic and Enhanced runs produce the same downstream evidence
  structure, with only declared capability/provenance/integrity differences.
- [ ] Commit the HIL report with firmware, board, fixture, build, and session
  provenance.

Exit gate: every Phase 1B done criterion has committed evidence.

### 8. Run The Final Phase 1 Acceptance Audit

- [ ] Map every Phase 1A, Phase 1B, and shared done criterion to a passing test
  or committed HIL/measurement record.
- [ ] Run Ruff, mypy, the full pytest suite, and `git diff --check`.
- [ ] Remove completed migration compatibility code and stale status wording.
- [ ] Change this document to `Phase 1 complete` only when both hardware paths
  and every shared criterion pass.

Exit gate: no criterion is inferred from unit tests when it explicitly requires
real hardware, and no unchecked item remains in this list.

## Later Phases — Not Active

| Phase | Status | Resume condition |
|---|---|---|
| Phase 2 — MCP integration | Paused; dependency/client/server-composition foundations exist | Phase 1 completes or the user explicitly reprioritizes. Next slice is tool registration and error projection. |
| Phase 3 — hardware/protocol refinement | Not started | Phase 2 completion and Phase 1 measurements identify concrete refinements. |
| Phase 4 — AI debug reports | Not started | Deterministic evidence and MCP surfaces are accepted. |
| Phase 5 — advanced hardware evidence | Not started | Earlier phases are accepted and a concrete evidence requirement is approved. |

MCP work does not count toward Phase 1 completion. Existing Phase 2 foundations
remain intact but paused while Phase 1 is active.
