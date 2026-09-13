#include "output_drain.h"

#include <errno.h>
#include <stdbool.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>

struct fake_output {
	const int *results;
	size_t result_count;
	size_t calls;
};

static int drain_one(void *context)
{
	struct fake_output *output = context;

	if (output->calls >= output->result_count) {
		return 0;
	}
	return output->results[output->calls++];
}

static void test_drains_until_idle(void)
{
	static const int results[] = {1, 1, 1, 0};
	struct fake_output output = {
		.results = results,
		.result_count = sizeof(results) / sizeof(results[0]),
	};
	struct dmh_output_drain_result result;

	if (dmh_output_drain_batch(drain_one, &output, 8U, &result) != 0 ||
	    result.drained_count != 3U || !result.idle || output.calls != 4U) {
		exit(EXIT_FAILURE);
	}
}

static void test_full_batch_keeps_draining(void)
{
	static const int results[] = {1, 1, 1, 1};
	struct fake_output output = {
		.results = results,
		.result_count = sizeof(results) / sizeof(results[0]),
	};
	struct dmh_output_drain_result result;

	if (dmh_output_drain_batch(drain_one, &output, 4U, &result) != 0 ||
	    result.drained_count != 4U || result.idle || output.calls != 4U) {
		exit(EXIT_FAILURE);
	}
}

static void test_error_stops_batch(void)
{
	static const int results[] = {1, 1, -EIO, 1};
	struct fake_output output = {
		.results = results,
		.result_count = sizeof(results) / sizeof(results[0]),
	};
	struct dmh_output_drain_result result;

	if (dmh_output_drain_batch(drain_one, &output, 8U, &result) != -EIO ||
	    result.drained_count != 2U || result.idle || output.calls != 3U) {
		exit(EXIT_FAILURE);
	}
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "drains-until-idle") == 0) {
		test_drains_until_idle();
		return EXIT_SUCCESS;
	}
	if (strcmp(argv[1], "full-batch-keeps-draining") == 0) {
		test_full_batch_keeps_draining();
		return EXIT_SUCCESS;
	}
	if (strcmp(argv[1], "error-stops-batch") == 0) {
		test_error_stops_batch();
		return EXIT_SUCCESS;
	}
	return EXIT_FAILURE;
}
