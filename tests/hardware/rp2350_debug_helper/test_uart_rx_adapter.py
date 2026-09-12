from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("uart_rx_adapter_harness.c")
STUB_INCLUDE = Path(__file__).with_name("uart_rx_stubs")


def _build_harness(tmp_path: Path) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path / "debug-helper-uart-rx-adapter"
    result = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(STUB_INCLUDE),
            "-I",
            str(FIRMWARE_SOURCE),
            str(HARNESS_SOURCE),
            str(FIRMWARE_SOURCE / "uart_rx.c"),
            str(FIRMWARE_SOURCE / "uart_rx_ring.c"),
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
    "scenario",
    [
        "line-error-recovers",
        "driver-error-is-fatal",
    ],
)
def test_uart_rx_adapter_error_policy(tmp_path: Path, scenario: str) -> None:
    harness = _build_harness(tmp_path)
    subprocess.run([harness, scenario], check=True)
