"""Unfiltered stdio acceptance through both installed console scripts."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest
from mcp.types import (
    CLIENT_CAPABILITIES_META_KEY,
    CLIENT_INFO_META_KEY,
    PROTOCOL_VERSION_META_KEY,
)
from mcp.types.version import LATEST_MODERN_VERSION

EXPECTED_TOOLS = [
    "get_status",
    "monitor",
    "interact",
    "send_uart",
    "reset_dut",
    "set_dut_boot_mode",
    "get_evidence",
    "get_recent_logs",
    "list_sessions",
    "get_session",
    "release_connection",
    "reacquire_connection",
]


def installed_command(command):
    executable = Path(sys.executable).with_name(command)
    assert executable.is_file(), f"missing installed console script: {executable}"
    return [str(executable), *(["mcp"] if command == "dutchmate" else [])]


def clean_environment():
    environment = dict(os.environ)
    for name in ("PYTHONPATH", "VIRTUAL_ENV", "DUTCHMATE_SERVICE_URL"):
        environment.pop(name, None)
    environment["PATH"] = "/usr/bin:/bin"
    return environment


async def exchange(process, request_id, method, **arguments):
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": {
            "_meta": {
                PROTOCOL_VERSION_META_KEY: LATEST_MODERN_VERSION,
                CLIENT_INFO_META_KEY: {"name": "installed-launch-test", "version": "1"},
                CLIENT_CAPABILITIES_META_KEY: {},
            },
            **arguments,
        },
    }
    process.stdin.write(json.dumps(request).encode() + b"\n")
    await process.stdin.drain()
    # Parse every line, unlike a transport that might discard non-JSON output.
    line = await asyncio.wait_for(process.stdout.readline(), 5)
    response = json.loads(line)
    assert response["jsonrpc"] == "2.0" and response["id"] == request_id
    assert "error" not in response, response
    return response["result"]


@pytest.mark.parametrize("command", ["dutchmate", "dutchmate-mcp"])
@pytest.mark.parametrize(
    "environment_url, explicit_url, expected_error",
    [
        ("file:///invalid-environment", "http://127.0.0.1:0", "service_unavailable"),
        ("http://127.0.0.1:0", None, "service_unavailable"),
        ("file:///invalid-environment", None, "invalid_argument"),
        ("http://127.0.0.1:0", "http://user:secret@127.0.0.1:0", "invalid_argument"),
    ],
)
async def test_installed_stdio_catalog_url_precedence_errors_and_eof(
    command,
    environment_url,
    explicit_url,
    expected_error,
    tmp_path,
):
    environment = clean_environment()
    environment["DUTCHMATE_SERVICE_URL"] = environment_url
    arguments = installed_command(command) + ["--log-level", "debug"]
    if explicit_url is not None:
        arguments.extend(["--service-url", explicit_url])
    process = await asyncio.create_subprocess_exec(
        *arguments,
        cwd=tmp_path,
        env=environment,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    # Drain diagnostics concurrently so stderr cannot block protocol progress.
    stderr_task = asyncio.create_task(process.stderr.read())
    try:
        discovery = await exchange(process, 1, "server/discover")
        assert discovery["supportedVersions"] == [LATEST_MODERN_VERSION]
        assert discovery["resultType"] == "complete"
        assert discovery["ttlMs"] == 300000 and discovery["cacheScope"] == "private"
        first = await exchange(process, 2, "tools/list")
        second = await exchange(process, 3, "tools/list")
        assert first == second
        assert [tool["name"] for tool in first["tools"]] == EXPECTED_TOOLS
        assert first["ttlMs"] == 300000 and first["cacheScope"] == "private"
        result = await exchange(process, 4, "tools/call", name="get_status", arguments={})
        assert result["resultType"] == "complete" and result["isError"] is True
        payload = result["structuredContent"]
        assert json.loads(result["content"][0]["text"]) == payload
        assert payload["ok"] is False and payload["error"] == expected_error
        assert 0 < len(payload["detail"].encode()) <= 1024
        assert payload["detail_truncated"] is False
        assert "secret" not in payload["detail"]
        if expected_error == "service_unavailable":
            assert "Start it with an explicit Basic or Enhanced backend" in payload["detail"]
        # An error leaves the same server alive and its catalog intact.
        assert await exchange(process, 5, "tools/list") == first
        process.stdin.close()
        assert await asyncio.wait_for(process.wait(), 5) == 0
        assert await process.stdout.read() == b""
        stderr = (await stderr_task).decode()
        assert "DEBUG" in stderr  # requested logging is emitted only on stderr
        assert "Traceback" not in stderr
    finally:
        if process.returncode is None:
            process.kill()
            await process.wait()
        await stderr_task
    assert list(tmp_path.iterdir()) == []  # no MCP-owned evidence or service artifacts


@pytest.mark.parametrize("command", ["dutchmate", "dutchmate-mcp"])
def test_installed_default_start_and_empty_eof_are_quiet(command, tmp_path):
    completed = subprocess.run(
        installed_command(command),
        input="",
        text=True,
        capture_output=True,
        env=clean_environment(),
        cwd=tmp_path,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 0
    assert completed.stdout == "" and "Traceback" not in completed.stderr
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("command", ["dutchmate", "dutchmate-mcp"])
@pytest.mark.parametrize("arguments", [["--log-level", "verbose"], ["--transport", "sse"]])
def test_installed_rejects_invalid_options_on_stderr(command, arguments, tmp_path):
    completed = subprocess.run(
        installed_command(command) + arguments,
        input="",
        text=True,
        capture_output=True,
        env=clean_environment(),
        cwd=tmp_path,
        timeout=5,
        check=False,
    )
    assert completed.returncode == 2
    assert completed.stdout == "" and completed.stderr
