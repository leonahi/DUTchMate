from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("connection_epoch_harness.c")


def _build_harness(tmp_path: Path) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path / "debug-helper-epoch"
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
            str(FIRMWARE_SOURCE / "connection_epoch.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return executable


def _run_states(tmp_path: Path, states: str) -> bytes:
    harness = _build_harness(tmp_path)
    result = subprocess.run(
        [harness, states],
        check=True,
        capture_output=True,
    )
    return result.stdout


def test_epoch_starts_once_per_dtr_assertion_and_ends_on_loss(tmp_path: Path) -> None:
    assert _run_states(tmp_path, "011100") == b"-S--E-"


def test_epoch_restarts_after_each_completed_disconnect(tmp_path: Path) -> None:
    assert _run_states(tmp_path, "01010") == b"-SESE"


def test_epoch_can_start_when_first_observation_is_asserted(tmp_path: Path) -> None:
    assert _run_states(tmp_path, "11") == b"S-"
