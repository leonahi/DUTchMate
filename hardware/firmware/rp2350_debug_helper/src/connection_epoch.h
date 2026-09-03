#ifndef DUTCHMATE_CONNECTION_EPOCH_H
#define DUTCHMATE_CONNECTION_EPOCH_H

#include <stdbool.h>

enum dmh_epoch_transition {
	DMH_EPOCH_NO_CHANGE = 0,
	DMH_EPOCH_STARTED,
	DMH_EPOCH_ENDED,
};

struct dmh_connection_epoch {
	bool active;
};

void dmh_connection_epoch_init(struct dmh_connection_epoch *epoch);
enum dmh_epoch_transition dmh_connection_epoch_update(
	struct dmh_connection_epoch *epoch,
	bool dtr_asserted
);

#endif
