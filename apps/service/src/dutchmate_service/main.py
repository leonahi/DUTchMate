"""Service entrypoint for DUTchMate."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

import uvicorn

from dutchmate_core.backends.settings import (
    BackendConfig,
    BackendConfigError,
    load_backend_config,
    resolve_backend_settings,
)
from dutchmate_service.app import create_app
from dutchmate_service.startup import DEFAULT_CONFIG_PATH, load_startup_hardware_config


def main(argv: Sequence[str] | None = None) -> None:
    """Start the Device Core Service."""

    parser = argparse.ArgumentParser(description="Run the DUTchMate Device Core Service.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=2040)
    parser.add_argument("--session-root", type=Path, default=Path(".dutchmate/sessions"))
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument("--backend", choices=("basic", "enhanced"))
    parser.add_argument("--serial-port")
    parser.add_argument("--baudrate", type=int)
    parser.add_argument("--data-bits", type=int)
    parser.add_argument("--parity")
    parser.add_argument("--stop-bits", type=int)
    parser.add_argument(
        "--tx-enabled",
        action=argparse.BooleanOptionalAction,
        default=None,
    )
    parser.add_argument("--reconnect-timeout-s", type=float)
    args = parser.parse_args(argv)
    hardware_config = load_startup_hardware_config(args.config)
    try:
        try:
            backend_config = load_backend_config(args.config)
        except FileNotFoundError:
            backend_config = BackendConfig()
        backend_settings = resolve_backend_settings(
            backend_config,
            mode=args.backend,
            serial_port=args.serial_port,
            baudrate=args.baudrate,
            data_bits=args.data_bits,
            parity=args.parity,
            stop_bits=args.stop_bits,
            tx_enabled=args.tx_enabled,
            reconnect_timeout_s=args.reconnect_timeout_s,
        )
    except BackendConfigError as exc:
        parser.error(str(exc))

    uvicorn.run(
        create_app(
            session_root=args.session_root,
            hardware_config=hardware_config,
            backend_settings=backend_settings,
        ),
        host=args.host,
        port=args.port,
    )
