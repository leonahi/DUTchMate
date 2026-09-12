#include "uart_rx.h"

#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>

const struct device fake_uart_device = {0};

static uart_irq_callback_user_data_t registered_callback;
static void *registered_user_data;
static int irq_update_result = 1;
static int error_result;
static const uint8_t *rx_bytes;
static size_t rx_length;
static size_t rx_offset;
static int interface_active;
static size_t rx_disable_calls;
static size_t error_disable_calls;
static size_t tx_fault_calls;

bool device_is_ready(const struct device *device)
{
	return device == &fake_uart_device;
}

int uart_configure(const struct device *device, const struct uart_config *config)
{
	return device == &fake_uart_device && config->baudrate == 460800U ? 0 : -EINVAL;
}

int uart_irq_callback_user_data_set(
	const struct device *device,
	uart_irq_callback_user_data_t callback,
	void *user_data
)
{
	if (device != &fake_uart_device) {
		return -EINVAL;
	}
	registered_callback = callback;
	registered_user_data = user_data;
	return 0;
}

int uart_irq_update(const struct device *device)
{
	return device == &fake_uart_device ? irq_update_result : -EINVAL;
}

int uart_err_check(const struct device *device)
{
	return device == &fake_uart_device ? error_result : -EINVAL;
}

int uart_irq_rx_ready(const struct device *device)
{
	return device == &fake_uart_device && rx_offset < rx_length;
}

int uart_fifo_read(const struct device *device, uint8_t *data, int length)
{
	size_t available;
	size_t copied;

	if (device != &fake_uart_device || length < 0) {
		return -EINVAL;
	}
	available = rx_length - rx_offset;
	copied = available < (size_t)length ? available : (size_t)length;
	(void)memcpy(data, rx_bytes + rx_offset, copied);
	rx_offset += copied;
	return (int)copied;
}

void uart_irq_rx_enable(const struct device *device)
{
	if (device != &fake_uart_device) {
		exit(EXIT_FAILURE);
	}
}

void uart_irq_rx_disable(const struct device *device)
{
	if (device != &fake_uart_device) {
		exit(EXIT_FAILURE);
	}
	rx_disable_calls++;
}

void uart_irq_err_enable(const struct device *device)
{
	if (device != &fake_uart_device) {
		exit(EXIT_FAILURE);
	}
}

void uart_irq_err_disable(const struct device *device)
{
	if (device != &fake_uart_device) {
		exit(EXIT_FAILURE);
	}
	error_disable_calls++;
}

uint64_t time_us_64(void)
{
	return 123456U;
}

int dutchmate_platform_uart_interface_set(bool active)
{
	interface_active = active ? 1 : 0;
	return 0;
}

void dutchmate_uart_tx_driver_fault(void)
{
	tx_fault_calls++;
}

void dutchmate_uart_tx_handle_interrupt(void)
{
}

void dutchmate_uart_tx_cancel(void)
{
}

static void initialize_and_start(void)
{
	if (dutchmate_uart_rx_initialize() != 0 ||
	    dutchmate_uart_rx_start() != 0 || registered_callback == NULL ||
	    interface_active == 0) {
		exit(EXIT_FAILURE);
	}
	rx_disable_calls = 0U;
	error_disable_calls = 0U;
}

static void test_line_error_recovers(void)
{
	static const uint8_t valid_bytes[] = {'O', 'K', '\n'};
	uint8_t output[sizeof(valid_bytes)] = {0};
	struct dmh_uart_rx_chunk chunk;
	struct dmh_uart_rx_overflow overflow;
	enum dmh_uart_rx_observation_kind kind;

	initialize_and_start();
	error_result = UART_BREAK;
	registered_callback(&fake_uart_device, registered_user_data);
	if (dutchmate_uart_rx_faulted() || interface_active == 0 ||
	    rx_disable_calls != 0U || error_disable_calls != 0U ||
	    tx_fault_calls != 0U) {
		exit(EXIT_FAILURE);
	}

	error_result = 0;
	rx_bytes = valid_bytes;
	rx_length = sizeof(valid_bytes);
	rx_offset = 0U;
	registered_callback(&fake_uart_device, registered_user_data);
	if (dutchmate_uart_rx_take_before(
		false,
		0U,
		output,
		sizeof(output),
		&kind,
		&chunk,
		&overflow
	) != 0 || kind != DMH_UART_RX_OBSERVATION_CHUNK ||
	    chunk.length != sizeof(valid_bytes) ||
	    memcmp(output, valid_bytes, sizeof(valid_bytes)) != 0) {
		exit(EXIT_FAILURE);
	}
}

static void test_driver_error_is_fatal(void)
{
	initialize_and_start();
	irq_update_result = -EIO;
	registered_callback(&fake_uart_device, registered_user_data);
	if (!dutchmate_uart_rx_faulted() || rx_disable_calls != 1U ||
	    error_disable_calls != 1U || tx_fault_calls != 1U) {
		exit(EXIT_FAILURE);
	}
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "line-error-recovers") == 0) {
		test_line_error_recovers();
		return EXIT_SUCCESS;
	}
	if (strcmp(argv[1], "driver-error-is-fatal") == 0) {
		test_driver_error_is_fatal();
		return EXIT_SUCCESS;
	}
	return EXIT_FAILURE;
}
