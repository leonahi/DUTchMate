"""Command-line entrypoint for DUTchMate."""

from __future__ import annotations

from typing import Annotated, NoReturn

import typer

from dutchmate_cli.client import (
    DEFAULT_SERVICE_URL,
    ServiceClientError,
    ServiceUnavailableError,
    configure_gpio_mode,
    fetch_status,
    reset_dut,
    set_boot_mode,
)
from dutchmate_cli.dut import format_boot_mode_result, format_reset_result
from dutchmate_cli.gpio import format_gpio_mode_result
from dutchmate_cli.status import format_status

app = typer.Typer(help="DUTchMate hardware debug helper.", no_args_is_help=True)
dut_app = typer.Typer(help="Run DUT-level workflows through configured control roles.")
gpio_app = typer.Typer(help="Configure and inspect DUT control GPIO channels.")
app.add_typer(dut_app, name="dut")
app.add_typer(gpio_app, name="gpio")


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


@gpio_app.command("mode")
def gpio_mode(
    channel: Annotated[
        str,
        typer.Argument(help="Control channel to configure, for example CTRL0."),
    ],
    role: Annotated[
        str,
        typer.Argument(help="User-facing role name, for example reset or power_en."),
    ],
    dut_signal: Annotated[
        str,
        typer.Argument(help="DUT signal connected to the channel, for example RESET_N."),
    ],
    mode: Annotated[
        str,
        typer.Option("--mode", help="GPIO drive mode: open_drain or push_pull."),
    ],
    active_level: Annotated[
        str,
        typer.Option("--active-level", help="Asserted signal level: low or high."),
    ],
    idle_level: Annotated[
        str | None,
        typer.Option("--idle-level", help="Optional idle signal level: low or high."),
    ] = None,
    service_url: Annotated[
        str,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
            show_default=True,
        ),
    ] = DEFAULT_SERVICE_URL,
) -> None:
    """Configure a DUT control GPIO channel."""
    try:
        payload = configure_gpio_mode(
            channel=channel,
            role=role,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
            service_url=service_url,
        )
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_gpio_mode_result(payload))


@dut_app.command("reset")
def dut_reset(
    pulse_ms: Annotated[
        int,
        typer.Option("--pulse-ms", min=1, max=10000, help="Reset pulse width in milliseconds."),
    ] = 100,
    service_url: Annotated[
        str,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
            show_default=True,
        ),
    ] = DEFAULT_SERVICE_URL,
) -> None:
    """Pulse the DUT reset control role."""
    try:
        payload = reset_dut(pulse_ms=pulse_ms, service_url=service_url)
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_reset_result(payload))


@dut_app.command("boot-mode")
def dut_boot_mode(
    mode: Annotated[
        str,
        typer.Argument(help="Boot mode to apply: normal or bootloader."),
    ],
    service_url: Annotated[
        str,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
            show_default=True,
        ),
    ] = DEFAULT_SERVICE_URL,
) -> None:
    """Set the DUT boot/control role."""
    try:
        payload = set_boot_mode(mode=mode, service_url=service_url)
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_boot_mode_result(mode, payload))


@app.command()
def mcp() -> None:
    """Run the Phase 2 MCP stdio adapter."""
    _fail("MCP server is planned for Phase 2.")


def _fail(message: str) -> NoReturn:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code=1)
