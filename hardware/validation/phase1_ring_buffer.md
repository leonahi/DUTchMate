# Phase 1 Ring Buffer Validation Record

> Status: selected_unvalidated
> Scope: Phase 1B RP2040 Debug Helper 32 KiB UART RX ring-buffer acceptance evidence.

## Decision State

The selected implementation baseline is 32 KiB. No Zephyr RAM report or
Revision A hardware-in-the-loop load result has been recorded yet. Phase 1B is
not accepted while this document remains `selected_unvalidated`.

This record must finish in exactly one state:

- `accepted_32k`: every acceptance criterion in
  `docs/ring_buffer_sizing_plan.md` passed with the 32 KiB baseline.
- `revised_with_evidence`: measurements required another size or policy, and
  the implementation/specification were updated together with the evidence.

## Fixture Identity

| Field | Result |
|---|---|
| Date/time | Not run |
| Operator | Not run |
| Debug Helper board revision | Not run |
| DUT/fixture | Not run |
| Host OS | Not run |
| Zephyr version | Not run |
| Board target | Not run |
| Application commit | Not run |
| Build ID/configuration | Not run |
| Related DUTchMate session IDs | Not run |

## Firmware RAM Report

| Measurement | Result |
|---|---|
| Static image RAM | Not run |
| UART RX ring buffer | 32768 bytes selected |
| USB/protocol buffers | Not run |
| Thread stacks/heaps | Not run |
| Measured stack high-water margins | Not run |
| Remaining RAM margin | Not run |

Attach or reference the exact Zephyr build output used for these values. Do not
estimate missing measurements.

## Load Results

| Profile | Runs | UART baud | Duration/stall | Max occupancy | Overflow events | Dropped bytes | Result |
|---|---:|---:|---|---:|---:|---:|---|
| Representative normal boot | 0 | 460800 | Not run | Not run | Not run | Not run | Not run |
| Dense synthetic burst | 0 | 460800 | 15 s | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 100 ms | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 250 ms | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 500 ms | Not run | Not run | Not run | Not run |
| Deliberate overflow | 0 | 460800 | Not run | Not run | Not run | Not run | Not run |

## Acceptance Checklist

- [ ] Ten consecutive representative normal boots produced zero overflow
  events.
- [ ] The 250 ms backpressure test produced zero overflow events.
- [ ] Deliberate stress produced explicit overflow telemetry with consistent
  dropped-byte and high-water accounting.
- [ ] Sessions exposed `loss_reported` and
  `debug_helper_rx_buffer` when overflow occurred.
- [ ] No test silently discarded overflow telemetry or represented the receive
  path as globally lossless.
- [ ] Zephyr RAM and stack measurements retained adequate margin for the fixed
  buffers and worst-case protocol encoding.

## Final Decision

`selected_unvalidated`

Replace this value only after recording reproducible measurements above. A
failed criterion requires `revised_with_evidence`; it must not be waived by
editing the final state alone.
