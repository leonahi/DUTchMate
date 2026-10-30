# DUTchMate Documentation

Use the [glossary](glossary.md) for project terminology. Current progress and
the next implementation step live only in
[development status](development_status.md); completed evidence is preserved in
the append-only [development history](development_history.md).

[Project context](project_context.md) and the
[Phase 1 implementation specification](phase1_implementation_spec.md) are the
normative product and Phase 1 behavior contracts. The Phase 1 v2 migration plan
is a migration-time execution reference and must not redefine them or describe
its pre-v2 baseline as the current implementation.

| Document | Canonical purpose |
|---|---|
| [Development status](development_status.md) | Current milestone, blockers, next step, and ordered queue. |
| [Development history](development_history.md) | Append-only completed-slice and validation record; not a progress tracker. |
| [Project context](project_context.md) | Durable product scope, safety, invariants, and phase definitions. |
| [Phase 1 implementation specification](phase1_implementation_spec.md) | Normative Phase 1 backend, API, session, protocol, test, and done criteria. |
| [Phase 1 v2 migration plan](dutchmate_phase1_v2_coding_agent_plan.md) | Migration-time baseline, staged acceptance scenarios and implementation rationale; current progress belongs only in status. |
| [Software architecture](software_architecture.md) | Python data flow, module ownership, and dependency boundaries. |
| [Developer guide](developer_guide.md) | Workspace setup, commands, package boundaries, and contribution workflow. |
| [Glossary](glossary.md) | Short definitions of recurring DUTchMate terms. |
| [Current Rev-A KiCad source](../hardware/pcb/debug-helper/rev-a/README.md) | Authoritative design, connector mapping, and manufactured-board validation boundaries. |
| [Legacy Revision A design](../hardware/pcb/debug-helper/legacy-eagle/revision_a.md) | Legacy voltage-domain design, pin map, BOM, and validation checklist. |
| [Debug Helper firmware](../hardware/firmware/rp2350_debug_helper/README.md) | RP2350 Pico 2 firmware behavior, build and host verification. |
| [Zephyr DUT fixture](../hardware/firmware/zephyr_dut/README.md) | Separate RP2040 Pico 1 test target, DMF/1 commands, wiring and builds. |
| [GPIO configuration semantics](gpio_configuration_semantics.md) | Control-channel identifiers, electrical modes, state, workflows, and reporting. |
| [Reconnect and session semantics](reconnect_session_semantics.md) | Reconnect, segment, timestamp, resume, and restart behavior. |
| [Ring-buffer sizing plan](ring_buffer_sizing_plan.md) | Phase 1B buffer baseline, telemetry, and validation method. |
| [Ring-buffer validation](../hardware/validation/phase1_ring_buffer.md) | Measurements and final empirical ring-buffer decision. |
| [MCP integration plan](mcp_integration_plan.md) | Phase 2 tools-only MCP transport, tool set, responses, and tests. |
| [Debug Agent context contract](debug_agent_context_contract.md) | Phase 4 bounded context, provider boundary, and report contract. |
| [CI and distribution plan](ci_packaging_distribution_plan.md) | CI, package ownership, firmware identity, plugin, and gated release design. |
| [v0.1.0 release notes](releases/v0.1.0.md) | First public Python host release. |

`hardware/protocol/v1/` is the canonical Enhanced host-device wire contract.
Its schemas, examples, host models, tests, and firmware handling must change
together.
