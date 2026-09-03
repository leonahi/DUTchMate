#include "uart_event.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static uint8_t data[DMH_UART_EVENT_MAX_DATA_BYTES + 1U];
static char frame[DMH_UART_EVENT_FRAME_CAPACITY];

static int encode_and_write(
	uint8_t channel,
	uint64_t timestamp_us,
	const uint8_t *bytes,
	size_t length,
	size_t capacity
)
{
	size_t frame_length;

	if (dmh_uart_event_encode(
		channel,
		timestamp_us,
		bytes,
		length,
		frame,
		capacity,
		&frame_length
	) != 0) {
		return 2;
	}
	if (fwrite(frame, 1U, frame_length, stdout) != frame_length) {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}

int main(int argc, char **argv)
{
	size_t index;

	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "canonical") == 0) {
		return encode_and_write(
			0U,
			182341200U,
			(const uint8_t *)"BOOT_OK\n",
			8U,
			sizeof(frame)
		);
	}
	if (strcmp(argv[1], "one") == 0) {
		data[0] = 0xFFU;
		return encode_and_write(1U, 0U, data, 1U, sizeof(frame));
	}
	if (strcmp(argv[1], "two") == 0) {
		data[0] = 0x00U;
		data[1] = 0xFEU;
		return encode_and_write(2U, 1U, data, 2U, sizeof(frame));
	}
	if (strcmp(argv[1], "three") == 0) {
		data[0] = 0x00U;
		data[1] = 0x01U;
		data[2] = 0x02U;
		return encode_and_write(255U, UINT64_MAX, data, 3U, sizeof(frame));
	}
	if (strcmp(argv[1], "maximum") == 0) {
		for (index = 0U; index < DMH_UART_EVENT_MAX_DATA_BYTES; index++) {
			data[index] = (uint8_t)index;
		}
		return encode_and_write(
			0U,
			42U,
			data,
			DMH_UART_EVENT_MAX_DATA_BYTES,
			sizeof(frame)
		);
	}
	if (strcmp(argv[1], "zero") == 0) {
		return encode_and_write(0U, 0U, data, 0U, sizeof(frame));
	}
	if (strcmp(argv[1], "oversized") == 0) {
		return encode_and_write(0U, 0U, data, sizeof(data), sizeof(frame));
	}
	if (strcmp(argv[1], "small-output") == 0) {
		data[0] = 1U;
		return encode_and_write(0U, 0U, data, 1U, 10U);
	}

	return EXIT_FAILURE;
}
