from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("command_executor_harness.c")


@pytest.fixture(scope="module")
def executor_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("command-executor") / "command-executor"
    result = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FIRMWARE_SOURCE),
            str(HARNESS_SOURCE),
            str(FIRMWARE_SOURCE / "command_executor.c"),
            str(FIRMWARE_SOURCE / "command_response.c"),
            str(FIRMWARE_SOURCE / "control_state.c"),
            str(FIRMWARE_SOURCE / "uart_tx_state.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return executable


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        (
            "control",
            b'{"ok":true,"timestamp_us":10}\n'
            b'{"ok":true,"timestamp_us":11}\n',
        ),
        (
            "errors",
            b'{"ok":false,"error":"not_configured",'
            b'"detail":"CTRL3 is not configured"}\n'
            b'{"ok":false,"error":"invalid_argument",'
            b'"detail":"Command argument is invalid"}\n'
            b'{"ok":false,"error":"invalid_command",'
            b'"detail":"Command is invalid"}\n',
        ),
        (
            "rejections",
            b'{"ok":false,"error":"invalid_command",'
            b'"detail":"Command is invalid"}\n'
            b'{"ok":false,"error":"invalid_argument",'
            b'"detail":"Command argument is invalid"}\n',
        ),
        ("pulse", b'{"ok":true,"timestamp_us":1000}\n'),
        (
            "pulse-fault",
            b'{"ok":false,"error":"hardware_fault",'
            b'"detail":"Control hardware operation failed"}\n',
        ),
        (
            "uart",
            b'{"ok":true,"timestamp_us":160,"bytes_accepted":3}\n',
        ),
        (
            "uart-failures",
            b'{"ok":false,"error":"timeout",'
            b'"detail":"UART transmission timed out"}\n'
            b'{"ok":false,"error":"hardware_fault",'
            b'"detail":"UART transmission failed"}\n',
        ),
        ("cancel", b""),
    ],
)
def test_command_executor_routes_one_command_to_one_exact_response(
    executor_harness: Path,
    scenario: str,
    expected: bytes,
) -> None:
    result = subprocess.run(
        [executor_harness, scenario],
        check=False,
        capture_output=True,
    )

    assert result.returncode == 0, result.stderr.decode(errors="replace")
    assert result.stdout == expected
