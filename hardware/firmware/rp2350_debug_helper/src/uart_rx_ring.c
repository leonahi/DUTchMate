#include "uart_rx_ring.h"

#include <errno.h>
#include <limits.h>
#include <string.h>

_Static_assert(
	sizeof(struct dmh_uart_rx_descriptor) == 16U,
	"Unexpected UART RX descriptor size"
);

static uint64_t saturating_add_u64(uint64_t value, uint64_t increment)
{
	return increment > UINT64_MAX - value ? UINT64_MAX : value + increment;
}

static struct dmh_uart_rx_descriptor *oldest_descriptor(
	struct dmh_uart_rx_ring *ring
)
{
	return &ring->descriptors[ring->descriptor_head];
}

static void remove_empty_oldest_descriptor(struct dmh_uart_rx_ring *ring)
{
	ring->descriptor_head =
		(ring->descriptor_head + 1U) % DMH_UART_RX_DESCRIPTOR_CAPACITY;
	ring->descriptor_count--;
}

static void drop_oldest_bytes(struct dmh_uart_rx_ring *ring, size_t length)
{
	while (length > 0U) {
		struct dmh_uart_rx_descriptor *descriptor = oldest_descriptor(ring);
		size_t dropped = length < descriptor->length ? length : descriptor->length;

		ring->read_index =
			(ring->read_index + dropped) % DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES;
		ring->used_bytes -= dropped;
		descriptor->length -= (uint32_t)dropped;
		length -= dropped;
		if (descriptor->length == 0U) {
			remove_empty_oldest_descriptor(ring);
		}
	}
}

static void record_drop(
	struct dmh_uart_rx_ring *ring,
	size_t dropped,
	uint64_t timestamp_us
)
{
	if (dropped == 0U) {
		return;
	}

	ring->dropped_bytes_total = saturating_add_u64(
		ring->dropped_bytes_total,
		(uint64_t)dropped
	);
	if (!ring->episode_active) {
		ring->episode_active = true;
		ring->episode_first_drop_timestamp_us = timestamp_us;
		ring->episode_dropped_bytes = 0U;
		ring->overflow_events = saturating_add_u64(ring->overflow_events, 1U);
	}
	ring->episode_dropped_bytes = saturating_add_u64(
		ring->episode_dropped_bytes,
		(uint64_t)dropped
	);
}

static void copy_into_ring(
	struct dmh_uart_rx_ring *ring,
	const uint8_t *data,
	size_t length
)
{
	size_t write_index =
		(ring->read_index + ring->used_bytes) %
		DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES;
	size_t first_length = DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - write_index;

	if (first_length > length) {
		first_length = length;
	}
	memcpy(&ring->bytes[write_index], data, first_length);
	memcpy(ring->bytes, data + first_length, length - first_length);
}

static void append_descriptor(
	struct dmh_uart_rx_ring *ring,
	uint8_t channel,
	uint64_t timestamp_us,
	size_t length
)
{
	size_t index =
		(ring->descriptor_head + ring->descriptor_count) %
		DMH_UART_RX_DESCRIPTOR_CAPACITY;

	ring->descriptors[index].timestamp_us = timestamp_us;
	ring->descriptors[index].length = (uint32_t)length;
	ring->descriptors[index].channel = channel;
	ring->descriptor_count++;
}

void dmh_uart_rx_ring_init(struct dmh_uart_rx_ring *ring)
{
	memset(ring, 0, sizeof(*ring));
}

int dmh_uart_rx_ring_push(
	struct dmh_uart_rx_ring *ring,
	uint8_t channel,
	uint64_t timestamp_us,
	const uint8_t *data,
	size_t length
)
{
	size_t retained_length;
	size_t input_drop;
	size_t retained_drop = 0U;

	if (ring == NULL || (data == NULL && length > 0U)) {
		return -EINVAL;
	}
	if (length == 0U) {
		return 0;
	}

	retained_length = length;
	if (retained_length > DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES) {
		retained_length = DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES;
	}
	input_drop = length - retained_length;

	if (ring->descriptor_count == DMH_UART_RX_DESCRIPTOR_CAPACITY) {
		retained_drop = oldest_descriptor(ring)->length;
		drop_oldest_bytes(ring, retained_drop);
	}
	if (ring->used_bytes > DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - retained_length) {
		size_t byte_space_drop =
			ring->used_bytes -
			(DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - retained_length);

		drop_oldest_bytes(ring, byte_space_drop);
		retained_drop += byte_space_drop;
	}

	record_drop(ring, input_drop, timestamp_us);
	record_drop(ring, retained_drop, timestamp_us);
	data += input_drop;
	copy_into_ring(ring, data, retained_length);
	append_descriptor(ring, channel, timestamp_us, retained_length);
	ring->used_bytes += retained_length;
	if (ring->used_bytes > ring->high_water_bytes) {
		ring->high_water_bytes = ring->used_bytes;
	}

	return 0;
}

int dmh_uart_rx_ring_take(
	struct dmh_uart_rx_ring *ring,
	uint8_t *output,
	size_t output_capacity,
	struct dmh_uart_rx_chunk *chunk
)
{
	struct dmh_uart_rx_descriptor *descriptor;
	size_t length;
	size_t first_length;

	if (ring == NULL || output == NULL || chunk == NULL) {
		return -EINVAL;
	}
	chunk->length = 0U;
	if (output_capacity == 0U || ring->descriptor_count == 0U) {
		return 0;
	}

	descriptor = oldest_descriptor(ring);
	length = output_capacity < descriptor->length ?
		output_capacity : descriptor->length;
	first_length = DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - ring->read_index;
	if (first_length > length) {
		first_length = length;
	}
	memcpy(output, &ring->bytes[ring->read_index], first_length);
	memcpy(output + first_length, ring->bytes, length - first_length);

	chunk->timestamp_us = descriptor->timestamp_us;
	chunk->channel = descriptor->channel;
	chunk->length = length;
	drop_oldest_bytes(ring, length);
	return 0;
}

void dmh_uart_rx_ring_snapshot(
	const struct dmh_uart_rx_ring *ring,
	struct dmh_uart_rx_snapshot *snapshot
)
{
	snapshot->capacity_bytes = DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES;
	snapshot->used_bytes = ring->used_bytes;
	snapshot->high_water_bytes = ring->high_water_bytes;
	snapshot->dropped_bytes_total = ring->dropped_bytes_total;
	snapshot->overflow_events = ring->overflow_events;
}

bool dmh_uart_rx_ring_claim_overflow(
	struct dmh_uart_rx_ring *ring,
	struct dmh_uart_rx_overflow *overflow
)
{
	if (ring == NULL || overflow == NULL || !ring->episode_active) {
		return false;
	}

	overflow->first_drop_timestamp_us = ring->episode_first_drop_timestamp_us;
	overflow->dropped_bytes = ring->episode_dropped_bytes;
	ring->episode_active = false;
	ring->episode_dropped_bytes = 0U;
	return true;
}

void dmh_uart_rx_ring_discard_retained(struct dmh_uart_rx_ring *ring)
{
	ring->read_index = 0U;
	ring->used_bytes = 0U;
	ring->descriptor_head = 0U;
	ring->descriptor_count = 0U;
	ring->episode_active = false;
	ring->episode_dropped_bytes = 0U;
}
