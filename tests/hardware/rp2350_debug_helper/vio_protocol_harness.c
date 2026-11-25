#include "command_decode.h"
#include "command_executor.h"
#include "telemetry.h"
#include "hello.h"

#include <assert.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>

static int prepare(void *context, bool enabled)
{
	(void)enabled;
	return *(int *)context;
}

static int enable(void *context, uint8_t channel, bool value)
{
	(void)context; (void)channel; (void)value;
	return 0;
}

static int data(void *context, uint8_t channel, enum dmh_control_level value)
{
	(void)context; (void)channel; (void)value;
	return 0;
}

static void cancel(void *context) { (void)context; }

int main(int argc, char **argv)
{
	assert(argc == 2);
	if (!strcmp(argv[1], "hello")) {
		char firmware[65];
		char frame[DMH_HELLO_FRAME_CAPACITY];
		size_t length;
		memset(firmware, 'f', 64);
		firmware[64] = '\0';
		assert(dmh_hello_encode(firmware, frame, sizeof(frame), &length) == 0);
		fwrite(frame, 1, length, stdout);
		return 0;
	}
	if (!strcmp(argv[1], "decode")) {
		struct dmh_command command;
		enum dmh_command_decode_failure failure;
		const char *valid[] = {"{\"cmd\":\"configure_power_sense\",\"enabled\":true}",
			"{\"enabled\":false,\"cmd\":\"configure_power_sense\"}"};
		for (unsigned int i = 0; i < 2; i++) {
			assert(dmh_command_decode((const uint8_t *)valid[i], strlen(valid[i]), &command, &failure) == 0);
			assert(command.kind == DMH_COMMAND_CONFIGURE_POWER_SENSE);
			assert(command.value.sense_enabled == (i == 0));
		}
		const char *bad[] = {"{\"cmd\":\"configure_power_sense\",\"enabled\":1}",
			"{\"cmd\":\"configure_power_sense\",\"enabled\":\"true\"}",
			"{\"cmd\":\"configure_power_sense\"}",
			"{\"cmd\":\"configure_power_sense\",\"enabled\":true,\"enabled\":false}",
			"{\"cmd\":\"configure_power_sense\",\"enabled\":true,\"channel\":\"CTRL0\"}"};
		for (unsigned int i = 0; i < sizeof(bad)/sizeof(bad[0]); i++) {
			assert(dmh_command_decode((const uint8_t *)bad[i], strlen(bad[i]), &command, &failure) != 0);
			assert(command.kind == DMH_COMMAND_NONE);
		}
		return 0;
	}
	if (!strncmp(argv[1], "ack", 3) || !strcmp(argv[1], "cancel")) {
		struct dmh_command_executor executor;
		struct dmh_control control = {0};
		struct dmh_command_uart_port uart = {.cancel = cancel};
		struct dmh_control_port pins = {.set_enable = enable, .set_data = data};
		dmh_control_init(&control, &pins);
		int error = !strcmp(argv[1], "ack-error") ? -EIO : 0;
		struct dmh_command_vio_port vio = {.context = &error, .prepare = prepare};
		struct dmh_command command = {.kind = DMH_COMMAND_CONFIGURE_POWER_SENSE, .value.sense_enabled = true};
		bool enabled;
		size_t length;
		dmh_command_executor_init(&executor, &control, &uart, &vio);
		assert(dmh_command_executor_submit(&executor, &command, 100) == DMH_COMMAND_EXECUTOR_RESPONSE_READY);
		assert(!dmh_command_executor_take_sense_configuration(&executor, &enabled));
		/* The USB owner can snapshot immutable intent before waking the worker. */
		assert(dmh_command_executor_response_sense_configuration(&executor, &enabled) == (error == 0));
		if (!error) assert(enabled);
		if (!strcmp(argv[1], "cancel")) {
			assert(dmh_command_executor_cancel_epoch(&executor) == DMH_CONTROL_OK);
			assert(!dmh_command_executor_take_sense_configuration(&executor, &enabled));
			return 0;
		}
		const char *response = dmh_command_executor_response(&executor, &length);
		assert(response != NULL);
		fwrite(response, 1, length, stdout);
		dmh_command_executor_response_sent(&executor);
		assert(dmh_command_executor_take_sense_configuration(&executor, &enabled) == (error == 0));
		if (!error) assert(enabled);
		assert(!dmh_command_executor_take_sense_configuration(&executor, &enabled));
		return 0;
	}
	struct dmh_vio_observation observation = {.timestamp_us = 1234567, .status = DMH_VIO_OK,
		.adc_raw = 3072, .voltage_mv = 4950, .reference_mv = 3300};
	if (!strcmp(argv[1], "adc-error")) observation.status = DMH_VIO_ERROR;
	if (!strcmp(argv[1], "saturated")) { observation.status = DMH_VIO_SATURATED; observation.adc_raw = 4095; }
	char output[256];
	size_t length;
	assert(dmh_dut_vio_encode(&observation, output, sizeof(output), &length) == 0);
	fwrite(output, 1, length, stdout);
	memset(output, '#', sizeof(output));
	assert(dmh_dut_vio_encode(&observation, output, 1, &length) == -ENOSPC);
	assert(output[1] == '#');
	return 0;
}
