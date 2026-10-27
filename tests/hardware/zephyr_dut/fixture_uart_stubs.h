#ifndef DUTCHMATE_TEST_FIXTURE_UART_STUBS_H_
#define DUTCHMATE_TEST_FIXTURE_UART_STUBS_H_

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>

#define DT_CHOSEN(name) 0
#define DT_NODELABEL(name) 0
#define DEVICE_DT_GET(node) (&test_device)
#define GPIO_INPUT 1
#define GPIO_PULL_DOWN 2
#define CONFIG_DUTCHMATE_FIXTURE_MODE0_PIN 2
#define CONFIG_DUTCHMATE_FIXTURE_MODE1_PIN 3
#define CONFIG_DUTCHMATE_FIXTURE_BUILD_ID "test-build"

struct device {
    int unused;
};

static const struct device test_device = {0};
static uint64_t test_uptime_ms;

static inline int device_is_ready(const struct device *device)
{
    (void)device;
    return 1;
}

static inline int gpio_pin_configure(const struct device *device, int pin, int flags)
{
    (void)device;
    (void)pin;
    (void)flags;
    return 0;
}

static inline int gpio_pin_get(const struct device *device, int pin)
{
    (void)device;
    (void)pin;
    return 0;
}

static inline int uart_poll_in(const struct device *device, unsigned char *byte)
{
    const int input = getchar();

    (void)device;
    if (input == EOF) {
        exit(ferror(stdin) ? EXIT_FAILURE : EXIT_SUCCESS);
    }
    *byte = (unsigned char)input;
    return 0;
}

static inline void uart_poll_out(const struct device *device, unsigned char byte)
{
    (void)device;
    (void)putchar(byte);
}

static inline void k_msleep(unsigned int duration_ms)
{
    test_uptime_ms += duration_ms;
}

static inline uint64_t k_uptime_get(void)
{
    return test_uptime_ms;
}

#endif
