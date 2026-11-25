#ifndef DUTCHMATE_VIO_SENSE_H
#define DUTCHMATE_VIO_SENSE_H

#include <stdbool.h>
#include <stdint.h>

#define DMH_VIO_INTERVAL_US 1000000ULL
#define DMH_VIO_DEADLINE_US 20000ULL

enum dmh_vio_adc_result { DMH_VIO_ADC_PENDING, DMH_VIO_ADC_COMPLETE, DMH_VIO_ADC_ERROR };
enum dmh_vio_status { DMH_VIO_OK, DMH_VIO_ERROR, DMH_VIO_SATURATED };

struct dmh_vio_adc_port {
	void *context;
	int (*start)(void *context);
	enum dmh_vio_adc_result (*poll)(void *context, uint16_t *raw, uint64_t *completed_us,
				       uint64_t *observation_sequence);
};

struct dmh_vio_observation {
	uint64_t timestamp_us;
	uint64_t observation_sequence;
	enum dmh_vio_status status;
	uint16_t adc_raw;
	uint16_t voltage_mv;
	uint16_t reference_mv;
	bool reference_measured;
};

struct dmh_vio_sense {
	struct dmh_vio_adc_port adc;
	struct dmh_vio_observation observation;
	uint64_t next_due_us;
	uint64_t started_us;
	uint16_t reference_mv;
	bool reference_measured;
	bool enabled;
	bool in_flight;
	bool discard_completion;
	bool pending;
};

void dmh_vio_sense_init(struct dmh_vio_sense *state, const struct dmh_vio_adc_port *adc,
			uint16_t reference_mv, bool reference_measured);
int dmh_vio_sense_configure(struct dmh_vio_sense *state, bool enabled, uint64_t now_us);
void dmh_vio_sense_poll(struct dmh_vio_sense *state, uint64_t now_us,
			 uint64_t observation_sequence);
bool dmh_vio_sense_take_observation(struct dmh_vio_sense *state, struct dmh_vio_observation *out);
void dmh_vio_sense_end_epoch(struct dmh_vio_sense *state);

#endif
