#ifndef DUTCHMATE_UART_TX_H
#define DUTCHMATE_UART_TX_H

#include "uart_tx_state.h"

#include <stddef.h>
#include <stdint.h>

int dutchmate_uart_tx_initialize(void);
enum dmh_uart_tx_result dutchmate_uart_tx_start(
	const uint8_t *data,
	size_t length
);
enum dmh_uart_tx_result dutchmate_uart_tx_poll(size_t *bytes_accepted);
void dutchmate_uart_tx_handle_interrupt(void);
void dutchmate_uart_tx_driver_fault(void);
void dutchmate_uart_tx_cancel(void);

#endif
