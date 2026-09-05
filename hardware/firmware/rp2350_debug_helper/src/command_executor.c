#include "command_executor.h"

#include <string.h>

static const char invalid_command_detail[] = "Command is invalid";
static const char invalid_argument_detail[] = "Command argument is invalid";
static const char control_fault_detail[] = "Control hardware operation failed";
static const char uart_fault_detail[] = "UART transmission failed";
static const char uart_timeout_detail[] = "UART transmission timed out";

static enum dmh_command_executor_result response_encoded(
	struct dmh_command_executor *executor,
	int encode_result
)
{
	if (encode_result != 0) {
		executor->state = DMH_COMMAND_EXECUTOR_STATE_IDLE;
		executor->response_length = 0U;
		return DMH_COMMAND_EXECUTOR_INTERNAL_FAULT;
	}
	executor->state = DMH_COMMAND_EXECUTOR_STATE_RESPONSE;
	return DMH_COMMAND_EXECUTOR_RESPONSE_READY;
}

static enum dmh_command_executor_result stage_timestamp(
	struct dmh_command_executor *executor,
	uint64_t timestamp_us
)
{
	return response_encoded(
		executor,
		dmh_timestamp_response_encode(
			timestamp_us,
			executor->response,
			sizeof(executor->response),
			&executor->response_length
		)
	);
}

static enum dmh_command_executor_result stage_uart_success(
	struct dmh_command_executor *executor,
	uint64_t timestamp_us,
	size_t bytes_accepted
)
{
	return response_encoded(
		executor,
		dmh_uart_send_response_encode(
			timestamp_us,
			bytes_accepted,
			executor->response,
			sizeof(executor->response),
			&executor->response_length
		)
	);
}

static enum dmh_command_executor_result stage_error(
	struct dmh_command_executor *executor,
	enum dmh_command_error_code code,
	const char *detail,
	size_t detail_length
)
{
	return response_encoded(
		executor,
		dmh_error_response_encode(
			code,
			detail,
			detail_length,
			executor->response,
			sizeof(executor->response),
			&executor->response_length
		)
	);
}

static enum dmh_command_executor_result stage_literal_error(
	struct dmh_command_executor *executor,
	enum dmh_command_error_code code,
	const char *detail
)
{
	return stage_error(executor, code, detail, strlen(detail));
}

static enum dmh_command_executor_result stage_not_configured(
	struct dmh_command_executor *executor,
	uint8_t channel
)
{
	char detail[] = "CTRL0 is not configured";

	detail[4] = (char)('0' + channel);
	return stage_error(
		executor,
		DMH_COMMAND_ERROR_NOT_CONFIGURED,
		detail,
		sizeof(detail) - 1U
	);
}

static enum dmh_command_executor_result map_control_result(
	struct dmh_command_executor *executor,
	enum dmh_control_result result,
	uint8_t channel,
	uint64_t timestamp_us
)
{
	if (result == DMH_CONTROL_OK) {
		return stage_timestamp(executor, timestamp_us);
	}
	if (result == DMH_CONTROL_INVALID_ARGUMENT) {
		return stage_literal_error(
			executor,
			DMH_COMMAND_ERROR_INVALID_ARGUMENT,
			invalid_argument_detail
		);
	}
	if (result == DMH_CONTROL_NOT_CONFIGURED) {
		return stage_not_configured(executor, channel);
	}
	return stage_literal_error(
		executor,
		DMH_COMMAND_ERROR_HARDWARE_FAULT,
		control_fault_detail
	);
}

static enum dmh_command_executor_result submit_configure(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
)
{
	const struct dmh_configure_command *configuration = &command->value.configure;

	return map_control_result(
		executor,
		dmh_control_configure(
			executor->control,
			command->channel,
			configuration->mode,
			configuration->active_level,
			configuration->has_idle_level,
			configuration->idle_level
		),
		command->channel,
		now_us
	);
}

static enum dmh_command_executor_result submit_pulse(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
)
{
	enum dmh_control_result result = dmh_control_pulse_start(
		executor->control,
		command->channel,
		command->value.pulse_ms,
		now_us
	);

	if (result == DMH_CONTROL_PENDING) {
		executor->state = DMH_COMMAND_EXECUTOR_STATE_CONTROL_PULSE;
		return DMH_COMMAND_EXECUTOR_PENDING;
	}
	return map_control_result(executor, result, command->channel, now_us);
}

static enum dmh_command_executor_result submit_control_state(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
)
{
	return map_control_result(
		executor,
		dmh_control_set_state(
			executor->control,
			command->channel,
			command->value.control_state
		),
		command->channel,
		now_us
	);
}

static enum dmh_command_executor_result submit_uart(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
)
{
	enum dmh_uart_tx_result result = executor->uart.start(
		executor->uart.context,
		command->value.uart_send.data,
		command->value.uart_send.length,
		now_us
	);

	if (result == DMH_UART_TX_PENDING) {
		executor->state = DMH_COMMAND_EXECUTOR_STATE_UART_TX;
		return DMH_COMMAND_EXECUTOR_PENDING;
	}
	if (result == DMH_UART_TX_COMPLETED) {
		return stage_uart_success(
			executor,
			now_us,
			command->value.uart_send.length
		);
	}
	if (result == DMH_UART_TX_INVALID_ARGUMENT) {
		return stage_literal_error(
			executor,
			DMH_COMMAND_ERROR_INVALID_ARGUMENT,
			invalid_argument_detail
		);
	}
	return stage_literal_error(
		executor,
		DMH_COMMAND_ERROR_HARDWARE_FAULT,
		uart_fault_detail
	);
}

void dmh_command_executor_init(
	struct dmh_command_executor *executor,
	struct dmh_control *control,
	const struct dmh_command_uart_port *uart
)
{
	executor->control = control;
	executor->uart = *uart;
	executor->state = DMH_COMMAND_EXECUTOR_STATE_IDLE;
	executor->response_length = 0U;
}

enum dmh_command_executor_result dmh_command_executor_submit(
	struct dmh_command_executor *executor,
	const struct dmh_command *command,
	uint64_t now_us
)
{
	if (executor->state != DMH_COMMAND_EXECUTOR_STATE_IDLE) {
		return DMH_COMMAND_EXECUTOR_BUSY;
	}
	if (command->kind == DMH_COMMAND_CONFIGURE_GPIO_MODE) {
		return submit_configure(executor, command, now_us);
	}
	if (command->kind == DMH_COMMAND_PULSE_CONTROL) {
		return submit_pulse(executor, command, now_us);
	}
	if (command->kind == DMH_COMMAND_SET_CONTROL_STATE) {
		return submit_control_state(executor, command, now_us);
	}
	if (command->kind == DMH_COMMAND_UART_SEND) {
		return submit_uart(executor, command, now_us);
	}
	return stage_literal_error(
		executor,
		DMH_COMMAND_ERROR_INVALID_COMMAND,
		invalid_command_detail
	);
}

enum dmh_command_executor_result dmh_command_executor_reject(
	struct dmh_command_executor *executor,
	enum dmh_command_decode_failure failure
)
{
	if (executor->state != DMH_COMMAND_EXECUTOR_STATE_IDLE) {
		return DMH_COMMAND_EXECUTOR_BUSY;
	}
	if (failure == DMH_COMMAND_DECODE_INVALID_ARGUMENT) {
		return stage_literal_error(
			executor,
			DMH_COMMAND_ERROR_INVALID_ARGUMENT,
			invalid_argument_detail
		);
	}
	return stage_literal_error(
		executor,
		DMH_COMMAND_ERROR_INVALID_COMMAND,
		invalid_command_detail
	);
}

enum dmh_command_executor_result dmh_command_executor_poll(
	struct dmh_command_executor *executor,
	uint64_t now_us
)
{
	if (executor->state == DMH_COMMAND_EXECUTOR_STATE_CONTROL_PULSE) {
		enum dmh_control_poll_result result = dmh_control_poll(
			executor->control,
			now_us
		);

		if (result == DMH_CONTROL_POLL_COMPLETED) {
			return stage_timestamp(executor, now_us);
		}
		if (result == DMH_CONTROL_POLL_HARDWARE_FAULT) {
			return stage_literal_error(
				executor,
				DMH_COMMAND_ERROR_HARDWARE_FAULT,
				control_fault_detail
			);
		}
		return DMH_COMMAND_EXECUTOR_PENDING;
	}
	if (executor->state == DMH_COMMAND_EXECUTOR_STATE_UART_TX) {
		size_t bytes_accepted;
		enum dmh_uart_tx_result result = executor->uart.poll(
			executor->uart.context,
			now_us,
			&bytes_accepted
		);

		if (result == DMH_UART_TX_COMPLETED) {
			return stage_uart_success(executor, now_us, bytes_accepted);
		}
		if (result == DMH_UART_TX_TIMEOUT) {
			return stage_literal_error(
				executor,
				DMH_COMMAND_ERROR_TIMEOUT,
				uart_timeout_detail
			);
		}
		if (result == DMH_UART_TX_HARDWARE_FAULT) {
			return stage_literal_error(
				executor,
				DMH_COMMAND_ERROR_HARDWARE_FAULT,
				uart_fault_detail
			);
		}
		if (result != DMH_UART_TX_PENDING) {
			return DMH_COMMAND_EXECUTOR_INTERNAL_FAULT;
		}
		return DMH_COMMAND_EXECUTOR_PENDING;
	}
	if (executor->state == DMH_COMMAND_EXECUTOR_STATE_RESPONSE) {
		return DMH_COMMAND_EXECUTOR_RESPONSE_READY;
	}
	return DMH_COMMAND_EXECUTOR_IDLE;
}

const char *dmh_command_executor_response(
	const struct dmh_command_executor *executor,
	size_t *response_length
)
{
	if (executor->state != DMH_COMMAND_EXECUTOR_STATE_RESPONSE) {
		*response_length = 0U;
		return NULL;
	}
	*response_length = executor->response_length;
	return executor->response;
}

void dmh_command_executor_response_sent(struct dmh_command_executor *executor)
{
	if (executor->state == DMH_COMMAND_EXECUTOR_STATE_RESPONSE) {
		executor->response_length = 0U;
		executor->state = DMH_COMMAND_EXECUTOR_STATE_IDLE;
	}
}

enum dmh_control_result dmh_command_executor_cancel_epoch(
	struct dmh_command_executor *executor
)
{
	executor->uart.cancel(executor->uart.context);
	executor->state = DMH_COMMAND_EXECUTOR_STATE_IDLE;
	executor->response_length = 0U;
	return dmh_control_end_epoch(executor->control);
}
