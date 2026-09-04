#include "ndjson_framer.h"

#include <assert.h>
#include <errno.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

static struct dmh_ndjson_framer framer;
static uint8_t large_input[DMH_HOST_FRAME_MAX_BYTES + 32U];

static void assert_frame(
	const struct dmh_ndjson_result *result,
	const uint8_t *expected,
	size_t expected_length
)
{
	assert(result->outcome == DMH_NDJSON_FRAME_READY);
	assert(result->frame_length == expected_length);
	assert(memcmp(result->frame, expected, expected_length) == 0);
}

static void test_fragmented_and_multiple_frames(void)
{
	static const uint8_t first_part[] = "{\"cmd\":\"uart_";
	static const uint8_t second_part[] =
		"send\"}\n{\"cmd\":\"pulse_control\"}\n";
	static const uint8_t first_frame[] = "{\"cmd\":\"uart_send\"}";
	static const uint8_t second_frame[] = "{\"cmd\":\"pulse_control\"}";
	struct dmh_ndjson_result result;
	size_t offset;

	dmh_ndjson_framer_init(&framer);
	assert(dmh_ndjson_framer_feed(
		&framer,
		first_part,
		sizeof(first_part) - 1U,
		&result
	) == 0);
	assert(result.outcome == DMH_NDJSON_INCOMPLETE);
	assert(result.consumed_bytes == sizeof(first_part) - 1U);

	assert(dmh_ndjson_framer_feed(
		&framer,
		second_part,
		sizeof(second_part) - 1U,
		&result
	) == 0);
	assert_frame(&result, first_frame, sizeof(first_frame) - 1U);
	offset = result.consumed_bytes;
	assert(offset < sizeof(second_part) - 1U);
	assert(dmh_ndjson_framer_feed(
		&framer,
		second_part + offset,
		sizeof(second_part) - 1U - offset,
		&result
	) == 0);
	assert_frame(&result, second_frame, sizeof(second_frame) - 1U);
	assert(result.consumed_bytes == sizeof(second_part) - 1U - offset);
}

static void test_crlf_normalization(void)
{
	static const uint8_t input[] = "{\"cmd\":1}\r\n{\"cmd\":2}\r\r\n";
	static const uint8_t first_frame[] = "{\"cmd\":1}";
	static const uint8_t second_frame[] = "{\"cmd\":2}\r";
	struct dmh_ndjson_result result;
	size_t offset;

	dmh_ndjson_framer_init(&framer);
	assert(dmh_ndjson_framer_feed(
		&framer, input, sizeof(input) - 1U, &result
	) == 0);
	assert_frame(&result, first_frame, sizeof(first_frame) - 1U);
	offset = result.consumed_bytes;
	assert(dmh_ndjson_framer_feed(
		&framer, input + offset, sizeof(input) - 1U - offset, &result
	) == 0);
	assert_frame(&result, second_frame, sizeof(second_frame) - 1U);
}

static void fill_exact_frame(size_t body_length, bool crlf)
{
	memset(large_input, ' ', body_length);
	large_input[0] = '{';
	large_input[body_length - 1U] = '}';
	if (crlf) {
		large_input[body_length] = '\r';
		large_input[body_length + 1U] = '\n';
	} else {
		large_input[body_length] = '\n';
	}
}

static void test_exact_frame_limit(void)
{
	struct dmh_ndjson_result result;

	dmh_ndjson_framer_init(&framer);
	fill_exact_frame(DMH_HOST_FRAME_MAX_BYTES - 1U, false);
	assert(dmh_ndjson_framer_feed(
		&framer, large_input, DMH_HOST_FRAME_MAX_BYTES, &result
	) == 0);
	assert(result.outcome == DMH_NDJSON_FRAME_READY);
	assert(result.frame_length == DMH_HOST_FRAME_MAX_BYTES - 1U);
	assert(result.consumed_bytes == DMH_HOST_FRAME_MAX_BYTES);

	dmh_ndjson_framer_init(&framer);
	fill_exact_frame(DMH_HOST_FRAME_MAX_BYTES - 2U, true);
	assert(dmh_ndjson_framer_feed(
		&framer, large_input, DMH_HOST_FRAME_MAX_BYTES, &result
	) == 0);
	assert(result.outcome == DMH_NDJSON_FRAME_READY);
	assert(result.frame_length == DMH_HOST_FRAME_MAX_BYTES - 2U);
	assert(result.consumed_bytes == DMH_HOST_FRAME_MAX_BYTES);
}

static void test_oversize_discards_through_lf_and_resynchronizes(void)
{
	static const uint8_t valid_frame[] = "{\"cmd\":\"uart_send\"}\n";
	struct dmh_ndjson_result result;
	size_t suffix_offset;

	dmh_ndjson_framer_init(&framer);
	memset(large_input, 'x', DMH_HOST_FRAME_MAX_BYTES);
	large_input[DMH_HOST_FRAME_MAX_BYTES] = '\n';
	memcpy(
		large_input + DMH_HOST_FRAME_MAX_BYTES + 1U,
		valid_frame,
		sizeof(valid_frame) - 1U
	);
	assert(dmh_ndjson_framer_feed(
		&framer,
		large_input,
		DMH_HOST_FRAME_MAX_BYTES + 1U + sizeof(valid_frame) - 1U,
		&result
	) == 0);
	assert(result.outcome == DMH_NDJSON_FRAME_TOO_LARGE);
	assert(result.consumed_bytes == DMH_HOST_FRAME_MAX_BYTES + 1U);
	suffix_offset = result.consumed_bytes;
	assert(dmh_ndjson_framer_feed(
		&framer,
		large_input + suffix_offset,
		sizeof(valid_frame) - 1U,
		&result
	) == 0);
	assert_frame(&result, valid_frame, sizeof(valid_frame) - 2U);
}

static void test_oversize_across_chunks_waits_for_lf(void)
{
	struct dmh_ndjson_result result;
	static const uint8_t terminator[] = "still discarded\n";

	dmh_ndjson_framer_init(&framer);
	memset(large_input, 'x', DMH_HOST_FRAME_MAX_BYTES);
	assert(dmh_ndjson_framer_feed(
		&framer, large_input, DMH_HOST_FRAME_MAX_BYTES, &result
	) == 0);
	assert(result.outcome == DMH_NDJSON_INCOMPLETE);
	assert(result.consumed_bytes == DMH_HOST_FRAME_MAX_BYTES);
	assert(dmh_ndjson_framer_feed(
		&framer, terminator, sizeof(terminator) - 1U, &result
	) == 0);
	assert(result.outcome == DMH_NDJSON_FRAME_TOO_LARGE);
	assert(result.consumed_bytes == sizeof(terminator) - 1U);
}

static void test_reset_discards_partial_and_oversize_state(void)
{
	struct dmh_ndjson_result result;
	static const uint8_t partial[] = "discard me";
	static const uint8_t valid[] = "{}\n";

	dmh_ndjson_framer_init(&framer);
	assert(dmh_ndjson_framer_feed(
		&framer, partial, sizeof(partial) - 1U, &result
	) == 0);
	dmh_ndjson_framer_reset(&framer);
	assert(dmh_ndjson_framer_feed(
		&framer, valid, sizeof(valid) - 1U, &result
	) == 0);
	assert_frame(&result, valid, sizeof(valid) - 2U);

	memset(large_input, 'x', DMH_HOST_FRAME_MAX_BYTES);
	assert(dmh_ndjson_framer_feed(
		&framer, large_input, DMH_HOST_FRAME_MAX_BYTES, &result
	) == 0);
	dmh_ndjson_framer_reset(&framer);
	assert(dmh_ndjson_framer_feed(
		&framer, valid, sizeof(valid) - 1U, &result
	) == 0);
	assert_frame(&result, valid, sizeof(valid) - 2U);
}

static void test_invalid_arguments(void)
{
	struct dmh_ndjson_result result;
	static const uint8_t input[] = "{}\n";

	dmh_ndjson_framer_init(&framer);
	assert(dmh_ndjson_framer_feed(NULL, input, sizeof(input), &result) == -EINVAL);
	assert(dmh_ndjson_framer_feed(&framer, NULL, 1U, &result) == -EINVAL);
	assert(dmh_ndjson_framer_feed(&framer, input, sizeof(input), NULL) == -EINVAL);
	assert(dmh_ndjson_framer_feed(&framer, NULL, 0U, &result) == 0);
	assert(result.outcome == DMH_NDJSON_INCOMPLETE);
	assert(result.consumed_bytes == 0U);
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "fragmented") == 0) {
		test_fragmented_and_multiple_frames();
	} else if (strcmp(argv[1], "crlf") == 0) {
		test_crlf_normalization();
	} else if (strcmp(argv[1], "exact-limit") == 0) {
		test_exact_frame_limit();
	} else if (strcmp(argv[1], "oversize-resync") == 0) {
		test_oversize_discards_through_lf_and_resynchronizes();
	} else if (strcmp(argv[1], "oversize-chunks") == 0) {
		test_oversize_across_chunks_waits_for_lf();
	} else if (strcmp(argv[1], "reset") == 0) {
		test_reset_discards_partial_and_oversize_state();
	} else if (strcmp(argv[1], "invalid") == 0) {
		test_invalid_arguments();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
