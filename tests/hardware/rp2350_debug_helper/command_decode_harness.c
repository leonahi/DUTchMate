#include "command_decode.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static void decode_ok(const char *frame, struct dmh_command *command)
{
	enum dmh_command_decode_failure failure;

	assert(dmh_command_decode(
		(const uint8_t *)frame, strlen(frame), command, &failure
	) == 0);
}

static void expect_failure(
	const char *frame,
	enum dmh_command_decode_failure expected
)
{
	struct dmh_command command;
	enum dmh_command_decode_failure failure;

	memset(&command, 0xA5, sizeof(command));
	assert(dmh_command_decode(
		(const uint8_t *)frame, strlen(frame), &command, &failure
	) == -EINVAL);
	if (failure != expected) {
		fprintf(
			stderr,
			"wrong failure for %s: got %d expected %d\n",
			frame,
			(int)failure,
			(int)expected
		);
	}
	assert(failure == expected);
	assert(command.kind == DMH_COMMAND_NONE);
}

static void test_configure_commands(void)
{
	struct dmh_command command;

	decode_ok(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL0\","
		"\"mode\":\"open_drain\",\"active_level\":\"low\"}",
		&command
	);
	assert(command.kind == DMH_COMMAND_CONFIGURE_GPIO_MODE);
	assert(command.channel == 0U);
	assert(command.value.configure.mode == DMH_CONTROL_MODE_OPEN_DRAIN);
	assert(command.value.configure.active_level == DMH_CONTROL_LEVEL_LOW);
	assert(!command.value.configure.has_idle_level);

	decode_ok(
		"{ \"idle_level\" : \"low\", \"active_level\" : \"high\","
		" \"mode\" : \"push_pull\", \"channel\" : \"CTRL\\u0033\","
		" \"cmd\" : \"configure_gpio_mode\" }",
		&command
	);
	assert(command.kind == DMH_COMMAND_CONFIGURE_GPIO_MODE);
	assert(command.channel == 3U);
	assert(command.value.configure.mode == DMH_CONTROL_MODE_PUSH_PULL);
	assert(command.value.configure.active_level == DMH_CONTROL_LEVEL_HIGH);
	assert(command.value.configure.has_idle_level);
	assert(command.value.configure.idle_level == DMH_CONTROL_LEVEL_LOW);
}

static void test_control_action_commands(void)
{
	struct dmh_command command;

	decode_ok(
		"{\"pulse_ms\":1,\"channel\":\"CTRL1\",\"cmd\":\"pulse_control\"}",
		&command
	);
	assert(command.kind == DMH_COMMAND_PULSE_CONTROL);
	assert(command.channel == 1U);
	assert(command.value.pulse_ms == 1U);
	decode_ok(
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL2\","
		"\"pulse_ms\":10000}",
		&command
	);
	assert(command.value.pulse_ms == 10000U);

	decode_ok(
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL2\","
		"\"state\":\"active\"}",
		&command
	);
	assert(command.kind == DMH_COMMAND_SET_CONTROL_STATE);
	assert(command.channel == 2U);
	assert(command.value.control_state == DMH_CONTROL_STATE_ACTIVE);
	decode_ok(
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL0\","
		"\"state\":\"idle\"}",
		&command
	);
	assert(command.value.control_state == DMH_CONTROL_STATE_IDLE);
}

static void test_uart_send_commands(void)
{
	static const char prefix[] = "{\"cmd\":\"uart_send\",\"data_b64\":\"";
	struct dmh_command command;
	char maximum[1500];
	size_t index;
	size_t prefix_length = sizeof(prefix) - 1U;

	decode_ok("{\"cmd\":\"uart_send\",\"data_b64\":\"AP7\\/\"}", &command);
	assert(command.kind == DMH_COMMAND_UART_SEND);
	assert(command.value.uart_send.length == 3U);
	assert(command.value.uart_send.data[0] == 0x00U);
	assert(command.value.uart_send.data[1] == 0xFEU);
	assert(command.value.uart_send.data[2] == 0xFFU);

	memcpy(maximum, prefix, prefix_length);
	for (index = prefix_length; index < prefix_length + 1366U; index++) {
		maximum[index] = 'A';
	}
	maximum[index++] = '=';
	maximum[index++] = '=';
	maximum[index++] = '"';
	maximum[index++] = '}';
	maximum[index] = '\0';
	decode_ok(maximum, &command);
	assert(command.kind == DMH_COMMAND_UART_SEND);
	assert(command.value.uart_send.length == 1024U);
}

static void test_invalid_command_envelopes(void)
{
	expect_failure("", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure("[]", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure(" {}", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure("{}", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure("{\"cmd\":", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure("{\"cmd\":7}", DMH_COMMAND_DECODE_INVALID_COMMAND);
	expect_failure(
		"{\"cmd\":\"unknown\"}", DMH_COMMAND_DECODE_INVALID_COMMAND
	);
	expect_failure(
		"{\"cmd\":\"uart_send\"}\r", DMH_COMMAND_DECODE_INVALID_COMMAND
	);
}

static void test_invalid_control_arguments(void)
{
	expect_failure(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL4\","
		"\"mode\":\"open_drain\",\"active_level\":\"low\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL0\","
		"\"mode\":\"open_drain\",\"active_level\":\"high\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL0\","
		"\"mode\":\"open_drain\",\"active_level\":\"low\","
		"\"idle_level\":\"high\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL0\","
		"\"mode\":\"push_pull\",\"active_level\":\"low\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL0\","
		"\"mode\":\"push_pull\",\"active_level\":\"low\","
		"\"idle_level\":\"low\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL0\",\"pulse_ms\":0}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL0\","
		"\"pulse_ms\":10001}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL0\",\"pulse_ms\":01}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL0\","
		"\"state\":\"held\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
}

static void test_invalid_shape_and_uart_arguments(void)
{
	static const char prefix[] = "{\"cmd\":\"uart_send\",\"data_b64\":\"";
	char oversized[1500];
	size_t index;
	size_t prefix_length = sizeof(prefix) - 1U;

	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":\"\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":\"AAA=AAAA\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":7}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":\"AA==\",\"extra\":true}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"cmd\":\"uart_send\",\"data_b64\":\"AA==\"}",
		DMH_COMMAND_DECODE_INVALID_ARGUMENT
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":\"AA==\",}",
		DMH_COMMAND_DECODE_INVALID_COMMAND
	);
	expect_failure(
		"{\"cmd\":\"uart_send\",\"data_b64\":\"AA==\"}x",
		DMH_COMMAND_DECODE_INVALID_COMMAND
	);

	memcpy(oversized, prefix, prefix_length);
	for (index = prefix_length; index < prefix_length + 1367U; index++) {
		oversized[index] = 'A';
	}
	oversized[index++] = '=';
	oversized[index++] = '"';
	oversized[index++] = '}';
	oversized[index] = '\0';
	expect_failure(oversized, DMH_COMMAND_DECODE_INVALID_ARGUMENT);
}

static void test_invalid_api_arguments(void)
{
	static const uint8_t frame[] = "{}";
	struct dmh_command command;
	enum dmh_command_decode_failure failure;

	assert(dmh_command_decode(NULL, 1U, &command, &failure) == -EINVAL);
	assert(dmh_command_decode(frame, sizeof(frame) - 1U, NULL, &failure) == -EINVAL);
	assert(dmh_command_decode(frame, sizeof(frame) - 1U, &command, NULL) == -EINVAL);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "configure") == 0) {
		test_configure_commands();
	} else if (strcmp(argv[1], "actions") == 0) {
		test_control_action_commands();
	} else if (strcmp(argv[1], "uart") == 0) {
		test_uart_send_commands();
	} else if (strcmp(argv[1], "invalid-command") == 0) {
		test_invalid_command_envelopes();
	} else if (strcmp(argv[1], "invalid-control") == 0) {
		test_invalid_control_arguments();
	} else if (strcmp(argv[1], "invalid-uart") == 0) {
		test_invalid_shape_and_uart_arguments();
	} else if (strcmp(argv[1], "invalid-api") == 0) {
		test_invalid_api_arguments();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
