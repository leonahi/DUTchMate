#include "hello.h"

#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	char frame[DMH_HELLO_FRAME_CAPACITY];
	size_t frame_length;

	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (dmh_hello_encode(argv[1], frame, sizeof(frame), &frame_length) != 0) {
		return 2;
	}

	if (fwrite(frame, 1U, frame_length, stdout) != frame_length) {
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}
