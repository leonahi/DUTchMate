#include "command_response.h"

#include <errno.h>
#include <stdbool.h>
#include <string.h>

struct response_writer {
	char *output;
	size_t capacity;
	size_t length;
};

static bool append_bytes(
	struct response_writer *writer,
	const char *bytes,
	size_t length
)
{
	if (length > writer->capacity - writer->length) {
		return false;
	}
	memcpy(writer->output + writer->length, bytes, length);
	writer->length += length;
	return true;
}

static bool append_literal(struct response_writer *writer, const char *literal)
{
	return append_bytes(writer, literal, strlen(literal));
}

static bool append_decimal(struct response_writer *writer, uint64_t value)
{
	char digits[20];
	size_t index = sizeof(digits);

	do {
		index--;
		digits[index] = (char)('0' + value % 10U);
		value /= 10U;
	} while (value > 0U);
	return append_bytes(writer, &digits[index], sizeof(digits) - index);
}

static bool valid_utf8_detail(const uint8_t *detail, size_t length)
{
	size_t index = 0U;

	while (index < length) {
		uint8_t first = detail[index++];

		if (first < 0x80U) {
			if (first < 0x20U || first == 0x7FU) {
				return false;
			}
			continue;
		}
		if (first >= 0xC2U && first <= 0xDFU) {
			if (index >= length || detail[index] < 0x80U ||
			    detail[index] > 0xBFU ||
			    (first == 0xC2U && detail[index] <= 0x9FU)) {
				return false;
			}
			index++;
			continue;
		}
		if (first >= 0xE0U && first <= 0xEFU) {
			if (index + 1U >= length || detail[index] < 0x80U ||
			    detail[index] > 0xBFU || detail[index + 1U] < 0x80U ||
			    detail[index + 1U] > 0xBFU ||
			    (first == 0xE0U && detail[index] < 0xA0U) ||
			    (first == 0xEDU && detail[index] > 0x9FU)) {
				return false;
			}
			index += 2U;
			continue;
		}
		if (first >= 0xF0U && first <= 0xF4U) {
			if (index + 2U >= length || detail[index] < 0x80U ||
			    detail[index] > 0xBFU || detail[index + 1U] < 0x80U ||
			    detail[index + 1U] > 0xBFU || detail[index + 2U] < 0x80U ||
			    detail[index + 2U] > 0xBFU ||
			    (first == 0xF0U && detail[index] < 0x90U) ||
			    (first == 0xF4U && detail[index] > 0x8FU)) {
				return false;
			}
			index += 3U;
			continue;
		}
		return false;
	}
	return true;
}

static bool append_json_string(
	struct response_writer *writer,
	const char *value,
	size_t length
)
{
	size_t index;

	for (index = 0U; index < length; index++) {
		if ((value[index] == '"' || value[index] == '\\') &&
		    !append_bytes(writer, "\\", 1U)) {
			return false;
		}
		if (!append_bytes(writer, &value[index], 1U)) {
			return false;
		}
	}
	return true;
}

static int finish_response(
	struct response_writer *writer,
	size_t *output_length
)
{
	if (!append_literal(writer, "}\n")) {
		return -ENOSPC;
	}
	*output_length = writer->length;
	return 0;
}

int dmh_success_response_encode(
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	static const char frame[] = "{\"ok\":true}\n";

	if (output == NULL || output_length == NULL) {
		return -EINVAL;
	}
	if (sizeof(frame) - 1U > output_capacity) {
		return -ENOSPC;
	}
	memcpy(output, frame, sizeof(frame) - 1U);
	*output_length = sizeof(frame) - 1U;
	return 0;
}

int dmh_timestamp_response_encode(
	uint64_t timestamp_us,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	struct response_writer writer = {
		.output = output,
		.capacity = output_capacity,
	};

	if (output == NULL || output_length == NULL) {
		return -EINVAL;
	}
	if (!append_literal(&writer, "{\"ok\":true,\"timestamp_us\":") ||
	    !append_decimal(&writer, timestamp_us)) {
		return -ENOSPC;
	}
	return finish_response(&writer, output_length);
}

int dmh_uart_send_response_encode(
	uint64_t timestamp_us,
	size_t bytes_accepted,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	struct response_writer writer = {
		.output = output,
		.capacity = output_capacity,
	};

	if (output == NULL || output_length == NULL || bytes_accepted > 1024U) {
		return -EINVAL;
	}
	if (!append_literal(&writer, "{\"ok\":true,\"timestamp_us\":") ||
	    !append_decimal(&writer, timestamp_us) ||
	    !append_literal(&writer, ",\"bytes_accepted\":") ||
	    !append_decimal(&writer, bytes_accepted)) {
		return -ENOSPC;
	}
	return finish_response(&writer, output_length);
}

int dmh_error_response_encode(
	enum dmh_command_error_code code,
	const char *detail,
	size_t detail_length,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	static const char *const codes[] = {
		[DMH_COMMAND_ERROR_INVALID_COMMAND] = "invalid_command",
		[DMH_COMMAND_ERROR_INVALID_ARGUMENT] = "invalid_argument",
		[DMH_COMMAND_ERROR_NOT_CONFIGURED] = "not_configured",
		[DMH_COMMAND_ERROR_CAPTURE_ACTIVE] = "capture_active",
		[DMH_COMMAND_ERROR_HARDWARE_FAULT] = "hardware_fault",
		[DMH_COMMAND_ERROR_TIMEOUT] = "timeout",
	};
	struct response_writer writer = {
		.output = output,
		.capacity = output_capacity,
	};
	const char *code_name;

	if ((unsigned int)code >= sizeof(codes) / sizeof(codes[0]) ||
	    detail == NULL || detail_length == 0U ||
	    detail_length > DMH_COMMAND_ERROR_DETAIL_MAX_BYTES || output == NULL ||
	    output_length == NULL ||
	    !valid_utf8_detail((const uint8_t *)detail, detail_length)) {
		return -EINVAL;
	}
	code_name = codes[code];
	if (!append_literal(&writer, "{\"ok\":false,\"error\":\"") ||
	    !append_literal(&writer, code_name) ||
	    !append_literal(&writer, "\",\"detail\":\"") ||
	    !append_json_string(&writer, detail, detail_length) ||
	    !append_literal(&writer, "\"")) {
		return -ENOSPC;
	}
	return finish_response(&writer, output_length);
}
