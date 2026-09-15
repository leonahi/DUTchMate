#include "platform_io.h"
#include "uart_rx.h"
#include "uart_tx.h"
#include "usb_connection.h"

#include <zephyr/kernel.h>

int main(void)
{
	if (IS_ENABLED(CONFIG_DUTCHMATE_STACK_PROBE)) {
		(void)k_thread_name_set(k_current_get(), "main");
	}
	int result = dutchmate_platform_io_initialize_safe();

	if (result != 0) {
		return result;
	}
	result = dutchmate_uart_rx_initialize();
	if (result != 0) {
		(void)dutchmate_platform_io_force_safe();
		return result;
	}
	result = dutchmate_uart_tx_initialize();
	if (result != 0) {
		(void)dutchmate_platform_io_force_safe();
		return result;
	}

	return dutchmate_usb_connection_run();
}
