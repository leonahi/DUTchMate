# Project Context: DUTchMate

> **Purpose:** durable product context for DUTchMate.
>
> This document defines the problem DUTchMate solves, the product model, deterministic behavior, evidence model, hardware/transport boundaries, client responsibilities, capability model, development phases, and product-level success criteria.
>
> It intentionally does **not** define executable API schemas, HTTP routes, MCP tool names, wire-protocol fields, storage file formats, exact timeout values, buffer sizes, or detailed acceptance procedures. Those belong in focused implementation specifications.

---

## 1. Product Definition

DUTchMate is a deterministic interface between software clients and a physical embedded Device Under Test (DUT).

Its purpose is to give both human developers and coding agents reliable access to the UART and configured hardware-control interfaces that embedded developers normally use while developing, debugging, testing, and diagnosing firmware.

At the product level DUTchMate provides three deterministic capabilities:

1. **Monitor** — observe UART evidence from the DUT through bounded observation workflows.
2. **Interact** — send UART data to the DUT and deterministically observe the resulting UART evidence.
3. **Control** — perform configured, bounded hardware-control actions when the selected backend supports them.

A later capability adds **hardware event observation** through generic event inputs.

These operations run on top of a more fundamental rule:

> **While DUTchMate owns an attached and connected backend, UART acquisition is continuous. Individual workflows are bounded windows and actions over that continuously acquired evidence stream; workflows do not start and stop the authoritative UART reader.**

This distinction is central to the product.

DUTchMate does not make AI part of the hardware-control path. A human, coding agent, test framework, or other client may decide **what** operation to request. DUTchMate owns **how** that operation executes according to explicit, deterministic rules.

The primary user-facing name is **DUTchMate**. The primary command-line command should be `dutchmate`; a short alias such as `dm` may be provided where appropriate.

---

## 2. The Problem DUTchMate Solves

UART remains one of the most common interfaces used during embedded firmware development.

Firmware frequently emits:

- boot messages;
- debug logs;
- assertions;
- fault information;
- runtime state;
- test progress and results;
- telemetry;
- shell prompts;
- command responses;
- crash diagnostics;
- application-specific debug information.

Many embedded applications also expose a bidirectional UART interface such as:

- a Zephyr shell;
- an application-specific CLI;
- diagnostic commands;
- manufacturing or validation commands;
- AT-style command interfaces;
- bootloader consoles;
- binary management or diagnostic protocols.

A human developer commonly works like this:

```text
build firmware
    -> flash DUT using an external tool
    -> observe UART
    -> reset or otherwise stimulate the DUT
    -> inspect boot/runtime output
    -> type a diagnostic command
    -> inspect the response
    -> modify firmware
    -> repeat
```

Coding agents can inspect and modify source code and can often invoke build and flash tools, but direct access to a physical DUT creates additional problems:

- who owns the serial port?;
- who keeps reading when no command is running?;
- what happens to spontaneous logs between commands?;
- how are TX and RX ordered?;
- where does a command-response window begin and end?;
- what if the DUT never responds?;
- what if it resets or disconnects?;
- what if an adapter buffer overflows?;
- what evidence existed before a failure?;
- who records what the client transmitted?;
- how are reset and boot signals controlled safely?;
- how does an external flash tool temporarily take the same serial port?;
- how does an agent avoid implementing timing-sensitive polling loops itself?;

Simply giving a coding agent `/dev/ttyUSB0` or a `pyserial` object does not answer those questions.

DUTchMate closes that gap by centralizing physical ownership, continuous acquisition, bounded workflows, hardware control, evidence recording, and provenance behind one deterministic service boundary.

---

## 3. Product Goals

DUTchMate should make the following embedded-development tasks reliable and reproducible.

### 3.1 Observe what the firmware is doing

A developer or coding agent should be able to inspect:

- startup and boot logs;
- debug messages;
- runtime logging;
- assertions and faults;
- spontaneous asynchronous events;
- output that occurs long after an earlier command completed.

The user should not need to predict when an interesting event will happen in order for DUTchMate to record it.

### 3.2 Interact with firmware over UART

A developer or coding agent should be able to:

- send an exact payload;
- send text with explicit line-ending behavior;
- wait for one or more observable completion conditions;
- apply a finite timeout;
- inspect all UART evidence associated with the operation;
- distinguish a match, timeout, disconnect, rejection, or transport failure.

### 3.3 Control the DUT when hardware permits

A configured backend may allow DUTchMate to:

- reset the DUT;
- select a boot mode;
- wake the DUT;
- operate another explicitly configured control input.

Basic serial adapters may provide a limited form of control through serial modem-control lines such as DTR/RTS when supported and deliberately configured. Enhanced hardware provides generic dedicated control channels.

### 3.4 Preserve evidence

DUTchMate should make it possible to answer later:

- what did the DUT emit?;
- what did DUTchMate transmit?;
- what hardware action occurred?;
- when did the physical connection change?;
- was there a period when DUTchMate did not own or observe the transport?;
- what serial settings were used?;
- what timestamp source applied?;
- was loss observable?;
- was evidence truncated because of a local quota?;
- why did a bounded operation terminate?;

---

## 4. Intended Users and Clients

DUTchMate serves multiple clients, but those clients must share one deterministic Device Core behavior.

### 4.1 Human developer

A developer uses the CLI to:

- attach to a DUT;
- view live UART output;
- follow logs for as long as desired;
- use an interactive console when UART TX is allowed;
- perform bounded Monitor workflows;
- perform bounded Interact workflows;
- invoke configured control operations;
- release the physical transport to an external tool;
- reacquire it afterward;
- retrieve earlier evidence;
- inspect connection and operation history.

The CLI is the first acceptance surface for DUTchMate behavior.

### 4.2 Coding agent

A coding agent later accesses the same Device Core behavior through a machine-oriented interface such as MCP.

The coding agent should not need to:

- open the serial device directly;
- create its own background reader;
- decide when to sleep between reads;
- race another client for UART ownership;
- reconstruct reconnect history;
- guess which serial settings produced an observation;
- directly manipulate arbitrary GPIOs;
- understand the private wire protocol of an Enhanced Debug Helper.

The coding agent requests bounded operations and receives structured results plus evidence references.

### 4.3 Other clients

CI systems, dedicated HIL test programs, IDE integrations, or future tools may become clients of the same Device Core Service. They must not create a parallel definition of hardware behavior.

---

## 5. Core Principle: Deterministic DUT Interaction

The central product principle is **deterministic execution**.

A deterministic DUTchMate workflow is a bounded operation over an authoritative DUT evidence stream whose execution semantics—including applicable input or hardware action, observation boundaries, ordering, completion conditions, timeout behavior, terminal outcome, and evidence association—are owned by DUTchMate rather than improvised by the human or coding agent.

Deterministic execution does **not** mean that the DUT itself behaves deterministically.

For example, two executions of:

```text
sensor read
```

may legitimately produce:

```text
temperature=23.4
```

and later:

```text
temperature=23.7
```

DUTchMate does not promise identical DUT output. It promises that the requested workflow executes according to the same defined rules and that the observations are preserved accurately.

The boundary is:

```text
Client decides WHAT operation to request.
DUTchMate owns HOW the bounded operation executes.
DUT determines WHAT physically happens in response.
```

---

## 6. Continuous Acquisition, Bounded Workflows

This is a foundational product decision.

### 6.1 Continuous UART acquisition

While DUTchMate owns a connected backend, there is one authoritative UART receive path and it remains active continuously.

UART acquisition does **not** stop merely because no Monitor or Interact request is currently running.

Therefore this sequence must remain observable:

```text
12:00:00  DUT: READY
12:00:10  client starts Interact
12:00:10  TX: status\r\n
12:00:10  DUT: OK
12:00:11  Interact completes

           no workflow is running

12:00:41  DUT: HardFault
12:00:41  DUT: PC=0x08001234
```

The fault at 12:00:41 is still DUTchMate evidence because the physical backend remained connected and owned by DUTchMate.

### 6.2 Bounded workflows are windows over the stream

Monitor and Interact do not create independent serial readers.

They establish bounded logical windows over the continuously acquired stream.

Conceptually:

```text
continuous UART evidence
---------------------------------------------------------->

                 operation start cursor
                         |
                         v
... earlier RX ... | TX command | RX | RX | RX | prompt | ... later RX ...
                   ^                              ^
                   |______________________________|
                         operation evidence window
```

### 6.3 Why this matters

Continuous acquisition prevents evidence gaps between operations.

It avoids races such as:

```text
RESET
   [first boot bytes arrive here]
MONITOR starts
```

because the reader was already active before reset.

It also captures asynchronous failures that occur after a bounded command finishes.

### 6.4 Continuous does not mean unbounded storage

Acquisition may be continuous while storage remains bounded.

DUTchMate may apply:

- file/session quotas;
- retention limits;
- rolling storage;
- segment limits;
- other explicit bounded persistence mechanisms.

If evidence is dropped or truncated because a DUTchMate-owned quota is reached, that fact must be explicit. Silent loss is not acceptable.

---

## 7. Core Capability Model

DUTchMate is organized around three deterministic capabilities.

```text
                         DUTchMate
                            |
              +-------------+-------------+
              |             |             |
              v             v             v
           MONITOR        INTERACT       CONTROL
              |             |             |
           UART RX        UART TX/RX   configured action
              |             |             |
              +-------------+-------------+
                            |
                            v
                           DUT
```

A later Enhanced capability adds hardware event observation:

```text
DUT -> EVENTn -> DUTchMate -> client
```

`Follow` and `Console` are user-facing views built on these underlying capabilities and the continuous stream. They are not separate physical capabilities.

---

## 8. Monitor: Deterministic UART Observation

### 8.1 Purpose

Monitor represents a bounded observation request over the continuously acquired UART evidence stream.

Examples include:

- wait for a boot banner;
- wait for a shell prompt;
- capture the next five seconds of activity;
- wait for a known fault marker;
- observe until a requested condition appears;
- collect a bounded amount of UART evidence.

### 8.2 Deterministic monitoring

DUTchMate owns:

- the operation start cursor in the authoritative stream;
- completion-condition evaluation;
- the finite timeout or other bound;
- operation termination;
- disconnect handling;
- evidence-window association;
- terminal result construction.

The UART reader itself is already running.

### 8.3 Example

```text
MONITOR
    until: "READY"
    timeout: 10 seconds
```

Conceptually:

```text
continuous RX already active
        |
        v
mark Monitor start cursor
        |
        +---- "READY" observed ----> matched
        |
        +---- timeout -------------> timeout
        |
        +---- connection lost -----> disconnected/reconnecting according to contract
        |
        v
return bounded operation result + evidence reference
```

### 8.4 Monitor is not the only way to view UART

A developer who simply wants to watch live logs should not need to create repeated bounded Monitor operations. That is the purpose of `follow`, described later.

---

## 9. Interact: Deterministic Bidirectional UART Interaction

### 9.1 Purpose

Interact represents a bounded operation in which a client transmits data and observes the UART stream around that action.

Examples include:

- Zephyr shell commands;
- application CLI commands;
- diagnostic requests;
- self-tests;
- validation commands;
- configuration interfaces;
- AT-style commands;
- bootloader consoles;
- binary management or diagnostic protocols.

### 9.2 Definition

A deterministic bidirectional UART workflow is a bounded operation in which DUTchMate owns the precise UART TX action, operation start boundary, observation window, ordering, completion-condition evaluation, timeout, terminal outcome, and evidence association.

The continuously running UART reader remains authoritative before, during, and after the transaction.

### 9.3 Example

```text
INTERACT
    send: "tamp test run\r\n"
    until: "Test complete"
    timeout: 10 seconds
```

Conceptually:

```text
continuous RX already active
        |
        v
mark operation start cursor
        |
record and perform exact TX
        |
continue observing the same RX stream
        |
        +---- completion condition matched --> matched
        |
        +---- timeout ------------------------> timeout
        |
        +---- unrecoverable disconnect ------> disconnected
        |
        v
return terminal outcome + evidence reference
```

### 9.4 Why independent `send()` and `read()` are not enough

A coding agent should not have to implement:

```text
send command
sleep
read
if incomplete:
    sleep again
    read again
repeat
```

That moves timing-sensitive hardware behavior into the agent and makes results dependent on client implementation.

DUTchMate should provide small deterministic primitives so clients can request an intention such as:

> send these bytes and wait for this observable condition, with this finite timeout.

### 9.5 Asynchronous output remains evidence

DUTchMate must not assume that every byte after TX is a clean response to the command.

For example:

```text
periodic log
shell prompt
TX command
command echo
command output
asynchronous warning
shell prompt
```

All of these bytes are real UART evidence.

Interact may identify an evidence window, but it must not silently delete unrelated-looking data to manufacture a synthetic command response.

### 9.6 Multiple completion conditions

A bounded interaction may support multiple explicit terminal observations, for example:

```text
send "selftest\r\n"

wait for:
    "PASS"
    or "FAIL"

timeout:
    10 seconds
```

Device Core reports what matched. Higher-level clients decide what that means for the test or firmware.

---

## 10. Follow: Live Human Observation

A human developer needs a convenient replacement for opening a separate terminal program solely to watch UART.

Phase 1 should therefore provide a live follow mode conceptually equivalent to:

```text
dutchmate follow
```

`follow` subscribes to the already-running authoritative evidence stream.

```text
DUT -> backend -> Device Core continuous capture
                         |
                         +--> durable evidence
                         |
                         +--> live CLI follow subscriber
```

Important semantics:

- starting `follow` does not start physical UART acquisition;
- stopping `follow` does not stop physical UART acquisition;
- Ctrl-C or client disconnect stops the live subscriber only;
- evidence continues to be recorded while Device Core retains backend ownership;
- multiple read-only subscribers may be permitted if the implementation can do so without affecting ordering or ownership.

`follow` is intentionally human-oriented and may remain open until the user exits. This does not violate the rule that autonomous waits and finite workflows must be bounded.

---

## 11. Console: Live Human Bidirectional Use

A developer should not need to stop DUTchMate and open `minicom`, `screen`, `picocom`, or another serial terminal merely to type commands interactively.

Otherwise the developer will bypass Device Core and the evidence trail will become incomplete.

A Phase 1 interactive console should therefore be supported when UART TX is allowed by the active DUT policy.

Conceptually:

```text
human keyboard
     |
     v
CLI console -> Device Core TX -> DUT

DUT -> Device Core continuous RX -> CLI console display
                      |
                      +-> durable evidence
```

Console mode is a user interface over the same Device Core stream and TX mechanisms. It must not directly open the serial port from the CLI.

Every transmitted byte remains auditable.

Agent-facing MCP operations should remain bounded; MCP should not require an indefinitely open interactive terminal session in order to use DUTchMate effectively.

---

## 12. Control: Deterministic Hardware Control

### 12.1 Purpose

Some debugging workflows require physical control in addition to UART.

Examples include:

- reset;
- boot-mode selection;
- wake;
- enable;
- application-specific control input.

### 12.2 Deterministic control

DUTchMate owns:

- capability validation;
- profile/configuration validation;
- policy validation;
- allowed electrical semantics;
- timing of the control sequence;
- finite bounds;
- safe-state handling where applicable;
- action recording;
- explicit success or failure reporting.

Clients request a configured semantic action rather than inventing arbitrary electrical pulse sequences dynamically.

### 12.3 Two physical forms of control

Control may come from two different physical mechanisms.

#### Basic serial-line control

Some USB-to-UART adapters expose serial modem-control lines such as:

```text
DTR
RTS
```

When the adapter, driver, wiring, and DUT profile explicitly support it, these lines may implement limited semantic control such as reset or boot-mode selection.

This is **not** general GPIO control.

The capability should be represented distinctly from dedicated Debug Helper GPIO control.

#### Enhanced generic control channels

The Enhanced Debug Helper may expose generic outputs such as:

```text
CTRL0
CTRL1
CTRL2
CTRL3
```

Host-side configuration maps these physical channels to DUT-specific roles such as reset, boot, or wake.

The Debug Helper firmware itself remains generic.

---

## 13. DTR/RTS and Serial-Open Side Effects

Opening a serial device is not always physically passive.

Many operating-system serial APIs and USB-UART drivers change DTR or RTS state when a port is opened. On common development boards those lines may be connected to reset or boot-mode circuitry.

Therefore a supposedly receive-only UART connection can unintentionally change DUT state unless line behavior is explicitly controlled.

DUTchMate must distinguish:

```text
UART payload direction:
    RX
    TX

serial adapter control lines:
    DTR
    RTS
```

### 13.1 Product-level rule

`Monitor` is **receive-only at the UART payload level**. It does not intentionally transmit UART bytes or intentionally perform a configured DUT control action.

However, the product must not claim that opening every serial adapter is electrically passive.

The active DUT profile must define intended DTR/RTS behavior where the platform exposes those lines. Device Core should apply and record the effective behavior as reliably as the platform permits.

If the host driver or adapter cannot guarantee a glitch-free open transition, that limitation should be represented honestly rather than hidden.

### 13.2 Explicit control through DTR/RTS

If DTR/RTS are intentionally used for reset or boot selection, that behavior must be configured as a semantic control mapping and treated as a hardware-changing operation.

It must not happen merely as an accidental consequence of opening the port.

---

## 14. Hardware Event Observation

Hardware event observation is the physical counterpart to UART monitoring.

A future Enhanced Debug Helper may expose generic event channels such as:

```text
EVENT0
EVENT1
EVENT2
EVENT3
```

Host-side roles may assign project meaning such as:

- interrupt output;
- ready signal;
- fault signal;
- wake indication;
- custom application event.

Event evidence should eventually follow the same principles as UART evidence:

- one authoritative capture path;
- explicit timestamp provenance;
- ordered evidence;
- explicit overflow/loss semantics;
- durable recording;
- bounded waits when used as workflow completion conditions.

---

## 15. UART Is a Byte Stream First

DUTchMate must not assume UART traffic is always human-readable text.

The authoritative representation is the exact UART byte stream admitted by the system.

```text
UART bytes                    authoritative evidence
     |
     +--> decoded text        derived view
     |
     +--> reconstructed lines derived view
     |
     +--> pattern matches     derived observation
     |
     +--> summaries           derived interpretation
```

If invalid UTF-8 or binary content appears, the raw bytes remain available even when the display representation is lossy.

This permits DUTchMate to support both ordinary text shells and arbitrary binary diagnostic/management protocols without building protocol-specific semantics into Device Core.

---

## 16. UART Transmission Semantics

UART TX must be explicit and auditable.

Device Core should fundamentally transmit bytes.

User-facing text interfaces may provide convenience transformations such as:

```text
none
LF
CR
CRLF
```

but the resulting exact transmitted bytes must be knowable.

DUTchMate must not silently append line endings or perform invisible payload transformations.

Binary transmission must remain possible at the Device Core level even if early CLI commands optimize for text workflows.

---

## 17. Serial Configuration

A UART observation has little value without knowing how the serial connection was configured.

The active DUT profile must define the intended serial configuration and each connection segment must preserve the effective settings used.

At minimum provenance should include applicable values for:

- baud rate;
- data bits;
- parity;
- stop bits;
- hardware flow control;
- software flow control;
- DTR behavior where relevant;
- RTS behavior where relevant.

Additional backend-specific parameters may also be recorded when they materially affect interpretation.

DUTchMate must not claim that configured settings are physically correct for the DUT merely because the host accepted them. It records the configuration that produced the evidence.

For example, bytes received at the wrong baud are still observed bytes, but their provenance must make the configuration clear.

---

## 18. DUT Profile

DUTchMate needs a first-class host-side **DUT Profile**.

The profile ties together the configuration required to interact with one physical/logical DUT consistently.

Conceptually a profile may contain:

```text
DUT Profile
|
+-- identity / human-readable name
|
+-- backend selection
|    +-- Basic / Enhanced
|    +-- device selector / expected identity
|
+-- UART configuration
|    +-- baud
|    +-- data bits
|    +-- parity
|    +-- stop bits
|    +-- flow control
|
+-- serial control-line behavior
|    +-- DTR
|    +-- RTS
|
+-- permissions / policy
|    +-- UART TX allowed?
|    +-- configured control actions allowed?
|
+-- semantic control mappings
|    +-- reset -> DTR/RTS or CTRLn
|    +-- boot -> DTR/RTS or CTRLn
|    +-- wake -> CTRLn
|
+-- control electrical semantics
|
+-- reconnect / expected device identity information
|
+-- human convenience defaults
     +-- optional default line ending
```

The exact schema belongs in an implementation specification.

### 18.1 Profiles are configuration, not evidence

A profile may change over time. Historical evidence must not silently inherit the newest profile values.

When a connection segment begins, DUTchMate should preserve the relevant **effective configuration snapshot** in provenance.

Conceptually:

```text
DUT Profile
     |
     v
configure backend
     |
     v
Connection Segment
     |
     +--> immutable/effective provenance snapshot
     |
     v
Evidence
```

---

## 19. Policy and Permissions

The term **policy** means human-owned configuration that determines which potentially state-changing DUTchMate operations clients are permitted to request for a DUT profile.

The policy is not chosen dynamically by an LLM and MCP does not bypass it.

### 19.1 Conservative default

A new or insufficiently configured DUT profile should default to observation-oriented behavior.

A suitable product-level default is:

| Capability | Default |
|---|---|
| UART RX / continuous acquisition | enabled when connected |
| UART evidence recording | enabled |
| UART TX | disabled until explicitly allowed |
| DTR/RTS semantic control | unavailable until explicitly configured |
| Enhanced CTRL semantic control | unavailable until explicitly configured |
| arbitrary public GPIO manipulation | unavailable |

This preserves Monitor as the safest initial use while allowing Interact and Control after explicit human configuration.

### 19.2 Policy does not replace electrical safety

Software permission does not guarantee that an attached cable, adapter, voltage level, or external circuit is electrically safe.

Policy governs what DUTchMate is allowed to request, not whether the physical setup is inherently safe.

---

## 20. Completion Conditions and Pattern Matching

Patterns are deterministic observation tools, not AI interpretation.

They may answer questions such as:

- has the boot banner appeared?;
- did a shell prompt return?;
- did the DUT emit a known fault marker?;
- did a bounded self-test emit one of its terminal strings?;

Pattern matching operates on explicitly defined derived representations such as complete lines or bounded text/byte windows.

The exact matching model—including encoding, line reconstruction, regex support if any, limits, overlap rules, and incomplete-line behavior—belongs in the implementation specification.

Patterns must never replace the underlying raw evidence.

---

## 21. Timeouts and Other Bounds

Autonomous operations that wait for the DUT must be bounded.

A DUT may:

- hang;
- crash;
- never emit the requested prompt;
- reboot unexpectedly;
- disconnect;
- produce continuous output;
- respond more slowly than expected.

Therefore:

```text
wait until "READY"
```

must have a finite timeout or another explicit finite bound.

Timeout is a normal workflow outcome, not necessarily an internal DUTchMate error.

Human-controlled `follow` or `console` modes may remain active until the user exits because the human is directly controlling their lifetime. That does not permit an agent-facing bounded workflow to wait forever.

---

## 22. Evidence Model

DUTchMate is both an interaction system and an evidence system.

Evidence may include:

- exact UART RX bytes;
- UART TX actions;
- timestamps;
- timestamp provenance;
- serial configuration provenance;
- decoded text;
- reconstructed lines;
- detected patterns;
- control actions;
- DTR/RTS actions;
- connection/disconnection events;
- release/reacquire events;
- reconnect boundaries;
- unobserved ownership gaps;
- overflow/loss telemetry where observable;
- local truncation information;
- future GPIO events;
- operation start/end markers;
- operation terminal outcomes.

The distinction between **evidence** and **interpretation** is fundamental.

```text
Evidence:
    UART emitted "HardFault"

Interpretation:
    firmware probably dereferenced an invalid pointer
```

Device Core owns the first. Humans, coding agents, or optional analysis components may produce the second.

Raw evidence must never be replaced by a summary.

---

## 23. Evidence Stream, Operations, Segments, and Sessions

These concepts must remain distinct.

### 23.1 Evidence stream

The evidence stream is the logical ordered history observed by Device Core while it owns the DUT/backend.

It includes ambient UART output even when no finite workflow is running.

### 23.2 Operation

An operation is a bounded logical action or observation over the evidence stream, for example:

- Monitor until pattern;
- Interact with command and completion condition;
- reset;
- boot-mode control.

An operation references evidence rather than owning a separate serial reader.

### 23.3 Connection segment

A connection segment represents an uninterrupted physical observation context with stable effective provenance.

A new segment is required when events such as these materially change the physical observation context:

- disconnect/reconnect;
- explicit release/reacquire;
- transport identity change;
- timestamp origin reset;
- configuration change requiring reconnection;
- other implementation-defined provenance boundary.

### 23.4 Session

A session is a durable, bounded container for evidence associated with a development/debugging run.

A session may contain:

- ambient UART evidence between operations;
- multiple bounded operations;
- one or more connection segments;
- control actions;
- reconnect/release boundaries;
- operation results;
- derived observations.

The implementation specification defines exact lifecycle, file format, quota, rollover, retention, and cursor behavior.

The product requirement is that **bytes observed between operations are not discarded merely because no operation was active**.

---

## 24. Evidence Quality and Loss

DUTchMate must distinguish what it knows from what it cannot observe.

A generic USB-to-UART adapter often cannot report whether bytes were lost upstream inside the adapter, USB stack, or before host observation.

An Enhanced Debug Helper may be able to report its own RX ring-buffer overflow or dropped-byte counters.

Those are different evidence qualities.

DUTchMate should distinguish concepts such as:

- loss observed by an available observer;
- no loss reported within that observer's scope;
- upstream loss not observable;
- local evidence dropped/truncated because a configured quota was reached;
- transport interruption;
- explicit ownership gap while released;
- incomplete derived-line processing.

`no loss reported` must never be represented as proof that the entire physical path was lossless.

---

## 25. Timestamp Provenance

Different backends observe UART at different points in the path.

For example:

```text
Basic:
DUT -> UART adapter -> USB -> OS -> Device Core observation

Enhanced:
DUT -> RP2350 UART -> helper timestamp -> USB -> Device Core
```

A Basic timestamp may represent host observation of a received chunk.

An Enhanced timestamp may represent observation in the Debug Helper using its device timer.

DUTchMate must preserve that provenance and must not present these timestamp domains as equivalent physical measurements.

Connection/reconnect boundaries may create new timestamp origins. Evidence across such boundaries must not be compared as if one continuous clock existed unless a future contract explicitly establishes such a relationship.

---

## 26. Connection Ownership

Exactly one component may own the active physical backend at a time.

CLI, MCP, and other clients do not independently open the serial device or Debug Helper.

Conceptually:

```text
CLI --------+
             |
MCP ---------+--> Device Core Service --> selected backend --> DUT
             |
other client-+
```

The service owns:

- backend open/close lifecycle;
- the authoritative UART reader;
- continuous acquisition;
- TX serialization;
- control serialization;
- reconnect behavior;
- evidence recording.

However, **single ownership does not mean permanent ownership**.

External tools sometimes legitimately need the same physical serial device.

---

## 27. Release and Reacquire for External Tools

Some external tools use the same port DUTchMate would normally own.

Examples include:

- `esptool` using a USB-UART adapter;
- a serial bootloader;
- vendor recovery/programming tools that require that transport;
- other protocol-specific tools.

DUTchMate must provide an explicit ownership handoff model.

Conceptually:

```text
DUTchMate owns backend
       |
       v
continuous capture
       |
       v
explicit RELEASE
       |
       +--> current connection segment closes
       +--> evidence records release boundary
       |
       v
external tool owns port
       |
       +--> DUTchMate cannot observe this interval
       |
       v
explicit or policy-driven REACQUIRE
       |
       +--> backend reopened
       +--> effective profile applied
       +--> new connection segment begins
       |
       v
continuous capture resumes
```

The ownership gap must be explicit evidence/provenance. DUTchMate must not pretend to know what happened on UART while another process owned the transport.

### 27.1 Independent flash transports

If firmware is flashed through an independent interface such as SWD/JTAG while DUTchMate owns a separate UART adapter, DUTchMate should remain connected whenever practical.

That permits capture of reset and earliest UART output without an ownership gap.

DUTchMate should not require release merely because an external tool is running; release is required only when the tool needs the same physical resource.

---

## 28. Connection Lifecycle

At the product level the service should distinguish states equivalent to:

```text
DETACHED
    |
    v
ATTACHING
    |
    v
CONNECTED / CONTINUOUS ACQUISITION
    |
    +--> transient disconnect --> RECONNECTING --> CONNECTED/new segment
    |
    +--> explicit RELEASE --> RELEASED --> REACQUIRE --> CONNECTED/new segment
    |
    +--> detach/stop --> DETACHED
```

Exact state names belong in the implementation specification.

The important product guarantees are:

- physical ownership is explicit;
- observation gaps are explicit;
- connection boundaries are preserved;
- continuous acquisition resumes whenever ownership and connectivity are restored.

---

## 29. Reconnects and Native USB Consoles

Not all serial topologies behave the same way during reset.

### 29.1 External USB-to-UART adapter

```text
Host -> USB-UART adapter -> DUT UART
```

Resetting the DUT usually does not remove the host serial device because the adapter remains powered and enumerated.

This topology is well suited to capturing boot output from the earliest UART activity after reset.

### 29.2 Native USB serial console

Some DUTs expose their console directly as USB CDC/ACM or another native USB serial function:

```text
Host -> USB -> DUT MCU
```

Reset may therefore cause:

```text
reset
  |
USB serial device disappears
  |
Device Core sees disconnect
  |
DUT boots
  |
USB firmware initializes
  |
device re-enumerates
  |
Device Core reconnects
```

For such a DUT, reset and reconnect are inherently coupled.

DUTchMate must preserve this as a segment boundary rather than pretending the transport remained continuous.

It must also acknowledge a physical limitation:

> UART/console output produced before the DUT reinitializes its native USB interface cannot be captured through that same interface.

A reset workflow may treat the disconnect/reconnect as expected behavior when the active profile/topology declares it, rather than automatically treating every disconnect as a fatal operation failure.

The exact reconnect matching rules belong in the implementation specification.

---

## 30. Single DUT per Service Instance

Phase 1 should keep service ownership deliberately simple:

> **One Device Core Service instance manages at most one active DUT profile and one physical backend at a time.**

Conceptually:

```text
Device Core Service
        |
        v
one active DUT Profile
        |
        v
one selected backend
        |
        v
one DUT
```

The service may expose historical evidence from that DUT's sessions, but it does not multiplex several simultaneously active DUTs in Phase 1.

Running multiple independent service instances for separate DUTs may be possible operationally, but multi-DUT orchestration is not a Phase 1 Device Core responsibility.

This keeps ownership, concurrency, session semantics, reconnect behavior, and later MCP tool semantics tractable.

---

## 31. Device Core

Device Core is the deterministic heart of DUTchMate.

It is responsible for concepts such as:

- DUT profile application;
- backend lifecycle;
- connection ownership;
- release/reacquire;
- continuous UART acquisition;
- capability validation;
- serial configuration;
- UART TX;
- Monitor workflows;
- Interact workflows;
- configured Control workflows;
- backend event normalization;
- ordering;
- bounded waits;
- timeout behavior;
- pattern detection;
- connection segments;
- session/evidence recording;
- evidence retrieval;
- reconnect semantics;
- explicit result/failure models.

Device Core must not depend on:

- a CLI framework;
- HTTP framework semantics;
- MCP;
- an LLM provider;
- coding-agent behavior.

The same deterministic behavior must be reusable by all client surfaces.

---

## 32. Device Core Service

The Device Core Service provides process-level ownership and a common client boundary around Device Core.

Its responsibilities include:

- owning at most one active DUT/backend;
- keeping the backend connection alive independently of short CLI invocations;
- keeping continuous acquisition active while connected;
- arbitrating TX and control operations;
- supporting live follow/console subscribers;
- exposing bounded workflows;
- maintaining evidence/session state;
- applying reconnect rules;
- exposing release/reacquire lifecycle;
- providing a common API for CLI and later MCP.

The service must not embed AI reasoning.

A default deployment should remain local to a trusted developer machine. Remote/shared deployment requires a separate authentication/authorization design.

---

## 33. CLI: First Acceptance Surface

The CLI is the first product surface on which DUTchMate behavior is validated.

Before a workflow is exposed to a coding agent through MCP, a human developer should be able to invoke and inspect it directly through the CLI.

The CLI remains a thin client of Device Core Service. It must not independently open the DUT serial port.

Phase 1 CLI functionality should cover product concepts such as:

- attach/start with a DUT profile;
- inspect status/capabilities;
- live `follow` of continuously captured UART;
- interactive console when TX policy allows;
- bounded Monitor;
- bounded Interact;
- configured Control;
- retrieve evidence/session history;
- release the backend for an external tool;
- reacquire the backend afterward;
- clearly present disconnect/reconnect/release boundaries.

Exact command names are implementation details and may differ.

---

## 34. MCP and Coding-Agent Access

MCP is introduced after the corresponding Device Core + CLI workflows are proven.

The MCP server is a thin machine-facing client of the Device Core Service.

It should not:

- own the serial port;
- create a second background UART reader;
- implement a separate hardware-control model;
- silently broaden DUT policy;
- bypass release/reacquire ownership rules;
- invoke an LLM merely to execute deterministic operations;
- replace evidence with interpretation.

Its purpose is to expose already-validated operations such as:

- inspect capabilities/status;
- bounded Monitor;
- bounded Interact;
- configured Control;
- retrieve evidence;
- inspect operation/session state.

MCP should normally use bounded operations rather than an indefinitely open terminal abstraction.

---

## 35. Basic Backend

Basic mode uses a user-selected host serial device, typically a TTL/logic-level USB-to-UART adapter or a native USB serial console presented as a normal serial port.

The design should remain vendor-independent.

Typical Basic capabilities are:

| Capability | Basic |
|---|---|
| UART receive | Yes |
| Continuous UART acquisition while connected | Yes |
| UART transmit | Optional; enabled by DUT policy |
| Deterministic Interact | Yes when TX is allowed |
| Host-side timestamp provenance | Yes |
| Standardized adapter overflow telemetry | Usually no |
| DTR/RTS observation/control | Optional, adapter/driver dependent |
| Semantic reset/boot via DTR/RTS | Optional, profile-configured |
| General-purpose GPIO control | No |
| GPIO event capture | No |

The user remains responsible for correct electrical connection, including:

- compatible voltage levels;
- common ground where required;
- correct TX/RX wiring;
- any required level translation;
- avoiding true RS-232 voltage levels on logic-level DUT pins.

Software TX policy is not proof that an attached adapter's physical TX pin is electrically high impedance.

---

## 36. Enhanced Backend

Enhanced mode uses a dedicated DUTchMate Debug Helper connected between host and DUT.

Expected capabilities include:

- UART RX;
- UART TX;
- continuous UART acquisition;
- device-side timestamps;
- explicit receive-buffer/overflow telemetry;
- generic dedicated control outputs such as `CTRL0` through `CTRL3`;
- defined safe states;
- later generic event inputs such as `EVENT0` through `EVENT3`.

Conceptually:

```text
Host
  |
  | USB
  v
DUTchMate Debug Helper
  |
  +--> UART RX/TX ------ DUT
  |
  +--> CTRL0..CTRL3 ---- DUT inputs
  |
  +<-- EVENT0..EVENT3 -- DUT outputs   [later]
```

The Debug Helper firmware implements generic physical mechanisms, timestamps, buffering, and safe-state behavior. It does not encode project-specific meanings such as "STM32 reset pin."

Those meanings belong in the DUT profile.

---

## 37. One Backend at a Time

A DUT connection uses exactly one physical backend.

DUTchMate must not silently combine:

```text
UART from one generic adapter
+
control from a separate Debug Helper
```

unless a future architecture explicitly designs synchronization between those devices.

Using one backend avoids ambiguous:

- timestamp domains;
- connection ownership;
- ordering;
- reconnect semantics;
- evidence provenance.

Unsupported operations fail explicitly through capability checks.

---

## 38. Normalized Backend Boundary

Basic and Enhanced backends differ physically, but downstream Device Core behavior should consume normalized backend events and capabilities.

Conceptually:

```text
Basic serial implementation -----+
                                 |
                                 v
                           normalized events
                                 ^
                                 |
Enhanced helper protocol --------+
                                 |
                                 v
                    shared Device Core behavior
```

Backend-specific protocol details must terminate at the backend boundary.

Shared behavior such as:

- continuous evidence recording;
- raw-byte preservation;
- text projection;
- pattern detection;
- Monitor;
- Interact;
- session/evidence retrieval;
- API behavior;
- CLI presentation;
- MCP exposure;

should not branch unnecessarily on adapter vendor or private Enhanced protocol message type.

Real backend capability and provenance differences remain explicit.

---

## 39. Capability Model vs. Role Model

DUTchMate distinguishes **physical capability** from **DUT-specific semantic role**.

Capabilities describe what a backend can physically do, for example:

```text
uart_receive
uart_send
serial_line_control
gpio_control
gpio_events
```

Roles describe what an explicitly configured channel/action means for a particular DUT, for example:

```text
reset
boot
wake
power_enable
interrupt
ready
custom project role
```

For example:

```text
role: reset
mechanism: CTRL0
DUT signal: RESET_N
```

or on a Basic adapter:

```text
role: reset
mechanism: DTR
```

Device Core resolves configured semantic roles to supported backend mechanisms.

---

## 40. Combining Deterministic Capabilities

Useful debugging workflows often combine the fundamental capabilities.

For example:

```text
RESET
  |
  v
WAIT for UART "READY"
```

or:

```text
set boot mode
  |
reset
  |
wait for bootloader prompt
```

or:

```text
INTERACT
    send "selftest\r\n"
    wait for "PASS" or "FAIL"
```

Continuous UART acquisition means combined operations are **not required to avoid missing bytes between separately issued requests**. The bytes are already being recorded.

However, small atomic combined operations may still be valuable because they provide:

- one bounded intent;
- one operation result;
- clear timing between action and completion condition;
- simpler client orchestration.

Device Core should avoid evolving into a general-purpose scripting language. Complex loops, build logic, source modification, test plans, and multi-step strategies belong above Device Core unless a small bounded primitive proves broadly useful.

---

## 41. Concurrency and Serialization

UART is a shared sequential resource.

DUTchMate must prevent concurrent clients from creating ambiguous state-changing operations such as two command-response transactions transmitting into the same shell simultaneously.

Product-level expectations are:

- one authoritative RX path;
- RX continues continuously while connected;
- TX/action workflows are serialized according to explicit rules;
- control actions are serialized where necessary;
- read-only evidence retrieval may proceed concurrently;
- live follow subscribers may observe the stream without becoming hardware owners;
- console input must pass through Device Core arbitration;
- bounded workflows must receive stable operation boundaries/cursors even while ambient UART continues.

The precise locking/concurrency model belongs in the implementation specification.

---

## 42. Hardware Safety

DUTchMate interacts with physical electronics and must distinguish observation from state-changing actions.

Core safety principles include:

- validate backend capability before acting;
- validate active DUT profile before acting;
- apply human-owned policy;
- keep state-changing operations bounded;
- record state-changing actions;
- define safe control states;
- treat intentional DTR/RTS changes as control when they affect the DUT;
- do not expose unrestricted arbitrary GPIO manipulation merely because a backend can toggle pins;
- distinguish software permission from electrical safety;
- keep AI outside the deterministic physical-control path.

Future operations such as power switching, voltage changes, repeated automated reset loops, or other potentially disruptive actions require explicit design rather than being generalized automatically from existing Control semantics.

---

## 43. AI Boundary

DUTchMate may be used by AI coding agents, but Device Core itself is not an AI system.

The deterministic path is:

```text
requested operation
       |
       v
validated Device Core workflow
       |
       v
physical DUT interaction / observation
       |
       v
recorded evidence
```

AI reasoning happens above that boundary:

```text
recorded evidence
       |
       v
human / coding-agent analysis
       |
       v
hypothesis / source change / next requested operation
```

AI interpretation must never overwrite or replace the underlying evidence.

An AI may request another operation, but Device Core validates and executes it using the same policy and deterministic contract used for a human client.

---

## 44. External Tool Boundaries

DUTchMate should integrate with the embedded toolchain rather than replace it.

External tools remain appropriate for:

- firmware compilation;
- firmware flashing;
- JTAG/SWD debugging;
- GDB;
- vendor-specific core-dump decoding;
- logic analysis;
- oscilloscope measurements;
- protocol-specific host tools;
- complex test orchestration.

A common development loop may therefore be:

```text
coding agent / developer
    |
modify source
    |
build
    |
external flash tool
    |
DUTchMate continues/reacquires observation
    |
Monitor / Interact / Control
    |
inspect evidence
    |
modify source
    |
repeat
```

If the flash tool needs the same serial device, explicit release/reacquire is part of the loop.

If the flash tool uses another transport, DUTchMate should remain connected whenever practical.

---

## 45. Explicit Non-Goals

Unless introduced by a later explicit design, DUTchMate is not intended to be:

- a firmware compiler;
- a general firmware flashing framework;
- a JTAG/SWD debugger;
- a GDB server;
- an oscilloscope;
- a logic analyzer;
- a general-purpose workflow/scripting engine;
- a vendor-specific shell implementation;
- a vendor-specific bootloader implementation;
- an MCUmgr implementation;
- a replacement for specialized protocol host tools;
- a multi-DUT orchestration system in Phase 1;
- an autonomous AI hardware controller;
- a system that gives AI unrestricted GPIO manipulation;
- a guarantee that DUT firmware itself behaves deterministically;
- a guarantee of lossless physical UART transport when the selected backend cannot observe all loss points.

---

## 46. Development Strategy

DUTchMate should be developed in layers so that deterministic physical behavior is proven before coding-agent integration.

The broad sequence is:

```text
product semantics
       |
       v
Device Core contracts
       |
       v
Basic + Enhanced backend implementations
       |
       v
Device Core Service
       |
       v
CLI workflows and live developer UX
       |
       v
real-hardware acceptance
       |
       v
MCP exposure
       |
       v
optional higher-level AI analysis
       |
       v
advanced hardware evidence
```

The ordering principle is:

> **Define and validate deterministic DUT behavior through Device Core and CLI independently of AI before exposing the same behavior to a coding agent.**

---

## 47. Phase 1: Deterministic DUT Interaction Through CLI

Phase 1 establishes DUTchMate as a useful human-facing embedded development tool without requiring MCP or an LLM.

Phase 1 must prove the connection model, continuous evidence model, two primary UART use cases, and supported Control mechanisms through the CLI against real hardware.

### 47.1 Phase 1 connection foundation

A Phase 1 implementation should prove that:

- one service owns at most one active DUT/backend;
- the backend is opened with explicit DUT profile configuration;
- the effective serial settings are recorded;
- UART acquisition continues while the backend is connected;
- UART output between finite operations remains recorded;
- connection segments preserve reconnect/provenance boundaries;
- explicit release/reacquire works when an external tool needs the same port;
- ownership gaps are visible in evidence;
- native-USB reconnect behavior is represented honestly where applicable.

### 47.2 Use Case 1: UART Monitoring

A human developer can monitor a real DUT's UART output through DUTchMate.

Phase 1 monitoring includes both:

1. **live human observation** through `follow`; and
2. **bounded deterministic Monitor** workflows for conditions/timeouts.

The system must be able to:

- continuously capture UART while connected;
- expose live UART without bypassing Device Core;
- preserve exact raw evidence;
- preserve ambient output between operations;
- derive bounded text/line views where requested;
- detect explicit patterns;
- apply finite workflow bounds;
- distinguish timeout, disconnect, and other terminal states;
- persist and retrieve evidence;
- report relevant evidence-quality limitations.

### 47.3 Use Case 2: Bidirectional UART Interaction

A human developer can use the CLI to interact bidirectionally with a real DUT.

Phase 1 must support:

- exact UART TX;
- explicit line-ending convenience for text workflows;
- UART TX policy enforcement;
- interactive human console mode when TX is enabled;
- bounded Interact operations;
- completion-condition waits;
- finite timeouts;
- continued capture of asynchronous output;
- transmitted-action recording;
- evidence windows over the continuous stream;
- explicit terminal outcomes;
- evidence/session retrieval.

The developer must not need to coordinate sleeps, polling loops, or multiple serial readers.

### 47.4 Phase 1 Control

Phase 1 should support deterministic configured Control where the active backend provides it.

For Basic this may include configured reset/boot semantics through DTR/RTS if supported by the adapter/driver and DUT wiring.

For Enhanced this includes generic dedicated `CTRLn` channels and their configured semantic roles.

Control remains:

- capability-gated;
- profile-gated;
- policy-gated;
- bounded;
- auditable.

---

## 48. Phase 1 Success Criteria

Phase 1 succeeds when DUTchMate is independently useful to a human embedded developer through the CLI.

### Success Criterion A: continuous evidence foundation

With a real DUT connected, DUTchMate continuously acquires and records UART evidence for the lifetime of each connected ownership segment.

Evidence produced while no finite workflow is active remains available, subject only to explicit bounded retention/quota rules.

A spontaneous event such as a crash occurring after an earlier command completes is not lost merely because the client was idle.

### Success Criterion B: live UART monitoring

A user can run a live CLI follow view and observe the same UART stream Device Core is already recording.

Starting or stopping the live view does not start or stop physical acquisition.

The user can later retrieve the corresponding evidence independently of the terminal display.

### Success Criterion C: bounded UART monitoring

A user can request a bounded Monitor workflow against a real DUT and receive an explicit result such as condition matched, timeout, or connection-related termination.

The operation references authoritative UART evidence from the continuous stream and clearly communicates timing/provenance and evidence-quality limitations.

### Success Criterion D: bidirectional UART interaction

A user can send an exact UART payload to a real DUT and deterministically observe the resulting evidence until a configured completion condition or timeout.

The result communicates:

- exact TX bytes/action;
- relevant RX evidence;
- operation boundaries;
- completion match if any;
- terminal outcome;
- timestamp/configuration provenance;
- evidence reference.

No client-managed sleep/read loop is required.

### Success Criterion E: interactive human console

When UART TX is permitted, a human can use DUTchMate as an interactive UART console without directly opening the serial port in another terminal program.

Input still passes through Device Core policy and arbitration, and transmitted/received evidence remains recorded.

### Success Criterion F: deterministic configured control

Where supported by the active backend and DUT profile, the user can invoke accepted semantic control operations and receive explicit auditable results.

This may include limited DTR/RTS-based control in Basic mode and generic `CTRLn`-based control in Enhanced mode.

### Success Criterion G: ownership handoff

When an external tool needs the same serial transport, a user can explicitly release the backend, run that tool, and reacquire the backend.

DUTchMate records the ownership boundary and represents the released interval as unobserved rather than inventing continuity.

### Success Criterion H: common client semantics

Monitor and Interact retain the same client-level meaning across Basic and Enhanced backends where the required physical capabilities exist.

Backend differences such as timestamp source, overflow telemetry, serial control lines, and dedicated GPIO capability remain explicit rather than leaking private transport details into every client workflow.

At this point DUTchMate is useful independently of MCP or AI.

---

## 49. Phase 2: MCP Integration

Phase 2 exposes the deterministic Device Core workflows already validated in Phase 1 to coding agents.

The MCP layer should provide a bounded tool set for concepts such as:

- inspect connection/backend capabilities;
- inspect active profile/status;
- bounded Monitor;
- bounded Interact;
- invoke allowed configured Control;
- retrieve evidence;
- inspect operation/session state.

MCP should not redefine the semantics of Monitor, Interact, Control, ownership, or evidence.

The coding agent uses the same continuously recorded physical evidence stream indirectly through bounded Device Core operations and evidence retrieval.

---

## 50. Phase 2 Success Criteria

Phase 2 succeeds when a coding agent can perform the same deterministic DUT interactions already proven through the CLI without manually operating a serial terminal.

A coding agent can:

1. inspect current backend/profile capability;
2. request bounded UART monitoring;
3. retrieve authoritative evidence;
4. send UART data and wait for explicit conditions/timeouts;
5. invoke allowed configured Control operations;
6. distinguish connection/reconnect/release boundaries;
7. understand relevant evidence-quality and provenance information;
8. operate entirely through Device Core semantics rather than directly opening the serial device.

The coding agent receives no privileged bypass around DUT policy, physical ownership, timeout, safety, or evidence rules.

---

## 51. Later: Optional AI Analysis

Higher-level analysis may consume bounded DUTchMate evidence to help debug firmware.

Possible functions include:

- summarize a session;
- classify a failure;
- compare current evidence with a baseline;
- correlate source excerpts with observed logs;
- suggest a next diagnostic operation.

Such analysis remains advisory.

It must preserve:

- provenance;
- uncertainty;
- the distinction between evidence and inference;
- the deterministic Device Core boundary.

---

## 52. Later: Advanced Hardware Evidence

Enhanced hardware may later add capabilities such as:

- GPIO/event edge capture;
- event-role configuration;
- synchronized UART/event evidence within documented limits;
- additional UART channels;
- power-control mechanisms;
- power/current/voltage measurement;
- other target-observation mechanisms.

Each candidate capability should be evaluated against the same questions:

- does it materially improve firmware debugging or DUT control?;
- can its behavior be bounded?;
- can its evidence provenance be represented accurately?;
- can it be exposed safely to human and coding-agent clients?;
- does it belong in Device Core or in an external specialist tool?

---

## 53. Engineering Invariants

The following rules define the intended long-term product architecture.

1. **Device Core is deterministic and AI-independent.**
   AI reasoning is not required to execute Monitor, Interact, Control, connection, session, or evidence behavior.

2. **CLI validates workflows before MCP exposure.**
   MCP exposes proven Device Core behavior; it does not define a parallel hardware model.

3. **One service instance owns at most one active DUT/backend in Phase 1.**
   Multi-DUT orchestration is a separate future concern.

4. **There is one authoritative physical owner at any instant.**
   CLI, MCP, and other clients never independently open the same backend while Device Core owns it.

5. **Single ownership has an explicit release/reacquire escape hatch.**
   External tools may temporarily own the transport, and DUTchMate records the resulting observation gap.

6. **UART acquisition is continuous while DUTchMate owns a connected backend.**
   Finite workflows do not start and stop the authoritative reader.

7. **Finite workflows are bounded windows/actions over the continuous evidence stream.**
   Monitor and Interact reference evidence rather than creating competing RX paths.

8. **Ambient UART output remains evidence.**
   Bytes received between operations are preserved subject to explicit retention/quota rules.

9. **UART bytes are authoritative evidence.**
   Text, lines, patterns, summaries, and AI interpretations are derived representations.

10. **UART remains binary-safe.**
    Human-readable text is an important use case, not a transport assumption.

11. **Finite autonomous waits are bounded.**
    Waiting for firmware output requires an explicit finite timeout or equivalent bound.

12. **DUTchMate owns timing-sensitive transaction mechanics.**
    Clients should not need arbitrary sleeps and polling loops to implement command/response behavior.

13. **Asynchronous UART output remains evidence.**
    DUTchMate does not fabricate a clean command response by silently deleting unrelated output.

14. **TX behavior is explicit.**
    Exact transmitted bytes and text transformations are knowable and auditable.

15. **Serial configuration is provenance.**
    Effective baud/framing/flow-control and relevant control-line behavior are recorded for each connection context.

16. **A DUT Profile is the human-owned configuration root for a DUT.**
    Backend selection, serial settings, policy, device identity expectations, and semantic control mappings belong there or in clearly associated configuration.

17. **Historical evidence snapshots effective configuration.**
    Changing a DUT Profile later does not rewrite the meaning of earlier evidence.

18. **UART TX is disabled by default until explicitly allowed for the DUT profile.**
    Observation is the safe default.

19. **DTR/RTS behavior is explicit where relevant.**
    Serial-open side effects must not be silently treated as passive observation.

20. **Basic control through DTR/RTS is limited and explicit.**
    It is not equivalent to general-purpose GPIO control.

21. **Enhanced hardware control is semantic, configured, capability-gated, bounded, and auditable.**
    Public clients do not receive unrestricted pin-level control by default.

22. **Physical capabilities and semantic roles remain separate.**
    Generic Debug Helper firmware does not encode DUT-specific meanings.

23. **One physical backend is selected for a DUT connection.**
    Cross-device hybrid composition requires a separate future synchronization design.

24. **Backend-specific protocol details terminate at the normalized backend boundary.**
    Shared Device Core workflows do not depend on private Enhanced framing or adapter vendor details.

25. **Evidence quality is explicit.**
    Unknown loss is not reported as proven losslessness.

26. **Timestamp provenance is explicit.**
    Host-observation and device-observation timestamps are not represented as equivalent measurements.

27. **Reconnects preserve physical boundaries.**
    A changed physical connection or timestamp origin creates an explicit segment/provenance boundary.

28. **Native USB console disappearance is a legitimate reconnect case.**
    Reset-related transport loss may be expected for configured topologies, and pre-enumeration output may be physically unobservable.

29. **Sessions are bounded and durable.**
    Continuous acquisition does not imply unbounded persistence.

30. **Hardware-changing operations are recorded.**
    A later investigator can distinguish DUT output from DUTchMate actions.

31. **Human live views do not bypass Device Core.**
    `follow` and interactive console use the same authoritative connection and evidence path.

32. **Stopping a live view does not stop evidence acquisition.**
    Capture lifetime follows backend ownership, not terminal lifetime.

33. **AI interpretation never replaces evidence.**
    Raw and structured evidence remain independently retrievable.

34. **DUT behavior is not claimed to be deterministic.**
    DUTchMate guarantees deterministic workflow execution within its documented observation/control boundaries.

35. **Complex orchestration stays above Device Core unless a small bounded primitive is broadly useful.**
    DUTchMate does not become a general scripting language.

36. **External specialist tools remain external where appropriate.**
    Build, flash, JTAG/SWD, GDB, oscilloscopes, logic analyzers, and protocol-specific tools are not reimplemented without a clear product reason.

37. **Unsupported operations fail explicitly.**
    DUTchMate does not silently emulate unavailable capabilities or weaken guarantees without telling the client.

38. **Implementation contracts may evolve without changing these product boundaries.**
    API names, schemas, protocol framing, quotas, exact timing limits, storage details, and CLI spelling belong in focused specifications.

---

## 54. Product Summary

DUTchMate is a deterministic bridge between software and a physical embedded DUT.

Its connection-level model is:

```text
one Device Core Service
        |
one active DUT Profile
        |
one owned backend
        |
continuous UART acquisition
        |
authoritative evidence stream
```

Its primary UART use cases are:

```text
MONITOR
bounded observation over the continuous UART stream

INTERACT
bounded TX + observation over the same continuous UART stream
```

Human developer UX additionally includes:

```text
FOLLOW
live read-only view of the same stream

CONSOLE
live human TX/RX through Device Core when policy allows
```

Hardware control is:

```text
CONTROL
configured semantic action
    |
    +--> optional Basic DTR/RTS mechanism
    |
    +--> Enhanced CTRLn mechanism
```

Future hardware observation adds:

```text
EVENT OBSERVATION
DUT -> EVENTn -> Debug Helper -> Device Core -> client
```

The defining boundaries are:

> **Connection/evidence lifetime is continuous while DUTchMate owns the connected backend. Workflow lifetime is bounded.**

> **The client chooses the operation. DUTchMate executes the interaction deterministically and preserves the evidence.**

Phase 1 proves this model through the CLI against real hardware, including live developer use, bounded monitoring, bidirectional interaction, configured control, provenance, reconnect behavior, and explicit ownership handoff.

Phase 2 exposes the same proven Device Core workflows through MCP so coding agents can interact with a physical DUT without manually operating a serial terminal or implementing timing-sensitive serial coordination themselves.

AI reasoning may assist debugging above this boundary, but it does not replace Device Core, control hardware directly, or replace recorded evidence.
