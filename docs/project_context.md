# Project Context: DUTchMate

> Status: accepted architecture overview
> Purpose: durable product context, architecture decisions, scope, and roadmap.

This document explains what DUTchMate is and why its major boundaries exist.
It intentionally does not duplicate executable contracts. The Phase 1 API,
session, backend, protocol, and acceptance requirements live in
`docs/phase1_implementation_spec.md`; focused documents own the hardware, GPIO,
reconnect, MCP, ring-buffer, and Debug Agent contracts.

## Product

DUTchMate is an AI-assisted embedded debugging system. Its host software
receives real evidence from a Device Under Test (DUT), stores that evidence as
structured debug sessions, and exposes deterministic workflows to humans and
coding agents. LLM reasoning runs on the host or in a selected remote service,
never on the embedded Debug Helper.

The problem is fragmented embedded debugging: UART terminals, reset controls,
flash tools, instruments, notes, and coding agents all hold separate parts of
the evidence. Coding agents can inspect source but normally cannot retrieve
boot logs or request a bounded hardware test. DUTchMate provides that controlled
evidence boundary without making AI part of hardware control.

Use **DUTchMate** in repository and user-facing text. The primary CLI command is
`dutchmate`; `dm` may remain as a short alias.

The target development loop is:

```text
build firmware
  -> flash DUT with an external tool
  -> reset manually or through a capable backend
  -> receive and store UART evidence
  -> detect and inspect failures
  -> modify source
  -> repeat
```

## Architecture

```text
Coding Agent / IDE Agent
        |
        | MCP stdio (Phase 2)
        v
MCP Server ------------------+
                             | HTTP
CLI -------------------------+
                             v
Device Core Service (FastAPI; owns one selected backend)
        |
        v
Device Core library (no HTTP, MCP, or AI dependency)
        |
        v
Exactly one device backend
  +-- Basic: generic USB-to-UART
  |     +-- UART receive and optional UART send
  +-- Enhanced: RP2040 DUTchMate Debug Helper
        +-- UART receive/send
        +-- CTRLn control
        +-- EVENTn observation (Phase 5)
        |
        v
Device Under Test
```

The Device Core Service is the only owner of the active serial connection. The
CLI and future MCP server are independent clients of its API. The reusable core
does not import app, MCP, or AI packages.

### Device Backends

Phase 1 supports two mutually exclusive backend modes:

| Capability | Basic | Enhanced |
|---|---|---|
| UART receive | Yes | Yes |
| UART send | Optional and policy-gated | Firmware capability and policy-gated |
| Timestamp source | Host serial-read observation | RP2040 device timer |
| Standardized overflow telemetry | No | Yes |
| `CTRLn` control | No | Yes |
| `EVENTn` observation | No | Hardware provisioned; software is Phase 5 |

The Basic backend is any user-selected TTL/logic-level USB-to-UART adapter that
appears as a normal host serial port. DUTchMate does not require a particular
vendor or chipset and does not probe it for a DUTchMate protocol. The user is
responsible for correct wiring, common ground, compatible TX/RX logic levels,
and any required voltage translation. An RS-232-level adapter must not connect
directly to DUT logic pins without external translation. Software transmit
disablement is permission policy, not proof that an attached adapter TX pin is
electrically high impedance.

The Enhanced backend is the complete RP2040-based DUTchMate Debug Helper. It
normalizes its private NDJSON protocol into the same host evidence model used by
Basic, adds device-side timestamps and buffer telemetry, and implements generic
`CTRL0` through `CTRL3` control. It is also the sole future owner of `EVENT0`
through `EVENT3` observation.

Exactly one backend is selected for a DUT connection. DUTchMate never combines
UART from a generic adapter with control or events from a separate Debug Helper.
Unsupported operations fail through explicit capability checks.

### Capabilities And Roles

Capabilities describe physical backend support, for example `uart_receive`,
`uart_send`, `gpio_control`, and future `gpio_events`. Roles describe project or
user meaning assigned to generic physical channels.

A user may map `CTRL0` to role `reset` and DUT signal `RESET_N`, or use custom
roles for another target. Interfaces may suggest `reset`, `boot`,
`power_enable`, and `wake`; these suggestions are not an enum. Phase 1 assigns
built-in workflow meaning only to exact lowercase `reset` and `boot`.

User roles and DUT signal names remain host-side metadata. Device Core resolves
a role to an accepted `CTRLn` mapping, then sends a generic configured-channel
action to firmware. Firmware does not interpret `reset`, `boot`, or a custom
role. Exact identifier and electrical-mode rules are defined in
`docs/gpio_configuration_semantics.md`.

### Evidence Boundary

Both backends implement the normalized `BackendEventSource` contract in
`docs/phase1_implementation_spec.md`. Backend-specific framing stops at that
boundary. Shared line reconstruction, pattern detection, session storage,
service behavior, CLI output, and future MCP tools consume normalized UART and
telemetry events without branching on adapter vendor or protocol message type.

Raw UART bytes are authoritative. Display text is a lossy UTF-8 projection;
patterns run on complete bounded lines, while every quota-admitted raw byte is
preserved. Serial and telemetry messages remain FIFO-ordered even while the
Enhanced backend waits for command responses.

Each connection or reconnect creates a new session segment with immutable
timestamp provenance. Basic timestamps describe host observation of a serial
read chunk. Enhanced timestamps describe firmware observation using the RP2040
timer. Neither implies per-byte timing, and timestamps are never compared across
segments.

Loss reporting is equally explicit. Basic normally reports upstream UART loss
as `not_observable`; Enhanced can report observations within its receive-buffer
scope. `none_reported` is never presented as proof that the complete path was
lossless. Local session truncation, transport interruption, and derived-line
limits remain separate evidence-quality facts.

### Sessions

Every finite receive workflow creates a filesystem session containing metadata,
raw UART bytes, UART events, hardware/session events, and detected patterns.
The native Phase 1 format is versioned, bounded, incrementally durable, and
uses one-way lifecycle transitions. Reconnects append segments to the same
session within a bounded policy window; process restart never silently resumes
a stale session.

The complete format, lifecycle, retention, baseline, quota, log-replay, and API
rules are in `docs/phase1_implementation_spec.md`. Reconnect and segment timing
rules are isolated in `docs/reconnect_session_semantics.md` because they apply
across storage, runtime, and both backends.

### Human And AI Clients

The CLI is a thin HTTP client and must validate workflows before they are
exposed through MCP. The Phase 2 MCP server is another thin Device Core Service
client over stdio; it does not own serial transport or invoke an LLM.

The optional Phase 4 Debug Agent is separate from the Coding Agent. It may
classify or summarize bounded session evidence through an explicitly selected
provider, but it cannot control hardware, crawl the repository, or apply source
patches. The Coding Agent retains source context and may explicitly supply a
bounded, provenance-bearing context package. `docs/debug_agent_context_contract.md`
owns this boundary.

## Scope

Phase 1 includes:

- backend-independent UART receive through Basic and Enhanced backends
- optional policy-gated UART send
- exact raw evidence preservation and bounded derived views
- deterministic pattern detection and `first_error`
- durable debug sessions, reconnect segments, retrieval, retention, and one
  project baseline
- local Device Core Service and CLI
- Enhanced generic control channels with configured reset/boot workflows
- RP2040 firmware, device timestamps, ring-buffer telemetry, and HIL validation

The project roadmap also includes Phase 2 MCP access, Phase 4 optional AI debug
reports, and Phase 5 GPIO event evidence and other advanced measurements.

Explicitly out of scope for Phase 1:

- firmware flashing; use target-specific external tools
- MCP or LLM integration
- GPIO `EVENTn` capture implementation
- Hybrid backend composition
- JTAG/SWD debugging
- arbitrary raw GPIO workflows
- power/current/voltage sensing
- multi-DUT support, GUI, Wi-Fi/BLE, and custom USB vendor protocols
- replacing oscilloscopes or logic analyzers

## Safety

```text
Hardware control is deterministic.
AI reasoning is advisory and bounded.
```

- Device Core validates every hardware-changing request.
- Control uses semantic workflows and configured roles, not arbitrary public
  pin-level commands.
- Reset and boot-mode operations require accepted GPIO configuration.
- Raw logs remain authoritative and are never replaced by summaries.
- Every hardware action is recorded with appropriate timing provenance.
- UART send is bounded, policy-gated, and visibly recorded when forced during
  an active receive workflow.
- Power cycling, voltage changes, arbitrary output drive, and repeated reset
  loops require explicit future design and enablement.
- AI analysis preserves uncertainty and never claims unsupported root-cause
  certainty or silently changes device state.

## Engineering Invariants

These rules summarize stable decisions. Detailed limits and validation order
remain in their owning contracts.

1. Keep Device Core independent from HTTP, MCP, and AI frameworks.
2. Preserve raw evidence before deriving text, lines, patterns, or reports.
3. Select one physical backend; never compose capabilities across devices.
4. Keep backend capabilities physical and control/event roles user-defined.
5. Terminate backend-specific protocol types at the normalized event boundary.
6. Use one background reader and preserve FIFO event order.
7. Represent reconnects as bounded segments with independent timestamp origins.
8. Keep loss observation, local truncation, interruption, and line-processing
   completeness as separate facts.
9. Serialize finite receive workflows; allow concurrent read-only retrieval.
10. Keep public hardware operations semantic, capability-gated, configured,
    bounded, and auditable.
11. Change Enhanced schemas, examples, parser/encoder models, tests, and firmware
    atomically when the wire protocol changes.
12. Keep session formats versioned, bounded, incrementally durable, and
    explicit about legacy compatibility.
13. Validate CLI and service workflows before MCP exposure.
14. Keep AI providers optional, pluggable, disabled by default, and outside the
    deterministic evidence path.
15. Require measurements for buffer sizing and hardware-component revisions.

## Roadmap

### Phase 1: Backend-Independent UART MVP

Phase 1A establishes the normalized event boundary, explicit Basic selection,
generic raw-serial receive/send, shared session and retrieval behavior, and a
real generic-adapter HIL path around a manual or external reset.

Phase 1B places the RP2040 Debug Helper behind the same boundary, migrates the
Enhanced protocol to `uart_receive` and generic channel actions, implements the
firmware and control workflows, validates the ring buffer, and runs Enhanced
HIL tests against the same DUT fixture.

Phase 1 is complete only when both backend modes pass shared mocked tests and
their real-hardware acceptance paths. `docs/phase1_implementation_spec.md` is
the normative implementation order and done checklist.

### Phase 2: MCP Integration

Add a separate `dutchmate mcp` stdio process that maps a bounded tool set to the
existing Device Core Service API. It returns deterministic Phase 1 evidence and
does not invoke an LLM. `docs/mcp_integration_plan.md` owns the transport and
tool contract.

### Phase 3: Hardware And Protocol Refinement

Use Phase 1 measurements to harden the hardware and protocol. Potential work
includes MessagePack plus COBS if NDJSON throughput is insufficient, controlled
protection/component revisions, connector refinement, and timestamp review.
Phase 3 does not include GPIO event capture.

### Phase 4: AI Debug Reports

Add bounded evidence packaging, optional source excerpts, advisory failure
classification, baseline comparison summaries, and structured reports behind a
pluggable provider boundary. The provider remains outside Device Core and never
receives unrestricted repository or hardware access.

### Phase 5: Advanced Hardware Evidence

Implement Enhanced `EVENTn` edge capture, event-role configuration,
segment-relative event timestamps, persistence, API/CLI exposure, and HIL
acceptance. Other candidates include multiple UART channels, power sensing,
power-cycle control, display, and wireless streaming.

## Success Criteria

Phase 1 succeeds when the same host pipeline can:

1. Receive a real DUT boot through a generic USB-to-UART adapter, preserve its
   evidence, detect relevant patterns, and expose the session through the CLI.
2. Repeat through the RP2040 Debug Helper without changing downstream
   processing, while adding device timestamps, overflow telemetry, UART send,
   and configured reset/boot-test control.
3. Report backend capability and evidence-quality differences explicitly.

Phase 2 succeeds when a coding agent can request those deterministic workflows
through MCP without manual log copying. Phase 4 analysis remains optional and
advisory.

## Known Limitations

- **Zephyr RP2040 PIO support:** Phase 1 uses supported UART, GPIO, timer, and
  USB CDC peripherals. Future PIO-based event/timing work may require custom
  drivers or Pico SDK integration.
- **Timestamp precision varies:** Basic host-read timestamps include adapter,
  USB, driver, scheduler, and application latency. Enhanced timer timestamps
  are stronger for within-segment ordering but still reflect firmware event
  granularity rather than sub-microsecond per-byte timing.
- **Basic loss is not fully observable:** generic adapters do not expose a
  standardized firmware-style dropped-byte counter. DUTchMate preserves bytes
  delivered to Device Core and reports the missing observer explicitly.
- **No galvanic isolation:** the Revision A Debug Helper shares ground with the
  DUT. Translation and connector protection reduce risk but do not isolate
  ground offsets, shorts, or fault energy. Prototype validation remains a
  release gate; see `docs/dutchmate_hardware_architecture.md`.
- **NDJSON overhead:** JSON and base64 increase Enhanced USB traffic. Phase 3
  may adopt a binary framed protocol if measured throughput requires it.
- **Firmware-sampled UART timestamps:** RP2040 timestamps are taken at firmware
  event handling granularity and are suitable for boot analysis, not precision
  logic analysis.
- **Continuous serial architecture is pending:** the current transport is
  synchronous. Phase 1 will use the pinned `pyserial-asyncio` dependency for
  one continuous reader per backend.
- **Ring buffer is selected but unvalidated:** Phase 1B starts at 32 KiB and
  records RAM and HIL measurements in
  `hardware/validation/phase1_ring_buffer.md` before acceptance.
- **Windows is not supported yet:** current service lifecycle management is
  POSIX-specific and serial naming differs.
- **Local API has no authentication:** the service binds to loopback by default
  and assumes a trusted single-developer machine. It must not be exposed to a
  network; shared or remote deployment requires an authentication design.

No unresolved architecture choices are currently recorded. Remaining work is
either implementation or an explicit empirical validation gate in its owning
document.
