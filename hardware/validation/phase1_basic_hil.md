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
uv run --package dutchmate-cli python -m serial.tools.list_ports -v
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
uv run --package dutchmate-cli dutchmate start
uv run --package dutchmate-cli dutchmate status
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
   uv run --package dutchmate-cli dutchmate capture --seconds 15
   ```

3. Within the first three seconds, briefly connect Pico RUN to GND and release
   it. Do not change the mode straps while the board is running.
4. Record the session ID printed when capture completes as `BOOT_SESSION`.
5. Retrieve its evidence:

   ```bash
   uv run --package dutchmate-cli dutchmate logs --session <BOOT_SESSION> --last 20
   uv run --package dutchmate-cli dutchmate session <BOOT_SESSION>
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
   uv run --package dutchmate-cli dutchmate capture --seconds 15
   ```

2. While it is active, run both commands in terminal B:

   ```bash
   uv run --package dutchmate-cli dutchmate send PING --force
   uv run --package dutchmate-cli dutchmate send INFO --force
   ```

3. Each send must print an attempt ID and `Perturbation logged: yes`.
4. Record the session ID printed by terminal A as `COMMAND_SESSION`.
5. Retrieve its evidence:

   ```bash
   uv run --package dutchmate-cli dutchmate logs --session <COMMAND_SESSION> --last 20
   uv run --package dutchmate-cli dutchmate session <COMMAND_SESSION>
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
uv run --package dutchmate-cli dutchmate stop
```

## Objective acceptance checklist

Mark the run passed only when every required assertion is supported by the
recorded session IDs.

- [ ] Adapter identity, selected port, and 115200 8-N-1 settings recorded.
- [ ] DUTchMate commit and dirty/clean state recorded.
- [ ] Zephyr revision, SDK, board, fixture build ID, `.config` digest, UF2
  digest, flash method, and strap state recorded.
- [ ] Basic status reports the intended connection and capabilities.
- [ ] Manual-reset capture contains the exact successful-boot protocol bytes.
- [ ] Boot session is completed, untruncated, and has no first error.
- [ ] Both UART sends have durable attempt/result evidence and accept 5 bytes.
- [ ] Command capture contains the exact `PONG` and `INFO` responses.
- [ ] Both sessions preserve non-empty raw bytes and normalized UART events.
- [ ] Session detail and recent-log retrieval reproduce the stored evidence.
- [ ] Both sessions report Basic integrity as `not_observable`.
- [ ] No assertion depends on Zephyr console or log prefixes.

Any failed or unverified item makes the run `failed` or `incomplete`, not
accepted. Preserve the session directories and describe the failure without
rewriting observed evidence.

## Baseline acceptance report template

Fill this section for the Phase 1A baseline run. For a later rerun, append a
dated copy so the accepted baseline and its replacement remain auditable.

### Run identity

- Result: `pending | passed | failed | incomplete`
- Run date/time and timezone: `<value>`
- Operator: `<value>`
- DUTchMate commit: `<40-character SHA>`
- DUTchMate working tree: `clean | dirty (describe)`

### DUT fixture provenance

- Board: `Raspberry Pi Pico 1 | Pico H`
- Zephyr board target: `rpi_pico`
- Zephyr version/tag: `<value>`
- Zephyr source commit: `<40-character SHA>`
- Zephyr SDK: `<value>`
- Fixture build ID: `<value>`
- Generated `.config` SHA-256: `<value>`
- UF2 SHA-256: `<value>`
- Flash method: `<value>`
- GP3/GP2 strap state: `00`

### Adapter and wiring

- Adapter manufacturer/model: `<value>`
- USB VID/PID: `<value>`
- Adapter serial number: `<value or unavailable>`
- DUTchMate serial port: `<value>`
- UART: `115200 8-N-1, no flow control`
- Wiring checked: `GP0->RX, GP1->TX, GND->GND, adapter VCC disconnected`

### Session evidence

| Scenario | Session ID | Raw bytes | UART records | Hardware records | Result |
|---|---|---:|---:|---:|---|
| Manual-reset boot capture | `<BOOT_SESSION>` | `<count>` | `<count>` | `<count>` | `<result>` |
| PING/INFO command capture | `<COMMAND_SESSION>` | `<count>` | `<count>` | `<count>` | `<result>` |

### Observed results

- Status connection/capabilities: `<observed result>`
- Boot protocol bytes: `<observed result>`
- PING response: `<observed result>`
- INFO response/build provenance: `<observed result>`
- UART send attempts/results: `<observed result>`
- Storage and retrieval: `<observed result>`
- Session state/truncation/first error: `<observed result>`
- Integrity: `<observed result>`
- Deviations or failures: `<none or description>`

### Decision

- Checklist: `<all passed | list failed/unverified items>`
- Phase 1A Basic HIL decision: `accepted | not accepted`
- Decision rationale: `<evidence-based summary>`
