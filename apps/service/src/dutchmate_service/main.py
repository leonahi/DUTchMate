"""Service entrypoint for DUTchMate."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

import uvicorn

from dutchmate_service.app import create_app


def main(argv: Sequence[str] | None = None) -> None:
    """Start the Device Core Service."""

    parser = argparse.ArgumentParser(description="Run the DUTchMate Device Core Service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2040)
    args = parser.parse_args(argv)

    uvicorn.run(create_app(), host=args.host, port=args.port)
