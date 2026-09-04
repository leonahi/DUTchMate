from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("command_response_harness.c")


@pytest.fixture(scope="module")
def response_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("command-response") / "command-response"
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
            str(FIRMWARE_SOURCE / "command_response.c"),
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


@pytest.mark.parametrize(
    ("scenario", "expected"),
    [
        ("success", b'{"ok":true}\n'),
        ("timestamp", b'{"ok":true,"timestamp_us":182334400}\n'),
        (
            "uart-send",
            b'{"ok":true,"timestamp_us":18446744073709551615,'
            b'"bytes_accepted":1024}\n',
        ),
        (
            "error",
            b'{"ok":false,"error":"not_configured",'
            b'"detail":"CTRL0 is not configured"}\n',
        ),
    ],
)
def test_response_matches_v1_frame(
    response_harness: Path,
    scenario: str,
    expected: bytes,
) -> None:
    result = _run(response_harness, scenario)

    assert result.returncode == 0
    assert result.stdout == expected


def test_error_response_preserves_utf8_and_escapes_json(
    response_harness: Path,
) -> None:
    result = _run(response_harness, "escaped-error")

    assert result.returncode == 0
    assert json.loads(result.stdout) == {
        "ok": False,
        "error": "hardware_fault",
        "detail": 'DUT é said "no\\retry"',
    }
    assert b'\\"no\\\\retry\\"' in result.stdout


def test_response_rejects_invalid_bounds(response_harness: Path) -> None:
    result = _run(response_harness, "invalid")

    assert result.returncode == 0
    assert result.stdout == b""
