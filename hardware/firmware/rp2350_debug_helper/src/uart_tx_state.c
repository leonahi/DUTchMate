#include "uart_tx_state.h"

#include <string.h>

static void finish(
	struct dmh_uart_tx *tx,
	enum dmh_uart_tx_result result
)
{
	tx->port.stop(tx->port.context);
	tx->state = result;
}

void dmh_uart_tx_init(
	struct dmh_uart_tx *tx,
	const struct dmh_uart_tx_port *port
)
{
	tx->port = *port;
	tx->length = 0U;
	tx->queued = 0U;
	tx->started_us = 0U;
	tx->timeout_us = 0U;
	tx->state = DMH_UART_TX_IDLE;
}

enum dmh_uart_tx_result dmh_uart_tx_start(
	struct dmh_uart_tx *tx,
	const uint8_t *data,
	size_t length,
	uint64_t now_us,
	uint64_t timeout_us
)
{
	if (data == NULL || length == 0U || length > DMH_UART_TX_MAX_BYTES ||
	    timeout_us == 0U) {
		return DMH_UART_TX_INVALID_ARGUMENT;
	}
	if (tx->state != DMH_UART_TX_IDLE) {
		return DMH_UART_TX_BUSY;
	}
	(void)memcpy(tx->bytes, data, length);
	tx->length = length;
	tx->queued = 0U;
	tx->started_us = now_us;
	tx->timeout_us = timeout_us;
	tx->state = DMH_UART_TX_PENDING;
	return DMH_UART_TX_PENDING;
}

void dmh_uart_tx_on_interrupt(struct dmh_uart_tx *tx)
{
	if (tx->state != DMH_UART_TX_PENDING) {
		tx->port.stop(tx->port.context);
		return;
	}
	if (tx->queued < tx->length) {
		size_t remaining = tx->length - tx->queued;
		int written = tx->port.write(
			tx->port.context,
			&tx->bytes[tx->queued],
			remaining
		);

		if (written <= 0 || (size_t)written > remaining) {
			finish(tx, DMH_UART_TX_HARDWARE_FAULT);
			return;
		}
		tx->queued += (size_t)written;
	}
	if (tx->queued == tx->length) {
		int completed = tx->port.is_complete(tx->port.context);

		if (completed < 0) {
			finish(tx, DMH_UART_TX_HARDWARE_FAULT);
		} else if (completed > 0) {
			finish(tx, DMH_UART_TX_COMPLETED);
		}
	}
}

void dmh_uart_tx_driver_fault(struct dmh_uart_tx *tx)
{
	if (tx->state == DMH_UART_TX_PENDING) {
		finish(tx, DMH_UART_TX_HARDWARE_FAULT);
	}
}

void dmh_uart_tx_cancel(struct dmh_uart_tx *tx)
{
	if (tx->state == DMH_UART_TX_PENDING) {
		tx->port.stop(tx->port.context);
	}
	tx->length = 0U;
	tx->queued = 0U;
	tx->state = DMH_UART_TX_IDLE;
}

enum dmh_uart_tx_result dmh_uart_tx_poll(
	struct dmh_uart_tx *tx,
	uint64_t now_us,
	size_t *bytes_accepted
)
{
	enum dmh_uart_tx_result result;

	*bytes_accepted = 0U;
	if (tx->state == DMH_UART_TX_PENDING &&
	    now_us - tx->started_us >= tx->timeout_us) {
		finish(tx, DMH_UART_TX_TIMEOUT);
	}
	result = tx->state;
	if (result == DMH_UART_TX_COMPLETED) {
		*bytes_accepted = tx->length;
	}
	if (result == DMH_UART_TX_COMPLETED || result == DMH_UART_TX_TIMEOUT ||
	    result == DMH_UART_TX_HARDWARE_FAULT) {
		tx->length = 0U;
		tx->queued = 0U;
		tx->state = DMH_UART_TX_IDLE;
	}
	return result;
}
