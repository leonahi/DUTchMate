#include "command_ingress.h"

#include <errno.h>
#include <string.h>

void dmh_command_ingress_reset(struct dmh_command_ingress *ingress)
{
	dmh_ndjson_framer_reset(&ingress->framer);
}

void dmh_command_ingress_init(struct dmh_command_ingress *ingress)
{
	dmh_ndjson_framer_init(&ingress->framer);
}

int dmh_command_ingress_feed(
	struct dmh_command_ingress *ingress,
	const uint8_t *input,
	size_t input_length,
	struct dmh_command_request *request,
	size_t *consumed_bytes
)
{
	struct dmh_ndjson_result frame;
	enum dmh_command_decode_failure failure;
	int result;

	if (ingress == NULL || request == NULL || consumed_bytes == NULL) {
		return -EINVAL;
	}
	(void)memset(request, 0, sizeof(*request));
	result = dmh_ndjson_framer_feed(
		&ingress->framer, input, input_length, &frame
	);
	if (result != 0) {
		return result;
	}
	*consumed_bytes = frame.consumed_bytes;
	if (frame.outcome == DMH_NDJSON_INCOMPLETE) {
		return 0;
	}
	if (frame.outcome == DMH_NDJSON_FRAME_TOO_LARGE) {
		request->kind = DMH_COMMAND_REQUEST_INVALID_ARGUMENT;
		return 0;
	}
	result = dmh_command_decode(
		frame.frame,
		frame.frame_length,
		&request->command,
		&failure
	);
	if (result == 0) {
		request->kind = DMH_COMMAND_REQUEST_COMMAND;
	} else if (failure == DMH_COMMAND_DECODE_INVALID_ARGUMENT) {
		request->kind = DMH_COMMAND_REQUEST_INVALID_ARGUMENT;
	} else {
		request->kind = DMH_COMMAND_REQUEST_INVALID_COMMAND;
	}
	return 0;
}
