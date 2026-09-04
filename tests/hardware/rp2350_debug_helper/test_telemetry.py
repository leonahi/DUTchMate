from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("telemetry_harness.c")


@pytest.fixture(scope="module")
def telemetry_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("telemetry") / "telemetry"
    result = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-D_GNU_SOURCE",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FIRMWARE_SOURCE),
            str(HARNESS_SOURCE),
            str(FIRMWARE_SOURCE / "telemetry.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return executable


def _run(harness: Path, scenario: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run([harness, scenario], check=False, capture_output=True)


def test_buffer_overflow_matches_canonical_v1_frame(telemetry_harness: Path) -> None:
    result = _run(telemetry_harness, "overflow")

    assert result.returncode == 0
    assert result.stdout == (
        b'{"type":"buffer_overflow","channel":0,"timestamp_us":182350000,'
        b'"dropped_bytes":512}\n'
    )


def test_buffer_status_matches_canonical_v1_frame(telemetry_harness: Path) -> None:
    result = _run(telemetry_harness, "status")

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "type": "buffer_status",
        "timestamp_us": 182360000,
        "uart_rx_size_bytes": 32768,
        "uart_rx_used_bytes": 4096,
        "uart_rx_high_water_bytes": 18432,
        "dropped_bytes_total": 512,
        "overflow_events": 1,
    }
    assert result.stdout.endswith(b"\n")


@pytest.mark.parametrize("scenario", ["full-width", "invalid", "schedule"])
def test_telemetry_bounds_and_schedule(
    telemetry_harness: Path,
    scenario: str,
) -> None:
    result = _run(telemetry_harness, scenario)

    assert result.returncode == 0
    assert result.stdout == b""
