from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

FIRMWARE_SOURCE = (
    Path(__file__).resolve().parents[3] / "hardware/firmware/rp2350_debug_helper/src"
)
HARNESS_SOURCE = Path(__file__).with_name("sense_pin_probe_harness.c")

# Only the Zephyr GPIO boundary is replaced; initialization runs from platform_io.c.
ZEPHYR_STUBS = """
#ifndef SENSE_PIN_PROBE_STUBS_H
#define SENSE_PIN_PROBE_STUBS_H
#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>
#include <errno.h>
struct device { bool ready; };
extern struct device test_gpio0;
struct test_pad_registers { uint32_t io[48]; };
extern struct test_pad_registers test_pads;
#define pads_bank0_hw (&test_pads)
#define PADS_BANK0_GPIO28_ISO_BITS 0x100U
static inline void hw_clear_bits(volatile uint32_t *address, uint32_t mask) {
    *address &= ~mask;
}
struct gpio_dt_spec { const struct device *port; unsigned int pin; unsigned int dt_flags; };
#define BUILD_ASSERT(condition) _Static_assert(condition, #condition)
#define DT_NODELABEL(name) 0
#define DT_NODE_HAS_STATUS(node, status) 1
#define DT_PROP_LEN(node, prop) 4
#define DEVICE_DT_GET(node) (&test_gpio0)
#define GPIO_DISCONNECTED 0U
#define GPIO_INPUT 1U
#define GPIO_OUTPUT_INACTIVE 2U
#define ARRAY_SIZE(value) (sizeof(value) / sizeof((value)[0]))
#define ARG_UNUSED(value) (void)(value)
#define TEST_uart_interface_enable_gpios 2U
#define TEST_event_interface_enable_gpios 11U
#define TEST_ctrl_enable_gpios_0 8U
#define TEST_ctrl_enable_gpios_1 7U
#define TEST_ctrl_enable_gpios_2 26U
#define TEST_ctrl_enable_gpios_3 22U
#define TEST_ctrl_data_gpios_0 9U
#define TEST_ctrl_data_gpios_1 10U
#define TEST_ctrl_data_gpios_2 20U
#define TEST_ctrl_data_gpios_3 21U
#define TEST_event_input_gpios_0 15U
#define TEST_event_input_gpios_1 14U
#define TEST_event_input_gpios_2 13U
#define TEST_event_input_gpios_3 12U
#define GPIO_DT_SPEC_GET(node, prop) { &test_gpio0, TEST_##prop, 0U }
#define GPIO_DT_SPEC_GET_BY_IDX(node, prop, index) \\
    { &test_gpio0, TEST_##prop##_##index, 0U }
int gpio_pin_configure(const struct device *port, unsigned int pin, unsigned int flags);
int gpio_pin_set(const struct device *port, unsigned int pin, int value);
static inline bool device_is_ready(const struct device *port) { return port->ready; }
static inline bool gpio_is_ready_dt(const struct gpio_dt_spec *spec) {
    return device_is_ready(spec->port);
}
static inline int gpio_pin_configure_dt(const struct gpio_dt_spec *spec, unsigned int flags) {
    return gpio_pin_configure(spec->port, spec->pin, flags | spec->dt_flags);
}
static inline int gpio_pin_set_dt(const struct gpio_dt_spec *spec, int value) {
    return gpio_pin_set(spec->port, spec->pin, value);
}
#endif
"""


@pytest.mark.parametrize(
    ("pad_report", "scenario"),
    [
        (False, "startup"),
        (False, "configure-error"),
        (True, "startup"),
        (True, "pad-report"),
        (True, "pad-report-bounds"),
    ],
)
def test_sense_pin_probe_initialization(
    tmp_path: Path,
    pad_report: bool,
    scenario: str,
) -> None:
    compiler = shutil.which("cc")
    assert compiler is not None, "a host C compiler is required for Debug Helper tests"
    (tmp_path / "sense_pin_probe_stubs.h").write_text(ZEPHYR_STUBS)
    for header in (
        "zephyr/device.h",
        "zephyr/devicetree.h",
        "zephyr/drivers/gpio.h",
        "zephyr/sys/util.h",
        "hardware/structs/pads_bank0.h",
    ):
        path = tmp_path / header
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#include "sense_pin_probe_stubs.h"\n')
    executable = tmp_path / "sense-pin-probe"
    compiled = subprocess.run(
        [
            compiler,
            "-std=c11",
            "-Wall",
            "-Wextra",
            "-Werror",
            '-DCONFIG_DUTCHMATE_FIRMWARE_VERSION="sensepad-2"',
            *(["-DCONFIG_DUTCHMATE_SENSE_PAD_REPORT=1"] if pad_report else []),
            "-I", str(tmp_path),
            "-I", str(FIRMWARE_SOURCE),
            str(HARNESS_SOURCE),
            str(FIRMWARE_SOURCE / "platform_io.c"),
            "-o", str(executable),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert compiled.returncode == 0, compiled.stderr
    result = subprocess.run([executable, scenario], check=False, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
