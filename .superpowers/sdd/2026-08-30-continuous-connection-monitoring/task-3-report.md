# Task 3 Report: Reconcile Runtime State Before Observation And Admission

Date: 2026-08-30

## Cleanup

The worktree initially contained exactly the failed-agent artifacts named by
the task brief: an uncommitted 14-line change in
`core/src/dutchmate_core/runtime.py` and an untracked
`tests/unit/runtime/test_device_core_monitoring.py`. The runtime change was
reverted and the untracked test file was removed before fresh test-first work.
No other worktree changes were present or modified.

## Implementation

- Added the private `DeviceCoreRuntime._reconcile_capture_source_health()`.
- Optional `CaptureSourceMonitor` sources are observed without affecting plain
  `CaptureEventSource` implementations.
- A disconnected health snapshot delegates to the existing idempotent
  `_mark_backend_disconnected()`; reconnect deadline, source ownership, and
  policy fields remain untouched.
- A connected monitor publishes non-`None` live integrity only while runtime
  remains logically connected, so a positive observation cannot undo an
  explicit disconnect.
- Reconciliation runs at the start of `status()` and before
  `_require_connected()` admission.
- Added seven focused runtime tests covering terminal state invalidation,
  admission, live Enhanced integrity, Basic `not_observable`, explicit
  disconnect authority, plain-source compatibility, and reconnect deadline
  precedence.

## Files

- `core/src/dutchmate_core/runtime.py`
- `tests/unit/runtime/test_device_core_monitoring.py`
- `docs/development_status.md`
- `.superpowers/sdd/2026-08-30-continuous-connection-monitoring/task-3-report.md`

## TDD evidence

RED command:

```text
rtk pytest tests/unit/runtime/test_device_core_monitoring.py -v
```

The RTK wrapper exited 1 without output in this worktree. The equivalent
repository interpreter command produced the expected RED result:

```text
.venv/bin/pytest tests/unit/runtime/test_device_core_monitoring.py -v
4 failed, 3 passed in 0.18s
```

The failures were the four missing monitor behaviors: terminal state was not
reconciled, admission did not reject stale connectivity, live Enhanced
integrity stayed at its initial value, and reconnecting status still reported
connected.

GREEN command:

```text
.venv/bin/pytest tests/unit/runtime/test_device_core_monitoring.py -v
7 passed in 0.06s
```

## Validation

Focused runtime regression command:

```text
.venv/bin/pytest tests/unit/runtime/test_device_core_monitoring.py tests/unit/runtime/test_device_core_capture.py tests/unit/runtime/test_device_core_wait.py tests/unit/runtime/test_device_core_uart_send.py tests/unit/runtime/test_device_core_lifecycle.py -v
64 passed in 0.75s
```

Additional checks:

```text
.venv/bin/ruff check .
All checks passed!

MYPYPATH=core/src .venv/bin/mypy
Success: no issues found in 73 source files

.venv/bin/pytest -q
1153 passed, 3 failed in 10.76s

git diff --check
passed
```

## Self-review and concerns

The implementation is limited to the brief’s private runtime helper and two
required call sites. It uses the existing RLock-safe disconnect transition,
does not mutate `_port`, `_backend_mode`, `_capability_policy`,
`_message_source`, or `_reconnect_deadline`, and retains plain-source
compatibility.

Three pre-existing service startup tests now fail because the coordinator
correctly publishes `connected=False` for an idle malformed `BackendInputError`
under the new monitoring contract. Runtime admission rejects before the
workflow consumes that retained terminal error. The failures are:

- `test_enhanced_capture_closes_source_on_malformed_input`
- `test_enhanced_startup_runtime_reopens_and_validates_hello`
- `test_enhanced_reconnect_rejects_changed_device_identity`

Resolving those behavioral expectations belongs with the subsequent startup /
reconnect migration and was intentionally not implemented in Task 3.
