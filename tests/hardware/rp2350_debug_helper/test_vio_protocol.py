import json
import subprocess
from pathlib import Path

import pytest

from dutchmate_core.device_connection.parser import parse_device_message

SOURCE = Path(__file__).parents[3] / "hardware/firmware/rp2350_debug_helper/src"


@pytest.fixture(scope="module")
def vio_protocol(tmp_path_factory):
    output = tmp_path_factory.mktemp("vio-protocol") / "harness"
    sources = [
        "command_decode.c",
        "command_executor.c",
        "command_response.c",
        "control_state.c",
        "uart_tx_state.c",
        "telemetry.c",
        "hello.c",
    ]
    result = subprocess.run(
        [
            "cc",
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            "-DCONFIG_ADC=1",
            "-I",
            str(SOURCE),
            str(Path(__file__).with_name("vio_protocol_harness.c")),
            *[str(SOURCE / x) for x in sources],
            "-o",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    return output


@pytest.mark.parametrize("scenario", ["decode", "ack", "ack-error", "cancel"])
def test_sensing_commands_require_ack_and_cancel_with_epoch(vio_protocol, scenario):
    result = subprocess.run([str(vio_protocol), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    if scenario == "ack":
        assert json.loads(result.stdout) == {"ok": True, "timestamp_us": 100}
    if scenario == "ack-error":
        assert json.loads(result.stdout)["error"] == "hardware_fault"


@pytest.mark.parametrize(
    "scenario,status,mv",
    [
        ("sample", "ok", 4950),
        ("adc-error", "adc_error", None),
        ("saturated", "saturated", None),
    ],
)
def test_real_firmware_voltage_frames_match_host_parser(vio_protocol, scenario, status, mv):
    result = subprocess.run([str(vio_protocol), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    message = parse_device_message(result.stdout)
    assert message.sample.status == status
    assert message.sample.voltage_mv == mv
    assert message.timestamp_us == 1234567


def test_sensing_hello_preserves_maximum_identity_and_frame_bound(vio_protocol):
    result = subprocess.run([str(vio_protocol), "hello"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    message = parse_device_message(result.stdout)
    assert message.firmware == "f" * 64
    assert "power_sense" in message.capabilities
    assert len(result.stdout.encode()) <= 256
