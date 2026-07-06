"""Command-line entrypoint for DUTchMate."""

import typer

app = typer.Typer(help="DUTchMate hardware debug helper.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """DUTchMate command-line interface."""


@app.command()
def start() -> None:
    """Start the Device Core Service."""
    raise typer.ClickException("Device Core Service is not implemented yet.")


@app.command()
def stop() -> None:
    """Stop the Device Core Service."""
    raise typer.ClickException("Device Core Service is not implemented yet.")


@app.command()
def status() -> None:
    """Show DUTchMate service and hardware status."""
    raise typer.ClickException("Device Core Service is not implemented yet.")


@app.command()
def mcp() -> None:
    """Run the Phase 2 MCP stdio adapter."""
    raise typer.ClickException("MCP server is planned for Phase 2.")
