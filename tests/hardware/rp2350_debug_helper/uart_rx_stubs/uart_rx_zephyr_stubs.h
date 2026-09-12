#ifndef DUTCHMATE_TEST_UART_RX_ZEPHYR_STUBS_H
#define DUTCHMATE_TEST_UART_RX_ZEPHYR_STUBS_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct device {
	int unused;
};

extern const struct device fake_uart_device;

#define DT_NODELABEL(name) 0
#define DEVICE_DT_GET(node_id) (&fake_uart_device)
#define ARG_UNUSED(argument) ((void)(argument))

struct uart_config {
	uint32_t baudrate;
	int parity;
	int stop_bits;
	int data_bits;
	int flow_ctrl;
};

#define UART_CFG_PARITY_NONE 0
#define UART_CFG_STOP_BITS_1 0
#define UART_CFG_DATA_BITS_8 8
#define UART_CFG_FLOW_CTRL_NONE 0
#define UART_BREAK (1 << 3)

typedef void (*uart_irq_callback_user_data_t)(const struct device *, void *);

bool device_is_ready(const struct device *device);
int uart_configure(const struct device *device, const struct uart_config *config);
int uart_irq_callback_user_data_set(
	const struct device *device,
	uart_irq_callback_user_data_t callback,
	void *user_data
);
int uart_irq_update(const struct device *device);
int uart_err_check(const struct device *device);
int uart_irq_rx_ready(const struct device *device);
int uart_fifo_read(const struct device *device, uint8_t *data, int length);
void uart_irq_rx_enable(const struct device *device);
void uart_irq_rx_disable(const struct device *device);
void uart_irq_err_enable(const struct device *device);
void uart_irq_err_disable(const struct device *device);

typedef int k_spinlock_key_t;

struct k_spinlock {
	int unused;
};

static inline k_spinlock_key_t k_spin_lock(struct k_spinlock *lock)
{
	(void)lock;
	return 0;
}

static inline void k_spin_unlock(
	struct k_spinlock *lock,
	k_spinlock_key_t key
)
{
	(void)lock;
	(void)key;
}

#define K_SPINLOCK(lock) for (int dmh_once = ((void)(lock), 1); dmh_once; dmh_once = 0)

uint64_t time_us_64(void);

#endif
