#include "vio_sense.h"

#include <assert.h>
#include <errno.h>
#include <string.h>

struct fake_adc {
	unsigned int starts;
	int start_error;
	enum dmh_vio_adc_result result;
	uint16_t raw;
	uint64_t completed_us;
};

static int start(void *context)
{
	struct fake_adc *adc = context;
	adc->starts++;
	return adc->start_error;
}

static enum dmh_vio_adc_result poll(void *context, uint16_t *raw, uint64_t *done, uint64_t *sequence)
{
	struct fake_adc *adc = context;
	*raw = adc->raw;
	*done = adc->completed_us;
	*sequence = 44U;
	return adc->result;
}

int main(int argc, char **argv)
{
	struct fake_adc adc = {0};
	struct dmh_vio_adc_port port = {.context = &adc, .start = start, .poll = poll};
	struct dmh_vio_sense state;
	struct dmh_vio_observation observation;
	assert(argc == 2);
	dmh_vio_sense_init(&state, &port, 3300, false);
	dmh_vio_sense_poll(&state, 0, 17U);
	assert(adc.starts == 0);
	assert(dmh_vio_sense_configure(&state, true, 0) == 0);
	if (!strcmp(argv[1], "start-error")) adc.start_error = -EIO;
	dmh_vio_sense_poll(&state, 0, 17U);
	assert(adc.starts == 1);
	if (!strcmp(argv[1], "start-error")) {
		assert(dmh_vio_sense_take_observation(&state, &observation));
		assert(observation.status == DMH_VIO_ERROR);
		dmh_vio_sense_poll(&state, 1, 17U);
		assert(adc.starts == 1);
		return 0;
	}
	if (!strcmp(argv[1], "timeout") || !strcmp(argv[1], "epoch") ||
	    !strcmp(argv[1], "disable")) {
		dmh_vio_sense_poll(&state, 20000, 17U);
		assert(dmh_vio_sense_take_observation(&state, &observation));
		assert(observation.status == DMH_VIO_ERROR);
		if (!strcmp(argv[1], "epoch")) dmh_vio_sense_end_epoch(&state);
		if (!strcmp(argv[1], "disable")) {
			assert(dmh_vio_sense_configure(&state, false, 20001) == 0);
		}
		assert(dmh_vio_sense_configure(&state, true, 30000) == 0);
		dmh_vio_sense_poll(&state, 1000000, 17U);
		assert(adc.starts == 1); /* Timeout/re-enable never reuses driver buffer. */
		adc.result = DMH_VIO_ADC_COMPLETE;
		adc.raw = 2048;
		adc.completed_us = 40000;
		dmh_vio_sense_poll(&state, 1000001, 17U);
		if (dmh_vio_sense_take_observation(&state, &observation)) {
			assert(observation.status == DMH_VIO_ERROR);
		}
		adc.result = DMH_VIO_ADC_PENDING;
		dmh_vio_sense_poll(&state, 2000000, 17U);
		assert(adc.starts == 2);
		return 0;
	}
	adc.result = !strcmp(argv[1], "read-error") ? DMH_VIO_ADC_ERROR : DMH_VIO_ADC_COMPLETE;
	adc.raw = !strcmp(argv[1], "zero") ? 0 : !strcmp(argv[1], "saturated") ? 4095 : 2048;
	adc.completed_us = !strcmp(argv[1], "late") ? 20001 : 20000;
	dmh_vio_sense_poll(&state, 30000, 17U); /* USB polls late; ADC completion can be on time. */
	assert(dmh_vio_sense_take_observation(&state, &observation));
	if (!strcmp(argv[1], "late") || !strcmp(argv[1], "read-error")) {
		assert(observation.status == DMH_VIO_ERROR);
	} else if (!strcmp(argv[1], "saturated")) {
		assert(observation.status == DMH_VIO_SATURATED);
	} else {
		assert(observation.status == DMH_VIO_OK);
		assert(observation.voltage_mv == (adc.raw == 0 ? 0 : 3300));
		assert(observation.timestamp_us == 20000);
	}
	assert(!dmh_vio_sense_take_observation(&state, &observation));
	assert(dmh_vio_sense_configure(&state, true, 50000) == 0); /* Idempotent. */
	adc.result = DMH_VIO_ADC_PENDING;
	dmh_vio_sense_poll(&state, 999999, 17U);
	assert(adc.starts == 1);
	dmh_vio_sense_poll(&state, 5000000, 17U); /* Skip missed slots; only one new conversion. */
	assert(adc.starts == 2);
	adc.result = DMH_VIO_ADC_COMPLETE;
	adc.completed_us = 5000001;
	adc.raw = 3072;
	dmh_vio_sense_poll(&state, 5000001, 17U);
	assert(dmh_vio_sense_take_observation(&state, &observation));
	assert(observation.voltage_mv == 4950);
	return 0;
}
