# Milestone Overview

> Reviewed: 2026-11-27. Dated release-scope and acceptance snapshot.
> Tasks, ownership, blockers and dependencies belong in
> [GitHub Issues](https://github.com/leonahi/DUTchMate/issues); Projects provides
> the team view. PRs record implementation and validation.

Update this overview when release scope or milestone acceptance changes, not
for every development slice. See the
[contribution workflow](../CONTRIBUTING.md#issues-and-pull-requests).

## Host Release Scope

The approved next host release is **v0.2.0**, with the five public host
distributions. Debug Agent publication remains deferred; its workspace version
is synchronized only for internal validation. The candidate versions, exact
internal pins and lockfile are prepared at `0.2.0`. All six workspace artifact
pairs and the five public pairs passed clean installed-package checks.
[Prepared release notes](releases/v0.2.0.md) describe upgrade behavior and limits.
Publication remains subject to review, CI and the existing protected release gates.

## Acceptance Snapshot

| Gate | Status |
|---|---|
| Phase 1A — Basic | Complete; fresh session 20261027T073956Z-7c038da2 satisfies normative criteria; E_COMMAND_001 unresolved/unclassified/non-blocking |
| Phase 1B — Enhanced | Incomplete until required manufactured KiCad Rev-A physical validation is performed and accepted; includes fresh UART electrical/oscilloscope evidence under existing criteria; legacy EAGLE functional HIL cannot satisfy this hardware gate |
| Phase 1 shared done criteria | Shared §35 behavioral evidence is retained; Phase 1 remains incomplete pending accepted current-board physical validation, without transferring EAGLE acceptance to KiCad |

- Report-only DUT_VIO sensing is implemented. Physical ADC accuracy tolerance
  and diagnostic runtime stack results remain unestablished.
- MCP v2 is accepted under its scoped policy. Optional VS Code tool-use and
  authenticated Claude Code host UI checks were unavailable, not passed.
- Phase 4 Debug Agent v2 packaging remains paused; existing schema-v1 support
  is retained. Phase 5 EVENT capture remains deferred.

## Evidence and Historical Handoff

- [Phase 1 specification](specs/phase1_implementation_spec.md) owns acceptance;
  [manufactured-board evidence](../hardware/validation/phase1_kicad_rev_a.md)
  retains measurements without transferring legacy EAGLE acceptance to KiCad.
- [Sensing provenance](../hardware/validation/dut_vio_software_20261125.json)
  retains build/reference identity. [KiCad source](../hardware/pcb/debug-helper/rev-a/README.md)
  retains design ownership and evidence boundaries.
- The [history archive](development_history.md#2026-11-27--issue-based-tracking-cutover)
  preserves the final local handoff, prior baselines, pending changes and bench
  context. It is historical evidence, not a live task queue.

Team tracking: [project board](https://github.com/users/leonahi/projects/1/views/2) and
[v0.2.0 milestone](https://github.com/leonahi/DUTchMate/milestone/1). Keep task ownership and progress in
those linked issues/PRs; this overview does not mirror the backlog.
