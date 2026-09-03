#ifndef DUTCHMATE_UART_EVENT_H
#define DUTCHMATE_UART_EVENT_H

#include <stddef.h>
#include <stdint.h>

#define DMH_UART_EVENT_MAX_DATA_BYTES 1024U
#define DMH_UART_EVENT_FRAME_CAPACITY 1536U

int dmh_uart_event_encode(
	uint8_t channel,
	uint64_t timestamp_us,
	const uint8_t *data,
	size_t data_length,
	char *output,
	size_t output_capacity,
	size_t *output_length
);

#endif
