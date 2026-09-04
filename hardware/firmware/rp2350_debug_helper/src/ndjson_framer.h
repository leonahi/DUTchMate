#ifndef DUTCHMATE_NDJSON_FRAMER_H
#define DUTCHMATE_NDJSON_FRAMER_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DMH_HOST_FRAME_MAX_BYTES 2048U
#define DMH_HOST_FRAME_MAX_PENDING_BYTES (DMH_HOST_FRAME_MAX_BYTES - 1U)

enum dmh_ndjson_outcome {
	DMH_NDJSON_INCOMPLETE = 0,
	DMH_NDJSON_FRAME_READY,
	DMH_NDJSON_FRAME_TOO_LARGE,
};

struct dmh_ndjson_result {
	enum dmh_ndjson_outcome outcome;
	const uint8_t *frame;
	size_t frame_length;
	size_t consumed_bytes;
};

struct dmh_ndjson_framer {
	uint8_t pending[DMH_HOST_FRAME_MAX_PENDING_BYTES];
	size_t pending_length;
	bool discarding_oversize;
};

void dmh_ndjson_framer_init(struct dmh_ndjson_framer *framer);
void dmh_ndjson_framer_reset(struct dmh_ndjson_framer *framer);
/*
 * At most one outcome is returned. consumed_bytes identifies any unconsumed
 * suffix for the caller's next feed. A ready frame remains valid until that
 * next feed or reset.
 */
int dmh_ndjson_framer_feed(
	struct dmh_ndjson_framer *framer,
	const uint8_t *input,
	size_t input_length,
	struct dmh_ndjson_result *result
);

#endif
