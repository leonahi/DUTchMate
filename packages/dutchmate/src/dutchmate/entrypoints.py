"""Public executable composition for the DUTchMate distribution."""

from importlib import import_module
from typing import Protocol, cast

import typer

from dutchmate_cli.main import app


class _DebugAgentCli(Protocol):
    def main(self, argv: list[str] | None = None) -> int: ...


@app.command(
    "debug",
    context_settings={
        "allow_extra_args": True,
        "ignore_unknown_options": True,
        "help_option_names": [],
    },
)
def debug(context: typer.Context) -> None:
    """Run the optional Debug Agent command surface."""

    try:
        debug_cli = cast(_DebugAgentCli, import_module("dutchmate_debug_agent.cli"))
    except ModuleNotFoundError as exc:
        if exc.name != "dutchmate_debug_agent":
            raise
        typer.echo(
            'Error: Debug Agent is not installed. Install with: '
            'uv tool install "dutchmate[debug-agent]"',
            err=True,
        )
        raise typer.Exit(code=1) from exc

    raise typer.Exit(code=debug_cli.main(list(context.args)))


__all__ = ["app"]
