#include "fixture_protocol.h"

#include <stddef.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>

#define FIXTURE_UART_NODE DT_CHOSEN(zephyr_console)
#define FIXTURE_GPIO_NODE DT_NODELABEL(gpio0)

struct zephyr_fixture_context {
    const struct device *uart;
};

static void write_uart(void *context, const unsigned char *data, size_t length)
{
    const struct zephyr_fixture_context *fixture_context = context;
    size_t index;

    for (index = 0U; index < length; index++) {
        uart_poll_out(fixture_context->uart, data[index]);
    }
}

static void sleep_ms(void *context, unsigned int duration_ms)
{
    (void)context;
    k_msleep(duration_ms);
}

static enum dmf_boot_mode read_boot_mode(const struct device *gpio)
{
    int mode0;
    int mode1;

    if (gpio_pin_configure(
            gpio,
            CONFIG_DUTCHMATE_FIXTURE_MODE0_PIN,
            GPIO_INPUT | GPIO_PULL_DOWN
        ) != 0) {
        return DMF_BOOT_INVALID;
    }
    if (gpio_pin_configure(
            gpio,
            CONFIG_DUTCHMATE_FIXTURE_MODE1_PIN,
            GPIO_INPUT | GPIO_PULL_DOWN
        ) != 0) {
        return DMF_BOOT_INVALID;
    }

    mode0 = gpio_pin_get(gpio, CONFIG_DUTCHMATE_FIXTURE_MODE0_PIN);
    mode1 = gpio_pin_get(gpio, CONFIG_DUTCHMATE_FIXTURE_MODE1_PIN);
    if (mode0 < 0 || mode1 < 0) {
        return DMF_BOOT_INVALID;
    }

    return (enum dmf_boot_mode)(((unsigned int)mode1 << 1U) | (unsigned int)mode0);
}

static void count_line_byte(struct dmf_line_diagnostics *line)
{
    if (line->line_len == UINT32_MAX) {
        line->counts_overflow = 1U;
    } else {
        line->line_len++;
    }
}

static void remember_discarded_byte(struct dmf_line_diagnostics *line, unsigned char byte)
{
    if (line->suffix_len == sizeof(line->suffix)) {
        memmove(line->suffix, line->suffix + 1U, sizeof(line->suffix) - 1U);
        line->suffix_len--;
    }
    line->suffix[line->suffix_len] = byte;
    line->suffix_len++;
}

int main(void)
{
    const struct device *const uart = DEVICE_DT_GET(FIXTURE_UART_NODE);
    const struct device *const gpio = DEVICE_DT_GET(FIXTURE_GPIO_NODE);
    struct zephyr_fixture_context context = {.uart = uart};
    struct dmf_fixture fixture;
    unsigned char command[DMF_COMMAND_CAPACITY];
    struct dmf_line_diagnostics line = {0};
    size_t command_length = 0U;
    int discarding = 0;

    if (!device_is_ready(uart) || !device_is_ready(gpio)) {
        return -1;
    }

    dmf_fixture_init(
        &fixture,
        write_uart,
        sleep_ms,
        &context,
        CONFIG_DUTCHMATE_FIXTURE_BUILD_ID
    );
    dmf_fixture_emit_boot(&fixture, read_boot_mode(gpio));

    for (;;) {
        unsigned char byte;

        dmf_fixture_poll(&fixture, (uint64_t)k_uptime_get());
        if (uart_poll_in(uart, &byte) != 0) {
            k_msleep(1U);
            continue;
        }

        if (byte == '\r') {
            continue;
        }
        if (byte == '\n') {
            if (discarding != 0) {
                dmf_fixture_handle_command(&fixture, command, 0U, discarding, &line);
            } else {
                dmf_fixture_handle_command(&fixture, command, command_length, discarding, &line);
            }
            command_length = 0U;
            discarding = 0;
            line = (struct dmf_line_diagnostics){0};
            continue;
        }
        count_line_byte(&line);
        if (discarding != 0) {
            remember_discarded_byte(&line, byte);
            continue;
        }
        if (command_length == sizeof(command)) {
            line.overflow_byte = byte;
            remember_discarded_byte(&line, byte);
            command_length = 0U;
            discarding = 1;
            continue;
        }
        command[command_length] = byte;
        command_length++;
    }

    return 0;
}
