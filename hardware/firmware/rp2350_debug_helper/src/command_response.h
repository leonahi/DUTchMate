#ifndef DUTCHMATE_COMMAND_RESPONSE_H
#define DUTCHMATE_COMMAND_RESPONSE_H

#include <stddef.h>
#include <stdint.h>

#define DMH_COMMAND_RESPONSE_FRAME_CAPACITY 640U
#define DMH_COMMAND_ERROR_DETAIL_MAX_BYTES 256U

enum dmh_command_error_code {
	DMH_COMMAND_ERROR_INVALID_COMMAND = 0,
	DMH_COMMAND_ERROR_INVALID_ARGUMENT,
	DMH_COMMAND_ERROR_NOT_CONFIGURED,
	DMH_COMMAND_ERROR_CAPTURE_ACTIVE,
	DMH_COMMAND_ERROR_HARDWARE_FAULT,
	DMH_COMMAND_ERROR_TIMEOUT,
};

int dmh_success_response_encode(
	char *output,
	size_t output_capacity,
	size_t *output_length
);
int dmh_timestamp_response_encode(
	uint64_t timestamp_us,
	char *output,
	size_t output_capacity,
	size_t *output_length
);
int dmh_uart_send_response_encode(
	uint64_t timestamp_us,
	size_t bytes_accepted,
	char *output,
	size_t output_capacity,
	size_t *output_length
);
int dmh_error_response_encode(
	enum dmh_command_error_code code,
	const char *detail,
	size_t detail_length,
	char *output,
	size_t output_capacity,
	size_t *output_length
);

#endif
