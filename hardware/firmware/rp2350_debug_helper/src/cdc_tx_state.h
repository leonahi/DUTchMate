#ifndef DUTCHMATE_CDC_TX_STATE_H
#define DUTCHMATE_CDC_TX_STATE_H

#include <stddef.h>
#include <stdint.h>

#define DMH_CDC_TX_MAX_FRAME_BYTES 1536U

enum dmh_cdc_tx_result {
	DMH_CDC_TX_IDLE = 0,
	DMH_CDC_TX_PENDING,
	DMH_CDC_TX_COMPLETED,
	DMH_CDC_TX_INVALID_ARGUMENT,
	DMH_CDC_TX_BUSY,
	DMH_CDC_TX_TIMEOUT,
	DMH_CDC_TX_HARDWARE_FAULT,
};

struct dmh_cdc_tx_port {
	void *context;
	int (*write)(void *context, const uint8_t *data, size_t length);
	void (*stop)(void *context);
};

struct dmh_cdc_tx {
	struct dmh_cdc_tx_port port;
	uint8_t frame[DMH_CDC_TX_MAX_FRAME_BYTES];
	size_t length;
	size_t accepted;
	uint64_t last_progress_us;
	uint64_t timeout_us;
	enum dmh_cdc_tx_result state;
};

void dmh_cdc_tx_init(
	struct dmh_cdc_tx *tx,
	const struct dmh_cdc_tx_port *port
);
enum dmh_cdc_tx_result dmh_cdc_tx_start(
	struct dmh_cdc_tx *tx,
	const uint8_t *frame,
	size_t length,
	uint64_t now_us,
	uint64_t timeout_us
);
void dmh_cdc_tx_on_writable(struct dmh_cdc_tx *tx, uint64_t now_us);
void dmh_cdc_tx_driver_fault(struct dmh_cdc_tx *tx);
void dmh_cdc_tx_cancel(struct dmh_cdc_tx *tx);
enum dmh_cdc_tx_result dmh_cdc_tx_poll(
	struct dmh_cdc_tx *tx,
	uint64_t now_us
);

#endif
