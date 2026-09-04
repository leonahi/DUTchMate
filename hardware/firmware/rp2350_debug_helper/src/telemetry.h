#ifndef DUTCHMATE_TELEMETRY_H
#define DUTCHMATE_TELEMETRY_H

#include "uart_rx_ring.h"

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DMH_TELEMETRY_FRAME_CAPACITY 256U
#define DMH_BUFFER_STATUS_INTERVAL_US 1000000ULL

struct dmh_buffer_status_observation {
	uint64_t timestamp_us;
	uint64_t observation_sequence;
	struct dmh_uart_rx_snapshot snapshot;
};

struct dmh_telemetry_schedule {
	uint64_t next_status_due_us;
	struct dmh_buffer_status_observation pending_status;
	bool active;
	bool status_pending;
};

int dmh_buffer_overflow_encode(
	uint8_t channel,
	uint64_t timestamp_us,
	uint64_t dropped_bytes,
	char *output,
	size_t output_capacity,
	size_t *output_length
);
int dmh_buffer_status_encode(
	uint64_t timestamp_us,
	const struct dmh_uart_rx_snapshot *snapshot,
	char *output,
	size_t output_capacity,
	size_t *output_length
);

void dmh_telemetry_schedule_init(struct dmh_telemetry_schedule *schedule);
void dmh_telemetry_schedule_start(
	struct dmh_telemetry_schedule *schedule,
	uint64_t now_us
);
void dmh_telemetry_schedule_stop(struct dmh_telemetry_schedule *schedule);
bool dmh_telemetry_status_due(
	const struct dmh_telemetry_schedule *schedule,
	uint64_t now_us
);
void dmh_telemetry_schedule_stage_status(
	struct dmh_telemetry_schedule *schedule,
	const struct dmh_buffer_status_observation *observation
);
const struct dmh_buffer_status_observation *dmh_telemetry_pending_status(
	const struct dmh_telemetry_schedule *schedule
);
void dmh_telemetry_schedule_status_sent(struct dmh_telemetry_schedule *schedule);

#endif
