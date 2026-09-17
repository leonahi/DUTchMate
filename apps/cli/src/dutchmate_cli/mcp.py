"""Process launcher for the separately packaged MCP stdio adapter."""

from __future__ import annotations

import os
from enum import Enum
from typing import NoReturn


class McpLogLevel(str, Enum):
    """Log levels accepted by the MCP server entrypoint."""

    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class McpLaunchError(RuntimeError):
    """Raised when the MCP server process cannot be launched."""


def launch_mcp(*, service_url: str | None, log_level: McpLogLevel) -> NoReturn:
    """Replace the CLI process with the MCP stdio server process."""

    command = ["dutchmate-mcp"]
    if service_url is not None:
        command.extend(["--service-url", service_url])
    command.extend(["--log-level", log_level.value])

    try:
        os.execvp(command[0], command)
    except FileNotFoundError as exc:
        raise McpLaunchError(
            "dutchmate-mcp executable is not installed; "
            "install the DUTchMate MCP server package"
        ) from exc
    except OSError as exc:
        raise McpLaunchError(f"could not launch dutchmate-mcp: {exc}") from exc
