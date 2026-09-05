#include "uart_tx.h"

#include <errno.h>

#include <hardware/timer.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>

#define DUTCHMATE_DUT_UART_NODE DT_NODELABEL(uart0)
#define DUTCHMATE_UART_TX_TIMEOUT_US 100000U

static const struct device *const dut_uart = DEVICE_DT_GET(DUTCHMATE_DUT_UART_NODE);
static struct dmh_uart_tx tx_state;
static struct k_spinlock tx_lock;
static struct k_work tx_kick_work;

static int write_fifo(void *context, const uint8_t *data, size_t length)
{
	ARG_UNUSED(context);
	return uart_fifo_fill(dut_uart, data, (int)length);
}

static int transmission_complete(void *context)
{
	ARG_UNUSED(context);
	return uart_irq_tx_complete(dut_uart);
}

static void stop_transmission(void *context)
{
	ARG_UNUSED(context);
	uart_irq_tx_disable(dut_uart);
}

static void kick_transmission(struct k_work *work)
{
	ARG_UNUSED(work);
	uart_irq_tx_enable(dut_uart);
}

int dutchmate_uart_tx_initialize(void)
{
	const struct dmh_uart_tx_port port = {
		.context = NULL,
		.write = write_fifo,
		.is_complete = transmission_complete,
		.stop = stop_transmission,
	};

	if (!device_is_ready(dut_uart)) {
		return -ENODEV;
	}
	dmh_uart_tx_init(&tx_state, &port);
	k_work_init(&tx_kick_work, kick_transmission);
	uart_irq_tx_disable(dut_uart);
	return 0;
}

enum dmh_uart_tx_result dutchmate_uart_tx_start(
	const uint8_t *data,
	size_t length
)
{
	enum dmh_uart_tx_result result;
	uint64_t now_us = time_us_64();

	K_SPINLOCK(&tx_lock) {
		result = dmh_uart_tx_start(
			&tx_state,
			data,
			length,
			now_us,
			DUTCHMATE_UART_TX_TIMEOUT_US
		);
	}
	if (result == DMH_UART_TX_PENDING) {
		if (k_work_submit(&tx_kick_work) < 0) {
			dutchmate_uart_tx_driver_fault();
			dutchmate_uart_tx_cancel();
			return DMH_UART_TX_HARDWARE_FAULT;
		}
	}
	return result;
}

enum dmh_uart_tx_result dutchmate_uart_tx_poll(size_t *bytes_accepted)
{
	enum dmh_uart_tx_result result;
	uint64_t now_us = time_us_64();

	K_SPINLOCK(&tx_lock) {
		result = dmh_uart_tx_poll(&tx_state, now_us, bytes_accepted);
	}
	return result;
}

void dutchmate_uart_tx_handle_interrupt(void)
{
	int ready = uart_irq_tx_ready(dut_uart);

	if (ready < 0) {
		uart_irq_tx_disable(dut_uart);
		dutchmate_uart_tx_driver_fault();
		return;
	}
	if (ready > 0) {
		K_SPINLOCK(&tx_lock) {
			dmh_uart_tx_on_interrupt(&tx_state);
		}
	}
}

void dutchmate_uart_tx_driver_fault(void)
{
	K_SPINLOCK(&tx_lock) {
		dmh_uart_tx_driver_fault(&tx_state);
	}
}

void dutchmate_uart_tx_cancel(void)
{
	K_SPINLOCK(&tx_lock) {
		dmh_uart_tx_cancel(&tx_state);
	}
}
