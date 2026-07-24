"""Command-line entrypoint for DUTchMate."""

from __future__ import annotations

from typing import Annotated, NoReturn

import typer

from dutchmate_cli.client import (
    DEFAULT_SERVICE_URL,
    ServiceClientError,
    ServiceUnavailableError,
    fetch_status,
)
from dutchmate_cli.status import format_status

app = typer.Typer(help="DUTchMate hardware debug helper.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """DUTchMate command-line interface."""


@app.command()
def start() -> None:
    """Start the Device Core Service."""
    _fail("Device Core Service is not implemented yet.")


@app.command()
def stop() -> None:
    """Stop the Device Core Service."""
    _fail("Device Core Service is not implemented yet.")


@app.command()
def status(
    service_url: Annotated[
        str,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
            show_default=True,
        ),
    ] = DEFAULT_SERVICE_URL,
) -> None:
    """Show DUTchMate service and hardware status."""
    try:
        payload = fetch_status(service_url=service_url)
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_status(payload))


@app.command()
def mcp() -> None:
    """Run the Phase 2 MCP stdio adapter."""
    _fail("MCP server is planned for Phase 2.")


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)
