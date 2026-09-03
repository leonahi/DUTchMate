#include "platform_io.h"

#include <zephyr/kernel.h>

int main(void)
{
	int result = dutchmate_platform_io_initialize_safe();

	if (result != 0) {
		return result;
	}

	k_sleep(K_FOREVER);
	return 0;
}
