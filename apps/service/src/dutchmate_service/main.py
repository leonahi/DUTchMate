"""Service entrypoint for DUTchMate."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from dutchmate_service.app import create_app
from dutchmate_service.startup import DEFAULT_CONFIG_PATH, load_startup_hardware_config


def main(argv: Sequence[str] | None = None) -> None:
    """Start the Device Core Service."""

    parser = argparse.ArgumentParser(description="Run the DUTchMate Device Core Service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2040)
    parser.add_argument("--session-root", type=Path, default=Path(".dutchmate/sessions"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--serial-port")
    args = parser.parse_args(argv)
    hardware_config = load_startup_hardware_config(args.config)

    uvicorn.run(
        create_app(
            session_root=args.session_root,
            hardware_config=hardware_config,
            serial_port=args.serial_port,
        ),
        host=args.host,
        port=args.port,
    )
