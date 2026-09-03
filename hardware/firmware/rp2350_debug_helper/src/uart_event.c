#include "uart_event.h"

#include <errno.h>
#include <string.h>

static const char frame_prefix[] = "{\"type\":\"uart\",\"channel\":";
static const char timestamp_prefix[] = ",\"timestamp_us\":";
static const char data_prefix[] = ",\"data_b64\":\"";
static const char frame_suffix[] = "\"}\n";
static const char base64_alphabet[] =
	"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

static size_t decimal_length(uint64_t value)
{
	size_t length = 1U;

	while (value >= 10U) {
		value /= 10U;
		length++;
	}
	return length;
}

static char *write_decimal(char *output, uint64_t value, size_t length)
{
	size_t index = length;

	do {
		index--;
		output[index] = (char)('0' + value % 10U);
		value /= 10U;
	} while (index > 0U);
	return output + length;
}

static char *write_base64(char *output, const uint8_t *data, size_t length)
{
	size_t index = 0U;

	while (length - index >= 3U) {
		uint32_t value = ((uint32_t)data[index] << 16U) |
				 ((uint32_t)data[index + 1U] << 8U) |
				 data[index + 2U];

		*output++ = base64_alphabet[(value >> 18U) & 0x3FU];
		*output++ = base64_alphabet[(value >> 12U) & 0x3FU];
		*output++ = base64_alphabet[(value >> 6U) & 0x3FU];
		*output++ = base64_alphabet[value & 0x3FU];
		index += 3U;
	}

	if (length - index == 1U) {
		uint32_t value = (uint32_t)data[index] << 16U;

		*output++ = base64_alphabet[(value >> 18U) & 0x3FU];
		*output++ = base64_alphabet[(value >> 12U) & 0x3FU];
		*output++ = '=';
		*output++ = '=';
	} else if (length - index == 2U) {
		uint32_t value = ((uint32_t)data[index] << 16U) |
				 ((uint32_t)data[index + 1U] << 8U);

		*output++ = base64_alphabet[(value >> 18U) & 0x3FU];
		*output++ = base64_alphabet[(value >> 12U) & 0x3FU];
		*output++ = base64_alphabet[(value >> 6U) & 0x3FU];
		*output++ = '=';
	}

	return output;
}

int dmh_uart_event_encode(
	uint8_t channel,
	uint64_t timestamp_us,
	const uint8_t *data,
	size_t data_length,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	size_t channel_length;
	size_t timestamp_length;
	size_t base64_length;
	size_t frame_length;
	char *cursor;

	if (data == NULL || output == NULL || output_length == NULL ||
	    data_length == 0U || data_length > DMH_UART_EVENT_MAX_DATA_BYTES) {
		return -EINVAL;
	}

	channel_length = decimal_length(channel);
	timestamp_length = decimal_length(timestamp_us);
	base64_length = 4U * ((data_length + 2U) / 3U);
	frame_length = sizeof(frame_prefix) - 1U + channel_length +
		       sizeof(timestamp_prefix) - 1U + timestamp_length +
		       sizeof(data_prefix) - 1U + base64_length +
		       sizeof(frame_suffix) - 1U;
	if (frame_length > output_capacity) {
		return -ENOSPC;
	}

	cursor = output;
	memcpy(cursor, frame_prefix, sizeof(frame_prefix) - 1U);
	cursor += sizeof(frame_prefix) - 1U;
	cursor = write_decimal(cursor, channel, channel_length);
	memcpy(cursor, timestamp_prefix, sizeof(timestamp_prefix) - 1U);
	cursor += sizeof(timestamp_prefix) - 1U;
	cursor = write_decimal(cursor, timestamp_us, timestamp_length);
	memcpy(cursor, data_prefix, sizeof(data_prefix) - 1U);
	cursor += sizeof(data_prefix) - 1U;
	cursor = write_base64(cursor, data, data_length);
	memcpy(cursor, frame_suffix, sizeof(frame_suffix) - 1U);
	*output_length = frame_length;
	return 0;
}
