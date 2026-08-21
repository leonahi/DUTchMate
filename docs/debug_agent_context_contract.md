# Debug Agent Context Contract

> Scope: Evidence and optional source context supplied to the AI-assisted Debug Agent, plus the provider boundary used to analyze it.

## Decision Summary

The Debug Agent receives structured, bounded hardware evidence automatically.
It receives source or project context only through an explicit context package
assembled by the Coding Agent. It never receives the full repository or
unrestricted filesystem access by default.

The Coding Agent remains responsible for repository inspection, root-cause
reasoning across the codebase, source changes, builds, and test execution. The
Debug Agent remains an evidence analyst and test-orchestration adviser.

AI analysis uses a pluggable provider adapter in the Debug Agent application
layer. It is disabled by default and never becomes a dependency of Device Core,
session capture, or deterministic evidence processing.

## Automatic Session Evidence

Given one or more session IDs, the context packer includes:

- session command, bounded backend identity, backend mode, pre-policy backend
  capabilities, effective capabilities, and capability-policy provenance
- segment metadata and timestamp provenance
- accepted `reconnect_timeout_s` policy and lifecycle outcome
- `integrity`, `truncated`, `interrupted`, and `resumed` state
- derived `line_processing` status and oversized-line count
- session evidence budget/written bytes and quota `truncation` details
- detected-pattern references and the deterministic Phase 1 `first_error` with
  at most its stored 4096-byte match excerpt when available
- summarized hardware/session events and relevant event excerpts
- baseline comparison summary only when the project session-store pointer
  designates a valid baseline; the package preserves baseline session ID and
  timing-comparability state rather than selecting a reference heuristically
- bounded UART text excerpts with session, segment, and timestamp references

Automatic evidence packaging accepts only native session `schema_version: 1`.
Legacy version `0` lacks the lifecycle and provenance required by this contract,
and unknown versions are not interpreted. Device Core returns
`unsupported_session_schema`; the packer does not infer missing facts or include
raw legacy artifacts as an implicit fallback.

The automatic UART excerpt budget is at most 300 lines and 64 KiB of UTF-8
display text per analyzed session. Selection prioritizes the deterministic
`first_error` window, detected-pattern lines, and boot start/end context. Hardware
event excerpts are limited to 100 events after summary counts are computed.

The packer never inserts all of `uart_raw.log` or every event automatically.
Complete artifacts remain stored in the session and can be retrieved through
bounded follow-up tools. When evidence is omitted, the package records
`context_truncated: true`, the applied limit, and omitted line/event counts.
Truncation must never be silent.

Oversized physical-line descriptors are evidence metadata, not UART text. The
packer includes their count and relevant descriptor references within the event
budget, never synthesizes their bytes into a line, and never expands a stored
pattern excerpt beyond its authoritative offsets.

The hardware-event summary must pair `uart_tx_attempt` and `uart_tx_result` by
`attempt_id`. It must preserve failed or partially accepted results and surface
every unmatched attempt as an unknown command outcome even when the 100-event
excerpt limit omits one of the raw records.

## Coding Agent Context Package

The Coding Agent may attach this versioned JSON-compatible structure:

```json
{
  "schema_version": 1,
  "objective": "Explain why sensor initialization started failing after the latest change",
  "session_ids": ["20260724T120000Z-a1b2c3d4"],
  "build": {
    "commit": "0123456789abcdef",
    "build_id": "debug-1042",
    "board": "example_board",
    "configuration": "debug"
  },
  "changed_files": [
    {
      "path": "src/sensor.c",
      "summary": "Changed regulator-enable delay"
    }
  ],
  "excerpts": [
    {
      "kind": "source",
      "path": "src/sensor.c",
      "commit": "0123456789abcdef",
      "start_line": 80,
      "end_line": 126,
      "language": "c",
      "text": "..."
    }
  ],
  "symbols": ["sensor_init", "sensor_power_enable"],
  "constraints": ["Do not change the regulator driver"]
}
```

The `build` object is supplied by the Coding Agent or test harness. Phase 1
session metadata does not define or infer source commit, build ID, board, or
build-configuration fields. A caller may correlate those facts with sessions
through `session_ids`; automatic evidence packaging includes only fields
actually defined by the native session schema.

Allowed excerpt kinds are `source`, `configuration`, and `diff`. Source and
configuration excerpts must include their repository-relative path, commit,
line range, and text. Diff excerpts must include the path, `base_commit`,
`head_commit`, unified-diff hunk ranges, and diff text.

Default package limits:

| Field | Limit |
|---|---:|
| `objective` | 4 KiB UTF-8 |
| `changed_files` | 100 entries |
| `symbols` | 100 entries |
| `excerpts` | 8 entries |
| One excerpt | 200 lines and 16 KiB UTF-8 |
| All excerpt text | 64 KiB UTF-8 |

The packer rejects an over-limit or malformed package rather than silently
discarding Coding Agent context. The caller may submit a smaller package.
Package limits may become configurable later, but every report must record the
effective limits.

## Access and Safety Rules

- The context packer reads session artifacts by validated session ID only.
- It does not crawl the repository or follow arbitrary paths supplied by the
  Debug Agent.
- The Coding Agent selects source excerpts explicitly. Repository access is not
  delegated through the package.
- Absolute paths, parent traversal, binary excerpts, private keys, credential
  files, and known secret material are rejected.
- Context does not grant new hardware permissions. All actions still use
  validated Device Core operations and capability/role checks.
- Raw evidence remains authoritative. A source excerpt or model inference must
  not overwrite, reclassify, or remove session evidence.

## Provider Boundary

- `disabled` is the default provider. Analysis starts only after the user
  explicitly selects and configures a registered provider adapter.
- Local and remote providers consume the same validated, versioned analysis
  request and must return the same structured report schema.
- A remote provider requires explicit remote-processing opt-in. Only the exact
  bounded context package is submitted; raw session artifacts, the repository,
  and unrestricted filesystem content are never uploaded automatically.
- Provider credentials come from environment variables, an operating-system
  credential store, or another external secret provider. Credentials must not
  appear in `.dutchmate/config.toml`, session artifacts, reports, or logs.
- Provider selection is fixed for one analysis request. The Debug Agent must not
  silently fall back from a local provider to a remote provider, or between
  remote providers.
- Provider timeouts, retries, malformed responses, and unavailability fail only
  the analysis request. They must not modify raw evidence or interrupt capture,
  storage, control, or other Device Core operations.
- The adapter validates the provider response against the report schema before
  storing or returning it. Invalid responses are analysis failures, not partial
  reports.
- Phase 4 may initially ship one provider adapter, but provider-specific SDKs
  and configuration remain outside Device Core and the context packer.

Before a remote request is submitted, the caller must be able to inspect a
manifest containing the selected session IDs, included source paths, applied
limits, truncation state, total text bytes, provider ID, and model ID. The
manifest need not duplicate the full context text.

## Report Contract

Every Debug Agent report separates:

- `observations`: facts with session/event/source references
- `inferences`: interpretations with basis and uncertainty
- `unknowns`: missing evidence that prevents a stronger conclusion
- `recommended_next_evidence`: bounded tests or observations to collect
- `recommended_source_areas`: files/symbols for the Coding Agent to inspect

The report may identify an advisory `first_meaningful_failure`, which may add
context to or differ from the deterministic Phase 1 `first_error`. It must cite
its evidence and must never overwrite or relabel the stored `first_error`.

The report records the context-package schema version, session IDs, effective
limits, truncation state, source commit when source context was provided,
provider ID, model ID, whether processing was remote, request-schema version,
and a digest of the submitted context. It never records credentials. It must
not claim a definitive code root cause without sufficient source evidence and
must not emit or apply a source patch.

## Phase 4 Test Requirements

- Automatic evidence selection respects line, byte, and event limits.
- Deterministic `first_error` and detected-pattern context is prioritized.
- An inferred `first_meaningful_failure` cites evidence and leaves the stored
  Phase 1 `first_error` unchanged.
- Omitted evidence sets explicit truncation fields and counts.
- Source excerpts without path, commit, or valid line provenance are rejected.
- Path traversal, binary data, and known credential/private-key inputs are
  rejected.
- Full-repository traversal is not available through the Debug Agent boundary.
- Reports preserve session integrity and timestamp-provenance warnings.
- Reports contain distinct observations, inferences, unknowns, and next steps.
- AI analysis remains disabled until a provider is explicitly configured.
- Local and remote adapter fixtures produce the common structured report shape.
- Remote analysis is rejected without explicit opt-in and exposes a submission
  manifest before transmission.
- Provider errors and invalid responses leave raw evidence and Device Core
  operation unchanged.
- Tests verify that credentials are absent from configuration, logs, reports,
  and persisted request metadata.

## Out of Scope

- Mandating a specific model vendor or provider
- Repository-wide semantic search by the Debug Agent
- Source patch generation or application
- Unbounded log or source injection
- Direct serial, GPIO, or filesystem access by the model
