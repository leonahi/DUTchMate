#ifndef DUTCHMATE_UART_RX_RING_H
#define DUTCHMATE_UART_RX_RING_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

#define DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES (32U * 1024U)
#define DMH_UART_RX_DESCRIPTOR_CAPACITY 512U

/* Caller serializes operations; the Zephyr adapter supplies the spinlock. */

enum dmh_uart_rx_observation_kind {
	DMH_UART_RX_OBSERVATION_NONE = 0,
	DMH_UART_RX_OBSERVATION_CHUNK,
	DMH_UART_RX_OBSERVATION_OVERFLOW,
};

struct dmh_uart_rx_descriptor {
	uint64_t timestamp_us;
	uint64_t observation_sequence;
	uint32_t length;
	uint8_t channel;
};

struct dmh_uart_rx_snapshot {
	size_t capacity_bytes;
	size_t used_bytes;
	size_t high_water_bytes;
	uint64_t dropped_bytes_total;
	uint64_t overflow_events;
};

struct dmh_uart_rx_overflow {
	uint64_t first_drop_timestamp_us;
	uint64_t dropped_bytes;
	uint64_t observation_sequence;
};

struct dmh_uart_rx_chunk {
	uint64_t timestamp_us;
	uint64_t observation_sequence;
	size_t length;
	uint8_t channel;
};

struct dmh_uart_rx_ring {
	uint8_t bytes[DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES];
	struct dmh_uart_rx_descriptor descriptors[DMH_UART_RX_DESCRIPTOR_CAPACITY];
	size_t read_index;
	size_t used_bytes;
	size_t high_water_bytes;
	size_t descriptor_head;
	size_t descriptor_count;
	uint64_t dropped_bytes_total;
	uint64_t overflow_events;
	uint64_t episode_first_drop_timestamp_us;
	uint64_t episode_dropped_bytes;
	uint64_t episode_observation_sequence;
	uint64_t next_observation_sequence;
	bool episode_active;
};

void dmh_uart_rx_ring_init(struct dmh_uart_rx_ring *ring);
/* One push represents one UART RX callback and its sampled timestamp. */
int dmh_uart_rx_ring_push(
	struct dmh_uart_rx_ring *ring,
	uint8_t channel,
	uint64_t timestamp_us,
	const uint8_t *data,
	size_t length
);
/*
 * Stage at most one timestamp descriptor, removing only copied bytes.
 * Returns -EAGAIN when an earlier overflow observation must be claimed first.
 */
int dmh_uart_rx_ring_take(
	struct dmh_uart_rx_ring *ring,
	uint8_t *output,
	size_t output_capacity,
	struct dmh_uart_rx_chunk *chunk
);
void dmh_uart_rx_ring_snapshot(
	const struct dmh_uart_rx_ring *ring,
	struct dmh_uart_rx_snapshot *snapshot
);
bool dmh_uart_rx_ring_claim_overflow(
	struct dmh_uart_rx_ring *ring,
	struct dmh_uart_rx_overflow *overflow
);
enum dmh_uart_rx_observation_kind dmh_uart_rx_ring_next_observation(
	const struct dmh_uart_rx_ring *ring
);
void dmh_uart_rx_ring_discard_retained(struct dmh_uart_rx_ring *ring);

#endif
