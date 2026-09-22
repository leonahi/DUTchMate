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
Use the deterministic MCP tools for reset, boot mode, UART capture, UART send,
wait-pattern, boot-test, recent-log, and session retrieval operations.

Treat tool errors as bounded Device Core results. Report the operation,
backend, session ID, and structured error without inventing missing hardware
evidence. Request explicit user confirmation before a device-changing action
when the surrounding task has not already authorized it.
