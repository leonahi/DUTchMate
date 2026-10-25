"""Incremental primary-evidence snapshots for the public durable tail API."""

from __future__ import annotations

import base64
import binascii
import heapq
import json
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from typing import BinaryIO, cast

from dutchmate_core.evidence.tail import (
    MAX_EVIDENCE_RESPONSE_BYTES,
    EvidencePage,
    compact_json,
)
from dutchmate_core.session_store.metadata import MAX_V2_JSONL_RECORD_BYTES
from dutchmate_core.validation import InputValidationError, validate_session_id


@dataclass(frozen=True, slots=True)
class _Position:
    session_id: str
    sequence: int = 0
    offsets: tuple[int, ...] = (0, 0, 0, 0)

    def encode(self) -> str:
        return base64.urlsafe_b64encode(
            compact_json([1, self.session_id, self.sequence, *self.offsets])
        ).decode("ascii")


def _decode(cursor: str) -> _Position:
    try:
        values = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if not isinstance(values, list) or len(values) != 7 or values[0] != 1:
            raise ValueError
        validate_session_id(values[1])
        if any(type(value) is not int or not 0 <= value < 2**63 for value in values[2:]):
            raise ValueError
        return _Position(values[1], values[2], tuple(values[3:]))
    except (TypeError, ValueError, binascii.Error, UnicodeError) as exc:
        raise InputValidationError("Invalid evidence cursor") from exc


@dataclass(slots=True)
class EvidenceSnapshot:
    """Open files bounded at committed lengths, protected by a short retention lease."""

    session_id: str
    metadata: dict[str, object]
    streams: tuple[BinaryIO, ...]
    lengths: tuple[int, ...]

    @property
    def next_sequence(self) -> int:
        return cast(int, self.metadata["next_evidence_seq"])

    @property
    def successor(self) -> str | None:
        value = self.metadata.get("successor_session_id")
        return validate_session_id(value) if value is not None else None

    def tail(self) -> _Position:
        return _Position(self.session_id, self.next_sequence, self.lengths)

    def read(self, position: _Position, limit: int) -> list[tuple[dict[str, object], _Position]]:
        if position.sequence > self.next_sequence or any(
            offset > length for offset, length in zip(position.offsets, self.lengths, strict=True)
        ):
            raise InputValidationError("Evidence cursor is beyond the durable tail")
        offsets = list(position.offsets)
        heap: list[tuple[int, int, dict[str, object], int]] = []

        def push(index: int) -> None:
            stream = self.streams[index]
            if stream.tell() >= self.lengths[index]:
                return
            raw = stream.readline(MAX_V2_JSONL_RECORD_BYTES + 1)
            if stream.tell() > self.lengths[index] or not raw.endswith(b"\n"):
                raise ValueError("Invalid evidence cursor or incomplete primary evidence")
            record = json.loads(raw)
            sequence = record.get("evidence_seq")
            if type(sequence) is not int or sequence >= self.next_sequence:
                raise ValueError("Invalid primary evidence sequence")
            heapq.heappush(heap, (sequence, index, record, stream.tell()))

        for index, stream in enumerate(self.streams):
            if offsets[index]:
                stream.seek(offsets[index] - 1)
                if stream.read(1) != b"\n":
                    raise InputValidationError("Evidence cursor is not at a record boundary")
            stream.seek(offsets[index])
            push(index)
        result: list[tuple[dict[str, object], _Position]] = []
        expected = position.sequence
        while heap and len(result) < limit:
            sequence, index, record, end = heapq.heappop(heap)
            if sequence != expected:
                raise InputValidationError(
                    "Evidence cursor does not identify a contiguous durable position"
                )
            expected += 1
            offsets[index] = end
            result.append(
                (self._project(record), _Position(self.session_id, expected, tuple(offsets)))
            )
            push(index)
        if not heap and expected != self.next_sequence:
            raise InputValidationError(
                "Evidence cursor does not identify a contiguous durable position"
            )
        return result

    def _project(self, record: dict[str, object]) -> dict[str, object]:
        # Whitelist scalar marker fields; never expose detail/error/parameters or exception text.
        projection: dict[str, object] = {
            "session_id": self.session_id,
            "evidence_seq": record["evidence_seq"],
            "type": record["type"],
        }
        for key in (
            "recorded_at",
            "segment_id",
            "timestamp_us",
            "channel",
            "operation_id",
            "operation_type",
            "attempt_id",
            "outcome",
            "status",
            "role",
            "provider",
            "accepted_bytes",
            "byte_length",
            "device_timestamp_us",
        ):
            value = record.get(key)
            if isinstance(value, str):
                projection[key] = "".join(c for c in value[:128] if c.isprintable())
            elif isinstance(value, (int, bool)):
                projection[key] = value
        if record["type"] in {"uart_rx", "uart_tx_attempt"}:
            data_b64 = cast(str, record["data_b64"])
            projection["data_b64"] = data_b64
            projection["display_text"] = base64.b64decode(data_b64, validate=True).decode(
                "utf-8", errors="replace"
            )
        if record["type"] == "uart_rx":
            projection["raw_offset_start"] = record["raw_offset_start"]
            projection["raw_offset_end"] = record["raw_offset_end"]
            segments = cast(list[dict[str, object]], self.metadata["segments"])
            segment = segments[cast(int, record["segment_id"])]
            projection["timestamp"] = segment["timestamp"]
        return projection


SnapshotFactory = Callable[[str], AbstractContextManager[EvidenceSnapshot]]


def read_evidence_page(
    snapshot: SnapshotFactory,
    *,
    cursor: str | None,
    tail_session_id: str | None,
    limit: int,
) -> EvidencePage:
    """Read at most limit whole records; byte-deferred records keep their cursor position."""

    if cursor is None:
        if tail_session_id is None:
            raise ValueError("A durable session is required to establish an evidence tail")
        position = _Position(tail_session_id)
    else:
        position = _decode(cursor)
    visited: set[str] = set()
    candidates: list[tuple[dict[str, object], _Position]] = []
    while len(candidates) < limit:
        if position.session_id in visited:
            raise ValueError("Evidence rollover chain contains a cycle")
        visited.add(position.session_id)
        with snapshot(position.session_id) as current:
            if cursor is None:
                position = current.tail()
            else:
                batch = current.read(position, limit - len(candidates))
                candidates.extend(batch)
                if batch:
                    position = batch[-1][1]
            successor = current.successor
            if position.sequence < current.next_sequence or successor is None:
                break
        position = _Position(successor)
    if cursor is None:
        return EvidencePage((), position.encode())
    records: list[dict[str, object]] = []
    next_cursor = cursor
    record_bytes = 0
    for index, (record, after) in enumerate(candidates):
        # Exact compact envelope + record sizes, including commas and UTF-8 expansion.
        proposed_cursor = after.encode()
        proposed_bytes = record_bytes + len(compact_json(record))
        omitted = len(candidates) - index - 1
        envelope_bytes = len(EvidencePage((), proposed_cursor, omitted).compact_json())
        if envelope_bytes + proposed_bytes + len(records) > MAX_EVIDENCE_RESPONSE_BYTES:
            break
        record_bytes = proposed_bytes
        records.append(record)
        next_cursor = proposed_cursor
    if not candidates:
        next_cursor = position.encode()
    return EvidencePage(tuple(records), next_cursor, len(candidates) - len(records))
