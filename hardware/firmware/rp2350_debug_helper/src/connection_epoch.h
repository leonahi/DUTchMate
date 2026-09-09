#ifndef DUTCHMATE_CONNECTION_EPOCH_H
#define DUTCHMATE_CONNECTION_EPOCH_H

#include <stdbool.h>
#include <stdint.h>

#define DMH_EPOCH_DTR_STABLE_US 100000ULL

enum dmh_epoch_transition {
	DMH_EPOCH_NO_CHANGE = 0,
	DMH_EPOCH_STARTED,
	DMH_EPOCH_ENDED,
};

struct dmh_connection_epoch {
	bool active;
	bool dtr_assertion_pending;
	uint64_t dtr_asserted_since_us;
};

void dmh_connection_epoch_init(struct dmh_connection_epoch *epoch);
enum dmh_epoch_transition dmh_connection_epoch_update(
	struct dmh_connection_epoch *epoch,
	bool dtr_asserted,
	uint64_t now_us
);

#endif
