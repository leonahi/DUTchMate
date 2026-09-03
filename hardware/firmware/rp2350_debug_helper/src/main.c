#include "platform_io.h"
#include "usb_connection.h"

int main(void)
{
	int result = dutchmate_platform_io_initialize_safe();

	if (result != 0) {
		return result;
	}

	return dutchmate_usb_connection_run();
}
