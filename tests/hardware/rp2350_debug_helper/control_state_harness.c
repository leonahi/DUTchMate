#include "control_state.h"

#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_OPERATIONS 64U

enum operation_kind {
	OP_ENABLE = 0,
	OP_DATA,
};

struct operation {
	enum operation_kind kind;
	uint8_t channel;
	int value;
};

struct fake_gpio {
	struct operation operations[MAX_OPERATIONS];
	size_t operation_count;
	size_t fail_at;
};

static int record_operation(
	struct fake_gpio *gpio,
	enum operation_kind kind,
	uint8_t channel,
	int value
)
{
	size_t index = gpio->operation_count;

	if (index >= MAX_OPERATIONS) {
		return -1;
	}
	gpio->operations[index] = (struct operation) {
		.kind = kind,
		.channel = channel,
		.value = value,
	};
	gpio->operation_count++;
	return index == gpio->fail_at ? -1 : 0;
}

static int set_enable(void *context, uint8_t channel, bool enabled)
{
	return record_operation(context, OP_ENABLE, channel, enabled ? 1 : 0);
}

static int set_data(void *context, uint8_t channel, enum dmh_control_level level)
{
	return record_operation(context, OP_DATA, channel, (int)level);
}

static struct dmh_control_port make_port(struct fake_gpio *gpio)
{
	return (struct dmh_control_port) {
		.context = gpio,
		.set_enable = set_enable,
		.set_data = set_data,
	};
}

static void expect_operation(
	const struct fake_gpio *gpio,
	size_t index,
	enum operation_kind kind,
	uint8_t channel,
	int value
)
{
	if (index >= gpio->operation_count || gpio->operations[index].kind != kind ||
	    gpio->operations[index].channel != channel ||
	    gpio->operations[index].value != value) {
		(void)fprintf(stderr, "unexpected operation at %zu\n", index);
		exit(EXIT_FAILURE);
	}
}

static void expect_result(enum dmh_control_result actual, enum dmh_control_result expected)
{
	if (actual != expected) {
		(void)fprintf(stderr, "result %d, expected %d\n", actual, expected);
		exit(EXIT_FAILURE);
	}
}

static void test_configuration_and_state_application(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			0U,
			DMH_CONTROL_MODE_OPEN_DRAIN,
			DMH_CONTROL_LEVEL_LOW,
			false,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_OK
	);
	if (!dmh_control_is_configured(&controller, 0U) || gpio.operation_count != 2U) {
		exit(EXIT_FAILURE);
	}
	expect_operation(&gpio, 0U, OP_ENABLE, 0U, 0);
	expect_operation(&gpio, 1U, OP_DATA, 0U, DMH_CONTROL_LEVEL_LOW);

	expect_result(
		dmh_control_set_state(&controller, 0U, DMH_CONTROL_STATE_ACTIVE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 2U, OP_ENABLE, 0U, 0);
	expect_operation(&gpio, 3U, OP_DATA, 0U, DMH_CONTROL_LEVEL_LOW);
	expect_operation(&gpio, 4U, OP_ENABLE, 0U, 1);

	expect_result(
		dmh_control_set_state(&controller, 0U, DMH_CONTROL_STATE_IDLE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 5U, OP_ENABLE, 0U, 0);
	expect_operation(&gpio, 6U, OP_DATA, 0U, DMH_CONTROL_LEVEL_LOW);

	expect_result(
		dmh_control_configure(
			&controller,
			3U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_HIGH,
			true,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 7U, OP_ENABLE, 3U, 0);
	expect_operation(&gpio, 8U, OP_DATA, 3U, DMH_CONTROL_LEVEL_LOW);
	expect_operation(&gpio, 9U, OP_ENABLE, 3U, 1);

	expect_result(
		dmh_control_set_state(&controller, 3U, DMH_CONTROL_STATE_ACTIVE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 10U, OP_ENABLE, 3U, 0);
	expect_operation(&gpio, 11U, OP_DATA, 3U, DMH_CONTROL_LEVEL_HIGH);
	expect_operation(&gpio, 12U, OP_ENABLE, 3U, 1);
}

static void test_invalid_configuration_has_no_side_effect(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			0U,
			DMH_CONTROL_MODE_OPEN_DRAIN,
			DMH_CONTROL_LEVEL_HIGH,
			false,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_INVALID_ARGUMENT
	);
	expect_result(
		dmh_control_configure(
			&controller,
			1U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			false,
			DMH_CONTROL_LEVEL_HIGH
		),
		DMH_CONTROL_INVALID_ARGUMENT
	);
	expect_result(
		dmh_control_configure(
			&controller,
			4U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			true,
			DMH_CONTROL_LEVEL_HIGH
		),
		DMH_CONTROL_INVALID_ARGUMENT
	);
	expect_result(
		dmh_control_set_state(&controller, 2U, DMH_CONTROL_STATE_ACTIVE),
		DMH_CONTROL_NOT_CONFIGURED
	);
	if (gpio.operation_count != 0U || dmh_control_is_configured(&controller, 0U)) {
		exit(EXIT_FAILURE);
	}
}

static void test_invalid_reconfiguration_preserves_accepted_state(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			1U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			true,
			DMH_CONTROL_LEVEL_HIGH
		),
		DMH_CONTROL_OK
	);
	expect_result(
		dmh_control_configure(
			&controller,
			1U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			true,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_INVALID_ARGUMENT
	);
	if (gpio.operation_count != 3U || !dmh_control_is_configured(&controller, 1U)) {
		exit(EXIT_FAILURE);
	}
	expect_result(
		dmh_control_set_state(&controller, 1U, DMH_CONTROL_STATE_ACTIVE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 4U, OP_DATA, 1U, DMH_CONTROL_LEVEL_LOW);
}

static void test_pulse_deadline_and_timer_wrap(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			2U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_HIGH,
			true,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_OK
	);
	expect_result(
		dmh_control_pulse_start(&controller, 2U, 2U, UINT64_MAX - 999U),
		DMH_CONTROL_PENDING
	);
	if (dmh_control_poll(&controller, 999U) != DMH_CONTROL_POLL_NONE) {
		exit(EXIT_FAILURE);
	}
	if (dmh_control_poll(&controller, 1000U) != DMH_CONTROL_POLL_COMPLETED) {
		exit(EXIT_FAILURE);
	}
	expect_operation(&gpio, 6U, OP_ENABLE, 2U, 0);
	expect_operation(&gpio, 7U, OP_DATA, 2U, DMH_CONTROL_LEVEL_LOW);
	expect_operation(&gpio, 8U, OP_ENABLE, 2U, 1);
	if (dmh_control_poll(&controller, 1001U) != DMH_CONTROL_POLL_NONE) {
		exit(EXIT_FAILURE);
	}

	expect_result(
		dmh_control_pulse_start(&controller, 2U, 0U, 0U),
		DMH_CONTROL_INVALID_ARGUMENT
	);
	expect_result(
		dmh_control_pulse_start(&controller, 2U, 10001U, 0U),
		DMH_CONTROL_INVALID_ARGUMENT
	);
}

static void test_disconnect_cancels_and_discards(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);
	uint8_t channel;

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			0U,
			DMH_CONTROL_MODE_OPEN_DRAIN,
			DMH_CONTROL_LEVEL_LOW,
			false,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_OK
	);
	expect_result(
		dmh_control_pulse_start(&controller, 0U, 100U, 500U),
		DMH_CONTROL_PENDING
	);
	expect_result(dmh_control_end_epoch(&controller), DMH_CONTROL_OK);
	if (dmh_control_poll(&controller, 100500U) != DMH_CONTROL_POLL_NONE) {
		exit(EXIT_FAILURE);
	}
	for (channel = 0U; channel < DMH_CONTROL_CHANNEL_COUNT; channel++) {
		if (dmh_control_is_configured(&controller, channel)) {
			exit(EXIT_FAILURE);
		}
		expect_operation(&gpio, 5U + (2U * channel), OP_ENABLE, channel, 0);
		expect_operation(
			&gpio,
			6U + (2U * channel),
			OP_DATA,
			channel,
			DMH_CONTROL_LEVEL_LOW
		);
	}
	expect_result(
		dmh_control_set_state(&controller, 0U, DMH_CONTROL_STATE_ACTIVE),
		DMH_CONTROL_NOT_CONFIGURED
	);
}

static void test_recoverable_fault_retains_configuration(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			3U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			true,
			DMH_CONTROL_LEVEL_HIGH
		),
		DMH_CONTROL_OK
	);
	expect_result(dmh_control_force_channel_safe(&controller, 3U), DMH_CONTROL_OK);
	if (!dmh_control_is_configured(&controller, 3U)) {
		exit(EXIT_FAILURE);
	}
	expect_result(
		dmh_control_set_state(&controller, 3U, DMH_CONTROL_STATE_IDLE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 5U, OP_ENABLE, 3U, 0);
	expect_operation(&gpio, 6U, OP_DATA, 3U, DMH_CONTROL_LEVEL_HIGH);
	expect_operation(&gpio, 7U, OP_ENABLE, 3U, 1);
}

static void test_hardware_failures_fall_back_safe(void)
{
	struct fake_gpio gpio = {.fail_at = 2U};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			0U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_HIGH,
			true,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_HARDWARE_FAULT
	);
	if (dmh_control_is_configured(&controller, 0U) || gpio.operation_count != 4U) {
		exit(EXIT_FAILURE);
	}
	expect_operation(&gpio, 0U, OP_ENABLE, 0U, 0);
	expect_operation(&gpio, 1U, OP_DATA, 0U, DMH_CONTROL_LEVEL_LOW);
	expect_operation(&gpio, 2U, OP_ENABLE, 0U, 1);
	expect_operation(&gpio, 3U, OP_ENABLE, 0U, 0);
}

static void test_failed_reconfiguration_keeps_previous_mapping(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			1U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_LOW,
			true,
			DMH_CONTROL_LEVEL_HIGH
		),
		DMH_CONTROL_OK
	);
	gpio.fail_at = 5U;
	expect_result(
		dmh_control_configure(
			&controller,
			1U,
			DMH_CONTROL_MODE_PUSH_PULL,
			DMH_CONTROL_LEVEL_HIGH,
			true,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_HARDWARE_FAULT
	);
	if (!dmh_control_is_configured(&controller, 1U)) {
		exit(EXIT_FAILURE);
	}
	gpio.fail_at = SIZE_MAX;
	expect_result(
		dmh_control_set_state(&controller, 1U, DMH_CONTROL_STATE_IDLE),
		DMH_CONTROL_OK
	);
	expect_operation(&gpio, 8U, OP_DATA, 1U, DMH_CONTROL_LEVEL_HIGH);
}

static void test_pulse_restore_failure_never_completes_successfully(void)
{
	struct fake_gpio gpio = {.fail_at = SIZE_MAX};
	struct dmh_control controller;
	struct dmh_control_port port = make_port(&gpio);

	dmh_control_init(&controller, &port);
	expect_result(
		dmh_control_configure(
			&controller,
			2U,
			DMH_CONTROL_MODE_OPEN_DRAIN,
			DMH_CONTROL_LEVEL_LOW,
			false,
			DMH_CONTROL_LEVEL_LOW
		),
		DMH_CONTROL_OK
	);
	expect_result(
		dmh_control_pulse_start(&controller, 2U, 1U, 100U),
		DMH_CONTROL_PENDING
	);
	gpio.fail_at = 5U;
	if (dmh_control_poll(&controller, 1100U) != DMH_CONTROL_POLL_HARDWARE_FAULT) {
		exit(EXIT_FAILURE);
	}
	if (dmh_control_poll(&controller, 1101U) != DMH_CONTROL_POLL_NONE ||
	    !dmh_control_is_configured(&controller, 2U)) {
		exit(EXIT_FAILURE);
	}
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "configuration") == 0) {
		test_configuration_and_state_application();
	} else if (strcmp(argv[1], "invalid") == 0) {
		test_invalid_configuration_has_no_side_effect();
	} else if (strcmp(argv[1], "reconfigure") == 0) {
		test_invalid_reconfiguration_preserves_accepted_state();
	} else if (strcmp(argv[1], "pulse") == 0) {
		test_pulse_deadline_and_timer_wrap();
	} else if (strcmp(argv[1], "disconnect") == 0) {
		test_disconnect_cancels_and_discards();
	} else if (strcmp(argv[1], "fault") == 0) {
		test_recoverable_fault_retains_configuration();
	} else if (strcmp(argv[1], "hardware-failure") == 0) {
		test_hardware_failures_fall_back_safe();
	} else if (strcmp(argv[1], "reconfiguration-failure") == 0) {
		test_failed_reconfiguration_keeps_previous_mapping();
	} else if (strcmp(argv[1], "pulse-failure") == 0) {
		test_pulse_restore_failure_never_completes_successfully();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
