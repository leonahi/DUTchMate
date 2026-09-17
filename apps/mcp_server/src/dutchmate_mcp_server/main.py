"""MCP server entrypoint for DUTchMate."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from typing import Final, cast

from dutchmate_mcp_server.server import LogLevel, run_stdio
from dutchmate_mcp_server.service_client import DEFAULT_SERVICE_URL

SERVICE_URL_ENV: Final = "DUTCHMATE_SERVICE_URL"
LOG_LEVELS: Final = ("debug", "info", "warning", "error", "critical")


def main(argv: Sequence[str] | None = None) -> None:
    """Start the DUTchMate MCP server over stdio."""

    arguments = _parser().parse_args(argv)
    run_stdio(
        service_url=arguments.service_url,
        log_level=cast(LogLevel, arguments.log_level.upper()),
    )


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the DUTchMate MCP stdio server.")
    parser.add_argument(
        "--service-url",
        default=os.environ.get(SERVICE_URL_ENV, DEFAULT_SERVICE_URL),
        help=(
            "Base URL for the Device Core Service "
            f"(default: ${SERVICE_URL_ENV} or {DEFAULT_SERVICE_URL})."
        ),
    )
    parser.add_argument(
        "--log-level",
        choices=LOG_LEVELS,
        default="info",
        type=str.lower,
        help="Process log level (default: info).",
    )
    return parser


if __name__ == "__main__":
    main()
