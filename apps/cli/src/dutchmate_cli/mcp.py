"""Process launcher for the separately packaged MCP stdio adapter."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path
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

    sibling_executable = _sibling_mcp_executable()
    executable = sibling_executable or "dutchmate-mcp"
    command = [executable]
    if service_url is not None:
        command.extend(["--service-url", service_url])
    command.extend(["--log-level", log_level.value])

    try:
        if sibling_executable is not None:
            os.execv(executable, command)
        os.execvp(executable, command)
    except FileNotFoundError as exc:
        raise McpLaunchError(
            "dutchmate-mcp executable is not installed; "
            "install the DUTchMate MCP server package"
        ) from exc
    except OSError as exc:
        raise McpLaunchError(f"could not launch dutchmate-mcp: {exc}") from exc


def _sibling_mcp_executable() -> str | None:
    candidate = Path(sys.executable).with_name("dutchmate-mcp")
    return str(candidate) if candidate.is_file() else None
