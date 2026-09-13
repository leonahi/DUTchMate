#include "output_drain.h"

#include <errno.h>

int dmh_output_drain_batch(
	dmh_output_drain_one_fn drain_one,
	void *context,
	size_t budget,
	struct dmh_output_drain_result *result
)
{
	int drain_result;

	if (drain_one == NULL || budget == 0U || result == NULL) {
		return -EINVAL;
	}
	result->drained_count = 0U;
	result->idle = false;
	while (result->drained_count < budget) {
		drain_result = drain_one(context);
		if (drain_result < 0) {
			return drain_result;
		}
		if (drain_result == 0) {
			result->idle = true;
			return 0;
		}
		result->drained_count++;
	}
	return 0;
}
