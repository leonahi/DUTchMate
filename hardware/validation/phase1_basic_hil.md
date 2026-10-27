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
