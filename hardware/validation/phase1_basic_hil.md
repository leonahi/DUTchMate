# Phase 1A Basic Hardware-in-the-Loop Validation

This document is the reproducible procedure and report template for accepting
the DUTchMate Phase 1A Basic hardware path. It uses the deterministic Zephyr
DUT fixture on a Raspberry Pi Pico 1 and a generic 3.3 V USB-to-UART adapter.

The procedure validates the real receive/send path, capture storage, and
session retrieval. Assertions use DUTchMate's normalized evidence and the
fixture's `DMF/1` byte protocol. They do not depend on Zephyr console or log
formatting.

## Acceptance scope

The baseline run must prove all of the following:

- DUTchMate explicitly connects to the generic adapter in Basic mode;
- a manual reset produces captured UART bytes in a 15-second session;
- policy-enabled UART transmit records attempts and accepted writes;
- `PING` and `INFO` responses are captured through the same session pipeline;
- raw bytes, normalized UART events, metadata, and hardware events persist;
- session detail and recent-log retrieval return the recorded evidence;
- Basic integrity is reported as `not_observable`, not inferred as lossless.

Partial-line, binary, burst, sustained-load, silent-boot, and failure-mode
scenarios remain useful fixture diagnostics, but they are not required for the
minimum Phase 1A Basic smoke-test gate.

## Required equipment and software

- Raspberry Pi Pico 1 or Pico H, powered through its Micro-USB connector;
- the DUTchMate Zephyr DUT fixture built for `rpi_pico` with a non-default,
  immutable build ID;
- a 3.3 V TTL USB-to-UART adapter with transmit and receive support;
- Zephyr `v4.4.0` and Zephyr SDK `1.0.1` for the reference baseline;
- a DUTchMate checkout with dependencies installed by `uv sync`;
- two host terminals in the repository root for capture/send overlap.

Do not connect RS-232 voltage levels, 5 V UART logic, or the adapter VCC pin to
the USB-powered Pico.

## Wiring and fixture mode

Use the successful-boot strap state. GP2 and GP3 have internal pull-downs and
must both remain open while the Pico starts.

| Pico signal | Physical pin | Adapter or action |
|---|---:|---|
| GP0 / UART0 TX | 1 | Adapter RX |
| GP1 / UART0 RX | 2 | Adapter TX |
| GND | 3 | Adapter GND |
| GP2 / mode bit 0 | 4 | Open |
| GP3 / mode bit 1 | 5 | Open |
| RUN | 30 | Momentarily connect to GND for manual reset |

The UART settings are 115200 baud, 8 data bits, no parity, one stop bit, and
no flow control.

## Record provenance before the run

Record command output in the report before starting the acceptance scenarios.
Replace the Zephyr and build paths with the paths used to produce the flashed
UF2.

```bash
git rev-parse HEAD
git status --short
uv run --package dutchmate python -m serial.tools.list_ports -v
git -C /path/to/zephyr describe --tags --always --dirty
git -C /path/to/zephyr rev-parse HEAD
shasum -a 256 /path/to/build/zephyr/.config
shasum -a 256 /path/to/build/zephyr/zephyr.uf2
```

Also record:

- adapter manufacturer/model, USB VID/PID, and serial number when available;
- serial port selected by DUTchMate;
- board target, fixture build ID, Zephyr SDK version, and flash method;
- GP3/GP2 strap state, recorded as `00` for this baseline.

An acceptance result with missing DUT commit, fixture build ID, adapter
identity, or UF2 digest is incomplete.

## Configure and start DUTchMate

Ensure no serial terminal or other process owns the adapter. Configure the
selected port in `.dutchmate/config.toml`:

```toml
[backend]
mode = "basic"
serial_port = "/dev/cu.usbserial-EXAMPLE"
reconnect_timeout_s = 5.0

[hardware.uart]
baudrate = 115200
data_bits = 8
parity = "none"
stop_bits = 1
tx_enabled = true

[sessions]
path = ".dutchmate/sessions"
max_size_mb = 16
```

Start the service and verify the resolved connection:

```bash
uv run --package dutchmate dutchmate start
uv run --package dutchmate dutchmate status
```

The status must report:

- service `running` and connection `connected`;
- backend `basic` and the intended serial port;
- backend/effective capabilities `uart_receive, uart_send`;
- UART TX policy enabled;
- host-monotonic `host_serial_read/serial_read_chunk` provenance;
- UART loss `not_observable`.

If the service was already running before the adapter was connected or the
configuration changed, stop it and start it again before continuing.

## Scenario 1: manual-reset receive and storage

1. Confirm GP3 and GP2 are open.
2. In terminal A, start the required 15-second capture:

   ```bash
   uv run --package dutchmate dutchmate capture --seconds 15
   ```

3. Within the first three seconds, briefly connect Pico RUN to GND and release
   it. Do not change the mode straps while the board is running.
4. Record the session ID printed when capture completes as `BOOT_SESSION`.
5. Retrieve its evidence:

   ```bash
   uv run --package dutchmate dutchmate logs --session <BOOT_SESSION> --last 20
   uv run --package dutchmate dutchmate session <BOOT_SESSION>
   ```

The UART evidence must include these exact fixture-protocol bytes, with the
recorded build ID substituted:

```text
DMF/1 BOOT OK board=rpi_pico build=<FIXTURE_BUILD_ID>\n
```

The session must be terminal and untruncated, use the Basic backend, contain at
least one UART event and non-empty `uart_raw.log`, report `first_error: none`,
and report integrity `not_observable`.

The capture summary fragment `lines=complete/oversized:0` reports line-processing
status and the oversized-line count. It does not mean that zero lines were
captured; use `dutchmate session` and the persisted artifacts for event and byte
counts.

## Scenario 2: transmit, response capture, and provenance

This scenario requires two terminals because capture is a finite blocking
command.

1. In terminal A, start another 15-second capture:

   ```bash
   uv run --package dutchmate dutchmate capture --seconds 15
   ```

2. While it is active, run both commands in terminal B:

   ```bash
   uv run --package dutchmate dutchmate send PING --force
   uv run --package dutchmate dutchmate send INFO --force
   ```

3. Each send must print an attempt ID and `Perturbation logged: yes`.
4. Record the session ID printed by terminal A as `COMMAND_SESSION`.
5. Retrieve its evidence:

   ```bash
   uv run --package dutchmate dutchmate logs --session <COMMAND_SESSION> --last 20
   uv run --package dutchmate dutchmate session <COMMAND_SESSION>
   ```

The replay must contain these lines in command order:

```text
DMF/1 PONG
DMF/1 INFO board=rpi_pico build=<FIXTURE_BUILD_ID> protocol=1
```

The session must contain two `uart_tx_attempt` and two successful
`uart_tx_result` records in `hardware_events.jsonl`. The accepted byte count
for both newline-terminated commands is 5. The session must also contain the
two normalized receive events and the corresponding raw UART bytes.

## Inspect persisted artifacts

The default session root is `.dutchmate/sessions`. For both session IDs, inspect
the native artifacts without editing them:

```bash
wc -c .dutchmate/sessions/<SESSION_ID>/uart_raw.log
sed -n '1,20p' .dutchmate/sessions/<SESSION_ID>/uart_events.jsonl
sed -n '1,20p' .dutchmate/sessions/<SESSION_ID>/hardware_events.jsonl
sed -n '1,220p' .dutchmate/sessions/<SESSION_ID>/metadata.json
```

The acceptance report records artifact byte/record counts from `dutchmate
session`, rather than copying the full evidence files into documentation.
Session directories remain the authoritative raw run evidence while the report
records stable provenance, assertions, and session IDs.

After the evidence and report fields have been recorded, release the adapter if
no further DUTchMate scenarios will run:

```bash
uv run --package dutchmate dutchmate stop
```

## Objective acceptance checklist

Mark the run passed only when every required assertion is supported by the
recorded session IDs.

- [x] Adapter identity, selected port, and 115200 8-N-1 settings recorded.
- [x] DUTchMate commit and dirty/clean state recorded.
- [x] Zephyr revision, SDK, board, fixture build ID, `.config` digest, UF2
  digest, flash method, and strap state recorded.
- [x] Basic status reports the intended connection and capabilities.
- [x] Manual-reset capture contains the exact successful-boot protocol bytes.
- [x] Boot session is completed, untruncated, and has no first error.
- [x] Both UART sends have durable attempt/result evidence and accept 5 bytes.
- [x] Command capture contains the exact `PONG` and `INFO` responses.
- [x] Both sessions preserve non-empty raw bytes and normalized UART events.
- [x] Session detail and recent-log retrieval reproduce the stored evidence.
- [x] Both sessions report Basic integrity as `not_observable`.
- [x] No assertion depends on Zephyr console or log prefixes.

Any failed or unverified item makes the run `failed` or `incomplete`, not
accepted. Preserve the session directories and describe the failure without
rewriting observed evidence.

## Baseline acceptance report — 2026-08-26

For a later rerun, append a dated copy of this report structure so the accepted
baseline and its replacement remain auditable.

### Run identity

- Result: `passed`
- Run date/time and timezone: `2026-08-26T23:13:24+02:00 CEST`
- Operator: `Nahit Pawar`
- DUTchMate commit: `483fcb39465fb159efe95640cb573c437eacd9ac`
- DUTchMate working tree: dirty only under `graphify-out/` from prior Graphify
  queries/reflections; tracked host and firmware source matched the commit

### DUT fixture provenance

- Board: `Raspberry Pi Pico 1`
- Zephyr board target: `rpi_pico`
- Zephyr version/tag: `v4.4.0`
- Zephyr source commit: `684c9e8f32e4373a21098559f748f06915f950c9`
- Zephyr SDK: `1.0.1`
- Fixture build ID: `phase1-pico-7e44ba9`
- Generated `.config` SHA-256:
  `91454b55fa0f40801705e6f5bdb20b8a7fe678197beee960603d342471a08dc9`
- UF2 SHA-256:
  `da637a59048eb88d085ea31a6d03554cb9317e07057e63d77326d37cef202a46`
- Flash method: manual USB UF2 copy through the Pico BOOTSEL mass-storage
  device
- GP3/GP2 strap state: `00`

The build was reproduced after the run with the recorded Zephyr source, SDK,
board qualifier, DUTchMate fixture source, and build ID. Its UF2 digest matched
the digest recorded before flashing exactly, establishing that the regenerated
`.config` belongs to the flashed image inputs.

### Adapter and wiring

- Adapter manufacturer/model: `FTDI FT231X USB UART`
- USB VID/PID: `0403:6015`
- Adapter serial number: `D358SG6A`
- DUTchMate serial port: `/dev/cu.usbserial-D358SG6A`
- UART: `115200 8-N-1, no flow control`
- Wiring checked: `GP0->RX, GP1->TX, GND->GND, adapter VCC disconnected`

### Session evidence

| Scenario | Session ID | Raw bytes | UART records | Hardware records | Result |
|---|---|---:|---:|---:|---|
| Manual-reset boot capture | `20260826T211103Z-2649d369` | 60 | 2 | 0 | passed |
| PING/INFO command capture | `20260826T211203Z-f541c8fb` | 74 | 2 | 4 | passed |

### Observed results

- Status connection/capabilities: connected in Basic mode on the recorded port;
  backend and effective capabilities were `uart_receive, uart_send`, TX policy
  was enabled, and provenance was host-monotonic at
  `host_serial_read/serial_read_chunk`.
- Boot protocol bytes: contained
  `DMF/1 BOOT OK board=rpi_pico build=phase1-pico-7e44ba9\n`.
- PING response: exactly `DMF/1 PONG\n`.
- INFO response/build provenance: exactly
  `DMF/1 INFO board=rpi_pico build=phase1-pico-7e44ba9 protocol=1\n`.
- UART send attempts/results: attempts
  `3d08712a747a4350af57194ed4f74574` and
  `74905cb6f9a34321bb1093e6fd66a29c` were durably recorded; both results were
  successful and accepted 5 bytes.
- Storage and retrieval: concatenating decoded `data_b64` from each session's
  UART events reproduced its `uart_raw.log` byte-for-byte; `dutchmate session`
  and `dutchmate logs` retrieved both sessions and their expected evidence.
- Session state/truncation/first error: both sessions completed by
  `duration_elapsed`, were not truncated, interrupted, resumed, or overflowed,
  and reported no first error.
- Integrity: both sessions reported Basic loss status `not_observable`.
- Deviations or failures: the manual-reset session preserved five electrical
  transition bytes (`00 00 ff 00 00`) before the intact boot marker. These did
  not alter or obscure the required marker and were retained in raw and
  normalized evidence. No acceptance assertion failed.

### Decision

- Checklist: all required assertions passed.
- Phase 1A Basic HIL decision: `accepted`.
- Decision rationale: the real generic adapter/Pico path demonstrated manual
  reset receive, policy-enabled transmit, deterministic fixture responses,
  native evidence storage, and CLI retrieval with complete provenance. The
  Basic backend correctly made no loss-observability claim.

## Phase 1A v2 Basic preflight attempt — 2026-10-26

Result: **blocked before hardware acceptance; no new acceptance decision**.
The report above remains historical evidence under its original contract.
This attempt uses the current specification sections 32–33 and Stage 8 Basic
HIL criteria, as directed by `docs/developer_guide.md`.

### Observed provenance

| Field | Observation |
|---|---|
| Discovery time | `2026-10-26T17:03:49.953709+05:30` (IST) |
| Branch | `stage8-phase1-acceptance` |
| HEAD and local upstream tracking ref | Both `e8f9e6186e92d6898f011cf8853e1071d0e62f01`; no fetch performed |
| Initial working tree | Clean, including index; no pre-existing changes |
| Host | macOS 26.2, build `25C56`; Darwin `25.2.0`, `arm64` |
| Generic USB-UART identity/path | Not identifiable; no USB serial device enumerated |
| Serial discovery | Only `/dev/cu.Bluetooth-Incoming-Port` and `/dev/cu.debug-console`; both description/HWID `n/a`, VID/PID, serial number, manufacturer, product, and location null |
| Device nodes | Only those two `cu` paths and their corresponding `/dev/tty.*` paths |
| USB inventory | GenesysLogic USB2.1 Hub `05e3:0610` at `00100000` and USB3.2 Hub `05e3:0625` at `00200000`; no USB-UART or Pico identified |
| Mounted volumes | Only `Macintosh HD`; no `RPI-RP2` volume observed |
| Physical DUT/fixture board | Not established; the documented target is Pico 1, not an observed hardware identity |
| Flashed Zephyr/application/build identity | Not established; no fixture communication, image verification, build, or flash performed |
| Wiring, logic levels, mode straps | Not verified; no physical inspection or operator confirmation available |
| Serial ownership | Not tested: no eligible target port to check; no claim that a target port is free |
| Effective UART/DTR/RTS/profile | None used: service not started and no port opened; documented Basic baseline is 115200 8-N-1 without flow control, not a measured configuration |
| New schema-v2 session IDs | None |

The absence of a USB identity does not establish whether an unenumerated,
unpowered, or UART-only fixture is physically on the bench. Historical adapter
serial `D358SG6A`, DUT build IDs, and image digests were not reused as current
identities.

### Commands and actions performed

Read `AGENTS.md`, `docs/development_status.md`, specification sections 32–35,
the Stage 8 HIL section, `docs/developer_guide.md`, the existing Basic/Enhanced
validation records and relevant Revision A/ring-buffer provenance, and the
Zephyr fixture README, `main.c`, and `fixture_protocol.{c,h}` before discovery.
Read-only preflight commands included:

```bash
rtk proxy git rev-parse HEAD origin/stage8-phase1-acceptance
rtk proxy git status --short --branch
rtk proxy git diff --exit-code
rtk proxy git diff --cached --exit-code
rtk proxy .venv/bin/python -m serial.tools.list_ports -v
rtk proxy sw_vers
rtk proxy uname -srm
rtk proxy ioreg -p IOUSB -l -w 0
rtk proxy ioreg -p IOUSB -w 0
rtk proxy ls /Volumes
```

These Git/host inventory commands also ran in shell batches. A read-only
`rtk proxy .venv/bin/python -` script recorded the timestamp with
`ZoneInfo('Asia/Kolkata')`, host information with `platform`, device nodes with
`glob('/dev/cu.*')` / `glob('/dev/tty.*')`, and all serial identity fields using
`serial.tools.list_ports.comports()`. Enumeration did not open serial devices.
The detailed USB tree output exceeded the tool output budget; the subsequent
compact tree confirmed that only the two hub devices were enumerated.

No Basic startup, Monitor, follow, send, Interact, console, release/reacquire,
external serial consumer, or session retrieval was executed. No firmware or
production source was changed. Enhanced HIL and MCP migration were not started.

### Criterion-by-criterion result

All hardware assertions are **not tested**, rather than failed software tests.
No existing automated or historical hardware result is promoted to a new pass.

| Phase 1A criterion (specification section 33, in order) | This attempt |
|---|---|
| Continuous real Basic RX, including ambient bytes between operations | Not tested — required hardware unavailable |
| Follow through the durable cursor; detach preserves the single RX owner | Not tested |
| Duration and literal-condition Monitor, outcomes and exact ranges | Not tested |
| TX disabled by default; explicitly enabled exact audited TX | Not tested |
| Single-send Interact, outcomes, asynchronous bytes, durable ranges, no retry | Not tested |
| Service-backed line console; exit preserves acquisition | Not tested |
| Native v2 ambient/action/operation evidence and serial/DTR/RTS provenance | Not tested |
| Linked size/segment rollover without stopping capture | Not rerun; no current result |
| Basic loss truthfully `not_observable` absent a trusted observer | Not tested |
| Release/external same-port ownership/reacquire and durable unobserved gap | Not tested |
| Unexpected reconnect with v2 evidence | Not tested |
| Shared fake-backend unit/service/CLI tests | Not rerun; prior software validation remains in development history |
| Real USB-UART + Zephyr fixture HIL, including delayed fault and retrieval | Not tested; no session or evidence range created |

Additional source-inspection limitation: the checked-in fixture implements
`PING`, `INFO`, `PARTIAL`, `BINARY`, `BURST`, `SUSTAIN`, and `SILENT` only. No
dedicated delayed-fault command or autonomous fault scheduler was found in the
inspected protocol/main source. This does not prove a runtime DUTchMate defect;
the requested delayed-fault scenario has no physical result. Fixture firmware
was not modified to supply it.

### Decision and documentation verification

Stopped at the required hardware-availability gate. Phase 1A remains
incomplete, and Stage 8, Phase 1B, and Phase 1 remain incomplete. No software
failure was observed or diagnosed by this preflight. The exact blocker is the
absence of an identifiable required generic USB-UART adapter and verified DUT
fixture on this host; wiring and flashed firmware identity remain unknown.

Only this appended report, a new development-history entry, and current-status
blocker/validation wording were changed. Changes remain uncommitted for review.
Documentation verification uses `rtk proxy git diff --check` and an append-only
comparison against HEAD; no full software acceptance rerun is claimed.

## Adapter attachment and fixture readiness check — 2026-10-26

At `2026-10-26T17:18:42.594713+05:30`, a repeat read-only
`rtk proxy .venv/bin/python -` inventory using
`serial.tools.list_ports.comports()` identified:

- FTDI `FT231X USB UART`, VID/PID `0403:6015`, serial `D358SG6A`;
- port `/dev/cu.usbserial-D358SG6A`, USB location `0-1.4`.

The user requested fixture-flashing guidance before HIL. No serial port was
opened and no HIL operation, service start, build, or flash was performed.
Physical DUT identity, wiring, current firmware, and port ownership remain
unverified. Branch/HEAD remain as recorded in the preceding attempt; its three
uncommitted documentation changes were preserved.

Read-only build-artifact inspection found only
`build/dutchmate-zephyr-dut-460800/zephyr/zephyr.uf2` for the DUT fixture,
SHA-256 `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6`.
Its generated configuration identifies `rpi_pico/rp2040`, build
`phase1-enhanced-460800-001`, Zephyr `4.4.0`, and UART0 speed `0x70800`
(460800). It is not the documented 115200-baud Basic baseline. No Basic UF2
was found in the inspected `build/*zephyr-dut*` directories.

The documented Basic source is `hardware/firmware/zephyr_dut`, target
`rpi_pico`, reference Zephyr `v4.4.0`/SDK `1.0.1`, with no 460800 overlay.
Its expected success marker is `DMF/1 BOOT OK board=rpi_pico build=<ID>\n`;
`PING\n` produces `DMF/1 PONG\n` and `INFO\n` identifies the build.
The delayed-fault source limitation recorded above remains unresolved, so this
baseline alone cannot substantiate the full requested v2 HIL gate. No firmware
changes were made. All acceptance decisions remain unchanged; Enhanced HIL
was not started.

## Reviewed fixture finalization / Basic HIL preflight — 2026-10-26

Result: **blocked before flash and serial ownership; Basic HIL not run**.
No new acceptance decision replaces any historical result above.

| Provenance | Observed value |
|---|---|
| Preflight time | `2026-10-26T19:02:24.994058+05:30` (IST) |
| Branch | `stage8-phase1-acceptance` |
| Reviewed fixture/preflight commit | `746121a35633c070f4e7112010ce26b656d8ef1d`, `test(hardware): prepare Basic Phase 1 HIL fixture` |
| Commit publication | Local only; SSH and HTTPS push authentication failed |
| Host | macOS 26.2, Darwin 25.2.0, arm64 |
| Adapter | FTDI FT231X USB UART, `0403:6015`, serial `D358SG6A`, location `0-1.4` |
| Port | `/dev/cu.usbserial-D358SG6A`; enumerated only, never opened |
| Reviewed UF2 | `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/zephyr/zephyr.uf2` |
| Independent UF2 SHA-256 | `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`; exact required match |
| Image build identity | `basic-v2-20261026-7bc2ec377767`, Zephyr v4.4.0 / SDK 1.0.1, `rpi_pico/rp2040`; built for 115200 8-N-1, no flow control/overlay |
| Physical DUT/BOOTSEL | Not verified; only `/Volumes/Macintosh HD` mounted, no `RPI-RP2` or `INFO_UF2.TXT` found |
| Wiring | Not verified; operator confirmation/physical inspection required |
| Flash / actual boot or INFO identity | Not performed / not observed |
| Effective DUTchMate profile, serial, DTR/RTS | Not resolved on hardware; service never started |
| New schema-v2 session IDs | None |

Actions/commands performed:

```bash
rtk proxy git diff --check
rtk proxy git add docs/development_history.md docs/development_status.md hardware/firmware/zephyr_dut/README.md hardware/firmware/zephyr_dut/src/fixture_protocol.c hardware/firmware/zephyr_dut/src/fixture_protocol.h hardware/firmware/zephyr_dut/src/main.c hardware/validation/phase1_basic_hil.md tests/hardware/zephyr_dut/fixture_protocol_harness.c tests/hardware/zephyr_dut/test_fixture_protocol.py
rtk proxy git diff --cached --check
rtk proxy git commit -m 'test(hardware): prepare Basic Phase 1 HIL fixture'
rtk proxy git push origin stage8-phase1-acceptance
rtk proxy ssh-add -l
rtk proxy env GIT_TERMINAL_PROMPT=0 git push https://github.com/leonahi/DUTchMate.git stage8-phase1-acceptance:stage8-phase1-acceptance
```

Read-only `rtk proxy .venv/bin/python -` scripts verified the reviewed source
digests against `fixture-build-report.json`, branch and absence of production
changes; then independently used `hashlib.sha256(uf2.read_bytes())` with an
assertion against the required hash, `serial.tools.list_ports.comports()`,
`Path('/Volumes').iterdir()`, and `Path('/Volumes').glob('*/INFO_UF2.TXT')`.
The raw inventory is also retained locally at
`/tmp/dutchmate-basic-hil-current-preflight.json`. No device was opened.

Push failed through SSH (`Permission denied (publickey)`; no agent identities)
and HTTPS (no available username/credentials). No production or fixture behavior
was patched, no alternative flashing mechanism was attempted, and no service,
external terminal, Monitor, Interact, follow, or console was started.

| Phase 1A criterion | This attempt |
|---|---|
| Continuous ambient RX / single service reader | Not tested — stopped before ownership |
| Boot/INFO physical identity | Not tested — no flash/serial open |
| Follow and recording after detach | Not tested |
| Duration/literal Monitor with exact ranges | Not tested |
| Default-disabled TX and explicitly enabled exact audited send | Not tested |
| Deterministic single-send Interact | Not tested |
| DELAYFAULT completion-before-fault ordering | Not tested — no operation/evidence sequence exists |
| Service-only line console | Not tested |
| Native v2 records and session/list/detail/evidence/log retrieval | Not tested |
| Linked size/segment rollover | Not rerun; earlier deterministic tests remain historical software evidence |
| Host-observation timestamps and truthful Basic loss state | Not tested |
| DTR/RTS requested/open provenance | Not tested |
| Release / external same-port ownership / reacquire | Not tested; no segment or observation gap created |
| Unexpected reconnect with v2 evidence | Not tested |
| Shared unit/service/CLI tests | Not rerun for wording-only finalization; prior 1,496-test result retained in history |
| Real generic adapter + Zephyr HIL | Blocked before flash/setup verification |

Required operator actions: restore GitHub authentication for the requested
branch push; disconnect Pico USB, hold BOOTSEL while reconnecting its USB data
cable, then release BOOTSEL when `RPI-RP2` appears. Confirm that board is the
Pico 1/Pico H and the wiring is GP0/pin 1 to FTDI RX, GP1/pin 2 to FTDI TX,
GND/pin 3 to FTDI GND, Pico independently USB-powered, FTDI VCC disconnected,
and adapter logic 3.3 V. Do not confuse its UF2 volume with another board.

This is an authentication/physical setup blocker, not an observed DUTchMate
software failure. Stage 8, Phase 1A, Phase 1B, and Phase 1 remain incomplete;
Enhanced HIL was not started and MCP migration remains deferred. This new HIL
blocker documentation remains uncommitted for review.

## Operator setup confirmation / waiting for push — 2026-10-26

At `2026-10-26T19:08:29.149606+05:30`, read-only serial discovery again
identified FTDI FT231X `0403:6015`, serial `D358SG6A`, at
`/dev/cu.usbserial-D358SG6A`; the reviewed UF2 hash still matched exactly.
`lsof` listed no owner of the cu/tty paths. The current CLI help and local
Basic 115200 8-N-1, TX-enabled configuration were inspected without starting
the service or opening serial.

The operator subsequently confirmed the connected Pico 1/Pico H was flashed
with `basic-v2-20261026-7bc2ec377767` and that GP0/pin 1 → FTDI RX,
GP1/pin 2 → FTDI TX, GND/pin 3 → FTDI GND, separate Pico USB power,
FTDI VCC disconnected, 3.3 V logic, and open GP2/GP3 all matched.
This confirmation supersedes the earlier missing operator setup information;
actual boot/INFO identity has not yet been observed through DUTchMate.

Another `rtk proxy git push origin stage8-phase1-acceptance` failed with
`Permission denied (publickey)`. The operator requested waiting for their push
before HIL and then requested committing the pending documentation. No serial
port was opened, no firmware was flashed by the agent, and no session or HIL
result was created. The earlier criterion table remains untested. All phase
statuses are unchanged; Enhanced HIL and MCP work were not started.

## Real Basic v2 HIL attempt stopped — 2026-10-26

Result: **incomplete; run invalidated by concurrent software-test store recovery**.
No Phase 1A acceptance is granted. The agent ran pytest against the checkout
while the physical service was active; unisolated service tests recovered its
live session. The resulting reproducible test-isolation defect requires a
separate correction and a fresh HIL run. No production/fixture fix was made.

### Physical and software provenance

| Field | Observed value |
|---|---|
| Branch/commit | Clean `stage8-phase1-acceptance` at `b3f850a4b71cc80c2081fb24f5f151ea01625c84`; upstream tracking ref matched after operator push |
| Fixture source baseline | `746121a35633c070f4e7112010ce26b656d8ef1d` |
| Host | macOS 26.2, Darwin 25.2.0, arm64 |
| Adapter | FTDI FT231X USB UART, VID/PID `0403:6015`, serial `D358SG6A`, `/dev/cu.usbserial-D358SG6A` |
| DUT identity | Pico 1/Pico H confirmed by operator; physical INFO returned `board=rpi_pico`; no independent unique board serial obtained |
| Firmware | `basic-v2-20261026-7bc2ec377767`; actual UART INFO matched exactly; Zephyr v4.4.0 (`684c9e8f32e4373a21098559f748f06915f950c9`), SDK 1.0.1 from reviewed build provenance |
| Reviewed/flashed UF2 | Operator confirmed flashing the reviewed image; independently hashed local image `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`; no device image readback and no agent flash |
| Wiring | Operator confirmed GP0/pin 1→FTDI RX, GP1/pin 2→FTDI TX, GND/pin 3→FTDI GND, own Pico USB power, FTDI VCC disconnected, 3.3 V logic, GP2/GP3 open |
| Service | PID 7478, `127.0.0.1:2040`; explicit Basic selection; one service-owned FTDI descriptor (FD 3u), no external owner |
| Session | `20261026T134413Z-e8d17b99`, native schema v2; started 13:44:13 UTC / 19:14:13 IST |
| Config/profile | `.dutchmate/config.toml`, unnamed profile; SHA-256 `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837` |
| Effective serial | 115200 8-N-1; `rtscts=false`, `xonxoff=false`; exact-path selector, external UART topology; reconnect timeout 5 s |
| TX | Explicit `hardware.uart.tx_enabled=true`; profile default ending `none`; both INFO requests explicitly used LF |
| DTR/RTS | Both requested `driver_default`; open transition `driver_managed`, RTS owner `driver`; electrical readback/glitch-free claims both false |
| Timestamp/loss | Host monotonic microseconds, segment-start origin, `host_serial_read/serial_read_chunk`; `not_observable`, null observer/drop count |

### Exact actions and retrieval

Preflight used `git status --short --branch`, `git rev-parse HEAD
origin/stage8-phase1-acceptance`, independent UF2 hashing/serial enumeration,
and `lsof -nP /dev/cu.usbserial-D358SG6A /dev/tty.usbserial-D358SG6A` through
`rtk proxy`. Current CLI help and source contracts were inspected.

The local recorder `.dutchmate/hil/basic-phase1a-20261026/run.py` invokes the
actual `.venv/bin/dutchmate` and normal HTTP endpoints, saving request start/end
timestamps, exact arguments/bodies, outputs, and return/status codes in
`commands.jsonl` plus numbered JSON files. It does not implement acquisition.

| UTC | Action | Observed result |
|---|---|---|
| 13:43:56 | `dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200`, direct launcher environment | Failed before service creation: runner PATH lacked `dutchmate-service`; preserved in `01-start.json` |
| 13:44:12 | Same CLI arguments under `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv run --frozen --package dutchmate python .../run.py 02-start cli ...` | Service PID 7478 started; no source change needed |
| 13:44:53 | `GET /status` | Connected Basic; no active operations; session/provenance above |
| 13:44:58 | `dutchmate interact INFO --line-ending lf --until 'DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1' --timeout 2` | `timeout`; fixture returned `E_COMMAND_001`; CLI exit 0 did not imply matched acceptance |
| 13:45:09 | `GET /dut/evidence?wait_s=0` | Durable tail cursor saved; this cursorless attachment returns no history |
| 13:45:48 | `POST /dut/uart/send`, body `{"text":"INFO","line_ending":"lf"}` | Separately requested diagnostic send, 5 accepted bytes, audit recorded; not an automatic Interact retry |
| 13:45:50 | `GET /dut/logs?session_id=20261026T134413Z-e8d17b99&lines=20` | Exact reviewed INFO response retrieved |
| 13:46:13 | `GET /sessions/20261026T134413Z-e8d17b99` | Active v2 detail, one segment, 113 RX bytes, no active operation |
| 13:46:37 | Full pytest running concurrently | Default-root `create_app()` tests recovered the live session as `abandoned/service_restart` |
| Before 13:48:06 | Operator briefly grounded RUN then released, with no bounded operation/view active | Operator confirmed reset; boot evidence was not persisted in the invalidated session |
| 13:48:06 | Same session/log retrieval | Session inactive, no BOOT marker; segment ended `service_restart` |
| 13:48:08 | `dutchmate monitor --seconds 0.5` | HTTP 503 `service_unavailable`: `Monitor requires a connected or reconnecting backend` |
| 13:48:39 | `GET /status` | `connection_state=faulted`, no active session/capabilities |
| 13:51:14 | Public `dutchmate stop` under the uv environment | Service stopped; no serial owner listed afterward |

### Preserved evidence and diagnosis

- Original session: `.dutchmate/sessions/20261026T134413Z-e8d17b99/`.
  Independent unchanged copy: `.dutchmate/hil/basic-phase1a-20261026/preserved-session/`.
- Operation start sequence 1, TX attempt 2, successful result 3, fixture command
  error RX 4, timeout terminal 5; range `[1,6)`. Operation ID
  `interact-4577de7a-e938-4a96-b33c-960e0e77c6bc`, attempt
  `ca38f784-3156-49c4-93f6-d9e25e87c4be`. Exactly one `INFO\n` TX (base64
  `SU5GTwo=`), accepted 5 bytes; no retry in this operation.
- Separate INFO attempt/result sequences 6/7, attempt
  `314026c7-4573-409a-bf8d-8b397a1493cd`; RX sequence 8 contains exactly
  `DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1\n`.
  This RX occurred outside a bounded operation, before the later store interference.
- Two RX records total 113 bytes. Decoded RX equals `uart_raw.log` byte-for-byte;
  TX request bytes `INFO\n` are absent from receive-only raw. TX audit records
  live in `operation_events.jsonl` under current schema v2, not the historical
  Basic report's hardware-event location. Attempts precede their results/RX.
- Raw SHA-256 `b2d79f264653793677ded02262c95db9136e311a241dcd8c0b3e63d85e6ebba0`;
  metadata SHA-256 `ec398919bb07faa04acc09c2549cc8ef280ac157b62e2d4b9e5a9005622c7fc0`;
  operation events SHA-256 `0d8687110ca16e6e4451e64d686d0d1ae716f35197ef1f6a01d082d23c244b38`.
  Full manifest: `preserved-manifest.json` in the run directory; all original
  hashes still matched after service cleanup. Only the current PID's log epoch
  is retained as `service-7478.log`, excluding older historical service runs.
- `apps/service/tests/test_errors.py` lines 206, 234, and 252 call `create_app()`
  with no temporary root. `apps/service/src/dutchmate_service/startup.py`
  builds a store and calls `recover_stale_sessions()` before its no-profile
  check. Thus these tests mutate the default real session directory.
- Exact standalone reproduction:
  `rtk proxy .venv/bin/python .dutchmate/hil/basic-phase1a-20261026/reproduce_test_isolation.py`.
  Twice, in temporary directories only, create a synthetic active Basic session,
  construct `TestClient(create_app())`, then try an RX append. Both sessions
  became abandoned/`service_restart`; both appends raised
  `ValueError: schema-v2 evidence can only append while active`. Results are in
  `test-isolation-reproduction.json`. This used no physical backend.

Classification: confirmed service-test isolation defect and acceptance-run
contamination caused by running those tests concurrently with the live service.
The recorder's subsequent fail-stop is not evidence of a normal single-owner
UART defect. The initial fixture command rejection has no established cause;
its later correct INFO response does not erase that anomaly. Neither issue is
silently attributed to wiring or fixed during acceptance.

### Criterion results

| Phase 1A criterion | Result for this run |
|---|---|
| Real Basic startup, exactly one serial owner, effective UART/profile | Observed before interference |
| Physical boot/INFO identity | INFO verified; ambient boot not captured after foreign recovery |
| Continuous operation-independent ambient evidence | INFO RX outside operations observed; complete ambient boot/fault gate not established |
| Follow / continued RX after detach | Not run; stopped at defect |
| Duration Monitor | Blocked: HTTP 503 after recorder fault |
| Literal-condition Monitor | Not run |
| Default-disabled / explicitly enabled audited TX | Explicit enabled TX passed for two sends; default-disabled physical check not run; software gate passed |
| Interact exact bytes, outcome/range, single send | One TX and correct timeout/range observed; matched Interact not established |
| DELAYFAULT ACK terminal before asynchronous fault | Not run; no delayed-fault ordering evidence |
| Service-backed console / recording after exit | Not run |
| Native v2 RX/action/provenance and retrieval | Partial: detail/log/tail attachment work; full listing/cursor replay gate not established |
| Size/segment linked rollover | Not physically exercised; software gate passed |
| Truthful Basic loss and host timestamp provenance | Observed; no lossless/electrical readback claim |
| DTR/RTS requested/open provenance | Observed as truthful driver-default/driver-managed provenance |
| Release / external owner / reacquire, segment and gap | Not run; no handoff segment/gap evidence |
| Unexpected reconnect | Not run |
| Shared unit/service/CLI gate | 1,496 passed in 36.01 s; unsafe default-store side effect identified despite green tests |
| Full real Basic HIL | Incomplete, no acceptance |

Ruff and configured mypy (103 files) passed. Final documentation
`git diff --check` passed. Stage 8, Phase 1A, Phase 1B, and Phase 1 remain
incomplete. Enhanced HIL and MCP work were not started. New HIL documentation
remains uncommitted for review; no production, fixture, or tracked test code
was changed, and the agent did not flash hardware.

## Clean Basic v2 rerun: release failure — 2026-10-26

Result: **incomplete; stopped at Basic release lifecycle failure**. This is a
new physical run. Session `20261026T134413Z-e8d17b99` remains unchanged failed-run
diagnostic evidence and contributes no acceptance to this run. All software
validation completed before physical service startup; no pytest, additional
service/runtime, or session store was created while it was running.

### Preflight and provenance

| Field | Observation |
|---|---|
| Branch / HEAD | Clean `stage8-phase1-acceptance`, `ad8b63abc3c9330864eaa49cb48aab57cd03f2cd`; upstream tracking ref matched |
| Isolation / fixture commits | `7f30a916a3033289dec6908ebeac17a687c0d806` merged; fixture source `746121a35633c070f4e7112010ce26b656d8ef1d` |
| Host | macOS 26.2, build 25C56; Darwin 25.2.0 arm64 |
| FTDI | FT231X USB UART; VID/PID `0403:6015`; serial `D358SG6A`; path `/dev/cu.usbserial-D358SG6A`; location `0-1.3` |
| Physical DUT | Operator-confirmed Pico 1/Pico H, RP2040; actual boot and INFO both identify `board=rpi_pico`; no independent unique board serial obtained |
| Fixture image | Reviewed `basic-v2-20261026-7bc2ec377767`, operator-confirmed flash; no new flash/readback by the agent |
| UF2 | `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/zephyr/zephyr.uf2`; independently verified SHA-256 `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16` |
| Zephyr / SDK | Reviewed build v4.4.0, revision `684c9e8f32e4373a21098559f748f06915f950c9`, SDK 1.0.1; normal `rpi_pico` target, no Enhanced overlay |
| Wiring | Existing operator confirmation: GP0/pin 1→FTDI RX; GP1/pin 2→FTDI TX; GND/pin 3→FTDI GND; Pico USB-powered; FTDI VCC disconnected; 3.3 V logic; GP2/GP3 open |
| Ownership | No preflight serial owner or service listener. PID 3451 then owned exactly one serial FD; follow added no serial descriptor |
| Service / session | `127.0.0.1:2040`; new schema-v2 `20261026T175336Z-3d1dd5a9`, started 17:53:36 UTC / 23:23:36 IST |
| Current config | `.dutchmate/config.toml`; 115200 8-N-1, `rtscts=false`, `xonxoff=false`, explicit `tx_enabled=true`, default ending `none`, sessions budget 16 MiB, retention disabled |
| Profile | Unnamed; digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`; exact-path selector, external UART, reconnect timeout 5 s |
| DTR/RTS | Both requested `driver_default`, open transition `driver_managed`, RTS owner `driver`; no electrical readback or glitch-free claim |
| Timestamps / loss | Host monotonic microseconds, `host_serial_read/serial_read_chunk`, segment-relative; Basic `not_observable`, null observer/drop count |

Software gate: pytest **1,499 passed in 35.84 s**, Ruff passed, configured mypy
passed (103 source files), offline lockfile check passed (66 packages), diff
check passed. Current CLI help was captured before service startup. Gate outputs
and completion timestamp are in `.dutchmate/hil/basic-clean-20261026/gate-*.json`
and `software-gate-complete.json`. No gate was rerun after hardware started.

### Workflows actually executed

All CLI commands below used the actual repository `.venv/bin/dutchmate`.
Service start/stop ran under the documented `uv run --frozen --package
dutchmate` environment so its sibling service executable was on PATH. Local
`run.py` and `scenarios.py` saved exact arguments/bodies, UTC timestamps,
results, outputs, evidence cursors and ownership observations; they use only
CLI/HTTP during service ownership and never construct a session store.

1. `dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200`.
   `GET /status` / `dutchmate status` confirmed the new session and Basic settings.
2. First TX was `POST /dut/uart/send` with
   `{"text":"INFO","line_ending":"lf"}`. It accepted exact `INFO\n`
   (`SU5GTwo=`), attempt/result sequences 1/2; RX 3 contained the exact reviewed
   INFO build. **The earlier `E_COMMAND_001` did not recur**, and is not declared
   fixed. No new raw RX contained that code.
3. With no bounded operation or view running, the operator briefly grounded RUN
   and released it. Two boot banners were retained, with reset-transition NUL
   bytes also preserved; complete boot markers are at evidence sequences 5/7.
   Actual bytes include `DMF/1 BOOT OK board=rpi_pico build=basic-v2-20261026-7bc2ec377767\n`.
4. `dutchmate monitor --seconds 0.5` returned elapsed; no physical RX ownership
   changed. A saved durable cursor was passed to `dutchmate follow --cursor
   <cursor>`; `dutchmate send PING --line-ending lf` produced displayed PONG.
   SIGINT exited follow with code 0. A subsequent standalone
   `dutchmate send INFO --line-ending lf` was still recorded and cursor-retrieved.
   `ownership-with-follow.txt` lists only service PID 3451 / FD 3u on the FTDI.
5. `dutchmate monitor --until 'DMF/1 PONG' --timeout 3` was started, its active
   status observed, then one audited `dutchmate send PING --line-ending lf`
   supplied its deterministic literal. Monitor matched with an exact range.
6. `dutchmate interact PING --line-ending lf --until 'DMF/1 PONG' --timeout 2`
   matched. Separate PING Interacts with `--seconds .3` and with
   `--until 'DMF/1 NEVER' --timeout .3` returned elapsed and timeout. Each
   operation had exactly one durable TX attempt/result; no TX was retried.
7. `dutchmate send DELAYFAULT --line-ending lf` armed an unrelated future log.
   A separate PING Interact with `--until 'DMF/1 ERROR ASYNC code=E_ASYNC_001'
   --timeout 12` retained its PONG plus that asynchronous fault, proving unrelated
   ambient output was not filtered out of the window.
8. Dedicated outside-operation test:
   `dutchmate interact DELAYFAULT --line-ending lf --until 'DMF/1 DELAYFAULT armed delay_ms=10000' --timeout 2`.
   It matched its ACK, then an 11-second idle interval ran with **no Monitor,
   Interact, follow or console**. Status before/after showed no active operation;
   cursor retrieval afterward recovered the later fault from durable evidence.
9. `dutchmate console --line-ending lf` received stdin `PING\nINFO\n` and EOF.
   It emitted audit markers for both LF sends; their RX responses were stored
   and cursor-retrieved. The piped console closed before displaying the later
   RX. A standalone PING after EOF was recorded, proving acquisition continued.
10. `GET /sessions/20261026T175336Z-3d1dd5a9` saved pre-release detail; current
    logs and durable cursor retrieval were successful. Final session listing and
    comprehensive retrieval were scheduled after handoff and were not reached.
11. `dutchmate release` persisted intent but did not finish. Acceptance stopped;
    external ownership/reacquire and unexpected physical reconnect were not run.

### Durable operation and delayed-fault evidence

All ranges below refer to `20261026T175336Z-3d1dd5a9`, with exclusive ends:

| Operation ID | Outcome | Range | TX attempts |
|---|---|---|---:|
| `monitor-64a9b0aa-446f-4d72-9bb7-0b84446e8be7` | elapsed | `[8,10)` | 0 |
| `monitor-da2394af-dee9-47c4-ac64-0ce4d6bcc742` | matched PONG | `[16,21)` | 0 |
| `interact-247abc75-036f-4ab5-b46d-f4f9c8bc44eb` | matched PONG | `[21,26)` | 1 |
| `interact-b447e369-5f97-4ed4-b337-776aa1a39796` | elapsed | `[26,30)` | 1 |
| `interact-5aca4a31-ccee-45a1-8fcc-4936ff29e4c6` | timeout | `[30,34)` | 1 |
| `interact-11283f98-c977-416d-8590-9f4a7e56a559` | matched unrelated ASYNC | `[37,43)` | 1 |
| `interact-7d0e3169-ab80-4465-a62d-630fa9e40b5a` | matched DELAYFAULT ACK | `[43,48)` | 1 |

The dedicated test recorded TX attempt/result 44/45, exact ACK RX 46,
**durable operation terminal 47**, then **fault RX 48** containing
`DMF/1 ERROR ASYNC code=E_ASYNC_001\n`. The fault is outside its operation's
range. ACK→fault host timestamps differ by **10,034,749 us** (10.034749 s);
recorded UTC times are 17:57:49 and 17:57:59. The sequence ordering, not merely
the delay, establishes completion before the ambient fault. Both synthetic
fault emissions remain recorded as expected failure-pattern evidence.

### Release failure, reproduction and cleanup

With status connected and no active operations/views, issue the normal
`dutchmate release` (service endpoint `POST /connection/release`). In this run:

- Request began at `2026-10-26T17:58:26.789445+00:00`; intent
  `release_requested` was durably sequence **57**. The only other connection
  event is initial `connected` sequence 0. No `released` marker, intentional gap,
  successor segment, or reacquire event was generated.
- CLI ended after **65.161843 s** with
  `Error: Device Core Service request timed out.` Status initially continued
  reporting connected, then a guarded status read timed out. The external
  consumer script aborted before its `serial.Serial` line; it never acquired
  or opened the FTDI. No concurrent port ownership occurred.
- OS ownership checks showed the physical FD was closed, but PID 3451 remained
  running. Read-only source tracing and
  `rtk proxy sample 3451 1 1 -file /tmp/dutchmate-basic-release-3451.sample.txt`
  captured diagnostics. The sample reported 11.8G process physical footprint.
  The exact internal failure mechanism has not been confirmed; no additional
  runtime, product patch, or physical repeat was attempted after the failure.
- Public CLI `dutchmate stop` sent SIGTERM and returned, but OS process checks
  still showed the same service alive. After preserving the session and matching
  PID/command identity, SIGKILL stopped that process. Final checks confirmed PID
  absent, no TCP 2040 listener, and no owner of either FTDI cu/tty path.
- This is an observed DUTchMate release lifecycle failure, distinct from the
  earlier test-isolation incident or a demonstrated hardware/wiring problem.
  Metadata remains stale `active` because forced shutdown did not terminalize
  it; it was preserved as recorded, not manually repaired or counted as live.

### Evidence preservation and criterion results

Authoritative session: `.dutchmate/sessions/20261026T175336Z-3d1dd5a9/`.
Run artifacts: `.dutchmate/hil/basic-clean-20261026/`, including pre-stop and final
session copies, full manifests, CLI/HTTP output, process sample, cleanup record,
and `acceptance-summary.json`. There are **590 raw bytes**, **16 RX records**,
**13 successful TX attempts/results**, **7 completed operations**, and contiguous
sequences **0..57**. Concatenated decoded RX matches raw byte-for-byte. Exact
TX request bytes `PING\n`, `INFO\n`, and `DELAYFAULT\n` are absent from RX raw.

| Artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `188c5e65ef42612bbdb812741a15aa270652993354db7341dd733fcfc4001de1` |
| `uart_events.jsonl` | `8b60463df35167d19e1da561d2026aeb991f0e3056872c495cee8dc4c29fcdbf` |
| `operation_events.jsonl` | `a114cf47d1af1df6b242f7369b5f148bfe5ca8ced327b6f30495a3878a82efa1` |
| `connection_events.jsonl` | `70ef61e350adf993e977fe34e7fc15f31362b1d528b48b7bd2475c0534021402` |
| `metadata.json` | `d0c6805c734889ecd05d9bc67b721467d6881d0447edb1b75950b324c4763e12` |

| Current Phase 1A criterion | Result |
|---|---|
| New real Basic connection / one service RX owner | Passed; no old session resumed |
| Continuous ambient RX / physical boot and INFO identity | Passed before lifecycle failure; idle boot markers and exact build retained |
| Follow / continued acquisition after detach | Passed, with durable cursor and post-SIGINT RX |
| Duration / literal Monitor | Passed, exact ranges above |
| TX disabled by default / explicitly enabled exact audited bytes | Default policy covered by pre-HIL software gate; enabled physical TX passed with explicit LF; no force bypass |
| Interact outcomes/ranges / one send / asynchronous RX | Passed for matched, elapsed, timeout and unrelated ambient fault |
| Delayed fault after operation completion | Passed: terminal 47 < fault 48, outside `[43,48)` |
| Service-backed line console / post-exit acquisition | TX/audit/RX persistence and post-EOF acquisition passed; interactive RX display was not exercised |
| Native v2 ambient/operation/action persistence and provenance | Passed for generated evidence; raw/event reconciliation verified |
| Linked size/segment rollover | Pre-HIL deterministic software gate passed; not physically triggered |
| Truthful Basic loss / host observation / DTR/RTS provenance | Passed before release; no lossless/electrical readback claim |
| Release / external same-port owner / reacquire | **Failed at release**; external owner not opened, reacquire not attempted |
| Explicit released interval / fresh segment | Not established; intent only, no completed boundary or observation-gap record |
| Unexpected reconnect | Not run after release failure |
| Session/evidence/log retrieval | Detail/log/cursor retrieval passed before failure; final listing/comprehensive retrieval gate not completed |
| Shared software tests | Passed before physical startup; no tests/store construction during HIL |
| Complete Basic Phase 1A | **Incomplete, not accepted** |

No production, fixture, or tracked test code changed. Only this appended report
and development status/history changed, left uncommitted for review. Final
`git diff --check` and preservation checks passed. Stage 8, Phase 1B, and Phase 1
remain incomplete. Enhanced HIL and MCP work were not started. The old failed
session/report were preserved unchanged, and no firmware was flashed.

## Release-fix Basic v2 rerun — 2026-10-27 IST

Result: **incomplete; no Phase 1A acceptance**. Release/external ownership/
reacquire passed. Unexpected reconnect exhausted its deadline; final retrieval
also exposed a CLI schema-v2 loss-display defect. Acceptance stopped without
changing production, tests, configuration or firmware. Neither previous failed
session (`20261026T134413Z-e8d17b99`, `20261026T175336Z-3d1dd5a9`) was resumed or
counted. Their historical reports and preserved copies remain intact.

### Preflight and provenance

| Field | Actual observation |
|---|---|
| Branch / HEAD | Clean `stage8-phase1-acceptance`, `21991fa403ad39f3100a24259b6f31a4c8ac1756`; reviewed release fix `df3ca29` merged |
| Pushed verification | HEAD/tracking ref matched; independent HTTPS `ls-remote` returned the same SHA. SSH authentication was unavailable |
| Host | macOS 26.2 build `25C56`, Darwin/arm64; local timezone Asia/Kolkata |
| FTDI | FT231X USB UART, VID/PID `0403:6015`, serial `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, location `0-1.3` |
| DUT | Operator reconfirmed Pico 1/Pico H, RP2040; physical preflight INFO and service boot/INFO identify `rpi_pico` and the exact reviewed build; no independent unique Pico serial obtained |
| Wiring / straps | Reconfirmed GP0/pin 1→FTDI RX; GP1/pin 2→FTDI TX; GND/pin 3→FTDI GND; Pico USB power; FTDI VCC disconnected; 3.3 V logic; GP2/GP3 open |
| Fixture | Existing operator-confirmed `basic-v2-20261026-7bc2ec377767`; no flash or rebuild |
| Build inputs | Reviewed Zephyr v4.4.0, revision `684c9e8f32e4373a21098559f748f06915f950c9`, SDK 1.0.1; normal `rpi_pico/rp2040`, no 460800 overlay |
| UF2 | `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/zephyr/zephyr.uf2`; freshly recomputed SHA-256 `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16` |
| Build configuration | `.config` SHA-256 `9bcb30687dd409d62d90fd083c2ebd208e432b54f4007801722a6677c02b714c`; board/build ID checked; generated UART0 DTS `current-speed=0x1c200` (115200) |
| Ownership preflight | No TCP 2040 listener or FTDI cu/tty owner; exclusive external INFO exchange completed and descriptor closed before service startup |
| Service / session | PID 5444, `127.0.0.1:2040`; fresh schema-v2 `20261026T185908Z-a2a4fdef`, started `2026-10-26T18:59:08Z` / `2026-10-27T00:29:08+05:30` |
| Effective UART | 115200 8-N-1, `rtscts=false`, `xonxoff=false`, explicit `tx_enabled=true`, default ending `none`; commands explicitly requested LF |
| Profile / storage | Unnamed, digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`; external UART/exact-path selector, reconnect 5 s; `.dutchmate/sessions`, 16 MiB, retention disabled |
| DTR/RTS | Both requested `driver_default`, open `driver_managed`, RTS owner `driver`; no electrical readback or glitch-free claim |
| Timestamps / loss | Host monotonic microseconds, segment-relative `host_serial_read/serial_read_chunk`; `not_observable`, null observer/drop count |

All software validation finished **before physical service startup**. Commands
below used prefix `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

| Command | Result |
|---|---|
| `uv run --frozen pytest -q --tb=short` | 1,509 passed in 36.77 s, including fixture, architecture, lifecycle/backend/recorder/service/CLI checks |
| `uv run --frozen ruff check .` | Passed |
| `uv run --frozen mypy` | Passed, 103 files |
| `uv lock --check --offline` | Passed, 66 packages; lockfile unchanged |

Preflight `rtk proxy git diff --check` passed. Current CLI help was captured.
No pytest, second service/runtime or session-store construction ran during HIL.
Local drivers used only CLI/HTTP, OS inspection, serial enumeration and read-only
native files while DUTchMate owned the connection.

### Actions and evidence

Artifacts: `.dutchmate/hil/basic-release-rerun-20261027/`. Gate/preflight JSON,
`commands.jsonl`, `scenario-actions.jsonl` and local scripts retain exact
arguments/bodies, outputs, UTC times, cursors and ownership observations. The
local date is October 27; recorded UTC timestamps are October 26.

1. `git -c credential.helper= ls-remote https://github.com/leonahi/DUTchMate.git refs/heads/stage8-phase1-acceptance`
   independently verified pushed HEAD after SSH failed. Rehashed image/config,
   enumerated FTDI, checked ownership, and performed a separate exclusive
   pre-service `serial.Serial` exchange: exact `INFO\n`, exact reviewed INFO
   response, then close. No service/runtime/store was constructed for that
   preflight exchange.
2. `uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200`
   started the single physical service. Other CLI calls below used repository
   `.venv/bin/dutchmate`. `GET /status` verified the fresh session/configuration.
   First audited `POST /dut/uart/send` body
   `{"text":"INFO","line_ending":"lf"}` accepted exact `INFO\n` (`SU5GTwo=`),
   attempt/result 1/2; RX 3 has the reviewed build. **No `E_COMMAND_001` recurred**
   anywhere in new raw RX; the older unexplained observation remains preserved.
3. Saved the durable tail; operator grounded/released RUN with no operation or
   view active. RX 4/5 retain two complete
   `DMF/1 BOOT OK board=rpi_pico build=basic-v2-20261026-7bc2ec377767\n` markers.
   Reset NUL bytes and one interrupted banner were retained without filtering.
4. `dutchmate monitor --seconds 0.5` elapsed. Attached
   `dutchmate follow --cursor <saved-cursor>`, sent
   `dutchmate send PING --line-ending lf`, and observed displayed PONG. SIGINT
   detached follow with exit 0. A later `dutchmate send INFO --line-ending lf`
   remained durably retrievable. Only service PID 5444 owned the FTDI.
5. `dutchmate monitor --until 'DMF/1 PONG' --timeout 3` became active, then one
   audited LF PING supplied its literal; Monitor matched with a durable range.
6. PING Interacts using `--line-ending lf` and respectively
   `--until 'DMF/1 PONG' --timeout 2`, `--seconds .3`, and
   `--until 'DMF/1 NEVER' --timeout .3` returned matched, elapsed and timeout.
   Every Interact has exactly one TX attempt and one successful result accepting
   its exact byte length; no retry.
7. `dutchmate send DELAYFAULT --line-ending lf`, followed by
   `dutchmate interact PING --line-ending lf --until 'DMF/1 ERROR ASYNC code=E_ASYNC_001' --timeout 12`,
   retained PONG and the unrelated asynchronous fault inside the operation.
8. Dedicated test:
   `dutchmate interact DELAYFAULT --line-ending lf --until 'DMF/1 DELAYFAULT armed delay_ms=10000' --timeout 2`.
   After durable ACK completion, waited 11 seconds with **no Monitor, Interact,
   follow or console**. Status before/after showed no active operations; later
   cursor retrieval recovered the fault.
9. `dutchmate console --line-ending lf` kept stdin open while PING and INFO were
   sent separately; **both RX responses actually displayed**. Only the service
   owned serial. EOF exited 0; a subsequent standalone LF PING remained recorded.
10. Sent/retrieved a final LF PING/PONG, then ran `dutchmate release`. Verified
    released status, durable boundary/gap, segment closure and no serial owner
    before opening any external tool.
11. `external_owner.py` checked released/no-owner state, opened the same FTDI at
    115200 8-N-1/no flow control, wrote `PARTIAL\n`, and received exactly
    `DMF/1 PARTIAL complete\n`. PID 5608 was sole owner. A 6-second hold exceeded
    the reconnect window; service remained released. External close preceded
    `dutchmate reacquire`, which returned connected, same session, fresh segment 1.
12. `dutchmate interact INFO --line-ending lf --until 'DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1' --timeout 2`
    matched after reacquire. External PARTIAL output is absent from service raw
    RX, truthfully representing the observation gap.
13. Saved a cursor and observed status during operator FTDI-only USB unplug/
    replug. Unexpected reconnect timed out; no manual reacquire or further
    acceptance operation followed. Pico USB power and UART wiring stayed intact.
14. Retrieved `dutchmate sessions`, `dutchmate session <new-id>`,
    `dutchmate logs --session <new-id> --last 100`, and `GET /sessions/<new-id>`.
    Saved-cursor `GET /dut/evidence` returned all 68 records from 4 through 71
    and reached the tail; initial INFO was separately retrieved earlier. Final
    CLI loss output exposed the defect below. Preserved session/log, then used
    `uv run --frozen --package dutchmate dutchmate stop` and checked OS cleanup.

### Durable operation and handoff ordering

Ranges are half-open, in session `20261026T185908Z-a2a4fdef`:

| Operation ID | Outcome | Range | TX attempts |
|---|---|---|---:|
| `monitor-83b4f0b7-cecf-493b-b022-d8d7bd08d6f7` | elapsed | `[6,8)` | 0 |
| `monitor-0b24e88e-9c42-4ed7-9b8b-ba4c59ec97be` | matched PONG | `[14,19)` | 0 |
| `interact-b7737e5a-525c-4fe7-ae19-fcd45d26ae28` | matched PONG | `[19,24)` | 1 |
| `interact-ed31c9a5-82f8-45e2-ac8b-6ffaa6347150` | elapsed | `[24,28)` | 1 |
| `interact-09833d5b-44e3-471b-9d9b-f29f1e5a0d50` | timeout | `[28,32)` | 1 |
| `interact-4d45dbfb-098e-44e1-9005-c9c370dd391f` | matched unrelated ASYNC | `[35,41)` | 1 |
| `interact-4beba278-77c5-41fd-a300-25a08ff01556` | matched DELAYFAULT ACK | `[41,46)` | 1 |
| `interact-00200859-df06-47d5-be85-ac5a5c83df59` | matched INFO after reacquire | `[64,69)` | 1 |

Dedicated delayed fault: TX 42/43, ACK RX **44**, durable terminal **45**, later
fault RX **46**, outside `[41,46)`. ACK→fault host delta **10,028,466 us**
(10.028466 s); terminal/fault UTC times 19:01:31/19:01:41. Durable order proves
operation completion before ambient fault, independently of timing. Both
deliberate ERROR markers appear in failure-pattern projection as expected.

Release CLI completed in **0.695716 s**. Final PONG RX **58** remains persisted,
then `release_requested` **59** and `released` **60** close segment 0 at 19:02:09
and count one intentional gap. Status answered released and OS showed no owner.
Reacquire at 19:02:34 records **61** (`reacquire_started`), **62**
(`segment_opened`) and **63** (`reacquire_succeeded`). Segment 1 has
`start_reason=reacquire`, a fresh host origin and the same serial provenance;
INFO RX **67** confirms acquisition. Every recorded RX byte survived release.
No forced in-flight-reader race was induced physically; the admitted-final-RX/
late-wakeup race is covered by the pre-HIL deterministic gate.

A local assertion initially omitted the valid `segment_opened` event. Inspection
verified the actual six-event handoff sequence; only the untracked driver
assertion was corrected, without product/test changes or a physical retry.

### Reconnect timeout and CLI defect

At **19:04:31 UTC**, unexpected disconnect **69** closes segment 1 and reconnect
start **70** records `timeout_s=5.0`. At **19:04:36**, failure **71** records
`reconnect_timeout`; metadata becomes `failed` with two observation gaps total.
Status remains responsive/disconnected. Operator confirmed replug within about
1–2 seconds. Later enumeration identifies the same FTDI path/VID/PID/serial/
location, but **OS availability during the five-second window was not measured**.
No automatic successor segment or post-reconnect RX exists. The unsuccessful
mandatory gate has an unclassified cause: enumeration/open availability versus
DUTchMate reconnect behavior is not established. No deadline enlargement,
product patch or further physical reproduction occurred. The HTTP-only status
watcher was interrupted after terminal failure; its progress is preserved.

Final retrieval independently demonstrates a product presentation defect:
`dutchmate session <id>` prints **`Integrity: none`**, and `dutchmate sessions`
prints **`loss=none`** for native v2. The API and metadata instead correctly expose
`evidence_quality.backend_integrity.loss_status=not_observable`; prior status and
the logs warning agree, recording quality is `complete`, observer/drop count are
null. `apps/cli/src/dutchmate_cli/sessions.py` formats the obsolete top-level
`integrity` field for both views, explaining the reproducible omission.
`47-final-sessions.json`, `48-final-detail.json`, and `50-final-retrieval.json`
preserve output versus API payload. No fix was applied during acceptance.

### Criterion-by-criterion decision

| Current Phase 1A criterion | Result |
|---|---|
| Real continuous Basic RX; ambient boot/INFO | Passed, exact reviewed build, no operation/view during reset |
| Follow/display/detach and continued recording | Passed; one service serial owner |
| Duration/literal Monitor | Passed, explicit outcomes/ranges |
| Default-disabled TX / enabled exact audited TX | Default/denial covered by fresh pre-HIL tests; 15 exact physical TX pairs passed with explicit LF |
| Interact matched/elapsed/timeout, one send, async RX | Passed; durable ranges and attempt/result correlations verified |
| Fault after durable operation completion | Passed: terminal 45 < fault 46, outside range, >10 s after ACK |
| Service console / recording after EOF | Passed; live PONG/INFO display and later PONG persisted |
| Native-v2 ambient/action/operation storage | Passed; 72 contiguous records, raw RX reconciled byte-for-byte |
| Linked size/segment rollover | Fresh deterministic gate passed; 16 MiB/32-segment bounds not physically forced |
| Basic loss / host timestamps / serial DTR/RTS | Native/API/log evidence passed; **CLI session/list loss projection failed** |
| Release intent, RX settlement, segment/gap, prompt responsive release | Passed; RX 58, intent 59, released 60; 0.696 s |
| Real external ownership and fresh-segment reacquire | Passed; sole external PID 5608, 6-second hold, segment 1 and INFO |
| Unexpected reconnect through native v2 | Disconnect/start/timeout evidence passed; **automatic recovery not demonstrated**, cause unclassified |
| Session/list/detail/evidence/log retrieval | Retrieval succeeded; CLI semantic loss projection defective |
| Shared unit/service/CLI/architecture checks | 1,509 passed before physical startup; no concurrent tests/runtime/store |
| Complete Phase 1A Basic | **Incomplete, not accepted** |

### Preservation and shutdown

Authoritative session: `.dutchmate/sessions/20261026T185908Z-a2a4fdef/`. Before/
after-stop copies, service log, hashes and `acceptance-summary.json` are in the
run artifact directory. Final counts: **725 raw bytes**, **17 RX records**,
**15 successful TX pairs**, **8 completed operations**, **2 segments**, contiguous
sequences **0..71**. Native-v2 TX/action records reside in
`operation_events.jsonl`; `hardware_events.jsonl` is empty. Decoded RX matches raw
exactly; command bytes and external PARTIAL output are absent from RX.

| Final artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `e2e3cd4a104e07e23625fcb77b9923066cc73295f77167154ee35e6b42e6cc0e` |
| `uart_events.jsonl` | `efa2beb7b332145577af9c8292bdde3f6dbc7b04ff65fe7f552047e832150101` |
| `operation_events.jsonl` | `c53e6b23a8cc2017422d0853c0a0aa49f2922b8be60e3d986c88036bf9a9b939` |
| `connection_events.jsonl` | `69533c1a0791981dce145267902beb2e11986af97d754fa17d3898c752857c19` |
| `metadata.json` | `6a0aebc7c2e19463be704cd3d4e821969d12e4078c6d8ef8eddf44371a7a8ca5` |

Normal single-service startup recovered the prior stale-active release-failure
session to `abandoned/service_restart` and removed its terminal reserve. Original
metadata/reserve hashes still match the earlier preserved
`basic-clean-20261026/preserved-final-session/` copies. Its RX/action/operation/
connection files and the earlier failed session are unchanged. This expected
startup recovery is explicit in `failed-session-startup-recovery.json`, rather
than claiming the live stale metadata remained byte-for-byte unchanged.

Graceful stop needed no SIGKILL. At `2026-10-26T19:06:49.366247Z`, PID 5444 was
absent, TCP 2040 had no listener, and neither FTDI cu/tty path had an owner
(`52-cleanup-verification.json`). Stage 8, Phase 1A, Phase 1B and Phase 1 remain
incomplete. Enhanced HIL and MCP were not started. Only this report and
development status/history changed, left uncommitted for review; final
diff/preservation checks are recorded in history.

## Focused Basic unexpected-reconnect diagnostic — 2026-10-27

Result: **automatic reconnect succeeded in the fully observed repeat** within
the unchanged `reconnect_timeout_s=5.0`. No reconnect product defect was
reproduced. Earlier timeout causes remain unclassified; this result does not
retroactively establish their OS availability or complete Phase 1A. No full
Basic HIL, Enhanced HIL or MCP workflow was run.

### Preflight, scope and method

- Clean branch `stage8-phase1-acceptance`, HEAD
  `7d6cac3764176820f6dc62f79f2d705749735b24`, independently matched to pushed
  HTTPS `ls-remote`. Reviewed CLI fix `ff8cc51` is merged. No production, test,
  firmware, API or configuration changes were made.
- Host: macOS 26.2 build `25C56`, Darwin 25.2.0 arm64. All table times below are
  UTC on October 27; local Asia/Kolkata time is UTC+05:30.
- FTDI FT231X `0403:6015`, serial `D358SG6A`, path
  `/dev/cu.usbserial-D358SG6A`, current USB location `0-1.4` (IORegistry location
  ID `1310720`). This differs from the older report's `0-1.3`; the repeat used
  the same current socket. Serial enumeration and IORegistry independently
  identified it. No service listener or FTDI cu/tty owner existed at preflight.
- Existing Basic configuration remained byte-for-byte unchanged: external UART,
  exact-path selector, reconnect 5.0 s, 115200 8-N-1, no RTS/CTS or XON/XOFF,
  explicit TX enabled, default line ending none, driver-default DTR/RTS. Profile
  digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
  Pico USB power and UART wiring stayed connected. Correct INFO responses
  identify reviewed `rpi_pico` build `basic-v2-20261026-7bc2ec377767`; no flash
  or build was performed.
- Software gate completed before the first physical startup: 1,514 pytest tests
  passed in 36.83 s, Ruff passed, mypy passed (103 files), offline lock check
  passed (66 packages), and `git diff --check` passed. Commands used
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. Current CLI help was
  captured. No tests or additional runtime/session store ran while either
  physical service was running; the first service was stopped before the repeat.
- Normal starts used
  `uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200`.
  The operator used local `mark_actions.py` to timestamp Enter immediately before
  unplug and after replug. Parallel passive observers recorded IORegistry USB
  matches, node `stat`, service-path `lsof`, HTTP status and read-only connection
  evidence with UTC and monotonic timestamp pairs. No runtime monkeypatching or
  production instrumentation was used.
- DUTchMate retains ownership during reconnect, so no external open probe
  competed with it. Successful service open is proven by reconnect publication
  and a positive descriptor observation. The only external probe occurred after
  the first attempt had terminalized, with disconnected status and no owner; it
  sent/read zero bytes and closed before the next normal start.

### First attempt: preserved with incomplete host timing

Session `20261027T063720Z-2c95d57d`, PID 3175, first INFO matched. A local helper
initially named `operator.py` shadowed Python's standard module and prevented the
startup wrapper from importing; it was renamed before the service started. This
was a diagnostic helper error, not DUTchMate behavior.

The first observer's six-minute operator-wait window ended at
06:44:03.879462, before the operator's pre-unplug marker at 06:44:17.251883 and
post-replug marker at 06:44:34.144737. Native evidence nevertheless retained
`unexpected_disconnect` 6 and `reconnect_started` 7 at 06:44:18, then
`reconnect_failed` 8 / `reconnect_timeout` at 06:44:23. An attempted observer
renewal found the service already disconnected and stopped at its connected
precondition. The USB/node transitions during this interval were missed.

These markers span 16.893 seconds but do not establish actual physical
downtime or OS availability. A later measured external open succeeded after
timeout (`05-post-timeout-open.json`); it does not prove earliest openability.
This attempt remains **unclassified**, not an environment or software diagnosis.
Its session, observer output and limitations are preserved. Public CLI stop
completed, and no listener/serial owner remained before the focused repeat.

### Fully observed repeat and timeline

Fresh session **`20261027T064604Z-7239cdfe`**, PID **18348**. The passive observer
remained active until the physical action, without an operator-wait expiry.
The production reconnect deadline remained 5.0 s.

| Event | Recorded UTC / evidence |
|---|---|
| Operator marker immediately before unplug | `06:51:45.911877` |
| Serial node first observed absent | `06:51:47.546341` |
| Durable `unexpected_disconnect` | Sequence **11**, native wall time `06:51:47Z`, first observed `06:51:47.546443` |
| Durable `reconnect_started` | Sequence **12**, same first-observed poll; detail `timeout_s=5.0` |
| FTDI USB first observed absent | `06:51:47.595688` |
| Same VID/PID/serial USB device enumerated again | `06:51:48.560095` |
| `/dev/cu.usbserial-D358SG6A` first observed back | `06:51:48.565031`, inode 713 (previously 705) |
| Successful service open proven by publication | **No later than `06:51:49.091107`**, first observation of durable success; exact open syscall return time is not logged |
| Durable fresh segment / reconnect success | **13** `segment_opened`, **14** `reconnect_succeeded`; native time `06:51:49Z`, first observed `06:51:49.091107` |
| Operator marker immediately after replug | `06:51:49.110892` (USB was already enumerated) |
| HTTP connected status observed | `06:51:49.117489`, same active session, segment 1 |
| Service serial FD first positively observed again | `06:51:49.146319`, PID 18348 / FD 3 |
| `reconnect_timeout` | **None in the repeat** |

Observed start-to-success delta is **1.544660125 s**, well inside five seconds.
Node reappearance preceded observed durable success by about 0.526 s. Individual
failed reconnect/open attempts and error codes are not emitted by existing
service logs/evidence; their number/times are **not inferred** from backoff code.
Password-free passive syscall tracing was unavailable (`sudo -n` requires a
password); no credentials or production changes were used to obtain it.

These are observation times, not invented mechanical or syscall timestamps.
Keypress markers bound/report operator actions; the physical contact instants
were not directly instrumented. Native connection wall times have one-second
resolution, while durable sequence order and the observer's monotonic clock
establish ordering. Conservative change brackets from adjacent samples are:

| Host transition | Previous sample start → first positive/negative sample finish |
|---|---|
| USB disappears | `06:51:47.500474` → `06:51:47.595688` |
| Node disappears | `06:51:47.533746` → `06:51:47.546341` |
| USB reappears | `06:51:48.353355` → `06:51:48.560095` |
| Node reappears | `06:51:48.552395` → `06:51:48.565031` |
| Service FD positively visible again | `06:51:49.050453` → `06:51:49.146319` |

The path-filtered `lsof` sample cannot timestamp closure of an old descriptor
while the device node is missing. A negative sample then includes `stat` errors;
it is not silently treated as an exact close event. Successful publication and
final ownership checks provide the stronger assertions. No external probe
measured the earliest possible open before the service succeeded; the actual
successful service open is sufficient to demonstrate in-window openability.

### Continuity, resumed RX and command anomaly

The same native-v2 session stayed active across the successful reconnect.
Segment 0 closes with `end_reason=unexpected_disconnect`; segment 1 opens with
`start_reason=reconnect` and a fresh host-monotonic origin. Metadata durably
records one observation gap. Profile/serial/DTR/RTS settings remain unchanged,
Basic loss is `not_observable`, local recording quality is `complete`, and
status answered connected with no active operation after the checks.

The earlier unexplained command anomaly **recurred**, independently of reconnect
publication: exact audited `INFO\n` (5 accepted bytes) received
`DMF/1 ERROR COMMAND code=E_COMMAND_001\n` at RX **4** before unplug and RX **18**
after successful reconnect. Their INFO-condition Interacts timed out truthfully.
Separate explicit INFO retests matched the exact reviewed build at RX **9** and
**23**. Each operation sent once; this was not automatic TX retry. Post-reconnect
RX 18/23 proves resumed recording, including the unexpected response. No cause
is assigned to DUTchMate, the fixture or wiring from audit/response evidence
alone, and no fix was made. The anomaly remains a separate acceptance concern.

### Evidence preservation and cleanup

Artifacts: `.dutchmate/hil/basic-reconnect-diagnostic-20261027/`, with the complete
repeat under `repeat/`. Files include software/preflight records, action markers,
`timing-samples.jsonl`, `timing-summary.json`, `event-sampling-statistics.json`,
`diagnostic-summary.json`, native before/after-stop copies, raw service logs and
exact CLI/HTTP argument/output records. The first attempt's missed interval and
helper/precondition errors are explicitly retained, not erased by the repeat.

The repeat contains **226 raw RX bytes**, **4 RX records**, **4 TX pairs**,
**4 completed operations**, **2 segments**, and contiguous evidence **0..24**.
Decoded RX reproduces raw bytes exactly. Final state is
`completed/service_shutdown`, with gap count 1 and no unresolved action.

| Final repeat artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `d19391e91b1caeaff0bb9fe59480bd51e82624e4089293beb3b081441f997a7e` |
| `uart_events.jsonl` | `a534ab9619158513dc02eef6b6d150eecfc7a15b19f22c9a4e0456043013ed48` |
| `operation_events.jsonl` | `61cc8f243df951298ef36967625dd11bee5bb00c37627d6a27f06c1fa33e03ca` |
| `connection_events.jsonl` | `810379a239a920db42f29f2bf86162ee24a4057cda53a52c9c4146235c796c82` |
| `metadata.json` | `2978294e9b2db2b9d5c2719b7decfb314b3d946bade3cbecc6ed3515960ea9ad` |

Normal CLI stop needed no SIGKILL. At **06:54:05.385913 UTC**, PID 18348 was
absent, TCP 2040 had no listener, and neither FTDI cu/tty path had an owner
(`repeat/11-cleanup-verification.json`). All pre-existing session hashes and
configuration bytes are unchanged. Only this report and development
status/history were updated, uncommitted for review. Phase 1A, Stage 8,
Phase 1B and Phase 1 remain incomplete; Enhanced HIL and MCP remain deferred.

## Focused E_COMMAND_001 command-path diagnostic — 2026-10-27

Result: **unclassified; the minimal new pair did not reproduce the anomaly**.
Both separately requested INFO operations returned the exact reviewed response.
No passive logic analyzer is available (operator confirmed), and the unchanged
fixture exposes neither its received command bytes nor its parser state. Host
audit and fixture responses cannot distinguish host/adapter/electrical effects
from fixture UART/parser behavior. Earlier error observations are not erased or
reclassified. No production or fixture patch was made.

### Preflight and observability

- Clean `stage8-phase1-acceptance`, HEAD
  `04f2ff28e47248bead99e9e3dc67d1af34bb693b`, independently matched to the latest
  pushed branch by read-only HTTPS `ls-remote`.
- macOS 26.2 build `25C56`, Darwin 25.2.0 arm64; FTDI FT231X `0403:6015`, serial
  `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, location `0-1.4`. Only FTDI and USB
  hubs were visible in USB inventory; no analyzer command was found on PATH. The
  operator separately confirmed no analyzer was available. No serial owner or
  service listener existed before startup.
- Current configuration was retained byte-for-byte: Basic/external UART/exact
  path; 115200 8-N-1, no flow control; TX explicitly enabled; default ending
  none; driver-default DTR/RTS; `reconnect_timeout_s=5.0`. Requested/open line
  provenance is not an electrical waveform measurement.
- Before physical startup: full pytest **1,514 passed in 37.39 s**, Ruff passed,
  mypy passed (103 files), offline lock check passed (66 packages), and
  `git diff --check` passed. Exact software commands used prefix
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. No tests or additional
  runtime/session store ran while the physical service was running.

### Source findings, distinct from physical evidence

Reviewed `hardware/firmware/zephyr_dut/src/main.c` accumulates non-CR/non-LF
bytes in a 32-byte command buffer. CR is ignored. LF invokes the command handler
with the accumulated length (or zero when discarding an overlong line), then
resets both command length and discard state. There is no idle-time clearing of
an unterminated prefix. NUL is not filtered by this loop. The protocol handler
requires a length-exact `INFO` match; unrecognized commands emit `E_COMMAND_001`.

Thus an earlier unexpected non-CR prefix could make a later `INFO\n` fail, with
the following LF clearing state so a separate INFO succeeds. An overlong line
could also reach the error branch. These are **hypotheses supported by source
semantics, not measurements that either occurred on the Pico**. Current protocol
tests exercise the command handler with supplied arguments; they do not expose
the physical UART ingress or live line-assembler state.

Basic open code performs no explicit UART handshake/write; its send loop passes
the requested bytes to the serial write and accounts for accepted writes.
Installed pySerial 3.5 open code configures the port/control lines and resets the
host input buffer. That does not inspect or clear the Pico's command buffer, and
source inspection does not measure wire behavior during USB/open transitions.
The installed open implementation was preserved in `pyserial-open-source.txt`.

Earlier preserved errors in `20261027T064604Z-7239cdfe` were read at RX 4,
29.128772 s after segment-0 source origin, and RX 18, 26.111850 s after segment-1
origin. Those host read times do not reveal when any prefix arrived; idle time
alone would not clear one under the reviewed parser loop. No stabilization
delay, parser workaround or timeout change was introduced.

### Minimal physical sequence and timing

Fresh native-v2 session **`20261027T071337Z-3be5f126`**, service PID **32203**.
All times below are UTC on October 27; local Asia/Kolkata is UTC+05:30.

Normal startup command:

```text
uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200
```

The HTTP-only local driver made exactly two planned, distinct
`POST /dut/interact` requests, regardless of the first outcome. Each body was:

```json
{"text":"INFO","line_ending":"lf","conditions":[{"pattern":"DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1"}],"timeout_s":2.0}
```

The existing INFO completion condition and two-second bound were retained.
Neither operation retried its TX. No command, blank-line resynchronization or
fixture reset was inserted before the first INFO. No USB unplug/reconnect was
performed in this slice; prior transition cases remain separate evidence.

| Event | UTC / native evidence |
|---|---|
| Start CLI invoked / returned | `07:13:36.831689` / `07:13:37.208425` |
| Configured Basic source origin | Host monotonic `4287918562 us`; created after configured serial open, not an exact open-syscall timestamp |
| Before first request | No earlier audited TX; host RX file empty. Pico ingress and parser contents **unknown** |
| First INFO request / HTTP return | `07:13:37.231648` / `07:13:38.187669` |
| First accepted TX | `07:13:37.237086`, attempt/result **2/3**, exact `494e464f0a` (`SU5GTwo=`), accepted 5 bytes |
| First response / terminal | RX **4**, exact reviewed INFO; terminal **5**, `matched` |
| Second INFO request / HTTP return | `07:13:38.188250` / `07:13:39.194046` |
| Second accepted TX | `07:13:38.197810`, attempt/result **7/8**, same exact bytes, accepted 5 |
| Second response / terminal | RX **9**, exact reviewed INFO; terminal **10**, `matched` |

First request was **72.269166 ms** after source origin. The second request began
**0.575875 ms** after the first HTTP result returned, measured using paired host
monotonic timestamps. This is the inter-request gap, not a wire inter-byte or
electrical-settling measurement.

| Operation | ID | Outcome / half-open range |
|---|---|---|
| First INFO | `interact-362b9f98-c97d-47e1-8181-13d1e37e6fe0` | matched, `[1,6)` |
| Second INFO | `interact-7796d849-d3fd-48e1-b290-24619da9a50f` | matched, `[6,11)` |

Attempts were `aaa6700b-ca5e-463e-8db3-613b58f62484` and
`284368ea-3901-46af-ac0d-3bd607318d1f`. Each operation has one attempt/result
pair, with exactly 5 accepted bytes. Both raw fixture responses were:

```text
DMF/1 INFO board=rpi_pico build=basic-v2-20261026-7bc2ec377767 protocol=1
```

### Evidence-based classification

| Question | Supported conclusion |
|---|---|
| Authoritative DUTchMate requested/accepted bytes | Exact `INFO\n`, 5 accepted bytes for each operation |
| Fixture response bytes | Two correct INFO responses; no new `E_COMMAND_001` in this pair |
| Raw bytes arriving at the Pico, including before INFO | **Not observed**; the firmware has no ingress echo/trace and no analyzer was available |
| Parser buffer/discard state before earlier failing commands | **Not observed** |
| Unexpected wire bytes or electrical/open-transition glitches | Neither established nor excluded |
| Exact wire INFO but faulty fixture parsing | Not established without complete relevant ingress/state evidence |
| Root-cause classification | **Insufficient evidence; unclassified** |

`uart_raw.log` is **Pico TX → FTDI RX → host RX**, not FTDI TX → Pico RX.
An empty pre-command host RX file says nothing about what the Pico previously
received. Accepted-byte audit likewise does not establish physical wire bytes.
The successful new pair does not invalidate earlier failures or exonerate any
layer. Further repetition without ingress capture would not close that gap.

### Preservation and cleanup

Artifacts: `.dutchmate/hil/basic-command-diagnostic-20261027/`, including
software/preflight records, `command_pair.py`, timestamped request/result files,
raw evidence retrieval, `audit-response-analysis.json`, prior-error review,
before/after-stop native copies and service logs. No existing evidence was
modified. Final native state is `completed/service_shutdown`: **148 raw bytes**,
**2 RX records**, **2 TX pairs**, **2 completed operations**, one segment and
contiguous sequences **0..10**. Decoded RX matches raw byte-for-byte.

| Final artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `ff1a9d099ed8a655b7ec4f58e8a0b4fcd3f43361eefd0a9f185820dcf78bb616` |
| `uart_events.jsonl` | `90d561cfbe0acc0cc9de4153e8a0269b23a806a81fc29f11e25bc5e286992e0e` |
| `operation_events.jsonl` | `830e0aa1506bd7e03fc802052281cd194e1c0f4293af42c2a4509d77367d8f40` |
| `metadata.json` | `d8d998ce844e685721bd75546a798f7206227e0a66166cff3331809c1ea98c6d` |

Graceful CLI stop succeeded. At **07:15:15.524773 UTC**, PID 32203 was absent,
TCP 2040 had no listener, and neither FTDI cu/tty path had an owner. Previous
session hashes and configuration bytes are unchanged. Only this report and
development status/history changed, uncommitted for review. Production/fixture
code, parser behavior, UART settings, timeouts and acceptance criteria were not
changed. No full Basic HIL, Enhanced HIL or MCP work occurred. Phase 1A, Stage 8,
Phase 1B and Phase 1 remain incomplete.

## Fresh complete Basic Phase 1A acceptance attempt — 2026-10-27

Result after normative contract audit: **Phase 1A Complete — accepted**. This
fresh run satisfies the current Basic exit criteria, including real handoff and
automatic reconnect with native-v2 evidence and resumed acquisition. Successful
INFO after unexpected reconnect is an added procedure/diagnostic check, not an
explicit requirement of the normative Phase 1A contract or Stage 8 plan.

That additional INFO still returned
`DMF/1 ERROR COMMAND code=E_COMMAND_001\n` and its Interact timed out. This is
preserved as an **unresolved, unclassified, non-blocking command-path anomaly**;
it was not retried, diagnosed or fixed. No production/fixture code was patched.

No prior failed or diagnostic session was resumed or counted as acceptance.
The native journal closed normally. Acceptance follows the criterion mapping
and contract audit below, not journal completion alone. Stage 8, Phase 1B and
overall Phase 1 remain incomplete pending Enhanced HIL and remaining physical
evidence. Enhanced HIL and MCP work were not started.

### Normative acceptance audit — 2026-10-27

Authority is the [Phase 1 implementation specification](../../docs/phase1_implementation_spec.md)
and the [Stage 8 plan](../../docs/dutchmate_phase1_v2_coding_agent_plan.md), whose
authority statement says it must not redefine the normative contracts.

- Specification **§13.6**, unexpected disconnect/reconnect, requires the durable
  boundary, reconnect state/deadline, continued active session and a safely
  opened new segment before the deadline. It does not require INFO or any
  particular DUT command/response after reconnect.
- Specification **§33**, Phase 1A Done, requires that "unexpected reconnect works
  through the same v2 evidence model." Its real Basic HIL list covers continuous
  capture, follow, Monitor, TX/Interact, delayed fault, retrieval and handoff.
  It does not add a successful post-reconnect INFO gate.
- Specification **§14.2** requires received evidence to remain recorded after
  backend reconnection; **§21.5** permits a condition Interact to return timeout
  when its requested literal does not match. Persisting the actual error and
  truthful timeout meets those service contracts; the extra INFO application
  assertion itself remains unsuccessful.
- **Stage 8 → HIL acceptance → Basic** lists continuous recording, follow,
  Monitor, exact TX/Interact, delayed fault, handoff and retrieval/provenance.
  **Stage 8 → Exit criterion** references the specification's Phase 1A/1B done
  criteria. Neither requires a successful INFO after unexpected reconnect.

The earlier incomplete decision incorrectly promoted the added post-reconnect
INFO assertion into a normative gate. The original evidence instead establishes
in-window success 76, the same ownership session, fresh segment 2, the durable
gap, resumed RX 80 and responsive status. The captured response is valid RX
evidence even though its application content is an error. All other §33 gates
are supported by the fresh run and its recorded pre-start software gate.

Default-disabled TX and bounded size/segment rollover are covered by that
1,514-test gate, including `test_basic_send_rejects_disabled_tx_without_writing`,
`test_v2_size_rollover_admits_next_whole_uart_unit_in_linked_successor` and
`test_reacquire_rolls_over_segment_bound_and_preserves_public_cursor`.
The 16 MiB/32-segment physical limits were not forced; §33 and the Stage 8 Basic
HIL list do not require those limits to be physically forced. No earlier failed
run is substituted for any required physical workflow in this accepted session.

This audit changed documentation/acceptance interpretation only. No tests,
service or hardware were run, no normative criteria were edited, and no native
evidence or run artifacts were changed. Pre-audit `acceptance-summary.json` and
`45-acceptance-stop.json` retain the original conservative classification; this
contract audit supersedes that classification without altering their records.

### Preflight and provenance

| Field | Actual evidence |
|---|---|
| Branch / HEAD | Clean `stage8-phase1-acceptance`, `31b14a4de28c3713fbb8451f31520600917616dc`; local HEAD/upstream and independent HTTPS `ls-remote` matched |
| Host | macOS 26.2 build `25C56`, Darwin 25.2.0 arm64; local Asia/Kolkata |
| FTDI | FT231X USB UART, VID/PID `0403:6015`, serial `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, location `0-1.4` |
| Physical DUT / wiring | Operator reconfirmed Pico 1/Pico H, RP2040; GP0/pin 1→FTDI RX, GP1/pin 2→FTDI TX, GND/pin 3→FTDI GND; own Pico USB power, FTDI VCC disconnected, 3.3 V logic, GP2/GP3 open, external terminal closed |
| Fixture | Existing reviewed `basic-v2-20261026-7bc2ec377767`; preflight operator confirmation plus immutable artifact; actual fresh-session boot/INFO verified after startup; no unique Pico chip serial or image readback obtained |
| Build inputs | Reviewed Zephyr v4.4.0 (`684c9e8f32e4373a21098559f748f06915f950c9`), SDK 1.0.1; `rpi_pico/rp2040`, 115200, no Enhanced overlay |
| UF2 / config | Freshly hashed `build/dutchmate-zephyr-dut-basic-v2-7bc2ec377767/zephyr/zephyr.uf2`: `f0e7c42aa8ee770634686e00e263c3d28a9199151d04da5ec0f6a1ddadb88c16`; `.config`: `9bcb30687dd409d62d90fd083c2ebd208e432b54f4007801722a6677c02b714c` |
| Artifact configuration | CMake board `rpi_pico`, overlay override empty, SDK path `zephyr-sdk-1.0.1`; generated UART0 speed `0x1c200` (115200), no hardware flow-control property |
| Ownership preflight | No service listener or FTDI cu/tty owner; serial/USB identity inspection only, no external preflight command or port open |
| Fresh session / process | `20261027T073956Z-7c038da2`, native schema v2; PID 33018, `127.0.0.1:2040`, start `2026-10-27T07:39:56Z` / 13:09:56 IST |
| Effective profile | Unnamed, digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`; Basic/external UART/exact path; reconnect **5.0 s unchanged** |
| UART / storage | 115200 8-N-1; `rtscts=false`, `xonxoff=false`; TX explicitly enabled, default ending none; explicit LF on all sends; 16 MiB budget, retention disabled |
| DTR/RTS / timestamps | Both requested `driver_default`, open `driver_managed`, RTS owner `driver`, no electrical readback/glitch-free claim; host monotonic microseconds, segment-relative `host_serial_read/serial_read_chunk` |
| Loss / local recording | Basic `not_observable`, null observer/drop count; local recording `complete` |

All software checks finished before physical startup. Commands used prefix
`rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`:

| Command | Result |
|---|---|
| `uv run --frozen pytest -q --tb=short` | 1,514 passed in 36.18 s, including fixture, architecture, backend/lifecycle/recorder/service/CLI and rollover checks |
| `uv run --frozen ruff check .` | Passed |
| `uv run --frozen mypy` | Passed, 103 source files |
| `uv lock --check --offline` | Passed, 66 packages; lockfile unchanged |

Preflight `git diff --check` passed; current CLI help and local client-script
syntax checks finished before startup. No pytest, extra DUTchMate runtime/session
store, firmware flash or production/fixture patch occurred while the service
was running. Client wrappers used only CLI/HTTP and read-only native evidence.
The external serial consumer ran only during explicit released ownership.

### Executed sequence

Run artifacts: `.dutchmate/hil/basic-acceptance-fresh-20261027/`. Gate/preflight
records, CLI help, `commands.jsonl`, `scenario-actions.jsonl`, saved cursors,
local scripts and numbered action results retain exact arguments, UTC times,
HTTP bodies, stdout/stderr, ownership checks and native evidence. All following
wall times are UTC on October 27 (IST = UTC+05:30).

1. Started normally with
   `uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200`.
   `GET /status` confirmed the new session/configuration and no active operation.
   Saved the evidence tail before any TX; no command was sent in preflight.
2. With no Monitor, Interact, follow or console active, operator grounded/released
   RUN. Continuous acquisition preserved three complete exact reviewed boot
   banners at RX 2/3/4, plus reset-transition NUL bytes. Then one
   `dutchmate interact INFO --line-ending lf --until '<exact reviewed INFO>' --timeout 2`
   matched, proving physical boot and INFO identity through the fresh path.
3. `dutchmate monitor --seconds 0.5` elapsed. Attached
   `dutchmate follow --cursor <saved-cursor>`, sent LF PING, observed displayed
   PONG, then detached by SIGINT with exit 0. A later standalone LF INFO remained
   durably recorded. Only PID 33018 owned the FTDI during follow.
4. `dutchmate monitor --until 'DMF/1 PONG' --timeout 3` was observed active, then
   one `dutchmate send PING --line-ending lf` supplied its literal; matched.
5. Single-send PING Interacts, each with explicit LF, respectively used
   `--until 'DMF/1 PONG' --timeout 2`, `--seconds .3`, and
   `--until 'DMF/1 NEVER' --timeout .3`. They returned matched, elapsed and timeout.
6. Sent DELAYFAULT once, then ran PING Interact with
   `--until 'DMF/1 ERROR ASYNC code=E_ASYNC_001' --timeout 12`. Its window retained
   the unrelated asynchronous output and PONG; matched the ASYNC marker.
7. Dedicated test:
   `dutchmate interact DELAYFAULT --line-ending lf --until 'DMF/1 DELAYFAULT armed delay_ms=10000' --timeout 2`.
   It matched its ACK, followed by an 11-second interval with no Monitor,
   Interact, follow or console. Status before/after showed no active operation;
   later cursor retrieval recovered the fault outside the completed range.
8. `dutchmate console --line-ending lf` kept stdin open while separately sending
   PING and INFO; live RX displayed both PONG and the exact reviewed INFO. EOF
   exited 0. A later standalone LF PING remained recorded. Only the service owned
   serial during console; no external terminal was opened concurrently.
9. Sent/retrieved a final LF PING/PONG, then `dutchmate release`. Verified durable
   intent, final RX, segment closure, intentional gap, prompt released status
   and absence of a serial owner before the external consumer opened.
10. Real external consumer opened the same port, sent exactly `PARTIAL\n` once,
    received exactly `DMF/1 PARTIAL complete\n`, and held ownership for 6 seconds
    while the service remained released. It closed before `dutchmate reacquire`.
    Reacquire continued the same session in fresh segment 1; its first exact INFO
    Interact matched. External PARTIAL output is absent from service raw RX.
11. Armed passive USB/node/status/descriptor/connection-evidence observers with
    no operator-wait expiry. The operator used `mark_actions.py` to mark FTDI-only
    USB unplug/replug in the same socket, leaving Pico USB/UART wiring intact.
    Automatic reconnect succeeded in segment 2 with the same ownership session.
12. Ran the **additional first post-reconnect INFO exactly once** with the same
    reviewed INFO condition and two-second bound. It returned `E_COMMAND_001`
    and timed out. Further UART actions stopped; no second INFO, manual reacquire,
    reset, blank-line resynchronization or other UART command followed this
    diagnostic failure. The contract audit above corrects its original treatment
    as an acceptance blocker.
13. Completed read-only final `status`, `sessions`, `session <id>`,
    `logs --session <id> --last 100`, `GET /sessions/<id>` and cursor evidence
    retrieval. CLI list/detail/log and API all reported `not_observable`.
    Preserved native evidence/logs, then stopped normally and verified release.

### Durable ranges and ordering

All ranges below are half-open in `20261027T073956Z-7c038da2`:

| Operation ID | Result | Range | TX attempts |
|---|---|---|---:|
| `interact-cb8cbebe-0258-467f-a3e6-3108031de846` | matched initial INFO | `[5,10)` | 1 |
| `monitor-28c57706-2c05-48ad-9af2-f23e42d9760d` | elapsed | `[10,12)` | 0 |
| `monitor-ae6a966f-a4bf-4579-b42d-2c499d1f6cfa` | matched PONG | `[18,23)` | 0 |
| `interact-a66095e4-6125-4aa3-b1cb-839d07783ffe` | matched PONG | `[23,28)` | 1 |
| `interact-afafc13e-f7e0-4546-bbf2-05021c3b8ee7` | elapsed | `[28,32)` | 1 |
| `interact-b72ea554-2d41-4c5e-9afb-d6d5d7211145` | intended timeout | `[32,36)` | 1 |
| `interact-fe0b8daa-3ef1-4bd4-a9b4-97c6b1e57389` | matched unrelated ASYNC | `[39,45)` | 1 |
| `interact-accc4efb-5797-4b5e-a9ae-335f9389e51a` | matched DELAYFAULT ACK | `[45,50)` | 1 |
| `interact-5278f211-f102-4569-a450-c79e5f5acd90` | matched reacquired INFO | `[68,73)` | 1 |
| `interact-f1864e18-1d4a-46b0-b666-de286db8e5ca` | additional INFO: timeout; anomaly retained | `[77,82)` | 1 |

Dedicated delayed fault: ACK RX **48**, durable operation terminal **49**, fault
RX **50**. The fault is outside `[45,50)`; host ACK→fault delta is
**10,040,059 us** (10.040059 s). Sequence order establishes completion before
the later ambient fault independently of elapsed timing. Both intentionally
generated ASYNC ERROR markers remain expected failure-pattern evidence.

Release completed in **0.673635 s**: final PONG RX **62**, intent **63**,
`released` **64** at 07:45:27. Segment 0 closed and gap count became 1. External
ownership/response/6-second hold passed with the service responsive and released.
Reacquire at 07:46:36 persisted start **65**, segment-open **66**, success **67**;
INFO RX **71** confirmed the new segment. No serial owner overlapped the handoff.

Unexpected disconnect/start **73/74** were first observed at **07:48:06.309105**;
USB reappeared at **07:48:08.782975**, node at **07:48:08.791297**, and new
segment/success **75/76** at **07:48:09.447608**. Observed start→success delta:
**3.138501291 s**, inside the unchanged five-second window. Segment 1 closed
as unexpected disconnect; segment 2 has `start_reason=reconnect` and a fresh
host origin. Gap count became 2. Mechanical action markers and host polling
bounds are retained; existing logs do not expose individual failed open attempts.
No external probe competed with automatic reconnect.

### Additional INFO timeout and non-blocking anomaly

At 07:48:42, attempt **78**, ID `8b2c5a03-f79b-4ce2-ab58-39a78a1f3961`,
audited exact `INFO\n` (`494e464f0a`, `SU5GTwo=`). Result **79** records success,
accepted **5** bytes. RX **80** instead preserves exact
`DMF/1 ERROR COMMAND code=E_COMMAND_001\n` in segment 2. Terminal **81**, at
07:48:43, records timeout of the reviewed INFO literal condition. CLI exit 0
describes completion of the bounded operation; the response remains unmatched.
Overall acceptance is determined by the normative mapping above. Only one
attempt/result exists for this operation.

This recurrence caused the added application-response check to fail. The
normative reconnect criterion passed: the
error response itself was captured in the new segment, status stayed responsive,
and the same session remained active. It is **not a demonstrated reconnect
transport defect**. Actual FTDI→Pico wire bytes and Pico parser state were not
captured, so no DUTchMate/adapter/fixture/electrical cause is established.
The historical anomaly remains unresolved, unclassified and non-blocking for
Phase 1A. It is neither diagnosed nor fixed. No retry was used to replace the
failed INFO assertion with a passing response.

### Criterion-by-criterion result

| Current Basic Phase 1A criterion | Result in this fresh run |
|---|---|
| Continuous real ambient RX, physical boot/INFO | Passed; exact reviewed build before bounded workflows |
| Follow live display/detach and continued acquisition | Passed; only service serial owner |
| Duration and literal-condition Monitor | Passed, durable outcomes/ranges |
| Default-disabled / explicitly enabled exact audited TX | Default/denial passed fresh software gate; 16 exact physical audit pairs passed under enabled policy |
| Matched/elapsed/timeout Interact, one TX each | Passed; extra INFO timeout and its RX evidence also preserved truthfully |
| Unrelated asynchronous RX inside Interact | Passed, PONG and ASYNC retained without filtering |
| Delayed fault after durable operation completion | Passed, terminal 49 < fault 50, outside range, 10.040059 s after ACK |
| Service console live RX and continued recording after EOF | Passed, PONG/INFO displayed and later PONG persisted |
| Native-v2 persistence, serial/DTR/RTS/host timestamp provenance | Passed in all three segments; no electrical readback claim |
| Linked size/segment rollover | Fresh deterministic software gate passed; 16 MiB/32-segment physical limits were not forced |
| Real release/external ownership/reacquire | Passed, exact external PARTIAL, 6-second hold, first reacquired INFO matched |
| Explicit observation gaps and fresh segments | Passed, two gaps, segments 0/1/2 with distinct origins |
| Unexpected reconnect / resumed RX | Passed; in-window success, same session, fresh segment 2, durable gap, resumed RX 80 and responsive service |
| Final list/detail/evidence/log retrieval | Passed; saved cursor returned 81 records from 1..81 to tail, plus native initial connected record 0 |
| CLI Basic loss display | Passed, `loss=not_observable`, `Integrity: not_observable`, matching status/API/log warning |
| Additional diagnostic: E_COMMAND_001 watch / no retry | Recurrence at RX 80 remains unresolved/unclassified/non-blocking; no subsequent UART command |
| Complete Phase 1A | **Complete; accepted after normative contract audit** |

### Preservation and shutdown

Native session `.dutchmate/sessions/20261027T073956Z-7c038da2/` and run artifacts
retain all evidence. `acceptance-summary.json`, `45-acceptance-stop.json`,
timing/ownership records, exact command outputs, raw service logs, before/after
copies and full manifests are under the run directory. Final counts:
**781 raw bytes**, **20 RX records**, **16 TX pairs**, **10 terminal operations**,
**3 segments**, **2 gaps**, contiguous sequences **0..81**. Decoded RX reconciles
raw byte-for-byte; exact TX command bytes and external PARTIAL output are absent
from raw RX. TX records reside in native-v2 `operation_events.jsonl`.

| Final artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `88b1362251776ae02879e2d1a643c25d9dd7ccb17c47edcebf44c490aad0b345` |
| `uart_events.jsonl` | `670221eb073157b0523ce5ffc33bf50ac35b5b4fc29da2ab8b5c62bf2ffc680d` |
| `operation_events.jsonl` | `e344440ac6f99a9f7860980e38b8c56caee8fbd450552e206760eb32fbbe3d0f` |
| `connection_events.jsonl` | `87cd3be057876318ca558105f5f59b239b0eef95f1952a90e171f1dd70009070` |
| `metadata.json` | `a337ff5410cbc98250ef2c749dbbf8161b0c08038b6ff28d5170e06cbe5b000c` |

Graceful public CLI stop succeeded without SIGKILL. At **07:50:22.320058 UTC**
(13:20:22 IST), PID 33018 was absent, TCP 2040 had no listener, and both FTDI
cu/tty paths were unowned. Final journal state is `completed/service_shutdown`,
which truthfully records clean service shutdown. The contract audit and evidence
mapping establish Phase 1A acceptance while retaining the unsuccessful extra
INFO check as a non-blocking anomaly. Stage 8, Phase 1B and overall Phase 1 remain
incomplete; Enhanced HIL and MCP work were not started.
All earlier session hashes and configuration bytes are unchanged. Only this
appended report and development status/history changed, left uncommitted for
review. Final documentation diff/preservation checks are recorded in history.


## Instrumented E_COMMAND_001 ingress diagnostic — 2026-10-27

Result: **reproduced on the first reconnect/INFO trial; fixture line-assembler
overflow/discard path confirmed for this recurrence**. The exact discarded
bytes, when they arrived and their origin remain unknown. No DUTchMate product
failure or electrical-wire cause is established. Stopped for review without
retry, reset, resynchronization, further trial or patch.

**Phase 1A remains Complete/accepted** from its existing fresh acceptance record.
This was a small diagnostic, not a full Basic acceptance rerun. Stage 8,
Phase 1B and overall Phase 1 remain incomplete. Enhanced HIL/MCP were not started.
Earlier uninstrumented anomalies remain unclassified; this result does not
retroactively establish their cause or parser state.

### Preflight and fixture provenance

- Clean `stage8-phase1-acceptance` at **69a0980e1c7ced2cfcf053ebdd95e7b8dcc16df4**, independently verified as
  the latest pushed tip by read-only HTTPS `ls-remote`. The fixture diagnostics
  are committed in that revision; no production or fixture code changed here.
- Host: macOS 26.2, build `25C56`, arm64. FTDI FT231X USB UART, `0403:6015`,
  serial `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, USB location `0-1.4`.
  No service PID file, TCP 2040 listener or FTDI owner before startup.
- Operator confirmed the new UF2 externally flashed onto Pico 1/Pico H; unchanged
  GP0/pin 1 → FTDI RX, GP1/pin 2 → FTDI TX, GND/pin 3 → FTDI GND, Pico powered
  by its own USB, FTDI VCC disconnected, 3.3 V logic, GP2/GP3 open, external
  terminals closed. The agent did not flash hardware.
- Build ID **`basic-diag-20261027-d406684c5dff`**, Zephyr `v4.4.0` / SDK `1.0.1`,
  target `rpi_pico/rp2040`; previously built normal Basic image, no overlay.
  UF2: `/Users/nahitpawar/Documents/github/dutchmate/DUTchMate/build/dutchmate-zephyr-dut-basic-diag-d406684c5dff/zephyr/zephyr.uf2`.
  Recomputed SHA-256: **`7eeead1fc216035eb4163aae768bdd22838988caa944d9f4bc5d3628575f43f3`**.
  Committed fixture source inventory matches the built source hash
  `d406684c5dffd4b505c2d683198719913d4d4b4c630be44037539e865bc6c92b`.
  The initial physical INFO independently confirmed the exact new build ID.
- Configuration unchanged: 115200 8-N-1, `rtscts=false`, `xonxoff=false`, TX
  explicitly enabled, default ending `none`, driver-default DTR/RTS,
  `reconnect_timeout_s=5.0`, exact-path selector, 16 MiB session budget,
  retention disabled. Raw config SHA-256 `55811eeb2385961b43e8d9bb05221aa461991ee93415f823616e24024ecd75ba`;
  resolved profile digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
- All software checks completed before physical startup: **1,527 tests passed
  in 39.73 s**, including fixture and architecture tests; Ruff passed; mypy
  passed (103 source files); offline lock check passed (66 packages);
  `git diff --check` passed. Exact commands used
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`.
  No pytest, second runtime/session store or production/fixture patch occurred
  while the physical service was live.

### Minimal actions and exact evidence

Fresh native-v2 session **`20261027T100353Z-1d5cd35f`**, service PID **41181**.
Normal start/stop used the existing CLI contract:

```text
uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200
uv run --frozen --package dutchmate dutchmate stop
```

Exactly two separate bounded `POST /dut/interact` requests were made through
HTTP-only diagnostic code, with this body each time:

```json
{"text":"INFO","line_ending":"lf","conditions":[{"pattern":"DMF/1 INFO board=rpi_pico build=basic-diag-20261027-d406684c5dff protocol=1"}],"timeout_s":2.0}
```

Neither request retries TX. No command, blank line or fixture reset was inserted
before the first INFO or between reconnection and its INFO. The observer/helper
accesses HTTP, existing evidence files and port-node presence; it never opens
serial or constructs a DUTchMate runtime/store. Only the service owns FTDI.
The trial cap was five, but execution stopped after **one reconnect trial**.

All times below are UTC on October 27 (Asia/Kolkata = UTC+05:30).

| Event | Time / native evidence |
|---|---|
| Start CLI invoked / returned | `10:03:53.632431` / `10:03:54.132794` |
| Initial INFO request / HTTP return | `10:04:10.069639` / `10:04:11.067234`; matched, operation `interact-4d0306cc-36f7-467d-b8dd-522f78458771`, range `[1,6)` |
| Initial exact TX / response | Attempt/result **2/3**, accepted 5 bytes; RX **4**, exact new-build INFO; terminal **5**, matched |
| Ambient host RX | RX **6**, `10:14:00Z`, one byte `00`, outside any bounded operation |
| Operator unplug marker | `10:14:46.251607`; marker just before the physical action |
| Unexpected disconnect / reconnect start | **7/8**, native `10:14:46Z`; first observer sample `10:14:46.989389` |
| Operator replug marker | `10:14:49.380900`; marker immediately after action |
| Fresh segment / reconnect success | **9/10**, segment **1**, native `10:14:50Z`; first observer sample `10:14:50.138189` |
| Post-reconnect INFO request / return | `10:14:50.156391` / `10:14:52.171828`; operation `interact-787a3fea-0c73-4516-a7b2-a46b40ff928f`, range `[11,16)` |
| Exact TX / diagnostic / terminal | Attempt/result **12/13**, RX **14**, timeout terminal **15** |

Observer start-to-success delta was **3.148789542 s**. These are poll observations,
not exact open-syscall timestamps; native event wall times have one-second
resolution. The service's successful reconnect before its unchanged deadline is
recorded durably. Same ownership session, fresh segment 1 with source origin
`14584858017 us`, closed prior segment (`unexpected_disconnect`), and one durable
observation gap are in metadata. The INFO request began **66.807625 ms** after
that new source origin. Service remained connected/responsive with no active
operation after the timeout; RX 14 is resumed acquisition in the fresh segment.

Both attempts audited exactly `INFO\n`, hex **`494e464f0a`**, base64 `SU5GTwo=`,
byte length 5. Both results record `status=success`, **5 accepted bytes**.
Attempt IDs are `116eb5d0-421f-4651-b71a-1ef315effd97` (initial) and
`a981ceb6-f2ec-46c2-9b3b-8bf1e3cd6436` (post-reconnect). No further INFO or other
UART TX followed the failure. The complete RX 14 response, including empty hex
value and terminating LF, is:

```text
DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=1\n
```

### Interpretation and limits

The new diagnostic establishes that the assembler was in its overlong/discard
state when LF dispatched this command. Under the unchanged fixture semantics,
the 33rd non-CR/non-LF byte clears the accumulated command and discards through
LF; the handler therefore received **zero bytes**, not exact `INFO` or a measured
`XINFO`/NUL-prefixed command. Empty `command_hex` is truthful handler input,
**not evidence that the ingress line was empty**. Discarded bytes were not saved.
The capture does not establish when those bytes arrived, their values or source.
This is not a reproduction of exact `INFO` reaching the handler and being rejected.

The host audit establishes requested/accepted TX, not electrical FTDI TX → Pico
RX bytes. Likewise, ambient RX 6 (`00`) is in the **Pico TX → FTDI RX → host RX**
direction; it must not be interpreted as a measured NUL in command ingress or
as an explanation for overflow. No electrical waveform was captured. The
fixture response narrows this recurrence to the discard path while the cause
remains unresolved/unclassified across host/adapter/electrical/firmware ingress.
No remediation or exoneration of any layer is claimed.

### Preservation and cleanup

Artifacts: **`.dutchmate/hil/basic-ingress-diagnostic-20261027/`** contains the
clean baseline and prior-session hashes; full pre-start software logs; UF2 and
actual INFO provenance; exact request/result and audit observations; operator
markers; passive reconnect samples/result; stop reason and bounded trial count;
read-only final status/session detail and tail-cursor snapshot; service log,
final native copy and manifest, diagnostic summary and cleanup verification.
The tail snapshot was requested without an input cursor and correctly returned
no historical records; historical evidence is preserved in native files below.

Native session `.dutchmate/sessions/20261027T100353Z-1d5cd35f/` ends normally as
`completed/service_shutdown`, with **153 raw bytes**, **3 RX records**,
**2 TX pairs**, **2 terminal operations**, **2 segments**, **1 gap**, contiguous
sequences **0..15**. Decoded RX reconciles byte-for-byte to `uart_raw.log`.
No unresolved action or active operation remains. This journal outcome is not
an INFO match or a diagnosis of the anomaly.

| Final native artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `a6598a256607dbf1ba3ca0ca8462512994db409942e03353d90602166c124ecd` |
| `uart_events.jsonl` | `b2a52bf29bc70d69dffd45f9d5a418a2bbe8aa60fd7523bb3cb9a4686b8cb9b4` |
| `operation_events.jsonl` | `e3851160a4f4a5cd8c1210621132decad7007ad4b2c8fd118ce40eb512079b40` |
| `connection_events.jsonl` | `1814735e7dcd6e97a2fcd59c9f783c74467592b998fcf7b995f0c4a6c572d6e0` |
| `metadata.json` | `2d6cf751e19d13a3f6ca29fc85078a74ffea4d98ffb03157e908258bd245b42c` |

Graceful public CLI stop returned at **10:15:35.223675 UTC**. At
**10:15:52.109926 UTC** (15:45:52 IST), PID 41181 and its PID file were absent,
TCP 2040 had no listener, and both FTDI cu/tty paths were unowned. No SIGKILL or
external same-port consumer was used. All **434 pre-existing session-file hashes**
and configuration bytes are unchanged. Only this appended diagnostic record,
development status and a new history entry changed, uncommitted for review.
`git diff --check` passed. Phase 1A remains accepted; no further physical run,
Enhanced HIL or MCP work was started.


## Bounded overflow diagnostic preparation — 2026-10-27 (software only)

Prepared on clean latest-pushed `stage8-phase1-acceptance`, source base
`68ae39714fb5ebfd55ec970e2709d29561c822e9`, independently verified by read-only HTTPS `ls-remote`.
This adds bounded fixture observations for the previously recorded discard-path
recurrence. **No new physical reproduction, serial open, service startup or
flash occurred.** The user's explicit review/commit/push gate precedes hardware;
implementation and documentation remain uncommitted for review. There is no new
physical session ID or response to report. Existing physical evidence above,
including `20261027T100353Z-1d5cd35f`, is unchanged.

### Instrumentation semantics and limits

Unknown overlong lines preserve the existing
`command_len=0 command_hex= discard=1` fields on a single LF-terminated DMF response.
Overflow-only additions are `line_len`, `prefix_hex`, `overflow_byte`,
`discarded_count`, and `suffix_hex`; exact formats/examples are in the
[fixture README](../firmware/zephyr_dut/README.md#unknown-command-byte-diagnostics).

- `line_len` counts every non-CR/non-LF byte assembled or discarded.
- `prefix_hex` is the exact first 32 relevant bytes, preserved in the existing
  command buffer; `overflow_byte` is the first byte beyond its capacity.
- `discarded_count = line_len - 32`, including the first overflow byte.
- `suffix_hex` contains the last up to eight discarded bytes in arrival order.
  It does not claim to expose the uncaptured middle of a longer overrun.
- Added state is exactly **16 bytes** on the ARM target: fixed 32-bit count,
  overflow byte, eight-byte suffix, suffix length and count-overflow flag. No
  allocation or extra prefix buffer. Beyond `4294967295` relevant bytes, counts
  are omitted and `counts_overflow=1` is emitted; values never wrap or approximate.
- CR/LF/NUL handling, idle prefix retention, discard-through-LF and valid command
  semantics are unchanged. LF resets the diagnostic state. Successful command
  output and non-overflow error responses remain byte-for-byte unchanged.

This captures firmware/UART-processing observations, **not the electrical
FTDI TX → Pico RX waveform**, and cannot recover bytes lost before polling or
the uncaptured middle of an overrun. The earlier discard-path result is not a
root-cause diagnosis; no new cause is assigned and no remediation was attempted.
**Phase 1A remains Complete/accepted**. Stage 8, Phase 1B and overall Phase 1
remain incomplete; Enhanced HIL and MCP were not started.

### Software and cross-build evidence

TDD: before implementation, **7 tests failed / 29 passed** because overflow
fields were absent, with both host C harnesses compiling. After implementation,
**36 focused tests passed in 9.73 s**. Coverage includes exact 32 bytes, first
33rd byte with binary prefix, longer varied overrun, NUL/`ff`, ignored CRs,
LF/state reset, next valid command, existing non-overflow errors, no successful
command diagnostics, a 100,000-byte line with bounded output, and seeded counter
exhaustion using the actual firmware count helper. No test-only hook was added
to firmware.

Full gate: **1,533 pytest tests passed in 43.29 s** (including architecture), Ruff
passed, mypy passed (103 source files), offline lock check passed (66 packages),
and `git diff --check` passed. Focused command:
`rtk proxy .venv/bin/python -m pytest tests/hardware/zephyr_dut/test_fixture_protocol.py -q --tb=short`.
Full commands used `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache`
followed by `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
`uv run --frozen mypy`, and `uv lock --check --offline`.

Cross-build used unchanged default Basic configuration, Zephyr `v4.4.0` / SDK
`1.0.1`, GNU `14.3.0`, west `1.3.0`. The review image is uniquely identified:

| Review-build field | Value |
|---|---|
| Build ID | `basic-ovf-20261027-3cbe8d2ee291` |
| Board | `rpi_pico/rp2040` |
| UART | 115200 8-N-1, no flow control, no overlay |
| UF2 | `build/dutchmate-zephyr-dut-basic-ovf-3cbe8d2ee291/zephyr/zephyr.uf2` (36,352 bytes) |
| UF2 SHA-256 | `c1f0067c910ccf8ae0108eed5362da957dc50e4a9a801a4afce69c0ce4407409` |
| `.config` SHA-256 | `8a4649450bb737da6289b6e358001626712f61db44c499220ef88bfeb547ceec` |
| Fixture source inventory SHA-256 | `3cbe8d2ee291b49c8185d6f1ff45996e371d82d63f3c142a57e94fe830e712b1` |

The source hash uses sorted relative fixture paths/NUL/content/NUL, excluding
README, as in earlier builds. Generated board/UART settings and empty overlay
settings were checked; the binary contains the new diagnostic fields and exact
build ID. UF2 magic/block indices/address layout were validated and decoded
payload matches `zephyr.bin`. A separate ARM compilation asserts the new
observation struct occupies 16 bytes. The UF2 has **not** been flashed and has
no physical validation yet; a host cross-build does not establish on-device RX.
All 996 existing `.dutchmate` file hashes and all
14 earlier UF2 hashes remain unchanged.


## Bounded overflow physical diagnostic — 2026-10-27

Result: **reproduced on reconnect trial 1; stopped immediately without retry**.
The fixture reports 90 relevant bytes, a first-32-byte NUL/`ff` prefix, first
excess byte `00`, 58 discarded bytes and a suffix ending in `INFO`. This is
firmware line-assembly evidence; **no electrical waveform or root cause is
established**. No code, firmware, parser state, UART configuration, reconnect
policy or acceptance criterion was changed during the run.

**Phase 1A remains Complete/accepted** from the existing acceptance session.
This was not a full Basic acceptance rerun. Stage 8, Phase 1B and overall Phase 1
remain incomplete; Enhanced HIL and MCP were not started. Older diagnostic and
acceptance records remain unchanged and are not retroactively assigned a cause.

### Preflight and provenance

- Clean `stage8-phase1-acceptance`, exact HEAD **`4692444f771f33b6d27994e03f2722c268e3f43a`**.
  Initial HTTPS remote lookup still showed `68ae397`; physical startup waited
  for the operator's push. A second independent lookup confirmed the exact
  tested HEAD above was pushed before any serial open. No branch/code change
  occurred between the software gate and physical startup.
- Host macOS 26.2 build `25C56`, arm64. FTDI FT231X `0403:6015`, serial
  `D358SG6A`, `/dev/cu.usbserial-D358SG6A`, location `0-1.4`. No listener,
  service PID file or FTDI cu/tty owner before startup; checked again immediately
  before starting. Passive USB matching used the same VID/PID/serial.
- User confirmed the reviewed image already externally flashed on Pico 1/Pico H:
  **`basic-ovf-20261027-3cbe8d2ee291`**, UF2 SHA-256 independently recomputed as
  **`c1f0067c910ccf8ae0108eed5362da957dc50e4a9a801a4afce69c0ce4407409`** from `/Users/nahitpawar/Documents/github/dutchmate/DUTchMate/build/dutchmate-zephyr-dut-basic-ovf-3cbe8d2ee291/zephyr/zephyr.uf2`.
  Fixture source inventory SHA-256 `3cbe8d2ee291b49c8185d6f1ff45996e371d82d63f3c142a57e94fe830e712b1` matches the
  committed source. This is the previously reviewed Zephyr 4.4.0 / SDK 1.0.1
  Basic build; no rebuild or agent flashing occurred here. Actual initial INFO
  confirmed the complete expected build literal before any reconnect.
- Existing wiring/power arrangement retained: GP0/pin 1 → FTDI RX,
  GP1/pin 2 → FTDI TX, GND/pin 3 → FTDI GND, Pico powered by its own USB,
  FTDI VCC disconnected, 3.3 V logic, GP2/GP3 open. Only FTDI USB was unplugged;
  no Pico reset, parser resynchronization or external serial consumer was used.
- Raw configuration unchanged, SHA-256 `55811eeb2385961b43e8d9bb05221aa461991ee93415f823616e24024ecd75ba`; resolved profile
  digest `42326da48a5c72bae4ea6c6165a45718cf64dd6b21f8378ec32933ae08f6d837`.
  Effective Basic profile: exact-path/external UART, 115200 8-N-1,
  `rtscts=false`, `xonxoff=false`, explicit TX enabled, default ending `none`,
  driver-default DTR/RTS, **`reconnect_timeout_s=5.0`**, 16 MiB budget,
  retention disabled. Initial/final service snapshots and native metadata agree.
- Pre-start software gate: **1,533 pytest tests passed in 42.52 s**, including
  fixture/architecture checks; Ruff passed; mypy passed (103 source files);
  offline lock check passed (66 packages); `git diff --check` passed. All tests
  finished at **16:20:25.507066 IST**, before CLI startup at
  **16:22:45.444537 IST**. Commands used
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache` followed by
  `uv run --frozen pytest -q --tb=short`, `uv run --frozen ruff check .`,
  `uv run --frozen mypy`, and `uv lock --check --offline`. Current CLI start/
  Interact help was captured. No pytest or additional runtime/session store
  ran while the physical service was live.

### Exactly one reconnect/INFO trial

Fresh native-v2 session **`20261027T105245Z-a78a6741`**, service PID **44442**.
Normal CLI lifecycle commands:

```text
uv run --frozen --package dutchmate dutchmate start --backend basic --serial-port /dev/cu.usbserial-D358SG6A --baudrate 115200
uv run --frozen --package dutchmate dutchmate stop
```

Exactly **two** bounded HTTP `POST /dut/interact` requests were made: one initial
INFO, required to match, and one INFO following automatic reconnect. Each body:

```json
{"text":"INFO","line_ending":"lf","conditions":[{"pattern":"DMF/1 INFO board=rpi_pico build=basic-ovf-20261027-3cbe8d2ee291 protocol=1"}],"timeout_s":2.0}
```

Each request has exactly one TX attempt/result pair for hex **`494e464f0a`**,
base64 `SU5GTwo=`, byte length **5**, result `status=success`, accepted bytes **5**.
No other UART command, blank line, reset, manual reacquire or parser alteration
was performed. Existing passive USB/node/status/native-connection observers were
armed before the helper prompted unplug. They neither opened serial nor created
another DUTchMate runtime/store. No external open probe competed with reconnect.
All observer threads stopped after the result. The maximum was three reconnect
trials; **only trial 1 was performed** because it reproduced the diagnostic.

Times below are **IST (UTC+05:30), October 27**. Artifacts also preserve UTC and
host-monotonic timestamps. Operator markers bound human actions, not exact
physical/electrical transitions; observer sample start/end times are retained.

| Event | IST time / evidence |
|---|---|
| Initial INFO request / return | `16:22:50.459017` / `16:22:50.807980`; matched |
| Initial TX / response / terminal | Attempt/result **2/3**, RX **4**, matched terminal **5**, range `[1,6)` |
| Operator unplug-imminent marker | `16:27:15.009147` |
| Unexpected disconnect / reconnect start | **6/7**, native `10:57:15Z`; first observed `16:27:15.798268` |
| Serial node again observed | `16:27:17.824305` |
| USB identity again observed | `16:27:17.842911` (sample began `16:27:17.805580`) |
| Operator replug-completed marker | `16:27:18.053180` |
| Fresh segment / reconnect success | **8/9**, segment **1**, native `10:57:18Z`; first observed `16:27:18.922512` |
| Post-reconnect INFO request / return | `16:27:19.023046` / `16:27:21.028144` |
| Exact TX / response / terminal | Attempt/result **11/12**, RX **13**, timeout terminal **14**, range `[10,15)` |

The same ownership session continued across the durable observation gap into
fresh segment 1. The old segment ended as `unexpected_disconnect`. New segment
host-monotonic source origin is `17133673000 us`; the request began
**112.610083 ms** later. First-observed reconnect-start → success delta was
**3.124234834 s**, within the unchanged 5.0 s policy. These are polling
observations, not exact open-syscall times. RX 13 proves resumed acquisition;
service remained connected/responsive with no active operations afterward.

Initial operation: `interact-e13759b8-c6f8-47fb-bf6f-493916c3fea0`, attempt
`a1fcb04c-04a4-4b5d-95c9-cc1075c36593`. Post-reconnect operation:
`interact-50ec32a1-b647-4188-8b8e-897d2f0feb98`, attempt
`4b105c6c-f5f0-47bc-9ad8-86def134ec1c`. The later Interact truthfully timed out
because the requested INFO literal did not match. It was not retried.

### Complete fixture diagnostic and explicit decode

Exact RX 13, with the terminating LF represented by `\n`:

```text
DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=1 line_len=90 prefix_hex=0000000000000000000000000000ff0000000000000000ff000000ff00000000 overflow_byte=00 discarded_count=58 suffix_hex=000000ff494e464f\n
```

| Field | Observed value / meaning |
|---|---|
| `command_len` / `command_hex` / `discard` | `0` / empty / `1`; handler received zero command bytes from the discard path |
| `line_len` | **90** non-CR/non-LF bytes observed by the assembler |
| `prefix_hex` | `0000000000000000000000000000ff0000000000000000ff000000ff00000000`; all 32 bytes decoded below |
| `overflow_byte` | **`00`**, the first relevant byte beyond capacity (position 33) |
| `discarded_count` | **58**, including that first excess byte |
| `suffix_hex` | **`000000ff494e464f`** = `00 00 00 ff 49 4e 46 4f` |
| Suffix ends in `494e464f` (`INFO`) | **Yes** |
| `counts_overflow` | **Absent**; no count-overflow flag was reported |

All 32 prefix bytes, in order (positions 1–16, then 17–32):

```text
00 00 00 00 00 00 00 00 00 00 00 00 00 00 ff 00
00 00 00 00 00 00 00 ff 00 00 00 ff 00 00 00 00
```

That prefix contains **29 `00` bytes** and **three `ff` bytes**. The `ff` bytes
are at one-based positions **15, 24 and 28**; all other prefix positions are `00`.
This reports the observed pattern exactly, without assigning its source.

Because the eight-byte suffix ends in `INFO`, the explicit INFO bytes reached
the firmware assembler while it was already processing an **overlong line**;
they were discarded with that line rather than passed alone to the command
handler. This is not exact `INFO` reaching the handler and being rejected.
The bytes at relevant positions **34–82 were not captured**. Their values must
not be filled in from the observed prefix/suffix. `line_len` excludes ignored
CR and terminating LF and does not establish a raw electrical byte count.

This instrumentation observes what the Pico firmware delivered to its UART
line-assembly path, **not the FTDI TX → Pico RX electrical waveform**. Host TX
requested/accepted bytes likewise do not establish the waveform. The source of
the extra bytes and their exact arrival times remain unknown. No root cause is
assigned to DUTchMate, FTDI, wiring, RP2040 UART, Zephyr or the fixture. No patch,
workaround or remediation was attempted during the run.

### Preservation and cleanup

Artifacts under **`.dutchmate/hil/basic-overflow-physical-20261027/`** include
preflight/remote verification, UF2/source/config hashes, pre-start software logs,
CLI help, exact request/result and TX audits, initial matched build identity,
operator markers, passive USB/node/status/connection samples, trial result,
complete diagnostic decode/stop reason, final status/session detail, durable
cursor retrieval, service log, final native copy, hash manifest and cleanup.
Saved-cursor retrieval returned **nine records, 6..14**, including reconnect,
post-reconnect TX, full response and terminal, without omission. Initial records
0..5 are preserved in the same native session. No historical session was reused.

Final native state **`completed/service_shutdown`**: **303 raw RX bytes**,
**2 RX records**, **2 TX pairs**, **2 terminal operations**, **2 segments**,
**1 observation gap**, contiguous evidence **0..14**. Decoded RX exactly matches
raw bytes. There was no other host RX in this fresh session; that does not
establish absence of earlier Pico ingress. Basic loss remains `not_observable`.

| Native artifact | SHA-256 |
|---|---|
| `uart_raw.log` | `4c908fc39eaedd8e6a008546d04de3bc27a00dd32d3a6fdf78ddf0f9ec05c948` |
| `uart_events.jsonl` | `4a734c184a5954d4d88e63ea759e065ea9fdbab950921a61a7c9b5a036cfe0e9` |
| `operation_events.jsonl` | `8c5e5a83baecbc58d05a98c7a3393e4a38cb9ef8a8167f7c0e8c8e547862e389` |
| `connection_events.jsonl` | `72f62a1f123548d420d39805ead6c54126b1627746b6ed24ed2e21ffd4df3f70` |
| `metadata.json` | `209289681794d37f1335a9a596f636c4901e5c64f174cd679060c2f82f9aaa29` |

Graceful CLI stop returned **16:27:52.676969 IST**. At
**16:27:54.550083 IST** (`2026-10-27T10:57:54.550083+00:00`), PID 44442 and its PID file
were absent, TCP 2040 had no listener and both FTDI cu/tty paths were unowned.
No SIGKILL, hardware flash or external serial consumer was used. All **441
prior session-file hashes** and configuration bytes are unchanged. Only this
appended Basic diagnostic record, current status and a new history entry changed;
changes are uncommitted for review and `git diff --check` passed. Phase 1A remains
accepted; no full Basic acceptance, Enhanced HIL or MCP work was started.
