"""Validate the built DUTchMate wheels in isolated uv tool environments."""

from __future__ import annotations

import argparse
import configparser
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from email.parser import Parser
from pathlib import Path

import anyio
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

EXPECTED_WHEEL_SCRIPTS = {
    "dutchmate": {
        "dutchmate": "dutchmate.entrypoints:app",
        "dm": "dutchmate.entrypoints:app",
        "dutchmate-service": "dutchmate_service.main:main",
        "dutchmate-mcp": "dutchmate_mcp_server.main:main",
    },
    "dutchmate-core": {},
    "dutchmate-cli": {},
    "dutchmate-service": {},
    "dutchmate-mcp-server": {},
    "dutchmate-debug-agent": {
        "dutchmate-debug": "dutchmate_debug_agent.cli:main",
    },
}
EXPECTED_TOOLS = [
    "reset_dut",
    "set_boot_mode",
    "capture_uart",
    "get_recent_uart_log",
    "wait_for_uart_pattern",
    "run_boot_test",
    "send_uart_command",
    "get_debug_session",
    "list_debug_sessions",
]


def main() -> None:
    arguments = _parser().parse_args()
    dist = arguments.dist.resolve()
    wheels = _wheels_by_distribution(dist)
    _validate_wheel_scripts(wheels)

    uv = shutil.which("uv")
    if uv is None:
        raise SystemExit("uv is required for installed-distribution acceptance")

    with tempfile.TemporaryDirectory(prefix="dutchmate-installed-") as temporary:
        root = Path(temporary)
        base_bin, base_env = _install_tool(
            uv=uv,
            wheel=wheels["dutchmate"],
            dist=dist,
            root=root / "base",
            extra=None,
        )
        _validate_base_commands(base_bin, base_env, root)
        anyio.run(_validate_mcp, base_bin / "dutchmate", base_env)

        debug_bin, debug_env = _install_tool(
            uv=uv,
            wheel=wheels["dutchmate"],
            dist=dist,
            root=root / "debug",
            extra="debug-agent",
        )
        _validate_debug_command(debug_bin, debug_env, root)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist", type=Path, required=True)
    return parser


def _wheels_by_distribution(dist: Path) -> dict[str, Path]:
    wheels: dict[str, Path] = {}
    for wheel in sorted(dist.glob("*.whl")):
        with zipfile.ZipFile(wheel) as archive:
            metadata_path = next(
                name for name in archive.namelist() if name.endswith(".dist-info/METADATA")
            )
            metadata = Parser().parsestr(archive.read(metadata_path).decode("utf-8"))
        distribution = metadata["Name"]
        if distribution in wheels:
            raise AssertionError(f"multiple wheels built for {distribution}")
        wheels[distribution] = wheel

    assert set(wheels) == set(EXPECTED_WHEEL_SCRIPTS), (
        f"unexpected built distributions: {sorted(wheels)}"
    )
    return wheels


def _validate_wheel_scripts(wheels: dict[str, Path]) -> None:
    owners: dict[str, str] = {}
    for distribution, wheel in wheels.items():
        scripts = _wheel_scripts(wheel)
        assert scripts == EXPECTED_WHEEL_SCRIPTS[distribution]
        for executable in scripts:
            if executable in owners:
                raise AssertionError(
                    f"{executable} is owned by {owners[executable]} and {distribution}"
                )
            owners[executable] = distribution


def _wheel_scripts(wheel: Path) -> dict[str, str]:
    with zipfile.ZipFile(wheel) as archive:
        candidates = [
            name for name in archive.namelist() if name.endswith(".dist-info/entry_points.txt")
        ]
        if not candidates:
            return {}
        parser = configparser.ConfigParser()
        parser.read_string(archive.read(candidates[0]).decode("utf-8"))
    return dict(parser["console_scripts"]) if parser.has_section("console_scripts") else {}


def _install_tool(
    *,
    uv: str,
    wheel: Path,
    dist: Path,
    root: Path,
    extra: str | None,
) -> tuple[Path, dict[str, str]]:
    tool_dir = root / "tools"
    bin_dir = root / "bin"
    cache_dir = root / "cache"
    clean_cwd = root / "cwd"
    clean_cwd.mkdir(parents=True)
    environment = os.environ.copy()
    environment.pop("PYTHONPATH", None)
    environment.update(
        {
            "UV_TOOL_DIR": str(tool_dir),
            "UV_TOOL_BIN_DIR": str(bin_dir),
            "UV_CACHE_DIR": str(cache_dir),
            "UV_NO_PROGRESS": "1",
        }
    )
    requirement = f"{wheel}[{extra}]" if extra is not None else str(wheel)
    _run(
        [
            uv,
            "tool",
            "install",
            "--python",
            sys.executable,
            "--find-links",
            str(dist),
            "--no-sources",
            requirement,
        ],
        environment=environment,
        cwd=clean_cwd,
    )
    return bin_dir, environment


def _validate_base_commands(bin_dir: Path, environment: dict[str, str], root: Path) -> None:
    for executable in ("dutchmate", "dm", "dutchmate-service", "dutchmate-mcp"):
        _run([str(bin_dir / executable), "--help"], environment=environment, cwd=root)

    assert not (bin_dir / "dutchmate-debug").exists()
    missing = _run(
        [str(bin_dir / "dutchmate"), "debug", "--help"],
        environment=environment,
        cwd=root,
        expected_exit=1,
    )
    assert "Debug Agent is not installed" in missing.stderr
    assert 'uv tool install "dutchmate[debug-agent]"' in missing.stderr


def _validate_debug_command(bin_dir: Path, environment: dict[str, str], root: Path) -> None:
    assert not (bin_dir / "dutchmate-debug").exists()
    result = _run(
        [str(bin_dir / "dutchmate"), "debug", "--help"],
        environment=environment,
        cwd=root,
    )
    assert "preview" in result.stdout
    assert "analyze" in result.stdout


async def _validate_mcp(executable: Path, environment: dict[str, str]) -> None:
    child_environment = environment.copy()
    child_environment.pop("PYTHONPATH", None)
    child_environment["PATH"] = os.pathsep.join(
        [str(executable.parent), "/usr/bin", "/bin"]
    )
    parameters = StdioServerParameters(
        command=str(executable),
        args=["mcp", "--service-url", "http://127.0.0.1:0"],
        env=child_environment,
    )

    with anyio.fail_after(20):
        async with Client(stdio_client(parameters), mode="auto", cache=None) as client:
            listing = await client.list_tools()
            assert [tool.name for tool in listing.tools] == EXPECTED_TOOLS


def _run(
    command: list[str],
    *,
    environment: dict[str, str],
    cwd: Path,
    expected_exit: int = 0,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != expected_exit:
        raise AssertionError(
            f"command returned {result.returncode}, expected {expected_exit}: {command}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


if __name__ == "__main__":
    main()
