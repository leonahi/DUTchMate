"""Human views of durable service evidence; never owns a physical reader."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from contextlib import suppress
from threading import Event

import httpx

from dutchmate_cli.client import DEFAULT_SERVICE_URL, ServiceClientError, fetch_evidence


def write_view(text: str) -> None:
    sys.stdout.write(text)
    sys.stdout.flush()


def format_evidence(record: Mapping[str, object]) -> str:
    """Display lossy RX text and bounded markers from the authoritative projection."""

    if record.get("type") == "uart_rx":
        text = record.get("display_text")
        return (
            "".join(c for c in text if c.isprintable() or c in "\n\r\t")
            if isinstance(text, str)
            else ""
        )
    fields = [str(record.get("type", "evidence"))]
    for key in (
        "session_id",
        "evidence_seq",
        "operation_type",
        "outcome",
        "status",
        "accepted_bytes",
    ):
        if key in record:
            fields.append(f"{key}={record[key]}")
    if record.get("type") == "uart_tx_attempt":
        fields.append(f"text={str(record.get('display_text', ''))[:160]!r}")
    marker = " ".join(fields)
    return "\n[" + "".join(c for c in marker[:768] if c.isprintable()) + "]\n"


class _EvidenceView:
    def __init__(
        self,
        *,
        service_url: str,
        cursor: str | None,
        transport: httpx.BaseTransport | None,
        emit: Callable[[str], None],
    ) -> None:
        self.service_url = service_url
        self.cursor = cursor
        self.transport = transport
        self.emit = emit

    def poll(self, *, wait_s: float) -> bool:
        page = fetch_evidence(
            cursor=self.cursor,
            wait_s=wait_s,
            service_url=self.service_url,
            transport=self.transport,
        )
        records = page.get("records")
        next_cursor = page.get("next_cursor")
        if not isinstance(records, list) or not isinstance(next_cursor, str) or not next_cursor:
            raise ServiceClientError("Device Core Service returned an invalid evidence page")
        for record in records:
            if not isinstance(record, Mapping):
                raise ServiceClientError("Device Core Service returned an invalid evidence record")
            self.emit(format_evidence(record))
        omitted = page.get("omitted_records")
        if isinstance(omitted, int) and omitted > 0:
            self.emit(f"\n[{omitted} whole records deferred by response cap; continuing cursor]\n")
        # Advance only after rendering. Slow output is recovered by the next durable request.
        self.cursor = next_cursor
        return bool(records)

    def run(self, stopped: Event) -> None:
        while not stopped.is_set():
            if not self.poll(wait_s=1.0):
                stopped.wait(0.05)


def run_follow(
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    cursor: str | None = None,
    transport: httpx.BaseTransport | None = None,
    emit: Callable[[str], None] = write_view,
) -> None:
    """Attach at tail by default; Ctrl-C closes only this client view."""

    view = _EvidenceView(service_url=service_url, cursor=cursor, transport=transport, emit=emit)
    with suppress(KeyboardInterrupt):
        view.run(Event())
