from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("hello_harness.c")


def _build_harness(tmp_path: Path) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path / "debug-helper-hello"
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
            str(FIRMWARE_SOURCE / "hello.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return executable


def _run_hello(tmp_path: Path, firmware: str) -> subprocess.CompletedProcess[bytes]:
    harness = _build_harness(tmp_path)
    return subprocess.run(
        [harness, firmware],
        check=False,
        capture_output=True,
    )


def test_hello_matches_complete_v1_identity_and_capability_contract(tmp_path: Path) -> None:
    result = _run_hello(tmp_path, "0.1.0")

    assert result.returncode == 0
    assert result.stdout == (
        b'{"type":"hello","v":1,"firmware":"0.1.0",'
        b'"device":"dutchmate-rp2350","capabilities":["uart_receive",'
        b'"gpio_control","uart_send","device_timestamp","overflow_telemetry"]}\n'
    )


def test_hello_accepts_64_byte_safe_firmware_identifier(tmp_path: Path) -> None:
    firmware = "a" * 64

    result = _run_hello(tmp_path, firmware)

    assert result.returncode == 0
    assert b'"firmware":"' + firmware.encode() + b'"' in result.stdout


@pytest.mark.parametrize(
    "firmware",
    ["", "a" * 65, " leading", "trailing ", 'quote"', "slash/"],
)
def test_hello_rejects_unsafe_firmware_identifier(tmp_path: Path, firmware: str) -> None:
    result = _run_hello(tmp_path, firmware)

    assert result.returncode == 2
    assert result.stdout == b""
