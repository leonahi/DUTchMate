#include "connection_epoch.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
	struct dmh_connection_epoch epoch;
	const char *states;
	size_t index;

	if (argc != 2) {
		return EXIT_FAILURE;
	}

	dmh_connection_epoch_init(&epoch);
	states = argv[1];
	for (index = 0U; states[index] != '\0'; index++) {
		enum dmh_epoch_transition transition;

		if (states[index] != '0' && states[index] != '1') {
			return EXIT_FAILURE;
		}
		transition = dmh_connection_epoch_update(&epoch, states[index] == '1');
		if (transition == DMH_EPOCH_STARTED) {
			(void)fputc('S', stdout);
		} else if (transition == DMH_EPOCH_ENDED) {
			(void)fputc('E', stdout);
		} else {
			(void)fputc('-', stdout);
		}
	}

	return EXIT_SUCCESS;
}
