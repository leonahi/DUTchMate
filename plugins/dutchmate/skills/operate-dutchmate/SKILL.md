---
name: operate-dutchmate
description: Use DUTchMate MCP tools to inspect status, control the configured DUT, and collect bounded UART evidence.
---

# Operate DUTchMate

Use the configured DUTchMate MCP server as the only device-control boundary.
Do not open serial ports, write session files, or reproduce Device Core behavior
inside the coding-agent host.

Before an operation, inspect the available tools and confirm that the local
Device Core Service is running with the intended Basic or Enhanced backend.
Use the twelve-tool MCP v2 surface for status, bounded Monitor/Interact,
exact UART send, configured `reset_dut`/`set_dut_boot_mode`, evidence/log/session
retrieval and explicit release/reacquire. Text TX requires an explicit line
ending; binary TX uses `data_b64`. Boot validation is client composition of
atomic tools, not a dedicated MCP workflow. MCP never starts the Device Core
Service.

Treat tool errors as bounded Device Core results. Report the operation,
backend, session ID, and structured error without inventing missing hardware
evidence. Request explicit user confirmation before a device-changing action
when the surrounding task has not already authorized it.
