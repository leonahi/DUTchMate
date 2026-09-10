#include "command_runtime.h"

#include "command_executor.h"
#include "command_ingress.h"
#include "platform_io.h"
#include "uart_tx.h"

#include <errno.h>
#include <stdint.h>

#include <hardware/timer.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>
#include <zephyr/sys/util.h>

#define DUTCHMATE_CDC_RX_CHUNK_BYTES 128U
#define DUTCHMATE_COMMAND_QUEUE_CAPACITY 1U
#define DUTCHMATE_COMMAND_STACK_SIZE 3072U
#define DUTCHMATE_CDC_RX_STACK_SIZE 4096U
#define DUTCHMATE_COMMAND_PRIORITY 3
#define DUTCHMATE_CDC_RX_PRIORITY 4
#define DUTCHMATE_COMMAND_POLL_INTERVAL K_MSEC(1)
#define DUTCHMATE_EPOCH_STOP_TIMEOUT K_MSEC(100)

struct queued_command {
	atomic_val_t epoch;
	struct dmh_command_request request;
};

K_MSGQ_DEFINE(
	command_queue,
	sizeof(struct queued_command),
	DUTCHMATE_COMMAND_QUEUE_CAPACITY,
	4
);
K_MSGQ_DEFINE(
	cdc_rx_queue,
	sizeof(uint8_t),
	DMH_HOST_FRAME_MAX_BYTES,
	1
);
K_SEM_DEFINE(rx_start, 0, 1);
K_SEM_DEFINE(rx_stopped, 0, 1);
K_SEM_DEFINE(command_start, 0, 1);
K_SEM_DEFINE(command_stopped, 0, 1);
K_SEM_DEFINE(response_ready, 0, 1);
K_SEM_DEFINE(response_consumed, 0, 1);

static const struct device *cdc;
static struct dmh_command_ingress ingress;
static struct dmh_control control;
static struct dmh_command_executor executor;
static atomic_t initialized;
static atomic_t epoch_active;
static atomic_t epoch_number;
static atomic_t runtime_fault;
static atomic_t response_outstanding;
static atomic_t epoch_end_result;

static enum dmh_uart_tx_result command_uart_start(
	void *context,
	const uint8_t *data,
	size_t length,
	uint64_t now_us
)
{
	ARG_UNUSED(context);
	ARG_UNUSED(now_us);
	return dutchmate_uart_tx_start(data, length);
}

static enum dmh_uart_tx_result command_uart_poll(
	void *context,
	uint64_t now_us,
	size_t *bytes_accepted
)
{
	ARG_UNUSED(context);
	ARG_UNUSED(now_us);
	return dutchmate_uart_tx_poll(bytes_accepted);
}

static void command_uart_cancel(void *context)
{
	ARG_UNUSED(context);
	dutchmate_uart_tx_cancel();
}

static bool epoch_matches(atomic_val_t epoch)
{
	return atomic_get(&epoch_active) != 0 &&
	       atomic_get(&epoch_number) == epoch;
}

static void mark_runtime_fault(void)
{
	atomic_set(&runtime_fault, 1);
}

static void queue_request(
	const struct dmh_command_request *request,
	atomic_val_t epoch
)
{
	struct queued_command queued = {
		.epoch = epoch,
		.request = *request,
	};

	while (epoch_matches(epoch) && atomic_get(&runtime_fault) == 0) {
		if (k_msgq_put(&command_queue, &queued, K_MSEC(1)) == 0) {
			return;
		}
	}
}

static void run_rx_epoch(atomic_val_t epoch)
{
	uint8_t input[DUTCHMATE_CDC_RX_CHUNK_BYTES];

	dmh_command_ingress_reset(&ingress);
	while (epoch_matches(epoch) && atomic_get(&runtime_fault) == 0) {
		size_t input_length = 0U;
		size_t offset = 0U;

		while (input_length < sizeof(input) &&
		       k_msgq_get(
			       &cdc_rx_queue,
			       &input[input_length],
			       K_NO_WAIT
		       ) == 0) {
			input_length++;
		}
		if (input_length == 0U) {
			k_sleep(DUTCHMATE_COMMAND_POLL_INTERVAL);
			continue;
		}
		while (offset < input_length && epoch_matches(epoch) &&
		       atomic_get(&runtime_fault) == 0) {
			struct dmh_command_request request;
			size_t consumed;

			if (dmh_command_ingress_feed(
				&ingress,
				&input[offset],
				input_length - offset,
				&request,
				&consumed
			) != 0 || consumed == 0U) {
				mark_runtime_fault();
				break;
			}
			offset += consumed;
			if (request.kind != DMH_COMMAND_REQUEST_NONE) {
				queue_request(&request, epoch);
			}
		}
	}
	dmh_command_ingress_reset(&ingress);
}

static void cdc_rx_thread(void *first, void *second, void *third)
{
	ARG_UNUSED(first);
	ARG_UNUSED(second);
	ARG_UNUSED(third);
	for (;;) {
		atomic_val_t epoch;

		k_sem_take(&rx_start, K_FOREVER);
		epoch = atomic_get(&epoch_number);
		run_rx_epoch(epoch);
		k_sem_give(&rx_stopped);
	}
}

static enum dmh_command_executor_result submit_request(
	const struct dmh_command_request *request
)
{
	if (request->kind == DMH_COMMAND_REQUEST_COMMAND) {
		return dmh_command_executor_submit(
			&executor, &request->command, time_us_64()
		);
	}
	return dmh_command_executor_reject(
		&executor,
		request->kind == DMH_COMMAND_REQUEST_INVALID_ARGUMENT ?
			DMH_COMMAND_DECODE_INVALID_ARGUMENT :
			DMH_COMMAND_DECODE_INVALID_COMMAND
	);
}

static void publish_response(void)
{
	if (atomic_cas(&response_outstanding, 0, 1)) {
		k_sem_give(&response_ready);
	}
}

static void service_executor(atomic_val_t epoch)
{
	enum dmh_command_executor_result result;

	if (atomic_get(&response_outstanding) != 0) {
		if (k_sem_take(&response_consumed, K_NO_WAIT) == 0) {
			dmh_command_executor_response_sent(&executor);
			atomic_set(&response_outstanding, 0);
		}
		return;
	}
	result = dmh_command_executor_poll(&executor, time_us_64());
	if (result == DMH_COMMAND_EXECUTOR_RESPONSE_READY) {
		publish_response();
		return;
	}
	if (result == DMH_COMMAND_EXECUTOR_INTERNAL_FAULT) {
		mark_runtime_fault();
		return;
	}
	if (result != DMH_COMMAND_EXECUTOR_IDLE &&
	    result != DMH_COMMAND_EXECUTOR_PENDING) {
		mark_runtime_fault();
		return;
	}
	if (result == DMH_COMMAND_EXECUTOR_IDLE) {
		struct queued_command queued;

		if (k_msgq_get(&command_queue, &queued, K_NO_WAIT) != 0) {
			return;
		}
		if (queued.epoch != epoch) {
			return;
		}
		result = submit_request(&queued.request);
		if (result == DMH_COMMAND_EXECUTOR_RESPONSE_READY) {
			publish_response();
		} else if (result != DMH_COMMAND_EXECUTOR_PENDING) {
			mark_runtime_fault();
		}
	}
}

static void run_command_epoch(atomic_val_t epoch)
{
	while (epoch_matches(epoch)) {
		if (atomic_get(&runtime_fault) == 0) {
			service_executor(epoch);
		}
		k_sleep(DUTCHMATE_COMMAND_POLL_INTERVAL);
	}
}

static void command_thread(void *first, void *second, void *third)
{
	ARG_UNUSED(first);
	ARG_UNUSED(second);
	ARG_UNUSED(third);
	for (;;) {
		enum dmh_control_result result;
		atomic_val_t epoch;

		k_sem_take(&command_start, K_FOREVER);
		epoch = atomic_get(&epoch_number);
		run_command_epoch(epoch);
		result = dmh_command_executor_cancel_epoch(&executor);
		atomic_set(&response_outstanding, 0);
		k_sem_reset(&response_ready);
		k_sem_reset(&response_consumed);
		k_msgq_purge(&command_queue);
		atomic_set(&epoch_end_result, (atomic_val_t)result);
		k_sem_give(&command_stopped);
	}
}

K_THREAD_DEFINE(
	cdc_rx_thread_id,
	DUTCHMATE_CDC_RX_STACK_SIZE,
	cdc_rx_thread,
	NULL,
	NULL,
	NULL,
	DUTCHMATE_CDC_RX_PRIORITY,
	0,
	0
);
K_THREAD_DEFINE(
	command_thread_id,
	DUTCHMATE_COMMAND_STACK_SIZE,
	command_thread,
	NULL,
	NULL,
	NULL,
	DUTCHMATE_COMMAND_PRIORITY,
	0,
	0
);

int dutchmate_command_runtime_initialize(const struct device *cdc_device)
{
	const struct dmh_command_uart_port uart_port = {
		.context = NULL,
		.start = command_uart_start,
		.poll = command_uart_poll,
		.cancel = command_uart_cancel,
	};
	struct dmh_control_port control_port;

	if (cdc_device == NULL || !device_is_ready(cdc_device) ||
	    !atomic_cas(&initialized, 0, 1)) {
		return -EINVAL;
	}
	cdc = cdc_device;
	control_port = dutchmate_platform_control_port();
	dmh_command_ingress_init(&ingress);
	dmh_control_init(&control, &control_port);
	dmh_command_executor_init(&executor, &control, &uart_port);
	return 0;
}

bool dutchmate_command_runtime_on_cdc_rx_ready(
	const struct device *cdc_device
)
{
	uint8_t input[DUTCHMATE_CDC_RX_CHUNK_BYTES];
	int input_length;
	int index;

	if (cdc_device != cdc || atomic_get(&epoch_active) == 0) {
		return false;
	}
	input_length = uart_fifo_read(cdc_device, input, sizeof(input));
	if (input_length <= 0) {
		mark_runtime_fault();
		return false;
	}
	for (index = 0; index < input_length; index++) {
		if (k_msgq_put(&cdc_rx_queue, &input[index], K_NO_WAIT) != 0) {
			mark_runtime_fault();
			return false;
		}
	}
	return true;
}

void dutchmate_command_runtime_discard_input(void)
{
	uint8_t byte;

	if (atomic_get(&epoch_active) != 0) {
		return;
	}
	k_msgq_purge(&cdc_rx_queue);
	while (uart_poll_in(cdc, &byte) == 0) {
		continue;
	}
}

int dutchmate_command_runtime_start_epoch(void)
{
	if (atomic_get(&initialized) == 0 ||
	    !atomic_cas(&epoch_active, 0, 1)) {
		return -EINVAL;
	}
	(void)atomic_inc(&epoch_number);
	atomic_set(&runtime_fault, 0);
	atomic_set(&epoch_end_result, DMH_CONTROL_OK);
	atomic_set(&response_outstanding, 0);
	k_msgq_purge(&command_queue);
	k_msgq_purge(&cdc_rx_queue);
	k_sem_reset(&rx_stopped);
	k_sem_reset(&command_stopped);
	k_sem_reset(&response_ready);
	k_sem_reset(&response_consumed);
	uart_irq_rx_enable(cdc);
	k_sem_give(&rx_start);
	k_sem_give(&command_start);
	return 0;
}

int dutchmate_command_runtime_end_epoch(void)
{
	int result = 0;

	if (atomic_get(&initialized) == 0) {
		return -EINVAL;
	}
	if (!atomic_cas(&epoch_active, 1, 0)) {
		return 0;
	}
	uart_irq_rx_disable(cdc);
	if (k_sem_take(&rx_stopped, DUTCHMATE_EPOCH_STOP_TIMEOUT) != 0) {
		result = -ETIMEDOUT;
	}
	if (k_sem_take(&command_stopped, DUTCHMATE_EPOCH_STOP_TIMEOUT) != 0) {
		result = -ETIMEDOUT;
	}
	k_msgq_purge(&cdc_rx_queue);
	if (atomic_get(&epoch_end_result) != DMH_CONTROL_OK && result == 0) {
		result = -EIO;
	}
	return result;
}

bool dutchmate_command_runtime_faulted(void)
{
	return atomic_get(&runtime_fault) != 0;
}

bool dutchmate_command_runtime_take_response(
	const char **response,
	size_t *response_length
)
{
	if (response == NULL || response_length == NULL ||
	    k_sem_take(&response_ready, K_NO_WAIT) != 0) {
		return false;
	}
	*response = dmh_command_executor_response(&executor, response_length);
	if (*response == NULL) {
		mark_runtime_fault();
		return false;
	}
	return true;
}

void dutchmate_command_runtime_response_sent(void)
{
	if (atomic_get(&response_outstanding) != 0) {
		k_sem_give(&response_consumed);
	}
}
