#include "cdc_tx.h"

#include "command_runtime.h"

#include <errno.h>

#include <hardware/timer.h>
#include <zephyr/device.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/atomic.h>

#define DUTCHMATE_CDC_TX_NO_PROGRESS_TIMEOUT_US 250000ULL

static const struct device *cdc;
static struct dmh_cdc_tx tx;
static struct k_spinlock tx_lock;
static atomic_t initialized;

static int write_bytes(void *context, const uint8_t *data, size_t length)
{
	const struct device *device = context;

	return uart_fifo_fill(device, data, (int)length);
}

static void stop_writes(void *context)
{
	const struct device *device = context;

	uart_irq_tx_disable(device);
}

static void cdc_callback(
	const struct device *device,
	void *user_data
)
{
	k_spinlock_key_t key;

	ARG_UNUSED(user_data);
	key = k_spin_lock(&tx_lock);
	if (device != cdc || uart_irq_update(device) <= 0) {
		dmh_cdc_tx_driver_fault(&tx);
	} else {
		while (uart_irq_is_pending(device) > 0) {
			if (uart_irq_rx_ready(device) > 0 &&
			    !dutchmate_command_runtime_on_cdc_rx_ready(device)) {
				break;
			}
			if (uart_irq_tx_ready(device) > 0) {
				dmh_cdc_tx_on_writable(&tx, time_us_64());
			}
			if (uart_irq_update(device) <= 0) {
				dmh_cdc_tx_driver_fault(&tx);
				break;
			}
		}
	}
	k_spin_unlock(&tx_lock, key);
}

int dutchmate_cdc_tx_initialize(const struct device *cdc_device)
{
	const struct dmh_cdc_tx_port port = {
		.context = (void *)cdc_device,
		.write = write_bytes,
		.stop = stop_writes,
	};
	int result;

	if (cdc_device == NULL || !device_is_ready(cdc_device) ||
	    !atomic_cas(&initialized, 0, 1)) {
		return -EINVAL;
	}
	cdc = cdc_device;
	dmh_cdc_tx_init(&tx, &port);
	result = uart_irq_callback_user_data_set(cdc, cdc_callback, NULL);
	if (result != 0) {
		atomic_clear(&initialized);
		cdc = NULL;
		return result;
	}
	return 0;
}

enum dmh_cdc_tx_result dutchmate_cdc_tx_start(
	const uint8_t *frame,
	size_t length
)
{
	enum dmh_cdc_tx_result result;
	k_spinlock_key_t key;

	if (atomic_get(&initialized) == 0) {
		return DMH_CDC_TX_HARDWARE_FAULT;
	}
	key = k_spin_lock(&tx_lock);
	result = dmh_cdc_tx_start(
		&tx,
		frame,
		length,
		time_us_64(),
		DUTCHMATE_CDC_TX_NO_PROGRESS_TIMEOUT_US
	);
	k_spin_unlock(&tx_lock, key);
	if (result == DMH_CDC_TX_PENDING) {
		uart_irq_tx_enable(cdc);
	}
	return result;
}

enum dmh_cdc_tx_result dutchmate_cdc_tx_poll(void)
{
	enum dmh_cdc_tx_result result;
	k_spinlock_key_t key;

	key = k_spin_lock(&tx_lock);
	result = dmh_cdc_tx_poll(&tx, time_us_64());
	k_spin_unlock(&tx_lock, key);
	return result;
}

void dutchmate_cdc_tx_cancel(void)
{
	k_spinlock_key_t key;

	if (atomic_get(&initialized) == 0) {
		return;
	}
	key = k_spin_lock(&tx_lock);
	dmh_cdc_tx_cancel(&tx);
	k_spin_unlock(&tx_lock, key);
}
