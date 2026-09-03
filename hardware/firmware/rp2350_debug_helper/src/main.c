#include "platform_io.h"
#include "uart_rx.h"
#include "usb_connection.h"

int main(void)
{
	int result = dutchmate_platform_io_initialize_safe();

	if (result != 0) {
		return result;
	}
	result = dutchmate_uart_rx_initialize();
	if (result != 0) {
		(void)dutchmate_platform_io_force_safe();
		return result;
	}

	return dutchmate_usb_connection_run();
}
