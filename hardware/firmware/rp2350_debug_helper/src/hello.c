#include "hello.h"

#include <errno.h>
#include <string.h>

#define FIRMWARE_MAX_BYTES 64U

static const char hello_prefix[] =
	"{\"type\":\"hello\",\"v\":1,\"firmware\":\"";
static const char hello_suffix[] =
	"\",\"device\":\"dutchmate-rp2350\",\"capabilities\":[\"uart_receive\","
	"\"gpio_control\",\"uart_send\",\"device_timestamp\",\"overflow_telemetry\"]}\n";

static int is_safe_firmware_byte(unsigned char byte)
{
	return (byte >= 'a' && byte <= 'z') ||
	       (byte >= 'A' && byte <= 'Z') ||
	       (byte >= '0' && byte <= '9') ||
	       byte == '.' || byte == '_' || byte == '+' || byte == '-';
}

static size_t bounded_string_length(const char *value, size_t limit)
{
	size_t length = 0U;

	while (length < limit && value[length] != '\0') {
		length++;
	}
	return length;
}

int dmh_hello_encode(
	const char *firmware,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	size_t firmware_length;
	size_t frame_length;
	size_t index;

	if (firmware == NULL || output == NULL || output_length == NULL) {
		return -EINVAL;
	}
	firmware_length = bounded_string_length(firmware, FIRMWARE_MAX_BYTES + 1U);
	if (firmware_length == 0U || firmware_length > FIRMWARE_MAX_BYTES) {
		return -EINVAL;
	}
	for (index = 0U; index < firmware_length; index++) {
		if (!is_safe_firmware_byte((unsigned char)firmware[index])) {
			return -EINVAL;
		}
	}

	frame_length = sizeof(hello_prefix) - 1U + firmware_length +
		       sizeof(hello_suffix) - 1U;
	if (frame_length > output_capacity) {
		return -ENOSPC;
	}

	memcpy(output, hello_prefix, sizeof(hello_prefix) - 1U);
	memcpy(output + sizeof(hello_prefix) - 1U, firmware, firmware_length);
	memcpy(
		output + sizeof(hello_prefix) - 1U + firmware_length,
		hello_suffix,
		sizeof(hello_suffix) - 1U
	);
	*output_length = frame_length;
	return 0;
}
