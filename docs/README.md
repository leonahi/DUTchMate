# DUTchMate Documentation

Use the [glossary](glossary.md) for project terminology. Track tasks and blockers
in [GitHub Issues](https://github.com/leonahi/DUTchMate/issues), with implementation
and validation in PRs. See the [contribution workflow](../CONTRIBUTING.md#issues-and-pull-requests).

[Project context](specs/project_context.md) and the
[Phase 1 implementation specification](specs/phase1_implementation_spec.md) are the
normative product and Phase 1 behavior contracts. Specification and contract
documents live under [specifications](specs/README.md). Completed implementation
plans are retired; implemented features retain their contracts and tests.

| Document | Canonical purpose |
|---|---|
| [Milestone overview](development_status.md) | Dated release scope and milestone acceptance; no task queue. |
| [History archive](development_history.md) | Frozen pre-tracker evidence, baselines and final migration handoff. |
| [Specifications and contracts](specs/README.md) | Product scope, Phase 1 behavior, GPIO, reconnect, voltage sensing, MCP, Debug Agent and distribution requirements. |
| [Implementation plans](plans/README.md) | Implementation planning policy and retained historical migration references. |
| [Software architecture](software_architecture.md) | Python data flow, module ownership, and dependency boundaries. |
| [Developer guide](developer_guide.md) | Workspace setup, commands, package boundaries, and contribution workflow. |
| [Glossary](glossary.md) | Short definitions of recurring DUTchMate terms. |
| [Current Rev-A KiCad source](../hardware/pcb/debug-helper/rev-a/README.md) | Authoritative design, connector mapping, and manufactured-board validation boundaries. |
| [Legacy Revision A design](../hardware/pcb/debug-helper/legacy-eagle/revision_a.md) | Legacy voltage-domain design, pin map, BOM, and validation checklist. |
| [Debug Helper firmware](../hardware/firmware/rp2350_debug_helper/README.md) | RP2350 Pico 2 firmware behavior, build and host verification. |
| [Zephyr DUT fixture](../hardware/firmware/zephyr_dut/README.md) | Separate RP2040 Pico 1 test target, DMF/1 commands, wiring and builds. |
| [Ring-buffer validation](../hardware/validation/phase1_ring_buffer.md) | Measurements and final empirical ring-buffer decision. |
| [v0.2.0 release notes](releases/v0.2.0.md) | Published host release: upgrade guidance, features, public scope and remaining limits. |
| [v0.1.0 release notes](releases/v0.1.0.md) | First public Python host release. |

`hardware/protocol/v1/` is the canonical Enhanced host-device wire contract.
Its schemas, examples, host models, tests, and firmware handling must change
together.

The [historical Phase 1 migration reference](plans/dutchmate_phase1_v2_coding_agent_plan.md)
lives under `plans/`. Its original stage instructions are in Git; use the
specifications above for current requirements.

Short forwarding pages retain old Phase 1, MCP and migration-reference links
used by append-only historical records. Canonical documents live in `specs/`
and `plans/`.
