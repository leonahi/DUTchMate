#ifndef DUTCHMATE_UART_TX_STATE_H
#define DUTCHMATE_UART_TX_STATE_H

#include "uart_limits.h"

#include <stddef.h>
#include <stdint.h>

#define DMH_UART_TX_MAX_BYTES DMH_UART_SEND_MAX_BYTES

enum dmh_uart_tx_result {
	DMH_UART_TX_IDLE = 0,
	DMH_UART_TX_PENDING,
	DMH_UART_TX_COMPLETED,
	DMH_UART_TX_INVALID_ARGUMENT,
	DMH_UART_TX_BUSY,
	DMH_UART_TX_TIMEOUT,
	DMH_UART_TX_HARDWARE_FAULT,
};

struct dmh_uart_tx_port {
	void *context;
	int (*write)(void *context, const uint8_t *data, size_t length);
	int (*is_complete)(void *context);
	void (*stop)(void *context);
};

struct dmh_uart_tx {
	struct dmh_uart_tx_port port;
	uint8_t bytes[DMH_UART_TX_MAX_BYTES];
	size_t length;
	size_t queued;
	uint64_t started_us;
	uint64_t timeout_us;
	enum dmh_uart_tx_result state;
};

void dmh_uart_tx_init(
	struct dmh_uart_tx *tx,
	const struct dmh_uart_tx_port *port
);
enum dmh_uart_tx_result dmh_uart_tx_start(
	struct dmh_uart_tx *tx,
	const uint8_t *data,
	size_t length,
	uint64_t now_us,
	uint64_t timeout_us
);
void dmh_uart_tx_on_interrupt(struct dmh_uart_tx *tx);
void dmh_uart_tx_driver_fault(struct dmh_uart_tx *tx);
void dmh_uart_tx_cancel(struct dmh_uart_tx *tx);
enum dmh_uart_tx_result dmh_uart_tx_poll(
	struct dmh_uart_tx *tx,
	uint64_t now_us,
	size_t *bytes_accepted
);

#endif
