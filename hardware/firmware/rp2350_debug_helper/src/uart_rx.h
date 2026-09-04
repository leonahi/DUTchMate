#ifndef DUTCHMATE_UART_RX_H
#define DUTCHMATE_UART_RX_H

#include "uart_rx_ring.h"

#include <stdbool.h>

int dutchmate_uart_rx_initialize(void);
int dutchmate_uart_rx_start(void);
void dutchmate_uart_rx_stop(void);
bool dutchmate_uart_rx_faulted(void);
int dutchmate_uart_rx_take_before(
	bool sequence_limit_active,
	uint64_t sequence_limit,
	uint8_t *output,
	size_t output_capacity,
	enum dmh_uart_rx_observation_kind *kind,
	struct dmh_uart_rx_chunk *chunk,
	struct dmh_uart_rx_overflow *overflow
);
void dutchmate_uart_rx_snapshot_observation(
	struct dmh_uart_rx_snapshot *snapshot,
	uint64_t *observation_sequence
);

#endif
