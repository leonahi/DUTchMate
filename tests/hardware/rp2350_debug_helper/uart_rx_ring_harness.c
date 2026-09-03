#include "uart_rx_ring.h"

#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static struct dmh_uart_rx_ring ring;
static uint8_t input[DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES + 8U];
static uint8_t output[DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES];

static void fill_pattern(uint8_t *bytes, size_t length, uint8_t seed)
{
	size_t index;

	for (index = 0U; index < length; index++) {
		bytes[index] = (uint8_t)(seed + index);
	}
}

static void test_initial_snapshot(void)
{
	struct dmh_uart_rx_snapshot snapshot;
	struct dmh_uart_rx_overflow overflow;

	dmh_uart_rx_ring_init(&ring);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.capacity_bytes == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(snapshot.used_bytes == 0U);
	assert(snapshot.high_water_bytes == 0U);
	assert(snapshot.dropped_bytes_total == 0U);
	assert(snapshot.overflow_events == 0U);
	assert(!dmh_uart_rx_ring_claim_overflow(&ring, &overflow));
}

static void test_fifo_wrap_and_timestamp_split(void)
{
	struct dmh_uart_rx_chunk chunk;
	size_t index;

	dmh_uart_rx_ring_init(&ring);
	fill_pattern(input, 30000U, 7U);
	assert(dmh_uart_rx_ring_push(&ring, 0U, 10U, input, 30000U) == 0);
	assert(dmh_uart_rx_ring_take(&ring, output, 29900U, &chunk) == 0);
	assert(chunk.length == 29900U);
	assert(chunk.channel == 0U);
	assert(chunk.timestamp_us == 10U);
	assert(memcmp(output, input, chunk.length) == 0);

	fill_pattern(input, 5000U, 91U);
	assert(dmh_uart_rx_ring_push(&ring, 3U, 20U, input, 5000U) == 0);
	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == 100U);
	assert(chunk.channel == 0U);
	assert(chunk.timestamp_us == 10U);
	for (index = 0U; index < chunk.length; index++) {
		assert(output[index] == (uint8_t)(7U + 29900U + index));
	}
	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == 5000U);
	assert(chunk.channel == 3U);
	assert(chunk.timestamp_us == 20U);
	for (index = 0U; index < chunk.length; index++) {
		assert(output[index] == (uint8_t)(91U + index));
	}
}

static void test_byte_overflow_drops_oldest(void)
{
	struct dmh_uart_rx_chunk chunk;
	struct dmh_uart_rx_overflow overflow;
	struct dmh_uart_rx_snapshot snapshot;

	dmh_uart_rx_ring_init(&ring);
	memset(input, 'A', DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - 8U);
	assert(dmh_uart_rx_ring_push(
		&ring,
		0U,
		100U,
		input,
		DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - 8U
	) == 0);
	memset(input, 'B', 16U);
	assert(dmh_uart_rx_ring_push(&ring, 0U, 200U, input, 16U) == 0);

	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.used_bytes == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(snapshot.high_water_bytes == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(snapshot.dropped_bytes_total == 8U);
	assert(snapshot.overflow_events == 1U);
	assert(dmh_uart_rx_ring_claim_overflow(&ring, &overflow));
	assert(overflow.first_drop_timestamp_us == 200U);
	assert(overflow.dropped_bytes == 8U);
	assert(!dmh_uart_rx_ring_claim_overflow(&ring, &overflow));

	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES - 16U);
	assert(chunk.timestamp_us == 100U);
	assert(output[0] == 'A');
	assert(output[chunk.length - 1U] == 'A');
	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == 16U);
	assert(chunk.timestamp_us == 200U);
	assert(memcmp(output, "BBBBBBBBBBBBBBBB", 16U) == 0);
}

static void test_oversized_callback_preserves_newest(void)
{
	struct dmh_uart_rx_chunk chunk;
	struct dmh_uart_rx_snapshot snapshot;

	dmh_uart_rx_ring_init(&ring);
	fill_pattern(input, sizeof(input), 17U);
	assert(dmh_uart_rx_ring_push(&ring, 1U, 300U, input, sizeof(input)) == 0);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.used_bytes == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(snapshot.dropped_bytes_total == 8U);
	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(chunk.channel == 1U);
	assert(chunk.timestamp_us == 300U);
	assert(memcmp(output, input + 8U, chunk.length) == 0);
}

static void test_descriptor_exhaustion_drops_oldest_descriptor(void)
{
	struct dmh_uart_rx_chunk chunk;
	struct dmh_uart_rx_snapshot snapshot;
	size_t index;

	dmh_uart_rx_ring_init(&ring);
	for (index = 0U; index < DMH_UART_RX_DESCRIPTOR_CAPACITY; index++) {
		input[0] = (uint8_t)index;
		assert(dmh_uart_rx_ring_push(&ring, 0U, index, input, 1U) == 0);
	}
	input[0] = 0xEEU;
	assert(dmh_uart_rx_ring_push(&ring, 0U, 900U, input, 1U) == 0);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.used_bytes == DMH_UART_RX_DESCRIPTOR_CAPACITY);
	assert(snapshot.dropped_bytes_total == 1U);
	assert(snapshot.overflow_events == 1U);
	assert(dmh_uart_rx_ring_take(&ring, output, sizeof(output), &chunk) == 0);
	assert(chunk.length == 1U);
	assert(chunk.timestamp_us == 1U);
	assert(output[0] == 1U);
}

static void test_overflow_episode_coalescing(void)
{
	struct dmh_uart_rx_overflow overflow;
	struct dmh_uart_rx_snapshot snapshot;

	dmh_uart_rx_ring_init(&ring);
	memset(input, 0, DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(dmh_uart_rx_ring_push(
		&ring,
		0U,
		1U,
		input,
		DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES
	) == 0);
	assert(dmh_uart_rx_ring_push(&ring, 0U, 10U, input, 1U) == 0);
	assert(dmh_uart_rx_ring_push(&ring, 0U, 11U, input, 1U) == 0);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.dropped_bytes_total == 2U);
	assert(snapshot.overflow_events == 1U);
	assert(dmh_uart_rx_ring_claim_overflow(&ring, &overflow));
	assert(overflow.first_drop_timestamp_us == 10U);
	assert(overflow.dropped_bytes == 2U);

	assert(dmh_uart_rx_ring_push(&ring, 0U, 12U, input, 1U) == 0);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.dropped_bytes_total == 3U);
	assert(snapshot.overflow_events == 2U);
	assert(dmh_uart_rx_ring_claim_overflow(&ring, &overflow));
	assert(overflow.first_drop_timestamp_us == 12U);
	assert(overflow.dropped_bytes == 1U);
}

static void test_disconnect_discard_preserves_boot_counters(void)
{
	struct dmh_uart_rx_snapshot snapshot;

	dmh_uart_rx_ring_init(&ring);
	memset(input, 0, DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(dmh_uart_rx_ring_push(
		&ring,
		0U,
		1U,
		input,
		DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES
	) == 0);
	assert(dmh_uart_rx_ring_push(&ring, 0U, 2U, input, 1U) == 0);
	dmh_uart_rx_ring_discard_retained(&ring);
	dmh_uart_rx_ring_snapshot(&ring, &snapshot);
	assert(snapshot.used_bytes == 0U);
	assert(snapshot.high_water_bytes == DUTCHMATE_UART_RING_BUFFER_SIZE_BYTES);
	assert(snapshot.dropped_bytes_total == 1U);
	assert(snapshot.overflow_events == 1U);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "initial") == 0) {
		test_initial_snapshot();
	} else if (strcmp(argv[1], "wrap") == 0) {
		test_fifo_wrap_and_timestamp_split();
	} else if (strcmp(argv[1], "byte-overflow") == 0) {
		test_byte_overflow_drops_oldest();
	} else if (strcmp(argv[1], "oversized") == 0) {
		test_oversized_callback_preserves_newest();
	} else if (strcmp(argv[1], "descriptor-overflow") == 0) {
		test_descriptor_exhaustion_drops_oldest_descriptor();
	} else if (strcmp(argv[1], "episode") == 0) {
		test_overflow_episode_coalescing();
	} else if (strcmp(argv[1], "discard") == 0) {
		test_disconnect_discard_preserves_boot_counters();
	} else {
		return EXIT_FAILURE;
	}

	return EXIT_SUCCESS;
}
