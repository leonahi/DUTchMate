from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("ndjson_framer_harness.c")


@pytest.fixture(scope="module")
def framer_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("ndjson-framer") / "ndjson-framer"
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
            str(FIRMWARE_SOURCE / "ndjson_framer.c"),
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
        "fragmented",
        "crlf",
        "exact-limit",
        "oversize-resync",
        "oversize-chunks",
        "reset",
        "invalid",
    ],
)
def test_ndjson_framer_contract(framer_harness: Path, scenario: str) -> None:
    subprocess.run([framer_harness, scenario], check=True)
