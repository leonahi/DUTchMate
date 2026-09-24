# DUTchMate Glossary

## Backend

The selected adapter path that turns device-specific I/O into DUTchMate's
normalized host contracts. One session uses either Basic or Enhanced, never a
hybrid of both.

## Basic backend

The backend for a user-selected generic TTL/logic-level USB-to-UART adapter. It
uses host-observed timestamps and can optionally send UART data.

## Baseline

One eligible completed session explicitly designated for later comparison.
DUTchMate uses the validated project pointer rather than choosing by recency.

## Coordinated reconnect

The service-owned process that serializes idle and active backend replacement,
validates the replacement identity, and publishes it without mixing old and new
connection state.

## `CTRLn`

The generic Enhanced control-channel identifiers `CTRL0` through `CTRL3`.
Accepted configuration maps a channel to a DUT role, signal, and electrical
mode.

## Debug Helper

The RP2350-based Raspberry Pi Pico 2 device used by the Enhanced backend. It
observes and controls DUT-facing signals while speaking the versioned DUTchMate
protocol to the host.

## Device Core Service

The local service that owns backend lifecycle, normalized workflows, and session
persistence. The CLI and MCP adapter call this service rather than owning device
policy themselves.

## DUT

Device under test: the embedded target DUTchMate is observing or controlling.

## Enhanced backend

The backend for the DUTchMate Debug Helper. It adds firmware timestamps, loss
telemetry, generic control channels, and bounded UART receive/send operations.

## Evidence package

A bounded, versioned Debug Agent input assembled from selected native sessions
and optional validated coding context. Its contents are frozen before provider
submission.

## First error

The first configured error pattern detected in a session, identified by its
segment and ingestion-event coordinates without duplicating captured text.

## HIL

Hardware-in-the-loop validation performed against real adapters, Debug Helpers,
fixtures, and DUT-facing electrical paths. Mocked tests cannot replace a
required HIL gate.

## Ingestion

The continuous service-owned consumption of normalized backend events into
session evidence. Finite workflows temporarily claim the active event window
without creating a second device reader.

## Integrity

The session's statement about whether UART loss was observable and reported.
Enhanced telemetry can report dropped bytes; Basic evidence may be marked not
observable.

## Manifest digest

The SHA-256 review token that binds a Debug Agent provider, model, limits, and
exact frozen analysis request. Analysis requires approval of the matching
digest.

## Native session

A session written in the current versioned evidence format. Legacy or unknown
formats may remain readable through explicitly bounded compatibility paths but
are not interpreted as native evidence.

## Segment

One continuous backend connection interval within a session. A coordinated
reconnect closes the old segment and creates a new timestamp context.

## Session

A bounded, durable record of one capture, boot test, wait, or related workflow,
including lifecycle state, segments, UART evidence, hardware actions, and
integrity metadata.

## Timestamp provenance

The recorded source, clock, observation point, and event granularity for a
timestamp. Basic timestamps are host-observed; Enhanced timestamps originate
from the Debug Helper's RP2350 timer.

## UART

The asynchronous serial interface used for DUT logs and optional commands.
DUTchMate stores UART evidence with explicit provenance and integrity state.
