# Reconnect and Session Semantics

> Status: draft decision
> Scope: Device Core session behavior when USB serial disconnects or the Debug Helper restarts during a capture.

## Goal

Disconnects must never erase evidence or make timestamps look continuous when they are not. DUTchMate preserves all bytes already received, marks uncertainty explicitly, and resumes a session only when the resumed evidence can be represented honestly.

## Definitions

| Term | Meaning |
|---|---|
| Segment | A continuous interval of device events received from one Debug Helper connection. |
| Disconnect | Host loses the USB CDC serial connection or serial reader EOF/errors. |
| Reconnect | Service opens a serial port again and receives a valid `hello`. |
| Resume | Continue appending to the same session after reconnect. |
| New session | Close the interrupted session and start another session after reconnect. |

## Session Segments

Every session has one or more segments. A normal uninterrupted session has exactly one segment.

`metadata.json` must include:

```json
{
  "interrupted": true,
  "resumed": true,
  "segments": [
    {
      "segment_id": 0,
      "started_at": "2026-07-04T12:00:00Z",
      "ended_at": "2026-07-04T12:00:03Z",
      "end_reason": "usb_disconnect",
      "hello": {
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "capabilities": ["uart_capture", "gpio_control", "uart_send"]
      },
      "first_device_timestamp_us": 1000,
      "last_device_timestamp_us": 3010000,
      "timestamp_epoch": 0
    },
    {
      "segment_id": 1,
      "started_at": "2026-07-04T12:00:05Z",
      "ended_at": null,
      "end_reason": null,
      "hello": {
        "firmware": "0.1.0",
        "device": "dutchmate-rp2040",
        "capabilities": ["uart_capture", "gpio_control", "uart_send"]
      },
      "first_device_timestamp_us": 500,
      "last_device_timestamp_us": null,
      "timestamp_epoch": 1
    }
  ]
}
```

`interrupted` means at least one disconnect occurred during the session. `resumed` means data was appended after a reconnect.

## Incremental Writes

The Device Core must write incrementally as events arrive:

- Append decoded UART bytes to `uart_raw.log`.
- Append parsed UART events to `uart_events.jsonl`.
- Append hardware/session events to `hardware_events.jsonl`.
- Update `metadata.json` when disconnect, reconnect, resume, truncation, or capture end occurs.

Data already written must not be rewritten or discarded during reconnect handling.

## Hardware Events

Reconnect lifecycle events are recorded in `hardware_events.jsonl`:

```json
{"type": "usb_disconnect", "host_timestamp": "2026-07-04T12:00:03Z", "segment_id": 0}
{"type": "usb_reconnect", "host_timestamp": "2026-07-04T12:00:05Z", "segment_id": 1}
{"type": "timestamp_discontinuity", "host_timestamp": "2026-07-04T12:00:05Z", "from_segment_id": 0, "to_segment_id": 1}
```

These are host-side hardware/session events, not device-to-host protocol messages.

## Timestamp Rules

Device timestamps are authoritative only within a segment.

Rules:

- Do not pretend RP2040 `timestamp_us` is continuous across a reconnect.
- Each UART event stored in `uart_events.jsonl` must include `segment_id` and `timestamp_epoch`.
- Ordering across segments is based on segment order and host reconnect metadata, not raw device timestamp comparison.
- If the Debug Helper restarts and its timer resets, the new segment gets a new `timestamp_epoch`.
- If firmware later provides a stable boot counter or monotonic connection id, the Device Core may use it to improve duplicate detection, but Phase 1 does not require it.

Example `uart_events.jsonl` entry:

```json
{"type": "uart", "segment_id": 1, "timestamp_epoch": 1, "timestamp_us": 500, "channel": 0, "data_b64": "Qk9PVF9PSwo=", "text": "BOOT_OK\n"}
```

## Resume Policy

An active capture can resume into the same session only when all conditions are true:

1. The reconnect occurs before `reconnect_timeout_s` expires.
2. The Device Core receives a valid `hello`.
3. The protocol version matches the active session.
4. The device identity is compatible with the interrupted session.
5. The session has not already ended due to timeout, truncation, explicit stop, or fatal parse error.

If these conditions are met:

- Append a new segment to the same session.
- Set `interrupted: true`.
- Set `resumed: true`.
- Record `usb_reconnect` and `timestamp_discontinuity`.
- Continue capture until the original requested end time unless the workflow defines a new timeout.

If any condition fails:

- Mark the existing session `interrupted: true`.
- End the active capture with `end_reason`.
- Start a new session only if a new user or workflow command requests one.

## Duration Behavior

For Phase 1, capture duration is wall-clock based from the host's workflow start time.

Example: if `capture --seconds 10` disconnects at second 3 and reconnects at second 5, capture still ends at second 10. The session contains a two-second evidence gap.

The gap must be visible through segment metadata and hardware events.

## Duplicate Prevention

Phase 1 does not attempt to deduplicate UART bytes across a USB disconnect.

Rationale:

- USB CDC disconnect generally means unread bytes in host/device buffers may be lost.
- Without firmware sequence numbers, duplicate detection can accidentally discard real repeated boot output.

Future protocol versions may add per-event sequence numbers. Until then, the session records the discontinuity and preserves all bytes received after reconnect.

## Service and CLI Reporting

Capture-like API responses include:

```json
{
  "ok": true,
  "session_id": "20260704_120000_000_capture",
  "overflow": false,
  "interrupted": true,
  "resumed": true,
  "segments": 2
}
```

`GET /sessions` includes `interrupted`, `resumed`, and `segments`.

`dutchmate status` should show reconnect state during an active capture:

```text
Capture: active
Session: 20260704_120000_000_capture
Connection: reconnecting (2.1s remaining)
```

`dutchmate logs` may show a visible separator between segments:

```text
[connection lost at 2026-07-04T12:00:03Z]
[connection resumed at 2026-07-04T12:00:05Z; timestamps restarted]
```

## Failure Modes

| Condition | Session result |
|---|---|
| Disconnect and no reconnect before timeout | `interrupted: true`, `resumed: false`, capture ends with `end_reason: "reconnect_timeout"` |
| Reconnect with protocol version mismatch | Existing session interrupted; new connection rejected until user resolves firmware mismatch |
| Reconnect after session size cap reached | Existing session remains `truncated: true`; no resume into truncated session |
| User stops capture while reconnecting | Existing session interrupted and ended with `end_reason: "user_stop"` |
| Parse error after reconnect | Existing session records error and ends if the parse error is fatal |

## Test Requirements

Minimum tests:

- Disconnect marks `interrupted: true`.
- Reconnect before timeout appends a second segment.
- Device timestamp reset creates a new `timestamp_epoch`.
- Reconnect after timeout does not append to the old session.
- Protocol version mismatch rejects resume.
- Size-capped/truncated sessions do not resume.
- `uart_events.jsonl` includes `segment_id` and `timestamp_epoch`.
- `hardware_events.jsonl` records disconnect, reconnect, and timestamp discontinuity.
