# Reconnect and Session Semantics

> Status: accepted Phase 1 target contract
> Scope: Device Core lifecycle and timestamp behavior when either Phase 1 backend disconnects or reconnects during a capture-like workflow.
> Implementation: durable session mutations, deterministic capture/boot-test deadline coordination, bounded Basic/Enhanced reopening, and volatile runtime status are present; continuous monitoring outside an active workflow remains.

## Goal

Disconnects must never erase admitted evidence or make timestamps look
continuous when they are not. DUTchMate preserves every byte admitted before
the disconnect, marks uncertainty explicitly, and resumes a session only when
the resumed evidence can be represented honestly. A size-cap rejection remains
the separate explicit truncation path.

## Definitions

| Term | Meaning |
|---|---|
| Segment | A continuous interval from one backend connection with one immutable timestamp origin/provenance object. |
| Disconnect | Host loses the selected serial connection or the serial reader reports EOF/error. |
| Reconnect | Service reopens the configured Basic port or reopens an Enhanced backend and validates `hello`. |
| Resume | Continue appending to the same session after reconnect. |
| New session | Close the interrupted session and start another session after reconnect. |

Top-level session lifecycle is independent from segment and reconnect facts.
`state` is `active` while the owning workflow can still receive evidence, then
transitions once to `completed`, `failed`, or `abandoned`. `interrupted` means
at least one disconnect was observed; `resumed` means evidence was appended in
a later segment. Neither flag determines lifecycle state by itself.

## Session Segments

Every session has 1..32 segments. A normal uninterrupted session has exactly
one segment. IDs are contiguous zero-based integers, so the initial connection
is segment `0`, the last permitted segment is `31`, and one session can resume
successfully at most 31 times.

`metadata.json` must include:

```json
{
  "interrupted": true,
  "resumed": true,
  "segments": [
    {
      "segment_id": 0,
      "started_at": "2026-07-04T12:00:00Z",
      "ended_at": "2026-07-04T12:00:03Z",
      "end_reason": "usb_disconnect",
      "backend": {
        "mode": "enhanced",
        "port": "/dev/ttyACM0",
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "backend_capabilities": ["uart_receive", "gpio_control", "uart_send"],
        "capabilities": ["uart_receive", "gpio_control", "uart_send"],
        "capability_policy": {
          "uart_send": {
            "tx_policy_enabled": true,
            "source": "hardware.uart.tx_enabled"
          }
        }
      },
      "timestamp": {
        "source": "device",
        "clock": "rp2040_timer",
        "unit": "us",
        "origin": "segment_start",
        "source_origin_us": 1000,
        "observation_point": "debug_helper_uart_receive",
        "event_granularity": "uart_event"
      },
      "first_timestamp_us": 0,
      "last_timestamp_us": 3000000
    },
    {
      "segment_id": 1,
      "started_at": "2026-07-04T12:00:05Z",
      "ended_at": null,
      "end_reason": null,
      "backend": {
        "mode": "enhanced",
        "port": "/dev/ttyACM0",
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "backend_capabilities": ["uart_receive", "gpio_control", "uart_send"],
        "capabilities": ["uart_receive", "gpio_control", "uart_send"],
        "capability_policy": {
          "uart_send": {
            "tx_policy_enabled": true,
            "source": "hardware.uart.tx_enabled"
          }
        }
      },
      "timestamp": {
        "source": "device",
        "clock": "rp2040_timer",
        "unit": "us",
        "origin": "segment_start",
        "source_origin_us": 500,
        "observation_point": "debug_helper_uart_receive",
        "event_granularity": "uart_event"
      },
      "first_timestamp_us": 0,
      "last_timestamp_us": null
    }
  ]
}
```

Each segment snapshots the complete backend identity for that connection.
`port` uses the exact 1..4096-byte UTF-8 session-identity contract; Basic
segments use null `firmware`/`device`, while Enhanced segments use the accepted
1..64-byte `hello` values. The top-level `backend_identity` is the immutable
session-start snapshot; segment snapshots preserve any identity observed after
a reconnect.

The 32-segment maximum is a schema constant, not a configurable retention or
evidence-quota setting. No writer may evict, merge, deduplicate, compress, or
truncate an earlier segment to admit another one. Before publishing a new event
source, Device Core durably appends the complete new segment metadata and
verifies that compact active metadata plus the worst-case terminal object still
fits the 262144-byte metadata cap. Schema tests must prove that 32
maximum-length segment identities and all fixed provenance/policy fields fit;
failure of that invariant is an implementation/schema defect, not an expected
runtime size-limit outcome.

`interrupted` means at least one disconnect occurred during the session. `resumed` means data was appended after a reconnect.

Within each segment, `backend_capabilities` preserves pre-policy backend
support, `capabilities` is the effective operation-gating list, and
`capability_policy` records the policy snapshot applied for that connection.
Reconnect must recompute and store all three after validating the backend.
`tx_policy_enabled` records software write permission only; it is not an
electrical state observation.

## Incremental Writes

The Device Core must write incrementally as events arrive:

- Append decoded UART bytes to `uart_raw.log`.
- Append parsed UART events to `uart_events.jsonl`.
- Append hardware/session events to `hardware_events.jsonl`.
- Update `metadata.json` when disconnect, reconnect, resume, truncation, or capture end occurs.

Data already written must not be rewritten or discarded during reconnect handling.

For a forced in-session UART send, `uart_tx_attempt` is appended before backend
dispatch and `uart_tx_result` after completion. Both carry the same
`attempt_id` and the segment active at dispatch. A disconnect while awaiting a
backend result should append a failed result with `bytes_accepted: null` when
Device Core remains able to write the session; this reports an API failure but
does not claim that zero bytes reached the DUT. If process interruption or a
result-persistence failure leaves the attempt unmatched, session readers must
surface its completion as unknown. Reconnect must never retry or synthesize a
result for that attempt.

## Hardware Events

Reconnect lifecycle events are recorded in `hardware_events.jsonl`:

```jsonl
{"type": "usb_disconnect", "host_timestamp": "2026-07-04T12:00:03Z", "segment_id": 0}
{"type": "usb_reconnect", "host_timestamp": "2026-07-04T12:00:05Z", "segment_id": 1}
{"type": "timestamp_discontinuity", "host_timestamp": "2026-07-04T12:00:05Z", "from_segment_id": 0, "to_segment_id": 1}
```

These are host-side hardware/session events, not device-to-host protocol messages.

## Timestamp Rules

All normalized timestamps are authoritative only within their segment.

Rules:

- Every normalized event stores `segment_id` and microseconds elapsed from that
  segment's source origin in `timestamp_us`.
- Segment metadata records `source`, `clock`, `unit`, `origin`,
  `source_origin_us`, `observation_point`, and `event_granularity`.
- The Basic backend uses `time.monotonic_ns()` and timestamps once when a host
  serial-read callback delivers a chunk. All bytes in that chunk share one
  timestamp.
- The Enhanced backend timestamps one UART event with the RP2040 timer before
  USB delivery. All bytes in that firmware event share one timestamp.
- If a source clock cannot be sampled at segment creation, the first event
  establishes `source_origin_us` and receives `timestamp_us: 0`.
- Ordering across segments is based on segment order and host reconnect
  metadata, never raw or normalized timestamp comparison.
- A reconnect always creates a new segment and source origin, even if a clock
  appears continuous.
- `started_at`, `ended_at`, and lifecycle-event wall times are descriptive RFC
  3339 metadata and are not used for event ordering.
- If firmware later provides a stable boot counter or monotonic connection id, the Device Core may use it to improve duplicate detection, but Phase 1 does not require it.

The target normalized model does not store `timestamp_epoch`; `segment_id`
already selects the timestamp epoch and provenance.

Example `uart_events.jsonl` entry:

```json
{"type": "uart", "segment_id": 1, "timestamp_us": 0, "channel": 0, "data_b64": "Qk9PVF9PSwo=", "text": "BOOT_OK\n"}
```

## Backend Event Boundary Ownership

The Device Core connection/session coordinator owns session-local segment IDs.
Each physical connection creates a new `BackendEventSource` bound to exactly one
segment ID; an event source is never rebound across reconnects. Once the Basic
or Enhanced adapter establishes the source origin, that source exposes one
immutable `SegmentContext` and must attach its segment ID and normalized
timestamp before publishing an event.

The event source drains already-parsed FIFO events before raising a disconnect
exception. This preserves evidence accepted before the connection loss. Once
the disconnect is reported, the old source cannot publish more events. A
successful reconnect creates a new source and segment context, and only that
new source may publish events for the new segment.

An ordinary read timeout returns `None` and does not change session state. A
disconnect exception triggers interruption/reconnect handling unless the
current segment is `31`, as defined below. Invalid Enhanced
framing or payload data raises a distinct backend-input error and follows the
fatal parse-error policy; it must not be reported as a timeout or disconnect.
Debug Helper command responses are routed to command waiters and never cross
the normalized event boundary.

Enhanced NDJSON is invalid when a total device-to-host frame exceeds 65536 wire
bytes including LF/optional CR, when pending bytes can no longer fit a valid
terminated frame, or when its UTF-8, JSON object, message schema, bounded fields,
or base64 payload is invalid. Valid complete frames before the offending frame
remain queued in FIFO order. The offending frame and all later bytes in that
serial read are not published. Device Core then closes the source and fails any
pending command waiter with `backend_input_error`.

For an active workflow this is immediately terminal `failed` /
`backend_input_error`, not a reconnect opportunity. Already admitted evidence
is preserved; the error itself does not set `interrupted`, `truncated`, or UART
loss status. The session error uses the shared non-empty 1..1024-byte diagnostic
projection plus `detail_truncated`; it never embeds the offending frame or DUT
payload.

## Resume Policy

`[backend].reconnect_timeout_s` is a host workflow policy. It defaults to `5.0`
seconds and accepts finite numeric values from `0.1` through `60.0`, inclusive;
booleans and all other types/ranges are invalid configuration. Device Core
validates it before opening a backend and snapshots the accepted value as
top-level `reconnect_timeout_s` in every native capture, boot-test, and
wait-pattern session. A later configuration change cannot alter an active or
stored session.

After the old event source drains its already-parsed FIFO, the coordinator uses
the host monotonic time at which that source reports the disconnect to start a
fresh reconnect window. Persistence and reopen/handshake work consume that
window; no step resets or extends it. The original workflow deadline remains
independent. Reconnect succeeds only if the replacement source is fully
validated and ready strictly before both deadlines. If the deadlines are due at
the same instant, the original workflow deadline takes precedence and produces
its normal completed outcome.

An active capture-like workflow, including wait-pattern, can resume into the
same session only when all conditions are true:

1. The reconnect occurs before `reconnect_timeout_s` expires.
2. The backend mode matches the interrupted session.
3. The effective serial-port path and configured 8-N-1 UART settings exactly
   match the interrupted connection. Enhanced additionally requires a valid
   `hello` with protocol version `1` and exact matching `device` and `firmware`
   identity strings. Device Core never resumes by selecting another port or
   silently changing serial settings.
4. The session has not already ended due to timeout, truncation, explicit stop,
   or fatal backend input error.
5. The session currently contains fewer than 32 segments.

If these conditions are met:

- Append a new segment to the same session.
- Set `interrupted: true`.
- Set `resumed: true`.
- Record `usb_reconnect` and `timestamp_discontinuity`.
- Continue the workflow until its original monotonic deadline. A wait-pattern
  matcher starts a fresh line buffer for the new segment and never joins a
  pre-disconnect partial line to post-reconnect bytes.
- If the old segment was counting an oversized physical line, close its
  `line_limit_exceeded` descriptor as unterminated with the observed byte count.
  The new segment starts normal line processing with independent limit state.

If any condition fails:

- Mark the existing session `interrupted: true`.
- End the active capture-like workflow with `state: "failed"`, a specific
  `end_reason` and canonical bounded error object, unless its original normal
  workflow deadline or explicit user stop ended it first.
- Start a new session only if a new user or workflow command requests one.

When the reconnect deadline expires first, the session fails with
`end_reason: "reconnect_timeout"` and an error object using
`code: "service_unavailable"`, canonical detail `Backend did not reconnect
before the reconnect deadline`, and `detail_truncated: false`. The owning HTTP
request returns 503 with context exactly `operation`, `session_id`, and the
snapshotted `reconnect_timeout_s`. Backend reconnection may continue for future
requests, but it can never reopen or append to the terminal session.

The segment-limit failure is handled at disconnect rather than after opening a
33rd connection. After the old source drains its already-parsed FIFO events,
Device Core admits the complete `usb_disconnect` evidence unit, closes segment
`31`, sets `interrupted: true`, and terminalizes immediately as:

```json
{
  "state": "failed",
  "end_reason": "reconnect_limit",
  "truncated": false,
  "error": {
    "code": "service_unavailable",
    "detail": "Session reached the 32-segment reconnect limit",
    "detail_truncated": false
  }
}
```

`resumed` retains its existing value, which is true for a valid segment `31`;
UART `integrity` and `line_processing` retain independently established facts.
Device Core does not attempt to reopen the Basic port or Enhanced backend and
does not write `usb_reconnect` or `timestamp_discontinuity`. The owning service
request returns HTTP 503 `service_unavailable` with context `operation`,
`session_id`, `segment_count: 32`, and `max_segments: 32`. The failed session
remains available through normal session retrieval.

Outcome precedence remains evidence-safe. A workflow already terminalized by
deadline or user stop never enters reconnect-limit handling. For an observed
disconnect, failure to durably admit its evidence is `persistence_error`; a
quota rejection is the existing successful `size_limit` truncation and wins
before reconnect-limit terminalization. Only an admitted disconnect from
segment `31` produces `reconnect_limit`.

## Duration Behavior

For Phase 1, capture duration and wait-pattern timeout are elapsed-time based
from the host workflow start and measured with a monotonic host clock.
Wall-clock adjustments and reconnect do not extend the deadline.

Capture and boot-test accept only an explicit finite numeric duration satisfying
`0 < duration_s <= 300`. Validation occurs before session/reset work. The
accepted duration is stored with the session and the original monotonic deadline
is retained across reconnect attempts.

Example: if `capture --seconds 10` disconnects at second 3 and reconnects at second 5, capture still ends at second 10. The session contains a two-second evidence gap.

Likewise, a 10-second wait that reconnects at second 5 still expires at second
10. If its deadline arrives while reconnecting, it ends as an interrupted,
unmatched wait result; a reconnect must not search the old segment or extend the
wait.

The gap must be visible through segment metadata and hardware events.

If the original workflow deadline arrives before or at the reconnect deadline, it
ends normally: capture/boot-test uses `state: "completed"` with
`end_reason: "duration_elapsed"`, and wait-pattern uses `state: "completed"`
with `end_reason: "timeout"` and `matched: false`. If the reconnect deadline
arrives first, the workflow uses `state: "failed"` with
`end_reason: "reconnect_timeout"` and service error `service_unavailable`.

## Process Restart Recovery

A process restart is not a reconnect. Before opening either backend or
accepting workflow requests, Device Core atomically transitions every native
`schema_version: 1` session still marked `active` to `state: "abandoned"` with
`end_reason: "service_restart"`, null `error`, and `ended_at` equal to the
recovery observation time. It preserves all existing evidence, does not add a
synthetic disconnect event, and never auto-resumes or appends a new segment to
that session. Unversioned legacy and unknown-version directories are reported
but remain untouched because their lifecycle semantics cannot be inferred.

## Duplicate Prevention

Phase 1 does not attempt to deduplicate UART bytes across a USB disconnect.

Rationale:

- USB CDC disconnect generally means unread bytes in host/device buffers may be lost.
- Without firmware sequence numbers, duplicate detection can accidentally discard real repeated boot output.

Future protocol versions may add per-event sequence numbers. Until then, the
session records the discontinuity and preserves every quota-admitted byte after
reconnect.

## Service and CLI Reporting

Capture-like API responses include:

```json
{
  "ok": true,
  "session_id": "20260704T120000Z-a1b2c3d4",
  "schema_version": 1,
  "integrity": {
    "loss_status": "none_reported",
    "observation_scope": "debug_helper_rx_buffer",
    "dropped_bytes": 0
  },
  "interrupted": true,
  "resumed": true,
  "segments": 2
}
```

Each native bounded `GET /sessions` summary includes lifecycle state/end
metadata plus `interrupted`, `resumed`, and segment count. Native
`GET /sessions/{id}` detail exposes the same facts. Legacy version `0` uses the
separate read-only compatibility shape and does not synthesize reconnect facts.

`dutchmate status` shows reconnect state during an active capture-like
workflow, including its kind:

```text
Workflow: wait-pattern (active)
Session: 20260704T120000Z-a1b2c3d4
Connection: reconnecting (2.1s remaining)
```

The current `GET /status` payload supplies this without reconstructing volatile
state from session files: `connection_state` is `connected`, `disconnected`, or
`reconnecting`; nullable `active_workflow` names the finite owner; and nullable
`reconnect_remaining_s` is the non-negative monotonic time remaining for that
active session. The existing `connected` boolean remains true only in the
`connected` state. `reconnect_remaining_s` is null outside an active reconnect
window and is display state, not persisted evidence.

`dutchmate logs` may show a visible separator between segments:

```text
[connection lost at 2026-07-04T12:00:03Z]
[connection resumed at 2026-07-04T12:00:05Z; new timestamp segment]
```

These separators are CLI presentation generated from lifecycle and segment
metadata. They are not entries in the service's `lines` or `partial_lines`
arrays and are never appended to UART evidence files. Recent-log reconstruction
uses an independent line buffer per segment/channel. Trailing bytes before a
disconnect remain a partial record in the old segment and never combine with
bytes received after reconnect. An oversized trailing physical line is exposed
as an unterminated descriptor instead of a partial `line_raw_b64` record.

## Failure Modes

| Condition | Session result |
|---|---|
| Reconnect deadline expires before workflow deadline | `state: "failed"`, `end_reason: "reconnect_timeout"`, service code `service_unavailable`, `interrupted: true`, and `resumed: false` unless an earlier reconnect had resumed once |
| Original workflow deadline expires first or ties while reconnecting | `state: "completed"` with `duration_elapsed` or wait-pattern `timeout`; `interrupted: true` remains independent |
| Reconnect with protocol version mismatch | Existing session fails as `backend_input_error` with input category `invalid_message`; the connection is rejected until compatible firmware is available |
| Admitted disconnect from segment `31` before the workflow deadline | `state: "failed"`, `end_reason: "reconnect_limit"`, service code `service_unavailable`, 32 preserved segments, and no reopen attempt |
| Next whole evidence unit would exceed the session budget | Unit is omitted in full; `state: "completed"`, `end_reason: "size_limit"`, and `truncated: true`; a later reconnect cannot resume it |
| User stops capture while reconnecting | `state: "completed"`, `end_reason: "user_stop"`, and `interrupted: true` |
| Fatal Enhanced framing/message error while active | `state: "failed"`, `end_reason: "backend_input_error"`, with the 1024-byte non-payload diagnostic projection and truncation flag; no resume |
| Device Core restarts with persisted active metadata | `state: "abandoned"`, `end_reason: "service_restart"`; no synthetic disconnect or automatic resume |

## Test Requirements

Minimum tests:

- Disconnect marks `interrupted: true`.
- Reconnect before timeout appends a second segment.
- Reconnect timeout configuration defaults to 5.0, accepts only finite numeric
  values in 0.1..60.0, rejects booleans, and is snapshotted in native metadata.
- Each disconnect starts a fresh monotonic reconnect window without extending
  the original workflow deadline; a deadline tie resolves as normal workflow
  completion.
- Reconnect creates a new segment with a new timestamp origin/provenance object.
- Segment IDs remain contiguous from `0`; segment `31` is accepted and a 33rd
  segment is never created for either backend.
- Worst-case compact metadata with 32 maximum-length identities, complete
  provenance/policy snapshots, and worst-case terminal fields remains at or
  below 262144 bytes.
- An admitted disconnect from segment `31` records and closes that segment,
  preserves all prior evidence, returns the specified `service_unavailable`
  context, and fails as `reconnect_limit` without a backend reopen attempt,
  reconnect/discontinuity events, truncation, or integrity mutation.
- Quota rejection of that disconnect yields `completed` / `size_limit`, while a
  disconnect persistence failure yields `persistence_error`; neither is
  relabeled `reconnect_limit`.
- Reconnect after timeout does not append to the old session.
- Workflow deadline before or tied with reconnect deadline produces a normal
  completed result; reconnect deadline first produces a failed
  `reconnect_timeout` / `service_unavailable` session and bounded HTTP context.
- Protocol version mismatch rejects resume.
- Size-capped/truncated sessions do not resume.
- Startup marks stale native schema version `1` active sessions abandoned before
  connecting and preserves their evidence without synthesizing reconnect events;
  non-native sessions remain read-only.
- `uart_events.jsonl` includes `segment_id` and segment-relative `timestamp_us`.
- Basic serial-read chunks share one host-monotonic timestamp and do not infer
  per-byte timing.
- Enhanced UART events use RP2040 timer provenance and are normalized relative
  to their segment origin.
- No ordering operation compares timestamps from different segments.
- Each reconnect replaces the old event source with a source bound to the new
  immutable segment context.
- Parsed FIFO events are delivered before the old source reports disconnect;
  no old-source event can appear after the disconnect transition.
- Receive timeout, disconnect, and malformed backend input remain distinct
  outcomes.
- Exact-limit Enhanced frames remain valid; oversized unterminated input fails
  before unbounded buffering. Valid frames preceding an invalid frame are
  delivered, while the invalid frame and later same-read bytes are not.
- Wait-pattern does not join lines across segments, does not extend its
  monotonic deadline during reconnect, and reports deadline expiry as an
  unmatched workflow result rather than a backend timeout error.
- `hardware_events.jsonl` records disconnect, reconnect, and timestamp discontinuity.
- Recent-log retrieval returns segment transitions in evidence order, exposes
  old-segment trailing bytes as partial, and never emits CLI separators as DUT
  evidence.
