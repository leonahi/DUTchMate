#ifndef DUTCHMATE_COMMAND_RUNTIME_H
#define DUTCHMATE_COMMAND_RUNTIME_H

#include <stdbool.h>
#include <stddef.h>

struct device;

int dutchmate_command_runtime_initialize(const struct device *cdc_device);
bool dutchmate_command_runtime_on_cdc_rx_ready(
	const struct device *cdc_device
);
void dutchmate_command_runtime_discard_input(void);
int dutchmate_command_runtime_start_epoch(void);
int dutchmate_command_runtime_end_epoch(void);
bool dutchmate_command_runtime_faulted(void);
bool dutchmate_command_runtime_take_response(
	const char **response,
	size_t *response_length
);
void dutchmate_command_runtime_response_sent(void);

#endif
