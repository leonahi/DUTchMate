#include "uart_tx_state.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct fake_uart {
	uint8_t bytes[DMH_UART_TX_MAX_BYTES];
	size_t length;
	size_t max_write;
	int forced_write_result;
	int complete_result;
	size_t write_calls;
	size_t stop_calls;
};

static int write_bytes(void *context, const uint8_t *data, size_t length)
{
	struct fake_uart *uart = context;
	size_t accepted = length < uart->max_write ? length : uart->max_write;

	uart->write_calls++;
	if (uart->forced_write_result != 0) {
		return uart->forced_write_result;
	}
	if (accepted > 0U) {
		(void)memcpy(&uart->bytes[uart->length], data, accepted);
		uart->length += accepted;
	}
	return (int)accepted;
}

static int transmission_complete(void *context)
{
	struct fake_uart *uart = context;

	return uart->complete_result;
}

static void stop_transmission(void *context)
{
	struct fake_uart *uart = context;

	uart->stop_calls++;
}

static struct dmh_uart_tx_port make_port(struct fake_uart *uart)
{
	return (struct dmh_uart_tx_port) {
		.context = uart,
		.write = write_bytes,
		.is_complete = transmission_complete,
		.stop = stop_transmission,
	};
}

static void expect_result(enum dmh_uart_tx_result actual, enum dmh_uart_tx_result expected)
{
	if (actual != expected) {
		(void)fprintf(stderr, "result %d, expected %d\n", actual, expected);
		exit(EXIT_FAILURE);
	}
}

static void test_bounds_and_busy_state(void)
{
	struct fake_uart uart = {.max_write = DMH_UART_TX_MAX_BYTES};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t bytes[DMH_UART_TX_MAX_BYTES + 1U] = {0x5aU};

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, NULL, 1U, 0U, 100U),
		DMH_UART_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, 0U, 0U, 100U),
		DMH_UART_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, DMH_UART_TX_MAX_BYTES + 1U, 0U, 100U),
		DMH_UART_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, 1U, 0U, 0U),
		DMH_UART_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, DMH_UART_TX_MAX_BYTES, 0U, 100U),
		DMH_UART_TX_PENDING
	);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, 1U, 0U, 100U),
		DMH_UART_TX_BUSY
	);
	if (uart.write_calls != 0U || uart.stop_calls != 0U) {
		exit(EXIT_FAILURE);
	}
	dmh_uart_tx_cancel(&tx);
}

static void test_partial_writes_complete_once(void)
{
	struct fake_uart uart = {.max_write = 2U};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t bytes[] = {0x10U, 0x20U, 0x30U};
	size_t bytes_accepted = 99U;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), 100U, 1000U),
		DMH_UART_TX_PENDING
	);
	bytes[0] = 0xffU;
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(dmh_uart_tx_poll(&tx, 500U, &bytes_accepted), DMH_UART_TX_PENDING);
	if (bytes_accepted != 0U) {
		exit(EXIT_FAILURE);
	}
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(dmh_uart_tx_poll(&tx, 1099U, &bytes_accepted), DMH_UART_TX_PENDING);
	uart.complete_result = 1;
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 1099U, &bytes_accepted),
		DMH_UART_TX_COMPLETED
	);
	if (bytes_accepted != 3U || uart.length != 3U || uart.stop_calls != 1U ||
	    uart.write_calls != 2U || uart.bytes[0] != 0x10U ||
	    uart.bytes[1] != 0x20U || uart.bytes[2] != 0x30U) {
		exit(EXIT_FAILURE);
	}
	expect_result(dmh_uart_tx_poll(&tx, 1100U, &bytes_accepted), DMH_UART_TX_IDLE);
}

static void test_zero_progress_is_hardware_fault(void)
{
	struct fake_uart uart = {.max_write = 0U};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t byte = 0xaaU;
	size_t bytes_accepted = 99U;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, &byte, 1U, 0U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 1U, &bytes_accepted),
		DMH_UART_TX_HARDWARE_FAULT
	);
	if (bytes_accepted != 0U || uart.write_calls != 1U || uart.stop_calls != 1U) {
		exit(EXIT_FAILURE);
	}
	dmh_uart_tx_on_interrupt(&tx);
	if (uart.write_calls != 1U || uart.stop_calls != 2U) {
		exit(EXIT_FAILURE);
	}
}

static void test_invalid_driver_counts_are_hardware_faults(void)
{
	struct fake_uart uart = {
		.max_write = 4U,
		.forced_write_result = 5,
	};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t bytes[] = {1U, 2U, 3U, 4U};
	size_t bytes_accepted;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 1U, &bytes_accepted),
		DMH_UART_TX_HARDWARE_FAULT
	);

	uart = (struct fake_uart) {
		.max_write = 4U,
		.forced_write_result = -1,
	};
	port = make_port(&uart);
	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 1U, &bytes_accepted),
		DMH_UART_TX_HARDWARE_FAULT
	);
}

static void test_completion_check_failure_is_hardware_fault(void)
{
	struct fake_uart uart = {
		.max_write = 1U,
		.complete_result = -1,
	};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t byte = 0x55U;
	size_t bytes_accepted;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, &byte, 1U, 0U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 1U, &bytes_accepted),
		DMH_UART_TX_HARDWARE_FAULT
	);
	if (uart.stop_calls != 1U) {
		exit(EXIT_FAILURE);
	}
}

static void test_timeout_handles_timer_wrap(void)
{
	struct fake_uart uart = {.max_write = 1U};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t bytes[] = {0x33U, 0x44U};
	size_t bytes_accepted = 99U;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), UINT64_MAX - 99U, 200U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	expect_result(dmh_uart_tx_poll(&tx, 99U, &bytes_accepted), DMH_UART_TX_PENDING);
	expect_result(dmh_uart_tx_poll(&tx, 100U, &bytes_accepted), DMH_UART_TX_TIMEOUT);
	if (bytes_accepted != 0U || uart.stop_calls != 1U) {
		exit(EXIT_FAILURE);
	}
	dmh_uart_tx_on_interrupt(&tx);
	if (uart.write_calls != 1U) {
		exit(EXIT_FAILURE);
	}
}

static void test_cancel_and_driver_fault_never_complete(void)
{
	struct fake_uart uart = {.max_write = 1U};
	struct dmh_uart_tx tx;
	struct dmh_uart_tx_port port = make_port(&uart);
	uint8_t bytes[] = {0x11U, 0x22U};
	size_t bytes_accepted;

	dmh_uart_tx_init(&tx, &port);
	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	dmh_uart_tx_cancel(&tx);
	expect_result(dmh_uart_tx_poll(&tx, 100U, &bytes_accepted), DMH_UART_TX_IDLE);
	dmh_uart_tx_on_interrupt(&tx);
	if (uart.write_calls != 1U || uart.stop_calls != 2U) {
		exit(EXIT_FAILURE);
	}

	expect_result(
		dmh_uart_tx_start(&tx, bytes, sizeof(bytes), 200U, 100U),
		DMH_UART_TX_PENDING
	);
	dmh_uart_tx_on_interrupt(&tx);
	dmh_uart_tx_driver_fault(&tx);
	expect_result(
		dmh_uart_tx_poll(&tx, 201U, &bytes_accepted),
		DMH_UART_TX_HARDWARE_FAULT
	);
	if (uart.write_calls != 2U || uart.stop_calls != 3U) {
		exit(EXIT_FAILURE);
	}
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "bounds") == 0) {
		test_bounds_and_busy_state();
	} else if (strcmp(argv[1], "partial") == 0) {
		test_partial_writes_complete_once();
	} else if (strcmp(argv[1], "zero") == 0) {
		test_zero_progress_is_hardware_fault();
	} else if (strcmp(argv[1], "invalid-count") == 0) {
		test_invalid_driver_counts_are_hardware_faults();
	} else if (strcmp(argv[1], "complete-fault") == 0) {
		test_completion_check_failure_is_hardware_fault();
	} else if (strcmp(argv[1], "timeout") == 0) {
		test_timeout_handles_timer_wrap();
	} else if (strcmp(argv[1], "cancel") == 0) {
		test_cancel_and_driver_fault_never_complete();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
