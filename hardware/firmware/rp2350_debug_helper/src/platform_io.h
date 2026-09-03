#ifndef DUTCHMATE_PLATFORM_IO_H
#define DUTCHMATE_PLATFORM_IO_H

#include <stdbool.h>

int dutchmate_platform_io_initialize_safe(void);
int dutchmate_platform_io_force_safe(void);
int dutchmate_platform_uart_interface_set(bool active);

#endif
