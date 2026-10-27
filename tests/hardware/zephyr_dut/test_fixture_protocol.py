from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE_ROOT = REPO_ROOT / "hardware" / "firmware" / "zephyr_dut"
HARNESS_SOURCE = Path(__file__).with_name("fixture_protocol_harness.c")


def _build_harness(tmp_path: Path, *, uart: bool = False) -> Path:
    compiler = shutil.which("cc")
    if compiler is None:
        raise AssertionError("a host C compiler is required for the Zephyr DUT protocol tests")

    executable = tmp_path / "fixture-protocol"
    if uart:
        # Compile the actual firmware UART loop against host-only I/O stubs.
        for header in ("device.h", "devicetree.h", "drivers/gpio.h", "drivers/uart.h", "kernel.h"):
            stub = tmp_path / "zephyr" / header
            stub.parent.mkdir(parents=True, exist_ok=True)
            stub.write_text('#include "fixture_uart_stubs.h"\n')
    source = HARNESS_SOURCE.with_name("fixture_uart_harness.c") if uart else HARNESS_SOURCE
    result = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-I",
            str(FIXTURE_ROOT / "src"),
            "-I",
            str(tmp_path),
            "-I",
            str(HARNESS_SOURCE.parent),
            str(source),
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


def test_delayed_fault_acknowledges_without_blocking_or_emitting_fault(tmp_path: Path) -> None:
    result = _run_command(tmp_path, "DELAYFAULT", trace=True)

    assert result.stdout == b"DMF/1 DELAYFAULT armed delay_ms=10000\n"
    assert result.stderr == b"W:38\n"


def _run_timeline(tmp_path: Path, *steps: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        [_build_harness(tmp_path), "timeline", *steps], check=True, capture_output=True
    )


def test_delayed_fault_is_due_after_ack_and_ping_and_fires_only_once(tmp_path: Path) -> None:
    result = _run_timeline(
        tmp_path, "@100", "DELAYFAULT", "@101", "PING", "@10100", "@10101", "@50000"
    )

    assert result.stdout == (
        b"DMF/1 DELAYFAULT armed delay_ms=10000\n"
        b"DMF/1 PONG\n"
        b"DMF/1 ERROR ASYNC code=E_ASYNC_001\n"
    )
    assert result.stderr == b"T:100\nT:101\nT:10101\n"


def test_delayed_fault_rearm_replaces_the_pending_deadline(tmp_path: Path) -> None:
    result = _run_timeline(
        tmp_path, "@100", "DELAYFAULT", "@101", "@200", "DELAYFAULT",
        "@201", "@10101", "@10200", "@10201", "@50000",
    )

    assert result.stdout == (
        b"DMF/1 DELAYFAULT armed delay_ms=10000\n" * 2
        + b"DMF/1 ERROR ASYNC code=E_ASYNC_001\n"
    )
    assert result.stderr == b"T:100\nT:200\nT:10201\n"


def test_silent_cancels_pending_fault_and_rejects_rearming(tmp_path: Path) -> None:
    result = _run_timeline(
        tmp_path, "DELAYFAULT", "@1", "SILENT", "DELAYFAULT", "PING", "@20000"
    )

    assert result.stdout == (
        b"DMF/1 DELAYFAULT armed delay_ms=10000\nDMF/1 SILENT armed-until-reset\n"
    )


def test_poll_without_an_armed_fault_emits_nothing(tmp_path: Path) -> None:
    result = _run_timeline(tmp_path, "@0", "@10000", "@50000")

    assert result.stdout == b""


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

    assert result.stdout == (
        b"DMF/1 ERROR COMMAND code=E_COMMAND_001 "
        b"command_len=7 command_hex=554e4b4e4f574e discard=0\n"
    )


def _run_uart(tmp_path: Path, ingress: bytes) -> bytes:
    result = subprocess.run(
        [_build_harness(tmp_path, uart=True)], input=ingress, check=True, capture_output=True
    )
    boot = b"DMF/1 BOOT OK board=rpi_pico build=test-build\n"
    assert result.stdout.startswith(boot)
    assert result.stderr == b""
    return result.stdout[len(boot):]


@pytest.mark.parametrize(
    ("ingress", "diagnostic"),
    [
        (b"UNKNOWN\n", b"command_len=7 command_hex=554e4b4e4f574e discard=0\n"),
        (b"\x00INFO\n", b"command_len=5 command_hex=00494e464f discard=0\n"),
        (b"XINFO\n", b"command_len=5 command_hex=58494e464f discard=0\n"),
        (b"IN\x00FO\n", b"command_len=5 command_hex=494e00464f discard=0\n"),
        (b"INFO\x00\x80\xff\n", b"command_len=7 command_hex=494e464f0080ff discard=0\n"),
        (b"X\rIN\rFO\r\n", b"command_len=5 command_hex=58494e464f discard=0\n"),
        (b"\r\n", b"command_len=0 command_hex= discard=0\n"),
    ],
)
def test_uart_unknown_command_reports_every_interpreted_byte(
    tmp_path: Path, ingress: bytes, diagnostic: bytes
) -> None:
    assert _run_uart(tmp_path, ingress) == (
        b"DMF/1 ERROR COMMAND code=E_COMMAND_001 " + diagnostic
    )


def test_uart_crs_are_ignored_and_success_has_no_diagnostics(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"P" + b"\r" * 100 + b"ING\r\nIN\rFO\n") == (
        b"DMF/1 PONG\nDMF/1 INFO board=rpi_pico build=test-build protocol=1\n"
    )


def test_uart_unterminated_prefix_emits_nothing(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"XINFO") == b""


def test_uart_full_32_byte_command_diagnostic_is_not_truncated(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"X" * 31 + b"\x00\n") == (
        b"DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=32 command_hex="
        + b"58" * 31 + b"00 discard=0\n"
    )


def test_uart_overflow_discards_until_lf_then_accepts_next_command(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"X" * 33 + b"\rINFO\x00\nINFO\n\n") == (
        b"DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=1\n"
        b"DMF/1 INFO board=rpi_pico build=test-build protocol=1\n"
        b"DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=0 command_hex= discard=0\n"
    )


def test_uart_unterminated_overflow_emits_nothing(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"X" * 100) == b""


def test_uart_silent_mode_suppresses_even_unknown_diagnostics(tmp_path: Path) -> None:
    assert _run_uart(tmp_path, b"SILENT\nXINFO\n" + b"X" * 33 + b"\n") == (
        b"DMF/1 SILENT armed-until-reset\n"
    )
