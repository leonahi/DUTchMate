#ifndef DUTCHMATE_PLATFORM_IO_H
#define DUTCHMATE_PLATFORM_IO_H

#include "control_state.h"

#include <stdbool.h>
#include <stddef.h>

int dutchmate_platform_io_initialize_safe(void);
int dutchmate_platform_io_force_safe(void);
int dutchmate_platform_uart_interface_set(bool active);
struct dmh_control_port dutchmate_platform_control_port(void);

#ifdef CONFIG_DUTCHMATE_SENSE_PAD_REPORT
int dutchmate_platform_sense_probe_firmware(char *output, size_t capacity);
#endif

#endif
