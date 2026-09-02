# Ring Buffer Sizing Plan

> Scope: RP2350-based Raspberry Pi Pico 2 Debug Helper UART RX buffering for
> Phase 1.

## Decision Summary

Implement a **32 KiB UART RX ring buffer** for Phase 1B, with a drop-oldest
overflow policy and explicit `buffer_overflow` events.

The nominal throughput calculation indicates that this size should absorb short
host/USB scheduling stalls at 460800 baud while leaving most of the RP2350's
520 KiB SRAM available for firmware, stacks, USB buffers, and protocol
encoding. The validation gate must confirm both assumptions.

This is the selected implementation baseline, not a validated final size. Its
decision state is `selected_unvalidated` until the firmware RAM report and HIL
measurements in this document produce either `accepted_32k` or
`revised_with_evidence`. Phase 1B cannot be declared complete while the state is
`selected_unvalidated`.

## Throughput Assumptions

MVP target DUT baud rate: `460800`.

Approximate raw UART throughput:

```text
460800 bits/s / 10 bits per byte ~= 46080 bytes/s
```

A 32 KiB buffer holds roughly:

```text
32768 bytes / 46080 bytes/s ~= 0.71 seconds
```

For a completely stalled consumer and an initially empty ring, the expected raw
UART accumulation is:

| Stall | Bytes | Approximate KiB |
|---:|---:|---:|
| 100 ms | 4,608 | 4.5 |
| 250 ms | 11,520 | 11.25 |
| 500 ms | 23,040 | 22.5 |

The ring stores raw UART bytes, so NDJSON/base64 expansion does not directly
consume ring capacity; it can still slow draining and therefore affects the
measured high-water mark.

The Phase 1 Enhanced wire contract limits one device-to-host NDJSON frame to
65536 bytes including LF. One `uart` message therefore carries at most 32768
decoded UART bytes; its base64 expansion and compact JSON framing fit within the
wire bound. Firmware splits a larger available ring-buffer batch into ordered
messages and never truncates bytes merely to fit a frame. The host enforces the
wire limit before decode so a missing LF cannot grow memory without bound.

This does not mean DUTchMate stores only 0.71 seconds of logs. The host streams events continuously to disk. The ring buffer only absorbs temporary backpressure between the UART ISR/reader and USB/protocol transmission.

## Phase 1 Firmware Requirements

The firmware must expose these constants in code:

```c
#define DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES (32 * 1024)
```

The Phase 1 ring contains only raw DUT UART RX bytes. Command responses,
`buffer_status`, and `buffer_overflow` records use separate protocol/control
queues. `EVENTn` capture is deferred to Phase 5 and does not share this ring.

The firmware must track:

- Current ring occupancy.
- Maximum observed occupancy since boot.
- Total dropped bytes.
- Number of overflow events.
- Timestamp of each overflow event.

Overflow policy:

- Drop oldest bytes.
- Preserve newest bytes.
- Emit a `buffer_overflow` event with `dropped_bytes`.
- Continue capture after overflow.

## Host Requirements

The Device Core must:

- Treat `buffer_overflow` as a normal protocol event, not a parse error.
- Treat malformed or oversized NDJSON as fatal `backend_input_error`, not buffer
  overflow, UART loss telemetry, timeout, or disconnect.
- Record every overflow in `hardware_events.jsonl`.
- Initialize Enhanced-backend session integrity as
  `loss_status: none_reported`,
  `observation_scope: debug_helper_rx_buffer`, and `dropped_bytes: 0`.
- Set `loss_status: loss_reported` after the first overflow in a session and
  record the dropped-byte count when known.
- Include the same `integrity` object in every affected capture-like API
  response.
- Preserve raw bytes that are received after overflow.

`none_reported` applies only to the Debug Helper RX buffer. It is not proof that
the complete electrical UART path was lossless. `truncated` and `interrupted`
remain independent session fields.

Firmware reports telemetry with a v1 `buffer_status` event. The service should expose the most recent buffer telemetry when available:

```json
{
  "buffer": {
    "uart_rx_size_bytes": 32768,
    "uart_rx_high_water_bytes": 18432,
    "dropped_bytes_total": 512,
    "overflow_events": 1
  }
}
```

## Validation Plan

Phase 1B must test at least three UART load profiles:

1. Normal boot log at 460800 baud.
2. Dense synthetic log burst at 460800 baud for 15 seconds.
3. Host backpressure simulation where USB/protocol transmission is stalled for 100 ms, 250 ms, and 500 ms.

For each run, record:

- DUT baud rate.
- Capture duration.
- Total bytes received.
- Maximum ring occupancy.
- Overflow event count.
- Dropped bytes.
- Host CPU/load conditions.
- Whether deterministic `first_error` selection still found the correct stored
  failure-pattern line.
- Firmware commit/build configuration and Zephyr version.
- Static RAM report plus configured stack and heap sizes.
- Board revision, DUT/fixture identity, and host OS.

Run at least ten consecutive representative normal boots so a single favorable
run cannot close the gate. Store the completed result in
`hardware/validation/phase1_ring_buffer.md`; raw test logs may remain outside
Git when large, but the report must identify where they were retained.

## Acceptance Criteria

The 32 KiB buffer is acceptable for Phase 1 if:

- Ten consecutive representative normal boot logs at 460800 baud produce zero
  overflow events.
- A 250 ms host backpressure simulation at 460800 baud produces zero overflow events.
- Overflow events appear correctly under deliberate stress.
- Sessions with overflow are clearly marked `loss_status: loss_reported` with
  `observation_scope: debug_helper_rx_buffer`.
- Deterministic `first_error` reporting surfaces reported loss and does not hide
  it behind a global `ok` or `complete` label.
- The final Zephyr build records static RAM, stack, and heap configuration and
  completes the boot, 500 ms backpressure, and deliberate-overflow tests without
  allocation failure, stack overflow, watchdog reset, or USB CDC failure.

After validation, the report records exactly one outcome:

- `accepted_32k`: all acceptance criteria passed; 32 KiB becomes the Phase 1
  validated size.
- `revised_with_evidence`: a different size or buffering/encoding design was
  required; the report records the failed criterion, measurements, new value,
  and associated firmware/documentation changes.

If normal boot logs overflow, increase the buffer to 64 KiB or reduce firmware/protocol overhead before exposing MCP tools.

If only dense synthetic continuous logging overflows, keep 32 KiB for MVP and document the limitation.

## Memory Budget

RP2350 SRAM: 520 KiB.

Initial Phase 1 budget target:

| Use | Budget |
|---|---:|
| UART RX ring buffer | 32 KiB |
| USB/protocol TX buffering | 16-32 KiB |
| Firmware stacks/heaps | TBD after Zephyr build |
| Event metadata and scratch buffers | 8-16 KiB |

The final firmware build must report static RAM usage and demonstrate runtime
headroom through stack/heap diagnostics and the stress tests above. A larger
ring must not be selected from throughput results alone if it causes memory or
USB stability failures.

## Future Options

If Phase 1 measurements show recurring overflow:

- Increase ring buffer to 64 KiB if RAM allows.
- Reduce per-event allocation and copying in firmware.
- Batch UART payloads more efficiently.
- Move from NDJSON/base64 to MessagePack + COBS in Phase 3.
- Use DMA/PIO-based capture in a later hardware evidence phase.

## Required Evidence

- Exact Zephyr RAM usage after USB CDC, UART, logging, and stacks are enabled.
- Real representative boot-log high-water marks and overflow counts.
- Synthetic-load and host-backpressure results on the Revision A prototype.

These are required measurements, not unresolved architecture choices. The
32 KiB implementation proceeds before they are available, but Phase 1B
acceptance does not.
