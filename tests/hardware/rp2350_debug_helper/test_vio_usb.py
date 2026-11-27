"""Production USB scheduling with only its Zephyr/physical ports substituted."""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).parents[3]
SOURCE = ROOT / "hardware/firmware/rp2350_debug_helper/src"
STUBS = r"""
#include <stdbool.h>
#include <stdint.h>
struct device { int unused; };
#define DT_NODELABEL(name) 0
#define DEVICE_DT_GET(node) ((const struct device *)0)
#define BUILD_ASSERT(...) _Static_assert(1,"build")
#define IS_ENABLED(...) 0
#define K_MSEC(value) (value)
#define UART_LINE_CTRL_DTR 1
#define UART_LINE_CTRL_DCD 2
#define UART_LINE_CTRL_DSR 3
uint64_t time_us_64(void);
unsigned int irq_lock(void);
void irq_unlock(unsigned int);
void k_sleep(int);
bool device_is_ready(const struct device *);
int uart_line_ctrl_get(const struct device *,int,uint32_t *);
int uart_line_ctrl_set(const struct device *,int,uint32_t);
"""


@pytest.fixture
def usb_harness(tmp_path):
    (tmp_path / "stub.h").write_text("#pragma once\n" + STUBS)
    for name in [
        "hardware/timer.h",
        "zephyr/device.h",
        "zephyr/devicetree.h",
        "zephyr/drivers/uart.h",
        "zephyr/kernel.h",
        "zephyr/irq.h",
        "zephyr/sys/util.h",
    ]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#include "stub.h"\n')
    output = tmp_path / "usb"
    command = [
        shutil.which("cc"),
        "-std=c11",
        "-Wall",
        "-Wextra",
        "-Werror",
        '-DCONFIG_DUTCHMATE_FIRMWARE_VERSION="vio-usb"',
        "-DCONFIG_DUTCHMATE_ADC_REFERENCE_MV=3300",
        "-I",
        str(tmp_path),
        "-I",
        str(SOURCE),
        str(Path(__file__).with_name("vio_usb_harness.c")),
    ]
    command += [
        str(SOURCE / name)
        for name in [
            "vio_sense.c",
            "uart_rx_ring.c",
            "uart_event.c",
            "telemetry.c",
            "hello.c",
            "connection_epoch.c",
            "output_drain.c",
        ]
    ]
    result = subprocess.run(command + ["-o", str(output)], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return output


@pytest.mark.parametrize(
    "scenario",
    ["delayed-poll", "completion-race", "failed-ack", "interrupted-ack", "disable-pending"],
)
def test_usb_voltage_order_and_complete_ack_gate(usb_harness, scenario):
    result = subprocess.run([str(usb_harness), scenario], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    frames = [json.loads(line) for line in result.stdout.splitlines()]
    events = [frame for frame in frames if "type" in frame]
    assert [frame["timestamp_us"] for frame in events] == (
        [50, 100, 110]
        if scenario in ("delayed-poll", "completion-race")
        else [50, 110]
        if scenario == "disable-pending"
        else []
    )
    if scenario in ("delayed-poll", "completion-race"):
        assert [frame["type"] for frame in events] == ["uart", "dut_vio", "uart"]
