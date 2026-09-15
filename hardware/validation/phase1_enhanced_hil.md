# Phase 1B Enhanced Workflow HIL Evidence

This record contains the 2026-09-15 configured reset/boot-test and USB reconnect
runs against the same Pico 1 Zephyr DUT fixture used for the Enhanced load
profiles. Phase and next-step ownership remain in `docs/development_status.md`.

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
integrity, while the raw `buffer_status` fields remain unchanged. The corrected
source and regression tests were committed as
`ab98caa67af19b624a782175f44ee64e3febdb58`. A repeat
`dutchmate boot-test --seconds 15` produced session
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

## Controlled USB reconnect

The operator unplugged and reconnected only Pico 2 USB while Pico 1, its UART
and `CTRL0` wiring, common ground, and `DUT_VIO=3.3 V` remained in place.
The service used the same `/dev/cu.usbmodem11201` path and 460800-baud DUT UART
setting throughout. An idle disconnect on the diagnostic image changed public
`connection_state` from `connected` to `disconnected` at 20:05:00 UTC and
back to `connected` at 20:05:30 UTC on the same port. The reconnecting idle
service had no active session. The ignored monitor record is
`build/reconnect-hil/idle-watch.jsonl`, SHA-256
`f3e754b8a89e3f822efe1609dd0b2020358fe5f430740befe2a4ecdf7ac7847e`.

The first active attempt used the opt-in stack diagnostic image and a configured
60-second reconnect window, within the documented 0.1–60-second range. Session
`20260915T200703Z-d86f54e3` entered `reconnecting` at 20:07:32 UTC with
59.9 seconds left, but the replacement `hello.firmware` did not match its
session-start value `stack-1of8-command-1112-3072`. The host returned HTTP
502 `backend_input_error: Reconnected Debug Helper identity changed`. Public
`dutchmate session` retrieval showed a failed, interrupted, unresumed session
with one preserved segment ending `usb_disconnect`; it did not append a
replacement segment. This is the required identity guard operating on an
unsuitable diagnostic image: `stack_probe.c` intentionally advances the
`stack-...` firmware identifier after each CDC epoch to expose frozen stack
readings. The ignored monitor record is
`build/reconnect-hil/active-watch.jsonl`, SHA-256
`5629275232233498c7016096e0b41d275c1b0a701cf31d174b956167cf8458c0`.
The failed session metadata SHA-256 is
`3656c59e07b38423d745f4da32c6822be29387bfc19dce4538377feff3d43e7f`.

The operator then flashed the normal, non-diagnostic Zephyr 4.4.2/SDK 1.0.1
`build/dutchmate-rp2350-normal-v2/zephyr/zephyr.uf2`, SHA-256
`5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`,
to Pico 2. After reboot, public status reported the stable `development`
firmware identifier and all five Enhanced capabilities. The Pico 2 image was
not read back; the UF2 digest and observed `hello` are the available image
provenance.

The normal-image repeat used the same 60-second window and a public 150-second
capture. A forced Pico 1 `PING` was sent before disconnect; two more were sent
after reconnect. The capture was session `20260915T201343Z-57c45321`:

| Evidence | Result |
|---|---|
| Connection | Active `reconnecting` at 20:15:00 UTC with 59.9 seconds remaining; active `connected` again at 20:15:15 UTC on the same port and `development` identity |
| Lifecycle | Completed `duration_elapsed`, `interrupted=true`, `resumed=true`, no truncation or overflow |
| Segments | Exactly two contiguous segments, both Enhanced/`development`; segment 0 ended `usb_disconnect`, segment 1 ended `duration_elapsed`; each has its own device `rp2350_timer` origin |
| Hardware evidence | One `usb_disconnect` on segment 0, one `usb_reconnect` on segment 1, one `timestamp_discontinuity` from 0 to 1 |
| UART evidence | Segment 0 contains `DMF/1 ERROR COMMAND code=E_COMMAND_001\n`; segment 1 contains two exact `DMF/1 PONG\n` lines, each with segment-relative device timestamps |
| Integrity | `none_reported`, zero current-session dropped bytes, `overflow=false` |
| Public access | `dutchmate session` returned the completed two-segment native session; `dutchmate logs --session ...` displayed separate segment 0 and 1 lines |

The first send record contains the exact five-byte `PING\n` payload
(`data_b64=UElORwo=`) and a successful physical-send acknowledgement. Pico 1
nevertheless emitted its generic `E_COMMAND_001` response; why its first
command was rejected is not established from this capture. The next two sends
of the same command returned `PONG`. The host correctly detected the fixture
error as the first downstream error in segment 0. It does not alter the observed
USB disconnect/reconnect or segment-resume result.

The ignored normal-image monitor
`build/reconnect-hil/active-normal-watch.jsonl` has SHA-256
`219d6ca0b03bb377e576cab13897464fd06491f074f07c6872d8907bc458dca1`.
The ignored completed session artifacts under
`.dutchmate/sessions/20260915T201343Z-57c45321/` have SHA-256 digests:
`metadata.json` `b17cb1e53d73a3ce036adf8483459672ffc78ebdb95787332dcd7d9ee36af28d`,
`uart_raw.log` `debc3fd50459ee9a8fe1fbaa42faa2a26dad39e832333db9af2eb8bffb6b9229`,
`uart_events.jsonl` `58553f24c4de7f9c75eda58fe5cfc5419447ea06f35cdd741bec8522ec6c8816`,
and `hardware_events.jsonl`
`0cd146811f25c6f717ce5f56646c2d84005c5110bad1b247097f087f0be14aeb`.
The service was stopped and the local reconnect configuration restored to its
5.0-second default afterward.

## Basic and Enhanced downstream evidence structure

The accepted Basic run in `hardware/validation/phase1_basic_hil.md` used the
same Pico 1 Zephyr fixture code at its default 115200 baud through an FTDI
adapter. Sessions `20260826T211103Z-2649d369` and
`20260826T211203Z-f541c8fb` stored raw UART bytes, normalized UART events,
metadata, and hardware events; event payloads reconstructed the raw log, and
both public session and recent-log retrieval succeeded. Basic reported
`not_observable` integrity and host-monotonic timestamp provenance. The
Enhanced boot and reconnect sessions recorded above used the same downstream
artifact names and public retrieval operations while reporting RP2350 device
timestamps and Enhanced buffer-loss telemetry.

A focused deterministic contract test,
`tests/unit/runtime/test_device_core_capture.py::test_basic_and_enhanced_capture_share_downstream_evidence_shape`,
now captures the same `DMF/1 PONG\n` bytes through fake Basic and Enhanced
event sources and the real shared `CaptureWorkflow`/`SessionStore` path. It
checks equal artifact filename sets, equal top-level metadata keys, equal
segment/backend field sets, identical normalized UART-event records, and equal
session-detail and recent-log field sets. Both modes return the exact PONG
line. Their explicit distinctions are Basic's null firmware/device, Basic
`uart_receive`/`uart_send` support, host-monotonic/serial-chunk provenance,
and `not_observable` integrity versus Enhanced's device/firmware identity,
GPIO capability, device-timer/UART-event provenance, and `none_reported`
integrity for the clean test.

The archived August Basic session directories are absent from this checkout,
so their historical field sets cannot be compared byte-for-byte to the
September Enhanced files. The committed Basic HIL report supplies the real
storage/retrieval result; the new contract test supplies a reproducible
same-source structural comparison on the current code baseline.

## Configured boot-mode workflow

The operator connected Revision A J3 pin 2 (`DUT_CTRL1`) to Pico 1 GP2
(physical pin 4), kept `DUT_CTRL0` on Pico 1 `RUN` (pin 30), left GP3 open,
and retained the 460800-baud UART, common ground, and `DUT_VIO=3.3 V`.
Pico 2 ran the normal Zephyr 4.4.2/SDK 1.0.1 UF2 SHA-256
`5a706740df03b046cbbbee68c2b6668b33cbabee06e08003edb16f21060c8819`
on `/dev/cu.usbmodem11201`. The public CLI configured `CTRL0` as
`reset -> RUN`, `open_drain`/active-low, and `CTRL1` as
`boot -> GP2`, `push_pull`/active-high/idle-low. Status confirmed both
accepted mappings and commanded mode `normal`.

The Pico 1 fixture samples GP2 once at startup and requires strap changes
while unpowered or held in reset. For both mode transitions, the operator
temporarily jumpered Pico 1 `RUN` to GND while leaving `DUT_CTRL0` wired
in parallel. The `bootloader` command drove GP2 high only during that hold;
its response reported `performed_at=2026-09-15T20:43:47.798353Z` and
`device_timestamp_us=1714277106`. After the jumper was removed, a public
`boot-test --seconds 15` pulsed `CTRL0`. The operator held `RUN` low again
for the `normal` command, whose response reported
`performed_at=2026-09-15T20:47:06.212054Z` and
`device_timestamp_us=1912690435`, then removed the jumper before the
restored-normal boot test.

| Session | Commanded mode | Exact raw evidence | Result |
|---|---|---|---|
| `20260915T203733Z-7d502d02` | `normal` | Reset `0x00` + `DMF/1 BOOT OK board=rpi_pico build=phase1-enhanced-460800-001\n` = 63 bytes | Completed, one segment, no first error |
| `20260915T204533Z-0d15abc2` | `bootloader` | Reset `0x00` + `DMF/1 ERROR INIT code=E_INIT_001 board=rpi_pico build=phase1-enhanced-460800-001\n` = 82 bytes | Completed, one segment, `ERROR` detected at segment 0/event 6 |
| `20260915T204741Z-617d85d9` | `normal` | Exact same 63-byte normal evidence and SHA-256 as the first session | Completed, one segment, no first error |

Each session persisted one accepted 100 ms `control_action` reset with raw
device timestamp: `1339767313`, `1819688434`, and `1947790470` us,
respectively. Every capture reported device `rp2350_timer` UART timestamps,
`none_reported` integrity with zero current-session dropped bytes, no
overflow, interruption, resume, or truncation. Public `dutchmate session`
retrieval returned native `boot_test` details; public `dutchmate logs`
displayed the expected fixture line in each session. Local assertions verified
the exact raw bytes, reconstruction from `data_b64` UART events, session
mode snapshots, reset evidence, and detected-error record.

The ignored session artifacts have these SHA-256 digests:

| Session | `metadata.json` | `uart_raw.log` | `uart_events.jsonl` | `hardware_events.jsonl` |
|---|---|---|---|---|
| First normal | `37b99d4bf3f6176d738adde1ca66223543f9f5c` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` | `52372b530e964dabdfca2966f2ad6bccf2748eb84e7719249a2e2ea1ef07ba8a` | `eb02250b46e763f654c3549d237eff2b12c4b26e28199579d4b5997f9a334f45` |
| GP2-high failure | `e79c42280d821fa12e16773aba64cc291f39884bb455701794849f9dc5afe1cc` | `7ac5b2f71bfd7f1d4da1edf607407c8cfcec70c4e4cb9dc2fd333c6aa26481e4` | `e648de80493348e88c4e494ebae3ab3108f8df6280a9f7210fb1cc55c2814dfe` | `b50d2b732c91efbfc9a8cf9459e9b56b585b18b5d8af267be20900426579ead5` |
| Restored normal | `7357f072c86851c51517c6ba7740736d246b11f6f81a061c7c0f1296e3c5b26d` | `61d68d9fa252ca54eeb95509d6f961e3bd46e74ea357c967eef0aaff7ae95839` | `f4d56c67c653c1e9c035248a79e6f4256ecfebc9f149885bed9a74612c1429b8` | `41cf83eae141106d727defdef070c4027327df37013fbf76527984ae43ed3398` |

A post-restoration forced `PING` in capture
`20260915T204855Z-51d462a8` returned exact `DMF/1 PONG\n`, one
in-session `uart_tx_attempt`, no first error, and `none_reported`
integrity. Its raw SHA-256 is
`ddca019a59596c677f2d348609ac57c9ab0c1967d3b71f64ce6b443f548cf8da`.
The earlier first-`PING` fixture rejection did not recur after this clean
reset, but its cause remains unestablished. The service was stopped after
retrieval, returning the control outputs to high impedance while Pico 1 GP2
retained its internal pull-down.
