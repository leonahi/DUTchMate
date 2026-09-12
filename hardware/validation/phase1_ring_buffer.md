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
| Flash/HIL state | Flashed on 2026-09-12. A direct 25 MS/s Saleae capture decoded the exact 62-byte build marker at 460800 8-N-1; Debug Helper boot-capture acceptance remains pending the line-error recovery image below. |

The ignored candidate image is retained at
`build/dutchmate-zephyr-dut-460800/zephyr/zephyr.uf2`.

The first integrated boot attempts exposed a normal reset-line interaction
before a representative load result could be claimed. Pico 1 `RUN` assertion
made its GP0 UART TX line low until firmware initialized it after release. The
original Debug Helper treated the resulting PL011 break/framing flag as a fatal
driver fault, returned `DBG_UART_IF_EN` to 0 V, and stopped servicing later CDC
epochs. Sessions `20260912T201857Z-7d797e80` and
`20260912T204452Z-1f60f8f1` each retained a single `0x00` observation rather
than the boot marker; session `20260912T203812Z-41fa19be`, run before the UART
wires were corrected, retained no UART bytes and is not product evidence.

The direct Saleae transition export measured `RUN` low for 1.214627 s during a
manual diagnostic, GP0 TX returning idle-high 27.753 ms after release, and the
UART burst starting 28.647 ms after release. Decoding at 460800 8-N-1 produced
the exact candidate marker:

```text
DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001\n
```

The 379-line raw transition export is retained as
`hardware/validation/phase1_pico1_boot_460800_saleae.csv`, SHA-256
`dfd247a19730935651791f09c40d7784b3699819a64dd9c78823513815e4de93`.

A focused adapter regression now requires positive UART line-error flags to be
cleared without faulting the epoch while negative driver API results remain
fatal. The corrected 104,448-byte RP2350 image target-builds successfully under
Zephyr 4.4.2/SDK 1.0.1 with SHA-256
`94a633420025ed1564b8066ca48adb1dc5b619df7c17d754ec84939a81f86bc8`,
and was flashed on 2026-09-12. Sessions
`20260912T212549Z-09d805d0` and `20260912T213056Z-dbb8e66c` each completed a
15 s Enhanced boot test in the same connection epoch. Each received the
reset-induced `0x00` byte followed by the exact 62-byte fixture marker, reached
a 62-byte ring high-water mark, and reported zero overflow events and zero
dropped bytes. The first run's Saleae capture showed a good 100 ms commanded
`RUN` pulse and clean TX edges; `DBG_UART_IF_EN` remained at 3.3 V afterward.
During the second run at `DUT_VIO = 3.3 V`, the PPK2 measured 54 uA idle,
177 uA during reset, 108 uA during the TX burst, and a return to 54 uA idle.

## Load Results

| Profile | Runs | UART baud | Duration/stall | Max occupancy | Overflow events | Dropped bytes | Result |
|---|---:|---:|---|---:|---:|---:|---|
| Representative normal boot | 2 of 10 | 460800 | 15 s each; 100 ms reset | 62 bytes | 0 | 0 | Passing so far; exact marker in both sessions |
| Dense synthetic burst | 0 | 460800 | 15 s | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 100 ms | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 250 ms | Not run | Not run | Not run | Not run |
| Host backpressure | 0 | 460800 | 500 ms | Not run | Not run | Not run | Not run |
| Deliberate overflow | 0 | 460800 | Not run | Not run | Not run | Not run | Not run |

## Acceptance Checklist

- [ ] Ten consecutive representative normal boots produced zero overflow
  events.
- [x] The 460800-baud Pico 1 fixture emitted its exact build marker in a direct
  Saleae capture, with the raw transition export retained above.
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
