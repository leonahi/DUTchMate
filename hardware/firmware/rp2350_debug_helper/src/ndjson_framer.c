#include "ndjson_framer.h"

#include <errno.h>
#include <string.h>

void dmh_ndjson_framer_reset(struct dmh_ndjson_framer *framer)
{
	framer->pending_length = 0U;
	framer->discarding_oversize = false;
}

void dmh_ndjson_framer_init(struct dmh_ndjson_framer *framer)
{
	dmh_ndjson_framer_reset(framer);
}

int dmh_ndjson_framer_feed(
	struct dmh_ndjson_framer *framer,
	const uint8_t *input,
	size_t input_length,
	struct dmh_ndjson_result *result
)
{
	size_t index;

	if (framer == NULL || (input == NULL && input_length > 0U) ||
	    result == NULL) {
		return -EINVAL;
	}
	memset(result, 0, sizeof(*result));
	for (index = 0U; index < input_length; index++) {
		uint8_t byte = input[index];

		if (framer->discarding_oversize) {
			if (byte == '\n') {
				dmh_ndjson_framer_reset(framer);
				result->outcome = DMH_NDJSON_FRAME_TOO_LARGE;
				result->consumed_bytes = index + 1U;
				return 0;
			}
			continue;
		}
		if (byte == '\n') {
			result->outcome = DMH_NDJSON_FRAME_READY;
			result->frame = framer->pending;
			result->frame_length = framer->pending_length;
			if (result->frame_length > 0U &&
			    result->frame[result->frame_length - 1U] == '\r') {
				result->frame_length--;
			}
			result->consumed_bytes = index + 1U;
			framer->pending_length = 0U;
			return 0;
		}
		if (framer->pending_length == DMH_HOST_FRAME_MAX_PENDING_BYTES) {
			framer->pending_length = 0U;
			framer->discarding_oversize = true;
			continue;
		}
		framer->pending[framer->pending_length] = byte;
		framer->pending_length++;
	}
	result->consumed_bytes = input_length;
	return 0;
}
