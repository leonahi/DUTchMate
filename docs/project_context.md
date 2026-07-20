# Project Context: DUTchMate

> Status: revised draft — redundancy removed, hardware/software decisions documented
> Purpose: durable project context for AI coding agents, human contributors, and future design iterations.

---

## 1. Overview

DUTchMate is an **AI-assisted embedded debugging system**. A small hardware Debug Helper captures real hardware evidence from a Device Under Test (DUT) and exposes it to AI coding agents through a structured interface (MCP). The LLM runs on the host or cloud — not on the embedded device.

**Project name:** DUTchMate (DUT = Device Under Test, Mate = companion). Use **DUTchMate** in documentation, repository naming, and user-facing descriptions. Generic subsystem names (Device Core, Debug Helper, MCP Server) are acceptable for individual components.

**CLI command:** `dutchmate` (primary), `dm` (optional short alias).

**Core problem:** Embedded debugging is fragmented across disconnected tools — UART terminal, reset button, flash tool, power supply, oscilloscope, developer notes, AI assistant. AI coding agents can read and edit source code but have no structured access to real hardware behavior: boot logs, reset timing, GPIO transitions, power events. They rely on the developer manually copying evidence into the chat. DUTchMate bridges that gap by giving AI coding agents controlled, structured access to real DUT evidence.

**Target workflow:**
1. Build firmware.
2. Flash DUT. *(external tool — out of scope)*
3. Reset DUT.
4. Capture UART logs and hardware events.
5. Analyze failures.
6. Modify code.
7. Repeat.

### 1.1 Prerequisites & Setup

**Supported platforms:** Linux (primary), macOS (supported), Windows (planned — not yet supported due to background process management differences).

**Requirements:**
- Python 3.10+
- RP2040-based board with DUTchMate firmware flashed *(see `hardware/firmware/` — use `picotool` or `west flash` to flash)*

**Install:**
```bash
pip install dutchmate
```

**First run:**
```bash
dutchmate start                        # auto-detects DUTchMate device by USB VID/PID
dutchmate start --port /dev/ttyACM0   # or specify port explicitly if auto-detect is ambiguous
dutchmate status                       # verify device is connected
dutchmate gpio-mode reset open_drain   # required before first reset; use hardware.control.reset config to persist
dutchmate boot-test --seconds 15       # run first boot test
```

**Optional config** — create `.dutchmate/config.toml` in your firmware project root to override defaults (port, session limits, pattern keywords). See §7 for the full config reference. Add `.dutchmate/` to your project's `.gitignore`.

**MCP registration** — to expose DUTchMate tools to an AI coding agent (Claude Code, Cursor, etc.), register the DUTchMate MCP Server command `dutchmate mcp` in the agent's MCP configuration. The MCP Server uses stdio transport by default and calls the Device Core Service at `http://localhost:2040`, which must be running first. Refer to your agent's documentation for the exact MCP registration steps.

---

## 2. Architecture

### 2.1 Layer Model

```
Coding Agent / IDE Agent
        ↓ MCP stdio (default)
Host: MCP Server ──┐
                   │ HTTP (Device Core Service API)
Host: CLI ─────────┤
                   ↓
Host: Device Core Service (FastAPI, persistent — single process holding the serial port)
  └─ Device Core library (hardware interface — no knowledge of MCP or HTTP)
        ↓ USB CDC/serial
Debug Helper Hardware (RP2040)
        ↓ UART / GPIO / reset / BOOT
Device Under Test
```

**Separation of concerns:**
- **Device Core library** — pure hardware interface. Knows nothing about MCP, HTTP, or AI. Runs inside the Device Core Service process.
- **Device Core Service** — persistent FastAPI process that owns the serial port and exposes a REST API. No MCP knowledge.
- **MCP Server** — thin adapter. Receives MCP tool calls from the AI agent, translates them to Device Core Service API calls. No hardware knowledge.
- **CLI** — thin client. Calls the Device Core Service API directly. No MCP involvement.

Both the MCP Server and CLI are independent clients of the Device Core Service API — neither is in the other's call chain.

### 2.2 Host-Side Folder Structure

```
apps/
  cli/           Human-facing command-line interface
  mcp_server/    MCP interface for coding agents
  service/       Device Core Service — long-running process holding the serial port; exposes REST API consumed by CLI and MCP Server

core/
  device_connection/   Transport and protocol handling
  uart_capture/        UART event ingestion and timestamping
  gpio_config/         Debug Helper GPIO mode configuration workflow/state
  session_store/       Persistent debug sessions
  log_processing/      Pattern detection and log extraction
  workflows/           Capture recording, guarded reset/boot actions, later boot test/reset-capture flows

ai/
  debug_reporter/      Optional LLM-based summary and classification
  prompt_templates/    Prompts for log diagnosis and report generation
  context_pack/        Structured context sent to LLM

hardware/
  firmware/     Debug helper firmware
  schematics/   Debug helper hardware design files
  protocol/     Host-device protocol definition
```

The core must remain usable without the AI layer.

Phase 1 implementation details are tracked in `docs/phase1_implementation_spec.md`. That document is the buildable contract for the RP2040 Debug Helper MVP and takes precedence over broad roadmap language when deciding Phase 1 task order.

---

## 3. System Roles

### 3.1 Debug Helper Hardware

Small embedded board physically connected to the DUT.

**Responsibilities:**
- Receive and timestamp UART data from the DUT using the RP2040 64-bit hardware TIMER (1µs resolution, within-session relative timestamps)
- Buffer recent UART data in a ring buffer
- Control DUT reset line and BOOT/control pins via voltage translator
- Optionally capture GPIO events (Phase 5)
- Optionally measure voltage/current (Phase 5)
- Expose a deterministic host protocol over USB CDC/serial

**Not responsible for:** LLM reasoning, source-code analysis, autonomous hardware actions, cloud dependency.

**Initial hardware:** RP2040-based board (Raspberry Pi Pico or equivalent)

**Rationale:** clean USB device support, native PIO for future headroom (custom UART capture, GPIO edge capture), sufficient GPIOs for UART/reset/BOOT wiring, low cost, suitable for Zephyr firmware development.

**Future alternatives:** ESP32-S3 (Wi-Fi/BLE, PSRAM, display), STM32 (industrial design).

---

### 3.2 Device Core

Host-side deterministic library that communicates with the Debug Helper. Runs inside the Device Core Service process — not a separate service. Has no knowledge of MCP, HTTP, or AI.

**Responsibilities:**
- Manage the serial/USB connection to the Debug Helper
- Decode the host-device protocol
- Collect and store UART events and session data
- Perform reset/capture workflows
- Detect configurable keyword patterns (defaults: `ERROR`, `ASSERT`, `PANIC`, `HardFault`, `BOOT_OK`; overridable in `.dutchmate/config.toml` under `[patterns]`) on decoded text — never on raw bytes; UART bytes must be buffered into complete lines before matching so that patterns split across USB packet boundaries are never missed
- Expose a clean internal API
- Decode base64 UART payloads; produce lossy UTF-8 view (with replacement characters) for display and pattern matching

**Must not** depend on MCP or any AI/LLM framework.

**Example internal API:**
```python
reset_dut(pulse_ms: int = 100) -> ResetResult
capture_uart(duration_s: float) -> CaptureResult
get_recent_logs(lines: int = 300) -> list[LogLine]
wait_for_pattern(pattern: str, timeout_s: float) -> PatternResult
run_boot_test(duration_s: float) -> BootTestResult
configure_control_role(role: str, channel: str, mode: Literal["open_drain", "push_pull"], dut_signal: str) -> None
send_uart_command(cmd: str, force: bool = False) -> SendResult
```

---

### 3.3 MCP Server

Thin adapter layer that exposes selected Device Core capabilities to AI agents.

**Responsibilities:**
- Expose high-level debug tools through MCP
- Validate all arguments
- Hide low-level protocol details
- Return structured, compact results
- Never expose raw GPIO control as a default tool

**Deployment:** The MCP Server is a separate process launched by the AI agent. Phase 2 uses MCP stdio transport by default via `dutchmate mcp`. The MCP Server is a thin adapter: it receives MCP tool calls from the AI agent and forwards them as HTTP requests to the Device Core Service API (default: `http://localhost:2040`, configurable in `.dutchmate/config.toml`). The Device Core Service must be running before the MCP Server can function. Optional Streamable HTTP MCP hosting can be added later at a local `/mcp` endpoint, but the deprecated HTTP+SSE MCP transport is not the default.

MCP transport and tool behavior are defined in `docs/mcp_integration_plan.md`. MCP tools are listed in §6.6.

---

### 3.4 Debug Agent (optional)

Optional AI-assisted layer on top of the Device Core. Uses an LLM to classify logs, summarize failures, and suggest next debug steps. Does not have source-code context unless explicitly provided.

**Responsibilities:**
- Summarize recent UART logs
- Extract first meaningful failure
- Classify failures into categories
- Compare current boot log with known-good baseline
- Generate structured debug reports
- Suggest what evidence to collect next and what the Coding Agent should inspect

**Not responsible for:** source-code patches, claiming root-cause certainty without code context, raw hardware control.

**Example output:**
```json
{
  "result": "boot_failed",
  "first_failure": "bq25185 init failed: -5",
  "failure_class": "i2c_or_power_sequence",
  "evidence": [
    "failure occurs after SENSOR_PWR_EN",
    "device did not report successful I2C probe",
    "known-good boot had a delay before this stage"
  ],
  "recommended_next_steps_for_coding_agent": [
    "Inspect charger initialization path",
    "Check I2C address/configuration",
    "Check delay after regulator enable"
  ]
}
```

---

### 3.5 Coding Agent

Separate from the Debug Agent. Has source-code context and drives the firmware development loop.

**Responsibilities:**
- Inspect source code, Kconfig, device tree, build scripts, and logs
- Build firmware and coordinate flashing *(flash step uses external tooling — out of scope)*
- Request hardware tests through MCP tools
- Apply patches and run static checks
- Treat the Debug Agent as a hardware evidence provider and test orchestrator

---

## 4. Safety & Boundaries

### 4.1 Core Principle

```
Hardware control must be deterministic.
AI reasoning must be advisory and bounded.
```

The LLM must never send arbitrary GPIO commands or raw serial bytes directly to the DUT. All hardware operations pass through the Device Core for validation.

```
Bad:  LLM → set GPIO 17 high → hardware
Good: LLM → reset_dut() → Device Core validates → hardware reset pulse
```

### 4.2 Required Safety Rules

- Always preserve raw logs
- Validate every hardware command in the Device Core
- Expose high-level operations, not raw pin pokes
- Require explicit `configure_gpio_mode` before any reset or boot-mode operation
- Log every hardware action with timestamps
- Mark power-control features as advanced

### 4.3 Dangerous Operations (require explicit enablement)

- Power-cycle DUT
- Drive arbitrary GPIO outputs
- Run repeated reset loops
- Change voltage rails

### 4.4 AI Reasoning Boundaries

**Appropriate uses:** summarizing logs, identifying first meaningful failure, classifying failure type, suggesting next evidence to collect, producing debug reports.

**Must not be used for:** unvalidated raw GPIO control, destructive operations, claiming root-cause certainty without code context, silently modifying device state, replacing raw logs.

AI-generated diagnosis must preserve uncertainty:
```
The evidence suggests...       ✓
The likely failure class is... ✓
This is not enough to prove root cause because... ✓

The exact bug is...            ✗ (unless evidence is explicit)
This definitely proves...      ✗
```

---

## 5. Scope

### In Scope

- UART log capture from a DUT
- Accurate within-session timestamping of UART events (relative to session start, using RP2040 64-bit TIMER)
- Reset control and boot-mode/control-pin control
- Debug session storage, log search and filtering
- Baseline comparison between known-good and failing logs
- First-failure extraction
- Structured reports for AI coding agents
- CLI and MCP access
- Optional GPIO event capture and power/current/voltage monitoring (Phase 5)

### Out of Scope

- Running an LLM on the debug helper hardware
- Replacing professional oscilloscopes or logic analyzers
- Full JTAG/SWD debugging
- Arbitrary autonomous hardware actions without validation
- Supporting every MCU/debug target from the start
- Complex GUI before core workflow is proven
- Wi-Fi/BLE in MVP
- Complex custom USB vendor interface in MVP
- **Flashing firmware to the DUT** — use external tooling (picotool, openocd, west flash, esptool)
- Source-code repository analysis inside the Debug Agent

---

## 6. MVP Definition

### 6.1 Hardware

- **RP2040-based board** (Raspberry Pi Pico or equivalent)
- DUT UART TX → RP2040 UART RX
- DUT UART RX ← RP2040 UART TX (command injection)
- DUT RESET and BOOT/control lines driven through safe DUT-referenced control stages (see §6.4)
- Common ground between DUT and debug helper
- RP2040 USB CDC/serial → host machine

### 6.2 Firmware

- Zephyr RTOS on RP2040 *(see Known Limitations §15.1)*
- RP2040 UART peripheral for DUT log capture at 460800 baud
- GPIO control for DUT RESET and BOOT/control pins through safe DUT-referenced control stages
- **64-bit hardware TIMER** for within-session event timestamps (1µs resolution)
- 32 KiB UART RX ring buffer to absorb short host/USB backpressure *(see `docs/ring_buffer_sizing_plan.md`)*
- NDJSON command protocol over USB CDC/serial *(migration path to MessagePack+COBS in Phase 3)*
- Timestamped event stream to host

### 6.3 Host Software

- Python 3.10+ implementation with `asyncio`-based serial reader using `pyserial-asyncio` (standard `pyserial` does not support asyncio natively)
- CLI for session management and debug workflows
- USB CDC/serial communication with RP2040
- Timestamped UART/event ingestion and raw log file storage
- Structured debug session storage
- Reset DUT, BOOT/control pin, and capture-after-reset workflows
- Get last N log lines, wait for log pattern, basic error keyword detection
- MCP tool exposure in Phase 2, after CLI workflows are validated in Phase 1
- Device Core Service: persistent FastAPI process (single owner of the serial port; CLI and MCP Server both call its REST API over local HTTP on port `2040` by default, configurable in `.dutchmate/config.toml`)

### 6.4 UART and Reset/BOOT Electrical Interface

Phase 1 hardware architecture is defined in
`docs/dutchmate_hardware_architecture.md`. In short, DUTchMate uses
fixed-direction voltage-domain interfaces instead of one generic bidirectional
translator for every signal:

- `CTRL0` to `CTRL3`: DUTchMate-to-DUT control channels.
- `EVENT0` to `EVENT3`: DUT-to-DUTchMate event channels.
- UART: fixed TX-to-RX translation in both directions.

The user maps physical channels to DUT schematic signals in configuration, for
example `CTRL0` as the `reset` role connected to the DUT `RESET_N` net.

The Device Core exposes an API to configure control roles and runtime GPIO
drive modes:

```python
configure_control_role(
    role: str,
    channel: str,
    mode: Literal["open_drain", "push_pull"],
    dut_signal: str,
) -> None
```

Valid Phase 1 workflow roles are `"reset"` and `"boot"`. Valid physical
control channels are `CTRL0` to `CTRL3`.

This must be configured explicitly before any reset or boot-mode operation.
There is no implicit default — the Device Core returns a `not_configured` error
if a reset or boot command is issued before the relevant role mapping and mode
have been accepted. A mode loaded from `.dutchmate/config.toml` counts as
explicit configuration because it represents a stored user decision. The
firmware may reject a requested mode with `invalid_argument` or
`hardware_fault` if the connected hardware revision cannot implement that mode
safely.

GPIO configuration semantics are defined in `docs/gpio_configuration_semantics.md`. In short: configuration is accepted only after firmware acknowledgement, runtime overrides do not edit `.dutchmate/config.toml`, rejected mode requests must not change the previous accepted mode or physical channel state, and `dutchmate status` must show each required role as `unconfigured`, `configured`, or `rejected`. The current host core implements the command/result workflow behind this state; the real serial transport is still pending.

### 6.5 CLI Commands

**Daemon lifecycle:**
```bash
dutchmate start                        # auto-detect DUTchMate device by USB VID/PID
dutchmate start --port /dev/ttyACM0   # specify port explicitly
dutchmate stop                         # shut down the daemon
dutchmate status                       # show daemon state and connected port
```

`dutchmate start` launches the Device Core Service as a background process on `http://localhost:2040` (default, configurable in `.dutchmate/config.toml`) and connects to the Debug Helper. Auto-detection scans USB serial ports for a device matching the DUTchMate USB VID/PID and product string. If exactly one match is found it connects automatically; if multiple matches are found it lists them and exits asking the user to specify `--port`. All other commands send HTTP requests to the running service and fail immediately with a clear error if the service is not running:
```
Error: service not running. Run 'dutchmate start' first.
```

**Debug commands:**
```bash
# hardware configuration (required before first reset/boot-mode)
dutchmate gpio-mode reset open_drain

# hardware control
dutchmate reset
dutchmate boot-mode normal       # drive BOOT/control pin to inactive state — DUT boots from flash
dutchmate boot-mode bootloader   # drive BOOT/control pin to active state — DUT enters DFU/bootloader on next reset

# capture and observation
dutchmate capture --seconds 10
dutchmate logs --last 200
dutchmate wait "BOOT_OK" --timeout 5
dutchmate boot-test --seconds 15

# UART interaction
dutchmate send "reboot"              # rejected if capture active
dutchmate send "reboot" --force      # sends immediately, logs perturbation warning

# session management
dutchmate mark-baseline <session_id> # designate session as known-good reference for compare_boot_log
```

### 6.6 MCP Tools

Phase 2 default launch command:

```bash
dutchmate mcp
```

This command speaks MCP over stdio and writes logs only to stderr. It does not start or own the Device Core Service; it returns a clear tool error if `dutchmate start` has not been run.

Full target tool list:

```
reset_dut()                               — Phase 2
set_boot_mode(mode)                       — Phase 2
capture_uart(seconds)                     — Phase 2
get_recent_uart_log(lines)                — Phase 2
wait_for_uart_pattern(pattern, timeout_s) — Phase 2
run_boot_test(duration_s)                 — Phase 2
send_uart_command(cmd, force=False)       — Phase 2
compare_boot_log(session_id)              — Phase 4
get_debug_session(session_id)             — Phase 2
list_debug_sessions()                     — Phase 2
```

### 6.7 Device Core Service API

The REST API exposed by the Device Core Service at `http://localhost:<port>`. Both the CLI and MCP Server are clients of this API. All endpoints return JSON. Error responses follow `{"ok": false, "error": "<code>", "detail": "..."}`.

**Service:**

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `GET` | `/status` | — | `{connected, port, firmware, active_session_id, gpio_modes}` |

**Hardware control:**

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `POST` | `/gpio/mode` | `{role: "reset"\|"boot", mode: "open_drain"\|"push_pull"}` | `{ok, role, channel, dut_signal, mode, source, timestamp_us?}` |
| `POST` | `/dut/reset` | `{pulse_ms?}` | `{ok, timestamp_us}` |
| `POST` | `/dut/boot-mode` | `{mode: "normal"\|"bootloader"}` | `{ok, timestamp_us}` |

**Capture and observation:**

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `POST` | `/dut/capture` | `{duration_s}` | `{ok, session_id, overflow, interrupted, resumed, segments}` |
| `GET` | `/dut/logs` | `?lines=300` | `{lines: [...], overflow}` |
| `GET` | `/dut/events` | — | SSE stream of NDJSON events |
| `POST` | `/dut/wait-pattern` | `{pattern, timeout_s}` | `{ok, matched, line, timestamp_us, overflow}` |
| `POST` | `/dut/boot-test` | `{duration_s}` | `{ok, session_id, first_error, overflow, interrupted, resumed, segments}` |

**UART:**

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `POST` | `/dut/uart/send` | `{cmd, force?}` | `{ok, perturbation_logged}` |

**Sessions:**

| Method | Path | Params / Body | Response |
|--------|------|---------------|----------|
| `GET` | `/sessions` | — | `[{session_id, timestamp, baseline, truncated, interrupted, resumed, segments}]` |
| `GET` | `/sessions/{id}` | — | full metadata + detected patterns + summary |
| `POST` | `/sessions/{id}/baseline` | — | `{ok}` |
| `GET` | `/sessions/{id}/compare` | — | baseline comparison result *(Phase 4)* |

Every response that involves a capture includes an `overflow: bool` field so callers can tell whether evidence may be incomplete.

**Concurrency:** Only one active capture at a time. `POST /dut/capture`, `POST /dut/boot-test`, `POST /dut/reset`, and `POST /dut/boot-mode` return `{"ok": false, "error": "capture_active"}` immediately if a capture is in progress (use `force: true` on `/dut/uart/send` to bypass the guard for UART commands). Read-only endpoints and `GET /dut/events` are always available.

---

## 7. Session Model

Every debug run is stored as a session.

**Session ID format:** `YYYYMMDD_HHmmss_SSS_<label>` (millisecond suffix prevents collision in rapid automated test loops).

`<label>` rules:
- Optional — defaults to the invoking command name in snake_case (e.g. `boot_test`, `capture`, `wait`)
- Overridable via `--label <name>` on CLI commands and an optional `label` parameter on MCP tools
- Allowed characters: `[a-z0-9_-]` only; the Device Core Service lowercases and replaces spaces with `_` before use
- Max 32 characters; truncated silently if longer
- The Device Core Service sanitizes the label before constructing the session directory path (no path traversal)

**Session contents:**
- Session ID and timestamp (host wall clock at session start)
- Project name, DUT name, board name
- Firmware version or git commit (if provided), test goal (if provided)
- Reset events
- UART raw log (decoded bytes, lossless)
- Parsed UART events (`uart_events.jsonl`)
- Hardware/session events (`hardware_events.jsonl`)
- Detected patterns (`detected_patterns.json`)
- First failure (if any)
- `truncated: true` if per-session size cap was hit mid-capture
- `interrupted: true` if USB disconnected mid-session
- `resumed: true` if events were appended after a reconnect
- Segment metadata for reconnect/timestamp discontinuities
- `baseline: true` if this session has been explicitly marked as the known-good reference
- Optional AI summary and baseline comparison result

**Storage location:** `.dutchmate/sessions/` relative to the DUT firmware project root. Overridable via `.dutchmate/config.toml`. The `.dutchmate/` directory should be added to the DUT project's `.gitignore` — it contains raw logs and debug data that should not be committed.

**Retention policy:** keep the last 100 sessions by default; delete the oldest when the count is exceeded. Configurable in `.dutchmate/config.toml`.

**Per-session size cap:** 50MB per session by default. When the cap is hit mid-capture, ingestion stops, the session is marked `truncated: true` in `metadata.json`, and a warning is logged. Configurable in `.dutchmate/config.toml`. Combined with the session count limit, worst-case disk usage is bounded at 5GB by default.

**File layout:**
```
.dutchmate/
  config.toml
  sessions/
    20260630_153000_123_boot_test/
      metadata.json
      uart_raw.log
      uart_events.jsonl
      hardware_events.jsonl
      detected_patterns.json
      report.md          # generated by AI Debug Agent — Phase 4 and later only
```

**Example `.dutchmate/config.toml`:**
```toml
[daemon]
port = 2040                  # localhost HTTP port
reconnect_timeout_s = 5      # seconds to wait for hello handshake before starting a new session

[sessions]
path = ".dutchmate/sessions" # relative to project root
max_count = 100              # oldest session deleted when exceeded
max_size_mb = 50             # per-session cap; triggers truncated: true when hit

[patterns]
keywords = ["ERROR", "ASSERT", "PANIC", "HardFault", "BOOT_OK"]

[hardware]
dut_io_voltage = 1.8

[hardware.control.reset]
channel = "CTRL0"
dut_signal = "RESET_N"
mode = "open_drain"          # applied automatically on service start
active_level = "low"

# boot intentionally omitted by default; configure per target wiring
```

If a required role is not mapped in `[hardware.control.*]`, that role remains unconfigured at startup — the `not_configured` error still applies until `dutchmate gpio-mode <role> <mode>` is called explicitly. `dutchmate gpio-mode` can be used to override the mode at runtime without editing the file.

Config-file GPIO modes are applied after the Debug Helper `hello` message is validated. A role is marked configured only after the firmware accepts the mode. If startup configuration is rejected, the service remains running, `dutchmate status` reports the rejected role state, and workflows requiring that role fail until a valid runtime mode is configured.

Raw logs are always more authoritative than AI summaries and must always be preserved.

---

## 8. Host-Device Protocol

### 8.1 Principles

The protocol must be:
- Versioned from day 1 (enables future encoding migration)
- Machine-readable and transport-agnostic (USB CDC now; USB vendor-class or TCP later without changing Device Core)
- Tolerant of reconnects — see reconnect behaviour below
- Timestamped on the device side (64-bit TIMER, before the USB CDC path)
- Support both event streaming and command/response

The v1 protocol schemas and canonical examples live under `hardware/protocol/v1/`. Firmware, Device Core parsing, and tests must use those schemas as the implementation contract.

**Reconnect behaviour:** see `docs/reconnect_session_semantics.md` for the full policy. In short, the Device Core writes `uart_raw.log`, `uart_events.jsonl`, `hardware_events.jsonl`, and `metadata.json` incrementally as events arrive. Data up to a disconnect is always preserved on disk. A disconnect marks the session `interrupted: true`; a valid reconnect before `reconnect_timeout_s` may append a new segment to the same session and mark `resumed: true`. Device timestamps are authoritative only within a segment, so resumed sessions record a timestamp discontinuity instead of pretending timestamps are continuous.

### 8.2 Encoding

**MVP 1 — NDJSON over USB CDC:**
Simple to implement, human-readable, easy to debug with a serial terminal. Suitable for typical boot log densities at 460800 baud.

**Phase 3 migration — MessagePack + COBS:**
MessagePack reduces payload ~30–40% vs JSON. COBS (Consistent Overhead Byte Stuffing) uses `0x00` as a reliable packet boundary, handles binary payloads cleanly, and adds minimal framing overhead. Protocol versioning from MVP 1 enables this migration without breaking the Device Core model.

**DUT baud rate: 460800 baud** (MVP 1 target). Widely supported by Zephyr, ESP-IDF, and most embedded targets. Gives ~46 KB/s raw throughput, manageable with NDJSON at typical boot log densities. 921600 baud is not recommended for MVP due to USB CDC overhead risk.

### 8.3 UART Payload Encoding

UART bytes from a DUT are not guaranteed to be valid UTF-8 (crash dumps, garbled boot output, binary blobs are expected). The wire protocol carries UART payload as **base64-encoded bytes** in a `data_b64` field — never as a raw JSON string. This keeps the protocol byte-safe regardless of DUT output.

The Device Core is the only layer that produces a lossy human-readable view (UTF-8 with replacement characters) for CLI display and pattern matching. `uart_raw.log` stores decoded raw bytes losslessly.

### 8.4 Example Messages

**Connection handshake** (sent by device immediately after USB connection):
```json
{"type": "hello", "v": 1, "firmware": "0.1.0", "device": "dutchmate-rp2040", "capabilities": ["uart_capture", "gpio_control", "uart_send"]}
```

The Device Core must validate `v` before starting any session. On version mismatch it must reject the connection with a clear error rather than silently misinterpreting messages.

The `capabilities` array lists features the connected firmware supports. Known values:

| Capability | Introduced | Meaning |
|---|---|---|
| `uart_capture` | Phase 1 | UART receive and timestamping |
| `gpio_control` | Phase 1 | Reset and BOOT/control pin drive |
| `uart_send` | Phase 1 | UART command injection |
| `gpio_events` | Phase 5 | PIO-based GPIO edge capture |
| `power_sense` | Phase 5 | Voltage/current sensing |
| `msgpack` | Phase 3 | MessagePack+COBS protocol encoding |

The Device Core must not call a command for a capability the firmware did not advertise. MCP tools that depend on an absent capability must return a clear error rather than forwarding a command that will fail.

Channel-aware GPIO mode configuration (must be sent before first reset or
boot-mode command):
```json
{"cmd": "configure_gpio_mode", "channel": "CTRL0", "role": "reset", "mode": "open_drain", "active_level": "low"}
```

Response (success):
```json
{"ok": true}
```

Reset command:
```json
{"cmd": "reset", "pulse_ms": 100}
```

Response (success):
```json
{"ok": true, "timestamp_us": 182334400}
```

Response (error — required role was not configured first):
```json
{"ok": false, "error": "not_configured", "detail": "reset role is not configured"}
```

Boot-mode command:
```json
{"cmd": "set_boot_mode", "mode": "bootloader"}
```

Response (success):
```json
{"ok": true, "timestamp_us": 182335000}
```

UART send command (payload base64-encoded for byte safety):
```json
{"cmd": "uart_send", "data_b64": "<base64>"}
```

Response (success):
```json
{"ok": true}
```

Error codes:

| Code | Meaning |
|---|---|
| `invalid_command` | Unknown or malformed command |
| `invalid_argument` | Argument out of range or wrong type |
| `not_configured` | Required role mapping or mode was not configured before reset/boot operation |
| `capture_active` | A capture is already in progress; hardware command rejected |
| `hardware_fault` | GPIO or UART operation failed |
| `timeout` | Operation did not complete in time |

UART event:
```json
{"type": "uart", "channel": 0, "timestamp_us": 182341200, "data_b64": "<base64>"}
```

Buffer overflow event:
```json
{"type": "buffer_overflow", "channel": 0, "timestamp_us": 182350000, "dropped_bytes": 512}
```

Buffer telemetry event:
```json
{"type": "buffer_status", "timestamp_us": 182360000, "uart_rx_size_bytes": 32768, "uart_rx_used_bytes": 4096, "uart_rx_high_water_bytes": 18432, "dropped_bytes_total": 512, "overflow_events": 1}
```

### 8.5 Buffer Overflow Policy

- Overflow must never be silent. A full buffer is an event, not a no-op.
- Default policy: **drop-oldest** (newest data has highest debugging value near a failure).
- Every `buffer_overflow` event is recorded in `hardware_events.jsonl`.
- `buffer_status` events provide firmware-side high-water and dropped-byte telemetry for sizing validation.
- Any result returned to MCP callers must include an `overflow: bool` field so agents can tell whether evidence may be incomplete without inspecting raw files.
- Initial Phase 1 UART RX ring buffer size: **32 KiB**. See `docs/ring_buffer_sizing_plan.md` for assumptions, memory budget, and validation criteria.

---

## 9. Design Rules

For contributors and AI coding agents working on this repository:

1. Keep hardware control deterministic.
2. Keep the Device Core independent from MCP and LLM providers.
3. Keep MCP tools thin and high-level.
4. Preserve raw logs before summarizing or filtering.
5. Prefer small, testable changes.
6. Do not add cloud dependencies to the core capture path.
7. Do not expose arbitrary raw GPIO control as a default MCP tool.
8. Use explicit schemas for commands, events, and reports.
9. Separate session storage from log analysis.
10. Treat AI-generated diagnosis as advisory.
11. Validate CLI workflows before exposing them through MCP.
12. Design for one DUT first; avoid premature multi-device complexity.
13. Require explicit `configure_gpio_mode` before any reset or boot-mode operation.
14. Serialize hardware-starting operations: only one active capture at a time. A second attempt returns `capture_active` immediately. Read-only operations (`GET /dut/logs`, `GET /sessions`, etc.) and the SSE event stream are always available concurrently.
15. Protocol changes require updating schemas, examples, parser tests, and firmware handling in the same change.
16. GPIO mode changes are accepted only after firmware acknowledgement; rejected mode requests must not change prior accepted state.
17. Reconnects must be represented as session segments with explicit timestamp discontinuities; never compare raw device timestamps across segments as if they share one epoch.
18. Buffer sizing changes require measurement data: high-water mark, overflow count, dropped bytes, UART baud rate, and host backpressure conditions.
19. MCP integration defaults to stdio via `dutchmate mcp`; Streamable HTTP is optional and HTTP+SSE is compatibility-only.

### 9.1 Testing Strategy

Three layers, in order of priority:

| Layer | Hardware required | Tooling |
|---|---|---|
| **Unit** — protocol parsing, pattern detection, session storage, base64 decoding, line buffering, overflow handling | None — inject pre-recorded NDJSON fixtures via mock serial transport | `pytest`, `pytest-asyncio` |
| **Integration** — Device Core Service API, full session lifecycle, reconnect and truncation behaviour | None — mock serial stream injected at the Device Core boundary | `httpx`, `pytest-asyncio` |
| **Hardware-in-the-loop** — real RP2040 + DUT, full boot test and UART capture workflow | Yes | Manual verification or a dedicated hardware CI rig |

Most Device Core logic is testable without hardware by replaying pre-recorded NDJSON streams. New Device Core features must include unit or integration tests before being exposed through MCP. Hardware-in-the-loop tests are reserved for firmware changes and full end-to-end validation.

Any workflow exposed through the CLI must first pass through mocked Device Core tests, Device Core Service integration tests, and CLI-level tests against the service API. Hardware smoke tests validate the final RP2040 + DUT behavior, but should not be the first place workflow correctness is established.

---

## 10. Contributing

**Repository:** `https://github.com/<your-org>/dutchmate` *(placeholder — update when repo is created)*

**Contribution workflow:**
1. Fork the repository and create a feature branch.
2. Make changes following the design rules in §9.
3. Add or update tests in the appropriate layer (see §9.1).
4. Open a pull request with a clear description of what changed and why.

**Key files for new contributors:**
- `project_context.md` — this document; read before making changes
- `docs/project_layout.md` — monorepo package layout and Python tooling decision
- `docs/phase1_implementation_spec.md` — concrete Phase 1 implementation order and done criteria
- `docs/dutchmate_hardware_architecture.md` — proposed voltage-domain GPIO/UART interface and channel mapping model
- `docs/gpio_configuration_semantics.md` — RESET/BOOT configuration state model and service behavior
- `docs/reconnect_session_semantics.md` — reconnect, resume, segment, and timestamp discontinuity behavior
- `docs/ring_buffer_sizing_plan.md` — Phase 1 buffer size, telemetry, and validation plan
- `docs/mcp_integration_plan.md` — Phase 2 MCP transport, launch, and tool behavior
- `hardware/protocol/` — host-device protocol definition; changes here affect both firmware and host
- `core/` — Device Core library; must remain MCP and LLM-independent
- `hardware/firmware/` — Zephyr firmware for RP2040

**Contribution guidelines:**
- CLI workflows must be validated before MCP exposure (design rule 11)
- New Device Core features must include unit or integration tests (§9.1)
- Raw log preservation is non-negotiable (design rule 4)
- Hardware-facing changes (reset pulse timing, GPIO mode, protocol messages) require justification in the PR description

**Reporting bugs:** open a GitHub issue at `https://github.com/<your-org>/dutchmate/issues` *(placeholder — update when repo is created)*. Include:
- OS and Python version
- Firmware version (`dutchmate status` output)
- RP2040 board model
- Steps to reproduce and what you expected vs. what happened
- Relevant log output or error messages

For hardware-specific issues (signal levels, timing, electrical), also include the DUT board model and how the RESET/BOOT lines are wired.

A `CONTRIBUTING.md` with full setup instructions for development will live at the repository root.

---

## 11. Development Phases

### Phase 1: RP2040 Debug Helper MVP

**Goal:** prove the hardware-in-the-loop workflow using RP2040 + Zephyr + USB CDC/serial.

Implementation order: build and test the host-side protocol parser, session store, workflows, service API, and CLI against mocked NDJSON fixtures before relying on hardware-in-the-loop testing. Firmware should then implement the already-tested v1 protocol contract.

Deliverables:
- Zephyr firmware for RP2040
- DUT UART capture with 64-bit TIMER timestamps
- Ring buffer + buffer overflow events
- Reset and BOOT/control pin control via voltage translator
- NDJSON command protocol over USB CDC
- Device Core Service (Phase 1 foundation — lightweight FastAPI process that imports the Device Core library and holds the serial port)
- Host-side Python CLI communicating with the Device Core Service over HTTP
- Boot-test workflow and debug session storage
- Basic error pattern detection
- UART command injection (`send_uart_command`) as a CLI command (MCP tool in Phase 2); rejected during active capture unless `--force` is passed

### Phase 2: MCP Integration

**Goal:** allow coding agents to use the debug workflow through MCP.

Deliverables: MCP Server added as a separate `dutchmate mcp` stdio process calling the Phase 1 Device Core Service API, MCP tools for reset/capture/boot-test/log-retrieval/UART-command, structured result schemas. Optional Streamable HTTP MCP hosting is deferred until a concrete client requires it.

### Phase 3: Hardware & Protocol Refinement

**Goal:** stabilize and harden the system after MVP validation.

Deliverables: protocol migration to MessagePack + COBS if throughput requires it, optional custom carrier board or shield with PCB-level protection components (TVS diodes, series resistors — complementing the Phase 1 voltage translator), optional GPIO edge capture, hardware timestamping review.

### Phase 4: AI Debug Reports

**Goal:** add optional LLM-assisted log diagnosis.

Deliverables: log context packer, first-failure extraction, failure classification, baseline comparison summaries, structured AI debug report.

### Phase 5: Advanced Hardware Evidence

**Goal:** support richer hardware debugging.

Possible features: multiple UART channels, PIO-based GPIO edge capture, current/voltage sensing, power-cycle control, display on debug helper, Wi-Fi streaming.

---

## 12. Example Workflow

```
1.  Coding Agent builds firmware.
2.  Coding Agent flashes DUT (external tool — out of scope).
3.  Coding Agent calls MCP tool: run_boot_test(duration_s=15).
4.  MCP Server forwards request to Device Core Service API.
5.  Device Core Service resets DUT via Device Core library.
6.  Device Core Service captures UART and hardware events.
7.  Device Core Service stores a debug session.
8.  Device Core Service returns structured evidence.
9.  Coding Agent uses evidence plus source code to inspect likely modules.
10. Coding Agent patches firmware.
11. Loop repeats.
```

Example structured result:
```json
{
  "status": "failed",
  "session_id": "20260630_153000_123_boot_test",
  "first_error": "ERROR: sensor init failed -5",
  "time_to_error_ms": 1240,
  "reset_count": 1,
  "overflow": false,
  "relevant_log_excerpt": [
    "[00:00:01.100] SENSOR_PWR_EN high",
    "[00:00:01.220] ERROR: sensor init failed -5"
  ]
}
```

---

## 13. Open Questions

1. What is the pin mapping for RP2040 UART, RESET, and BOOT/control signals?
2. Which exact fixed-direction UART translator package and open-drain transistor parts should be used in the first schematic revision?
3. Does the initial 32 KiB UART RX ring buffer meet Phase 1 validation criteria on real boot logs?
4. Which clients need optional Streamable HTTP MCP mode beyond the Phase 2 default `dutchmate mcp` stdio transport?
5. How much context should the Debug Agent receive from the Coding Agent?
6. Should AI log analysis be local-only, cloud-based, or pluggable?
7. What DUT firmware ecosystem should be tested first: Zephyr, STM32Cube, ESP-IDF, or Linux/RPi?

---

## 14. Success Criteria

The project is successful when a coding agent can run:

```
Build firmware → flash DUT (external) → reset DUT → capture timestamped UART log
→ detect failure → inspect source → patch → retest
```

with minimal manual log copying or button pressing.

**Strong MVP demonstration:**
1. DUT boots and emits UART logs.
2. RP2040 debug helper captures timestamped logs after reset.
3. Device Core Service stores the run as a debug session.
4. Coding Agent requests the latest boot test through MCP.
5. Device Core Service returns structured failure evidence with `overflow: bool` field.
6. Coding Agent uses source context to suggest or apply a firmware fix.
7. Device Core Service verifies the new firmware behavior after the next reset.

**Primary value proposition:**
```
Give AI coding agents reliable eyes and hands on real embedded hardware.
```

---

## 15. Known Limitations

### 15.1 Zephyr on RP2040 — PIO Support

Zephyr's RP2040 BSP supports core peripherals (UART, GPIO, USB CDC) and is sufficient for Phase 1. However, **PIO is not well-supported under Zephyr**. PIO-based features planned for Phase 5 — custom UART capture, GPIO edge capture, trigger logic — may require custom Zephyr drivers or a partial migration to the Pico SDK HAL. This is a known risk to be evaluated before committing to Phase 5 features.

### 15.2 USB CDC Timestamp Jitter

USB CDC delivery from the RP2040 to the host has millisecond-level jitter. **Host-side timestamps are unreliable for event ordering.** All event timestamps in the protocol are generated on the RP2040 by the 64-bit TIMER peripheral before the USB CDC path, so within-session event ordering is accurate. Host timestamps are only used for session metadata (wall clock at session start).

### 15.3 Electrical Isolation

The RP2040 debug helper is USB-powered and shares a common ground with the DUT. If the DUT has power problems (brownout, latch-up, short circuit), the debug helper is directly exposed. Minimum recommended protection:
- TVS diodes on UART and RESET signal lines
- Series resistors (33–100Ω) on UART RX/TX lines
- Voltage translator isolation between RP2040 and DUT signal domains

These protections are not implemented in MVP 1 but should be added before any shared or production-adjacent use.

### 15.4 NDJSON Throughput at High Baud Rates

NDJSON + base64 encoding adds ~33–50% overhead over raw UART bytes. At 460800 baud (~46 KB/s raw), this is manageable for typical boot log densities. At 921600 baud or with dense continuous DUT logging, ring buffer overflows become likely. The planned Phase 3 migration to MessagePack + COBS addresses this.

### 15.5 Software Timestamps Only (MVP)

The RP2040 UART peripheral delivers bytes via interrupt. TIMER timestamps are captured in the interrupt handler — accurate to firmware scheduling jitter (typically tens of microseconds under Zephyr). This is sufficient for boot sequence analysis and failure detection but not for sub-microsecond timing measurements. PIO-based hardware UART capture (Phase 5) could provide true hardware timestamps if needed.

### 15.6 pyserial-asyncio Required

Standard `pyserial` does not support asyncio. The Device Core serial reader must use `pyserial-asyncio`. Using `pyserial` directly in an asyncio context requires `loop.run_in_executor` wrapping a blocking read, which adds complexity and latency. Pin `pyserial-asyncio` as an explicit dependency from the start.

### 15.7 Ring Buffer Size Requires Validation

The initial Phase 1 UART RX ring buffer size is 32 KiB. At 460800 baud (~46 KB/s raw UART throughput), this absorbs roughly 0.7 seconds of full-rate UART data while the host streams events to disk. This is a backpressure buffer, not the long-term log store.

The size is constrained by the RP2040's 264 KiB RAM, which is shared with firmware, stacks, USB buffers, and protocol encoding. Phase 1 must measure high-water marks, overflow counts, and dropped bytes on real boot logs and synthetic stress loads before freezing the design. Until then, overflow events must be treated as normal operational conditions.

### 15.8 Windows Not Yet Supported

`dutchmate start` launches the daemon as a background process using POSIX process management (signals, background fork). This does not work on Windows without a different approach (e.g. Windows Service, `pythonw`, or a separate `dutchmate daemon` command that keeps the terminal). Serial port naming also differs (`COM3` vs `/dev/ttyACM0`). Windows support is planned but not in scope for MVP. Contributors targeting Windows should note these two areas as the primary porting work.

### 15.9 Device Core Service Has No Authentication (MVP)

The Device Core Service binds to `http://localhost:2040` with no authentication. Any local process or user on the machine can send hardware commands (reset, boot-mode, UART injection). Localhost binding prevents remote access, so this is acceptable for a single-developer workstation. On shared workstations or CI servers it is a real exposure.

A simple API key (bearer token, configurable in `.dutchmate/config.toml`) is planned for Phase 3 when multi-user or CI use becomes relevant. Until then, treat the Device Core Service port as trusted-local only and do not expose it to the network.
