#include "uart_rx.h"

#include "platform_io.h"
#include "uart_tx.h"

#include <errno.h>
#include <stdint.h>

#include <hardware/timer.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/spinlock.h>

#define DUTCHMATE_DUT_UART_NODE DT_NODELABEL(uart0)
#define DUTCHMATE_DUT_UART_CHANNEL 0U
#define DUTCHMATE_UART_ISR_BUFFER_BYTES 64U

static const struct device *const dut_uart = DEVICE_DT_GET(DUTCHMATE_DUT_UART_NODE);
static struct dmh_uart_rx_ring rx_ring;
static struct k_spinlock rx_ring_lock;
static bool epoch_active;
static bool driver_faulted;

static void mark_driver_fault(void)
{
	k_spinlock_key_t key = k_spin_lock(&rx_ring_lock);

	driver_faulted = true;
	k_spin_unlock(&rx_ring_lock, key);
	dutchmate_uart_tx_driver_fault();
	uart_irq_rx_disable(dut_uart);
	uart_irq_err_disable(dut_uart);
}

static void dut_uart_callback(const struct device *device, void *user_data)
{
	uint8_t bytes[DUTCHMATE_UART_ISR_BUFFER_BYTES];
	uint64_t timestamp_us = time_us_64();
	int result;

	ARG_UNUSED(user_data);
	result = uart_irq_update(device);
	if (result < 0) {
		mark_driver_fault();
		return;
	}
	result = uart_err_check(device);
	/* DUT reset can produce break/framing flags; checking clears them. */
	if (result < 0) {
		mark_driver_fault();
		return;
	}

	for (;;) {
		int ready = uart_irq_rx_ready(device);

		if (ready < 0) {
			mark_driver_fault();
			return;
		}
		if (ready == 0) {
			break;
		}

		int received = uart_fifo_read(device, bytes, sizeof(bytes));

		if (received < 0) {
			mark_driver_fault();
			return;
		}
		if (received == 0) {
			break;
		}

		K_SPINLOCK(&rx_ring_lock) {
			if (epoch_active) {
				(void)dmh_uart_rx_ring_push(
					&rx_ring,
					DUTCHMATE_DUT_UART_CHANNEL,
					timestamp_us,
					bytes,
					(size_t)received
				);
			}
		}
	}
	dutchmate_uart_tx_handle_interrupt();
}

int dutchmate_uart_rx_initialize(void)
{
	static const struct uart_config config = {
		.baudrate = 460800,
		.parity = UART_CFG_PARITY_NONE,
		.stop_bits = UART_CFG_STOP_BITS_1,
		.data_bits = UART_CFG_DATA_BITS_8,
		.flow_ctrl = UART_CFG_FLOW_CTRL_NONE,
	};
	int result;

	if (!device_is_ready(dut_uart)) {
		return -ENODEV;
	}
	result = uart_configure(dut_uart, &config);
	if (result != 0) {
		return result;
	}
	result = uart_irq_callback_user_data_set(dut_uart, dut_uart_callback, NULL);
	if (result != 0) {
		return result;
	}

	uart_irq_rx_disable(dut_uart);
	uart_irq_err_disable(dut_uart);
	dmh_uart_rx_ring_init(&rx_ring);
	epoch_active = false;
	driver_faulted = false;
	return 0;
}

int dutchmate_uart_rx_start(void)
{
	int result;

	K_SPINLOCK(&rx_ring_lock) {
		dmh_uart_rx_ring_discard_retained(&rx_ring);
		driver_faulted = false;
		epoch_active = true;
	}
	result = dutchmate_platform_uart_interface_set(true);
	if (result != 0) {
		K_SPINLOCK(&rx_ring_lock) {
			epoch_active = false;
		}
		return result;
	}

	uart_irq_err_enable(dut_uart);
	uart_irq_rx_enable(dut_uart);
	return 0;
}

void dutchmate_uart_rx_stop(void)
{
	dutchmate_uart_tx_cancel();
	uart_irq_rx_disable(dut_uart);
	uart_irq_err_disable(dut_uart);
	(void)dutchmate_platform_uart_interface_set(false);
	K_SPINLOCK(&rx_ring_lock) {
		epoch_active = false;
		dmh_uart_rx_ring_discard_retained(&rx_ring);
	}
}

bool dutchmate_uart_rx_faulted(void)
{
	bool faulted;

	K_SPINLOCK(&rx_ring_lock) {
		faulted = driver_faulted;
	}
	return faulted;
}

int dutchmate_uart_rx_take_before(
	bool sequence_limit_active,
	uint64_t sequence_limit,
	uint8_t *output,
	size_t output_capacity,
	enum dmh_uart_rx_observation_kind *kind,
	struct dmh_uart_rx_chunk *chunk,
	struct dmh_uart_rx_overflow *overflow
)
{
	int result;

	K_SPINLOCK(&rx_ring_lock) {
		result = dmh_uart_rx_ring_take_before(
			&rx_ring,
			sequence_limit_active,
			sequence_limit,
			output,
			output_capacity,
			kind,
			chunk,
			overflow
		);
	}
	return result;
}

void dutchmate_uart_rx_snapshot_observation(
	struct dmh_uart_rx_snapshot *snapshot,
	uint64_t *observation_sequence
)
{
	K_SPINLOCK(&rx_ring_lock) {
		dmh_uart_rx_ring_snapshot_observation(
			&rx_ring,
			snapshot,
			observation_sequence
		);
	}
}
