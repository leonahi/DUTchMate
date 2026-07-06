# Ring Buffer Sizing Plan

> Status: draft decision
> Scope: RP2040 Debug Helper UART/event buffering for Phase 1.

## Decision Summary

Use a **32 KiB UART RX ring buffer** for Phase 1, with a drop-oldest overflow policy and explicit `buffer_overflow` events.

This is large enough to absorb short host/USB scheduling stalls during typical boot logging at 460800 baud while leaving most of the RP2040's 264 KiB SRAM available for firmware, stacks, USB buffers, and protocol encoding.

The size is a starting point, not a permanent product constraint. Phase 1 must measure real high-water marks and overflow frequency before freezing the hardware/firmware design.

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

This does not mean DUTchMate stores only 0.71 seconds of logs. The host streams events continuously to disk. The ring buffer only absorbs temporary backpressure between the UART ISR/reader and USB/protocol transmission.

## Phase 1 Firmware Requirements

The firmware must expose these constants in code:

```c
#define DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES (32 * 1024)
```

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
- Record every overflow in `hardware_events.jsonl`.
- Set session `overflow: true` after the first overflow in a session.
- Include `overflow: true` in every affected capture-like API response.
- Preserve raw bytes that are received after overflow.

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

Phase 1 should test at least three UART load profiles:

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
- Whether first-failure detection still found the correct line.

## Acceptance Criteria

The 32 KiB buffer is acceptable for Phase 1 if:

- Normal boot logs at 460800 baud produce zero overflow events.
- A 250 ms host backpressure simulation at 460800 baud produces zero overflow events.
- Overflow events appear correctly under deliberate stress.
- Sessions with overflow are clearly marked `overflow: true`.
- First-failure extraction refuses to claim complete evidence when `overflow: true`.

If normal boot logs overflow, increase the buffer to 64 KiB or reduce firmware/protocol overhead before exposing MCP tools.

If only dense synthetic continuous logging overflows, keep 32 KiB for MVP and document the limitation.

## Memory Budget

RP2040 SRAM: 264 KiB.

Initial Phase 1 budget target:

| Use | Budget |
|---|---:|
| UART RX ring buffer | 32 KiB |
| USB/protocol TX buffering | 16-32 KiB |
| Firmware stacks/heaps | TBD after Zephyr build |
| Event metadata and scratch buffers | 8-16 KiB |

The final firmware build must report static RAM usage and leave enough headroom for USB CDC and Zephyr runtime behavior.

## Future Options

If Phase 1 measurements show recurring overflow:

- Increase ring buffer to 64 KiB if RAM allows.
- Reduce per-event allocation and copying in firmware.
- Batch UART payloads more efficiently.
- Move from NDJSON/base64 to MessagePack + COBS in Phase 3.
- Use DMA/PIO-based capture in a later hardware evidence phase.

## Open Questions

- Exact Zephyr RAM usage after USB CDC, UART, logging, and stacks are enabled.
- Whether one shared event ring or separate UART/hardware-event rings are simpler in firmware.
- Whether firmware should expose buffer telemetry through a future `status` response or only through host-side diagnostics.
