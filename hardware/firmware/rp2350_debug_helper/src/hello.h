#ifndef DUTCHMATE_HELLO_H
#define DUTCHMATE_HELLO_H

#include <stddef.h>

#define DMH_HELLO_FRAME_CAPACITY 256U

int dmh_hello_encode(
	const char *firmware,
	char *output,
	size_t output_capacity,
	size_t *output_length
);

#endif
