"""Line-oriented human console using only Device Core Service APIs."""

from __future__ import annotations

import sys
from collections.abc import Callable, Mapping
from threading import Event, Thread
from typing import TextIO

import httpx

from dutchmate_cli.client import (
    DEFAULT_SERVICE_URL,
    ServiceClientError,
    fetch_status,
    send_uart_command,
)
from dutchmate_cli.follow import _EvidenceView, write_view
from dutchmate_core.validation import prepare_uart_tx_payload


def _resolve_ending(status: Mapping[str, object], requested: str) -> str:
    if requested != "profile_default":
        return requested
    value = status.get("effective_profile")
    for key in ("hardware", "uart", "default_line_ending"):
        value = value.get(key) if isinstance(value, Mapping) else None
    if not isinstance(value, str) or value not in {"none", "lf", "cr", "crlf"}:
        raise ServiceClientError("Service status does not expose the profile default line ending")
    return value


def run_console(
    *,
    service_url: str = DEFAULT_SERVICE_URL,
    line_ending: str = "profile_default",
    input_stream: TextIO | None = None,
    transport: httpx.BaseTransport | None = None,
    emit: Callable[[str], None] = write_view,
) -> None:
    """Follow durable evidence while sending complete input lines through audited TX."""

    prepare_uart_tx_payload(text="validate", line_ending=line_ending)
    status = fetch_status(service_url=service_url, transport=transport)
    capabilities = status.get("capabilities")
    if not isinstance(capabilities, list) or "uart_send" not in capabilities:
        raise ServiceClientError("Console requires effective uart_send [unsupported_capability]")
    # Resolve the immutable service profile once; every request names the exact ending.
    ending = _resolve_ending(status, line_ending)
    view = _EvidenceView(service_url=service_url, cursor=None, transport=transport, emit=emit)
    view.poll(wait_s=0)
    stopped = Event()
    failures: list[ServiceClientError] = []

    def follow() -> None:
        try:
            view.run(stopped)
            # Include the last completed send's evidence on EOF without another long poll.
            view.poll(wait_s=0)
        except ServiceClientError as exc:
            failures.append(exc)
            stopped.set()
            emit(f"\n{exc}\n")

    worker = Thread(target=follow, name="dutchmate-console-view")
    worker.start()
    try:
        stream = input_stream if input_stream is not None else sys.stdin
        while not stopped.is_set():
            line = stream.readline()
            if not line or stopped.is_set():
                break
            text = line.removesuffix("\n").removesuffix("\r")
            try:
                send_uart_command(
                    text=text,
                    line_ending=ending,
                    service_url=service_url,
                    transport=transport,
                )
            except (ServiceClientError, ValueError) as exc:
                # Rejections (including operation_active) do not retry or end observation.
                emit(f"\n{exc}\n")
    except KeyboardInterrupt:
        pass
    finally:
        stopped.set()
        worker.join()
    if failures:
        raise failures[0]
