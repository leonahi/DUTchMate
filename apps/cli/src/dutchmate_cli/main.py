"""Command-line entrypoint for DUTchMate."""

from __future__ import annotations

import math
from typing import Annotated, NoReturn

import typer

from dutchmate_cli.capture import format_boot_test_result, format_capture_result
from dutchmate_cli.client import (
    ServiceClientError,
    ServiceUnavailableError,
    capture_uart,
    configure_gpio_mode,
    fetch_status,
    reset_dut,
    run_boot_test,
    set_boot_mode,
)
from dutchmate_cli.config import CliConfig, CliConfigError, load_cli_config
from dutchmate_cli.devices import DeviceSelectionError, format_devices, resolve_start_serial_port
from dutchmate_cli.dut import format_boot_mode_result, format_reset_result
from dutchmate_cli.gpio import format_gpio_mode_result
from dutchmate_cli.lifecycle import (
    LifecycleError,
    start_service,
    stop_service,
)
from dutchmate_cli.status import format_status
from dutchmate_core.device_connection.discovery import (
    list_dutchmate_candidates,
    list_serial_ports,
)

app = typer.Typer(help="DUTchMate hardware debug helper.", no_args_is_help=True)
dut_app = typer.Typer(help="Run DUT-level workflows through configured control roles.")
gpio_app = typer.Typer(help="Configure and inspect DUT control GPIO channels.")
app.add_typer(dut_app, name="dut")
app.add_typer(gpio_app, name="gpio")


@app.callback()
def main() -> None:
    """DUTchMate command-line interface."""


def _validate_positive_seconds(value: float) -> float:
    if not math.isfinite(value) or value <= 0:
        raise typer.BadParameter("must be a positive finite number")
    return value


@app.command()
def start(
    host: Annotated[
        str | None,
        typer.Option("--host", help="Host interface for the local Device Core Service."),
    ] = None,
    port: Annotated[
        int | None,
        typer.Option("--port", min=1, max=65535, help="HTTP port for the local service."),
    ] = None,
    serial_port: Annotated[
        str | None,
        typer.Option("--serial-port", help="Debug Helper serial device path."),
    ] = None,
) -> None:
    """Start the Device Core Service."""
    config = _load_config_or_fail()
    resolved_host = host or config.daemon.host
    resolved_port = port or config.daemon.port
    try:
        resolved_serial_port = resolve_start_serial_port(
            serial_port,
            list_dutchmate_candidates(),
        )
    except DeviceSelectionError as exc:
        _fail(str(exc))

    try:
        result = start_service(
            host=resolved_host,
            port=resolved_port,
            session_root=config.sessions.path,
            serial_port=resolved_serial_port,
        )
    except LifecycleError as exc:
        _fail(str(exc))

    typer.echo(f"Device Core Service started (pid {result.pid}, {result.url})")
    if not result.ready:
        typer.echo(f"Status endpoint is not ready yet. Logs: {result.log_file}")


@app.command()
def stop() -> None:
    """Stop the Device Core Service."""
    try:
        result = stop_service()
    except LifecycleError as exc:
        _fail(str(exc))

    typer.echo(f"Device Core Service stopped (pid {result.pid})")


@app.command()
def devices(
    all_ports: Annotated[
        bool,
        typer.Option("--all", help="Show all serial ports, not just DUTchMate candidates."),
    ] = False,
) -> None:
    """List serial ports that may be DUTchMate Debug Helpers."""
    candidates = list_serial_ports() if all_ports else list_dutchmate_candidates()
    typer.echo(format_devices(candidates))


@app.command()
def status(
    service_url: Annotated[
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Show DUTchMate service and hardware status."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = fetch_status(service_url=resolved_service_url)
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_status(payload))


@app.command()
def capture(
    seconds: Annotated[
        float,
        typer.Option(
            "--seconds",
            callback=_validate_positive_seconds,
            help="Capture duration in seconds.",
        ),
    ],
    service_url: Annotated[
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Capture DUT UART evidence into a debug session."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = capture_uart(
            duration_s=seconds,
            service_url=resolved_service_url,
        )
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_capture_result(payload))


@app.command("boot-test")
def boot_test(
    seconds: Annotated[
        float,
        typer.Option(
            "--seconds",
            callback=_validate_positive_seconds,
            help="Boot capture duration in seconds.",
        ),
    ],
    service_url: Annotated[
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Reset the DUT and capture boot evidence into a debug session."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = run_boot_test(
            duration_s=seconds,
            service_url=resolved_service_url,
        )
    except ServiceUnavailableError as exc:
        _fail(str(exc))
    except ServiceClientError as exc:
        _fail(str(exc))

    typer.echo(format_boot_test_result(payload))


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
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Configure a DUT control GPIO channel."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = configure_gpio_mode(
            channel=channel,
            role=role,
            dut_signal=dut_signal,
            mode=mode,
            active_level=active_level,
            idle_level=idle_level,
            service_url=resolved_service_url,
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
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Pulse the DUT reset control role."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = reset_dut(pulse_ms=pulse_ms, service_url=resolved_service_url)
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
        str | None,
        typer.Option(
            "--service-url",
            help="Base URL for the local Device Core Service.",
        ),
    ] = None,
) -> None:
    """Set the DUT boot/control role."""
    resolved_service_url = _resolve_service_url(service_url)
    try:
        payload = set_boot_mode(mode=mode, service_url=resolved_service_url)
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


def _load_config_or_fail() -> CliConfig:
    try:
        return load_cli_config()
    except CliConfigError as exc:
        _fail(str(exc))


def _resolve_service_url(service_url: str | None) -> str:
    if service_url is not None:
        return service_url
    return _load_config_or_fail().service_url
