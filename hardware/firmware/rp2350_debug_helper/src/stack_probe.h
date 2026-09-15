#ifndef DUTCHMATE_STACK_PROBE_H
#define DUTCHMATE_STACK_PROBE_H

#include <stddef.h>

void dutchmate_stack_probe_epoch_ended(void);
int dutchmate_stack_probe_firmware(char *output, size_t capacity);
void dutchmate_stack_probe_hello_sent(void);

#endif
