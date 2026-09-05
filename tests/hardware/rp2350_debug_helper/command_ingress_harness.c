#include "command_ingress.h"

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static void expect_none(
	struct dmh_command_ingress *ingress,
	const uint8_t *data,
	size_t length
)
{
	struct dmh_command_request request;
	size_t consumed;

	assert(dmh_command_ingress_feed(
		ingress, data, length, &request, &consumed
	) == 0);
	assert(consumed == length);
	assert(request.kind == DMH_COMMAND_REQUEST_NONE);
}

static struct dmh_command_request feed_one(
	struct dmh_command_ingress *ingress,
	const uint8_t *data,
	size_t length,
	size_t *consumed
)
{
	struct dmh_command_request request;

	assert(dmh_command_ingress_feed(
		ingress, data, length, &request, consumed
	) == 0);
	return request;
}

static void test_fragmented_frame_decodes_typed_command(void)
{
	static const uint8_t first[] =
		"{\"cmd\":\"configure_gpio_mode\",\"channel\":\"CTRL2\",";
	static const uint8_t second[] =
		"\"mode\":\"push_pull\",\"active_level\":\"high\","
		"\"idle_level\":\"low\"}\n";
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;

	dmh_command_ingress_init(&ingress);
	expect_none(&ingress, first, sizeof(first) - 1U);
	request = feed_one(&ingress, second, sizeof(second) - 1U, &consumed);
	assert(consumed == sizeof(second) - 1U);
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_CONFIGURE_GPIO_MODE);
	assert(request.command.channel == 2U);
	assert(request.command.value.configure.mode == DMH_CONTROL_MODE_PUSH_PULL);
	assert(request.command.value.configure.active_level == DMH_CONTROL_LEVEL_HIGH);
	assert(request.command.value.configure.has_idle_level);
	assert(request.command.value.configure.idle_level == DMH_CONTROL_LEVEL_LOW);
}

static void test_batch_returns_one_request_and_exact_consumption(void)
{
	static const uint8_t batch[] =
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL1\","
		"\"state\":\"active\"}\n"
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL3\","
		"\"pulse_ms\":25}\n";
	static const char first[] =
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL1\","
		"\"state\":\"active\"}\n";
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;

	dmh_command_ingress_init(&ingress);
	request = feed_one(&ingress, batch, sizeof(batch) - 1U, &consumed);
	assert(consumed == sizeof(first) - 1U);
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_SET_CONTROL_STATE);
	assert(request.command.channel == 1U);
	assert(request.command.value.control_state == DMH_CONTROL_STATE_ACTIVE);

	request = feed_one(
		&ingress,
		&batch[consumed],
		(sizeof(batch) - 1U) - consumed,
		&consumed
	);
	assert(consumed == (sizeof(batch) - 1U) - (sizeof(first) - 1U));
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_PULSE_CONTROL);
	assert(request.command.channel == 3U);
	assert(request.command.value.pulse_ms == 25U);
}

static void test_malformed_frame_maps_and_resynchronizes(void)
{
	static const uint8_t batch[] =
		"{\"cmd\":}\n"
		"{\"cmd\":\"uart_send\",\"data_b64\":\"AQI=\"}\n";
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;
	size_t offset;

	dmh_command_ingress_init(&ingress);
	request = feed_one(&ingress, batch, sizeof(batch) - 1U, &consumed);
	assert(request.kind == DMH_COMMAND_REQUEST_INVALID_COMMAND);
	offset = consumed;
	request = feed_one(
		&ingress,
		&batch[offset],
		(sizeof(batch) - 1U) - offset,
		&consumed
	);
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_UART_SEND);
	assert(request.command.value.uart_send.length == 2U);
	assert(request.command.value.uart_send.data[0] == 1U);
	assert(request.command.value.uart_send.data[1] == 2U);
}

static void test_schema_failure_maps_invalid_argument(void)
{
	static const uint8_t frame[] =
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL0\","
		"\"pulse_ms\":0}\n";
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;

	dmh_command_ingress_init(&ingress);
	request = feed_one(&ingress, frame, sizeof(frame) - 1U, &consumed);
	assert(consumed == sizeof(frame) - 1U);
	assert(request.kind == DMH_COMMAND_REQUEST_INVALID_ARGUMENT);
}

static void test_oversized_frame_maps_once_then_resynchronizes(void)
{
	static const uint8_t valid[] =
		"{\"cmd\":\"set_control_state\",\"channel\":\"CTRL0\","
		"\"state\":\"idle\"}\n";
	uint8_t input[DMH_HOST_FRAME_MAX_BYTES + sizeof(valid)];
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;
	size_t offset;

	(void)memset(input, 'x', DMH_HOST_FRAME_MAX_BYTES);
	input[DMH_HOST_FRAME_MAX_BYTES] = '\n';
	(void)memcpy(
		&input[DMH_HOST_FRAME_MAX_BYTES + 1U], valid, sizeof(valid) - 1U
	);
	dmh_command_ingress_init(&ingress);
	request = feed_one(&ingress, input, sizeof(input), &consumed);
	assert(request.kind == DMH_COMMAND_REQUEST_INVALID_ARGUMENT);
	assert(consumed == DMH_HOST_FRAME_MAX_BYTES + 1U);
	offset = consumed;
	request = feed_one(
		&ingress, &input[offset], sizeof(input) - offset, &consumed
	);
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_SET_CONTROL_STATE);
	assert(request.command.value.control_state == DMH_CONTROL_STATE_IDLE);
}

static void test_epoch_reset_discards_partial_frame(void)
{
	static const uint8_t partial[] = "{\"cmd\":\"pulse_control\",";
	static const uint8_t valid[] =
		"{\"cmd\":\"pulse_control\",\"channel\":\"CTRL0\","
		"\"pulse_ms\":1}\n";
	struct dmh_command_ingress ingress;
	struct dmh_command_request request;
	size_t consumed;

	dmh_command_ingress_init(&ingress);
	expect_none(&ingress, partial, sizeof(partial) - 1U);
	dmh_command_ingress_reset(&ingress);
	request = feed_one(&ingress, valid, sizeof(valid) - 1U, &consumed);
	assert(request.kind == DMH_COMMAND_REQUEST_COMMAND);
	assert(request.command.kind == DMH_COMMAND_PULSE_CONTROL);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "fragmented") == 0) {
		test_fragmented_frame_decodes_typed_command();
	} else if (strcmp(argv[1], "batch") == 0) {
		test_batch_returns_one_request_and_exact_consumption();
	} else if (strcmp(argv[1], "malformed") == 0) {
		test_malformed_frame_maps_and_resynchronizes();
	} else if (strcmp(argv[1], "arguments") == 0) {
		test_schema_failure_maps_invalid_argument();
	} else if (strcmp(argv[1], "oversize") == 0) {
		test_oversized_frame_maps_once_then_resynchronizes();
	} else if (strcmp(argv[1], "reset") == 0) {
		test_epoch_reset_discards_partial_frame();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
