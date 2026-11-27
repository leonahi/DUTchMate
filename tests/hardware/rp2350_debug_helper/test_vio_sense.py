import subprocess
from pathlib import Path

import pytest

SOURCE = Path(__file__).parents[3] / "hardware/firmware/rp2350_debug_helper/src"


@pytest.fixture(scope="module")
def vio_harness(tmp_path_factory):
    output = tmp_path_factory.mktemp("vio-sense") / "harness"
    result = subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(SOURCE),
            str(Path(__file__).with_name("vio_sense_harness.c")),
            str(SOURCE / "vio_sense.c"),
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return output


@pytest.mark.parametrize(
    "scenario",
    [
        "valid",
        "zero",
        "saturated",
        "start-error",
        "read-error",
        "timeout",
        "late",
        "epoch",
        "disable",
    ],
)
def test_vio_sampling_bounds_and_late_driver_ownership(vio_harness, scenario):
    result = subprocess.run([str(vio_harness), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
