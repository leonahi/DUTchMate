#ifndef DUTCHMATE_CDC_TX_H
#define DUTCHMATE_CDC_TX_H

#include "cdc_tx_state.h"

#include <stddef.h>
#include <stdint.h>

struct device;

int dutchmate_cdc_tx_initialize(const struct device *cdc_device);
enum dmh_cdc_tx_result dutchmate_cdc_tx_start(
	const uint8_t *frame,
	size_t length
);
enum dmh_cdc_tx_result dutchmate_cdc_tx_poll(void);
void dutchmate_cdc_tx_cancel(void);

#endif
