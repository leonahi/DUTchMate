# DUTchMate Phase 1 v2 Repository Migration Plan

> **Purpose:** temporary implementation plan for migrating the current repository to the approved `docs/project_context.md` and rewritten `docs/phase1_implementation_spec.md`.
>
> **Authority:** the two normative documents define behavior. This plan maps the current repository to those contracts; it must not redefine them. `docs/development_status.md` remains the only progress/next-step tracker.
>
> **Execution rule:** implement one stage at a time, keep each stage independently testable, and do not preserve obsolete runtime/session semantics solely for MCP, Debug Agent, or backward API convenience.

---

## 1. Repository Baseline and Main Gap

The inspected repository is the snapshot whose `docs/development_status.md` names code baseline `6d54acf0a11a3fa7a43eccfa753c2230cdaaad88` reviewed on 2026-09-24. The repository currently considers the old Phase 1A Basic behavior accepted and the old Phase 1B host/firmware behavior largely implemented.

Those historical results remain useful evidence, but they do **not** satisfy the newly approved Phase 1 contract because the product semantics have changed.

The central current runtime path is:

```text
Basic/Enhanced backend source
        |
        v
apps/service/ContinuousIngestionCoordinator
        |
        +-- idle: drain and discard normalized events
        |
        +-- finite workflow active: expose a temporary FIFO
                            |
                            v
                   CaptureWorkflow
                            |
                            v
                   schema-v1 session
```

The target path is:

```text
Basic/Enhanced backend source
        |
        v
one authoritative continuous recorder
        |
        +-- persist every admissible ambient RX/telemetry event
        +-- assign global session-local evidence_seq
        +-- maintain connection/session lifecycle
        |
        v
schema-v2 evidence session
        |
        +-- Monitor windows
        +-- Interact windows
        +-- standalone TX
        +-- Control actions
        +-- Follow/Console views
        +-- reconnect/release/reacquire segments
```

The migration is therefore primarily a change in **evidence lifetime, session ownership, operation semantics, and connection ownership**. It is not a reason to replace the proven Basic/Enhanced physical adapters or RP2350 protocol.

---

## 2. Keep / Modify / Retire / Add Inventory

### 2.1 Keep as architectural foundations

| Current area | Action | Reason |
|---|---|---|
| `core/src/dutchmate_core/backends/contracts.py` normalized UART/telemetry events | **Keep / extend** | Correct backend-neutral physical boundary. |
| `BasicBackendEventSource` one-reader model | **Keep** | Already provides one normalized FIFO reader and host timestamp provenance. |
| `BasicBackendConnection.send_uart()` ordered short-write handling | **Keep** | Matches target exact-byte transport behavior. |
| Enhanced async single-owner host | **Keep** | Correct resource ownership; adapt only around evidence/session lifecycle. |
| Enhanced NDJSON protocol, `uart_receive`, `uart_send`, `pulse_control`, `set_control_state` | **Keep** | Already matches the generic backend boundary and safe control model. |
| RP2350 timestamps and buffer telemetry | **Keep** | Required by the new spec; change where they are persisted, not their wire meaning. |
| `gpio_config/` role/mode/electrical validation | **Keep** | Product still requires host-side semantic roles and generic firmware channels. |
| `uart_capture/line_buffer.py`, `uart_capture/processor.py`, `log_processing/patterns.py` | **Reuse / adapt** | Raw-byte, bounded-line, and pattern logic remains valid. |
| session atomic write/fsync helpers and terminal-reserve principle | **Keep / extend** | Required by v2 durability rules. |
| retention, baseline, comparison, log replay concepts | **Keep / adapt** | Product still needs them, now with v2-aware semantics. |
| FastAPI service as sole process owner | **Keep** | Still the one local service boundary. |
| CLI as thin HTTP client | **Keep** | CLI remains first acceptance surface. |
| MCP as a separate service client | **Keep, migrate last** | Must consume proven Phase 1 semantics, not drive them. |

### 2.2 Modify substantially

| Current component | Required change |
|---|---|
| `apps/service/src/dutchmate_service/continuous_ingestion.py` | Replace active-workflow FIFO / idle discard semantics with or migrate into a core-owned continuous evidence recorder. |
| `core/src/dutchmate_core/runtime.py` | Remove finite-capture ownership as the central state; own active v2 session, operations, action arbitration, and expanded connection state. |
| `core/src/dutchmate_core/session_store/*` | Add schema-v2 writer/read models, global evidence ordering, new artifacts, rollover, operation/action/connection records; preserve v0/v1 read-only compatibility. |
| `core/src/dutchmate_core/workflows/capture.py` | Extract reusable matching/reconnect behavior and replace capture ownership with Monitor operation semantics. |
| `core/src/dutchmate_core/workflows/uart_send.py` | Make every TX audited in the active v2 session; remove forced-capture perturbation model. |
| `core/src/dutchmate_core/workflows/device_actions.py` | Preserve action logic but add attempt/result persistence and common action arbitration. |
| `core/src/dutchmate_core/backends/settings.py` | Fold into/bridge to first-class DUT Profile; add flow control, topology, selector, line ending, DTR/RTS policy/provenance. |
| `core/src/dutchmate_core/backends/basic.py` | Apply explicit DTR/RTS open behavior and effective serial settings; optionally expose `serial_line_control` only when configured/supported. |
| `apps/service/src/dutchmate_service/backend_reconnect.py` | Add explicit released state suppression, selector-based native USB reconnect, and reacquire semantics. |
| `apps/service/src/dutchmate_service/startup.py` | Resolve one DUT Profile, prepare v2 persistence before authoritative receive, publish initial segment, start recorder, and compose reconnect/action ports. |
| `apps/service/src/dutchmate_service/app.py` / `schemas.py` / `errors.py` | Add v2 endpoints and operation/error contracts; phase out legacy capture/wait contracts. |
| CLI client and commands | Add Monitor, Interact, Follow, Console, Release/Reacquire; explicit line endings; remove `--force`. |
| MCP client/server | After CLI acceptance, remap tools to Monitor/Interact/Control/session-v2 semantics. |

### 2.3 Retire after consumers migrate

The following are target-obsolete concepts, not permanent compatibility contracts:

- idle UART drain-and-discard;
- `CaptureWorkflowLifecycle.begin_workflow()` / `end_workflow()` as UART cursor ownership;
- `ContinuousIngestionCoordinator._workflow_active` and workflow-only FIFO;
- `DeviceCoreRuntime._capture_in_progress` as the global action exclusion mechanism;
- `SessionWorkflow = Literal["capture", "boot_test", "wait_pattern"]` as the identity of a native session;
- schema-v1 **new writes**;
- forced-send semantics and `--force`;
- `ActiveUartSendSession` as a special perturbation-only audit path;
- public `capture_active` conflict semantics for ordinary host operations;
- `discard_preexisting` as a way to manufacture a fresh physical capture stream;
- `/dut/capture` and `/dut/wait-pattern` once temporary wrappers are no longer needed;
- CLI `capture` / `wait` legacy semantics once users/clients are migrated;
- exact reconnect identity that requires the same path for a `native_usb_console` profile.

Do **not** mechanically remove the Enhanced protocol string `capture_active` merely because the host public error changes. Remove/change a wire error only if the firmware/protocol contract no longer has any valid producer/consumer and its protocol tests are updated atomically.

### 2.4 Add

Add cohesive ownership for these new concepts. Exact filenames may differ if a simpler fit is found, but dependency direction must remain core-first and framework-independent.

```text
core/src/dutchmate_core/
  profile/       resolved DUT Profile + digest/provenance
  evidence/      continuous recorder, durable cursor/range projection
  operations/    Monitor / Interact / common operation lifecycle
  connection/    connection state / ownership lifecycle policy
```

Do not create abstractions merely to match this directory sketch. A new module/package should own a real independently changing responsibility.

---

## 3. Cross-Cutting Invariants During Migration

Every stage must preserve these constraints:

1. Exactly one physical backend reader exists while connected.
2. Device Core remains independent of FastAPI, Typer, MCP, AI providers, and `httpx`.
3. Raw UART RX bytes remain authoritative; TX bytes never enter `uart_raw.log`.
4. Backend-specific framing terminates at the normalized backend boundary.
5. Basic and Enhanced feed the same host evidence/operation model.
6. New v2 writes never mutate or upgrade v0/v1 sessions.
7. Persist mutating attempt evidence before dispatch.
8. Never continue claiming authoritative recording after an unrecoverable persistence/ingestion fault.
9. A bounded operation never creates a second serial reader.
10. Do not let current MCP or Debug Agent consumers force retention of obsolete runtime/session semantics.

Use TDD for state machines, concurrency, persistence, reconnect, and externally visible contracts as directed by `AGENTS.md`.

---

# 4. Ordered Coding-Agent Stages

## Stage 0 — Adopt the New Normative Baseline and Reopen Phase 1

### Goal

Make the repository truthful before changing production code.

### Files

- replace `docs/project_context.md` with the approved new file;
- replace `docs/phase1_implementation_spec.md` with the approved rewritten file;
- update `docs/development_status.md`;
- append a short historical note to `docs/development_history.md` if needed.

### Required status change

The current status says old Phase 1A is accepted and only Revision-A physical acceptance remains. That is no longer sufficient under the new normative success criteria.

Update status to state, in substance:

- a Phase 1 semantic migration is active;
- prior Basic/Enhanced/HIL results remain historical evidence for physical/backend behavior;
- they do not prove continuous ambient recording, session v2, Monitor, Interact, follow/console, or release/reacquire;
- next step is Stage 1 DUT Profile/provenance.

Do not rewrite old history as if it never happened.

### Validation

Documentation-only checks plus `git diff --check`. Do not claim any new Phase 1 implementation requirement is complete.

### Exit criterion

There is one unambiguous target contract and one truthful progress tracker.

---

## Stage 1 — Introduce DUT Profile and Effective Serial Provenance

### Goal

Create the configuration/provenance model required by all later session and reconnect work **without changing physical runtime behavior yet**.

### Current code to reuse

- `core/src/dutchmate_core/backends/settings.py`
- `apps/cli/src/dutchmate_cli/config.py`
- `core/src/dutchmate_core/gpio_config/config.py`
- `apps/service/src/dutchmate_service/startup.py`
- CLI/service startup overrides.

### Implement

Introduce a resolved immutable DUT Profile containing at least:

- profile name;
- backend mode;
- serial selector/current exact path;
- reconnect timeout;
- topology: external UART vs native USB console;
- baud/data bits/parity/stop bits;
- RTS/CTS and XON/XOFF;
- TX policy;
- DTR/RTS requested open behavior;
- optional default line ending;
- Enhanced GPIO role/electrical configuration;
- device matching/selector data required for reconnect.

Add a canonical bounded projection and SHA-256 profile digest suitable for v2 metadata.

Keep `.dutchmate/config.toml` as the file-backed source. CLI startup overrides still win where supported, but the service receives one validated effective profile rather than independent loosely related settings.

### Likely code changes

- add `core/src/dutchmate_core/profile/`;
- adapt `backends/settings.py` to resolve transport settings into the profile or become a compatibility helper during the stage;
- adapt CLI `CliConfig` so daemon/session config remains delivery config while DUT configuration resolves through the profile model;
- expose effective profile/provenance in runtime status, initially without v2 storage;
- keep existing GPIO parser behavior, but make its accepted configuration part of the resolved profile projection.

### Tests

Add/focus tests for:

- conservative TX default false;
- 8N1 defaults and Enhanced fixed baud;
- flow-control validation;
- DTR/RTS configuration validation;
- invalid RTS-control + RTS/CTS conflict rejected;
- topology/selector validation;
- canonical digest stability;
- profile changes alter digest;
- CLI overrides produce the expected resolved profile;
- existing Basic/Enhanced startup still opens exactly one backend.

### Do not do yet

- no DTR/RTS physical manipulation beyond preserving existing behavior;
- no session-v2 writer;
- no release/reacquire;
- no new Monitor/Interact API.

### Exit criterion

Runtime/service status can expose one validated effective DUT Profile and its digest while existing behavior still passes.

---

## Stage 2 — Build Session Schema v2 Persistence Before Runtime Migration

### Goal

Implement the new evidence storage contract independently of live ingestion so the hardest persistence invariants can be tested deterministically first.

### Primary files

- `core/src/dutchmate_core/session_store/models.py`
- `metadata.py`
- `evidence.py`
- `persistence.py`
- `store.py`
- `retrieval.py`
- `retention.py`
- `log_replay.py`
- `baseline.py`
- `comparison.py`
- `transactions.py`
- existing `tests/unit/session_store/*`.

### Implement

Add native schema-v2 support with:

```text
metadata.json
uart_raw.log
uart_events.jsonl
operation_events.jsonl
hardware_events.jsonl
connection_events.jsonl
detected_patterns.json
.terminal-reserve   # active only
```

Introduce:

- v2 session creation/terminalization;
- contiguous `evidence_seq` allocation for every primary evidence unit;
- UART RX exact raw offsets + base64 equivalence;
- operation start/terminal records;
- UART TX attempt/result records;
- Control attempt/result records;
- connection lifecycle records;
- evidence positions/ranges;
- predecessor/successor rollover links;
- size rollover before an over-budget whole unit;
- segment rollover before segment 33;
- startup abandonment of stale active v2 sessions;
- unresolved attempt visibility after restart;
- v2 retrieval/list/detail/log replay;
- v2-aware retention protection;
- v2 baseline/compare rules.

### Compatibility

- keep v0 read-only compatibility;
- keep v1 read-only compatibility;
- stop creating new v1 sessions once runtime switches in Stage 3;
- do not upgrade historical directories in place.

Prefer discriminated v2/v1/v0 public projection models over pretending old v1 `NativeSessionDetail` describes v2.

### Important design constraint

A recorder must be able to preflight a complete evidence unit, roll over, publish the successor, and admit that whole unit without intentionally truncating it.

### Tests

Implement the spec's section 31.2 persistence tests before connecting live runtime, including:

- exact-boundary admission;
- rollover_size next-unit behavior;
- successor creation failure => persistence fault;
- 32 segments then rollover_segments;
- operation ranges spanning rollover;
- stale-active abandonment;
- retention protection;
- corrupt/unknown schema blocks destructive retention;
- metadata cap and terminal reserve;
- serialization/short-write/fsync/rename/disk-full fault injection.

Retain existing v0/v1 reader tests.

### Exit criterion

SessionStore can create, mutate, roll over, recover, retrieve, and retain schema-v2 sessions entirely through deterministic unit tests, while old sessions remain readable.

---

## Stage 3 — Replace Idle Drain/Discard with the Authoritative Continuous Evidence Recorder

### Goal

Make continuous recording the connection-level truth.

This is the deepest architectural stage. Keep it isolated from Monitor/Interact feature work.

### Current code that must change

- `apps/service/src/dutchmate_service/continuous_ingestion.py`
- `core/src/dutchmate_core/runtime.py`
- `apps/service/src/dutchmate_service/startup.py`
- reconnect callbacks that currently depend on workflow-active consumption.

### Target ownership

Move the authoritative evidence recorder into `dutchmate_core` (for example `evidence/recorder.py`). The service may still own physical reopen/composition callbacks, but service code must not decide whether a normalized UART event is evidence.

The recorder must:

1. own exactly one backend event source at a time;
2. continuously consume it while connected;
3. persist every admissible RX/telemetry event to the active v2 session;
4. assign contiguous `evidence_seq` through one serialization path;
5. update continuous line/pattern projections, including ambient `first_error`;
6. publish durable-tail notifications/cursors to operations/subscribers only **after** persistence;
7. handle source replacement without losing the evidence ordering contract;
8. treat internal recorder overflow/persistence loss as fatal evidence faults, not silent drops.

### Runtime changes

Replace these central fields/concepts:

- `_capture_in_progress`;
- `_active_session_handle` meaning "finite capture session";
- `_active_workflow: SessionWorkflow`;
- capture lifecycle start/stop as ingestion control.

with:

- active v2 ownership session;
- current connection state/segment;
- active bounded operation registry or minimal operation state;
- action/interact exclusivity state;
- durable evidence tail/cursor access.

A connected runtime should have an active v2 session even when no client operation exists.

### Startup order

Respect the spec ordering:

1. validate profile;
2. prepare persistence;
3. open backend;
4. validate Enhanced identity;
5. establish segment context;
6. durably publish segment;
7. start authoritative receive.

For Enhanced, verify that hello/open-time adapter buffering cannot silently lose interleaved DUT UART before the recorder starts. Do not add a second reader to solve this.

### Replace current coordinator tests

Current tests asserting fresh workflow FIFO semantics must be rewritten. Add the architectural proof tests:

- idle UART is stored;
- UART with no operation is later retrievable;
- one Interact-like action placeholder completes, then a delayed HardFault is still stored;
- reset/control marker followed by early boot RX is stored before any later Monitor;
- exactly one physical reader remains active;
- all primary events have contiguous sequence values;
- slow/nonexistent subscriber cannot alter recording;
- recorder persistence fault closes ownership rather than continuing silently.

### Exit criterion

With no Monitor/Interact endpoint implemented yet, starting the service and connecting a fake/real backend creates a v2 session and continuously persists ambient UART/telemetry until disconnect/shutdown/rollover.

---

## Stage 4 — Implement Monitor as a Bounded Window over Durable Evidence

### Goal

Replace finite capture ownership with bounded observation operations over the continuously recorded stream.

### Current code to migrate/reuse

- `core/src/dutchmate_core/workflows/capture.py`
- `runtime.capture_uart()`
- `runtime.wait_pattern()`
- `uart_capture/processor.py`
- `log_processing/patterns.py`
- service `/dut/capture`, `/dut/wait-pattern`;
- CLI `capture`, `wait`.

### Implement

Add a common bounded operation model:

- operation ID;
- validated completion mode;
- start durable cursor;
- monotonic deadline;
- terminal outcome;
- end cursor/evidence ranges;
- cancellation;
- optional matched condition reference;
- operation lifecycle records in `operation_events.jsonl`.

Implement Monitor modes:

- duration => `elapsed`;
- literal completion conditions => `matched` or normal `timeout` outcome;
- deterministic disconnect/reconnect continuation while both deadlines remain valid.

Matching must start at the operation cursor and must not search earlier history. Preserve the specified partial-line boundary rule.

### API/CLI

Add:

- `POST /dut/monitor`;
- CLI `dutchmate monitor --seconds ...`;
- CLI `dutchmate monitor --until ... --timeout ...`.

Legacy endpoints/commands may temporarily call the same Monitor implementation but must not create v1 sessions or independent readers.

### Tests

Add section 31.4 tests at core, service, and CLI levels. In particular:

- positive fractional duration and 300 s bound;
- invalid args cause no operation/persistence side effects;
- pre-start history does not match;
- partial line crossing start boundary does not create a false requested match;
- multiple-condition tie-break;
- condition timeout returns HTTP 200 operation outcome, not transport error;
- reconnect continuation/failure semantics.

### Exit criterion

`monitor` works through CLI against the same continuously persisted evidence stream; legacy capture/wait, if still present, are thin temporary aliases only.

---

## Stage 5 — Make UART TX Always Audited, Add Interact, and Migrate Control/Boot-Test Auditing

### Goal

Complete the deterministic action side of the product.

### UART TX changes

Refactor:

- `core/src/dutchmate_core/validation.py`;
- `core/src/dutchmate_core/workflows/uart_send.py`;
- runtime `send_uart()`;
- service `UartSendRequest` / endpoint;
- CLI send command/client.

Target semantics:

- byte-first payload model;
- exactly one of `data_b64` or text convenience form;
- explicit `none|lf|cr|crlf|profile_default` transformation;
- 1..1024 final bytes;
- no silent newline append;
- every TX attempt durably recorded before dispatch;
- result recorded after completion when possible;
- TX never written to `uart_raw.log`;
- standalone send allowed during read-only Monitor/follow;
- remove public `force` and capture-active coupling.

### Interact

Implement one exclusive bounded Interact operation:

1. admit operation start and establish start cursor;
2. admit TX attempt;
3. dispatch exact bytes;
4. persist TX result;
5. continue observing the existing evidence stream;
6. terminate on duration/condition/reconnect outcome;
7. persist operation terminal record;
8. return exact TX bytes + evidence ranges + match/quality facts.

Do not attribute every RX byte in the range as causally caused by the command; unrelated asynchronous output remains normal evidence.

### Control auditing

Keep existing `DeviceActionRunner`, GPIO role mapping, and Enhanced command semantics, but make reset/boot/GPIO mode changes use the same persist-attempt-before-dispatch rule and common action serialization.

Replace `_require_no_active_capture()` with explicit conflict rules:

- read-only Monitor does not block standalone TX/Control unless the spec says otherwise;
- Interact excludes other TX/Control/console TX;
- mutating actions serialize;
- release excludes in-flight mutating actions.

### Boot-test

Rebuild boot-test as a composite operation over:

```text
continuous recording already active
    -> reset Control action
    -> Monitor completion window
```

It must not start capture after reset.

### API/CLI

Add `POST /dut/interact` and CLI `interact`.

Update standalone send response to return resolved exact bytes/transformation and audit status.

### Tests

Add section 31.5 plus Control persistence tests:

- TX policy default false;
- exact line-ending transformations;
- no `force` target contract;
- attempt record precedes physical dispatch;
- unresolved attempts survive restart;
- send during Monitor succeeds when otherwise allowed;
- Interact exclusivity;
- Interact cursor established before TX;
- unrelated async RX remains in range;
- no automatic TX retry after reconnect;
- reset-before-Monitor early boot bytes already persisted;
- failed Control/TX still has correct audit evidence.

### Exit criterion

CLI can perform standalone audited send, deterministic Interact, reset/boot, and boot-test without any finite-capture ownership model.

---

## Stage 6 — Add Durable Evidence Cursor API, `follow`, and Human `console`

### Goal

Make DUTchMate usable as the developer's normal serial observation/interface tool so humans do not need to bypass the service.

### Implement

Add `GET /dut/evidence` with opaque cursor semantics and durable paging/long-poll behavior. It must read from persisted evidence, not a subscriber-only volatile queue.

Add CLI:

- `dutchmate follow`;
- `dutchmate console`.

`follow`:

- starts at current durable tail by default;
- prints new UART plus bounded lifecycle/action markers;
- Ctrl-C closes only the view;
- a slow client backfills from durable cursor or receives explicit cursor-gap/expiry behavior;
- never applies backpressure that can drop authoritative physical evidence.

`console`:

- combines follow with line-oriented service TX;
- never opens serial directly;
- uses explicit/default-resolved line ending;
- all TX is audited;
- console TX is rejected while Interact holds exclusivity;
- Ctrl-C exits only the client.

### Files

Likely:

- core evidence retrieval/cursor projection;
- session-store snapshot/read helpers;
- service app/schemas;
- CLI client;
- new CLI follow/console modules and commands.

### Tests

Implement section 31.6:

- no-cursor starts at tail;
- cursor preserves order across rollover;
- output byte cap drops whole records only;
- retention-deleted cursor => `cursor_expired`;
- follow connect/disconnect does not affect recorder;
- console never directly opens serial;
- explicit TX line ending/audit;
- console conflict with active Interact.

### Exit criterion

A human can leave DUTchMate running as the single serial owner and use `follow`/`console` for ordinary development without breaking the evidence trail.

---

## Stage 7 — Implement Explicit Ownership Lifecycle: Release/Reacquire, DTR/RTS, Native USB

### Goal

Close the remaining physical ownership gaps.

### Connection state

Expand runtime status from the current connected/disconnected/reconnecting model to:

```text
disconnected
connecting
connected
reconnecting
released
reacquiring
faulted
```

Do not use a single boolean as the source of truth.

### Release/reacquire

Refactor the current reconnect service/runtime split so:

- explicit release is distinct from unexpected disconnect;
- release intent/boundary is durably recorded before close;
- already-admitted evidence is flushed;
- reconnect worker is suppressed while released;
- released interval is an explicit observation gap;
- reacquire uses the resolved profile and opens a new segment;
- same active session continues after explicit release/reacquire when allowed;
- restart/failed session leads to a new session on later reacquire.

Add service endpoints and CLI `release` / `reacquire`.

### DTR/RTS

Extend Basic serial open/configuration so requested DTR/RTS behavior is explicit and provenance is recorded. Do not claim passive physical behavior that the driver cannot guarantee.

Add optional `serial_line_control` capability only when deliberately configured and physically supported. Never advertise it as `gpio_control`.

### Native USB

Replace the current reconnect identity rule `(mode, exact port, device, firmware)` where necessary with profile-defined selector semantics:

- external UART may require exact path;
- native USB may safely accept a changed path only when identity matching is unique;
- ambiguous discovery fails; never guess.

Expected reset-induced native USB disconnect is still a segment boundary/observation gap.

### Tests

Implement section 31.7/31.8:

- release disables auto reconnect;
- release marker/gap recorded;
- reacquire creates next segment;
- unexpected disconnect != explicit release;
- native USB path change accepted only under safe selector;
- ambiguity rejected;
- DTR/RTS requested/open provenance captured;
- RTS flow-control conflict rejected;
- release rejected during Interact/in-flight action.

### Exit criterion

Same-port external tools can take explicit ownership and return it without killing the service, and native USB reset/re-enumeration is modeled without fabricating continuity.

---

## Stage 8 — Enhanced Parity, Legacy Cleanup, Full CLI Acceptance, and HIL

### Goal

Finish Phase 1 against both physical backends and remove migration scaffolding.

### Enhanced parity checks

Verify—not redesign unless a failing requirement demands it—that:

- continuous Enhanced UART and telemetry are recorded outside operations;
- device timestamp provenance remains correct per segment;
- overflow telemetry updates v2 evidence/quality continuously;
- existing `pulse_control` / `set_control_state` and GPIO safety tests remain valid;
- reset/boot actions are v2-audited;
- no role metadata is sent on wire;
- EVENTn remains unadvertised in Phase 1;
- 32 KiB ring-buffer gate and existing firmware/HIL evidence are preserved.

Do not rewrite RP2350 firmware or protocol merely because host session semantics changed.

### Remove obsolete host compatibility

After all host consumers use target contracts, remove:

- old workflow FIFO APIs;
- capture session ownership code;
- `_capture_in_progress`;
- permanent `/dut/capture` and `/dut/wait-pattern` wrappers unless explicitly retained as documented CLI aliases without architectural branching;
- `force` request fields/options/tests;
- v1 new-session writer paths;
- stale public `capture_active` host errors;
- stale docs describing one-workflow-one-session.

Run reference searches before deletion.

### Debug Agent handling

Do not redesign Phase 4 during Phase 1. Preserve build/test health using the read-only compatibility layer. If the Debug Agent cannot yet consume v2, make that explicit rather than retaining v1 writes for it. A full v2 evidence-package migration can remain Phase 4 work.

### HIL acceptance

Run Basic first, then Enhanced, covering at least:

**Basic**

- service continuously records with no operation;
- follow shows live output;
- Monitor duration/condition;
- exact TX and Interact;
- delayed fault after Interact remains stored;
- release/reacquire with an external same-port tool or deterministic surrogate;
- retrieval/session-v2 provenance.

**Enhanced**

- same Monitor/Interact semantics;
- reset/boot-test with no first-byte race;
- timestamps;
- buffer telemetry/overflow evidence;
- configured reset/boot control;
- reconnect/session-v2 retrieval.

### Full validation gate

Run fresh:

```text
uv run --frozen ruff check .
uv run --frozen mypy
uv run --frozen pytest
git diff --check
```

If repository/environment policy requires non-frozen commands locally, record the exact commands actually run. Do not claim completion without fresh results.

Because this migration changes shared interfaces/dependency ownership, run one focused Graphify impact check/update near the end **if Graphify is installed/configured**, per `AGENTS.md`; verify any important relationship against source/tests.

### Documentation/progress

Update:

- `docs/software_architecture.md` if module ownership changed;
- `docs/reconnect_session_semantics.md` or retire/align it if the new normative spec supersedes conflicting material;
- `docs/developer_guide.md` and README examples for monitor/interact/follow/console/release;
- `docs/development_status.md` with concise current result/next step;
- `docs/development_history.md` with dated validation evidence.

### Exit criterion

All Phase 1A and 1B done criteria in the rewritten implementation spec are met through Device Core + service + CLI, with real-hardware evidence where required.

---

# 5. Post-Phase-1 CLI Acceptance — Migrate MCP, Then Resume Phase 4 Separately

Do this only after Stage 8 CLI/HIL acceptance.

### MCP

Update:

- `apps/mcp_server/src/dutchmate_mcp_server/service_client.py`;
- `server.py`;
- MCP tests;
- `docs/mcp_integration_plan.md` if its tool contract conflicts with the new Phase 1 API.

MCP should expose the already-proven deterministic service contracts rather than recreate timing/state logic. Remove MCP `force` and old capture/wait tool semantics once replacement tools are accepted.

### Debug Agent

Treat full schema-v2 evidence packaging as Phase 4 work. It may consume v2 only after its context/evidence contract is explicitly updated; do not put AI concerns back into Device Core.

---

## 6. Recommended Commit / PR Boundaries

Do not implement the migration in one coding-agent run or one giant commit. Recommended boundaries:

1. normative docs + development status;
2. DUT Profile/provenance;
3. session-v2 store/retrieval compatibility;
4. continuous recorder/runtime ownership;
5. Monitor;
6. audited TX + Interact + Control/boot-test;
7. follow/console;
8. release/reacquire + DTR/RTS + native USB;
9. Enhanced parity + cleanup + full CLI/HIL acceptance;
10. later MCP migration.

Each structural commit should have focused tests during implementation and the repository-required final validation before it is declared complete.

---

## 7. Critical Regression Tests That Must Exist Before Declaring the Migration Successful

These are the architectural proof tests, not optional examples.

### A. Ambient fault after operation

```text
Interact sends command
    -> response arrives
    -> Interact completes
    -> no Monitor/Interact active
    -> 30 seconds later DUT emits HardFault
```

Expected: HardFault is durably retrievable in the active v2 session.

### B. Reset/boot race

```text
continuous recorder already active
    -> reset action
    -> first boot bytes arrive
    -> later Monitor waits for READY
```

Expected: first boot bytes are present even if they precede Monitor start.

### C. One physical reader

Run Monitor + follow + retrieval concurrently.

Expected: exactly one backend reader; all clients observe projections of the same durable evidence stream.

### D. Persist-before-dispatch

Inject persistence failure when writing a TX/Control attempt.

Expected: physical action is not dispatched.

### E. Unknown result after crash

Persist action attempt, simulate process death before result.

Expected after recovery: attempt is unresolved/unknown, never fabricated as success/failure.

### F. Rollover under live traffic

Force session-size rollover while UART continues and an operation is active.

Expected: no intentionally lost evidence unit; one operation ID with multiple half-open evidence ranges across linked sessions.

### G. Explicit release gap

Release transport, let an external process own it, then reacquire.

Expected: no claimed UART during released interval; explicit observation gap; next connection segment is recorded.

### H. Native USB re-enumeration

Reset a native USB console whose path changes.

Expected: safe unique selector reconnects to a new segment; early physically unobservable USB boot interval remains an explicit gap.

---

## 8. Coding-Agent Working Instructions

For each stage, the coding agent should:

1. read `AGENTS.md`, `docs/development_status.md`, `docs/project_context.md`, and the relevant implementation-spec sections before editing;
2. inspect `git status` and existing diffs first;
3. use direct `rg`/source inspection for known symbols; use one focused Graphify query only when cross-module impact remains unclear and Graphify is available;
4. write focused regression tests before/with state-machine, persistence, concurrency, or public-contract behavior changes;
5. do not redesign requirements already settled by the normative spec;
6. do not preserve old code solely because MCP/Debug Agent still consumes it—migrate or explicitly defer those consumers;
7. avoid unrelated refactors;
8. run focused tests during implementation;
9. before declaring the stage complete, run Ruff, mypy, full pytest, and `git diff --check`;
10. update `development_status.md` and append detailed validation to `development_history.md` in the same completed slice.

---

## 9. First Coding-Agent Task

The first coding-agent task should be **Stage 0 only**:

> Replace the repository copies of `docs/project_context.md` and `docs/phase1_implementation_spec.md` with the approved versions. Reconcile `docs/development_status.md` so it truthfully states that the new Phase 1 semantic migration is active and that previous Basic/Enhanced acceptance remains historical evidence but does not satisfy the new continuous-evidence/session-v2/Monitor/Interact/follow/release criteria. Preserve historical completed work in `docs/development_history.md`. Do not change production code in this task. Run documentation consistency/reference checks and `git diff --check`, then report the exact diff and the proposed next Stage 1 task.

After that task is reviewed and committed, start Stage 1.
