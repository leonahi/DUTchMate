"""Bounded diagnostic projection shared by persistence and delivery adapters."""

from __future__ import annotations

import unicodedata
from typing import Final

MAX_DIAGNOSTIC_BYTES: Final = 1024


def project_diagnostic_detail(*, fallback_code: str, detail: str) -> tuple[str, bool]:
    """Return a sanitized, non-empty diagnostic and whether it was truncated."""

    if not isinstance(fallback_code, str) or not fallback_code:
        raise ValueError("diagnostic fallback code must be a non-empty string")
    if not isinstance(detail, str):
        raise TypeError("diagnostic detail must be a string")

    cleaned = "".join(
        " "
        if character in {"\r", "\n", "\t"}
        else "\ufffd"
        if unicodedata.category(character) == "Cc"
        else character
        for character in detail
    )
    if not cleaned:
        cleaned = fallback_code.replace("_", " ")

    encoded = cleaned.encode("utf-8")
    truncated = len(encoded) > MAX_DIAGNOSTIC_BYTES
    if truncated:
        prefix = encoded[:MAX_DIAGNOSTIC_BYTES]
        while True:
            try:
                cleaned = prefix.decode("utf-8")
                break
            except UnicodeDecodeError:
                prefix = prefix[:-1]
    return cleaned, truncated
