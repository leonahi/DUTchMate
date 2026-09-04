#include "telemetry.h"

#include <errno.h>
#include <string.h>

struct frame_writer {
	char *output;
	size_t capacity;
	size_t length;
};

static bool append_bytes(
	struct frame_writer *writer,
	const char *bytes,
	size_t length
)
{
	if (length > writer->capacity - writer->length) {
		return false;
	}
	memcpy(writer->output + writer->length, bytes, length);
	writer->length += length;
	return true;
}

static bool append_literal(struct frame_writer *writer, const char *literal)
{
	return append_bytes(writer, literal, strlen(literal));
}

static bool append_decimal(struct frame_writer *writer, uint64_t value)
{
	char digits[20];
	size_t index = sizeof(digits);

	do {
		index--;
		digits[index] = (char)('0' + value % 10U);
		value /= 10U;
	} while (value > 0U);
	return append_bytes(writer, &digits[index], sizeof(digits) - index);
}

int dmh_buffer_overflow_encode(
	uint8_t channel,
	uint64_t timestamp_us,
	uint64_t dropped_bytes,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	struct frame_writer writer = {
		.output = output,
		.capacity = output_capacity,
	};

	if (output == NULL || output_length == NULL || dropped_bytes == 0U) {
		return -EINVAL;
	}
	if (!append_literal(&writer, "{\"type\":\"buffer_overflow\",\"channel\":") ||
	    !append_decimal(&writer, channel) ||
	    !append_literal(&writer, ",\"timestamp_us\":") ||
	    !append_decimal(&writer, timestamp_us) ||
	    !append_literal(&writer, ",\"dropped_bytes\":") ||
	    !append_decimal(&writer, dropped_bytes) ||
	    !append_literal(&writer, "}\n")) {
		return -ENOSPC;
	}
	*output_length = writer.length;
	return 0;
}

int dmh_buffer_status_encode(
	uint64_t timestamp_us,
	const struct dmh_uart_rx_snapshot *snapshot,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	struct frame_writer writer = {
		.output = output,
		.capacity = output_capacity,
	};

	if (snapshot == NULL || output == NULL || output_length == NULL ||
	    snapshot->capacity_bytes == 0U ||
	    snapshot->used_bytes > snapshot->capacity_bytes ||
	    snapshot->high_water_bytes < snapshot->used_bytes ||
	    snapshot->high_water_bytes > snapshot->capacity_bytes) {
		return -EINVAL;
	}
	if (!append_literal(&writer, "{\"type\":\"buffer_status\",\"timestamp_us\":") ||
	    !append_decimal(&writer, timestamp_us) ||
	    !append_literal(&writer, ",\"uart_rx_size_bytes\":") ||
	    !append_decimal(&writer, snapshot->capacity_bytes) ||
	    !append_literal(&writer, ",\"uart_rx_used_bytes\":") ||
	    !append_decimal(&writer, snapshot->used_bytes) ||
	    !append_literal(&writer, ",\"uart_rx_high_water_bytes\":") ||
	    !append_decimal(&writer, snapshot->high_water_bytes) ||
	    !append_literal(&writer, ",\"dropped_bytes_total\":") ||
	    !append_decimal(&writer, snapshot->dropped_bytes_total) ||
	    !append_literal(&writer, ",\"overflow_events\":") ||
	    !append_decimal(&writer, snapshot->overflow_events) ||
	    !append_literal(&writer, "}\n")) {
		return -ENOSPC;
	}
	*output_length = writer.length;
	return 0;
}

void dmh_telemetry_schedule_init(struct dmh_telemetry_schedule *schedule)
{
	memset(schedule, 0, sizeof(*schedule));
}

void dmh_telemetry_schedule_start(
	struct dmh_telemetry_schedule *schedule,
	uint64_t now_us
)
{
	schedule->active = true;
	schedule->status_pending = false;
	schedule->next_status_due_us = now_us + DMH_BUFFER_STATUS_INTERVAL_US;
}

void dmh_telemetry_schedule_stop(struct dmh_telemetry_schedule *schedule)
{
	schedule->active = false;
	schedule->status_pending = false;
}

bool dmh_telemetry_status_due(
	const struct dmh_telemetry_schedule *schedule,
	uint64_t now_us
)
{
	return schedule->active && now_us >= schedule->next_status_due_us;
}

void dmh_telemetry_schedule_stage_status(
	struct dmh_telemetry_schedule *schedule,
	const struct dmh_buffer_status_observation *observation
)
{
	schedule->pending_status = *observation;
	schedule->status_pending = true;
	schedule->next_status_due_us =
		observation->timestamp_us + DMH_BUFFER_STATUS_INTERVAL_US;
}

const struct dmh_buffer_status_observation *dmh_telemetry_pending_status(
	const struct dmh_telemetry_schedule *schedule
)
{
	return schedule->status_pending ? &schedule->pending_status : NULL;
}

void dmh_telemetry_schedule_status_sent(struct dmh_telemetry_schedule *schedule)
{
	schedule->status_pending = false;
}
