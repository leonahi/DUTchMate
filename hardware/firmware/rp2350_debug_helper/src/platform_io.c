#include "platform_io.h"

#include <stddef.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/util.h>

#define DUTCHMATE_IO_NODE DT_NODELABEL(dutchmate_io)
#define DUTCHMATE_CHANNEL_COUNT 4U

BUILD_ASSERT(DT_NODE_HAS_STATUS(DUTCHMATE_IO_NODE, okay));
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, ctrl_enable_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, ctrl_data_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, event_input_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DMH_CONTROL_CHANNEL_COUNT == DUTCHMATE_CHANNEL_COUNT);

static const struct gpio_dt_spec uart_interface_enable =
	GPIO_DT_SPEC_GET(DUTCHMATE_IO_NODE, uart_interface_enable_gpios);
static const struct gpio_dt_spec event_interface_enable =
	GPIO_DT_SPEC_GET(DUTCHMATE_IO_NODE, event_interface_enable_gpios);

static const struct gpio_dt_spec ctrl_enable[DUTCHMATE_CHANNEL_COUNT] = {
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_enable_gpios, 0),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_enable_gpios, 1),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_enable_gpios, 2),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_enable_gpios, 3),
};

static const struct gpio_dt_spec ctrl_data[DUTCHMATE_CHANNEL_COUNT] = {
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_data_gpios, 0),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_data_gpios, 1),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_data_gpios, 2),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, ctrl_data_gpios, 3),
};

static const struct gpio_dt_spec event_input[DUTCHMATE_CHANNEL_COUNT] = {
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, event_input_gpios, 0),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, event_input_gpios, 1),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, event_input_gpios, 2),
	GPIO_DT_SPEC_GET_BY_IDX(DUTCHMATE_IO_NODE, event_input_gpios, 3),
};

static int record_first_error(int first_error, int result)
{
	return first_error != 0 ? first_error : result;
}

static int set_all_inactive(const struct gpio_dt_spec *pins, size_t count)
{
	int first_error = 0;
	size_t index;

	for (index = 0U; index < count; index++) {
		first_error = record_first_error(first_error, gpio_pin_set_dt(&pins[index], 0));
	}

	return first_error;
}

int dutchmate_platform_io_force_safe(void)
{
	int first_error;

	first_error = gpio_pin_set_dt(&uart_interface_enable, 0);
	first_error = record_first_error(
		first_error,
		gpio_pin_set_dt(&event_interface_enable, 0)
	);
	first_error = record_first_error(
		first_error,
		set_all_inactive(ctrl_enable, ARRAY_SIZE(ctrl_enable))
	);
	first_error = record_first_error(
		first_error,
		set_all_inactive(ctrl_data, ARRAY_SIZE(ctrl_data))
	);

	return first_error;
}

int dutchmate_platform_uart_interface_set(bool active)
{
	return gpio_pin_set_dt(&uart_interface_enable, active ? 1 : 0);
}

static int control_set_enable(void *context, uint8_t channel, bool enabled)
{
	ARG_UNUSED(context);
	if (channel >= DUTCHMATE_CHANNEL_COUNT) {
		return -EINVAL;
	}
	return gpio_pin_set_dt(&ctrl_enable[channel], enabled ? 1 : 0);
}

static int control_set_data(
	void *context,
	uint8_t channel,
	enum dmh_control_level level
)
{
	ARG_UNUSED(context);
	if (channel >= DUTCHMATE_CHANNEL_COUNT ||
	    (level != DMH_CONTROL_LEVEL_LOW && level != DMH_CONTROL_LEVEL_HIGH)) {
		return -EINVAL;
	}
	return gpio_pin_set_dt(
		&ctrl_data[channel],
		level == DMH_CONTROL_LEVEL_HIGH ? 1 : 0
	);
}

struct dmh_control_port dutchmate_platform_control_port(void)
{
	return (struct dmh_control_port) {
		.context = NULL,
		.set_enable = control_set_enable,
		.set_data = control_set_data,
	};
}

int dutchmate_platform_io_initialize_safe(void)
{
	int result;
	size_t index;

	if (!gpio_is_ready_dt(&uart_interface_enable) ||
	    !gpio_is_ready_dt(&event_interface_enable)) {
		return -ENODEV;
	}
	for (index = 0U; index < DUTCHMATE_CHANNEL_COUNT; index++) {
		if (!gpio_is_ready_dt(&ctrl_enable[index]) ||
		    !gpio_is_ready_dt(&ctrl_data[index]) ||
		    !gpio_is_ready_dt(&event_input[index])) {
			return -ENODEV;
		}
	}

	result = gpio_pin_configure_dt(&uart_interface_enable, GPIO_OUTPUT_INACTIVE);
	if (result != 0) {
		return result;
	}
	result = gpio_pin_configure_dt(&event_interface_enable, GPIO_OUTPUT_INACTIVE);
	if (result != 0) {
		return result;
	}
	for (index = 0U; index < DUTCHMATE_CHANNEL_COUNT; index++) {
		result = gpio_pin_configure_dt(&ctrl_enable[index], GPIO_OUTPUT_INACTIVE);
		if (result != 0) {
			return result;
		}
	}
	for (index = 0U; index < DUTCHMATE_CHANNEL_COUNT; index++) {
		result = gpio_pin_configure_dt(&ctrl_data[index], GPIO_OUTPUT_INACTIVE);
		if (result != 0) {
			return result;
		}
	}
	for (index = 0U; index < DUTCHMATE_CHANNEL_COUNT; index++) {
		result = gpio_pin_configure_dt(&event_input[index], GPIO_INPUT);
		if (result != 0) {
			return result;
		}
	}

	return dutchmate_platform_io_force_safe();
}
