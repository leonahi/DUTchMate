#include "vio_sense.h"

#include <errno.h>
#include <stddef.h>

static void stage(struct dmh_vio_sense *state, enum dmh_vio_status status,
		  uint16_t raw, uint64_t timestamp_us, uint64_t observation_sequence)
{
	state->observation = (struct dmh_vio_observation) {
		.timestamp_us = timestamp_us, .observation_sequence = observation_sequence, .status = status, .adc_raw = raw,
		.voltage_mv = (uint16_t)(((uint64_t)raw * state->reference_mv * 2U + 2048U) / 4096U),
		.reference_mv = state->reference_mv, .reference_measured = state->reference_measured,
	};
	state->pending = true;
}

void dmh_vio_sense_init(struct dmh_vio_sense *state, const struct dmh_vio_adc_port *adc,
			uint16_t reference_mv, bool reference_measured)
{
	*state = (struct dmh_vio_sense) {
		.adc = *adc, .reference_mv = reference_mv, .reference_measured = reference_measured,
	};
}

int dmh_vio_sense_configure(struct dmh_vio_sense *state, bool enabled, uint64_t now_us)
{
	if (!enabled) {
		dmh_vio_sense_end_epoch(state);
		return 0;
	}
	if (state->adc.start == NULL || state->adc.poll == NULL ||
	    state->reference_mv < 2500U || state->reference_mv > 3600U) {
		return -EINVAL;
	}
	if (!state->enabled) {
		state->enabled = true;
		state->next_due_us = now_us;
	}
	return 0;
}

void dmh_vio_sense_end_epoch(struct dmh_vio_sense *state)
{
	state->enabled = false;
	state->pending = false;
	/* The driver still owns any outstanding buffer across a logical epoch end. */
	state->discard_completion = state->in_flight;
}

void dmh_vio_sense_poll(struct dmh_vio_sense *state, uint64_t now_us,
			 uint64_t observation_sequence)
{
	if (state->in_flight) {
		uint16_t raw = 0U;
		uint64_t completed_us = 0U;
		uint64_t completed_sequence = 0U;
		enum dmh_vio_adc_result result = state->adc.poll(state->adc.context, &raw, &completed_us, &completed_sequence);

		if (result != DMH_VIO_ADC_PENDING) {
			state->in_flight = false;
			if (!state->discard_completion && state->enabled) {
				if (result != DMH_VIO_ADC_COMPLETE || completed_us < state->started_us ||
				    completed_us - state->started_us > DMH_VIO_DEADLINE_US || raw > 4095U) {
					stage(state, DMH_VIO_ERROR, 0U, now_us, observation_sequence);
				} else {
					stage(state, raw == 4095U ? DMH_VIO_SATURATED : DMH_VIO_OK,
					      raw, completed_us, completed_sequence);
				}
			}
			state->discard_completion = false;
		} else if (!state->discard_completion && now_us - state->started_us >= DMH_VIO_DEADLINE_US) {
			state->discard_completion = true;
			if (state->enabled) stage(state, DMH_VIO_ERROR, 0U, now_us, observation_sequence);
		}
	}
	if (!state->enabled || now_us < state->next_due_us) return;
	state->next_due_us += ((now_us - state->next_due_us) / DMH_VIO_INTERVAL_US + 1U) * DMH_VIO_INTERVAL_US;
	if (state->in_flight || state->adc.start(state->adc.context) != 0) {
		stage(state, DMH_VIO_ERROR, 0U, now_us, observation_sequence);
		return;
	}
	state->started_us = now_us;
	state->in_flight = true;
}

bool dmh_vio_sense_take_observation(struct dmh_vio_sense *state, struct dmh_vio_observation *out)
{
	if (!state->pending) return false;
	*out = state->observation;
	state->pending = false;
	return true;
}
