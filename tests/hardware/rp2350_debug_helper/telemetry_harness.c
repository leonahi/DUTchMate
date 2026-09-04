#include "telemetry.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int encode_overflow(void)
{
	char output[DMH_TELEMETRY_FRAME_CAPACITY];
	size_t output_length;

	assert(dmh_buffer_overflow_encode(
		0U,
		182350000U,
		512U,
		output,
		sizeof(output),
		&output_length
	) == 0);
	assert(fwrite(output, 1U, output_length, stdout) == output_length);
	return EXIT_SUCCESS;
}

static int encode_status(void)
{
	const struct dmh_uart_rx_snapshot snapshot = {
		.capacity_bytes = 32768U,
		.used_bytes = 4096U,
		.high_water_bytes = 18432U,
		.dropped_bytes_total = 512U,
		.overflow_events = 1U,
	};
	char output[DMH_TELEMETRY_FRAME_CAPACITY];
	size_t output_length;

	assert(dmh_buffer_status_encode(
		182360000U,
		&snapshot,
		output,
		sizeof(output),
		&output_length
	) == 0);
	assert(fwrite(output, 1U, output_length, stdout) == output_length);
	return EXIT_SUCCESS;
}

static void test_full_width_counters(void)
{
	const struct dmh_uart_rx_snapshot snapshot = {
		.capacity_bytes = 32768U,
		.used_bytes = 32768U,
		.high_water_bytes = 32768U,
		.dropped_bytes_total = UINT64_MAX,
		.overflow_events = UINT64_MAX,
	};
	char output[DMH_TELEMETRY_FRAME_CAPACITY];
	size_t output_length;

	assert(dmh_buffer_overflow_encode(
		255U,
		UINT64_MAX,
		UINT64_MAX,
		output,
		sizeof(output),
		&output_length
	) == 0);
	assert(memmem(
		output,
		output_length,
		"18446744073709551615",
		20U
	) != NULL);
	assert(dmh_buffer_status_encode(
		UINT64_MAX,
		&snapshot,
		output,
		sizeof(output),
		&output_length
	) == 0);
	assert(output[output_length - 1U] == '\n');
}

static void test_invalid_telemetry(void)
{
	struct dmh_uart_rx_snapshot snapshot = {
		.capacity_bytes = 32768U,
		.used_bytes = 1U,
		.high_water_bytes = 1U,
	};
	char output[DMH_TELEMETRY_FRAME_CAPACITY];
	size_t output_length;

	assert(dmh_buffer_overflow_encode(
		0U, 1U, 0U, output, sizeof(output), &output_length
	) == -EINVAL);
	assert(dmh_buffer_overflow_encode(
		0U, 1U, 1U, output, 4U, &output_length
	) == -ENOSPC);
	snapshot.capacity_bytes = 0U;
	assert(dmh_buffer_status_encode(
		1U, &snapshot, output, sizeof(output), &output_length
	) == -EINVAL);
	snapshot.capacity_bytes = 32768U;
	snapshot.used_bytes = 2U;
	assert(dmh_buffer_status_encode(
		1U, &snapshot, output, sizeof(output), &output_length
	) == -EINVAL);
	snapshot.used_bytes = 1U;
	snapshot.high_water_bytes = 32769U;
	assert(dmh_buffer_status_encode(
		1U, &snapshot, output, sizeof(output), &output_length
	) == -EINVAL);
	snapshot.high_water_bytes = 1U;
	assert(dmh_buffer_status_encode(
		1U, &snapshot, output, 4U, &output_length
	) == -ENOSPC);
}

static void test_periodic_status_coalescing(void)
{
	struct dmh_telemetry_schedule schedule;
	struct dmh_buffer_status_observation first = {
		.timestamp_us = 1000000U,
		.observation_sequence = 10U,
		.snapshot = {
			.capacity_bytes = 32768U,
			.used_bytes = 5U,
			.high_water_bytes = 8U,
		},
	};
	struct dmh_buffer_status_observation newest = first;

	dmh_telemetry_schedule_init(&schedule);
	assert(!dmh_telemetry_status_due(&schedule, UINT64_MAX));
	dmh_telemetry_schedule_start(&schedule, 0U);
	assert(!dmh_telemetry_status_due(&schedule, 999999U));
	assert(dmh_telemetry_status_due(&schedule, 1000000U));
	dmh_telemetry_schedule_stage_status(&schedule, &first);
	assert(!dmh_telemetry_status_due(&schedule, 1999999U));

	newest.timestamp_us = 2000000U;
	newest.observation_sequence = 12U;
	newest.snapshot.used_bytes = 7U;
	assert(dmh_telemetry_status_due(&schedule, newest.timestamp_us));
	dmh_telemetry_schedule_stage_status(&schedule, &newest);
	assert(dmh_telemetry_pending_status(&schedule)->observation_sequence == 12U);
	assert(dmh_telemetry_pending_status(&schedule)->snapshot.used_bytes == 7U);
	dmh_telemetry_schedule_status_sent(&schedule);
	assert(dmh_telemetry_pending_status(&schedule) == NULL);

	dmh_telemetry_schedule_stage_status(&schedule, &first);
	dmh_telemetry_schedule_stop(&schedule);
	assert(dmh_telemetry_pending_status(&schedule) == NULL);
	assert(!dmh_telemetry_status_due(&schedule, UINT64_MAX));
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "overflow") == 0) {
		return encode_overflow();
	}
	if (strcmp(argv[1], "status") == 0) {
		return encode_status();
	}
	if (strcmp(argv[1], "full-width") == 0) {
		test_full_width_counters();
	} else if (strcmp(argv[1], "invalid") == 0) {
		test_invalid_telemetry();
	} else if (strcmp(argv[1], "schedule") == 0) {
		test_periodic_status_coalescing();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
