#include "cdc_tx_state.h"

#include <string.h>

static void finish(
	struct dmh_cdc_tx *tx,
	enum dmh_cdc_tx_result result
)
{
	tx->port.stop(tx->port.context);
	tx->state = result;
}

void dmh_cdc_tx_init(
	struct dmh_cdc_tx *tx,
	const struct dmh_cdc_tx_port *port
)
{
	tx->port = *port;
	tx->length = 0U;
	tx->accepted = 0U;
	tx->last_progress_us = 0U;
	tx->timeout_us = 0U;
	tx->state = DMH_CDC_TX_IDLE;
}

enum dmh_cdc_tx_result dmh_cdc_tx_start(
	struct dmh_cdc_tx *tx,
	const uint8_t *frame,
	size_t length,
	uint64_t now_us,
	uint64_t timeout_us
)
{
	if (frame == NULL || length == 0U || length > DMH_CDC_TX_MAX_FRAME_BYTES ||
	    timeout_us == 0U) {
		return DMH_CDC_TX_INVALID_ARGUMENT;
	}
	if (tx->state != DMH_CDC_TX_IDLE) {
		return DMH_CDC_TX_BUSY;
	}
	(void)memcpy(tx->frame, frame, length);
	tx->length = length;
	tx->accepted = 0U;
	tx->last_progress_us = now_us;
	tx->timeout_us = timeout_us;
	tx->state = DMH_CDC_TX_PENDING;
	return DMH_CDC_TX_PENDING;
}

void dmh_cdc_tx_on_writable(struct dmh_cdc_tx *tx, uint64_t now_us)
{
	size_t remaining;
	int written;

	if (tx->state != DMH_CDC_TX_PENDING) {
		tx->port.stop(tx->port.context);
		return;
	}
	remaining = tx->length - tx->accepted;
	written = tx->port.write(
		tx->port.context,
		&tx->frame[tx->accepted],
		remaining
	);
	if (written <= 0 || (size_t)written > remaining) {
		finish(tx, DMH_CDC_TX_HARDWARE_FAULT);
		return;
	}
	tx->accepted += (size_t)written;
	tx->last_progress_us = now_us;
	if (tx->accepted == tx->length) {
		finish(tx, DMH_CDC_TX_COMPLETED);
	}
}

void dmh_cdc_tx_driver_fault(struct dmh_cdc_tx *tx)
{
	if (tx->state == DMH_CDC_TX_PENDING) {
		finish(tx, DMH_CDC_TX_HARDWARE_FAULT);
	}
}

void dmh_cdc_tx_cancel(struct dmh_cdc_tx *tx)
{
	if (tx->state == DMH_CDC_TX_PENDING) {
		tx->port.stop(tx->port.context);
	}
	tx->length = 0U;
	tx->accepted = 0U;
	tx->last_progress_us = 0U;
	tx->timeout_us = 0U;
	tx->state = DMH_CDC_TX_IDLE;
}

enum dmh_cdc_tx_result dmh_cdc_tx_poll(
	struct dmh_cdc_tx *tx,
	uint64_t now_us
)
{
	enum dmh_cdc_tx_result result;

	if (tx->state == DMH_CDC_TX_PENDING &&
	    now_us - tx->last_progress_us >= tx->timeout_us) {
		finish(tx, DMH_CDC_TX_TIMEOUT);
	}
	result = tx->state;
	if (result == DMH_CDC_TX_COMPLETED ||
	    result == DMH_CDC_TX_TIMEOUT ||
	    result == DMH_CDC_TX_HARDWARE_FAULT) {
		tx->length = 0U;
		tx->accepted = 0U;
		tx->last_progress_us = 0U;
		tx->timeout_us = 0U;
		tx->state = DMH_CDC_TX_IDLE;
	}
	return result;
}
