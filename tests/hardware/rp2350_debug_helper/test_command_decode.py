from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("command_decode_harness.c")


@pytest.fixture(scope="module")
def decoder_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("command-decode") / "command-decode"
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
            str(FIRMWARE_SOURCE / "command_decode.c"),
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
        "configure",
        "actions",
        "uart",
        "invalid-command",
        "invalid-control",
        "invalid-uart",
        "invalid-api",
    ],
)
def test_command_decoder_contract(decoder_harness: Path, scenario: str) -> None:
    subprocess.run([decoder_harness, scenario], check=True)
