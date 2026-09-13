from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("output_drain_harness.c")


def _build_harness(tmp_path: Path) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path / "debug-helper-output-drain"
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
            str(FIRMWARE_SOURCE / "output_drain.c"),
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
        "drains-until-idle",
        "full-batch-keeps-draining",
        "error-stops-batch",
    ],
)
def test_output_drain_batch_policy(tmp_path: Path, scenario: str) -> None:
    harness = _build_harness(tmp_path)
    subprocess.run([harness, scenario], check=True)
