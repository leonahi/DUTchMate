from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "hardware" / "firmware" / "zephyr_dut"
HARNESS_SOURCE = Path(__file__).with_name("fixture_protocol_harness.c")


def _build_harness(tmp_path: Path) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for the Zephyr DUT protocol tests")

    executable = tmp_path / "fixture-protocol"
    result = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FIXTURE_ROOT / "src"),
            str(HARNESS_SOURCE),
            str(FIXTURE_ROOT / "src" / "fixture_protocol.c"),
            "-o",
            str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return executable


def test_success_boot_emits_unambiguous_marker(tmp_path: Path) -> None:
    fixture_harness = _build_harness(tmp_path)
    result = subprocess.run(
        [fixture_harness, "boot", "0"],
        check=True,
        capture_output=True,
    )

    assert result.stdout == b"DMF/1 BOOT OK board=rpi_pico build=test-build\n"


def test_init_failure_boot_emits_stable_first_error(tmp_path: Path) -> None:
    fixture_harness = _build_harness(tmp_path)
    result = subprocess.run(
        [fixture_harness, "boot", "1"],
        check=True,
        capture_output=True,
    )

    assert result.stdout == (
        b"DMF/1 ERROR INIT code=E_INIT_001 board=rpi_pico build=test-build\n"
    )


def test_silent_boot_emits_no_bytes(tmp_path: Path) -> None:
    fixture_harness = _build_harness(tmp_path)
    result = subprocess.run(
        [fixture_harness, "boot", "2"],
        check=True,
        capture_output=True,
    )

    assert result.stdout == b""


def test_invalid_boot_mode_emits_stable_configuration_error(tmp_path: Path) -> None:
    fixture_harness = _build_harness(tmp_path)
    result = subprocess.run(
        [fixture_harness, "boot", "3"],
        check=True,
        capture_output=True,
    )

    assert result.stdout == (
        b"DMF/1 ERROR MODE code=E_MODE_001 board=rpi_pico build=test-build\n"
    )


def _run_command(
    tmp_path: Path, command: str, *, trace: bool = False
) -> subprocess.CompletedProcess[bytes]:
    fixture_harness = _build_harness(tmp_path)
    mode = "trace-command" if trace else "command"
    return subprocess.run(
        [fixture_harness, mode, command],
        check=True,
        capture_output=True,
    )


def test_ping_proves_uart_command_response(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "PING")

    assert result.stdout == b"DMF/1 PONG\n"


def test_info_reports_fixture_identity_and_build(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "INFO")

    assert result.stdout == b"DMF/1 INFO board=rpi_pico build=test-build protocol=1\n"


def test_partial_splits_one_line_across_two_writes(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "PARTIAL", trace=True)

    assert result.stdout == b"DMF/1 PARTIAL complete\n"
    assert result.stderr == b"W:10\nS:50\nW:13\n"


def test_binary_emits_invalid_utf8_bytes_without_encoding(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "BINARY")

    assert result.stdout == b"DMF/1 BINARY \xf0(\x8c(\xff\xfe\n"


def test_burst_is_bounded_numbered_and_self_checking(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "BURST")
    lines = result.stdout.splitlines()

    assert len(lines) == 2050
    assert lines[0] == b"DMF/1 BURST BEGIN count=2048"
    assert lines[1] == b"DMF/1 BURST seq=0000"
    assert lines[-2] == b"DMF/1 BURST seq=2047"
    assert lines[-1] == b"DMF/1 BURST END count=2048 checksum=2096128"


def test_sustained_output_is_bounded_numbered_and_paced(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "SUSTAIN", trace=True)
    lines = result.stdout.splitlines()

    assert len(lines) == 4098
    assert lines[0] == b"DMF/1 SUSTAIN BEGIN count=4096 interval_ms=2"
    assert lines[1] == b"DMF/1 SUSTAIN seq=0000"
    assert lines[-2] == b"DMF/1 SUSTAIN seq=4095"
    assert lines[-1] == b"DMF/1 SUSTAIN END count=4096 checksum=8386560"
    assert result.stderr.count(b"S:2\n") == 4096


def test_silent_command_acknowledges_then_mutes_until_reset(tmp_path: Path) -> None:
    fixture_harness = _build_harness(tmp_path)
    result = subprocess.run(
        [fixture_harness, "sequence", "SILENT", "PING"],
        check=True,
        capture_output=True,
    )

    assert result.stdout == b"DMF/1 SILENT armed-until-reset\n"


def test_unknown_command_has_stable_error(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "UNKNOWN")

    assert result.stdout == b"DMF/1 ERROR COMMAND code=E_COMMAND_001\n"
