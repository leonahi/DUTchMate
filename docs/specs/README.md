# Specifications and Contracts

These documents define durable product requirements, expected behavior and
acceptance criteria. Implementation does not retire a specification; supersede
it explicitly when its requirements change.

| Document | Canonical purpose |
|---|---|
| [Project context](project_context.md) | Durable product scope, safety, invariants, and phase definitions. |
| [Phase 1 implementation specification](phase1_implementation_spec.md) | Normative Phase 1 backend, API, session, protocol, test, and done criteria. |
| [DUT_VIO sensing contract](dut_vio_sensing_contract.md) | Report-only voltage extension: ADC/reference provenance, negotiated protocol, durable evidence, status and acceptance criteria. |
| [GPIO configuration semantics](gpio_configuration_semantics.md) | Control-channel identifiers, electrical modes, state, workflows, and reporting. |
| [Reconnect and session semantics](reconnect_session_semantics.md) | Reconnect, segment, timestamp, resume, and restart behavior. |
| [UART RX buffering criteria](phase1_implementation_spec.md#121-uart-rx-buffering-and-acceptance) | Sizing, overflow, memory and per-build acceptance requirements. |
| [MCP adapter contract](mcp_adapter_contract.md) | Tools-only transport, live tool catalog, responses and scoped acceptance. |
| [Debug Agent context contract](debug_agent_context_contract.md) | Phase 4 bounded context, provider boundary, and report contract. |
| [CI and distribution contract](ci_packaging_distribution_contract.md) | Package ownership, version identities, installed-artifact acceptance and publication rules. |

[Software architecture](../software_architecture.md) describes module ownership
and dependency direction. [Developer guidance](../developer_guide.md),
[milestone overview](../development_status.md),
[history archive](../development_history.md) and
[release notes](../releases/v0.1.0.md) remain outside this directory.
GitHub Issues own task progress and PRs record implementation/validation.

The Enhanced wire schemas and examples remain authoritative under
[`hardware/protocol/v1/`](../../hardware/protocol/v1/); this move does not change
the wire protocol or relocate machine-readable schemas.
