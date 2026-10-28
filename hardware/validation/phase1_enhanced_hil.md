# Phase 1B Enhanced Workflow HIL Evidence

This record preserves the historical Enhanced runs, the current-contract HIL,
and its preflight audit below. Phase and next-step ownership remain in
`docs/development_status.md`.

## Evidence Reconciliation Addendum — 2026-10-28

The [Revision A reconciliation](phase1_revision_a.md#phase-1b-evidence-reconciliation--2026-10-28)
audits the combined accepted evidence at pushed `9ff33c1` against normative
§§11/34/35. Enhanced workflow criteria, including explicit handoff/control and
automatic USB reconnect/control, are satisfied across the retained runs. Two
§34 evidence gaps remain: adopted 10 kOhm helper-input correction consistency
and prototype UART electrical signal-integrity measurements. The wider historical
parts/continuity, cable/passive, absolute-leakage, transient/isolation and ESD
gap lists below must be read with that item-by-item reconciliation; they are
not additional acceptance criteria. No old run or measurement is amended, and
no hardware was accessed. Phase 1B remains incomplete; current work belongs in
Development Status.

## Automatic Pico 2 USB Reconnect HIL: Passed — 2026-10-27

**The current Enhanced unexpected USB reconnect criterion passed.** This run
tested startup and one automatic Pico 2 USB reconnect on the reviewed cleanup
fix. It did not repeat explicit release/reacquire or the other accepted workflows
and measurements. The physically passed explicit path remains supported by
`20261027T165848Z-b9a62f0b`; the automatic path now has the successful evidence
below. Earlier failed runs, including 303/304 and 739/740, remain unchanged.
Phase 1A remains accepted. **Phase 1B, Stage 8 and overall Phase 1 remain
incomplete** pending the remaining §34/Revision A evidence reconciliation.

### Baseline, retained setup and pre-start gate

Clean `fix/enhanced-terminal-read-cleanup` HEAD
`14e6717554e76444a6b9bc21dbf257a0e51d1efe` matched its independently fetched
pushed branch before startup. The original Basic configuration was preserved.
A new HIL working directory used the same Enhanced config, byte-for-byte:
SHA-256 `df0ac6bd8a424f60a20c8ae27f127f70520945eda9d6402775f8f344a52f005c`,
Profile digest
`941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`.
It retains the exact helper path `/dev/cu.usbmodem1401`, **5.0 s** reconnect
timeout, 460800 8-N-1/no flow control, explicit TX policy, declared 3.3 V,
CTRL0/RUN open-drain active-low and CTRL1/GP2 push-pull active-high/idle-low.

USB identity was `2E8A:000A`, serial `FA63A4D787572B33`. No competing listener
or serial owner was found before startup. The accepted normal helper and
460800-baud DUT UF2 source hashes still match the retained reference flashes
documented below; no new flash/readback or hardware change occurred. The retained
wiring is CTRL0→RUN, CTRL1→GP2, DUT_TX→GP0, DUT_RX→GP1, common GND, DUT_VIO
from Pico 2 3V3, GP3 open. Live normal helper identity and exact DUT boot marker
support that retained provenance; generic `development` alone is not a UF2 hash.

Before any physical startup, using
`rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
`uv run --frozen pytest -q --tb=line` **1,569 passed in 47.60 s**, completed
**18:00:02.239505 UTC**; Ruff passed; mypy passed/103 source files; offline
lock passed/66 packages; architecture included; diff/clean-tree checks passed.
No tests or additional DUTchMate runtime/store ran while the physical service
was active.

### One fresh session and exact lifecycle order

One CLI start at **18:01:19.880597–18:01:21.666191 UTC** created sole service
PID **5775** and fresh native-v2 session **`20261027T180121Z-9ea027ae`**.
Startup status reported `dutchmate-rp2350` / `development`, the expected Profile,
and accepted CTRL0/CTRL1 mappings. Initial telemetry reports 32,768 bytes.
Startup CTRL1 configuration **1→3** and CTRL0 **4→5** preceded the single
100 ms reset **6→8**, success; RX **7, 9..14** retained exact NUL + normal
62-byte `phase1-enhanced-460800-001` boot line.

Passive HTTP status/native-evidence observation was then armed. The operator
confirmed unplugging/replugging only Pico 2 USB into the same port, leaving
Pico 1 power and all other wiring unchanged. There was no manual release,
reacquire, GPIO configuration, action retry or firmware change.

| Required fact | Durable evidence/result |
|---|---|
| Old terminal read failure | **100** `unexpected_disconnect`, segment 0, `error=Enhanced serial read failed`, 18:02:47 UTC. This original connection error remains in the native journal and saved public cursor retrieval. |
| Automatic reconnect begins | **101** `reconnect_started`, segment 0, `timeout_s=5.0`. |
| Fresh replacement segment | **102** `segment_opened`, segment 1, 18:02:52 UTC, same ownership session/Profile and stable helper identity. |
| Fresh boot-channel configuration | CTRL1/GP2 attempt **103**, success ACK **104**, `source=config`, raw device timestamp **3019850 us**. |
| Fresh reset-channel configuration | CTRL0/RUN attempt **105**, success ACK **106**, `source=config`, raw device timestamp **3032034 us**. |
| Success after both ACKs | **107** `reconnect_succeeded`, connection generation 1. |
| Telemetry resumes | **108** buffer status, segment 1, relative timestamp 0; 32,768-byte ring, dropped/overflow counters zero. |
| One immediate reset succeeds | Attempt **109**, result **111**, HTTP 200/success; 100 ms pulse, raw timestamp **3183925 us**. Dispatch **18:02:52.280368 UTC**, **0.379 ms** after the first connected status response. |
| RX resumes | **110, 112..116**, segment 1, exact NUL + normal 62-byte boot marker. |

The required sequence is **100 → 101 → 102 → 104 → 106 → 107 → 111**.
Control attempts/results belong to the new segment; the lifecycle success cannot
be substituted for or reordered before either configuration acknowledgement.
Status after reconnect/reset reports both channels `configured`, `source=config`,
fresh `configured_at=2026-10-27T18:02:52Z` and the matching raw ACK timestamps.
The Profile digest and 5.0 s timeout are unchanged.

RP2350 source origins are **188867368 us** for segment 0 and **3001478 us** for
segment 1. The second segment starts `reconnect`; times remain segment-local,
not continuous across the gap. The observer saw the first disconnected/
reconnecting state at **18:02:47.764736 UTC**, the USB node present again at
**18:02:49.743969 UTC**, segment publication by **18:02:52.222481 UTC**, and
connected status at **18:02:52.279988 UTC**. The first reconnect observation to
connected observation spans **4.515240 s**. Including the prior no-event poll,
a conservative request-start-to-connected-response upper bound is
**4.579836 s < 5.0 s**. These are host observer bounds, not electrical contact
timing; the policy was neither enlarged nor restarted manually.

### Cleanup confirmation and error-preservation evidence

This run reached replacement opening/publication through the reviewed
production close path, with no `cleanup_unconfirmed`, faulted observer state,
reconnect failure or secondary close error. This is stronger than treating
the absence of an exception as proof: in `14e6717`, `_OwnedStreamReader` retains
the original serial resource and successful close requires both
**`is_open is False`** and **`transport.get_extra_info("serial") is None`**.
The coordinator waits for that close before opening the replacement. A
`wait_closed()` exception is accepted only when it is the exact already-observed
read exception and those same positive checks pass. The original backend read
error/cause is not replaced by a close symptom.

The evidence boundary remains explicit: native/public records directly retain
the bounded terminal read-failure description at 100; they do not serialize
the raw Python exception object or private close flags. Positive closure is
established by the enforced, reviewed code path actually completing before 102,
supported by the pre-start installed-transport regressions. Raw object identity/
cause is not claimed as an independently exported physical measurement. The
unchanged implementation/source hash, module origin and this inference are
retained in `cleanup-code-path.json` / `cleanup-confirmation.json`.

### Retrieval, reconciliation, shutdown and scope

Public session/detail, logs and status APIs plus CLI `session`, `logs` and
`status` passed after the physical action. The saved startup cursor retrieved
contiguous **6..137**, **132** records over two pages, including the complete
disconnect/configuration/success/reset ordering and exact resumed UART bytes.
Native/public type and base64 RX correspondence was checked without constructing
another runtime/store.

CLI stop **18:03:20.280053–18:03:20.397463 UTC** was followed by
`Application shutdown complete`, no ERROR/traceback, and native
**`completed/service_shutdown`**, ended 18:03:20 UTC. PID 5775/PID file,
TCP 2040 listener and serial ownership were verified absent. The helper remains
enumerated at the original path/identity; no further open/action was performed.

Final native **0..144 / 145** primary records reconcile with contiguous sequence
numbers: **126 raw RX bytes / 13 RX records**, six successful control pairs,
two closed segments and one unexpected observation gap; no UART sends, bounded
operations or unresolved attempts. Raw reconstruction is byte-for-byte,
SHA-256 `9fc5ffce82472defa7adb38f69ed3306894732766fd911956b8541960228fa5d`.
The two reset/boot byte strings happen to match the earlier focused session;
their segmentation and lifecycle evidence are distinct. Ambient telemetry
naturally retained **115** records (86/29 by segment), zero reported drops/
overflows and maximum high-water 62. Loss scope remains `debug_helper_rx_buffer`,
not electrical losslessness. Local recording and line processing are complete.

All **463** previous session/config file hashes remain unchanged, including
both failed Enhanced sessions. Full local evidence is under
`.dutchmate/hil/enhanced-usb-reconnect-20261027T175902Z/`: pushed baseline and
preservation manifest, preflight/config, individual software gate logs, sole-owner
record, CLI/API/cursor data, observer stream and timing bounds, exact sequence
proof, cleanup confirmation reasoning, service log/shutdown checks, terminal
native snapshot/hash manifest and reconciliation.

Only startup and this automatic USB path were physically exercised. Explicit
handoff, Monitor, Interact, follow, console, ring-buffer/overflow stress, Revision
A measurements, Basic HIL and MCP were not repeated. Prior accepted/current
evidence remains reused within its recorded scope. The current Enhanced
unexpected USB reconnect criterion is **passed**; the earlier control-generation
blockers now have passed explicit and automatic physical paths across these two
focused sessions. Remaining populated-parts/continuity/adopted-correction, analog
UART/cable/passive, leakage/transient/isolation and ESD §34/Revision A gaps remain
open; this does not declare Phase 1B complete. Only this report, development
status and development history changed, unstaged and uncommitted for review.

## Focused Control-Generation HIL: Explicit Pass, USB Cleanup Failure — 2026-10-27

**Focused HIL stopped on the automatic USB path.** Startup and explicit
`release → external owner → reacquire → immediate reset` passed on the reviewed
fix. Unexpected USB reconnect failed before a replacement could be initialized.
The combined control-generation acceptance and current unexpected-reconnect
criterion remain open. Phase 1B, Stage 8 and overall Phase 1 remain incomplete;
Phase 1A remains accepted. The earlier failed run below, including 739/740, is
preserved unchanged and is not reclassified as passing.

### Reviewed baseline, setup and pre-start gate

Clean `fix/enhanced-reacquire-control-config` HEAD
`6d0c1a87b8867d6ea0741b90a9e6d90cb9fc7ce8` matched its freshly fetched pushed
branch before startup. No product source was changed during HIL. The original
Basic config was preserved; a new working directory copied the earlier Enhanced
config byte-for-byte: SHA-256
`df0ac6bd8a424f60a20c8ae27f127f70520945eda9d6402775f8f344a52f005c`,
Profile digest
`941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`.
It retains 460800 8-N-1/no flow control, explicit TX enable, exact path
`/dev/cu.usbmodem1401`, **5.0 s** reconnect timeout, declared 3.3 V, reset
CTRL0/RUN open-drain active-low and boot CTRL1/GP2 push-pull active-high/idle-low.

The retained setup is the same previously identified normal helper and
`phase1-enhanced-460800-001` DUT reference pair, with the operator-confirmed
UART/control/common-ground/Pico 2 3V3 wiring and GP3 open recorded below.
Both retained UF2 hashes again matched the accepted values in the reuse audit.
No new flash or image readback was performed: image provenance remains the
identified same-day transfers plus stable live helper identity and the exact
DUT boot marker. USB enumerated `2E8A:000A`, serial `FA63A4D787572B33`, at the
configured path. Passive checks found no service listener or serial owner before
startup. No new Revision A measurement or correction was made.

The normal software gate completed by **16:56:26 UTC**, before physical startup:
using `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`,
`uv run --frozen pytest -q --tb=line` **1,555 passed in 46.31 s**;
Ruff passed; mypy passed/103 source files; offline lock check passed/66 packages;
`git diff --check` and clean tracked status passed. No tests or additional
DUTchMate runtime/session store ran while the physical service was active.

### Startup and explicit ownership lifecycle: passed

One CLI start, **16:58:47.161072–16:58:49.024171 UTC**, created sole service
PID **3559** and fresh native-v2 session **`20261027T165848Z-b9a62f0b`**.
The journal retained these exact primary sequence orders; intervening telemetry
and RX remain in the native files:

| Path / segment | Durable ordering and physical result |
|---|---|
| Startup / 0 | Connected **0**; CTRL1 configuration **1 → 3**, CTRL0 configuration **4 → 5**; one 100 ms reset **6 → 8**, success. RX **7, 9..13** reconstructs exact NUL + 62-byte normal boot line. |
| Explicit release | CLI release **16:59:10.467476–16:59:10.730948 UTC**; intent **35**, released **36**. Segment 0 closed `released`; automatic reconnect stayed suspended. |
| External owner | Standalone pyserial PID **3600** owned the released helper **16:59:10.732885–16:59:13.272852 UTC**, received one stable `hello` and two buffer-status frames, then closed. Service status remained `released`. No DUT UART send or control command was issued by the external owner; no second runtime/store was constructed. |
| Reacquire / 1 | CLI reacquire **16:59:13.273277–16:59:14.709352 UTC**; started **37**, segment opened **38**, CTRL1 configuration **39 → 40**, CTRL0 configuration **41 → 42**, then `reacquire_succeeded` **43**. Both configuration results are `success`, `source=config`, with new acceptance metadata. |
| Immediate reset / 1 | Single HTTP reset dispatched **16:59:14.709605 UTC**, **0.232 ms** after the CLI subprocess completed; attempt/result **45 → 47**, HTTP 200/success. RX **46, 48..52** reconstructs exact NUL + normal boot line. No manual GPIO configuration or reset retry occurred. |

Fresh CTRL1/CTRL0 raw acknowledgement timestamps are **399416360 / 399427759**
us at startup and **425213260 / 425226654** us after reacquire; public status
matches those new results. RP2350 segment origins are **399388717** and
**425196591** us. The same session and immutable Profile are retained across the
intentional gap. Sequence **38 < 39 < 40 < 41 < 42 < 43 < 45 < 47** establishes
segment staging, fresh configuration, lifecycle success and immediate reset in
the required order. Explicit reacquire/control behavior passed this physical run;
the full two-path criterion is not closed by that narrower pass.

### Automatic Pico 2 USB lifecycle: failed before replacement

After the explicit path passed, a read-only HTTP/native-journal observer was
armed. The operator confirmed unplugging/replugging only Pico 2 USB, with Pico 1
power and the other wiring left in place. The unchanged **5.0 s** policy is
retained both in metadata and `reconnect_started` **304**. No reconnect/reset
trial was repeated.

At **17:03:25 UTC**, native **303** records `unexpected_disconnect`, detail
`Enhanced serial read failed`; **304** records `reconnect_started`. Observer
samples show `reconnecting` with the serial node absent at
**17:03:25.355909 UTC**, then **`faulted` / `service_unavailable` /
`cleanup_unconfirmed`** at **17:03:25.415053 UTC**. That status reports
`Physical cleanup is unconfirmed`, no active session/provenance/capabilities,
unconfigured controls and null commanded boot mode. Native metadata terminalized
as **`failed/backend_input_error`**, detail
**`read failed: [Errno 6] Device not configured`**, at 17:03:25 UTC.

The shutdown traceback retains the old-source close path:
`close_current_source_for_reconnect → EnhancedAsyncHost.close →
close_and_drain_events → reader.close → writer.wait_closed`, re-raising that
`serial.serialutil.SerialException`. There is **no segment 2**, fresh automatic
GPIO configuration, `reconnect_succeeded`, or post-reconnect reset attempt.
There is also no separate native `reconnect_failed` event: the fault is retained
in terminal metadata, public status and the service log. This is not a reconnect
deadline-expiry result; the old transport fault stopped the path before the
replacement-generation behavior could be physically validated. Further root
cause investigation/repair was outside this HIL and was not performed.

The observer stopped at the first fault and requested CLI stop at
**17:03:25.419487 UTC**, acknowledged at **17:03:25.561989 UTC**. Application
shutdown logged the retained serial exception and `Application shutdown failed`;
the CLI acknowledgment is not represented as an error-free shutdown. Subsequent
checks verified PID 3559/PID file, TCP 2040 listener and serial ownership absent.
The helper re-enumerated at its original path/identity after the operator's
replug; no reopen/reset was attempted afterward. Later process/owner absence
does not turn the failed in-run cleanup certainty into a reconnect pass.

### Evidence preservation, reuse and disposition

Final native **0..304**, **305** primary records, reconcile without gaps or
duplicates: **126 raw RX bytes / 12 RX records**, six successful control
attempt/result pairs, two segments and two observation gaps. Raw reconstruction
is byte-for-byte, SHA-256
`9fc5ffce82472defa7adb38f69ed3306894732766fd911956b8541960228fa5d`.
There are no DUT UART sends, bounded operations or unresolved action attempts.
Ambient recording naturally retained **273** buffer-status records; all report
32,768 bytes, zero dropped/overflow counts, maximum high-water **62** bytes.
`none_reported` remains scoped to `debug_helper_rx_buffer`; local recording and
line processing are complete despite the failed ownership lifecycle.

All **456** earlier session/config file hashes remain unchanged, including the
original failed HIL session and Basic config. Artifacts live under
`.dutchmate/hil/enhanced-control-generation-20261027T165521Z/`: baseline/preflight,
per-command software gate, CLI/API timestamps and responses, startup/reacquire
proofs, external ownership, full USB observer stream, fault observation,
operator declaration, copied service log, shutdown ownership checks, terminal
native snapshot/hash manifest and reconciliation. A passive diagnostic initially
expected exit 0 from `lsof` with both cu/unused tty paths; its actual rows listed
the sole correct service PID but exit 1. The corrected read-only check preserved
both results; no physical action was retried for that harness assumption.

This was not a full Phase 1B repeat. Existing accepted/current Monitor, Interact,
follow, console, first-byte retention, telemetry, `accepted_32k`/overflow and
bounded Revision A evidence below remain reused within their recorded limits.
No timeout enlargement, manual GPIO reconfiguration, product/firmware patch,
stress repeat, Revision A or MCP work occurred. §34/§35 cannot close: the
automatic Enhanced lifecycle now has a preserved cleanup blocker, and the
previously identified populated-parts/continuity/adopted-correction, analog UART,
cable/passive, leakage/transient/isolation and ESD gaps remain open. Only this
report, development status and development history are changed, uncommitted.

## Current v2 HIL: Reacquire/Control Blocker — 2026-10-27

**Enhanced HIL stopped incomplete.** Phase 1B, Stage 8 and overall Phase 1
remain incomplete; Phase 1A remains accepted. This run did not reach unexpected
USB reconnect. A real control-state mismatch after explicit reacquire stopped
the affected path without reconfiguration, retry, or an in-run product fix.

### Known-reference preparation and clean baseline

The operator declared the installed images unknown and authorized reflashing
the retained accepted references before acceptance. Both images match the
SHA-256 values in the audit below; UF2 block magic/count/order/payload/end
markers and RP2350/RP2040 families were checked. Each target boot drive was
identified separately before its single successful `/bin/cp` transfer:

| Target | Boot identity | Transfer and reboot observation (UTC) |
|---|---|---|
| Pico 2 helper | `/Volumes/RP2350`, bootloader v1.0, model Raspberry Pi RP2350, board RP2350 | Normal accepted UF2, 104,448 bytes; copy 11:40:25.369806–11:40:26.267602, exit 0. Boot volume absent and expected helper serial present at 11:40:31.920834. |
| Pico 1 DUT | `/Volumes/RPI-RP2`, bootloader v3.0, model Raspberry Pi RP2, board RPI-RP2 | Accepted `phase1-enhanced-460800-001` UF2, 34,304 bytes; copy 11:42:20.956161–11:42:21.459537, exit 0. Boot volume absent at 11:42:43.924033. |

The images were not read back. Available provenance is the exact accepted
source hashes, identified boot targets, successful transfers, passive reboot
observations, subsequent helper hello and exact DUT boot/INFO markers. The
helper uses the accepted normal image, not the changing-identity stack probe.
Preparation records are `flash-helper.json`, `helper-after-flash.json`,
`flash-dut.json`, and `dut-after-flash.json` in the preflight audit folder.

Operator-confirmed wiring: `CTRL0 → RUN`, `CTRL1 → GP2`, `DUT_TX → GP0`,
`DUT_RX → GP1`, common GND, GP3 open, and `DUT_VIO` supplied from Pico 2 3V3.
This is a trusted wiring/supply declaration, not a new calibrated measurement.
No accepted physical measurement was repeated.

Before startup, HEAD again matched the latest pushed
`887768c2e10da1ba8ae9c323474fad86648a7d34` by independent HTTPS remote lookup.
The pending documentation was backed up, temporarily restored to HEAD for a
clean tracked tree, and restored after HIL. No product source changed. The
original Basic config was preserved. A separate HIL working directory supplied
an immutable Enhanced profile at
`.dutchmate/hil/enhanced-phase1b-20261027/run/.dutchmate/config.toml`:
460800 8-N-1/no flow control, explicit TX enable, exact helper path
`/dev/cu.usbmodem1401`, 5.0 s reconnect timeout, 3.3 V declaration, reset
CTRL0/RUN open-drain active-low, boot CTRL1/GP2 push-pull active-high/idle-low.
Profile digest: `941268f4df4522268941b23364cdbf0c0ff6927bfd3efbbb244ad4cad6cbb319`;
config-file SHA-256:
`df0ac6bd8a424f60a20c8ae27f127f70520945eda9d6402775f8f344a52f005c`.

Fresh software gate finished before service startup, with
`rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:
`uv run --frozen pytest -q --tb=short` **1,533 passed in 43.44 s**, including
architecture; Ruff passed; mypy passed/103 files; offline lock check passed/66
packages; `git diff --check` and clean tracked status passed. No pytest or second
DUTchMate runtime/session store ran while the service was live.

### Continuous session and bounded/human operations

CLI startup at 11:44:39–40 UTC created sole service PID **46863** and native-v2
session **`20261027T114440Z-7db24eae`**. Passive ownership checks showed that PID
alone on the helper. Live hello/status reported `dutchmate-rp2350`, firmware
`development`, and `uart_receive`, `uart_send`, `gpio_control`,
`device_timestamp`, `overflow_telemetry`; no `uart_capture` or EVENT capability.
Startup mode attempts/results 1/3 and 4/5 accepted boot/reset configuration.

Acquisition and ambient telemetry were already active before reset attempt 42.
RX 43 retained the reset-induced `00` before successful result 44; RX 45..49
retained the complete 62-byte BOOT OK marker. The exact **63 raw bytes** were
verified before any Monitor started. The configured reset path therefore has
positive continuous-v2 first-byte evidence in segment 0, without live boot-test.

| Check | Durable result |
|---|---|
| First INFO Interact | One exact `INFO\n` send; matched fixture build; range `[67,77)`, terminal 76. |
| Duration Monitor | 0.5 s, elapsed; `[77,80)`, terminal 79. |
| Follow/detach | CLI follow displayed split `DMF/1 PARTIAL complete\n` at RX 135/136 and TX audit 133/134; SIGINT detached the view. Later BINARY RX remained recorded, including invalid UTF-8. |
| Duration Interact | One exact `PING\n`, 0.3 s, elapsed; `[190,195)`, terminal 194. |
| Condition Interact timeout | One exact `PARTIAL\n`, unmatched literal/0.3 s, normal timeout; `[195,202)`, terminal 201; unrelated partial-line UART retained. |
| Literal Monitor | Active Monitor followed by one standalone `PING\n`; matched PONG, `[214,219)`, terminal 218. |
| Condition Monitor timeout | Unmatched literal/0.3 s, normal timeout; `[219,221)`, terminal 220. |
| Console | Actual CLI console with interactive piped stdin sent one `PING` line using explicit LF and displayed PONG; SIGINT detached. Later standalone INFO RX remained recorded. |

The first follow-verification harness expected an incorrect PARTIAL literal and
asserted after the valid response. Inspection of retained fixture source
`203649f:hardware/firmware/zephyr_dut/src/fixture_protocol.c` confirmed the
captured `DMF/1 PARTIAL complete\n` is correct. Original output and the harness
correction are preserved; that send was not repeated. This was not a product
failure or a silently retried operation.

### Boot role and ambient fault evidence

Following the fixture's startup-only strap constraint, the operator held RUN
low while the audited boot role selected bootloader (attempt/result 556/557,
device timestamp `745243683` us), then removed the temporary jumper. RX 582..587
retained the exact 81-byte `E_INIT_001` boot line at 11:53:16 UTC with no bounded
operation active. This expected synthetic fixture fault is also the session's
detected first error; it is not the later control blocker.
The retained fixture predates `DELAYFAULT`, so no scheduled delayed-fault UART
command was run. Physical ambient-fault evidence here is the boot error outside
all bounded operations; delayed-fault semantics also have the pre-start software
gate's coverage.

The operator held RUN low again for audited `normal` (680/681, device timestamp
`860324220` us), then released it. RX 700..704 retained the exact 62-byte normal
boot line. CTRL0 remained wired throughout; only the temporary RUN-ground
jumper was removed. The manual reset assertions' NUL bytes were retained too.
No GP2 change was commanded outside a confirmed held-reset interval.

Live actions and durable parameters establish role→channel resolution.
Current encoder/adapter source and the passing wire-level regression tests
establish generic `pulse_control`/`set_control_state` payloads without `role` or
`dut_signal`; no independent physical USB packet capture was made. Capability,
configuration and electrical-mode rejection tests passed in the pre-start gate.

### Ownership handoff and the blocking result

Release at 11:55:32–33 UTC persisted request/released **733/734**, closed segment
0, and left an explicit intentional observation gap. No serial owner was then
reported. Only while status was `released`, standalone pyserial PID **47481**
opened the helper at 11:55:57–59 UTC. It received the normal hello and two
32 KiB status frames, sent no UART/control command, and closed. Its sole
ownership is recorded in `external-owner.json`; no second DUTchMate runtime or
session store was constructed.

One CLI reacquire at 11:56:29–30 UTC persisted started/opened/succeeded
**735/736/737**, retained the same session, created segment 1 and resumed
telemetry at 738. RP2350 origins are **253900607** us for segment 0 and
**964063386** us for segment 1; timestamps are segment-local, not comparable
across the gap. The profile and its reset/boot mappings were unchanged.

**Blocker:** status immediately after reacquire still advertised CTRL0 and CTRL1
as `configured`, `source=config`, with their old 11:44:40 acceptance metadata.
The single following CLI reset returned HTTP **409 `not_configured`**, detail
**`CTRL0 is not configured`**. Its durable attempt **739** resolved
`reset → CTRL0/RUN`; result **740** records `status=not_configured` and null
device timestamp. There is no success result to substitute for that failure.
Final public status still advertised both configured channels. The observed
host/helper configuration mismatch and unavailable reset after same-profile
reacquire are the defect; full root cause and repair are outside this run.

The acceptance path stopped. No GPIO reapplication, reset retry, product or
firmware patch, timeout enlargement, further Interact, or USB reconnect trial
followed. Segment 1 later retained a separate reset byte plus exact normal boot
at RX **784..789**, 11:57:14 UTC, about 44 s after the rejected reset. Its trigger
is not established by host action evidence and is not credited as success of
the rejected reset. It does establish resumed UART recording alongside telemetry.

### Telemetry, retrieval and shutdown

All **774** native `buffer_status` records report 32,768 bytes, lifetime dropped
bytes 0 and overflow events 0; observed high-water reached **81 bytes**. Session
integrity is `none_reported`, scope `debug_helper_rx_buffer`, dropped bytes 0;
local recording and line processing are complete. This does not claim electrical
losslessness or physically exercise a nonzero current-session counter delta.
The exact accepted normal helper and Enhanced fixture were reflashed, so the
audited `accepted_32k`/deliberate-overflow measurements below remain reusable;
no heavy ring-buffer campaign was repeated. Nonzero/baselined loss projection
has the prior physical evidence plus current deterministic v2 coverage.

CLI `sessions`, `session`, `logs`, and `status`, plus service detail/log retrieval,
passed before shutdown. A saved pre-reset cursor retrieved contiguous **42..866**
in 825 records, retaining controls, operation results, both segments and gap
markers, including failed control 739/740. Direct native reconciliation covers
**0..866**, 867 primary records, **510 raw RX bytes / 47 RX records**, eight
exact TX attempt/result pairs, six control attempt/result pairs (five successes,
one `not_configured`), and six completed bounded operations. Raw reconstruction
is byte-for-byte; SHA-256
`feeaabbc890ece3168090a62b324f10c2ae5845f2eceeccab70d9a88ca3f2e17`.

Graceful CLI stop returned at 11:58:31.098956 UTC; native state is
`completed/service_shutdown`, ended 11:58:31 UTC, two closed segments and one
gap. This normal journal termination does not mean acceptance passed. PID
46863/PID file, TCP 2040 listener and serial ownership were verified absent.
All 448 prior session-file hashes and the original Basic config remain unchanged.
Full artifacts, snapshots, CLI/API output, cursor pages, copied service log,
terminal reconciliation and final native hashes are under
`.dutchmate/hil/enhanced-phase1b-20261027/`. Documentation remains uncommitted.

### Specification §34 disposition after this HIL

| Criterion (in §34 order) | Evidence/disposition |
|---|---|
| Phase 1A host semantics through Enhanced | Passed current bounded operations, exact audited TX, follow/console/detach, ambient RX, v2 retrieval and ownership handoff; post-reacquire Control blocked, unexpected USB reconnect remains open. Default policy/rollover limits have software coverage, not a forced physical rollover. |
| Normalized RP2350 RX/send contracts | Passed current raw/normalized RX and eight exact successful TX audits through service/CLI. |
| `uart_receive`, not `uart_capture` | Passed live hello/status and segment capabilities. |
| Generic channel actions | Passed initial reset and both boot-mode actions; source/exact-wire regression tests verify `pulse_control`/`set_control_state`. |
| Role/signal metadata host-side | Passed current host resolution/audit plus encoder/schema/regression evidence; no independent USB packet trace. |
| Adopted hardware consistency and measurements | Still-valid bounded Revision A results reused; genuine mapping/parts/correction, analog UART/passive, leakage/transient and ESD gaps remain as audited below. |
| Gated/audited reset and boot | Passed segment-0 actions and durable failure/gating evidence; **blocked across reacquire by stale configured status/helper rejection**. |
| Acquisition before reset; first boot bytes retained | Passed current 42..49; exact reset NUL + 62-byte normal marker persisted before any Monitor. |
| RP2350 timestamp provenance | Passed native metadata, cursor RX projections and two fresh segment origins. |
| Continuous buffer/overflow telemetry | Passed 774 ambient status records across operations and two segments; loss scope stays explicit. No current overflow was forced. |
| Measured 32 KiB gate | Satisfied by still-valid `accepted_32k`; reference-image hashes and live ring size match. |
| Deliberate-overflow observer/count | Satisfied by audited prior accepted byte accounting for the reflashed references, with current v2 regression coverage; no stress repeat. |
| EVENT ownership documented, unadvertised/unimplemented | Passed current live capabilities plus unchanged protocol/source coverage; no EVENT workflow introduced. |
| Fake Enhanced integration/CLI tests | Passed full fresh 1,533-test gate before startup. |
| Real Pico 2 + same Zephyr fixture combined acceptance | Partial current HIL; stopped on post-reacquire reset mismatch. Unexpected USB reconnect and subsequent same-session provenance/retrieval remain open, in addition to identified physical gaps. |

Shared §35 cannot close: configured Control is unavailable after the ownership
boundary, and the complete Enhanced lifecycle path has not passed. The initial
software gate and successful portions above do not supersede this blocker.
No MCP work or separate fix/TDD slice was started.

## Initial v2 Acceptance Preflight — 2026-10-27

**Stopped before acceptance service startup; no current Enhanced HIL result.** Phase 1A
remains accepted. Phase 1B, Stage 8, and overall Phase 1 remain incomplete.
This audit applies specification §§33–35 and Stage 8 of the coding-agent plan;
it does not convert historical finite-capture/`boot_test` sessions into v2
acceptance. The removed live boot-test workflow was not invoked.

### Baseline and preflight observations

- Clean `stage8-phase1-acceptance` HEAD
  `887768c2e10da1ba8ae9c323474fad86648a7d34` matched both the local origin ref
  and an independent HTTPS `git ls-remote` of the pushed branch. Sandbox fetch
  could not write `.git/FETCH_HEAD`; SSH remote verification failed public-key
  authentication. Read-only HTTPS verification succeeded without changing refs.
- At `2026-10-27T11:27:19.705174Z` (16:57:19 IST), passive pyserial enumeration
  returned only `/dev/cu.debug-console` and
  `/dev/cu.Bluetooth-Incoming-Port`, neither with USB identity. `ioreg -p IOUSB`
  subsequently showed only host controllers and two hubs. No Pico 2 CDC path,
  VID:PID, serial number, or live firmware identity could be verified. Historical
  `2E8A:000A` / `FA63A4D787572B33` and old CDC paths are expectations only.
- `lsof -nP -iTCP:2040 -sTCP:LISTEN` returned no listener. Process enumeration
  was sandbox-denied; no global process-absence claim is made. Ownership of an
  attached helper still needs verification once a device exists. No physical
  port was opened, service started, or ownership session created by this audit.
- Pure profile resolution of unchanged `.dutchmate/config.toml` selected
  **Basic**, exact path `/dev/cu.usbserial-D358SG6A`, external UART,
  115200 8-N-1, no flow control, TX enabled, line ending `none`, driver-default
  DTR/RTS, reconnect timeout **5.0 s**, and declared `DUT_VIO=3.3 V`.
  Its control mapping is empty: neither reset nor boot resolves to a channel.
  A voltage declaration is not a physical measurement. There is no resolved
  Enhanced acceptance profile in this configuration; it was not changed.
- Actual DUT image, UART wiring/baud, voltage, strap state, adopted hardware
  correction, and reset/boot wiring were not positively established. Recent
  Basic diagnostics used a different 115200-baud image; that is not evidence
  that the required Enhanced fixture is currently flashed.

Operator follow-up on 2026-10-27 confirms `CTRL0 → RUN`, `CTRL1 → GP2`,
`DUT_TX → GP0`, `DUT_RX → GP1`, common ground, and `DUT_VIO` supplied from
**Pico 2 `3V3`**. This records the operator's wiring declaration; it is not a
new voltage or continuity measurement. GP3/strap state, installed hardware
correction, flashed helper/DUT images, and 460800-baud DUT operation remain
unconfirmed. A subsequent passive serial/IOUSB recheck still found no Pico
device and no TCP 2040 listener. The Basic configuration remains unchanged;
acceptance is still stopped before startup.

After the operator connected USB, the recheck at
`2026-10-27T11:34:50.844840Z` (17:04:50 IST) enumerated
`/dev/cu.usbmodem1401`, VID:PID `2E8A:000A`, serial `FA63A4D787572B33`,
description `Debug Helper`, location `0-1.4`. IOUSB independently showed
`Debug Helper@00140000`. No owner was reported by `lsof` for its cu/tty paths,
and no TCP 2040 listener was observed. This resolves USB visibility and matches
the recorded helper's USB identity; it does not identify its flashed firmware.
Both flashed-image identities, DUT baud, GP3/strap state, actual voltage and
installed correction remain unverified. No serial open or service startup
occurred. The passive result is saved as `usb-recheck.json` in the audit folder.

The operator then reported that installed images are unknown and authorized
reflashing known references. This is a separate hardware-preparation step before
acceptance. At `2026-10-27T11:37:23.514031Z`, both retained UF2s again matched
the hashes below, and all block headers, sequence/count fields, payload bounds,
end markers and board-family IDs were validated: normal helper, 104,448 bytes /
204 blocks, RP2350 ARM secure `0xe48bff57`; DUT, 34,304 bytes / 67 blocks,
RP2040 `0xe48bff56`. No boot volume was mounted and no flashing had yet occurred.
`flash-preparation.json` records the chosen images and authorization. The operator
was asked to enter BOOTSEL on Pico 2 first and confirm Pico 1 GP3 state; each
boot drive must be identified before writing its corresponding image.

### Authorized known-reference hardware preparation

The operator confirmed Pico 1 GP3 is open and put Pico 2 into BOOTSEL.
`/Volumes/RP2350/INFO_UF2.TXT` reported `UF2 Bootloader v1.0`,
`Model: Raspberry Pi RP2350`, `Board-ID: RP2350`; IOUSB showed
`RP2350 Boot@00140000`. No service listener was observed. After rechecking
the accepted normal helper UF2 hash, one `/bin/cp` wrote all 104,448 source
bytes to `/Volumes/RP2350/dutchmate-helper-accepted.uf2` between
`2026-10-27T11:40:25.369806Z` and `11:40:26.267602Z`, exit 0, no stderr.
At `11:40:31.920834Z` the boot volume was absent and the helper again enumerated
at `/dev/cu.usbmodem1401`, `2E8A:000A`, serial `FA63A4D787572B33`.
`flash-helper.json` and `helper-after-flash.json` preserve the transfer and
passive reboot observations. The firmware was not read back; provenance is
the identified boot target, exact accepted source hash, successful transfer,
and re-enumeration. Live hello/capabilities remain for the preflight/service path.

Pico 1's installed image is still unknown at this point. The operator was asked
to put only Pico 1 into BOOTSEL for a separately identified RP2040 transfer of
the accepted 460800-baud fixture. No DUT image has yet been written. No
acceptance session, UART send, control action, or stress run has started.

Local passive facts, profile projection, artifact hashes, and a preservation
manifest are retained under `.dutchmate/hil/enhanced-preflight-20261027/`.
They are preflight audit artifacts, not a native-v2 hardware session.

### Reuse audit: ring buffer and firmware provenance

The following retained images were hashed again and match the accepted records:

| Artifact | SHA-256 |
|---|---|
| Normal helper `build/dutchmate-rp2350-normal-v2/zephyr/zephyr.uf2` | `5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819` |
| Diagnostic helper `build/dutchmate-rp2350-stack-probe-v2/zephyr/zephyr.uf2` | `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66` |
| Enhanced DUT `build/dutchmate-zephyr-dut-460800/zephyr/zephyr.uf2` | `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6` |
| Enhanced DUT generated `.config` | `4e472f3f0ea19c89611b2d9f05ef2f08b0fcfca198fc573a0b074b7de3441595` |

The DUT configuration identifies `rpi_pico/rp2040`, build
`phase1-enhanced-460800-001`; its accepted provenance is Zephyr 4.4.0 / SDK
1.0.1, with the 460800 overlay. The helper images have accepted Zephyr 4.4.2 /
SDK 1.0.1 provenance. Local image identity does **not** establish flashed-image
identity; a generic live `development` string alone would not prove a UF2 hash.
The stack diagnostic changes its identity across CDC epochs and is unsuitable
for the normal reconnect acceptance path, as the historical run below shows.

All five revised stack/profile JSON reports named in the ring-buffer record
(boot, stack/backpressure, profile/backpressure, stack/overflow, profile/overflow)
match their recorded hashes. The boot Saleae CSV and five-cycle TX-pull-up CSV
also match. The accepted record establishes 32,768 raw ring bytes, final normal
static RAM 81,040/532,480 bytes, at least 1,248/5,120 bytes free on CDC RX,
and deliberate overflow of 19,418 retained + 23,663 reported dropped = 43,081
fixture bytes with six overflow records and surviving BEGIN/END checksum.
The corrected host repeat separately reconciles 19,079 + 24,002 = 43,081.

Source comparison from accepted stack-margin commit `ae01ce2` to this HEAD
found no change in ring, UART drain, control, stack sizing, mapping, or protocol
schemas. Changes within the helper are product-version documentation/config
and equivalent bounded hello-string length calculation. They do not establish
invalidation of the accepted measured images. The host v2 migration still
requires fresh continuous telemetry/evidence HIL; older v1 projections do not
prove it. **Retain `accepted_32k`; do not repeat heavy stress.** Applicability
to the actual setup remains open until flashed helper/fixture and hardware
identity are confirmed. No firmware/protocol/hardware invalidation was observed
and no new stress procedure was devised.

`none_reported` means only no reported Debug Helper RX-buffer loss for the
session, after applicable counter baselining. It does not establish losslessness
on the electrical UART path. Live 32 KiB status, high-water, session-local
counter interpretation, and continuous persisted telemetry remain untested here.

### Reuse audit: Revision A physical evidence

The detailed source is [the Revision A record](phase1_revision_a.md), including
its later dated sections rather than just its summary or unchecked design list.
No accepted measurement was repeated or withdrawn.

| Area | Reusable evidence and actual remaining limits |
|---|---|
| Mapping and logic parts | Prior 17-net schematic/board/overlay audit agrees; provisional parts are recorded. Populated markings/physical continuity remain unaudited. Replacement KiCad sources are absent. The accepted 10 kOhm helper-input correction after R16 has digital evidence but its next-revision schematic/BOM and actual installed state remain unverified. |
| Voltage operation | Exact 33-byte 460800-baud loopback passed at 1.8/2.5/3.3/5.0 V, with idle-current evidence; reuse these results within that short-jumper scope. They do not establish all cable lengths or analog margins. |
| Controls | All four push-pull controls at 1.8 V and representative CTRL0 levels at 2.5/3.3/5.0 V passed; representative open-drain reset with 10 kOhm pull-up, 250 ms/2 s/10 s pulses, and every control high-impedance during helper reset passed. Broader loading/threshold/voltage margins remain limited to recorded conditions. |
| Missing supplies/isolation | Loaded missing-VIO sweep covers all external digital signals; debugger-unpowered 1.8 V sweeps cover controls, UART, and events. Loaded 3V3 back-power observation fell from 0.13 to 0.02 V. Reuse these static results; calibrated absolute leakage and broader voltage/transient isolation are still open. |
| Sequencing/hot-plug | All four control /OE nodes passed settled both-order sequencing; repeated unloaded supply cycles passed at 1.8 V. Later 3.3 V digital captures establish clean recovery with the helper-side 10 kOhm TX pull-up, including five cycles. These are valid bounded results, not closure of all loaded-cable/power transient combinations. |
| UART signal integrity/passives | Analog edge shape, overshoot/undershoot/ringing, voltage margin, cable-length coverage, and oscilloscope validation of series resistors remain explicitly deferred/open; digital Saleae decoding cannot close them. ESD capacitance/leakage/clamping measurements are not recorded as passed. |
| Configuration safety | Prior trusted-voltage and invalid/duplicate mapping rejection evidence plus current software tests remain reusable; no new physical no-glitch/contention measurement was made. |
| EVENT0–EVENT3 | Physical input-path measurements do not imply a live EVENT feature. Phase 1 keeps these unadvertised/unimplemented; no EVENT API or event-rate HIL was introduced. Broader design-checklist event tests have no accepted result here. |

### Explicit specification §34 disposition

“Open” below means the current physical requirement has not been demonstrated;
passing deterministic tests are supporting evidence, not a fabricated HIL pass.

| Criterion (in §34 order) | Disposition at this preflight |
|---|---|
| Inherited Phase 1A host semantics through Enhanced | Open live: ambient recording, follow/detach, duration/literal Monitor, exact single-send matched/elapsed/timeout Interact, asynchronous UART, console, v2 provenance/retrieval, release/reacquire gap, and unexpected reconnect. Software gate passes; Basic acceptance is preserved, not transferred to Enhanced. |
| Normalized RP2350 RX/TX contracts | Software tests pass; open live. |
| `uart_receive`, not `uart_capture` | Current hello source/protocol and prior live identity support it; current live capabilities open. |
| Generic `pulse_control` / `set_control_state` | Current decoder/schema and tests support both; current live action evidence open. |
| Role/DUT-signal metadata host-side | Current protocol/tests support separation; live resolved profile/action evidence open. |
| Adopted hardware consistency and prototype measurements | Prior bounded physical results above remain reusable; identified design/measurement gaps remain open. |
| Gated reset/boot with durable v2 audit | Deterministic tests pass; current profile has no mappings, live test open. |
| Acquisition active before reset; immediate boot bytes retained | Historical exact 63-byte boot is supporting physical evidence only; current continuous-v2 proof open. No reset or boot action was attempted. |
| RP2350 segment timestamp provenance | Prior device-timestamp evidence reusable as history; current persisted v2 segments/origins open. |
| Continuous buffer/overflow telemetry | Deterministic tests pass; current ambient v2 telemetry open. |
| Measured 32 KiB acceptance gate | Satisfied by still-valid `accepted_32k` measurements for their recorded image/setup; hashes verified. Actual connected-image applicability awaits identity. |
| Deliberate overflow scope/count | Satisfied by prior reconciled `debug_helper_rx_buffer` measurements for the accepted image/setup; no stress repeat justified. Current v2 loss projection remains a live HIL check. |
| EVENT ownership documented, unadvertised/unimplemented | Source/protocol and prior capabilities support this; current live capabilities open. |
| Fake Enhanced integration/CLI tests | Passed in the full 1,533-test software gate, including Stage 8 Enhanced parity and shared CLI acceptance tests. |
| Real Pico 2 + same Zephyr fixture: continuous RX/Interact/reset/boot retrieval/timestamps/telemetry/v2/retrieval | Open: physical preflight prevented startup; no fresh Enhanced session exists. |

No criterion passed **by current HIL**, because none ran. Shared §35 completion
also cannot be asserted: Enhanced continuous RX/first-byte preservation,
follow/Monitor/Interact/console, configured control, ownership/reconnect, and
live provenance/quality still lack this run's physical evidence. Software schema,
storage, ownership, and architecture regressions passed, but do not close the
remaining backend/physical gates. MCP remains deferred.

### Operator prerequisites for a subsequent run

1. Connect the accepted RP2350 Pico 2/Revision A helper and the same Pico 1
   Enhanced fixture; establish the actual USB VID/PID/serial/path and absence
   of a competing owner before opening it. Identify the installed hardware
   correction rather than assuming historical wiring still applies.
2. Positively identify the flashed normal helper and 460800-baud DUT images
   against the retained provenance above. If different/missing, prepare and
   identify the required images before acceptance; the authorized helper flash
   is recorded separately above and DUT preparation remains pending. Confirm
   GP0/pin 1 TX → helper RX, helper TX → GP1/pin 2 RX,
   common ground, actual `DUT_VIO=3.3 V`, GP3 open, and strap state. The operator
   has declared the UART/control/ground wiring and Pico 2 3V3 supply above;
   image/baud/strap confirmation remains required; helper USB now enumerates
   with the accepted serial identity at `/dev/cu.usbmodem1401`.
3. Establish the Enhanced profile before acceptance: 460800 8-N-1/no flow
   control, explicit TX policy, unchanged 5.0 s reconnect timeout, reset
   `CTRL0 → RUN`/pin 30 open-drain active-low, boot `CTRL1 → GP2`/pin 4
   push-pull active-high/idle-low, or positively document the actual accepted
   mapping. The existing Basic configuration was left unchanged. GP2 is sampled
   only at startup; preserve the fixture's held-reset/unpowered strap constraint.
4. Repeat passive preflight and the required software gate before physical
   startup on the then-reviewed baseline. Use one service owner and fresh native
   v2 session where practical. Reset/boot Control and later evidence/Monitor
   retrieval must prove acquisition precedes control; use no live boot-test.
   Any failed required action must be preserved without an acceptance retry or
   in-run patch. Do not enlarge reconnect timeouts or rerun accepted stress.

### Validation and preservation

Before any possible physical startup, using
`rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

- `uv run --frozen pytest -q --tb=short`: **1,533 passed in 42.86 s**,
  including `tests/architecture/test_dependencies.py`.
- `uv run --frozen ruff check .`: passed.
- `uv run --frozen mypy`: passed, 103 source files.
- `uv lock --check --offline`: passed, 66 packages.
- `rtk git diff --check`: passed before documentation and after final review.

The initial audit started no service, firmware flash, control, UART send,
reconnect, runtime/store probe, or stress campaign. The subsequent authorized
helper flash is recorded separately above; acceptance has not started.
The software gate used its existing isolated
test infrastructure. All 448 existing session-file hashes and the local config
were preserved. Only this report, development status, and a new history entry
are changed, uncommitted for review; previous evidence remains intact.

## Historical Enhanced Workflow HIL — 2026-09-15

The following configured reset/boot-test and USB reconnect runs used the same
Pico 1 Zephyr DUT fixture as the Enhanced load profiles under the earlier contract.

| Provenance | Observed value |
|---|---|
| Debug Helper | Fully assembled Revision A translator prototype with a non-wireless Raspberry Pi Pico 2 (`rpi_pico2/rp2350a/m33`) |
| Pico 2 image | Opt-in Zephyr 4.4.2/SDK 1.0.1 stack diagnostic `build/dutchmate-rp2350-stack-probe-v2/zephyr/zephyr.uf2`; SHA-256 `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66` |
| DUT fixture | Raspberry Pi Pico 1 `rpi_pico` opt-in Zephyr 460800-baud fixture; build marker `phase1-enhanced-460800-001` |
| Wiring/supply | User-confirmed UART, `CTRL0` to Pico 1 `RUN`, common ground, and `DUT_VIO=3.3 V` |
| Host | macOS 26.2; Debug Helper CDC `/dev/cu.usbmodem11201`; local Device Core Service at `127.0.0.1:2040` |
| Runtime selection | CLI `--backend enhanced --serial-port /dev/cu.usbmodem11201 --baudrate 460800`; UART TX policy enabled |
| Control mapping | `CTRL0` role `reset`, DUT signal `RUN`, `open_drain`, active low; configured through the public CLI before each boot test |

The first public `dutchmate boot-test --seconds 15` call used the host source at
commit `9d18bdb` and session `20260915T192952Z-2cf24586`. It completed a
100 ms configured reset and retained exactly 63 UART bytes: reset `0x00` followed
by `DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001\n`. The raw
SHA-256 was `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`.
The first `buffer_status` had an empty current RX ring but reported a 6,045-byte
lifetime high-water, 23,663 lifetime dropped bytes, and six lifetime overflow
events from the preceding deliberate `BURST` session. The host incorrectly
interpreted those absolute MCU counters as this boot session's loss. It marked
`loss_reported` with 23,663 dropped bytes and overflow despite the exact clean
boot output. The initial session metadata and hardware-event SHA-256 digests are
`6a3cc039f83ddf5400ac82b8c691afc53238a389a7808af7958bd792306c374d`
and `9ca6f5946ab241b5b07aa04630bf5a4d014d755cd31aeb54d655b67bef428163`.

The corrected host treats the first status in each capture window as a baseline,
accounts for ordered explicit overflow records before that status, and reports
later counter increases as new loss. New sessions start with fresh Enhanced
integrity, while the raw `buffer_status` fields remain unchanged. The corrected
source and regression tests were committed as
`ab98caa67af19b624a782175f44ee64e3febdb58`. A repeat
`dutchmate boot-test --seconds 15` produced session
`20260915T194748Z-78db848e`:

| Evidence | Corrected repeat result |
|---|---|
| Reset action | One accepted `CTRL0` pulse, 100 ms, device timestamp `2336115113` us |
| UART capture | Exact same 63 bytes and raw SHA-256 `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` |
| Timestamp provenance | Device `rp2350_timer`, `debug_helper_uart_receive/uart_event`, one segment |
| Session lifecycle | Completed after 15 seconds; no interruption, resume, truncation, or first error |
| Session integrity | `none_reported`, zero session dropped bytes, `overflow=false` |
| Lifetime status retained | First raw status still reported 23,663 MCU-lifetime dropped bytes, six MCU-lifetime overflow events, and 6,045-byte lifetime high-water |
| Public retrieval | `dutchmate session 20260915T194748Z-78db848e` returned the completed native v1 `boot_test` session, 63-byte raw artifact, five UART-event records, 16 hardware-event records, one segment, and `none_reported` integrity |

The corrected session's ignored local artifacts are under
`.dutchmate/sessions/20260915T194748Z-78db848e/`. SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `4618f0f181d9edc8a64642cd60b27a18894d587db9e5510d60373d334ce03b69` |
| `uart_raw.log` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` |
| `uart_events.jsonl` | `a47f20e1cce8535044c013a4afcdd13401eedf4b9ba9e77fd175ec4fb9c192eb` |
| `hardware_events.jsonl` | `faf4e2905e2683ca4e5d09a24d9a7a3d8fae9ea6767a6658a4659b1b79093b94` |

The post-test public status remained connected with `none_reported` integrity.
The service was stopped after retrieval so DTR dropped and the Pico 2 returned
its control outputs to the safe idle state. The diagnostic firmware later
reported a frozen `stack-1of8-...` identifier during the corrected service
epoch; that identifier belongs to the same UF2 named above.

The host correction also passed a positive-loss repeat on the same image and
fixture. A public 15-second capture with a forced `BURST` UART send produced
session `20260915T195131Z-28e6d4b8`. It retained 19,079 bytes and six ordered
overflow records explicitly reported 24,002 dropped bytes, exactly reconciling
the fixture's 43,081-byte output. Both `BURST BEGIN count=2048` and
`BURST END count=2048 checksum=2096128` survived. Metadata reported
`loss_reported`, `debug_helper_rx_buffer`, 24,002 session dropped bytes,
`overflow=true`, and one uninterrupted segment. The first status contained
the previous MCU totals of 23,663 drops and six events; the final status
contained 47,665 drops and 12 events. Their 24,002-byte/six-event increase
matches the current-session overflow telemetry. Post-run host load averages
were 2.62/2.48/2.45. The helper report is
`build/enhanced-burst-after-counter-fix.json`, SHA-256
`fa3a34cf44ab3b8633889018a76cf795993c07232ec75a22a9fb3214cc4c41fb`.
The ignored session artifacts under
`.dutchmate/sessions/20260915T195131Z-28e6d4b8/` have SHA-256 digests:
metadata `80c552ae224ecb11f7fc60997c88f492b387df058b2005a77273bf8b43caaea4`,
raw UART `da7c06a2e5cdd359160981af9b488c122c7d9e5f21c58debbca3e86bbf7e245e`,
and hardware events `5ab4e3908668d18fc0d6781f5403b2147b42b1f356eff5bb138fbc33402e4835`.
The service was stopped afterward.

## Controlled USB reconnect

The operator unplugged and reconnected only Pico 2 USB while Pico 1, its UART
and `CTRL0` wiring, common ground, and `DUT_VIO=3.3 V` remained in place.
The service used the same `/dev/cu.usbmodem11201` path and 460800-baud DUT UART
setting throughout. An idle disconnect on the diagnostic image changed public
`connection_state` from `connected` to `disconnected` at 20:05:00 UTC and
back to `connected` at 20:05:30 UTC on the same port. The reconnecting idle
service had no active session. The ignored monitor record is
`build/reconnect-hil/idle-watch.jsonl`, SHA-256
`f3e754b8a89e3f822efe1609dd0b2020358fe5f430740befe2a4ecdf7ac7847e`.

The first active attempt used the opt-in stack diagnostic image and a configured
60-second reconnect window, within the documented 0.1–60-second range. Session
`20260915T200703Z-d86f54e3` entered `reconnecting` at 20:07:32 UTC with
59.9 seconds left, but the replacement `hello.firmware` did not match its
session-start value `stack-1of8-command-1112-3072`. The host returned HTTP
502 `backend_input_error: Reconnected Debug Helper identity changed`. Public
`dutchmate session` retrieval showed a failed, interrupted, unresumed session
with one preserved segment ending `usb_disconnect`; it did not append a
replacement segment. This is the required identity guard operating on an
unsuitable diagnostic image: `stack_probe.c` intentionally advances the
`stack-...` firmware identifier after each CDC epoch to expose frozen stack
readings. The ignored monitor record is
`build/reconnect-hil/active-watch.jsonl`, SHA-256
`5629275232233498c7016096e0b41d275c1b0a701cf31d174b956167cf8458c0`.
The failed session metadata SHA-256 is
`3656c59e07b38423d745f4da32c6822be29387bfc19dce4538377feff3d43e7f`.

The operator then flashed the normal, non-diagnostic Zephyr 4.4.2/SDK 1.0.1
`build/dutchmate-rp2350-normal-v2/zephyr/zephyr.uf2`, SHA-256
`5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`,
to Pico 2. After reboot, public status reported the stable `development`
firmware identifier and all five Enhanced capabilities. The Pico 2 image was
not read back; the UF2 digest and observed `hello` are the available image
provenance.

The normal-image repeat used the same 60-second window and a public 150-second
capture. A forced Pico 1 `PING` was sent before disconnect; two more were sent
after reconnect. The capture was session `20260915T201343Z-57c45321`:

| Evidence | Result |
|---|---|
| Connection | Active `reconnecting` at 20:15:00 UTC with 59.9 seconds remaining; active `connected` again at 20:15:15 UTC on the same port and `development` identity |
| Lifecycle | Completed `duration_elapsed`, `interrupted=true`, `resumed=true`, no truncation or overflow |
| Segments | Exactly two contiguous segments, both Enhanced/`development`; segment 0 ended `usb_disconnect`, segment 1 ended `duration_elapsed`; each has its own device `rp2350_timer` origin |
| Hardware evidence | One `usb_disconnect` on segment 0, one `usb_reconnect` on segment 1, one `timestamp_discontinuity` from 0 to 1 |
| UART evidence | Segment 0 contains `DMF/1 ERROR COMMAND code=E_COMMAND_001\n`; segment 1 contains two exact `DMF/1 PONG\n` lines, each with segment-relative device timestamps |
| Integrity | `none_reported`, zero current-session dropped bytes, `overflow=false` |
| Public access | `dutchmate session` returned the completed two-segment native session; `dutchmate logs --session ...` displayed separate segment 0 and 1 lines |

The first send record contains the exact five-byte `PING\n` payload
(`data_b64=UElORwo=`) and a successful physical-send acknowledgement. Pico 1
nevertheless emitted its generic `E_COMMAND_001` response; why its first
command was rejected is not established from this capture. The next two sends
of the same command returned `PONG`. The host correctly detected the fixture
error as the first downstream error in segment 0. It does not alter the observed
USB disconnect/reconnect or segment-resume result.

The ignored normal-image monitor
`build/reconnect-hil/active-normal-watch.jsonl` has SHA-256
`219d6ca0b03bb377e576cab13897464fd06491f074f07c6872d8907bc458dca1`.
The ignored completed session artifacts under
`.dutchmate/sessions/20260915T201343Z-57c45321/` have SHA-256 digests:
`metadata.json` `b17cb1e53d73a3ce036adf8483459672ffc78ebdb95787332dcd7d9ee36af28d`,
`uart_raw.log` `debc3fd50459ee9a8fe1fbaa42faa2a26dad39e832333db9af2eb8bffb6b9229`,
`uart_events.jsonl` `58553f24c4de7f9c75eda58fe5cfc5419447ea06f35cdd741bec8522ec6c8816`,
and `hardware_events.jsonl`
`0cd146811f25c6f717ce5f56646c2d84005c5110bad1b247097f087f0be14aeb`.
The service was stopped and the local reconnect configuration restored to its
5.0-second default afterward.

## Basic and Enhanced downstream evidence structure

The accepted Basic run in `hardware/validation/phase1_basic_hil.md` used the
same Pico 1 Zephyr fixture code at its default 115200 baud through an FTDI
adapter. Sessions `20260826T211103Z-2649d369` and
`20260826T211203Z-f541c8fb` stored raw UART bytes, normalized UART events,
metadata, and hardware events; event payloads reconstructed the raw log, and
both public session and recent-log retrieval succeeded. Basic reported
`not_observable` integrity and host-monotonic timestamp provenance. The
Enhanced boot and reconnect sessions recorded above used the same downstream
artifact names and public retrieval operations while reporting RP2350 device
timestamps and Enhanced buffer-loss telemetry.

A focused deterministic contract test,
`tests/unit/runtime/test_device_core_capture.py::test_basic_and_enhanced_capture_share_downstream_evidence_shape`,
now captures the same `DMF/1 PONG\n` bytes through fake Basic and Enhanced
event sources and the real shared `CaptureWorkflow`/`SessionStore` path. It
checks equal artifact filename sets, equal top-level metadata keys, equal
segment/backend field sets, identical normalized UART-event records, and equal
session-detail and recent-log field sets. Both modes return the exact PONG
line. Their explicit distinctions are Basic's null firmware/device, Basic
`uart_receive`/`uart_send` support, host-monotonic/serial-chunk provenance,
and `not_observable` integrity versus Enhanced's device/firmware identity,
GPIO capability, device-timer/UART-event provenance, and `none_reported`
integrity for the clean test.

The archived August Basic session directories are absent from this checkout,
so their historical field sets cannot be compared byte-for-byte to the
September Enhanced files. The committed Basic HIL report supplies the real
storage/retrieval result; the new contract test supplies a reproducible
same-source structural comparison on the current code baseline.

## Configured boot-mode workflow

The operator connected Revision A J3 pin 2 (`DUT_CTRL1`) to Pico 1 GP2
(physical pin 4), kept `DUT_CTRL0` on Pico 1 `RUN` (pin 30), left GP3 open,
and retained the 460800-baud UART, common ground, and `DUT_VIO=3.3 V`.
Pico 2 ran the normal Zephyr 4.4.2/SDK 1.0.1 UF2 SHA-256
`5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`
on `/dev/cu.usbmodem11201`. The public CLI configured `CTRL0` as
`reset -> RUN`, `open_drain`/active-low, and `CTRL1` as
`boot -> GP2`, `push_pull`/active-high/idle-low. Status confirmed both
accepted mappings and commanded mode `normal`.

The Pico 1 fixture samples GP2 once at startup and requires strap changes
while unpowered or held in reset. For both mode transitions, the operator
temporarily jumpered Pico 1 `RUN` to GND while leaving `DUT_CTRL0` wired
in parallel. The `bootloader` command drove GP2 high only during that hold;
its response reported `performed_at=2026-09-15T20:43:47.798353Z` and
`device_timestamp_us=1714277106`. After the jumper was removed, a public
`boot-test --seconds 15` pulsed `CTRL0`. The operator held `RUN` low again
for the `normal` command, whose response reported
`performed_at=2026-09-15T20:47:06.212054Z` and
`device_timestamp_us=1912690435`, then removed the jumper before the
restored-normal boot test.

| Session | Commanded mode | Exact raw evidence | Result |
|---|---|---|---|
| `20260915T203733Z-7d502d02` | `normal` | Reset `0x00` + `DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001\n` = 63 bytes | Completed, one segment, no first error |
| `20260915T204533Z-0d15abc2` | `bootloader` | Reset `0x00` + `DMF/1 ERROR INIT code=E_INIT_001 board=rpi_pico build=phase1-enhanced-460800-001\n` = 82 bytes | Completed, one segment, `ERROR` detected at segment 0/event 6 |
| `20260915T204741Z-617d85d9` | `normal` | Exact same 63-byte normal evidence and SHA-256 as the first session | Completed, one segment, no first error |

Each session persisted one accepted 100 ms `control_action` reset with raw
device timestamp: `1339767313`, `1819688434`, and `1947790470` us,
respectively. Every capture reported device `rp2350_timer` UART timestamps,
`none_reported` integrity with zero current-session dropped bytes, no
overflow, interruption, resume, or truncation. Public `dutchmate session`
retrieval returned native `boot_test` details; public `dutchmate logs`
displayed the expected fixture line in each session. Local assertions verified
the exact raw bytes, reconstruction from `data_b64` UART events, session
mode snapshots, reset evidence, and detected-error record.

The ignored session artifacts have these SHA-256 digests:

| Session | `metadata.json` | `uart_raw.log` | `uart_events.jsonl` | `hardware_events.jsonl` |
|---|---|---|---|---|
| First normal | `37b99d4bf3f6176d738adde1ca66223543f9f5c` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` | `52372b530e964dabdfca2966f2ad6bccf2748eb84e7719249a2e2ea1ef07ba8a` | `eb02250b46e763f654c3549d237eff2b12c4b26e28199579d4b5997f9a334f45` |
| GP2-high failure | `e79c42280d821fa12e16773aba64cc291f39884bb455701794849f9dc5afe1cc` | `7ac5b2f71bfd7f1d4da1edf607407c8cfcec70c4e4cb9dc2fd333c6aa26481e4` | `e648de80493348e88c4e494ebae3ab3108f8df6280a9f7210fb1cc55c2814dfe` | `b50d2b732c91efbfc9a8cf9459e9b56b585b18b5d8af267be20900426579ead5` |
| Restored normal | `7357f072c86851c51517c6ba7740736d246b11f6f81a061c7c0f1296e3c5b26d` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` | `f4d56c67c653c1e9c035248a79e6f4256ecfebc9f149885bed9a74612c1429b8` | `41cf83eae141106d727defdef070c4027327df37013fbf76527984ae43ed3398` |

A post-restoration forced `PING` in capture
`20260915T204855Z-51d462a8` returned exact `DMF/1 PONG\n`, one
in-session `uart_tx_attempt`, no first error, and `none_reported`
integrity. Its raw SHA-256 is
`ddca019a59596c677f2d348609ac57c9ab0c1967d3b71f64ce6b443f548cf8da`.
The earlier first-`PING` fixture rejection did not recur after this clean
reset, but its cause remains unestablished. The service was stopped after
retrieval, returning the control outputs to high impedance while Pico 1 GP2
retained its internal pull-down.
