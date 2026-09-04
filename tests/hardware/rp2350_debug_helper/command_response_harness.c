#include "command_response.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static char output[DMH_COMMAND_RESPONSE_FRAME_CAPACITY];

static int write_result(int result, size_t output_length)
{
	assert(result == 0);
	assert(fwrite(output, 1U, output_length, stdout) == output_length);
	return EXIT_SUCCESS;
}

static int encode_success(void)
{
	size_t output_length;
	int result;

	result = dmh_success_response_encode(output, sizeof(output), &output_length);
	return write_result(result, output_length);
}

static int encode_timestamp(void)
{
	size_t output_length;
	int result;

	result = dmh_timestamp_response_encode(
		182334400U, output, sizeof(output), &output_length
	);
	return write_result(result, output_length);
}

static int encode_uart_send(void)
{
	size_t output_length;
	int result;

	result = dmh_uart_send_response_encode(
		UINT64_MAX, 1024U, output, sizeof(output), &output_length
	);
	return write_result(result, output_length);
}

static int encode_error(void)
{
	static const char detail[] = "CTRL0 is not configured";
	size_t output_length;
	int result;

	result = dmh_error_response_encode(
		DMH_COMMAND_ERROR_NOT_CONFIGURED,
		detail,
		sizeof(detail) - 1U,
		output,
		sizeof(output),
		&output_length
	);
	return write_result(result, output_length);
}

static int encode_escaped_error(void)
{
	static const char detail[] = "DUT é said \"no\\retry\"";
	size_t output_length;
	int result;

	result = dmh_error_response_encode(
		DMH_COMMAND_ERROR_HARDWARE_FAULT,
		detail,
		sizeof(detail) - 1U,
		output,
		sizeof(output),
		&output_length
	);
	return write_result(result, output_length);
}

static void test_invalid_bounds(void)
{
	static const char valid_detail[] = "bad command";
	static const char control_detail[] = "bad\x1F" "command";
	static const char invalid_utf8[] = "bad\xC0\xAF";
	static const char invalid_e0[] = {'x', (char)0xE0, (char)0xFF, (char)0x80};
	static const char invalid_ed[] = {'x', (char)0xED, (char)0x20, (char)0x80};
	static const char invalid_f0[] = {
		'x', (char)0xF0, (char)0xFF, (char)0x80, (char)0x80
	};
	char long_detail[257];
	size_t output_length;

	memset(long_detail, 'x', sizeof(long_detail));
	assert(dmh_uart_send_response_encode(
		1U, 1025U, output, sizeof(output), &output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_COMMAND,
		"",
		0U,
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		long_detail,
		sizeof(long_detail),
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		control_detail,
		sizeof(control_detail) - 1U,
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		invalid_utf8,
		sizeof(invalid_utf8) - 1U,
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		invalid_e0,
		sizeof(invalid_e0),
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		invalid_ed,
		sizeof(invalid_ed),
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_ARGUMENT,
		invalid_f0,
		sizeof(invalid_f0),
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		(enum dmh_command_error_code)99,
		valid_detail,
		sizeof(valid_detail) - 1U,
		output,
		sizeof(output),
		&output_length
	) == -EINVAL);
	assert(dmh_error_response_encode(
		DMH_COMMAND_ERROR_INVALID_COMMAND,
		valid_detail,
		sizeof(valid_detail) - 1U,
		output,
		4U,
		&output_length
	) == -ENOSPC);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "success") == 0) {
		return encode_success();
	}
	if (strcmp(argv[1], "timestamp") == 0) {
		return encode_timestamp();
	}
	if (strcmp(argv[1], "uart-send") == 0) {
		return encode_uart_send();
	}
	if (strcmp(argv[1], "error") == 0) {
		return encode_error();
	}
	if (strcmp(argv[1], "escaped-error") == 0) {
		return encode_escaped_error();
	}
	if (strcmp(argv[1], "invalid") == 0) {
		test_invalid_bounds();
		return EXIT_SUCCESS;
	}
	return EXIT_FAILURE;
}
