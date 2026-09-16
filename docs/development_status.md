# Development Status

> Active phase: Phase 1
> Code baseline reviewed: `28caf60f362220f0e8ec995ff708490e1ceea5c1` on 2026-09-16
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
  exact success/error encoders enforce response bounds and escaping. A
  hardware-independent control owner stores accepted `CTRL0`–`CTRL3` electrical
  modes, applies active/idle behavior with disable-before-data sequencing, runs
  bounded wrap-safe pulses, and returns channels to high impedance on
  recoverable faults or epoch end. Its Revision A adapter maps those ordered
  operations to the fixed enable/data GPIO arrays. A portable UART TX owner
  copies bounded payloads, advances partial FIFO fills, waits for physical
  completion, and terminalizes timeout, cancellation, and driver faults without
  retry. Its RP2350 UART0 adapter shares the RX interrupt, protects ISR/thread
  state, and moves the PL011 software kick off the command caller. A
  hardware-independent executor now routes typed configure,
  set-state, pulse, and UART-send commands to those owners. It holds exactly one
  command or response, acknowledges pulses only after idle restoration and UART
  sends only after physical completion, and discards work, responses, and CTRL
  mappings on epoch cancellation. Dedicated CDC RX and command/control threads
  now connect bounded framing and decoding to that executor through one static
  backpressure slot. The main USB TX owner prioritizes the executor's response
  lane without disturbing UART/overflow/status observation order. Command
  ingress starts only after `hello`; epoch end discards partial input, queued
  commands, and unsent responses. One bounded portable CDC TX owner now copies
  complete frames and advances only through exact Zephyr FIFO acceptance.
  Response/evidence acknowledgements follow full acceptance; invalid progress,
  250 ms without progress, driver faults, or DTR loss cancel the staged suffix
  and end the epoch without application-level replay. Both
  selected backends reconnect while idle and during active finite workflows
  through one service coordinator. Production Enhanced startup and each
  replacement use exactly one async host. Its concrete serial opener now holds
  DTR low through port configuration, input flushing, and async-reader
  attachment, then asserts DTR exactly once. This prevents pyserial's normal
  open-time input flush from discarding the firmware's one-shot epoch `hello`.
  The host applies portable 115200 line coding to the independent USB CDC port;
  the Enhanced setting remains the firmware-owned 460800 DUT UART rate.
  Pico 2 HIL now verifies the complementary firmware lifecycle: DTR must remain
  asserted for 100 ms, DCD/DSR publish device readiness, and a 64-byte CDC TX
  FIFO packet-paces multi-packet frames. Two consecutive epochs delivered the
  complete 175-byte `hello`. Sustained-runtime diagnosis then isolated a Zephyr
  4.4.0 PL011 error-interrupt storm; the application now enforces Zephyr 4.4.2,
  whose corrected driver acknowledges those interrupts. The patched build
  emits periodic telemetry, closes immediately, and passes consecutive real CLI
  start/status/stop cycles with all five capabilities.
  The obsolete synchronous Enhanced
  command/source, hello,
  startup, and reconnect compatibility path is removed; shared runtime/workflow
  tests use backend-neutral semantic fakes, while wire behavior remains covered
  at the async adapter boundary. The Step 5 audit confirms automated host-
  compiled coverage for every portable firmware boundary and records a
  reproducible Pico 2 target build. Firmware implementation is complete;
  electrical and broader workflow acceptance remain pending. Step 6 has now
  started on the assembled Revision A prototype. USB identity, preliminary
  missing-`DUT_VIO` safe-state behavior, 1.8 V debugger-unpowered leakage, and
  both settled supply orders are recorded. With all four DUT controls externally
  pulled up, VIO-first USB insertion/removal and debugger-first VIO application/
  removal retained the expected rail, control-output, and measured-enable
  levels. Direct measurements then confirmed that all four active-low control
  `/OE` nodes stayed at VIO through both supply orders whenever VIO was present.
  With debugger USB absent and its 3.3 V rail loaded through 10 kOhm, all four
  event and both UART connector signals also retained individual 1.8 V/10 kOhm
  pull-ups without raising any Pico power rail.
  Five VIO-positive-lead insertion/removal cycles with USB held on and five
  USB insertion/removal cycles with VIO held at 1.8 V then retained the expected
  settled rails, enables, `/OE` levels, and USB enumeration behavior.
  Analog UART cable/edge and series-resistor waveform validation is deferred at
  the user's request because no analog oscilloscope is available.
  An active Enhanced epoch at 1.8 V
  enabled only the UART translator, produced the expected 1.8 V DUT-side UART
  idle level, reported zero loss, and returned the measured UART enable and
  output voltage to 0.0 V after shutdown. The first loopback attempt then
  exposed a live CDC command-ingress defect: telemetry flowed but every host
  command timed out.
  The firmware now services RX and TX readiness in its shared CDC interrupt
  callback, drains RX through the Zephyr FIFO API, and transfers bounded bytes
  to the existing command thread. A repeatable invalid-command probe failed on
  the old and enable-only images and passed after the corrected image was
  flashed. The 1.8 V, 2.5 V, 3.3 V, and 5.0 V 460800-baud loopbacks each
  returned an exact 33-byte payload with zero reported loss or overflow. The
  25.2 uA
  unpowered, 28.93–28.96 uA powered 1.8 V, 39.96 uA powered 2.5 V, and 54.47 uA
  powered 3.3 V, and 79.66 uA powered 5.0 V idle results are within budget. The
  debugger-unpowered `3V3(OUT)` observation at 1.8 V collapsed from 0.13 V to
  0.02 V under a 10 kOhm load while average PPK2 current remained 75 uA and
  `VSYS`/`VBUS` remained at 0.0 V. This passes the specific loaded back-power
  check as high-impedance leakage or instrument offset, with the result kept
  instrument-limited because the DMM identity and calibration are unknown. The
  75 uA absolute current did not reproduce the earlier 25.2 uA idle reading and
  remains flagged for later controlled-load correlation. At 1.8 V,
  all four control channels now pass configured push-pull idle-low,
  active-high, return-to-idle, and epoch-disable measurements. Representative
  unrelated enables remained low. A controlled `CTRL0` run with the UART
  loopback continuously installed also remained connected with zero reported
  loss for five minutes. Representative `CTRL0` push-pull low/high,
  return-to-idle, and epoch-disable measurements now also pass at 2.5 V and
  3.3 V and 5.0 V. At 5.0 V, a second-channel discriminator also confirmed
  that the approximately 59 uA active-high current increase follows U3's
  expected state-dependent supply current rather than the DMM or one control
  path. Final shutdown returned to the disabled baseline with all measured
  enables and target signals low. At 1.8 V, representative open-drain reset
  assertion/release and loaded high-impedance behavior also pass against an
  external 10 kOhm DUT-side pull-up. A commanded 250 ms pulse measured
  250.853 ms with clean edges and returned to the released baseline. The test
  also exposed that the public 10,000 ms pulse limit exceeds the Enhanced
  adapter's fixed 1.0-second response timeout; the first correction then exposed
  the CLI's independent fixed 2.0-second HTTP timeout. Focused TDD now makes the
  adapter wait for `max(1.0 s, pulse + 0.5 s)` and the CLI wait for
  `max(2.0 s, pulse + 1.0 s)`. Real 2,000 ms and maximum 10,000 ms pulses both
  completed with clean measured edges, correct current, successful responses,
  and no Enhanced transport disconnect. Every control output also remained
  high-impedance through a Pico 2 `RUN` reset at 1.8 V against the external
  10 kOhm pull-up: each DUT line stayed at 1.8 V without a low glitch, all
  enables stayed low, current remained near 30 uA, and USB reappeared. A fresh
  pristine Zephyr 4.4.2/SDK 1.0.1 build now starts ring-buffer acceptance with
  an exact static memory baseline: 52,012 bytes flash and 78,032 bytes RAM,
  leaving 454,448 bytes of RP2350 SRAM. This pristine build is the starting
  memory baseline; the final normal image uses 81,040 bytes RAM, leaving 451,440
  bytes, with 15,168 bytes of fixed stacks and no system heap. Runtime stack
  high-water and load evidence are recorded in the ring-buffer acceptance
  record. The existing Pico 1 DUT fixture's 115200-baud Basic default did
  not meet the ring-buffer gate's 460800-baud requirement, so an opt-in
  devicetree overlay now selects 460800 without changing the accepted Basic
  image. Its Zephyr 4.4.0/SDK 1.0.1 candidate target-build passes with immutable
  build ID `phase1-enhanced-460800-001`. That candidate is now flashed, and a
  direct Saleae capture decodes its exact 62-byte build marker at 460800 8-N-1.
  Integrated boot attempts exposed that Pico 1 TX stays low during reset; the
  Debug Helper treated the resulting PL011 break/framing flag as a fatal driver
  fault and ended the epoch before the boot marker. Focused TDD now keeps
  positive UART line-error flags recoverable while retaining fatal behavior for
  negative driver API results. The corrected RP2350 image now passes HIL. Ten
  consecutive 15 s Enhanced boot sessions each retained the reset-induced
  `0x00` byte plus the exact 62-byte marker, a 62-byte ring high-water mark,
  zero overflow/loss, and one uninterrupted connection segment. The initial
  dense profile explicitly reconciled 8,825 retained plus 34,256 dropped bytes
  to its 43,081-byte output. A required no-stall `SUSTAIN` control then exposed
  that loss was not dense-only: 13,188 retained plus 81,111 dropped bytes
  exactly account for 94,299 bytes, with 17 overflow episodes and only a
  5,405-byte high-water mark. Source tracing found the USB loop drained one
  timestamp descriptor before an unconditional 10 ms sleep, capping output near
  100 descriptors/s while the fixture produced about 500/s. Focused TDD now
  drains bounded batches until idle and skips the idle wait while backlog
  remains. That first candidate improved the no-stall result to 52,541 retained
  plus 41,758 explicitly dropped bytes, but still failed with only a 4,019-byte
  high-water mark. The remaining limit was the 64-byte CDC TX FIFO: typical
  timestamped frames crossed its one-packet boundary and serialized USB
  completions. A focused configuration regression now requires frame-sized CDC
  staging, and a second candidate uses a 2,048-byte TX FIFO. All 97 Debug Helper
  host tests and a pristine RP2350 target build pass. HIL of that image reported
  zero firmware loss/overflow and only 160 bytes of ring occupancy, but the
  15 s host session persisted only 67,336 of 94,299 bytes and 2,925 of 4,096
  sequence lines. Source timestamps cover only about 6.145 s, isolating the
  remaining ceiling to the host's per-event durable session transactions.
  Focused TDD now batches up to 64 consecutive UART events into one existing
  crash-recoverable transaction while preserving exact records, processing,
  rollback, and quota-prefix behavior; wait-pattern remains single-event. The
  repeat no-stall session now passes with all 94,299 bytes, all 4,096 sequence
  lines, the exact checksum, zero overflow/loss, a 131-byte ring high-water
  mark, and one uninterrupted segment. A measured 104.328 ms host pause also
  retained that exact stream with zero loss/overflow and a 160-byte high-water
  mark. The formal 250 ms criterion now passes with a measured 250.255 ms pause,
  identical exact evidence, zero loss/overflow, and 160-byte high-water. A
  measured 505.137 ms pause also retained the identical exact stream with zero
  loss/overflow, 160-byte high-water, and no allocation, stack, watchdog, USB,
  or session failure. A corrected dense `BURST` then deliberately overflowed:
  15,691 retained plus 27,390 explicitly dropped bytes exactly reconcile its
  43,081-byte output, the END marker survived, and the session remained
  connected and uninterrupted with visible `loss_reported` integrity. USB-only
  runtime stack measurement now works on the Pico 2. Its first boot, measured
  505.093 ms backpressure, deliberate-overflow, and bounded maximum-payload
  HIL probes all returned eight thread/ISR high-water readings. The load and
  overflow evidence passed, but CDC RX used 3,872 of its 4,096-byte stack,
  leaving only 224 bytes. The 5,120-byte correction has now passed repeat Pico 2
  boot, measured 504.049 ms backpressure, and deliberate-overflow HIL. All eight
  stacks retained measured headroom; CDC RX kept at least 1,248 bytes free. The
  32 KiB ring decision is `accepted_32k`. Phase 1B Enhanced workflow HIL has
  now begun. A real configured `CTRL0` reset and 15-second boot test retained
  the exact Pico 1 fixture marker and device timestamps, but its first session
  inherited 23,663 dropped bytes from earlier MCU-lifetime telemetry. The host
  now separates those absolute counters from capture-window loss while retaining
  raw status evidence. A corrected repeat boot session completed with 63 exact
  raw bytes, zero current-session loss/overflow, and successful public session
  retrieval. A same-fixture forced `BURST` UART send during capture then retained
  19,079 bytes plus 24,002 explicitly dropped bytes, exactly accounting for the
  43,081-byte output with six current-session overflow records and visible
  `loss_reported` integrity. Controlled idle USB disconnect/reconnect then
  recovered on the same port. An active capture on the stack diagnostic image
  correctly failed its required identity check when that image advanced its
  stack-reading firmware identifier. After Pico 2 was flashed with the stable
  normal image, a 150-second capture resumed through an operator-controlled
  USB disconnect/reconnect within a configured 60-second window. Public
  retrieval confirmed two timestamp segments, disconnect/reconnect/
  discontinuity records, `interrupted` and `resumed` flags, zero reported
  loss, and UART evidence on both sides. The first fixture `PING` produced an
  unexplained generic command error despite the exact logged payload; two
  post-reconnect `PING` responses were clean. A focused current-code Basic/
  Enhanced capture contract test now passes for the same UART payload,
  artifact names, metadata/segment fields, normalized events, and public
  retrieval shapes; the accepted Basic and Enhanced HIL reports each verify
  real storage and retrieval. The historical Basic session files are absent
  locally, so their old field sets cannot be directly re-read. The configured
  `CTRL1` boot workflow now passes on the live GP2-wired Pico 1 fixture:
  normal boot, GP2-high `E_INIT_001` failure, and restored normal boot all
  retained exact markers, device timestamps, zero reported loss, and native
  session retrieval. The two normal raw artifacts have identical SHA-256.
  A post-restoration forced `PING` captured exact `PONG`; the earlier
  first-command anomaly did not recur, but its cause is still unestablished.
  The 75 uA idle-current discrepancy remains open and deferred at the user's
  request; the other Revision A electrical gates also remain open. The Phase 1
  acceptance audit now maps the Basic, Enhanced workflow, and shared software
  criteria to committed evidence. A source-level parser audit confirms all 17
  Revision A net/GPIO/physical-pin assignments across the normative table,
  Eagle schematic, Eagle board, and RP2350 overlay, plus the five provisional
  logic-device references in the design files. Live malformed mapping/mode
  requests left accepted CTRL0/CTRL1 state unchanged. The audit also found that
  `dut_io_voltage` stopped at TOML parsing; Enhanced startup could open the
  Debug Helper and GPIO configuration could dispatch without a trusted voltage
  declaration. Focused TDD now rejects a connected Enhanced startup before USB
  open when `hardware.dut_io_voltage` is absent and rejects direct control
  configuration before transport dispatch when no declaration is present.
  The populated-part identity and physical pin/net continuity audit is now
  deferred at the user's request. A loaded missing-`DUT_VIO` sweep then passed:
  with Pico 2 USB-powered and Device Core stopped, every interface/control
  enable measured 0.0 V; each of the four control, four event, and two UART
  external lines retained an injected 1.8 V through 10 kOhm while a separate
  10 kOhm load held `DUT_VIO` at 0.0 V.
- With debugger USB absent, `DUT_VIO` supplied at 1.8 V, and all four control
  outputs individually pulled up through 10 kOhm, every control remained at
  approximately 1.8 V while Pico `3V3(OUT)`, `VSYS`, and `VBUS` remained at
  approximately 0.0 V. This passes the static debugger-supply-absent control-
  output isolation check.
- Both settled supply orders then passed with the same four pull-ups: VIO-first
  USB insertion/removal and debugger-first VIO application/removal retained the
  expected VIO, control-output, debugger-rail, and measured-enable levels.
- Direct follow-up measurements passed the explicit all-order control-disable
  requirement: `DBG_CTRL_nOE0` through `DBG_CTRL_nOE3` remained at
  approximately 1.8 V in every VIO-present state through both supply orders,
  while all pulled-up control outputs stayed released.
- The reverse-direction translator isolation sweep also passed: with VIO at
  1.8 V, debugger USB absent, and `3V3(OUT)` loaded to ground through 10 kOhm,
  each UART and event connector signal retained its individual 1.8 V pull-up
  while `3V3(OUT)`, `VSYS`, and `VBUS` remained approximately 0.0 V.
- Repeated unloaded supply hot-plug also passed at 1.8 V. Five VIO lead cycles
  with USB held on and five USB cycles with VIO held on behaved identically;
  settled rails, enables, `/OE` levels, and enumeration remained correct.
- Analog UART cable/edge and series-resistor waveform validation is deferred at
  the user's request because no analog oscilloscope is available. The existing
  25 MS/s Saleae results remain digital functional evidence only.
- **Next step:** Continue with loaded DUT-cable hot-plug using the Pico 1
  460800-baud fixture and the live Enhanced capture path. Passive/ESD validation
  follows; full analog edge/cable acceptance remains deferred.
  The populated-part/continuity audit and 75 uA correlation remain deferred at
  the user's request. Resolve the transient first-`PING` fixture response only
  if it recurs. EVENT pins remain reserved; do not add event capture.
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
RP2350 firmware cross-builds reproducibly with its USB identity,
connection-epoch hello,
portable 32 KiB RX ring, interrupt-driven UART RX/timestamp adapter, ordered
UART/overflow output, periodic buffer telemetry, and a bounded host-command
framer plus typed decoder/response encoder. Generic control and UART TX cores
plus their Revision A adapters and the portable one-command executor are
target-build verified. Live bounded CDC ingress and shared evidence/response
scheduling are connected with explicit thread ownership. Bounded complete-frame
CDC driver acceptance is target-build verified. All portable protocol,
lifecycle, ring-buffer, control, UART TX, telemetry, command, and CDC TX
boundaries have automated host-compiled tests; prototype validation and HIL
remain incomplete. The production host serial opener deterministically sequences
DTR after its final input flush and async-reader attachment. Pico 2 HIL verifies
USB enumeration, two complete idle connection epochs, and real Enhanced CLI
startup, configured boot workflow, UART/load, and controlled active reconnect;
electrical acceptance remains.

| Delivery area | Status | Evidence or remaining gate |
|---|---|---|
| Shared normalized host pipeline | Implemented | Basic and Enhanced fake sources use shared processing, workflow, and session boundaries. |
| Phase 1A Basic host adapter | Accepted | Mocked coverage plus sessions `20260826T211103Z-2649d369` and `20260826T211203Z-f541c8fb` prove real receive/send, storage, and retrieval through the generic adapter. |
| Shared sessions and evidence access | Implemented | Lifecycle, quotas, recovery, reconnect segments, retention, logs, wait-pattern, baseline designation/comparison, and UART send are tested. |
| Shared control/status contract | Implemented | Typed backend-input categories, bounded frame context, and operation/backend projection are covered without persisting offending input. |
| Phase 1B Enhanced host adapter | Host implementation complete; startup, configured reset/boot-test, UART-send, reconnect, and boot-mode HIL passed | Target protocol migration, required timestamp/overflow capability alignment, RP2350 identity/timer migration, the reviewed fake-backed async adapter, production-capable one-resource serial factory, async semantic consumers, service lifecycle/startup selection, service-owned continuous ingestion, coordinated idle/active reconnect, and obsolete sync-path removal are complete. Production startup and each replacement use exactly one async host. Port configuration and the final input flush occur with DTR low; DTR is asserted only after async-reader attachment so the one-shot firmware `hello` cannot be flushed. The independent USB CDC port uses portable 115200 line coding instead of the firmware-owned 460800 DUT UART rate. Real CLI startup, configured `CTRL0` reset/boot workflow, forced `BURST` UART-send/capture, idle recovery, and a resumed two-segment active capture against Pico 2 pass. The host correctly interprets MCU-lifetime UART loss counters in fresh sessions while preserving raw status evidence. Configured boot-mode HIL now passes; electrical acceptance remains pending. |
| Zephyr DUT fixture | Implemented and Basic-HIL validated | The `rpi_pico` application cross-builds with Zephyr 4.4.0 and SDK 1.0.1; its reproduced UF2 matched the flashed image digest and the fixture passed the real Basic acceptance run. |
| RP2350 Debug Helper firmware | Firmware implementation complete; frame-sized FIFO is HIL lossless | The non-wireless Pico 2 application preserves the Revision A pin map and safe states. Identity, hello/epoch behavior, the ordered 32 KiB ring, interrupt-driven GP1 UART RX with RP2350 timestamps, bounded exact v1 evidence output, periodic buffer status, host-command framing/decoding, response encoding, generic control state transitions, bounded UART TX completion, one-command execution/cancellation, and live CDC command routing are implemented. The writer drains immediately ready outputs in bounded batches instead of sleeping 10 ms after every descriptor. The 2,048-byte staging FIFO holds the maximum encoded frame and permits continuous USB packet packing. Its first no-stall HIL run reported zero firmware loss/overflow and only 160 bytes of ring occupancy while exposing a downstream host persistence limit. After host batching, repeat HIL retained the exact stream with zero loss/overflow and only 131 bytes of ring high-water. The shared CDC callback services RX and TX readiness using the Zephyr FIFO APIs. Stable DTR, carrier-ready state, Zephyr 4.4.2 line-error handling, reset-line recovery, supported-voltage loopback/control, and representative reset HIL pass. Electrical margins, remaining baud rates, events, and broader load behavior remain incomplete. The Pico 1 DUT fixture stays separate. |
| Revision A prototype validation | In progress; static missing-supply isolation in both directions for every external digital signal, settled pulled-control supply ordering including direct `/OE` verification, repeated unloaded 1.8 V supply hot-plug, source mapping/config rejection, supported-voltage push-pull, representative open-drain reset, debugger-reset control high impedance, and the loaded `3V3(OUT)` check passed | `hardware/validation/phase1_revision_a.md` records the assembled prototype identity, preliminary safe-state observations, passing idle current, exact short-jumper 460800-baud UART loopback at all four supported VIO points, the passing four-channel 1.8 V push-pull control sweep, representative 2.5/3.3/5.0 V control levels, representative 1.8 V open-drain reset behavior against a 10 kOhm DUT-side pull-up, all four externally pulled-up control outputs remaining high-impedance through Pico `RUN` reset, and the instrument-limited loaded `3V3(OUT)` result. With debugger USB present and `DUT_VIO` absent, all ten externally injected signal lines remained at 1.8 V while a 10 kOhm load held `DUT_VIO` at 0.0 V and all enables remained low. With debugger USB absent and `DUT_VIO` at 1.8 V, every control, event, and UART connector signal retained an individual 1.8 V/10 kOhm pull-up while Pico `3V3(OUT)`, `VSYS`, and `VBUS` remained approximately 0.0 V; the UART/event sweep additionally loaded `3V3(OUT)` through 10 kOhm. Both settled supply orders retained the expected rails, pulled-up controls, measured enable levels, and active-low control `/OE` levels. Five VIO lead cycles with USB held on and five USB cycles with VIO held on retained the expected settled readings and enumeration. The committed design table, Eagle schematic/board, and firmware overlay agree on all mapped pins; populated-part identity and physical continuity are explicitly deferred. Invalid channel/mode and duplicate config assignments reject without changing accepted live state. Loaded cable hot-plug remains open; analog UART cable/edge, series-resistor waveform, and broader transient capture are explicitly deferred because no analog oscilloscope is available. |
| Ring-buffer acceptance | `accepted_32k` | Static RAM and fixture provenance are recorded, and ten consecutive representative boots pass. No-stall and 100/250/500 ms backpressure sessions retained the exact 94,299-byte stream with zero loss/overflow and uninterrupted epochs. Deliberate overflow sessions reconcile retained plus explicitly dropped bytes to the 43,081-byte fixture output with visible `loss_reported` integrity. The corrected 5,120-byte CDC RX stack passed repeat boot, 504.049 ms backpressure, and deliberate-overflow Pico 2 HIL with at least 1,248 bytes free. All eight stacks retained headroom, and final normal static RAM is 81,040/532,480 bytes. `hardware/validation/phase1_ring_buffer.md` records the decision. |
| Basic and Enhanced HIL acceptance | Basic passed; Enhanced configured reset/boot-test, UART send, reconnect, and boot-mode passed | `hardware/validation/phase1_basic_hil.md` records the accepted Basic run. Pico 2 USB hello, real CLI startup, host command response, exact short-jumper 460800-baud loopbacks at all four supported VIO points, a 15-second configured reset/boot-test capture with session retrieval, forced `BURST` UART-send/capture with exact loss accounting, idle recovery, and a resumed active capture with two segment timestamps, and normal/failure/restored-normal GP2 boot captures pass. A current-code same-payload contract test and both accepted HIL reports verify the shared downstream evidence shape. Broader electrical gates remain pending. |

The passing mocked/unit suite is necessary evidence, but it cannot substitute
for the real-hardware gates in the Phase 1 done criteria.

The acceptance audit currently resolves the normative groups as follows:

| Done-criterion group | Audit result | Primary evidence |
|---|---|---|
| Phase 1A Basic backend | Pass | `hardware/validation/phase1_basic_hil.md` and shared fake-backed host/service/CLI tests |
| Phase 1B protocol, host, firmware, and ring buffer | Pass | Protocol/firmware suites and `hardware/validation/phase1_ring_buffer.md` |
| Phase 1B real workflows and shared evidence shape | Pass | `hardware/validation/phase1_enhanced_hil.md` and the current-code Basic/Enhanced contract comparison |
| Shared Phase 1 session, duration, reconnect, retrieval, and backend-selection contracts | Pass | Full automated suite, including an explicit `hybrid` rejection case added by this audit |
| Revision A first-prototype electrical acceptance | Open | Source mapping and configured rejection checks pass; populated BOM/continuity and the remaining section 14 measurements are incomplete |

Phase 1 therefore remains active because the first-prototype done criterion
explicitly requires recorded leakage, sequencing, isolation, voltage-level,
and UART signal-integrity acceptance. The audit does not infer those physical
results from software tests.

## Latest Validation

Loaded missing-`DUT_VIO` isolation sweep, reviewed 2026-09-16:

- The user explicitly deferred the populated U1/U2/U3/U5/U6 identity and
  physical pin/net continuity audit. The 75 uA correlation remains separately
  deferred.
- Pico 1, normal `DUT_VIO`, and external pull-ups were disconnected. With Pico
  2 USB as the only normal supply and Device Core stopped, `3V3(OUT)` measured
  3.3 V while `DUT_VIO`, `DBG_UART_IF_EN`, `DBG_INPUT_IF_EN`, and all four
  `DBG_CTRL_ENn` points measured 0.0 V.
- A first unloaded `DUT_CTRL0` injection charged the floating `DUT_VIO` rail to
  1.8 V; both returned to 0.0 V after source removal. The run was repeated with
  a defined 10 kOhm `DUT_VIO`-to-ground load. A current-limited 1.8 V source
  through a separate 10 kOhm resistor was moved across all four `DUT_CTRLx`,
  all four `DUT_EVENTx`, `DUT_UART_RX`, and `DUT_UART_TX` connector lines.
  Every injected line remained at 1.8 V while loaded `DUT_VIO` remained at
  0.0 V.
- This passes the loaded missing-supply/high-impedance check for all ten
  external lines and the DUT-side-supply-absent half of translator isolation.
  No source-current measurement was taken, so absolute leakage remains open;
  the reverse-direction and all-order sequencing checks remained open at this
  point.

Debugger-supply-absent pulled-control isolation, reviewed 2026-09-16:

- Pico USB, Pico 1, UART, and event connections were absent. `DUT_VIO` was
  supplied at 1.80 V with a 1 mA current limit, and each of the four DUT control
  outputs had its own 10 kOhm pull-up to `DUT_VIO`.
- `DUT_VIO` measured 1.8 V and every `DUT_CTRLx` measured approximately
  1.8 V. Pico `3V3(OUT)`, `VSYS`, and `VBUS` each measured approximately
  0.0 V.
- This passes static debugger-supply-absent isolation for every control output
  at 1.8 V. Exact insertion/removal sequencing and direct UART/event loading in
  this supply direction remain open.

Pulled-control supply-order sequence, reviewed 2026-09-16:

- The four individual 10 kOhm control pull-ups were retained while Device Core
  remained stopped. With VIO applied first, USB insertion produced
  `DUT_VIO = 1.8 V`, all controls approximately 1.8 V, `3V3(OUT) = 3.3 V`, and
  every measured enable at 0.0 V. USB removal returned all three Pico rails to
  0.0 V while VIO and all controls remained approximately 1.8 V.
- With debugger USB applied first and VIO absent, VIO and all controls measured
  0.0 V, `3V3(OUT)` approximately 3.3 V, and every measured enable
  approximately 0.0 V. Applying VIO raised VIO and every control to
  approximately 1.8 V without changing the enable readings; removing VIO
  returned VIO and controls to approximately 0.0 V while `3V3(OUT)` remained
  approximately 3.3 V and all measured enables remained approximately 0.0 V.
- These settled readings pass the rail, external pull-up, and measured-enable
  expectations for both supply orders. The active-low `DBG_CTRL_nOE0` through
  `DBG_CTRL_nOE3` nodes were then measured in a direct follow-up.
- In the debugger-first order, all four `/OE` nodes and controls measured
  approximately 1.8 V after VIO application and approximately 0.0 V after VIO
  removal while `3V3(OUT)` remained at 3.3 V. In the VIO-first order, all four
  `/OE` nodes and controls measured approximately 1.8 V before USB connection,
  after USB connection, and after USB removal; the Pico rails remained
  approximately 0.0 V whenever USB was absent.
- This passes the settled all-order `/OE` pull-up and control-disable
  requirement. Transition waveforms remain unmeasured.

Debugger-supply-absent UART/event isolation, reviewed 2026-09-16:

- Pico USB was disconnected, `DUT_VIO` remained at 1.80 V with a 1 mA current
  limit, and Pico `3V3(OUT)` was loaded to ground through 10 kOhm. A second
  10 kOhm resistor pulled each `DUT_EVENT0` through `DUT_EVENT3`,
  `DUT_UART_TX`, and `DUT_UART_RX` high to VIO in turn.
- Every pulled signal measured approximately 1.8 V. Loaded `3V3(OUT)`, `VSYS`,
  and `VBUS` all measured approximately 0.0 V.
- Together with the preceding control sweep, this passes static debugger-
  supply-absent isolation for all ten external digital signals. Hot-plug/
  transient behavior, absolute leakage, and ESD validation remain open.

Repeated unloaded supply hot-plug, reviewed 2026-09-16:

- With Pico USB connected, all external signals disconnected, common ground
  retained, and the 1.80 V/1 mA source enabled, the positive `DUT_VIO` lead was
  connected and disconnected five times. Every cycle behaved identically:
  connected VIO measured approximately 1.8 V, disconnected VIO approximately
  0.0 V, `3V3(OUT)` remained approximately 3.3 V, and every enable remained
  approximately 0.0 V.
- With VIO then held continuously at 1.8 V, Pico USB was disconnected and
  reconnected five times. Every insertion enumerated and every cycle behaved
  identically. With USB connected, `3V3(OUT)` measured approximately 3.3 V,
  all enables approximately 0.0 V, and all four `/OE` nodes approximately
  1.8 V. With USB disconnected, all Pico rails measured approximately 0.0 V
  while VIO and all `/OE` nodes remained approximately 1.8 V.
- This passes repeated unloaded supply hot-plug at 1.8 V using settled readings.
  Loaded DUT-cable hot-plug and transition waveform capture remain open.
- The user then explicitly deferred analog UART cable/edge and series-resistor
  waveform validation because no analog oscilloscope is available. The 25 MS/s
  Saleae can retain digital decoding evidence but cannot close the analog
  waveform checks.

Phase 1 acceptance and voltage-safety audit, reviewed 2026-09-16:

- The normative Phase 1A, Phase 1B, and shared done criteria were compared with
  committed tests and HIL records. All software/protocol/workflow groups have
  evidence; the Revision A first-prototype criterion remains open.
- A source parser confirmed exact agreement for all 17 Revision A mappings
  between section 10.1, Eagle schematic `U4` pinrefs, Eagle board `U4` pads,
  and the RP2350 overlay. Eagle devicesets/board values match U1
  `TXU0202DCUR`, U2 `TXU0104PWR`, U3 `SN74LV4T125PWR`, and U5/U6
  `SN74LVC2G06DBVR`. This does not prove populated-part identity or physical
  continuity.
- With the 3.3 V Pico 1/Pico 2 fixture connected, malformed channel and
  electrical-mode requests returned CLI exit 2 and service HTTP 400
  `invalid_argument`; duplicate config assignment raised `GpioConfigError`.
  Accepted CTRL0/CTRL1 state, commanded boot mode, and connection state were
  unchanged. The service was stopped afterward.
- The audit found an unconsumed voltage declaration. Enhanced startup now
  requires `hardware.dut_io_voltage` before opening a configured serial port,
  and runtime GPIO configuration requires the declaration before transport
  dispatch. Focused tests observed both regressions fail before implementation
  and pass afterward. Out-of-range declarations remain rejected by the
  existing 1.8–5.0 V parser contract.
- A positive startup with the local trusted declaration set to 3.3 V connected
  the real Pico 2 as `dutchmate-rp2350` firmware `development`, advertised all
  five Enhanced capabilities, reported zero UART loss, and stopped cleanly.
  Its control channels remained unconfigured during this check.
- The deferred 75 uA correlation remains unresolved by user request.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,295 cases, and
  `git diff --check` passed.

Enhanced configured GP2 boot-mode HIL, reviewed 2026-09-15:

- The user wired Revision A `DUT_CTRL1` to Pico 1 GP2, retained
  `DUT_CTRL0` on `RUN`, left GP3 open, and kept 460800-baud UART, common
  ground, and `DUT_VIO=3.3 V`. The normal Pico 2 UF2 was in service. Public
  configuration accepted `CTRL0` open-drain active-low reset and `CTRL1`
  push-pull active-high/idle-low boot control. The operator held Pico 1
  `RUN` low during each GP2 mode change, then released it before each boot
  capture as required by the fixture strap procedure.
- Native 15-second boot sessions `20260915T203733Z-7d502d02` (`normal`),
  `20260915T204533Z-0d15abc2` (`bootloader`), and
  `20260915T204741Z-617d85d9` (restored `normal`) retained exact
  63/82/63-byte fixture output. The two normal raw artifacts share SHA-256
  `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`;
  the GP2-high run retained `E_INIT_001` with SHA-256
  `7ac5b2f71bfd7f1d4da1edf607407c8cfcec70c4e4cb9dc2fd333c6aa26481e4`
  and a detected `ERROR` in segment 0. Every session snapshotted its
  commanded mode, one accepted 100 ms reset, RP2350 device timestamps, one
  segment, `none_reported`/zero loss, and public session/log retrieval.
  Local assertions verified exact raw/event equivalence and control evidence.
- A post-restoration in-session forced `PING` capture
  `20260915T204855Z-51d462a8` returned exact `DMF/1 PONG\n` without
  a first error. The earlier transient first-command rejection did not
  recur; its cause is unestablished. Artifact hashes and action timestamps are
  in `hardware/validation/phase1_enhanced_hil.md`. The service was stopped
  after retrieval, returning its controls to high impedance.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,292 cases, and
  `git diff --check` passed.

Basic/Enhanced downstream evidence comparison, reviewed 2026-09-15:

- The accepted Basic Pico 1/FTDI HIL record and the Enhanced Pico 1/Pico 2 HIL
  record both verify raw UART, normalized events, native session storage, and
  public session/log retrieval through the shared pipeline. The historical
  Basic session files are absent locally, so their original field sets cannot
  be directly re-read.
- A focused deterministic current-code test sends the same `DMF/1 PONG\n`
  payload through fake Basic and Enhanced sources into the real
  `CaptureWorkflow`/`SessionStore` path. It passes equal artifact filename,
  top-level metadata, segment/backend, session-detail, and recent-log field
  sets; UART-event records and raw bytes are identical. Explicit backend
  identity, advertised capabilities, host/device timestamp provenance, and
  `not_observable`/`none_reported` integrity retain their declared mode
  distinctions. The test and comparison limits are recorded in
  `hardware/validation/phase1_enhanced_hil.md`.
- After binding the test's per-mode session ID factory, fresh Ruff passed,
  mypy found no issues in 73 source files, the full pytest suite passed 1,292
  cases, and `git diff --check` passed.

Enhanced idle and active USB reconnect HIL, reviewed 2026-09-15:

- With Pico 1 and the Revision A UART/control wiring left powered, the
  diagnostic Pico 2 image disconnected while idle at 20:05:00 UTC and
  reconnected at 20:05:30 UTC on the same CDC path. An active diagnostic-image
  capture `20260915T200703Z-d86f54e3` failed as `backend_input_error` after
  the image intentionally advanced its `hello.firmware` stack-reading
  identifier. Public retrieval preserved its one interrupted, unresumed
  segment and `usb_disconnect` evidence; the host identity guard behaved as
  specified.
- The operator flashed the normal Zephyr 4.4.2/SDK 1.0.1 Pico 2 UF2 SHA-256
  `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`.
  The replacement `hello` reported stable `development` identity and all
  five Enhanced capabilities. Using the documented 60-second reconnect
  setting for operator timing, active capture
  `20260915T201343Z-57c45321` disconnected at 20:15:00 UTC and resumed
  on the same port at 20:15:15 UTC. It completed after 150 seconds with two
  contiguous device-timestamp segments, `usb_disconnect`,
  `usb_reconnect`, and `timestamp_discontinuity` records, `interrupted`
  and `resumed` flags, no reported loss/overflow, and public session/log
  retrieval. The first segment retained a Pico 1 generic command-error line;
  two exact `PONG` lines were captured in the second segment. The first
  `PING\n` host payload and send acknowledgement were exact; the fixture
  rejection's cause is not established. Artifact hashes and the diagnostic
  image limitation are in `hardware/validation/phase1_enhanced_hil.md`.
  The service was stopped and the local reconnect setting restored to 5.0
  seconds after the run.
- Fresh final validation passed: Ruff `All checks passed!`, mypy found no
  issues in 73 source files, full pytest passed 1,291 cases, and
  `git diff --check` passed. Local HIL assertions also verified the idle
  state sequence, preserved diagnostic-image failure, two-segment normal-image
  resume, raw-byte/UART-event equivalence, and ordered lifecycle records.

Enhanced configured boot workflow and lifetime-counter host correction,
reviewed 2026-09-15:

- User-confirmed Pico 1 460800-baud fixture, Pico 2 diagnostic UF2, `CTRL0` to
  Pico 1 `RUN`, common ground, and `DUT_VIO=3.3 V` formed the live HIL setup.
  Initial session `20260915T192952Z-2cf24586` retained the exact 63-byte
  boot output and a successful 100 ms reset, but its first `buffer_status`
  carried the earlier dense run's absolute 23,663 dropped bytes and six
  overflow events. The host falsely marked this clean new boot as lost.
- After the host correction, session `20260915T194748Z-78db848e` again
  retained reset `0x00` plus the exact 62-byte
  `phase1-enhanced-460800-001` fixture marker. It completed in one segment
  with device `rp2350_timer` timestamps, `none_reported` loss, zero session
  overflow, no interruption, and successful public `dutchmate session`
  retrieval. Its 63 raw bytes have SHA-256
  `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`.
  The first raw `buffer_status` still records 23,663 lifetime dropped bytes
  and six lifetime overflow events; the firmware wire/evidence format is
  unchanged. Details and artifact hashes are in
  `hardware/validation/phase1_enhanced_hil.md`.
- Same-fixture session `20260915T195131Z-28e6d4b8` accepted a forced `BURST`
  UART send during capture and retained 19,079 plus 24,002 explicitly dropped
  bytes, exactly reconciling the 43,081-byte fixture output. Six current-session
  overflow records, BEGIN/END markers, `loss_reported` integrity, and one
  uninterrupted segment survived despite a nonzero MCU-lifetime starting
  counter. The service was stopped after the test.
- Regression tests cover prior lifetime counters, new status deltas, explicit
  overflow before the first status, two reconnect segments, and idle health
  projection. Fresh Ruff passed; mypy found no issues in 75 source files; all
  1,291 pytest cases passed; and `git diff --check` passed.
- The shared capture-storage port changed to pass capture-window counter totals
  without altering raw MCU status evidence. `graphify update .` refreshed the
  structural graph to 4,754 nodes and 12,575 edges. Its existing Zephyr fixture
  macro-heavy header warning did not affect the update.

Ring-buffer final stack and load HIL, reviewed
2026-09-15:

- The first USB-only diagnostic image measured CDC RX at 3,872/4,096 bytes,
  leaving only 224 bytes. The corrected image SHA-256 is
  `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66`.
  It reports `stackprobe-1` and all five Enhanced capabilities and froze all
  eight thread/ISR high-water readings after each revised workload.
- Revised boot session `20260915T191042Z-7b355b2a` retained the exact 63-byte
  reset byte plus fixture marker with zero loss/overflow and one segment. The
  504.049 ms backpressure session `20260915T191158Z-a59e0ff6` retained the
  exact 94,299-byte stream, all 4,096 numbered records and checksum 8,386,560,
  zero loss/overflow, and one segment. Dense session
  `20260915T191317Z-172eb838` reconciled 19,418 retained plus 23,663
  explicitly dropped bytes to the 43,081-byte fixture output with six overflow
  records, visible `loss_reported`, and one uninterrupted segment.
- Revised CDC RX high-water was 3,872/5,120 bytes under backpressure and
  overflow, leaving 1,248 bytes (24.4%); the other seven stacks kept 272–1,808
  bytes free. Final normal static RAM is 81,040/532,480 bytes, leaving 451,440
  bytes; the diagnostic build uses 82,136 bytes. No allocation, stack, watchdog,
  USB CDC, or lifecycle failure was observed. The ring record is `accepted_32k`.
- The corrected source passed Ruff, mypy on 73 application files and both HIL
  helper scripts, all 1,286 pytest cases, both Zephyr 4.4.2 RP2350 target
  builds, and `git diff --check` before the revised HIL. After the evidence/status
  update, fresh Ruff passed, mypy found no issues in 75 source files, all 1,286
  pytest cases passed, and `git diff --check` passed.

Revision A initial electrical validation record, reviewed 2026-09-11:

- The user confirmed that the connected hardware is a fully assembled Revision
  A translator prototype. macOS enumerated DUTchMate Debug Helper
  `2E8A:000A`, serial `FA63A4D787572B33`, at
  `/dev/cu.usbmodem11401`.
- With the DUT and `DUT_VIO` absent, pre-epoch, active-epoch, and post-epoch
  enable/output measurements were qualitatively as expected. Device Core
  reported the Enhanced backend connected with all control channels
  unconfigured, UART TX policy disabled, and zero reported loss. Exact numeric
  readings and calibrated instrument identity were not recorded, so those
  checklist items remain open.
- One initial direct adapter epoch received `hello` and then observed a USB
  re-enumeration through pyserial errno 6. A 4.119-second raw epoch and three
  further consecutive epochs did not reproduce it; all delivered complete
  `hello` and zero-loss `buffer_status` frames. The transient remains recorded
  for later reconnect/load correlation.
- With USB disconnected and `DUT_VIO` supplied at 1.80 V with a 1 mA current
  limit, idle current was 25.2 uA, below the documented 50 uA target. Pico
  `VSYS` and `VBUS` measured 0 V. Pico `3V3(OUT)` measured 0.13 V on an old,
  uncalibrated DMM.
- With `DUT_VIO` still at 1.80 V, connecting Pico USB while Device Core remained
  stopped produced a 28.93 uA steady-state `DUT_VIO` current. `DUT_VIO` remained
  1.8 V, Pico `3V3(OUT)` reached 3.3 V, and `DBG_UART_IF_EN`,
  `DBG_INPUT_IF_EN`, and all four `DBG_CTRL_ENn` signals measured 0.0 V. This
  passes the safe enable-state expectations for that VIO-first power-up
  sequence but does not prove output high impedance or cover every ordering.
- With `DUT_VIO` kept at 1.80 V and Device Core stopped, Pico USB was then
  disconnected. The operator reported that settled current, `DUT_VIO`, and all
  interface/control enable voltages were as expected. Exact values were not
  recorded, so this is preliminary power-down evidence rather than an accepted
  reproducible checklist result.
- With Pico USB connected first and Device Core stopped, applying `DUT_VIO` at
  1.80 V with a 1 mA current limit produced a 28.96 uA steady-state current.
  `DUT_VIO` measured 1.8 V, Pico `3V3(OUT)` measured 3.3 V, and every interface
  and control enable measured 0.0 V. This passes the measured enable-state
  expectations for that debugger-first power-up sequence but does not close
  the broader high-impedance or all-orderings checks.
- With Pico USB left connected and Device Core stopped, the bench supply was
  turned off and disconnected from `DUT_VIO` while common ground remained.
  `DUT_VIO` measured 0.0 V, Pico `3V3(OUT)` remained 3.3 V, and every interface
  and control enable measured 0.0 V. This passes the measured rail and enable
  expectations for that debugger-first VIO power-down sequence without proving
  high impedance or loaded leakage.
- With both rails powered and `DUT_VIO` at 1.80 V, an Enhanced 460800-baud epoch
  with UART TX policy disabled and controls unconfigured measured 28.93 uA,
  `DBG_UART_IF_EN = 3.3 V`, `DUT_UART_RX = 1.8 V`, and every unrelated enable at
  0.0 V. Device Core remained connected with zero reported loss. After clean
  shutdown, current measured 28.96 uA and both `DBG_UART_IF_EN` and
  `DUT_UART_RX` measured 0.0 V while all other enables remained 0.0 V. This
  passes the recorded static active/post-epoch voltage expectations, not UART
  output high impedance.
- The first DUT-side loopback attempt exposed a firmware CDC ingress defect:
  device-to-host telemetry continued, but `uart_send` and a raw invalid command
  both timed out. The registered CDC callback now drains RX readiness with the
  Zephyr FIFO API and queues bounded bytes to the command thread. The reusable
  command-ingress probe failed before the correction and passed after flashing
  the corrected 104,448-byte UF2 with SHA-256
  `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`.
- With the loopback installed, `DUT_VIO = 1.8 V`, and idle current at 28.94 uA,
  capture `20260910T192926Z-033765ed` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_1V8_460800_A5\n` payload at 460800 baud. The device
  accepted all 33 bytes; the session completed with zero reported loss, no
  overflow, one segment, and RP2350 timer provenance.
- At `DUT_VIO = 2.5 V`, idle current measured 39.96 uA, below the 60 uA target.
  Capture `20260910T193944Z-07bc3bc9` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_2V5_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance.
- At `DUT_VIO = 3.3 V`, idle current measured 54.47 uA, below the 70 uA target.
  Capture `20260910T194704Z-334fb7df` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_3V3_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance.
- At `DUT_VIO = 5.0 V`, idle current measured 79.66 uA, below the 100 uA
  target. Capture `20260910T195209Z-b9518e95` received the exact 33-byte
  `DUTCHMATE_LOOPBACK_5V0_460800_A5\n` payload at 460800 baud. The session
  completed with zero reported loss, no overflow, one segment, and RP2350
  timer provenance. This completes the short-jumper functional loopback sweep
  across all four supported VIO points; electrical margins and remaining baud
  rates are still open.
- At `DUT_VIO = 1.8 V`, `CTRL0` through `CTRL3` each passed configured
  push-pull idle-low, active-high, return-to-idle, and post-epoch disabled
  measurements. Enabled currents ranged from 68.0 uA to 68.76 uA; active-high
  DUT outputs measured 1.8 V, idle-low outputs measured 0.0 V, and post-epoch
  current returned to 28.90–28.95 uA with all target control signals at 0.0 V.
  Representative unrelated enables remained at 0.0 V.
- Two earlier `CTRL0` epochs entered the measured safe-disabled state and
  required USB power cycling. The operator later reported removing the UART
  loopback during the measurement, leaving the enabled `DUT_UART_TX` receiver
  floating. A controlled repeat with the loopback continuously installed held
  the configured idle-low state for five minutes with zero reported loss and
  did not reproduce the interruption. This is recorded as the likely cause,
  not a conclusively identified firmware fault, because no fault-source
  telemetry was available.
- At `DUT_VIO = 2.5 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Enabled current measured 93.71–94 uA, the active-high DUT output measured
  2.5 V, and post-epoch current returned to 39.98 uA with all target control
  signals at 0.0 V.
- At `DUT_VIO = 3.3 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Enabled current measured 122.60–122.70 uA, the active-high DUT output measured
  3.3 V, and post-epoch current returned to 54.60 uA with all target control
  signals at 0.0 V.
- At `DUT_VIO = 5.0 V`, representative `CTRL0` push-pull idle-low,
  active-high, return-to-idle, and post-epoch disabled measurements passed.
  Idle-low current measured 184.12 uA, the active-high DUT output measured
  5.0 V at 243.26 uA, and returned idle-low measured 183.96 uA. The active-high
  increase remained with the DMM disconnected and reproduced on `CTRL1`
  (183.44 uA idle-low, 243.13 uA active-high), identifying expected U3
  state-dependent input supply current rather than channel-specific leakage.
  After returning `CTRL1` idle-low at 183.78 uA, clean epoch shutdown returned
  current to 79.79 uA with all measured control and unrelated enable signals at
  0.0 V. This completes representative push-pull level validation across all
  four supported VIO points.
- At `DUT_VIO = 1.8 V`, `CTRL0` passed representative open-drain reset
  assertion/release and loaded high-impedance behavior against an external
  10 kOhm pull-up to `DUT_VIO`. Released current measured 29.34–30 uA with
  `DUT_CTRL0 = 1.8 V`; held assertion measured 239.44 uA with
  `DUT_CTRL0 = 0.0 V`. A Saleae measured a commanded 250 ms reset pulse as
  250.853 ms with clean edges and approximately 240 uA asserted current. Final
  shutdown returned to 29.87 uA, the external pull-up restored `DUT_CTRL0` to
  1.8 V, and all measured enables were 0.0 V.
- A pre-fix 10,000 ms reset request reproduced the fixed 1.0-second Enhanced
  command-response timeout. After correcting that layer, a 2,000 ms retry
  exposed the CLI's independent fixed 2.0-second HTTP timeout while the service
  and transport remained connected. Focused regression tests now require the
  Enhanced adapter to use `max(1.0 s, pulse + 0.5 s)` and the CLI to use
  `max(2.0 s, pulse + 1.0 s)`, while retaining their existing minima for short
  operations. Real 2,000 ms and maximum 10,000 ms reset commands then completed
  successfully. The Saleae measured 2.000 s and 10.00 s with clean 1.8 V/0.0 V
  edges; PPK2 measured approximately 240 uA asserted and 30 uA released. Status
  after each command remained connected in the same Enhanced epoch with
  `CTRL0` configured and zero reported UART loss.
- TDD red first proved a 2,000 ms pulse still received only the old 1.0-second
  Enhanced timeout, then separately proved the CLI still assigned its old
  2.0-second HTTP timeout. The focused Enhanced and CLI suites passed with 77
  tests after both corrections. Ruff passed; mypy reported no issues in 73
  source files; full pytest passed with 1,276 tests; and `git diff --check`
  found no whitespace errors.
- With the service stopped, `DUT_VIO = 1.8 V`, and an external 10 kOhm pull-up
  moved across `DUT_CTRL0` through `DUT_CTRL3`, every DUT control output stayed
  at 1.8 V without a low glitch while the Pico 2 `RUN` input was grounded for
  approximately one second. Target enable/data signals and all unrelated
  enables remained 0.0 V, PPK2 current stayed near 30 uA, and the RP2350 USB
  device reappeared after release. This passes the every-control-output
  debugger-reset high-impedance item at the representative 1.8 V point.
- With Pico USB and Saleae signal leads disconnected, the PPK2 supplied
  `DUT_VIO = 1.8 V` at a 1 mA limit. Pico `VSYS` and `VBUS` remained 0.0 V.
  Loading Pico physical pin 36 from `3V3(OUT)` to ground through 10 kOhm
  collapsed the unloaded 0.13 V reading to 0.02 V; average PPK2 current stayed
  at 75 uA and maximum current changed from 85 uA to 82 uA. This passes the
  specific debugger-unpowered source-impedance check as high-impedance leakage
  or instrument offset. It remains instrument-limited because the DMM identity,
  calibration, accuracy, and input impedance are unknown. The 75 uA absolute
  reading did not reproduce the earlier 25.2 uA idle measurement and remains
  flagged for controlled-load correlation.
- A pristine `rpi_pico2/rp2350a/m33` build at application commit
  `3e149a530bfa6fd2b29682874f2942d619d7a30c` reproduced under Zephyr 4.4.2 and
  SDK 1.0.1. It used 52,012 bytes flash and 78,032 of 532,480 RAM bytes. The
  complete 45,136-byte RX-ring object contains the selected 32,768 raw bytes,
  512 timestamp descriptors, and accounting state. Configured stacks total
  14,144 bytes, the system heap is zero, and 454,448 bytes of static RAM margin
  remain. The 104,448-byte UF2 SHA-256 is
  `c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`,
  matching the digest of the file previously reported as flashed; no Pico
  readback was performed. Runtime stack high-water and HIL load profiles remain
  open; detailed ignored-tree artifacts and hashes are recorded in
  `hardware/validation/phase1_ring_buffer.md`.
- The accepted Pico 1 Basic fixture defaults to 115200 baud, which cannot drive
  the fixed 460800-baud Debug Helper ring-buffer profile. A new opt-in
  `rpi_pico_460800.overlay` preserves that Basic default while setting UART0
  `current-speed` to 460800 for Enhanced HIL. A pristine Zephyr 4.4.0/SDK 1.0.1
  target build confirmed generated `current-speed = < 0x70800 >` and immutable
  build ID `phase1-enhanced-460800-001`. The 34,304-byte candidate UF2 SHA-256
  is `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6`.
  It was flashed on 2026-09-12. A direct 25 MS/s Saleae capture decoded the
  exact 62-byte build marker at 460800 8-N-1. Integrated sessions then exposed
  that Pico 1 GP0 TX stays low during reset, creating PL011 break/framing flags
  before its valid marker begins 28.647 ms after `RUN` release. The old Debug
  Helper classified those positive line errors as fatal, disabled
  `DBG_UART_IF_EN`, and stopped servicing later CDC epochs. Sessions
  `20260912T201857Z-7d797e80` and `20260912T204452Z-1f60f8f1` each retained one
  `0x00` instead of the marker. Focused TDD now proves positive line-error flags
  preserve the epoch and later valid ring input, while a negative driver result
  remains fatal. The 93-test Debug Helper suite and a pristine Zephyr 4.4.2/SDK
  1.0.1 RP2350 target build pass. The corrected 104,448-byte UF2 SHA-256 is
  `94a633420025ed1564b8066ca48adb1dc5b619df7c17d754ec84939a81f86bc8`;
  it was flashed on 2026-09-12. Sessions
  `20260912T212549Z-09d805d0` and `20260912T213056Z-dbb8e66c` each completed a
  15 s Enhanced boot test with the reset-induced `0x00` byte followed by the
  exact marker, 62-byte ring high-water, zero dropped bytes, zero overflow,
  and no connection interruption. Saleae showed a good commanded 100 ms
  `RUN` pulse and clean TX edges, and `DBG_UART_IF_EN` remained at 3.3 V. The
  second run's PPK2 trace measured 54 uA idle, 177 uA during reset, 108 uA
  during the TX burst, and 54 uA after return to idle.
  Eight consecutive sessions on 2026-09-13 completed the ten-boot profile:
  `20260913T172726Z-f5bd6a28`, `20260913T172806Z-17f9e499`,
  `20260913T172841Z-77f0338e`, `20260913T172915Z-a47bcb84`,
  `20260913T172950Z-61fe0955`, `20260913T173025Z-678e82e0`,
  `20260913T173057Z-6095a8ba`, and `20260913T173133Z-e9fd8542`. Every
  run received the exact marker, reached a 62-byte ring high-water mark,
  reported zero dropped bytes and zero overflow events, and completed in one
  uninterrupted segment. The ten-consecutive-boot acceptance criterion passes.
- Dense profile session `20260913T174455Z-b94d2252` ran a synchronized 15 s
  capture with `BURST` sent 0.5 s after capture start under normal host load.
  The fixture emitted 43,081 deterministic bytes; 8,825 were retained and five
  explicit overflow episodes reported 34,256 dropped bytes, reconciling the
  output exactly. Final high-water was 7,842 bytes, the final
  `count=2048 checksum=2096128` marker survived, loss scope was
  `debug_helper_rx_buffer`, and the one-segment session had no interruption,
  truncation, CDC failure, or false `first_error`. Diagnostic setup sessions
  and their exclusion reasons are recorded in the ring-buffer validation file.
- No-stall control session `20260913T175222Z-b278daf8` then sent the
  94,299-byte `SUSTAIN` stream without artificial backpressure. It retained
  13,188 bytes and explicitly reported 81,111 dropped across 17 episodes, with
  a 5,405-byte high-water mark and an uninterrupted epoch. This invalidated the
  earlier dense-only limitation classification and blocked the stall profiles.
  Source tracing identified the unconditional 10 ms wait after each descriptor
  drain as the cause. TDD now batches up to 32 ready outputs and continues
  immediately while backlog remains; all 96 firmware host tests pass. A
  pristine Zephyr 4.4.2/SDK 1.0.1 build uses 52,100 bytes flash and 78,032 RAM.
  The candidate UF2 SHA-256 is
  `7ac75259f7e11d4ae8b17da2fb49864994b4da6cca524d5e2881bdc3dd975814`;
  its HIL result is superseded below.
- The bounded-drain candidate passed parser-reset boot session
  `20260913T180846Z-6de3ee06`, then failed no-stall session
  `20260913T180919Z-df367ab0` with 52,541 retained plus 41,758 explicitly
  dropped bytes across 22 episodes. The exact total remained 94,299 bytes; the
  session was uninterrupted and error-free, but its 4,019-byte high-water and
  64-byte CDC TX FIFO isolated packet-boundary serialization. A new regression
  requires the FIFO to hold the 1,536-byte maximum evidence frame. The
  2,048-byte-FIFO candidate passes all 97 firmware host tests and target-builds
  at 52,100 bytes flash and 80,016 bytes RAM. Its UF2 SHA-256 is
  `a1a3459994b29686b772fbc01f2ee2ecfbd0eb943d1e7e8353fd70077b488ae5`;
  it was flashed on 2026-09-13. Parser-reset session
  `20260913T182730Z-5ecc6e50` retained the exact expected 63 bytes with zero
  loss/overflow. No-stall session `20260913T182750Z-85ac6c6f` reported zero
  firmware loss/overflow, one uninterrupted segment, no error, and only a
  160-byte ring high-water mark, but persisted just 67,336 raw bytes, 2,926 line
  feeds, and 2,925 complete sequence lines. The retained device timestamps span
  about 6.145 s, showing that the 15 s host workflow fell behind the source.
  Source tracing isolated one crash-recoverable filesystem transaction per UART
  event, including repeated raw/JSONL `fsync`, metadata replacement, and marker
  updates. Focused TDD now combines up to 64 consecutive UART events in one
  existing transaction, preserves exact per-event evidence and rollback, falls
  back to ordered single admission when the whole batch exceeds quota, and
  leaves wait-pattern capture single-event. Ruff passes, mypy reports no issues
  in 73 source files, all 1,286 tests pass, and `git diff --check` is clean.
  Repeat no-stall session `20260914T205443Z-f931321d` then retained exactly
  94,299 bytes and 4,098 lines: BEGIN, all 4,096 ordered sequence lines, and the
  exact `count=4096 checksum=8386560` END record. It completed with zero
  overflow/loss, one uninterrupted segment, no truncation or first error, and a
  131-byte maximum/final ring high-water mark. The final occupancy was zero.
  This passes the no-stall gate; the 100 ms host-backpressure profile is next.
- A controlled host-backpressure run sent `SIGSTOP` to the verified Device Core
  Service process during `SUSTAIN` and resumed it after a monotonic measured
  104.328 ms. Session `20260914T205746Z-79a5348b` retained the identical exact
  94,299-byte stream and SHA-256, all 4,096 ordered sequence lines, and the END
  checksum. It reported zero loss/overflow, one uninterrupted segment, no
  truncation or first error, a 160-byte maximum/final ring high-water mark, and
  zero final occupancy. This passes the 100 ms profile; 250 ms is next.
- The formal 250 ms profile paused the same verified service process for a
  monotonic measured 250.255 ms. Session `20260914T205958Z-ccfb482c` again
  retained the identical exact 94,299-byte stream and SHA-256, all sequence
  lines, and the END checksum. It completed with zero loss/overflow, one
  uninterrupted segment, no truncation or first error, a 160-byte maximum/final
  high-water mark, and zero final occupancy. The 250 ms acceptance criterion
  passes; 500 ms is next.
- The 500 ms profile paused the service for a monotonic measured 505.137 ms.
  Session `20260914T210144Z-282b29e0` retained the same exact 94,299-byte stream,
  all sequence lines, checksum, and SHA-256. It completed with zero
  loss/overflow, one uninterrupted segment, no truncation or first error, a
  160-byte maximum/final high-water mark, and zero final occupancy. No
  allocation, stack-overflow, watchdog, USB CDC, or session-lifecycle failure
  was observed. All required backpressure durations now pass; deliberate
  overflow is next.
- Corrected dense session `20260914T210453Z-104d1c17` deliberately overflowed
  without a host pause. It retained 15,691 bytes and reported 27,390 dropped
  bytes across eight overflow records; the exact sum is the fixture's 43,081
  bytes. The END checksum survived, proving post-loss capture continued.
  Metadata and the public session view exposed `loss_reported` with
  `debug_helper_rx_buffer`, while the session remained one uninterrupted,
  untruncated segment and Pico2 stayed connected. This passes the corrected
  dense and deliberate-overflow gates; runtime stack high-water is next.

Enhanced macOS startup and RP2350 PL011 correction working tree, reviewed 2026-09-09:

- Hardware diagnosis isolated pyserial's default open sequence: it asserted DTR
  before its final input flush, while the RP2350 firmware emits its one-shot
  epoch `hello` immediately on DTR assertion. The flush could therefore discard
  the frame before the async reader received it.
- The concrete Enhanced opener now creates the serial resource closed, holds
  DTR low while opening and flushing, attaches the resource to the asyncio
  reader, and asserts DTR exactly once afterward. Partial-open failures close
  the serial resource.
- The next hardware run reached async transport attachment and exposed a second
  issue: `serial_asyncio` reapplied the configured 460800 rate through macOS
  `IOSSIOSPEED`, which the CDC device rejected with errno 83. That value belongs
  to the firmware-owned DUT UART; the Phase 1 contract explicitly keeps it off
  the independent host USB CDC port. The host now uses portable 115200 CDC line
  coding without changing the 460800 DUT UART.
- TDD red proved the old production opener still used the unsafe
  `open_serial_connection` path. A second red proved that the DUT UART rate was
  still passed to the CDC opener. The focused Enhanced serial I/O suite now
  passes all 13 tests, including exact DTR ordering, separation of CDC line
  coding from DUT UART rate, and attachment-failure cleanup.
- Pico 2 diagnosis then isolated two firmware-side requirements. DTR must remain
  asserted for 100 ms before an epoch starts, and the CDC device publishes DCD
  and DSR readiness without clearing carrier during DTR-low gaps. This makes
  macOS port open deterministic while DTR alone continues to own epochs.
- With Zephyr's default 1,024-byte CDC TX FIFO, the firmware accepted the whole
  175-byte `hello`, disabled TX interrupts, delivered exactly two 64-byte
  packets, and wedged before the final 47 bytes. The board overlay now fixes the
  FIFO at one 64-byte full-speed packet so each completion advances the next
  chunk through the existing partial-acceptance state machine.
- The first Zephyr 4.4.0 HIL result was not stable: `hello` could arrive, but
  periodic `buffer_status` stopped and DTR-low/close blocked for about 6.5
  seconds. Controlled diagnostic images showed hello-only healthy, UART-only
  broken, UART with interrupts masked healthy, RX interrupt only healthy, and
  error interrupt only broken. This isolates the failure to the PL011 error
  interrupt path rather than CDC, protocol, telemetry, or UART RX.
- Zephyr advisory
  [GHSA-36rp-2hcp-f5hv](https://github.com/zephyrproject-rtos/zephyr/security/advisories/GHSA-36rp-2hcp-f5hv)
  confirms releases before 4.4.2 enable PL011 error interrupts without
  acknowledging them in the ISR. The application now rejects Zephyr before
  4.4.2 at configure time and keeps UART error interrupts enabled.
- The full production build with Zephyr 4.4.2/SDK 1.0.1 confirms
  `tx-fifo-size = <0x40>`: 51,772 bytes flash, 75,944 bytes RAM, and a
  103,936-byte UF2 with SHA-256
  `db5ba9dfcbcc6d6bbfd83149dd9d5c1b8f206478ad2d7d6ef68f18b57dc16afe`.
- Patched Pico 2 HIL delivered the complete valid 175-byte `hello`, then six
  complete 172-byte periodic `buffer_status` frames over 6.5 seconds. DTR-low
  and close completed immediately. A fresh epoch again delivered `hello` and
  status before closing normally.
- The exact CLI sequence `start`, `status`, `stop`, immediate `start`, `status`,
  `stop` passed twice against `/dev/cu.usbmodem11401`. Both status checks
  reported `connected`, device `dutchmate-rp2350`, firmware `development`, and
  all five required capabilities.
- Retain the independently validated USB/host corrections alongside the Zephyr
  4.4.2 minimum: portable 115200 CDC line coding, deterministic DTR
  open/flush/attach/close sequencing, the DTR-low restart dwell, and the
  one-packet CDC TX FIFO each addressed a separate observed failure. Do not
  blanket-revert them as part of the PL011 correction. The firmware's 100 ms
  DTR-high qualification and DCD/DSR publication are optional future cleanup
  candidates only; remove either one only after an isolated Zephyr 4.4.2 A/B
  run passes sustained telemetry and consecutive CLI start/status/stop cycles.
- All 91 portable firmware tests and all 14 focused Enhanced serial I/O tests
  passed. Ruff passed; mypy reported no issues in 73 source files; full pytest
  passed with 1,274 tests; and `git diff --check` found no whitespace errors.

RP2350 firmware test/build audit commit
`1409522dcdbc69b5b4e16be2576b2869bccbef21`, reviewed 2026-09-05:

- The audit maps every portable boundary to host-compiled tests: exact protocol
  identity/output, NDJSON framing and command validation, the RX ring and loss
  telemetry, CTRL/UART command state machines, epoch cancellation, and exact
  CDC FIFO-acceptance semantics. No uncovered hardware-independent behavior was
  found, so no artificial source-text tests or production behavior were added.
- The firmware README now gives a reproducible build command from the pinned
  Zephyr west workspace and one focused command for all portable firmware
  tests. It explicitly separates host tests, target-build evidence, and HIL
  claims.
- EVENT0 through EVENT3 remain input-only and reserved. The EVENT translator
  remains disabled; neither capture behavior nor `gpio_events` was added.
- Zephyr 4.4.0 with SDK 1.0.1 built warning-free for
  `rpi_pico2/rp2350a/m33`: 51,476 bytes flash, 76,904 bytes RAM, and a
  103,424-byte UF2 image.
- All 90 portable firmware tests passed. Ruff passed; mypy reported no issues
  in 73 source files; full pytest passed with 1,269 tests; and
  `git diff --check` found no whitespace errors.
- Graphify was queried for the firmware/build/test boundary. No structural
  graph update was required because this audit changed documentation only.

RP2350 complete CDC write implementation commit
`cf5325b5b3c8b132c2a07bb02a087b8c18ccfd0b`, reviewed 2026-09-05:

- TDD red first failed six scenarios because the CDC TX state module was absent;
  a second red failed seven scenarios when bounded no-progress timing was added.
  Green covers exact 1..1,536-byte bounds, owned frame copying, busy rejection,
  partial FIFO progress, exact-once completion, invalid progress, driver faults,
  timer wrap, cancellation, and no replay of a staged suffix.
- One Zephyr CDC callback is the only context that calls `uart_fifo_fill`; the
  main USB TX owner starts, polls, and cancels frames. Hello, responses, UART
  events, overflow records, and status records all use the same adapter.
- The approved ownership description now records the Zephyr constraint: the
  main USB TX thread remains sole output scheduler/frame owner, while the CDC
  workqueue callback may advance only its already armed immutable frame.
- Responses and status snapshots are acknowledged only after the complete frame
  reaches the CDC driver FIFO. A 250 ms no-progress deadline resets after every
  accepted chunk. DTR loss cancels pending output and ends the active epoch;
  invalid progress or a driver fault ends it as a fatal transport failure.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 51,476 bytes flash, 76,904 bytes RAM, and a
  103,424-byte UF2 image.
- Focused CDC TX gate: 7 tests passed; all 90 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,269 passed with zero failures.
- Graphify updated the structural graph to 4,563 nodes and 12,157 edges. Its
  parser still reports the existing macro-heavy Zephyr fixture header as a
  partial syntax extraction; target compilation remains authoritative there.
- `git diff --check`: passed with no whitespace errors.
- USB FIFO timing, driver-buffer behavior across physical reset, reconnect
  behavior, command load, and electrical behavior remain HIL gates because the
  Revision A prototype is unavailable.

RP2350 live CDC command integration commit
`a8ac38362144fbd05fdbb69be515371ad07166e7`, reviewed 2026-09-05:

- TDD red failed six ingress scenarios because the bounded ingress module was
  absent and failed executor rejection routing because that API was absent.
  Green covers fragmented and batched input, exact consumed-byte ownership,
  malformed/schema-invalid/oversized mapping, resynchronization, and epoch
  reset. Exact invalid-command and invalid-argument responses use the existing
  one-response lane.
- A dedicated CDC RX thread drains at most 128 bytes per bounded staging chunk
  and stops reading when the single static command slot is full. A separate,
  higher-priority command/control thread is the sole executor, CTRL, pulse, and
  UART TX owner. The lower-priority main thread remains the sole CDC writer.
- `hello` is written before command ingress starts. Responses take the response
  lane before the next evidence frame; existing internal observation sequences
  continue to order UART, overflow, and status evidence.
- Epoch end waits for RX and command owners to stop, resets partial framing,
  purges the command slot, cancels executor work, discards unsent responses and
  CTRL mappings, and forces the hardware safe state. Internal runtime faults end
  the epoch instead of accepting more work.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 50,444 bytes flash, 75,312 bytes RAM, and a
  101,376-byte UF2 image.
- Focused ingress/executor gate: 14 tests passed.
- All 83 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,262 passed with zero failures.
- Graphify updated the structural graph to 4,522 nodes and 12,052 edges. Its
  parser still reports the existing macro-heavy Zephyr fixture header as a
  partial syntax extraction; target compilation remains authoritative there.
- `git diff --check`: passed with no whitespace errors.
- Complete CDC-driver frame acceptance, reconnect timing, command load,
  CTRL/UART electrical behavior, and stack margins remain HIL gates because the
  Revision A prototype is unavailable.

RP2350 command executor implementation commit
`97f5c0b13480c128bf8d839995efe760e37be68a`, reviewed 2026-09-05:

- TDD red failed all seven scenarios because the command executor was absent.
  Green covers exact control success/error responses, one owned response lane,
  wrap-safe pulse completion, UART partial-write and physical-completion
  semantics, timeout/fault terminalization, and epoch cancellation.
- Configure and set-state acknowledge at the operation timestamp. Pulse
  acknowledges only after idle restoration; UART send acknowledges only after
  physical completion and reports the exact accepted byte count.
- Pending work and staged responses reject another command. Epoch cancellation
  cancels UART TX without retry, discards any response, restores all CTRL
  channels to high impedance, and forgets accepted CTRL mappings.
- Error mapping is exact for invalid commands/arguments, unconfigured CTRL
  channels, CTRL hardware faults, UART faults, and UART timeouts. Live CDC
  framing and shared evidence/response scheduling remain the next slice.
- Zephyr 4.4.0 with SDK 1.0.1 target-built warning-free for
  `rpi_pico2/rp2350a/m33`: 43,580 bytes flash, 63,912 bytes RAM, and an
  87,552-byte UF2 image.
- Focused executor gate: 7 tests passed.
- All 76 portable firmware tests passed.
- Ruff: `uv run ruff check .` passed with `All checks passed!`.
- Mypy: `uv run mypy` passed with no issues in 73 source files.
- Full Pytest: `uv run pytest -q` passed: 1,255 passed with zero failures.
- `git diff --check`: passed with no whitespace errors.
- CDC command throughput, response/evidence ordering, disconnect behavior, and
  CTRL/UART electrical behavior remain HIL gates because the Revision A
  prototype is unavailable.

RP2350 UART TX implementation commit
`197d9b56a04ee1fccffa9dd5b2d0c55cc8f506b7`, reviewed 2026-09-05:

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
- [x] Implement the hardware-independent one-command executor, exact response
  mapping, asynchronous completion, and epoch cancellation.
- [x] Connect bounded USB command execution and ordered responses to the
  implemented protocol, UART, and control owners.
- [x] Implement generic `CTRLn` configuration, pulse, and active/idle actions
  with safe startup/disconnect states and portable command routing.
- [x] Enforce the final protocol limits and complete-write acknowledgements.
- [x] Add build instructions and automated firmware-level tests where hardware
  is not required.

Exit gate: a reproducible firmware build implements the exact committed v1
schema and exposes the required identity/capabilities.

### 6. Validate The Revision A Prototype And Ring Buffer

- [ ] Build the first prototype with the documented provisional logic devices
  and exact Pico mapping.
  - [x] Confirm the committed Revision A table, Eagle schematic, Eagle board,
    and RP2350 overlay agree on all 17 net/GPIO/physical-pin assignments and
    that the design files name the five provisional logic-device references.
  - [ ] Inspect the populated U1/U2/U3/U5/U6 markings and verify physical Pico
    pin/net continuity on the unpowered prototype. Deferred at the user's
    request on 2026-09-16.
- [ ] Record leakage, sequencing, isolation, voltage-level, UART signal
  integrity, and safe-state results.
  - [x] Resolve the 1.8 V debugger-unpowered `3V3(OUT)` observation with a
    10 kOhm loaded source-impedance check, retaining instrument limitations.
  - [x] Reject missing trusted `DUT_VIO` declaration before opening a connected
    Enhanced backend, reject out-of-range declarations during config parsing,
    and reject malformed/duplicate control mappings before changing accepted
    state or dispatching a control command.
  - [x] With debugger USB powered and physical `DUT_VIO` absent, verify all
    interface/control enables low and all ten external signal lines
    high-impedance using a 1.8 V/10 kOhm injection plus a separate 10 kOhm
    `DUT_VIO` load.
- [x] Record Zephyr RAM/stack usage and every load profile required by
  `docs/ring_buffer_sizing_plan.md`.
  - [x] Record the reproducible static RAM, configured stack/heap, remaining
    margin, build identity, and artifact hashes.
  - [x] Flash the 460800-baud Pico 1 fixture candidate and directly verify its
    exact 62-byte build marker with a retained Saleae capture.
  - [x] Flash the corrected RP2350 line-error recovery image and run the
    synchronized normal-boot capture through the Debug Helper.
  - [x] Complete ten consecutive representative 460800-baud boot captures with
    the exact marker, zero loss/overflow, and no interrupted segment.
  - [x] Run and record the 15 s dense synthetic profile with exact byte/loss
    reconciliation and an uninterrupted Enhanced epoch.
  - [x] Flash the bounded-drain throughput candidate and record its improved
    but still lossy 94,299-byte no-stall `SUSTAIN` control.
  - [x] Flash the frame-sized CDC FIFO candidate and require a lossless
    94,299-byte no-stall `SUSTAIN` control before host-backpressure injection.
  - [x] Record lossless 100 ms, 250 ms, and 500 ms host-backpressure profiles
    and a corrected deliberate-overflow profile with exact accounting.
  - [x] Measure all eight runtime thread/ISR stacks under boot, 500 ms
    backpressure, deliberate overflow, and a bounded maximum UART-send input;
    identify the first CDC RX stack's inadequate 224-byte margin.
  - [x] Flash the 5,120-byte CDC RX-stack measurement image and repeat the
    boot, 500 ms backpressure, and deliberate-overflow profiles with adequate
    measured margin and no allocation, watchdog, USB, or lifecycle failure.
- [x] Close `hardware/validation/phase1_ring_buffer.md` as `accepted_32k` or
  `revised_with_evidence`; do not waive failed criteria.

Exit gate: the prototype electrical checklist and ring-buffer decision contain
reproducible measured evidence.

### 7. Accept Phase 1B On Real Hardware

- [x] Run the RP2350 Debug Helper against the same Zephyr DUT fixture used for
  Phase 1A.
  - [x] Prepare and target-build an explicitly selected 460800-baud variant of
    the same Pico 1 fixture without changing its accepted 115200-baud default.
  - [x] Directly verify the fixture's exact build marker at 460800 baud and
    retain the Saleae transition export.
  - [x] Flash and verify the corrected Debug Helper UART line-error recovery
    image on the RP2350 before collecting the ten-boot load profile.
- [x] Demonstrate configured reset, boot-test, UART receive/send, device
  timestamps, overflow telemetry, reconnect behavior, and session retrieval.
  - [x] Run a configured `CTRL0` reset/boot-test against the live 460800-baud
    Pico 1 fixture, preserve exact UART bytes/device timestamps, and retrieve
    the completed zero-loss session after correcting MCU-lifetime telemetry
    projection.
  - [x] Run same-fixture UART send during capture and verify explicit overflow
    accounting from nonzero MCU-lifetime starting counters.
  - [x] Run controlled idle/active reconnect workflow HIL with segment/session
    evidence.
  - [x] Run configured `CTRL1` GP2 boot-mode HIL with explicit normal,
    bootloader, and restored-normal command/session evidence.
- [x] Confirm Basic and Enhanced runs produce the same downstream evidence
  structure, with only declared capability/provenance/integrity differences.
- [x] Commit the HIL report with firmware, board, fixture, build, and session
  provenance.

Exit gate: every Phase 1B done criterion has committed evidence.

### 8. Run The Final Phase 1 Acceptance Audit

- [ ] Map every Phase 1A, Phase 1B, and shared done criterion to a passing test
  or committed HIL/measurement record.
  - [x] Map Phase 1A, Phase 1B software/protocol/workflow, and shared criteria
    to current automated tests and committed Basic/Enhanced HIL evidence.
  - [ ] Close and map the Revision A first-prototype electrical criterion after
    its remaining section 14 checks pass.
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
