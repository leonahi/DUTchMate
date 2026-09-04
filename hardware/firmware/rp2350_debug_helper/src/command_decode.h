#ifndef DUTCHMATE_COMMAND_DECODE_H
#define DUTCHMATE_COMMAND_DECODE_H

#include "control_types.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DMH_UART_SEND_MAX_BYTES 1024U

enum dmh_command_kind {
	DMH_COMMAND_NONE = 0,
	DMH_COMMAND_CONFIGURE_GPIO_MODE,
	DMH_COMMAND_PULSE_CONTROL,
	DMH_COMMAND_SET_CONTROL_STATE,
	DMH_COMMAND_UART_SEND,
};

enum dmh_command_decode_failure {
	DMH_COMMAND_DECODE_INVALID_COMMAND = 0,
	DMH_COMMAND_DECODE_INVALID_ARGUMENT,
};

struct dmh_configure_command {
	enum dmh_control_mode mode;
	enum dmh_control_level active_level;
	enum dmh_control_level idle_level;
	bool has_idle_level;
};

struct dmh_uart_send_command {
	uint8_t data[DMH_UART_SEND_MAX_BYTES];
	size_t length;
};

struct dmh_command {
	enum dmh_command_kind kind;
	uint8_t channel;
	union {
		struct dmh_configure_command configure;
		uint32_t pulse_ms;
		enum dmh_control_state control_state;
		struct dmh_uart_send_command uart_send;
	} value;
};

int dmh_command_decode(
	const uint8_t *frame,
	size_t frame_length,
	struct dmh_command *command,
	enum dmh_command_decode_failure *failure
);

#endif
