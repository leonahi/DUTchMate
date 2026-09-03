#ifndef DUTCHMATE_UART_RX_H
#define DUTCHMATE_UART_RX_H

#include "uart_rx_ring.h"

#include <stdbool.h>

int dutchmate_uart_rx_initialize(void);
int dutchmate_uart_rx_start(void);
void dutchmate_uart_rx_stop(void);
bool dutchmate_uart_rx_faulted(void);
int dutchmate_uart_rx_take(
	uint8_t *output,
	size_t output_capacity,
	struct dmh_uart_rx_chunk *chunk
);
void dutchmate_uart_rx_snapshot(struct dmh_uart_rx_snapshot *snapshot);
bool dutchmate_uart_rx_claim_overflow(struct dmh_uart_rx_overflow *overflow);
enum dmh_uart_rx_observation_kind dutchmate_uart_rx_next_observation(void);

#endif
