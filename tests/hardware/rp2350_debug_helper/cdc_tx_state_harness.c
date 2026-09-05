#include "cdc_tx_state.h"

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct fake_cdc {
	uint8_t bytes[DMH_CDC_TX_MAX_FRAME_BYTES * 2U];
	size_t length;
	size_t max_write;
	int forced_write_result;
	size_t write_calls;
	size_t stop_calls;
};

static int write_bytes(void *context, const uint8_t *data, size_t length)
{
	struct fake_cdc *cdc = context;
	size_t accepted = length < cdc->max_write ? length : cdc->max_write;

	cdc->write_calls++;
	if (cdc->forced_write_result != 0) {
		return cdc->forced_write_result;
	}
	if (accepted > 0U) {
		(void)memcpy(&cdc->bytes[cdc->length], data, accepted);
		cdc->length += accepted;
	}
	return (int)accepted;
}

static void stop_writes(void *context)
{
	struct fake_cdc *cdc = context;

	cdc->stop_calls++;
}

static struct dmh_cdc_tx_port make_port(struct fake_cdc *cdc)
{
	return (struct dmh_cdc_tx_port) {
		.context = cdc,
		.write = write_bytes,
		.stop = stop_writes,
	};
}

static void expect_result(enum dmh_cdc_tx_result actual, enum dmh_cdc_tx_result expected)
{
	if (actual != expected) {
		(void)fprintf(stderr, "result %d, expected %d\n", actual, expected);
		exit(EXIT_FAILURE);
	}
}

static void test_bounds_and_busy_state(void)
{
	struct fake_cdc cdc = {.max_write = DMH_CDC_TX_MAX_FRAME_BYTES};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t bytes[DMH_CDC_TX_MAX_FRAME_BYTES + 1U] = {0x5aU};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, NULL, 1U, 0U, 100U),
		DMH_CDC_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, 0U, 0U, 100U),
		DMH_CDC_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_cdc_tx_start(
			&tx,
			bytes,
			DMH_CDC_TX_MAX_FRAME_BYTES + 1U,
			0U,
			100U
		),
		DMH_CDC_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, 1U, 0U, 0U),
		DMH_CDC_TX_INVALID_ARGUMENT
	);
	expect_result(
		dmh_cdc_tx_start(
			&tx,
			bytes,
			DMH_CDC_TX_MAX_FRAME_BYTES,
			0U,
			100U
		),
		DMH_CDC_TX_PENDING
	);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, 1U, 0U, 100U),
		DMH_CDC_TX_BUSY
	);
	if (cdc.write_calls != 0U || cdc.stop_calls != 0U) {
		exit(EXIT_FAILURE);
	}
	dmh_cdc_tx_cancel(&tx);
}

static void test_partial_driver_acceptance_completes_once(void)
{
	struct fake_cdc cdc = {.max_write = 2U};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t bytes[] = {0x10U, 0x20U, 0x30U};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	bytes[0] = 0xffU;
	dmh_cdc_tx_on_writable(&tx, 1U);
	expect_result(dmh_cdc_tx_poll(&tx, 1U), DMH_CDC_TX_PENDING);
	dmh_cdc_tx_on_writable(&tx, 2U);
	expect_result(dmh_cdc_tx_poll(&tx, 2U), DMH_CDC_TX_COMPLETED);
	if (cdc.length != 3U || cdc.write_calls != 2U || cdc.stop_calls != 1U ||
	    cdc.bytes[0] != 0x10U || cdc.bytes[1] != 0x20U ||
	    cdc.bytes[2] != 0x30U) {
		exit(EXIT_FAILURE);
	}
	expect_result(dmh_cdc_tx_poll(&tx, 3U), DMH_CDC_TX_IDLE);
	dmh_cdc_tx_on_writable(&tx, 3U);
	if (cdc.write_calls != 2U || cdc.stop_calls != 2U) {
		exit(EXIT_FAILURE);
	}
}

static void test_zero_progress_is_hardware_fault(void)
{
	struct fake_cdc cdc = {.max_write = 0U};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t byte = 0xaaU;

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, &byte, 1U, 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 1U);
	expect_result(dmh_cdc_tx_poll(&tx, 1U), DMH_CDC_TX_HARDWARE_FAULT);
	if (cdc.write_calls != 1U || cdc.stop_calls != 1U) {
		exit(EXIT_FAILURE);
	}
	expect_result(dmh_cdc_tx_poll(&tx, 2U), DMH_CDC_TX_IDLE);
}

static void test_invalid_driver_counts_are_hardware_faults(void)
{
	struct fake_cdc cdc = {.max_write = 4U, .forced_write_result = 5};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t bytes[] = {1U, 2U, 3U, 4U};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 1U);
	expect_result(dmh_cdc_tx_poll(&tx, 1U), DMH_CDC_TX_HARDWARE_FAULT);

	cdc = (struct fake_cdc) {.max_write = 4U, .forced_write_result = -1};
	port = make_port(&cdc);
	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 1U);
	expect_result(dmh_cdc_tx_poll(&tx, 1U), DMH_CDC_TX_HARDWARE_FAULT);
}

static void test_no_progress_timeout_resets_after_progress_and_handles_wrap(void)
{
	struct fake_cdc cdc = {.max_write = 1U};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t bytes[] = {0x01U, 0x02U, 0x03U};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, sizeof(bytes), UINT64_MAX - 99U, 200U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, UINT64_MAX - 99U);
	expect_result(dmh_cdc_tx_poll(&tx, 50U), DMH_CDC_TX_PENDING);
	dmh_cdc_tx_on_writable(&tx, 50U);
	expect_result(dmh_cdc_tx_poll(&tx, 249U), DMH_CDC_TX_PENDING);
	expect_result(dmh_cdc_tx_poll(&tx, 250U), DMH_CDC_TX_TIMEOUT);
	if (cdc.length != 2U || cdc.write_calls != 2U || cdc.stop_calls != 1U) {
		exit(EXIT_FAILURE);
	}
	dmh_cdc_tx_on_writable(&tx, 251U);
	if (cdc.length != 2U || cdc.write_calls != 2U || cdc.stop_calls != 2U) {
		exit(EXIT_FAILURE);
	}
}

static void test_cancel_discards_partial_frame_without_replay(void)
{
	struct fake_cdc cdc = {.max_write = 1U};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t old_frame[] = {0x11U, 0x22U};
	uint8_t new_frame[] = {0x33U};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, old_frame, sizeof(old_frame), 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 1U);
	dmh_cdc_tx_cancel(&tx);
	expect_result(dmh_cdc_tx_poll(&tx, 2U), DMH_CDC_TX_IDLE);
	dmh_cdc_tx_on_writable(&tx, 2U);
	expect_result(
		dmh_cdc_tx_start(&tx, new_frame, sizeof(new_frame), 3U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 4U);
	expect_result(dmh_cdc_tx_poll(&tx, 4U), DMH_CDC_TX_COMPLETED);
	if (cdc.length != 2U || cdc.bytes[0] != 0x11U || cdc.bytes[1] != 0x33U) {
		exit(EXIT_FAILURE);
	}
}

static void test_driver_fault_stops_partial_frame(void)
{
	struct fake_cdc cdc = {.max_write = 1U};
	struct dmh_cdc_tx tx;
	struct dmh_cdc_tx_port port = make_port(&cdc);
	uint8_t bytes[] = {0x44U, 0x55U};

	dmh_cdc_tx_init(&tx, &port);
	expect_result(
		dmh_cdc_tx_start(&tx, bytes, sizeof(bytes), 0U, 100U),
		DMH_CDC_TX_PENDING
	);
	dmh_cdc_tx_on_writable(&tx, 1U);
	dmh_cdc_tx_driver_fault(&tx);
	expect_result(dmh_cdc_tx_poll(&tx, 1U), DMH_CDC_TX_HARDWARE_FAULT);
	dmh_cdc_tx_on_writable(&tx, 2U);
	if (cdc.length != 1U || cdc.write_calls != 1U || cdc.stop_calls != 2U) {
		exit(EXIT_FAILURE);
	}
}

int main(int argc, char **argv)
{
	if (argc != 2) {
		return EXIT_FAILURE;
	}
	if (strcmp(argv[1], "bounds") == 0) {
		test_bounds_and_busy_state();
	} else if (strcmp(argv[1], "partial") == 0) {
		test_partial_driver_acceptance_completes_once();
	} else if (strcmp(argv[1], "zero") == 0) {
		test_zero_progress_is_hardware_fault();
	} else if (strcmp(argv[1], "invalid-count") == 0) {
		test_invalid_driver_counts_are_hardware_faults();
	} else if (strcmp(argv[1], "timeout") == 0) {
		test_no_progress_timeout_resets_after_progress_and_handles_wrap();
	} else if (strcmp(argv[1], "cancel") == 0) {
		test_cancel_discards_partial_frame_without_replay();
	} else if (strcmp(argv[1], "driver-fault") == 0) {
		test_driver_fault_stops_partial_frame();
	} else {
		return EXIT_FAILURE;
	}
	return EXIT_SUCCESS;
}
