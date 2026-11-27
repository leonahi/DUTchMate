# DUT_VIO Voltage-Sensing Contract

> Approved report-only design contract, 2026-11-24.
> This document defines the extension, not its implementation or acceptance status.
> Task progress and reviews belong in GitHub Issues and PRs; milestone acceptance
> is summarized in the [milestone overview](../development_status.md).

## Purpose and scope

An Enhanced helper measures its DUT-supplied interface reference and exposes the
observation through durable evidence, service status and `dutchmate status`.
The user selected reporting only. Measurements do not enable, disable, reconfigure
or gate CTRL outputs, UART, EVENT interfaces, reset or boot actions. Configured
`hardware.dut_io_voltage` remains an optional user declaration and is never
overwritten. Omitting it does not prevent Enhanced startup or GPIO control.

This is an extension beyond the existing Phase 1 sensing exclusion, not an
additional Phase 1 completion criterion. It does not add current measurement,
power switching, EVENT capture, a public sampling command, or a new MCP tool.
Existing MCP status exposure follows the service's status projection.

Existing authorities remain:

- [Phase 1 specification](phase1_implementation_spec.md), particularly §§8, 11–12
  and the continuous acquisition, evidence, ownership and failure contracts.
- [KiCad Rev-A electrical mapping](../../hardware/pcb/debug-helper/rev-a/README.md#hardware-defined-dut_vio-sense-isolation).
- [Reconnect semantics](reconnect_session_semantics.md) and
  [software architecture](../software_architecture.md).
- [Protocol schemas](../../hardware/protocol/v1/device_to_host.schema.json), examples
  and typed parsers, which must change together when this extension is implemented.

## Hardware and conversion

The supported mapping is the current KiCad Rev-A helper: TMUX2819 isolation,
R10/R11 = 47 kΩ/47 kΩ, C7 = 10 nF, GP28/ADC2 and common/analog ground. Firmware
does not control the TMUX. A zero reading measures the interface reference at
this connector; it does not prove the entire DUT is unpowered.

Use Zephyr's ADC driver on channel 2, single-ended, gain 1 and 12-bit resolution.
Replace the board ADC pinctrl state with a valid, empty state: the pinned Pico
pinctrl implementation enables digital input and clears ISO before setting final
pull/input flags, so it must write no ADC pads during driver initialization.
The existing ordered `GPIO_DISCONNECTED`/ISO path alone configures GP28 with
digital input, output and pulls disabled; ADC channel 2 selects its analog input
independently. The board's default group includes GP26 (CTRL2 enable) and must
not be applied. Preserve pad-readback diagnostics. This empty-state detail
supersedes the original GP28-only generic pinctrl proposal to preserve its
required electrical startup invariant.

The first version takes one conversion per observation. There is no averaging,
automatic calibration or extra ADC channel. At most one conversion is in flight;
sampling and USB transmission must not block continuous UART acquisition or
command execution. Use asynchronous ADC completion with a 20 ms observation
deadline. On expiry, report an ADC error and quarantine the outstanding request
and its static buffer until the driver signals completion. Never reuse that
buffer or start a second request merely because an epoch or deadline ended.

The reference is the voltage at the Pico's ADC reference, not an independently
measured internal standard and not an inferred value from DUT_VIO. Build-time
configuration supplies `adc_reference_mv` (2500–3600, default 3300) and
`reference_source` (`nominal` by default, or `measured`). `measured` is allowed
only with a retained measurement at ADC_VREF, physical pin 35, and build/image
provenance for this specific helper. Pin-36 3V3 measurements alone are not that
calibration. [Raspberry Pi's pin documentation](https://www.raspberrypi.com/documentation/microcontrollers/pico-series.html)
identifies pin 35 as ADC_VREF. No service profile or persisted user configuration
is changed.

Use integer arithmetic with a wide intermediate and round once to nearest mV:

```text
voltage_mv = (adc_raw × adc_reference_mv × 2 + 2048) // 4096
```

The fixed multiplier 2 follows the nominal divider. With a nominal 3300 mV
reference, hand-checked vectors are 0→0, 1024→1650, 2048→3300 and 3072→4950 mV.
The raw range is 0–4095. Do not clamp a computed value to the supported
1.8–5.0 V operating range or treat a valid zero as an ADC failure. Do not claim
millivolt accuracy from millivolt storage units; reference, divider, ADC and
switch errors still require physical characterization. ADC full-scale code
4095 is reported as `saturated`, without presenting a precise voltage.

## Negotiated private protocol

Keep protocol v1 and add an opt-in extension. Firmware implementing this contract
includes `power_sense` in `hello.capabilities`. It sends no new message type
until explicitly enabled, so existing hosts retain their existing frame set.
New hosts skip negotiation when an older helper lacks the capability.

One private command enables or disables a fixed 1000 ms publication interval:

```json
{"cmd":"configure_power_sense","enabled":true}
```

Only `cmd` and boolean `enabled` are allowed. Acceptance uses the existing
`{"ok":true,"timestamp_us":...}` response, with no extra response fields.
Enable is idempotent; disable cancels pending publications and prevents new
conversions without reusing any still-active ADC buffer. The first observation
is scheduled immediately after the enable ACK; subsequent sampling deadlines
are 1000 ms apart with missed slots skipped, never replayed in a burst.
Only the current unsent observation may be retained; a newer observation can
replace it before transmission. This is periodic telemetry, not an edge log.

The host enables sensing once per opened connection segment after the existing
profile initialization completes, using the existing serialized command path.
It waits for the ACK without waiting for a sample before declaring readiness.
Explicit setup rejection leaves voltage unavailable and UART/control usable.
Command timeout, ambiguous response, malformed input and transport failure
retain their existing terminal/cleanup handling; they are not silently ignored.
The adapter accepts voltage observations only after a successful enable ACK
from a helper advertising `power_sense` in that segment. An unsolicited frame
outside that negotiated state is a protocol violation, not a source of live voltage.

A successful observation has exactly these fields:

```json
{"type":"dut_vio","timestamp_us":1234567,"status":"ok","adc_raw":2048,"voltage_mv":3300,"adc_reference_mv":3300,"reference_source":"nominal"}
```

`timestamp_us` is the existing RP2350 monotonic clock at conversion completion.
All numeric fields are JSON integers, never booleans. `adc_reference_mv` and
`reference_source` obey the conversion contract above. `voltage_mv` must match
the stated conversion exactly, including when it is outside the operating range.
Unknown/extra fields remain invalid under the strict schema/parser policy.

Two observation failures use the same keys and bounded schema:

| `status` | `adc_raw` | `voltage_mv` | Meaning |
|---|---|---|---|
| `adc_error` | `null` | `null` | Conversion failed or exceeded its deadline; timestamp is failure observation time |
| `saturated` | `4095` | `null` | Conversion completed at full scale; timestamp is completion time |

The timestamp of an error is never presented as the timestamp of a successful
measurement. An ADC error does not fabricate a zero or fault the UART/control
path. While enabled, an unresolved timed-out conversion produces at most one
error observation per publication slot; valid sampling may resume after its
late completion has been discarded. DTR loss, USB disconnect or epoch end
disables publication, drops pending observations and requires fresh negotiation.

Retain complete-frame output, ACK priority and bounded UART draining. Integrate
the voltage observation with the existing UART observation-sequence barrier so
it cannot precede older queued UART observations and establish an invalid
timestamp origin. No raw JSON is inserted outside the existing frame writer.

Compatibility matrix:

| Host | Helper | Behavior |
|---|---|---|
| Existing | Existing | Existing behavior |
| New | Existing | No sensing command; status says unsupported |
| Existing | New | No negotiation and no voltage frames; existing UART/control behavior |
| New | New | Negotiate per segment, record observations and expose status |

## Evidence and host state

Add a typed message and backend event rather than overloading UART bytes or
buffer-loss telemetry. Preserve timestamp normalization, the single source
owner, bounded queues and recorder ordering. The event carries a host monotonic
receipt marker for live age calculation; that process-local clock is not
serialized as a portable timestamp.

Persist each received observation as a `dut_vio` record in schema-v2
`hardware_events.jsonl`, retaining the wire fields, normalized segment timestamp,
session/segment identity and normal durable evidence sequence/recording time.
Use the existing transactional admission, quota, rollover, recovery and tail
mechanisms. This does not add a file, change existing record layouts, rewrite
historical sessions or reinterpret schema-v0/v1 evidence. A voltage observation
does not alter UART loss/integrity or satisfy a UART Monitor/Interact condition.

The new reader validates known voltage records and preserves generic counting
and retrieval for other hardware record types. Schema-v2 primary records already
carry a string type; this is an additive record type, not a metadata schema bump.
Compatibility checks must confirm that the pre-extension v2 detail/tail readers
can retrieve/count it without inferring voltage semantics. Older AI/report
consumers are not extended as part of this slice.

Publish the live observation only after durable admission. Status includes an
evidence reference (`session_id`, `segment_id`, `evidence_seq`) for the displayed
observation. The last observation is held in the recorder's existing synchronized
health projection, not a second serial reader or a separately writing poller.
Reset that projection at disconnect, release, reconnect/reacquire boundaries and
shutdown; no sample can cross to another physical connection segment. On storage
rollover, retain correct current-session references and never refresh the receipt
age simply because the logical stored segment was renumbered.

## Status and CLI

Add one `dut_vio` object to service status. Its keys are `state`, `reason`,
`voltage_mv`, `age_ms`, `sample` and `evidence`. All keys are present; absent
values are `null`. `sample` contains the last observation's wire fields with the
normalized timestamp; `evidence` contains the three reference fields above.
`age_ms` is elapsed host monotonic time since receipt, floored to integer ms
and clamped to zero, not time since a status request or durable commit. Apply
the 3000 ms state boundary to that integer. It is an arrival-age measure, not a
guarantee about measurement age when USB or the host has buffered traffic.

| `state` | `reason` | Public voltage |
|---|---|---|
| `unsupported` | `capability_missing` | `null`; Basic or connected older helper |
| `unavailable` | `awaiting_sample` | `null`; enabled, no durably admitted observation yet |
| `unavailable` | `setup_rejected` | `null`; helper explicitly rejected enable |
| `unavailable` | `adc_error` or `saturated` | `null`; matching observation retained in `sample` |
| `unavailable` | `disconnected`, `reconnecting`, `released`, `reacquiring` or `faulted` | `null`; no retained live sample/evidence/age |
| `valid` | `null` | Last successful mV value, receipt age ≤3000 ms |
| `stale` | `sample_timeout` | `null`; receipt age >3000 ms; last successful observation retained in `sample` |

Connection state takes precedence over capability and sample state. With no
selected/connected backend, status is unavailable/disconnected, not unsupported.
A current error observation takes precedence over a previous successful value;
its error reason remains until a new observation arrives or the segment ends.
Staleness never authorizes control changes. Status does not restore a live
sample from an old session at service restart. Clock injection follows existing
test/adapter boundaries; there is no broad clock-interface refactor.

`dutchmate status` adds a concise line such as
`DUT VIO: ≈3.30 V (nominal reference; received 120 ms ago)` for a valid nominal
reading. Stale, unsupported and unavailable states print their state/reason,
never a standalone last-known voltage. The HTTP value remains integer mV.
A measured reference is labeled as such; it is not a claim that all measurement
errors have been calibrated. Preserve all existing status fields and behavior.

## Component ownership

| Responsibility | Existing area to extend |
|---|---|
| ADC configuration and bounded sampling | Helper overlay/Kconfig/config, platform I/O and a focused sensing module |
| Negotiation and complete-frame scheduling | Helper command decode/runtime, hello and USB output scheduling |
| Private contract | v1 schemas/examples, command encoder and device message parser/models |
| Normalized observations | Enhanced adapter and shared backend event contract |
| Durable admission and live projection | Recorder, session-store admission/retrieval and existing health/status path |
| Delivery | Service status schema/serialization, CLI status formatter and existing MCP status projection |

Keep framework/serial/ADC details out of application/domain policy. No new
interface is required solely to mirror the existing layers. Changes to shared
events, persistence and status must be tested against their actual consumers;
update architecture ownership documentation and Graphify once after meaningful
structural changes, not for authoring this contract.

## Acceptance criteria

Software acceptance requires:

1. C harnesses cover conversion vectors/boundaries, ADC failure/saturation,
   timeout/late completion, epoch changes and bounded observation replacement.
2. Firmware pin initialization tests and a real Zephyr 4.4.2 build confirm that
   ADC boot pinctrl writes no pads and only GP28 is configured for sensing,
   with safe digital/pull/ISO settings and
   unchanged control/UART mappings. Normal and diagnostic configurations build.
3. Schema/parser/encoder tests cover strict types, exact conversion consistency,
   enable/disable ACK order and all four host/helper compatibility combinations.
   Worst-case hello/telemetry frames fit the bounded writers, including the
   existing maximum firmware-identity length; do not shorten identity limits.
4. Recorder/store tests cover durable publication, evidence references, rollback,
   quotas, rollover, recovery, tail retrieval, old-v2-reader compatibility and
   unchanged legacy evidence. UART pattern/loss/provenance semantics stay intact.
5. Runtime/service/CLI/MCP status tests cover valid zero, outside-range values,
   nominal/measured references, the 3000 ms boundary, delayed admission, errors,
   reconnect/release/reacquire, disconnected precedence and Basic/older helpers.
6. Congested UART plus sensing preserves byte-exact UART and ACK/timestamp order;
   the full pytest suite, Ruff, mypy, offline lock and diff checks pass.

Physical sensing validation remains separate from those software results:

- Retain the firmware identity/UF2 hash, helper identity, reference provenance
  and actual meter-measured DUT_VIO for each point. Do not substitute PPK2 setpoint.
- Compare reported ADC/mV observations against the Fluke at zero and approximately
  1.8, 2.5, 3.3 and 5.0 V, with UART active and without loading GP28 with a meter
  during the reported observation. Characterize error; do not invent a tolerance
  or advertise a calibrated instrument from these design targets.
- Repeat power-order/reconnect and UART-load checks for the new image, verifying
  the existing unloaded divider behavior and absence of control side effects.
- Existing manufactured-board electrical acceptance, scope requirements and
  secure helper-rail load-access requirements remain independently open.
