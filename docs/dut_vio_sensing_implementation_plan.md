# DUT_VIO Sensing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> `superpowers:executing-plans` for approved native execution, or
> `superpowers:subagent-driven-development` if the user chooses delegation.
> Task checkboxes are temporary execution aids, not a second progress tracker.

**Goal:** Implement the approved report-only DUT_VIO extension through firmware,
durable evidence and existing status/CLI/MCP delivery.

**Architecture:** Extend the existing Enhanced protocol and single-owner recorder.
ADC/serial details remain in their adapters; immutable sensing values and status
policy remain framework-independent. Preserve existing control behavior and
connection ownership rather than introducing a parallel sensing service.

**Tech stack:** Python 3.10+, existing FastAPI/Typer/MCP delivery, C, Zephyr 4.4.2,
Raspberry Pi Pico 2/RP2350A Cortex-M33, Zephyr SDK 1.0.1.

**Spec:** [Approved DUT_VIO contract](dut_vio_sensing_contract.md).
The contract defines all wire/status fields and acceptance criteria; read it
alongside this plan. Base: `4880590`; software-fix baseline: `81ab6f8`.

This is a temporary implementation aid. Record current progress only in
[Development Status](development_status.md), evidence in
[Development History](development_history.md), and remove this plan after the
slice is complete. Keep durable decisions in the sensing contract and architecture.

## Global constraints

- Report only; preserve configured `hardware.dut_io_voltage`, output control,
  UART acquisition, existing timeouts, ownership and historical evidence.
- GP28/ADC2 only; preserve digital-disable-before-ISO-release initialization and
  GP26 CTRL2 enable. ADC: 12-bit, gain 1, one conversion in flight, 20 ms deadline.
- Publication: 1000 ms slots; nominal reference 3300 mV; build reference range
  2500–3600 mV; status validity boundary 3000 integer receipt-age ms.
- Protocol v1 extension is opt-in per epoch. Existing/new host/helper combinations
  must work as defined in the contract. No metadata schema bump or new MCP tool.
- Keep the operator's two dirty KiCad files out of software edits and commits.
  No flash, pause signal, service startup or physical test during software checks.
- Use TDD for changed behavior and focused checks while developing; run the full
  required gate once near completion. Keep commits coherent and independently
  testable; no automatic commit merely because a task checkbox exists.

## Review focus

| Risk | Owning task and required regression |
|---|---|
| Enable ACK and first sample in the same serial-read batch | Task 5: accept the sample after processing its ACK, before the request coroutine resumes |
| Late ADC completion after timeout, disable or epoch end | Tasks 2–3: retain buffer ownership, discard late data and prevent cross-epoch publication |
| Rollover/delayed admission makes old data appear newly received | Task 4: preserve receipt marker and correct current-session evidence references |
| Older UART chunks remain queued when the first voltage observation is ready | Tasks 3 and 7: preserve the observation barrier and valid timestamp origin under congestion |
| Old readers/new helpers or malformed telemetry corrupt an existing session | Tasks 1, 4–5: strict validation, no unsolicited frames, generic old-v2 retrieval and unchanged legacy bytes |

## Shared interfaces and file ownership

Names below are the seams between tasks. Keep other helpers private. New files
are limited to a cohesive sensing-value/policy module, a deterministic firmware
sampler and their tests; extend established modules for existing responsibilities.

| Location | Interface/change |
|---|---|
| New `core/src/dutchmate_core/dut_vio.py` | Frozen `DutVioSample(status, adc_raw, voltage_mv, adc_reference_mv, reference_source)` with invariant validation; `DutVioObservation(sample, timestamp_us, received_at_monotonic, session_id, segment_id, evidence_seq)` for admitted observations; typed `DutVioStatus` and `project_dut_vio_status(...)` |
| `device_connection/messages.py`, `parser.py`, `commands.py` | `DutVioMessage(timestamp_us: int, sample: DutVioSample)`; `ConfigurePowerSenseCommand(enabled: bool).to_ndjson() -> bytes`; parse/validate the flattened contract fields |
| `backends/contracts.py`, `enhanced.py`, `enhanced_serial.py` | `DutVioEvent(segment_id: int, timestamp_us: int, sample: DutVioSample, received_at_monotonic: float)` added to `BackendEvent`; `AsyncEnhancedSerialAdapter.configure_power_sense(*, enabled: bool, timeout_s: float) -> bool` returns false only for explicit rejection |
| `workflows/capture.py`, `evidence/recorder.py` | Optional runtime-checkable `BackendObservationInitializer.initialize_observation() -> bool` (false only for explicit setup rejection); `CaptureSourceHealth` adds defaulted observation/setup-rejection fields; recorder owns admission and live projection |
| `session_store/store.py` and recorder store protocol | `append_v2_dut_vio(handle: SessionHandle, *, event: DutVioEvent) -> V2EvidenceAdmission`; extend existing telemetry rollover handling |
| `runtime.py` | `DeviceCoreStatus.dut_vio: DutVioStatus`; `DeviceCoreRuntime.initialize_backend_observation() -> None` delegates startup setup to the recorder; project status using the existing injected monotonic clock; no serial imports |
| New helper `src/vio_sense.c` / `.h` | `struct dmh_vio_sense`, immutable `struct dmh_vio_observation`, and `dmh_vio_sense_init/configure/poll/take_observation/end_epoch`; USB owner alone advances this deterministic state |
| Helper `platform_io.c` / `.h` | `int dutchmate_platform_vio_initialize(void)` and `struct dmh_vio_adc_port dutchmate_platform_vio_port(void)`; callbacks keep one static ADC buffer owned until driver completion |

`project_dut_vio_status(*, connection_state: str, capable: bool,
setup_rejected: bool, observation: DutVioObservation | None,
now_monotonic: float) -> DutVioStatus` is the pure policy entrypoint. Implement
the contract's precedence/nullability there; delivery only serializes/formats it.
Represent sample/reference enums with typed literals; avoid generic state dictionaries.

The firmware state seam uses these signatures in `vio_sense.h`:

- `void dmh_vio_sense_init(struct dmh_vio_sense *state, const struct dmh_vio_adc_port *adc, uint16_t reference_mv, bool reference_measured)`.
- `int dmh_vio_sense_configure(struct dmh_vio_sense *state, bool enabled, uint64_t now_us)`.
- `void dmh_vio_sense_poll(struct dmh_vio_sense *state, uint64_t now_us)`.
- `bool dmh_vio_sense_take_observation(struct dmh_vio_sense *state, struct dmh_vio_observation *out)`.
- `void dmh_vio_sense_end_epoch(struct dmh_vio_sense *state)`; discard logical
  observations without resetting driver-owned outstanding conversion memory.

`dmh_vio_adc_port` provides context, nonblocking `start(context) -> int`, and
`poll(context, uint16_t *raw, uint64_t *completed_us) -> enum dmh_vio_adc_result`
with `DMH_VIO_ADC_PENDING`, `DMH_VIO_ADC_COMPLETE`, `DMH_VIO_ADC_ERROR` results.
Platform I/O constructs this port; hardware
completion time is captured at completion, not when USB later polls it. An
observation taken into the USB scheduler replaces its single unsent observation.

## Task 1 — Typed sensing values and private wire contract

- [ ] Add the new value module, message/command models, parser dispatch and backend
  event export. Update both `hardware/protocol/v1/` schemas and add examples for
  enable, successful voltage, ADC error and saturation as
  `examples/power_sense_configure.json`, `examples/dut_vio.json`,
  `examples/dut_vio_adc_error.json` and `examples/dut_vio_saturated.json`;
  keep current frames valid.
- First reproduce missing support using the actual parser/encoder/schema consumers
  in `tests/unit/protocol/test_device_message_{parser,schema,examples}.py` and
  `test_host_command_{encoder,schema}.py`; add `tests/unit/test_dut_vio.py` for
  value invariants. Pin literal vectors `0→0`, `1024→1650`, `2048→3300`,
  `3072→4950`; reject booleans, extra/missing fields, inconsistent mV,
  illegal null/status combinations and reference bounds 2499/3601.
- Implement only after those regressions fail for missing behavior. Do not reuse
  the production conversion helper to calculate expected test values.
- Verify: `rtk proxy .venv/bin/pytest -q tests/unit/protocol tests/unit/test_dut_vio.py`.
  Acceptance: all existing examples plus the new strict contract cases pass.

## Task 2 — Bounded ADC sampling with safe pin configuration

- [ ] Add `src/vio_sense.c/.h`; extend helper `Kconfig`, `prj.conf`,
  `CMakeLists.txt`, board overlay and `platform_io.c/.h`. Keep voltage publication
  disconnected until Task 3 supplies negotiation and complete-frame scheduling.
- Use Zephyr asynchronous ADC with GP28-only pinctrl and the existing safe pad
  sequence. Keep platform driver/buffer ownership separate from the pure sampler;
  a timeout marks unavailable but never cancels by reusing its buffer. Set
  build reference/provenance explicitly and preserve normal/readback/stack builds.
  Enable `CONFIG_ADC=y` and `CONFIG_ADC_ASYNC=y`; add
  `CONFIG_DUTCHMATE_ADC_REFERENCE_MV` (3300, range 2500–3600) and
  `CONFIG_DUTCHMATE_ADC_REFERENCE_MEASURED` (default n), mapped to the contract's
  reference fields. Retain test-only hardware stubs where platform headers change.
- Add `tests/hardware/rp2350_debug_helper/vio_sense_harness.c` and
  `test_vio_sense.py`; extend `test_sense_pin_probe.py` and
  `test_firmware_configuration.py`. RED cases cover conversion/rounding, zero,
  saturation, setup/read failures, 20 ms timeout, late completion, one in-flight
  buffer, missed-slot skipping and replacement of one pending observation.
  Pin completion at 20000 versus 20001 µs, and delayed USB polling after an
  on-time completion, using the completion timestamp supplied by the ADC port.
- Verify: `rtk proxy .venv/bin/pytest -q tests/hardware/rp2350_debug_helper/test_vio_sense.py tests/hardware/rp2350_debug_helper/test_sense_pin_probe.py tests/hardware/rp2350_debug_helper/test_firmware_configuration.py`.
  Acceptance: state-machine behavior passes with strict host-C warnings and no
  control-pin or pad initialization regression.

## Task 3 — Firmware negotiation, ACK handoff and ordered output

- [ ] Extend helper `command_decode.c/.h`, `command_executor.c/.h`,
  `command_runtime.c/.h`, `hello.c/.h`, `telemetry.c/.h` and `usb_connection.c`.
  Advertise `power_sense` only with the working implementation wired in.
- Decoder/executor accept `configure_power_sense` and stage the existing ACK.
  Extend `dmh_command_executor_init` with a `const struct dmh_command_vio_port *vio`
  whose context and `int (*prepare)(void *context, bool enabled)` callback validate
  readiness and stage intent without modifying USB-owned sampler state. Migrate
  all initializer callers, including C harnesses, rather than adding a legacy shim.
  The command worker stages an epoch-tagged configuration intent; it must not
  mutate USB-owned sampler state. After successful complete ACK transmission,
  pass that intent through the existing response-consumed synchronization and a
  bounded mailbox to the USB owner. Drop old-epoch intents and observations.
- Add `dutchmate_command_runtime_take_sense_configuration(bool *enabled) -> bool`
  for the USB owner; it returns only acknowledged, current-epoch intent. Sampling
  starts on consumption. Shared ADC completion uses Zephyr's completion signal;
  no unprotected worker/USB/ISR access to sampler state or sample memory.
- Extend command/hello/telemetry/output-drain harnesses; add regression coverage
  for no frames before enable ACK, idempotent enable, disable, DTR loss,
  failed ACK transmission, epoch change before intent consumption, and sustained
  UART with observation-sequence barriers. Check maximum identity/frame sizes.
- Verify: `rtk proxy .venv/bin/pytest -q tests/hardware/rp2350_debug_helper`.
  Acceptance: no unsolicited frames; ACK and byte/timestamp ordering preserved.

## Task 4 — Durable observations, rollover and live health

- [ ] Extend `evidence/recorder.py`, `workflows/capture.py`,
  `session_store/store.py`, `retrieval.py`, `tail.py` and relevant type exports.
  Reuse the existing admission transaction and telemetry quota/rollover path.
- Persist Task 1 events as hardware `dut_vio` records; retain normalized time
  and portable evidence fields, but never serialize process-local monotonic time.
  Publish `DutVioObservation` into synchronized recorder health only after commit.
  Reset it at physical segment boundaries and retain receipt time through logical
  rollover. Update the telemetry-tail whitelist for voltage/reference scalars;
  do not expose arbitrary new record fields.
- Add `tests/unit/session_store/test_dut_vio.py` and extend
  `tests/unit/evidence/test_recorder.py`. RED cases cover failed/blocked commit,
  rollback, quota exhaustion, rollover with correct evidence references, stale
  queued input, boundary reset, recovery and UART pattern/loss non-interference.
- Export the pre-extension readers at `4880590` to an isolated temporary snapshot
  and query a new-type fixture through detail and tail. Assert contiguous evidence
  and generic type/count retrieval; do not claim old readers understand voltage.
  Hash historical fixtures before/after compatibility checks.
- Verify: `rtk proxy .venv/bin/pytest -q tests/unit/evidence tests/unit/session_store`.
  Acceptance: every published sample has retrievable committed evidence and no
  reference or freshness is fabricated across a boundary.

## Task 5 — Host negotiation and connection lifecycle

- [ ] Extend `backends/enhanced.py`, `enhanced_serial.py`, `workflows/capture.py`,
  service `enhanced_async.py`, `startup.py`, `app.py`, `backend_reconnect.py`,
  and the recorder/runtime initialization seam used by staged replacements.
- Implement Task 1's adapter API under its existing request serialization.
  Match the pending negotiation ACK in `_dispatch_batch` and transition enabled
  state there, before consuming a following sample in that same batch. Attach
  the monotonic receipt marker at input dispatch, before queue admission.
  Add the voltage type to `enhanced_message_timestamp_us`; extend
  `normalize_enhanced_message` with optional keyword `received_at_monotonic: float | None`.
  Require that marker for voltage normalization; preserve existing callers for
  UART/overflow/status messages without manufacturing a receipt time later.
- `EnhancedAsyncHost.initialize_observation() -> bool` implements the optional setup
  protocol; it is idempotent per concrete host/segment and records explicit
  setup rejection for health. Missing capability is a successful no-op. Use this narrow
  setup boundary rather than adding sensing methods to `DeviceControl`.
- Invoke optional setup after initial profile application (including an empty
  control mapping): `create_app` calls runtime's initializer after startup config,
  which delegates through `ContinuousEvidenceRecorder.initialize_observation()`.
  In `_replace_source_admitted`, invoke the same private setup helper explicitly
  on `replacement` after the profile initializer and before lifecycle success;
  the recorder has not installed `replacement` as `_source` at that point.
  Never capture the initial host in a permanent callback.
  Keep ambiguous ACK/timeout/cleanup handling and existing deadlines intact.
- RED tests in `tests/unit/backends/test_enhanced_serial.py`, service
  `test_enhanced_async.py`, `test_enhanced_control_lifecycle.py` and
  `test_enhanced_transport_reconnect.py` cover all four compatibility cases,
  same-batch ACK/sample, unsolicited data, explicit rejection, no-control startup,
  new-segment enable, setup timeout and shutdown while enable is pending.
- Verify those four test files together; acceptance includes preserved original
  cleanup exception identity and existing control ACK order.

## Task 6 — Runtime status, HTTP, CLI and existing MCP status

- [ ] Implement Task 1's `project_dut_vio_status` in the value module; extend
  `runtime.py`, service `schemas.py`, and CLI `status.py`. Existing MCP
  `service_client.py`/`server.py` pass status through; change them only if actual
  integration proves an adaptation is necessary. Preserve the twelve-tool set.
- Add the contract's six-key `dut_vio` object to status. Use the existing injected
  monotonic clock, connection-first precedence and receipt-age calculation.
  Preserve existing status fields; CLI shows the contract's approximate nominal
  voltage line or an explicit state/reason without a standalone stale value.
- Extend `tests/unit/test_dut_vio.py`, runtime `test_device_core_status_control.py`,
  service `test_status_endpoint.py`, CLI `test_status.py` and MCP
  `test_protocol_integration.py`. RED cases pin 3000 versus 3001 ms, valid zero,
  measured/nominal reference, outside-range observations, saturation/ADC error,
  disconnected precedence, release/reconnect/reacquire and absent capability.
- Verify these five files together. Acceptance: service, CLI and the real MCP
  tool see the same authoritative status/evidence, with no independent reads.

## Task 7 — Integrated gate, firmware artifacts and physical handoff

- [ ] Add/extend real pipe/recorder integration tests for high-rate UART with
  sensing, batched ACK/sample input, startup/reset controls, automatic reconnect,
  release/reacquire, retention rollover and shutdown. Assert exact UART bytes,
  contiguous evidence and absence of extra reader/transport ownership.
- Build normal, pad-readback and stack-probe images from the pinned west workspace
  at `/Users/nahitpawar/zephyrproject`, using the existing README procedure with
  `-b rpi_pico2/rp2350a/m33`, explicit new firmware identities and separate
  repository `build/` directories. Inspect generated ADC pinctrl/configuration,
  retain image hashes and memory/stack results, and preserve existing UF2 files.
- Run the final gate: `rtk proxy .venv/bin/pytest -q --tb=short`,
  `rtk proxy .venv/bin/ruff check .`, `rtk proxy .venv/bin/mypy`,
  `rtk proxy env UV_CACHE_DIR=/tmp/dutchmate-stage8-uv-cache uv lock --check --offline`,
  architecture/dependency checks and `rtk git diff --check`. All must pass.
- Review every new shared-event consumer and stale reference; update
  `docs/software_architecture.md` and firmware/usage docs for actual ownership.
  Run `rtk proxy graphify update .` once after structural changes and report any
  extraction warning. Update current status/history with actual validation;
  reconcile code references after requested commits and remove this working plan.
- Prepare the contract's Fluke/actual-VIO campaign and source/image provenance
  before live use. Software completion does not imply ADC accuracy, physical
  sensing acceptance or full board acceptance. Confirm operator setup/access
  before any later flash or measurement; leave those results explicitly pending
  until performed. Phase 4 and EVENT capture remain outside this slice.
