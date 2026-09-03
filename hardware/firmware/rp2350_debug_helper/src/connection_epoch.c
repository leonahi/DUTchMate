#include "connection_epoch.h"

void dmh_connection_epoch_init(struct dmh_connection_epoch *epoch)
{
	epoch->active = false;
}

enum dmh_epoch_transition dmh_connection_epoch_update(
	struct dmh_connection_epoch *epoch,
	bool dtr_asserted
)
{
	if (dtr_asserted == epoch->active) {
		return DMH_EPOCH_NO_CHANGE;
	}

	epoch->active = dtr_asserted;
	return dtr_asserted ? DMH_EPOCH_STARTED : DMH_EPOCH_ENDED;
}
