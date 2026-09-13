#ifndef DUTCHMATE_OUTPUT_DRAIN_H
#define DUTCHMATE_OUTPUT_DRAIN_H

#include <stdbool.h>
#include <stddef.h>

typedef int (*dmh_output_drain_one_fn)(void *context);

struct dmh_output_drain_result {
	size_t drained_count;
	bool idle;
};

int dmh_output_drain_batch(
	dmh_output_drain_one_fn drain_one,
	void *context,
	size_t budget,
	struct dmh_output_drain_result *result
);

#endif
