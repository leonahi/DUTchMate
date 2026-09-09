#include "connection_epoch.h"

void dmh_connection_epoch_init(struct dmh_connection_epoch *epoch)
{
	epoch->active = false;
	epoch->dtr_assertion_pending = false;
	epoch->dtr_asserted_since_us = 0U;
}

enum dmh_epoch_transition dmh_connection_epoch_update(
	struct dmh_connection_epoch *epoch,
	bool dtr_asserted,
	uint64_t now_us
)
{
	if (!dtr_asserted) {
		epoch->dtr_assertion_pending = false;
		epoch->dtr_asserted_since_us = 0U;
		if (epoch->active) {
			epoch->active = false;
			return DMH_EPOCH_ENDED;
		}
		return DMH_EPOCH_NO_CHANGE;
	}

	if (epoch->active) {
		return DMH_EPOCH_NO_CHANGE;
	}
	if (!epoch->dtr_assertion_pending) {
		epoch->dtr_assertion_pending = true;
		epoch->dtr_asserted_since_us = now_us;
		return DMH_EPOCH_NO_CHANGE;
	}
	if (now_us - epoch->dtr_asserted_since_us < DMH_EPOCH_DTR_STABLE_US) {
		return DMH_EPOCH_NO_CHANGE;
	}

	epoch->active = true;
	epoch->dtr_assertion_pending = false;
	return DMH_EPOCH_STARTED;
}
