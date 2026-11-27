#include "platform_io.h"

#include <stddef.h>

#ifdef CONFIG_DUTCHMATE_SENSE_PAD_REPORT
#include <stdio.h>
#endif

#include <hardware/structs/pads_bank0.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/gpio.h>
#include <zephyr/sys/util.h>

#ifdef CONFIG_ADC
#include <hardware/timer.h>
#include <zephyr/drivers/adc.h>
#include <zephyr/irq.h>
#include "uart_rx.h"
#include <zephyr/kernel.h>

BUILD_ASSERT(DT_CHILD_NUM(DT_PHANDLE(DT_NODELABEL(adc), pinctrl_0)) == 0,
             "ADC boot pinctrl must not write digital pads");

static const struct device *const vio_adc = DEVICE_DT_GET(DT_NODELABEL(adc));
static struct k_poll_signal vio_signal;
static uint16_t vio_buffer;
static uint64_t vio_completed_us;
static uint64_t vio_completed_sequence;
static bool vio_initialized;
static bool vio_active;

static enum adc_action vio_complete(const struct device *dev,
				  const struct adc_sequence *sequence, uint16_t index)
{
	ARG_UNUSED(dev);
	ARG_UNUSED(sequence);
	ARG_UNUSED(index);
	/* Timestamp and ordering position describe the same completion instant. */
	unsigned int key = irq_lock();
	struct dmh_uart_rx_snapshot snapshot;
	vio_completed_us = time_us_64();
	dutchmate_uart_rx_snapshot_observation(&snapshot, &vio_completed_sequence);
	irq_unlock(key);
	return ADC_ACTION_CONTINUE;
}

int dutchmate_platform_vio_initialize(void)
{
	const struct adc_channel_cfg channel = {
		.gain = ADC_GAIN_1, .reference = ADC_REF_VDD_1,
		.acquisition_time = ADC_ACQ_TIME_DEFAULT, .channel_id = 2U,
	};
	int result;

	if (!device_is_ready(vio_adc)) return -ENODEV;
	result = adc_channel_setup(vio_adc, &channel);
	if (result != 0) return result;
	k_poll_signal_init(&vio_signal);
	vio_initialized = true;
	return 0;
}

bool dutchmate_platform_vio_ready(void)
{
	return vio_initialized;
}

static int vio_start(void *context)
{
	static const struct adc_sequence_options options = {.callback = vio_complete};
	const struct adc_sequence sequence = {
		.options = &options, .channels = BIT(2), .buffer = &vio_buffer,
		.buffer_size = sizeof(vio_buffer), .resolution = 12U,
	};
	int result;

	ARG_UNUSED(context);
	if (!vio_initialized || vio_active) return -EBUSY;
	k_poll_signal_reset(&vio_signal);
	vio_completed_us = 0U;
	vio_active = true;
	result = adc_read_async(vio_adc, &sequence, &vio_signal);
	if (result != 0) vio_active = false;
	return result;
}

static enum dmh_vio_adc_result vio_poll(void *context, uint16_t *raw, uint64_t *done,
				      uint64_t *observation_sequence)
{
	unsigned int signaled;
	int result;

	ARG_UNUSED(context);
	if (!vio_active) return DMH_VIO_ADC_ERROR;
	k_poll_signal_check(&vio_signal, &signaled, &result);
	if (!signaled) return DMH_VIO_ADC_PENDING;
	/* Completion signal publishes the ISR's buffer and completion timestamp. */
	vio_active = false;
	if (result != 0) return DMH_VIO_ADC_ERROR;
	*raw = vio_buffer;
	*done = vio_completed_us;
	*observation_sequence = vio_completed_sequence;
	return DMH_VIO_ADC_COMPLETE;
}

bool dutchmate_platform_vio_completion_ready(void)
{
	unsigned int signaled;
	int result;

	if (!vio_active) return false;
	k_poll_signal_check(&vio_signal, &signaled, &result);
	return signaled != 0U;
}

struct dmh_vio_adc_port dutchmate_platform_vio_port(void)
{
	return (struct dmh_vio_adc_port) {.start = vio_start, .poll = vio_poll};
}
#else
int dutchmate_platform_vio_initialize(void) { return -ENOTSUP; }
bool dutchmate_platform_vio_ready(void) { return false; }
bool dutchmate_platform_vio_completion_ready(void) { return false; }
struct dmh_vio_adc_port dutchmate_platform_vio_port(void)
{
	return (struct dmh_vio_adc_port){0};
}
#endif

#define DUTCHMATE_IO_NODE DT_NODELABEL(dutchmate_io)
#define DUTCHMATE_CHANNEL_COUNT 4U

BUILD_ASSERT(DT_NODE_HAS_STATUS(DUTCHMATE_IO_NODE, okay));
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, ctrl_enable_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, ctrl_data_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DT_PROP_LEN(DUTCHMATE_IO_NODE, event_input_gpios) == DUTCHMATE_CHANNEL_COUNT);
BUILD_ASSERT(DMH_CONTROL_CHANNEL_COUNT == DUTCHMATE_CHANNEL_COUNT);

#ifdef CONFIG_DUTCHMATE_SENSE_PAD_REPORT
/* Reserve ten version bytes for "-p" and eight raw-register hex digits. */
BUILD_ASSERT(sizeof(CONFIG_DUTCHMATE_FIRMWARE_VERSION) <= 55U);

int dutchmate_platform_sense_probe_firmware(char *output, size_t capacity)
{
	int length;

	if (output == NULL) {
		return -EINVAL;
	}
	length = snprintf(
		output, capacity, "%s-p%08lx", CONFIG_DUTCHMATE_FIRMWARE_VERSION,
		(unsigned long)pads_bank0_hw->io[28]
	);
	if (length < 0) {
		return -EIO;
	}
	return (size_t)length >= capacity ? -ENOSPC : 0;
}
#endif

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

	/* Keep GP28/ADC2 unloaded before any negotiated ADC sampling. */
	result = gpio_pin_configure(
		DEVICE_DT_GET(DT_NODELABEL(gpio0)), 28U, GPIO_DISCONNECTED
	);
	if (result != 0) {
		return result;
	}
	/* Release the reset pull latch only after disabling pulls, input and output. */
	hw_clear_bits(&pads_bank0_hw->io[28], PADS_BANK0_GPIO28_ISO_BITS);

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
