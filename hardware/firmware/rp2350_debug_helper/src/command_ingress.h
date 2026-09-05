#ifndef DUTCHMATE_COMMAND_INGRESS_H
#define DUTCHMATE_COMMAND_INGRESS_H

#include "command_decode.h"
#include "ndjson_framer.h"

#include <stddef.h>
#include <stdint.h>

enum dmh_command_request_kind {
	DMH_COMMAND_REQUEST_NONE = 0,
	DMH_COMMAND_REQUEST_COMMAND,
	DMH_COMMAND_REQUEST_INVALID_COMMAND,
	DMH_COMMAND_REQUEST_INVALID_ARGUMENT,
};

struct dmh_command_request {
	enum dmh_command_request_kind kind;
	struct dmh_command command;
};

struct dmh_command_ingress {
	struct dmh_ndjson_framer framer;
};

void dmh_command_ingress_init(struct dmh_command_ingress *ingress);
void dmh_command_ingress_reset(struct dmh_command_ingress *ingress);
int dmh_command_ingress_feed(
	struct dmh_command_ingress *ingress,
	const uint8_t *input,
	size_t input_length,
	struct dmh_command_request *request,
	size_t *consumed_bytes
);

#endif
