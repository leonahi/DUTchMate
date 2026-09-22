---
name: investigate-debug-session
description: Investigate DUTchMate session evidence through deterministic MCP retrieval before suggesting source changes.
---

# Investigate a DUTchMate Debug Session

Use DUTchMate MCP session and recent-log tools to retrieve bounded evidence.
Start from an explicit session ID when one is supplied; otherwise list sessions
and select only a session whose backend, timing, and lifecycle match the user's
request.

Separate observed UART/control evidence from inference. Preserve integrity,
truncation, reconnect, timestamp-provenance, and first-error fields in the
analysis. Do not claim that missing or truncated evidence proves the absence of
a device event.

Source suggestions may follow only after the evidence is summarized. Keep
provider-assisted Debug Agent analysis optional and outside the deterministic
MCP hardware-control path.
