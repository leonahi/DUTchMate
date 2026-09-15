# Phase 1B Enhanced Workflow HIL Evidence

This record contains the 2026-09-15 configured reset/boot-test run against the
same Pico 1 Zephyr DUT fixture used for the Enhanced load profiles. Phase and
next-step ownership remain in `docs/development_status.md`.

| Provenance | Observed value |
|---|---|
| Debug Helper | Fully assembled Revision A translator prototype with a non-wireless Raspberry Pi Pico 2 (`rpi_pico2/rp2350a/m33`) |
| Pico 2 image | Opt-in Zephyr 4.4.2/SDK 1.0.1 stack diagnostic `build/dutchmate-rp2350-stack-probe-v2/zephyr/zephyr.uf2`; SHA-256 `3dd67569e0fda9042c72a96632a72a19626fdf55cc2cf01b3c6920565a6b3d66` |
| DUT fixture | Raspberry Pi Pico 1 `rpi_pico` opt-in Zephyr 460800-baud fixture; build marker `phase1-enhanced-460800-001` |
| Wiring/supply | User-confirmed UART, `CTRL0` to Pico 1 `RUN`, common ground, and `DUT_VIO=3.3 V` |
| Host | macOS 26.2; Debug Helper CDC `/dev/cu.usbmodem11201`; local Device Core Service at `127.0.0.1:2040` |
| Runtime selection | CLI `--backend enhanced --serial-port /dev/cu.usbmodem11201 --baudrate 460800`; UART TX policy enabled |
| Control mapping | `CTRL0` role `reset`, DUT signal `RUN`, `open_drain`, active low; configured through the public CLI before each boot test |

The first public `dutchmate boot-test --seconds 15` call used the host source at
commit `9d18bdb` and session `20260915T192952Z-2cf24586`. It completed a
100 ms configured reset and retained exactly 63 UART bytes: reset `0x00` followed
by `DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001\n`. The raw
SHA-256 was `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839`.
The first `buffer_status` had an empty current RX ring but reported a 6,045-byte
lifetime high-water, 23,663 lifetime dropped bytes, and six lifetime overflow
events from the preceding deliberate `BURST` session. The host incorrectly
interpreted those absolute MCU counters as this boot session's loss. It marked
`loss_reported` with 23,663 dropped bytes and overflow despite the exact clean
boot output. The initial session metadata and hardware-event SHA-256 digests are
`6a3cc039f83ddf5400ac82b8c691afc53238a389a7808af7958bd792306c374d`
and `9ca6f5946ab241b5b07aa04630bf5a4d014d755cd31aeb54d655b67bef428163`.

The corrected host treats the first status in each capture window as a baseline,
accounts for ordered explicit overflow records before that status, and reports
later counter increases as new loss. New sessions start with fresh Enhanced
integrity, while the raw `buffer_status` fields remain unchanged. Its corrected
repeat `dutchmate boot-test --seconds 15` produced session
`20260915T194748Z-78db848e`:

| Evidence | Corrected repeat result |
|---|---|
| Reset action | One accepted `CTRL0` pulse, 100 ms, device timestamp `2336115113` us |
| UART capture | Exact same 63 bytes and raw SHA-256 `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` |
| Timestamp provenance | Device `rp2350_timer`, `debug_helper_uart_receive/uart_event`, one segment |
| Session lifecycle | Completed after 15 seconds; no interruption, resume, truncation, or first error |
| Session integrity | `none_reported`, zero session dropped bytes, `overflow=false` |
| Lifetime status retained | First raw status still reported 23,663 MCU-lifetime dropped bytes, six MCU-lifetime overflow events, and 6,045-byte lifetime high-water |
| Public retrieval | `dutchmate session 20260915T194748Z-78db848e` returned the completed native v1 `boot_test` session, 63-byte raw artifact, five UART-event records, 16 hardware-event records, one segment, and `none_reported` integrity |

The corrected session's ignored local artifacts are under
`.dutchmate/sessions/20260915T194748Z-78db848e/`. SHA-256 digests:

| Artifact | SHA-256 |
|---|---|
| `metadata.json` | `4618f0f181d9edc8a64642cd60b27a18894d587db9e5510d60373d334ce03b69` |
| `uart_raw.log` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` |
| `uart_events.jsonl` | `a47f20e1cce8535044c013a4afcdd13401eedf4b9ba9e77fd175ec4fb9c192eb` |
| `hardware_events.jsonl` | `faf4e2905e2683ca4e5d09a24d9a7a3d8fae9ea6767a6658a4659b1b79093b94` |

The post-test public status remained connected with `none_reported` integrity.
The service was stopped after retrieval so DTR dropped and the Pico 2 returned
its control outputs to the safe idle state. The diagnostic firmware later
reported a frozen `stack-1of8-...` identifier during the corrected service
epoch; that identifier belongs to the same UF2 named above.

The host correction also passed a positive-loss repeat on the same image and
fixture. A public 15-second capture with a forced `BURST` UART send produced
session `20260915T195131Z-28e6d4b8`. It retained 19,079 bytes and six ordered
overflow records explicitly reported 24,002 dropped bytes, exactly reconciling
the fixture's 43,081-byte output. Both `BURST BEGIN count=2048` and
`BURST END count=2048 checksum=2096128` survived. Metadata reported
`loss_reported`, `debug_helper_rx_buffer`, 24,002 session dropped bytes,
`overflow=true`, and one uninterrupted segment. The first status contained
the previous MCU totals of 23,663 drops and six events; the final status
contained 47,665 drops and 12 events. Their 24,002-byte/six-event increase
matches the current-session overflow telemetry. Post-run host load averages
were 2.62/2.48/2.45. The helper report is
`build/enhanced-burst-after-counter-fix.json`, SHA-256
`fa3a34cf44ab3b8633889018a76cf795993c07232ec75a22a9fb3214cc4c41fb`.
The ignored session artifacts under
`.dutchmate/sessions/20260915T195131Z-28e6d4b8/` have SHA-256 digests:
metadata `80c552ae224ecb11f7fc60997c88f492b387df058b2005a77273bf8b43caaea4`,
raw UART `da7c06a2e5cdd359160981af9b488c122c7d9e5f21c58debbca3e86bbf7e245e`,
and hardware events `5ab4e3908668d18fc0d6781f5403b2147b42b1f356eff5bb138fbc33402e4835`.
The service was stopped afterward.
