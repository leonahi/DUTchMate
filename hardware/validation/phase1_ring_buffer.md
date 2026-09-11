# Phase 1 Ring Buffer Validation Record

> Status: selected_unvalidated
> Scope: Phase 1B RP2350-based Raspberry Pi Pico 2 Debug Helper 32 KiB UART RX
> ring-buffer acceptance evidence.

## Decision State

The selected implementation baseline is 32 KiB. The reproducible Zephyr static
RAM report is recorded below. Runtime stack high-water margins and Revision A
hardware-in-the-loop load results have not been recorded yet. Phase 1B is not
accepted while this document remains `selected_unvalidated`.

This record must finish in exactly one state:

- `accepted_32k`: every acceptance criterion in
  `docs/ring_buffer_sizing_plan.md` passed with the 32 KiB baseline.
- `revised_with_evidence`: measurements required another size or policy, and
  the implementation/specification were updated together with the evidence.

## Fixture Identity

| Field | Result |
|---|---|
| Date/time | 2026-09-11, Europe/Paris |
| Operator | Not run |
| Debug Helper platform | Raspberry Pi Pico 2, non-wireless, RP2350A |
| Debug Helper board revision | User-confirmed fully assembled Revision A translator prototype; not connected for this build-only step |
| DUT/fixture | None for static Debug Helper build; 460800-baud Pico 1 HIL candidate prepared below |
| Host OS | macOS 26.2, build 25C56 |
| Zephyr version | 4.4.2 with SDK 1.0.1 |
| Zephyr board target | `rpi_pico2/rp2350a/m33` |
| Application commit | `3e149a530bfa6fd2b29682874f2942d619d7a30c` |
| Build ID/configuration | `development`; pristine `prj.conf` build; firmware source last changed by `8bf0a03783c31232095dc00a14b783889f6efa57` |
| Related DUTchMate session IDs | None for static build |

## Firmware RAM Report

| Measurement | Result |
|---|---|
| Static image RAM | 78,032 of 532,480 bytes (14.65%); linker total including alignment/padding |
| UART RX ring buffer | 32,768 raw bytes; 45,136-byte complete ring object including 512 timestamp descriptors and accounting state |
| USB/protocol buffers | Major named static allocations: CDC TX state 1,584 bytes; command ingress 2,056; command queues 3,088; UART TX state 1,072; evidence frame 1,536; UART staging 1,024; CDC RX/TX rings 1,024/64; UDC endpoint heap 1,024 |
| Thread stacks/heaps | 14,144 statically allocated stack bytes; system heap `CONFIG_HEAP_MEM_POOL_SIZE=0` |
| Measured stack high-water margins | Not run |
| Remaining RAM margin | 454,448 bytes (443.8 KiB, 85.35%) after the linked static image |

The 14,144 stack bytes comprise the 4,096-byte CDC RX thread, 3,072-byte command
thread, 2,048-byte main stack, 2,048-byte interrupt stack, 1,024-byte system
workqueue, 1,024-byte USB-device thread, 512-byte RP2350 UDC thread, and
320-byte idle stack. These are configured/static allocations, not measured
runtime high-water margins.

The pristine build used Zephyr tag `v4.4.2`, SDK 1.0.1, west 1.3.0, and the
required CMSIS 6 and Raspberry Pi Pico HAL modules. It completed with 52,012
bytes of flash and 78,032 bytes of RAM. The generated UF2 is 104,448 bytes and
has SHA-256
`c98fe7b19bb86ae7452b9d0aa4a24523e28137882ed92df588971a13e824b2bc`,
matching the digest of the file previously reported as flashed. The Pico image
was not read back, so this match does not independently prove its contents. The
ignored build tree retains the exact evidence at:

- `build/dutchmate-rp2350-debug-helper/build_info.yml`;
- `build/dutchmate-rp2350-debug-helper/zephyr/.config`, SHA-256
  `c59e0ce8c51304d00c4bb52cf6da76954cecdbc0ec8bdf72bad22305bc6c3ba0`;
- `build/dutchmate-rp2350-debug-helper/zephyr/zephyr.elf`, SHA-256
  `5a3ae5b4170d35010e30b59b1a9af8134a44f786845f5f03ef0210058ee36d91`;
- `build/dutchmate-rp2350-debug-helper/zephyr/zephyr.map`; and
- `build/dutchmate-rp2350-debug-helper/ram.json`, SHA-256
  `1af223f9c4530bd589c83267dd6a2eecb1271b94539f592572740a7a78a52943`.

Zephyr's symbol-attributed `ram_report` accounts for 76,583 bytes. The linker
region total of 78,032 bytes is authoritative for the static footprint because
it also includes allocation alignment and padding. Do not estimate the still
missing runtime measurements from these static values.

## 460800-Baud HIL Fixture Candidate

The existing Pico 1 Zephyr DUT fixture remains unchanged at its 115200-baud
default for the accepted Basic path. An opt-in
`boards/rpi_pico_460800.overlay` now supplies the Enhanced ring-buffer rate
without changing that default.

| Field | Candidate result |
|---|---|
| Board/target | Raspberry Pi Pico 1, `rpi_pico/rp2040` |
| Zephyr/toolchain | Zephyr 4.4.0, SDK 1.0.1 |
| Fixture source baseline | `203649f18ff4c75c505043a921f3183bb35e41f5` |
| Fixture build ID | `phase1-enhanced-460800-001` |
| UART | 460800 baud, 8-N-1; generated UART0 `current-speed = < 0x70800 >` |
| Build footprint | 16,840 bytes flash; 4,952 bytes RAM |
| Generated `.config` SHA-256 | `4e472f3f0ea19c89611b2d9f05ef2f08b0fcfca198fc573a0b074b7de3441595` |
| UF2 | 34,304 bytes; SHA-256 `152cc8593e5c75be92c2595f6fc2dc664738dcb2716dec204aa6ffd0634ecbb6` |
| Flash/HIL state | Not flashed; no result claimed |

The ignored candidate image is retained at
`build/dutchmate-zephyr-dut-460800/zephyr/zephyr.uf2`. Flashing and a captured
boot marker are required before this becomes HIL fixture provenance.

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
