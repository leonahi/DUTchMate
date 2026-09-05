#ifndef DUTCHMATE_COMMAND_EXECUTOR_H
#define DUTCHMATE_COMMAND_EXECUTOR_H

#include "command_decode.h"
#include "command_response.h"
#include "control_state.h"
#include "uart_tx_state.h"

#include <stddef.h>
#include <stdint.h>

enum dmh_command_executor_result {
	DMH_COMMAND_EXECUTOR_IDLE = 0,
	DMH_COMMAND_EXECUTOR_PENDING,
	DMH_COMMAND_EXECUTOR_RESPONSE_READY,
	DMH_COMMAND_EXECUTOR_BUSY,
	DMH_COMMAND_EXECUTOR_INTERNAL_FAULT,
};

struct dmh_command_uart_port {
	void *context;
	enum dmh_uart_tx_result (*start)(
		void *context,
		const uint8_t *data,
		size_t length,
		uint64_t now_us
	);
	enum dmh_uart_tx_result (*poll)(
		void *context,
		uint64_t now_us,
		size_t *bytes_accepted
	);
	void (*cancel)(void *context);
};

enum dmh_command_executor_state {
	DMH_COMMAND_EXECUTOR_STATE_IDLE = 0,
	DMH_COMMAND_EXECUTOR_STATE_CONTROL_PULSE,
	DMH_COMMAND_EXECUTOR_STATE_UART_TX,
	DMH_COMMAND_EXECUTOR_STATE_RESPONSE,
};

struct dmh_command_executor {
	struct dmh_control *control;
	struct dmh_command_uart_port uart;
	enum dmh_command_executor_state state;
	char response[DMH_COMMAND_RESPONSE_FRAME_CAPACITY];
	size_t response_length;
};

void dmh_command_executor_init(
	struct dmh_command_executor *executor,
	struct dmh_control *control,
	const struct dmh_command_uart_port *uart
);
enum dmh_command_executor_result dmh_command_executor_submit(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
);
enum dmh_command_executor_result dmh_command_executor_poll(
	struct dmh_command_executor *executor,
	uint64_t now_us
);
const char *dmh_command_executor_response(
	const struct dmh_command_executor *executor,
	size_t *response_length
);
void dmh_command_executor_response_sent(struct dmh_command_executor *executor);
enum dmh_control_result dmh_command_executor_cancel_epoch(
	struct dmh_command_executor *executor
);

#endif
