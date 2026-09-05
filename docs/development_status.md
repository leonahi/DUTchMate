# Development Status

> Active phase: Phase 1
> Code baseline reviewed: `81491bb222a05f0b90fae0e1e0849b38dab6f305` on 2026-09-04
> Authority: the only project progress tracker and next-step queue

## Resume Here

Read this document first whenever development resumes.

- **Current milestone:** Phase 1A is accepted; Phase 1B now targets a
  non-wireless Raspberry Pi Pico 2 with its RP2350A MCU for the Enhanced Debug
  Helper. The firmware architecture is approved. Its host prerequisites now
  align required capabilities, canonical `dutchmate-rp2350` identity fixtures,
  and new `rp2350_timer` provenance while retaining read compatibility for
  legacy RP2040 session evidence. The initial RP2350 application now builds for
  the required target, owns the Revision A mapping and safe GPIO states, and
  now exposes its build-configurable USB CDC identity. Each DTR assertion emits
  one exact v1 `hello`; DTR loss forces safe GPIO state. Its portable UART RX
  core now enforces the 32 KiB byte-ring, bounded timestamp descriptors,
  drop-oldest, high-water, and overflow-episode invariants. UART0 now captures
  GP1 RX at fixed 460800 8-N-1 into that ring, sampling the RP2350 64-bit
  microsecond timer once per interrupt callback. Epoch start enables the shared
  UART translator only after `hello`; disconnect or driver fault stops RX and
  returns it to safe state. The sole CDC writer now drains bounded 1,024-byte
  chunks as exact v1 base64 UART events. Internal observation sequences prevent
  UART data from crossing a pending overflow record. The writer now emits exact
  v1 overflow records and one internally consistent buffer-status snapshot per
  second; one pending status snapshot coalesces to the newest sample while UART,
  overflow, and status evidence retain sequence order. The portable host-command
  NDJSON framer now enforces the exact 2,048-byte LF/CRLF boundary, returns one
  frame at a time, and resynchronizes after oversized input. The portable v1
  decoder now validates every committed command shape into typed values, and
  exact success/error encoders enforce response bounds and escaping. These
  components are target-compiled but intentionally not connected to CDC until
  execution and ordered response handling prevent silent command loss. A
  hardware-independent control owner now stores accepted `CTRL0`–`CTRL3`
  electrical modes, applies active/idle behavior with disable-before-data
  sequencing, runs bounded wrap-safe pulses, and returns channels to high
  impedance on recoverable faults or epoch end. Its Revision A adapter maps
  those ordered operations to the fixed enable/data GPIO arrays. A portable
  UART TX owner now copies bounded payloads, advances partial FIFO fills, waits
  for physical completion, and terminalizes timeout, cancellation, and driver
  faults without retry. Its RP2350 UART0 adapter shares the RX interrupt,
  protects ISR/thread state, and moves the PL011 software kick off the command
  caller. Both
  selected backends reconnect while idle and during active finite workflows
  through one service coordinator. Production Enhanced startup and each
  replacement use exactly one async host. The obsolete synchronous Enhanced
  command/source, hello,
  startup, and reconnect compatibility path is removed; shared runtime/workflow
  tests use backend-neutral semantic fakes, while wire behavior remains covered
  at the async adapter boundary.
- **Next step:** Continue Step 5 with a TDD-built hardware-independent command
  executor. Route typed configure, set-state, pulse, and UART-send commands to
  their existing owners; enforce one in-flight command, exact response mapping,
  and epoch cancellation. Keep it disconnected from CDC until those invariants
  pass. Keep EVENT pins reserved without capture and avoid a large plan.
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

Phase 1 is not complete. Phase 1A is accepted on the real Basic hardware path
using the deterministic Raspberry Pi Pico 1 DUT fixture and a generic FTDI
adapter. Phase 1B is partial: its atomic host wire migration, initial async
semantic/lifecycle/startup-selection slice, service-owned continuous ingestion
coordinator, continuous connection/integrity monitoring, and coordinated idle
and active reconnect are complete. The Enhanced host stack is async-only. The
RP2350 firmware cross-builds with its USB identity, connection-epoch hello,
portable 32 KiB RX ring, interrupt-driven UART RX/timestamp adapter, ordered
UART/overflow output, periodic buffer telemetry, and a bounded host-command
framer plus typed decoder/response encoder. Generic control and UART TX cores
plus their Revision A adapters are target-build verified. CDC command
execution/response routing remains incomplete; prototype and HIL validation
remain incomplete.

| Delivery area | Status | Evidence or remaining gate |
|---|---|---|
| Shared normalized host pipeline | Implemented | Basic and Enhanced fake sources use shared processing, workflow, and session boundaries. |
| Phase 1A Basic host adapter | Accepted | Mocked coverage plus sessions `20260826T211103Z-2649d369` and `20260826T211203Z-f541c8fb` prove real receive/send, storage, and retrieval through the generic adapter. |
| Shared sessions and evidence access | Implemented | Lifecycle, quotas, recovery, reconnect segments, retention, logs, wait-pattern, baseline designation/comparison, and UART send are tested. |
| Shared control/status contract | Implemented | Typed backend-input categories, bounded frame context, and operation/backend projection are covered without persisting offending input. |
| Phase 1B Enhanced host adapter | Host implementation complete; hardware acceptance pending | Target protocol migration, required timestamp/overflow capability alignment, RP2350 identity/timer migration, the reviewed fake-backed async adapter, production-capable one-resource serial factory, async semantic consumers, service lifecycle/startup selection, service-owned continuous ingestion, coordinated idle/active reconnect, and obsolete sync-path removal are complete. Production startup and each replacement use exactly one async host. |
| Zephyr DUT fixture | Implemented and Basic-HIL validated | The `rpi_pico` application cross-builds with Zephyr 4.4.0 and SDK 1.0.1; its reproduced UF2 matched the flashed image digest and the fixture passed the real Basic acceptance run. |
| RP2350 Debug Helper firmware | UART receive/telemetry/TX, portable USB protocol core, and generic control core target-build verified; command execution and HIL pending | The non-wireless Pico 2 application preserves the Revision A pin map and safe states. Identity, hello/epoch behavior, the ordered 32 KiB ring, interrupt-driven GP1 UART RX with RP2350 timestamps, bounded exact v1 evidence output, periodic buffer status, host-command framing/decoding, response encoding, generic control state transitions, and bounded UART TX completion are implemented. Revision A CTRL and UART0 adapters are compiled. CDC execution/routing and real-hardware behavior remain incomplete. The Pico 1 DUT fixture stays separate. |
| Revision A prototype validation | Not run | Electrical design is documented; physical validation evidence is absent. |
| Ring-buffer acceptance | Not run | The decision record remains `selected_unvalidated`. |
| Basic and Enhanced HIL acceptance | Basic passed; Enhanced not run | `hardware/validation/phase1_basic_hil.md` records the accepted Basic run; the Debug Helper path remains unavailable. |

The passing mocked/unit suite is necessary evidence, but it cannot substitute
for the real-hardware gates in the Phase 1 done criteria.

## Latest Validation

RP2350 UART TX implementation, reviewed 2026-09-05:

- TDD red failed all seven scenarios because the portable TX state machine was
  absent. Green covers null/zero/1,024/1,025-byte bounds, owned payload copying,
  busy rejection, partial FIFO progress, physical completion, and one exact
  `bytes_accepted` result.
- Zero, negative, and over-reported FIFO progress plus completion-check and
  mid-transmission driver faults terminate as `hardware_fault`. Later callbacks
  cannot retry or complete a terminal transmission.
- Timeout uses unsigned 64-bit elapsed time across timer wrap. A timed-out or
  epoch-cancelled partial transmission stops without retry and cannot report
  success.
- The RP2350 adapter uses the existing UART0 interrupt callback and a spinlock
  around portable state. A Zephyr work item contains the PL011 driver's
  synchronous initial TX kick so the future command/control caller can poll the
  100 ms internal deadline and preempt it on disconnect or fault.
- UART RX stop now cancels TX before disabling the bidirectional translator;
  UART driver faults terminate both directions. CDC commands still cannot start
  TX until the command executor and ordered response lane exist. EVENT pins
  remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,580 bytes flash, 63,912 bytes RAM, and an
  87,552-byte UF2 image.
- Focused TX/decoder gate: 14 tests passed.
- All 69 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,248 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real partial writes, physical-drain completion, timeout, disconnect, and UART
  signal integrity remain HIL gates because the prototype is unavailable.


RP2350 generic control implementation commit
`81491bb222a05f0b90fae0e1e0849b38dab6f305`, reviewed 2026-09-04:

- TDD red failed all seven initial scenarios because the portable control module
  was absent. Green coverage now exercises accepted open-drain and push-pull
  mappings, active/idle application, invalid and failed reconfiguration,
  unconfigured actions, and all four physical channels.
- Pulse coverage proves active drive, exact 1..10000 ms bounds, deadline restore,
  64-bit timer wrap, cancellation without late completion, and no successful
  completion when idle restoration faults.
- Every transition disables output before changing data and enables only a
  requested driven state. Enable failure performs a best-effort disable;
  channel faults retain accepted configuration for retry, while epoch end
  cancels the pulse, drives every channel high impedance, and discards mappings.
- The Revision A adapter binds the portable enable/data port to fixed
  `CTRL0`–`CTRL3` GPIO arrays. The target compiles it, but command execution does
  not instantiate the control owner yet. EVENT pins remain input-only and the
  EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. Linker allocation is unchanged before command-path
  integration.
- Focused control/decoder gate: 16 tests passed.
- All 62 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,241 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CTRL electrical sequencing and disconnect/fault behavior remain HIL gates
  because the Revision A prototype is unavailable in this workspace.

RP2350 typed command protocol implementation commit
`f6fbae41150783ef4206ec7288a5d969fb801f58`, reviewed 2026-09-04:

- TDD red first proved response encoding absent, then green covered exact plain,
  timestamped, UART-acceptance, and error frames plus limits, JSON escaping,
  UTF-8 validity, and Unicode control rejection. A focused red-green regression
  closed invalid multibyte continuation acceptance.
- A second TDD red proved command decoding absent. Green validates all
  four committed command types independent of field order, including escaped
  ASCII values, `CTRL0`–`CTRL3`, open-drain/push-pull electrical invariants,
  1..10000 ms pulses, active/idle states, and 1..1024 decoded UART bytes.
- Invalid/missing/unknown commands and malformed objects classify as
  `invalid_command`; missing, extra, duplicate, wrong-type, out-of-range, and
  invalid-base64 fields classify as `invalid_argument`. Failed decoding clears
  the typed output, so it cannot carry partial state into a hardware action.
- Systematic debugging isolated one wrong-type `data_b64` classification to a
  missing value-token check; the narrow fix preserves malformed-string
  classification and the focused decoder/response gate passes.
- The modules are target-compiled but CDC RX remains disconnected until command
  execution and ordered response routing exist. EVENT pins remain input-only
  and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. No decoder/response instance is allocated yet.
- All 53 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,232 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC command execution, response ordering, disconnect cancellation, and
  recovery remain HIL gates because the Revision A prototype is unavailable in
  this workspace.

RP2350 bounded host-command framing implementation commit
`c3ce6aa58d26f3531c4b735261ec8ecf4e87dcdf`, reviewed 2026-09-04:

- TDD red failed in all seven scenarios because the framer was absent. Green
  covers fragmented frames, multiple frames in one input chunk, CRLF handling,
  exact 2,048/2,049-byte boundaries, discard-through-LF resynchronization,
  disconnect reset, and invalid arguments.
- The framer retains at most 2,047 bytes and reports consumed input so its
  caller can hand off exactly one completed frame or oversize result at a time.
- The implementation is target-compiled but CDC RX remains disconnected until
  the command decoder and response path exist; complete commands therefore
  cannot yet be consumed without their required ordered response.
- EVENT pins remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image. No framer instance is allocated until CDC integration.
- All 40 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,219 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC input, frame handoff, disconnect reset, and error recovery remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 buffer telemetry implementation commit
`1bf616c5ac1b28096b2a1ceefc214793f988af89`, reviewed 2026-09-04:

- TDD red gates first proved both telemetry encoders and the periodic scheduler
  were absent, then proved status snapshots lacked ring observation ordering
  and atomic overflow staging.
- Green coverage verifies exact canonical `buffer_overflow` and `buffer_status`
  frames, full-width counters, invalid invariants and capacities, one-second
  scheduling, newest-pending coalescing, and UART/overflow/status ordering.
- Status snapshots receive their sequence inside the ring spinlock. Selecting
  and removing the next UART or overflow observation also happens atomically
  against the pending-status sequence; encoding and CDC writes remain outside
  the lock.
- DTR loss clears the pending status snapshot with the rest of the connection
  epoch. EVENT pins remain input-only and the EVENT translator remains disabled.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,036 bytes flash, 62,824 bytes RAM, and an
  86,528-byte UF2 image.
- All 33 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,212 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real CDC throughput, telemetry cadence, overflow ordering, and reconnect
  behavior remain HIL gates because the Revision A prototype is unavailable in
  this workspace.

RP2350 ordered UART event output commit
`aadefb0e279242a606bc405388b28019cec6322d`, reviewed 2026-09-03:

- TDD red gate failed in eight UART-event scenarios because the encoder was
  absent; green covers canonical output, binary data, base64 padding, maximum
  1,024-byte staging, 64-bit timestamps, channel bounds, and invalid sizes.
- A second ring TDD red gate proved observation ordering was absent, then green
  added internal 64-bit sequences and prevents a consumer from taking UART data
  ahead of an earlier overflow episode.
- The sole CDC writer emits one bounded UART event per scheduling pass. A
  pending overflow intentionally pauses later UART output until the next slice
  adds loss telemetry, avoiding evidence reordering.
- The 512 descriptors are now 24 bytes each (12 KiB) because they retain the
  internal observation sequence; this remains within the committed 8-16 KiB
  metadata budget and still requires HIL acceptance.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 41,484 bytes flash, 62,824 bytes RAM, and an
  83,456-byte UF2 image. RAM includes the 1,024-byte UART staging buffer,
  1,536-byte encoded-frame buffer, and expanded descriptor metadata.
- All 26 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,205 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real CDC throughput, overflow ordering, and reconnect behavior remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 UART RX and hardware timestamp adapter commit
`6129759b1652bc703b6c3baeeacb9ee17002ee0b`, reviewed 2026-09-03:

- Straightforward Zephyr peripheral initialization was target-build verified;
  no artificial TDD test was added, matching the approved test boundary.
- Generated devicetree selects UART0 GP0 TX/GP1 RX at 460800 baud. Source fixes
  8 data bits, no parity, one stop bit, and no flow control.
- ELF symbols confirm the 64-bit RP2350 `time_us_64` path and allocated RX ring
  are linked. Each IRQ callback samples once before draining its FIFO.
- The DTR lifecycle sends `hello` before enabling UART RX/translator. DTR loss
  and UART driver faults disable RX and return UART/CTRL/EVENT enables to safe
  state; EVENT pins remain input-only with no capture path.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 40,612 bytes flash, 56,152 bytes RAM, and an
  81,408-byte UF2 image. RAM now includes the allocated 32 KiB byte ring and
  8 KiB descriptor ring.
- All 18 portable firmware tests passed unchanged.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,197 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Real UART capture, timestamp, overflow, and disconnect behavior remain HIL
  gates because the Revision A prototype is unavailable in this workspace.

RP2350 portable UART RX ring commit
`285323983e1c4a35e6248c5c90bbe98553f73956`, reviewed 2026-09-03:

- TDD red gate failed in all seven scenarios because the ring implementation
  was absent.
- Focused green gate covers initialization, FIFO wrap, bounded descriptor
  staging, callback timestamp preservation across split drains, byte-space and
  descriptor-space drop-oldest behavior, oversized callback handling,
  overflow-episode coalescing, and disconnect discard with boot-cumulative
  counters preserved.
- The descriptor ring is fixed at 512 16-byte metadata entries (8 KiB); this
  remains subject to the committed RAM and HIL acceptance gates.
- All 18 portable firmware tests passed after integration with the prior hello
  and connection-epoch suites.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 39,212 bytes flash, 15,120 bytes RAM, and a
  78,848-byte UF2 image. The ring source is target-compiled but its storage is
  not allocated until the hardware UART adapter owns an instance next slice.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,197 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Hardware UART integration and ring load HIL were not run in this portable
  logic slice.

RP2350 USB identity and connection-epoch hello commit
`6bbee39b37ed35d41fa4d3b01372303038dcfb46`, reviewed 2026-09-03:

- TDD red gates failed as expected: eight hello tests first lacked the encoder,
  then three connection-epoch tests lacked the state machine.
- Focused green gate passed all 11 portable firmware tests, including the exact
  five-capability v1 hello, firmware-version bounds, and DTR edge semantics.
- Zephyr 4.4.0 with SDK 1.0.1 built warning-free for
  `rpi_pico2/rp2350a/m33`: 39,212 bytes flash, 15,120 bytes RAM, and a
  78,848-byte UF2 image.
- A production build retaining development VID/PID `2E8A:000A` failed at the
  intended compile-time guard. A validation build using replacement VID/PID
  `1234:5678` passed; these are test values, not assigned production identity.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,190 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- USB enumeration and DTR reconnect HIL were not run because the Revision A
  prototype is not available in this workspace.

RP2350 application and safe-I/O scaffold commit
`dcf8d8d94fd961055e236a3cb09941b9f7322ff6`, reviewed 2026-09-03:

- Zephyr 4.4.0 with SDK 1.0.1 cross-built the application for
  `rpi_pico2/rp2350a/m33` and generated a 27,648-byte UF2 image.
- Generated devicetree evidence preserves the exact Revision A UART enable,
  CTRL0–CTRL3 enable/data, EVENT enable, and EVENT0–EVENT3 GPIO ordering.
- Source inspection confirms EVENT channels have no interrupt registration or
  event-capture path; their translator remains disabled.
- No TDD test was manufactured for this straightforward peripheral-
  initialization slice, matching the approved firmware test boundary.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,179 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Physical startup voltage and translator-state HIL checks were not run because
  the Revision A prototype is not available in this workspace.

RP2350 identity and timestamp-provenance migration commit
`c8a9aba8278283421df79b8033f27b58aa44dd44`, reviewed 2026-09-03:

- TDD red gate failed in the expected two places because Enhanced segment
  normalization still emitted `rp2040_timer` and the canonical hello still
  identified `dutchmate-rp2040`.
- Focused green gate passed: 807 backend, protocol, session, runtime, service,
  and CLI tests. An explicit compatibility test proves legacy
  `dutchmate-rp2040` / `rp2040_timer` evidence remains readable.
- Active source/fixture search found RP2040 names only in the deliberate legacy
  timestamp type/reader support and its compatibility test.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,179 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

RP2350 capability-contract alignment commit
`816055db8990aeee07fc07b740aeaf0a8435320f`, reviewed 2026-09-03:

- TDD red gate failed in the expected five places because the schema and host
  parser rejected `device_timestamp` / `overflow_telemetry`, while the canonical
  hello omitted them; green gate passed all 109 focused protocol tests.
- Broader protocol/Enhanced gate passed: 299 tests.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,177 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

Previous RP2350 firmware architecture documentation commit
`31e9d4a50f6fa9aee012f23bb51dffaf469d7a47`, reviewed 2026-09-02:

- Architecture self-review found no placeholders, RP2040 target leakage, or
  unresolved scope contradiction. The known capability mismatch is explicit
  and assigned to the first implementation slice.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,173 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Firmware build and HIL validation were not run because firmware implementation
  has not started.

Previous sync-path removal validation based on implementation commit
`11e5bd24d665a8f113884acfc5f6cd509ba82909`, reviewed 2026-09-01:

- Focused removal gate passed: 195 tests across Enhanced adapter,
  serial-frame writing, reconnect/startup, runtime, GPIO configuration, and
  device-action workflow coverage.
- Ruff: `.venv/bin/ruff check .` passed with `All checks passed!`.
- Mypy: `.venv/bin/mypy` passed with no issues in 73 source files.
- Full Pytest: `.venv/bin/pytest` passed: 1,173 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- Exact stale-reference search found no remaining synchronous Enhanced adapter,
  transport, hello, startup, or reconnect compatibility symbols outside
  historical design/implementation records.
- The dependency-direction search for `apps` or `dutchmate_service` imports in
  `core/src` returned no matches.
- Graphify code update completed with 4,078 nodes, 11,006 edges, and 191
  communities. Its parser reported the existing Zephyr fixture header as a
  partial-extraction warning; source compilation/tests remain authoritative.

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
- bounded structured `invalid_argument` context for GPIO `role` and
  `dut_signal` identifier type, length, whitespace, and control errors.
- typed `not_configured` context with originating operation, required role,
  and exact unconfigured or rejected role state.
- typed Enhanced backend-input classification with operation/backend context
  and bounded frame sizes kept out of session metadata.
- continuous idle connection-state and Enhanced integrity projection through the
  existing status contract.
- coordinated idle and active reconnect for Basic and Enhanced, with production
  Enhanced startup and replacement retained on one async host, capability-
  compatible publication, and retained rejected-candidate cleanup failures.
- removal of the obsolete synchronous Enhanced command/source, hello, startup,
  and reconnect compatibility path.

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
- [x] Preserve bounded GPIO identifier `field`, `reason`, `max_bytes`, and
  applicable `actual_bytes` context through service validation.
- [x] Return `operation`, `required_role`, and `role_state` for every
  `not_configured` workflow failure.
- [x] Classify Enhanced `backend_input_error` context, including bounded frame
  sizes where required, without exposing offending input.

Exit gate: focused core/service/CLI tests and the full suite prove identical
validation order and response semantics for both backend modes.

### 2. Establish The Zephyr DUT Fixture And Accept Phase 1A

- [x] Add the small deterministic Zephyr DUT fixture firmware/configuration and
  document its supported board, build, flash, and UART scenarios.
- [x] Add a reproducible Basic HIL procedure and report template without making
  host assertions depend on Zephyr log formatting.
- [x] Run the real generic USB-to-UART receive/send, capture, storage, and
  retrieval smoke test.
- [x] Record adapter identity, DUT build provenance, DUTchMate session IDs, and
  results.

Exit gate: every Phase 1A done criterion has committed evidence; Phase 1A can be
marked accepted independently of Phase 1B.

### 3. Perform The Atomic Enhanced Protocol Migration

- [x] Rename `uart_capture` to `uart_receive` across schemas, examples, host
  models, parser, fixtures, tests, and future firmware handling.
- [x] Replace role-specific `reset` and `set_boot_mode` wire actions with
  generic `pulse_control` and `set_control_state` channel actions.
- [x] Remove host role and DUT signal metadata from firmware commands; those
  remain host-side policy/configuration data.
- [x] Enforce target NDJSON frame, decoded payload, whitespace, and validation
  limits consistently.
- [x] Prove that the host transport retries short writes to complete acceptance
  or reports known partial acceptance.

Exit gate: schemas, canonical examples, encoders, parser, protocol tests, and
firmware-facing contract fixtures change together with no legacy wire command
remaining.

### 4. Implement Continuous Ingestion And The Asynchronous Enhanced Adapter

- [x] Add a production-capable factory with one owned `pyserial-asyncio` reader,
  bounded framing, same-resource exact writes, hello validation, and exact-once
  failed-start cleanup.
- [x] Complete the fake-backed single-reader/dispatcher foundation with bounded
  FIFO event backpressure, serialized command routing, terminal-error and
  cancellation boundaries, waiter wake-up, capacity-one same-batch admission
  ordering, blocked-write close release, and exactly-once shutdown.
- [x] Route command responses to pending requests while publishing UART and
  telemetry events in FIFO order.
- [x] Prove command-path backpressure, terminal errors, cancellation, and
  shutdown under deterministic tests before production integration (Task 5).
- [x] Migrate Enhanced semantic control and UART-send consumers plus service
  lifecycle ownership, then select the async factory without creating a second
  reader. Enhanced startup and coordinated reconnect now use the same async
  host/adapter opener.
- [x] Add one service-owned continuous ingestion coordinator for the selected
  backend. It may consume the Basic adapter's existing async FIFO boundary but
  must not create a second Basic serial reader.
- [x] Continuously ingest and monitor connection state outside finite workflows
  for either backend.
- [x] Coordinate reconnect, hello/identity validation, source replacement, and
  segment origins without creating a second processing pipeline. Both backends
  now reconnect while idle and active; production Enhanced stays async.
- [x] Remove the obsolete synchronous compatibility path after all production
  consumers migrate.

Exit gate: shared fake-backend and transport tests cover interleaving,
cancellation/shutdown, malformed input, disconnect/reconnect, and bounded
queues; no production workflow imports Enhanced wire DTOs.

### 5. Implement RP2350 Debug Helper Firmware

- [x] Agree and record the initial firmware architecture, concurrency ownership,
  ring invariants, safe states, failure semantics, and test boundaries.
- [x] Align `device_timestamp` and `overflow_telemetry` atomically across the
  device schema, host capability parser, canonical examples, and tests.
- [x] Add the Zephyr RP2350 application for a non-wireless Raspberry Pi Pico 2
  using the normative Revision A pin map and the
  `rpi_pico2/rp2350a/m33` board target.
- [x] Update Enhanced identity fixtures and normalized timer provenance from
  RP2040-specific names to RP2350-specific names before firmware/HIL acceptance.
- [x] Implement build-configurable Enhanced USB identity with development
  VID/PID `2E8A:000A`, `device = "dutchmate-rp2350"`, and a required production
  VID/PID override.
- [x] Implement UART receive/send cores and RP2350 adapters, device timestamps,
  the 32 KiB drop-oldest RX ring, and buffer telemetry.
- [ ] Connect bounded USB command execution and ordered responses to the
  implemented protocol, UART, and control owners.
- [ ] Implement generic `CTRLn` configuration, pulse, and active/idle actions
  with safe startup/disconnect states and connect them to command execution.
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

- [ ] Run the RP2350 Debug Helper against the same Zephyr DUT fixture used for
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
