from __future__ import annotations

import base64
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIRMWARE_SOURCE = REPO_ROOT / "hardware" / "firmware" / "rp2350_debug_helper" / "src"
HARNESS_SOURCE = Path(__file__).with_name("uart_event_harness.c")


@pytest.fixture(scope="module")
def uart_event_harness(tmp_path_factory: pytest.TempPathFactory) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for Debug Helper tests")

    executable = tmp_path_factory.mktemp("uart-event") / "uart-event"
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
            str(FIRMWARE_SOURCE / "uart_event.c"),
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


def test_uart_event_matches_canonical_v1_frame(uart_event_harness: Path) -> None:
    result = _run(uart_event_harness, "canonical")

    assert result.returncode == 0
    assert result.stdout == (
        b'{"type":"uart","channel":0,"timestamp_us":182341200,'
        b'"data_b64":"Qk9PVF9PSwo="}\n'
    )


@pytest.mark.parametrize(
    ("scenario", "channel", "timestamp_us", "expected_data"),
    [
        ("one", 1, 0, b"\xff"),
        ("two", 2, 1, b"\x00\xfe"),
        ("three", 255, 2**64 - 1, b"\x00\x01\x02"),
    ],
)
def test_uart_event_encodes_binary_and_base64_padding(
    uart_event_harness: Path,
    scenario: str,
    channel: int,
    timestamp_us: int,
    expected_data: bytes,
) -> None:
    result = _run(uart_event_harness, scenario)

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload == {
        "type": "uart",
        "channel": channel,
        "timestamp_us": timestamp_us,
        "data_b64": base64.b64encode(expected_data).decode("ascii"),
    }
    assert result.stdout.endswith(b"\n")


def test_uart_event_accepts_bounded_staging_maximum(uart_event_harness: Path) -> None:
    result = _run(uart_event_harness, "maximum")

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert base64.b64decode(payload["data_b64"], validate=True) == bytes(
        index & 0xFF for index in range(1024)
    )
    assert len(result.stdout) <= 1536


@pytest.mark.parametrize("scenario", ["zero", "oversized", "small-output"])
def test_uart_event_rejects_invalid_bounds(
    uart_event_harness: Path,
    scenario: str,
) -> None:
    result = _run(uart_event_harness, scenario)

    assert result.returncode == 2
    assert result.stdout == b""
