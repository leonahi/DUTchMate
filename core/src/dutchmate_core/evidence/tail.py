"""Public evidence-tail contract, independent of bounded operation cursors."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass

from dutchmate_core.validation import InputValidationError

MAX_EVIDENCE_RESPONSE_BYTES = 262144


class EvidenceCursorExpired(ValueError):
    """The retained evidence cannot safely continue this cursor."""

    def __init__(
        self,
        detail: str = "Evidence cursor position is no longer retained; attach again explicitly",
    ) -> None:
        super().__init__(detail)


def validate_evidence_query(*, cursor: str | None, limit: int, wait_s: float) -> None:
    if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 500:
        raise InputValidationError("evidence limit must be an integer from 1 to 500")
    if (
        isinstance(wait_s, bool)
        or not isinstance(wait_s, (int, float))
        or not math.isfinite(wait_s)
        or not 0 <= wait_s <= 30
    ):
        raise InputValidationError("evidence wait_s must be finite and from 0 to 30")
    if cursor is not None and (not isinstance(cursor, str) or not 1 <= len(cursor) <= 2048):
        raise InputValidationError("Invalid evidence cursor")


@dataclass(frozen=True, slots=True)
class EvidencePage:
    records: tuple[dict[str, object], ...]
    next_cursor: str
    omitted_records: int = 0

    def payload(self) -> dict[str, object]:
        return {
            "ok": True,
            "records": list(self.records),
            "next_cursor": self.next_cursor,
            "omitted_records": self.omitted_records,
        }

    def compact_json(self) -> bytes:
        return compact_json(self.payload())


def compact_json(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode(
        "utf-8"
    )
