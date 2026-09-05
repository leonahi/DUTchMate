#include "command_executor.h"

#include <assert.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define GPIO_OPERATION_CAPACITY 64U

struct gpio_operation {
	uint8_t channel;
	bool enable;
	int value;
};

struct fake_gpio {
	struct gpio_operation operations[GPIO_OPERATION_CAPACITY];
	size_t count;
	size_t fail_at;
};

struct fake_uart {
	uint8_t bytes[DMH_UART_TX_MAX_BYTES];
	size_t length;
	size_t max_write;
	int complete;
	size_t stop_calls;
};

struct harness {
	struct fake_gpio gpio;
	struct fake_uart uart;
	struct dmh_control control;
	struct dmh_uart_tx uart_tx;
	struct dmh_command_executor executor;
	uint64_t uart_timeout_us;
};

static int gpio_enable(void *context, uint8_t channel, bool enabled)
{
	struct fake_gpio *gpio = context;
	size_t index = gpio->count++;

	assert(index < GPIO_OPERATION_CAPACITY);
	gpio->operations[index] = (struct gpio_operation) {
		.channel = channel,
		.enable = true,
		.value = enabled ? 1 : 0,
	};
	return index == gpio->fail_at ? -1 : 0;
}

static int gpio_data(void *context, uint8_t channel, enum dmh_control_level level)
{
	struct fake_gpio *gpio = context;
	size_t index = gpio->count++;

	assert(index < GPIO_OPERATION_CAPACITY);
	gpio->operations[index] = (struct gpio_operation) {
		.channel = channel,
		.enable = false,
		.value = (int)level,
	};
	return index == gpio->fail_at ? -1 : 0;
}

static int uart_write(void *context, const uint8_t *data, size_t length)
{
	struct fake_uart *uart = context;
	size_t written = length < uart->max_write ? length : uart->max_write;

	if (written == 0U) {
		return 0;
	}
	assert(uart->length + written <= sizeof(uart->bytes));
	(void)memcpy(&uart->bytes[uart->length], data, written);
	uart->length += written;
	return (int)written;
}

static int uart_complete(void *context)
{
	struct fake_uart *uart = context;

	return uart->complete;
}

static void uart_stop(void *context)
{
	struct fake_uart *uart = context;

	uart->stop_calls++;
}

static enum dmh_uart_tx_result executor_uart_start(
	void *context,
	const uint8_t *data,
	size_t length,
	uint64_t now_us
)
{
	struct harness *harness = context;

	return dmh_uart_tx_start(
		&harness->uart_tx,
		data,
		length,
		now_us,
		harness->uart_timeout_us
	);
}

static enum dmh_uart_tx_result executor_uart_poll(
	void *context,
	uint64_t now_us,
	size_t *bytes_accepted
)
{
	struct harness *harness = context;

	return dmh_uart_tx_poll(&harness->uart_tx, now_us, bytes_accepted);
}

static void executor_uart_cancel(void *context)
{
	struct harness *harness = context;

	dmh_uart_tx_cancel(&harness->uart_tx);
}

static void harness_init(struct harness *harness)
{
	const struct dmh_control_port control_port = {
		.context = &harness->gpio,
		.set_enable = gpio_enable,
		.set_data = gpio_data,
	};
	const struct dmh_uart_tx_port uart_port = {
		.context = &harness->uart,
		.write = uart_write,
		.is_complete = uart_complete,
		.stop = uart_stop,
	};
	const struct dmh_command_uart_port executor_uart = {
		.context = harness,
		.start = executor_uart_start,
		.poll = executor_uart_poll,
		.cancel = executor_uart_cancel,
	};

	(void)memset(harness, 0, sizeof(*harness));
	harness->gpio.fail_at = SIZE_MAX;
	harness->uart.max_write = DMH_UART_TX_MAX_BYTES;
	harness->uart_timeout_us = 100U;
	dmh_control_init(&harness->control, &control_port);
	dmh_uart_tx_init(&harness->uart_tx, &uart_port);
	dmh_command_executor_init(
		&harness->executor,
		&harness->control,
		&executor_uart
	);
}

static void consume_response(struct harness *harness, bool emit)
{
	const char *response;
	size_t length;

	response = dmh_command_executor_response(&harness->executor, &length);
	assert(response != NULL);
	if (emit) {
		assert(fwrite(response, 1U, length, stdout) == length);
	}
	dmh_command_executor_response_sent(&harness->executor);
}

static struct dmh_command push_pull_command(uint8_t channel)
{
	struct dmh_command command = {
		.kind = DMH_COMMAND_CONFIGURE_GPIO_MODE,
		.channel = channel,
	};

	command.value.configure = (struct dmh_configure_command) {
		.mode = DMH_CONTROL_MODE_PUSH_PULL,
		.active_level = DMH_CONTROL_LEVEL_HIGH,
		.idle_level = DMH_CONTROL_LEVEL_LOW,
		.has_idle_level = true,
	};
	return command;
}

static struct dmh_command open_drain_command(uint8_t channel)
{
	struct dmh_command command = {
		.kind = DMH_COMMAND_CONFIGURE_GPIO_MODE,
		.channel = channel,
	};

	command.value.configure = (struct dmh_configure_command) {
		.mode = DMH_CONTROL_MODE_OPEN_DRAIN,
		.active_level = DMH_CONTROL_LEVEL_LOW,
		.idle_level = DMH_CONTROL_LEVEL_LOW,
		.has_idle_level = false,
	};
	return command;
}

static void test_immediate_control_responses_and_lane_ownership(void)
{
	struct harness harness;
	struct dmh_command configure = push_pull_command(1U);
	struct dmh_command active = {
		.kind = DMH_COMMAND_SET_CONTROL_STATE,
		.channel = 1U,
		.value.control_state = DMH_CONTROL_STATE_ACTIVE,
	};

	harness_init(&harness);
	assert(dmh_command_executor_submit(&harness.executor, &configure, 10U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	assert(harness.gpio.count == 3U);
	assert(harness.gpio.operations[1].value == DMH_CONTROL_LEVEL_LOW);
	assert(dmh_command_executor_submit(&harness.executor, &active, 11U) ==
	       DMH_COMMAND_EXECUTOR_BUSY);
	assert(harness.gpio.count == 3U);
	consume_response(&harness, true);

	assert(dmh_command_executor_submit(&harness.executor, &active, 11U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	assert(harness.gpio.count == 6U);
	assert(harness.gpio.operations[4].value == DMH_CONTROL_LEVEL_HIGH);
	consume_response(&harness, true);
}

static void test_typed_command_errors_map_exactly(void)
{
	struct harness harness;
	struct dmh_command pulse = {
		.kind = DMH_COMMAND_PULSE_CONTROL,
		.channel = 3U,
		.value.pulse_ms = 10U,
	};
	struct dmh_command invalid = open_drain_command(0U);
	struct dmh_command unknown = {.kind = DMH_COMMAND_NONE};

	harness_init(&harness);
	assert(dmh_command_executor_submit(&harness.executor, &pulse, 1U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);

	invalid.value.configure.active_level = DMH_CONTROL_LEVEL_HIGH;
	assert(dmh_command_executor_submit(&harness.executor, &invalid, 2U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);

	assert(dmh_command_executor_submit(&harness.executor, &unknown, 3U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
	assert(harness.gpio.count == 0U && harness.uart.length == 0U);
}

static void test_ingress_rejections_use_the_owned_response_lane(void)
{
	struct harness harness;
	struct dmh_command command = push_pull_command(0U);

	harness_init(&harness);
	assert(dmh_command_executor_reject(
		&harness.executor, DMH_COMMAND_DECODE_INVALID_COMMAND
	) == DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	assert(dmh_command_executor_reject(
		&harness.executor, DMH_COMMAND_DECODE_INVALID_ARGUMENT
	) == DMH_COMMAND_EXECUTOR_BUSY);
	assert(dmh_command_executor_submit(&harness.executor, &command, 1U) ==
	       DMH_COMMAND_EXECUTOR_BUSY);
	consume_response(&harness, true);
	assert(dmh_command_executor_reject(
		&harness.executor, DMH_COMMAND_DECODE_INVALID_ARGUMENT
	) == DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
}

static void test_pulse_waits_for_idle_restore(void)
{
	struct harness harness;
	struct dmh_command configure = open_drain_command(0U);
	struct dmh_command pulse = {
		.kind = DMH_COMMAND_PULSE_CONTROL,
		.channel = 0U,
		.value.pulse_ms = 2U,
	};
	struct dmh_command other = push_pull_command(2U);

	harness_init(&harness);
	assert(dmh_command_executor_submit(&harness.executor, &configure, 10U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, false);
	assert(dmh_command_executor_submit(&harness.executor, &pulse, UINT64_MAX - 999U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	assert(dmh_command_executor_submit(&harness.executor, &other, 20U) ==
	       DMH_COMMAND_EXECUTOR_BUSY);
	assert(dmh_command_executor_poll(&harness.executor, 999U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	assert(dmh_command_executor_poll(&harness.executor, 1000U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
}

static void test_pulse_restore_fault_maps_hardware_error(void)
{
	struct harness harness;
	struct dmh_command configure = push_pull_command(2U);
	struct dmh_command pulse = {
		.kind = DMH_COMMAND_PULSE_CONTROL,
		.channel = 2U,
		.value.pulse_ms = 1U,
	};

	harness_init(&harness);
	assert(dmh_command_executor_submit(&harness.executor, &configure, 1U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, false);
	assert(dmh_command_executor_submit(&harness.executor, &pulse, 10U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	harness.gpio.fail_at = harness.gpio.count;
	assert(dmh_command_executor_poll(&harness.executor, 1010U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
}

static void test_uart_success_waits_for_physical_completion(void)
{
	struct harness harness;
	struct dmh_command command = {.kind = DMH_COMMAND_UART_SEND};

	command.value.uart_send.data[0] = 0x10U;
	command.value.uart_send.data[1] = 0x20U;
	command.value.uart_send.data[2] = 0x30U;
	command.value.uart_send.length = 3U;
	harness_init(&harness);
	harness.uart.max_write = 2U;
	assert(dmh_command_executor_submit(&harness.executor, &command, 100U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	assert(dmh_command_executor_submit(&harness.executor, &command, 100U) ==
	       DMH_COMMAND_EXECUTOR_BUSY);
	dmh_uart_tx_on_interrupt(&harness.uart_tx);
	assert(dmh_command_executor_poll(&harness.executor, 120U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	dmh_uart_tx_on_interrupt(&harness.uart_tx);
	assert(dmh_command_executor_poll(&harness.executor, 150U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	harness.uart.complete = 1;
	dmh_uart_tx_on_interrupt(&harness.uart_tx);
	assert(dmh_command_executor_poll(&harness.executor, 160U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
	assert(harness.uart.length == 3U && harness.uart.bytes[0] == 0x10U &&
	       harness.uart.bytes[1] == 0x20U && harness.uart.bytes[2] == 0x30U);
}

static void test_uart_failures_map_without_retry(void)
{
	struct harness harness;
	struct dmh_command command = {.kind = DMH_COMMAND_UART_SEND};

	command.value.uart_send.data[0] = 0xaaU;
	command.value.uart_send.data[1] = 0xbbU;
	command.value.uart_send.length = 2U;
	harness_init(&harness);
	harness.uart.max_write = 1U;
	assert(dmh_command_executor_submit(&harness.executor, &command, 100U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	dmh_uart_tx_on_interrupt(&harness.uart_tx);
	assert(dmh_command_executor_poll(&harness.executor, 200U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
	assert(harness.uart.length == 1U);

	harness.uart.length = 0U;
	assert(dmh_command_executor_submit(&harness.executor, &command, 300U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	dmh_uart_tx_on_interrupt(&harness.uart_tx);
	dmh_uart_tx_driver_fault(&harness.uart_tx);
	assert(dmh_command_executor_poll(&harness.executor, 301U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, true);
	assert(harness.uart.length == 1U);
}

static void test_epoch_cancel_discards_work_and_responses(void)
{
	struct harness harness;
	struct dmh_command configure = open_drain_command(0U);
	struct dmh_command pulse = {
		.kind = DMH_COMMAND_PULSE_CONTROL,
		.channel = 0U,
		.value.pulse_ms = 10U,
	};
	struct dmh_command unknown = {.kind = DMH_COMMAND_NONE};
	size_t response_length;

	harness_init(&harness);
	assert(dmh_command_executor_submit(&harness.executor, &configure, 1U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	consume_response(&harness, false);
	assert(dmh_command_executor_submit(&harness.executor, &pulse, 2U) ==
	       DMH_COMMAND_EXECUTOR_PENDING);
	assert(dmh_command_executor_cancel_epoch(&harness.executor) == DMH_CONTROL_OK);
	assert(dmh_command_executor_poll(&harness.executor, 10002U) ==
	       DMH_COMMAND_EXECUTOR_IDLE);
	assert(dmh_command_executor_response(&harness.executor, &response_length) == NULL);
	assert(!dmh_control_is_configured(&harness.control, 0U));

	assert(dmh_command_executor_submit(&harness.executor, &unknown, 20U) ==
	       DMH_COMMAND_EXECUTOR_RESPONSE_READY);
	assert(dmh_command_executor_cancel_epoch(&harness.executor) == DMH_CONTROL_OK);
	assert(dmh_command_executor_response(&harness.executor, &response_length) == NULL);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "control") == 0) {
		test_immediate_control_responses_and_lane_ownership();
	} else if (strcmp(argv[1], "errors") == 0) {
		test_typed_command_errors_map_exactly();
	} else if (strcmp(argv[1], "rejections") == 0) {
		test_ingress_rejections_use_the_owned_response_lane();
	} else if (strcmp(argv[1], "pulse") == 0) {
		test_pulse_waits_for_idle_restore();
	} else if (strcmp(argv[1], "pulse-fault") == 0) {
		test_pulse_restore_fault_maps_hardware_error();
	} else if (strcmp(argv[1], "uart") == 0) {
		test_uart_success_waits_for_physical_completion();
	} else if (strcmp(argv[1], "uart-failures") == 0) {
		test_uart_failures_map_without_retry();
	} else if (strcmp(argv[1], "cancel") == 0) {
		test_epoch_cancel_discards_work_and_responses();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
