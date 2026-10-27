# Reconnect and Session Semantics

> Scope: current continuous evidence ownership and segment provenance.
> Normative authority: [Phase 1 specification](phase1_implementation_spec.md),
> especially sections 13–16, 18–25, and 26. Implementation ownership is described
> in [Software Architecture](software_architecture.md).

## Ownership and evidence lifetime

Device Core owns one physical connection and one authoritative receive path.
`ContinuousEvidenceRecorder` persists UART and telemetry even when no Monitor,
Interact, follow, or console client is active. Bounded operations observe durable
ranges; completing or cancelling them does not close the continuous journal.
All newly created sessions and evidence writes use schema v2.

The connection states are `disconnected`, `connecting`, `connected`,
`reconnecting`, `released`, `reacquiring`, and `faulted`. Status reports the active
session, active operations, remaining reconnect time, capabilities, provenance,
and bounded connection diagnostics. A journal can remain active while ownership
is released. Journal lifecycle and connection state are distinct facts.

## Segments and timestamps

A connection establishes one immutable normalized source context. Each accepted
reconnect/reacquire creates a new segment, even if the physical device clock
appears continuous. Source-local segment IDs are rebased by the recorder into
contiguous journal-local IDs; old sources are never rebound.

Each segment retains backend identity, raw/effective capabilities, policy,
effective serial configuration, and timestamp provenance. Basic uses a host
monotonic timestamp per serial-read chunk; Enhanced uses the RP2350 timer per
firmware UART event. The first timestamped Enhanced event can establish its
origin without being consumed by startup. All normalized times are relative to
that segment's source origin. Wall times describe lifecycle facts; they do not
establish primary evidence ordering. `evidence_seq` orders evidence within a
session, and explicit successor links establish rollover continuity.

No line or pattern joins bytes across segment or rollover boundaries. Partial
and oversized lines close explicitly. Basic loss remains `not_observable`;
Enhanced telemetry reports only the Debug Helper RX-buffer observer scope.
Continuity, local persistence, line processing, and observed loss remain separate.

## Unexpected disconnect and reconnect

Already-normalized events drain before the old source reports disconnect. A
receive timeout does not create a boundary. Malformed Enhanced input is a fatal
`backend_input_error`, distinct from timeout and transport loss.

The continuous recorder persists `unexpected_disconnect`, closes the segment,
and records an observation gap. The service coordinator closes the old source,
records reconnect start, and retries within the profile's monotonic reconnect
window. Replacement identity/settings and timestamp provenance must validate
before publication. The recorder then admits the new segment and reconnect
result before receiving from the replacement. Exactly one physical reader owns
each connection; operations cannot initiate their own reconnect attempts.

For a new Enhanced helper epoch, the persisted segment precedes required Profile
GPIO initialization, and `reconnect_succeeded` / `reacquire_succeeded` follows
its acknowledgements. The runtime invalidates previous physical acceptance and
uses the same validated, audited `GpioConfigurator` path as startup. Each new
acknowledgement supplies fresh host/device acceptance metadata. The immutable
Profile remains the desired source; runtime overrides do not carry old physical
acceptance into another helper epoch. No role or DUT-signal metadata is sent on
the wire. Basic has no additional initialization.

While initializing, public state remains `reconnecting` or `reacquiring` and
does not advertise prior accepted controls as configured. The candidate's
existing Enhanced owner buffers normalized input until recorder handoff; input
buffered by successful initialization is then durably admitted in the new
segment. No additional physical reader is created. GPIO initialization waits
for submitted mutations without holding the recorder's admission lock. An
Interact retains its exclusive operation lease while observing, but holds the
mutation lock only for TX, so initialization can proceed without resending TX.

Deadline/cancellation checks run while waiting for mutation ownership, before
each configuration command and before final success publication. Required
configuration rejection/timeout faults the new ownership attempt, preserves the
actual control result and lifecycle failure, and does not publish success.
The service coordinator closes the unpublished candidate. Failed close retains
an explicit cleanup-unconfirmed ownership fault; known initialization failures
are not misreported as successful reconnects or silently retried as fresh
configuration attempts. No reconnect deadline is extended.

Enhanced stream cleanup confirms both that the retained serial resource reports
`is_open == False` and that the transport has released its serial reference.
`is_closing()` or completion of the protocol close waiter alone is insufficient.
Asyncio may deliver the same terminal read exception again through
`wait_closed()`: that exact, previously observed exception does not represent
cleanup uncertainty when both physical-closure checks pass. The original backend
read error and its cause remain authoritative. A different close exception,
missing/uninspectable resource, still-owned transport or incomplete close retains
blocking cleanup uncertainty, including failed-open cleanup. The existing shared
close task prevents repeated callers from closing the resource again.

Exact-path selection remains the default. Native USB may follow a changed path
only with a unique configured VID/PID/serial-number match. Ambiguity never selects
a candidate. Unknown cleanup retains a blocking ownership fault; it cannot report
the port free or silently retry.

An operation's deadline remains independent of reconnect; neither extends the
other. Monitor may continue within both windows; Interact never retries TX after
a disconnect. Its accepted-byte outcome can remain unknown. The specification
owns outcome precedence and exact range semantics. Reconnect expiry terminalizes
the ownership journal, preserving admitted evidence.

## Explicit handoff

Release persists `release_requested` before closing the backend, drains admitted
RX, closes the segment with `released`, and persists the boundary. Automatic
reconnect stays suspended. Read-only Monitor settles as `released`; an active
Interact or submitted mutation rejects competing release with `operation_active`.
Follow remains a journal reader and does not acquire transport ownership.

External same-port tools may open the released port. After they close it,
reacquire opens and validates the configured backend, records its result, and
starts a fresh timestamp segment. A valid active journal resumes; a terminal
journal produces a new v2 session. The released interval remains an explicit
unobserved gap. A cursor cannot silently join unrelated ownership sessions.

## Rollover, faults, and restart

The next whole evidence unit that would exceed the budget rolls into a linked
successor. A required 33rd segment similarly rolls over instead of failing with a
finite-capture reconnect limit. Operations retain one ID and ranges across the
chain. Rollover does not stop acquisition or imply a physical reconnect.

Persistence failure faults ownership and closes physical input; no client
success can substitute for durable admission. In-flight action attempts retain
known or unknown results without fabricated acknowledgements. Shutdown drains
normalized input, settles operations, and terminalizes the active journal.

Startup recovers interrupted v2 transactions and abandons stale active v2
sessions before opening hardware. A process restart is not a reconnect and never
auto-resumes a stale journal. Historical v0/v1 artifacts remain read-only,
including legacy lifecycle/transaction bookkeeping; no startup migration or
legacy new-session writer exists. Schema-aware retrieval and replay preserve
historical fields without inventing v2 provenance.

Retention follows specification section 15.18, protecting active journals,
operation ranges, baselines, and in-progress readers. Unsupported/corrupt evidence
blocks destructive retention. Cursor expiry is explicit.

## Compatibility and validation

`capture`/`wait` and `/dut/capture`/`/dut/wait-pattern` are thin Monitor aliases.
They have no independent finite ownership or legacy response path. Reset and
boot Control are audited atomic actions; clients compose later observation or
durable evidence retrieval. No dedicated boot-test composite exists.

Current regressions live in `tests/unit/evidence`, `tests/unit/runtime`,
`tests/unit/session_store/test_v2_persistence.py`, service lifecycle/reconnect
checks, and CLI acceptance tests. Hardware records retain their actual historical
firmware, sessions, and measurements; they do not establish current v2 acceptance.
