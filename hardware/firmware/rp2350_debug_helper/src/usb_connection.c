#include "usb_connection.h"

#include "cdc_tx.h"
#include "command_runtime.h"
#include "command_response.h"
#include "connection_epoch.h"
#include "hello.h"
#include "output_drain.h"
#include "platform_io.h"
#ifdef CONFIG_DUTCHMATE_STACK_PROBE
#include "stack_probe.h"
#endif
#include "telemetry.h"
#include "uart_event.h"
#include "uart_rx.h"

#include <errno.h>
#include <stddef.h>
#include <stdint.h>

#include <hardware/timer.h>
#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/util.h>

#define DUTCHMATE_CDC_NODE DT_NODELABEL(cdc_acm_uart0)
#define DUTCHMATE_DEVELOPMENT_VID 0x2E8A
#define DUTCHMATE_DEVELOPMENT_PID 0x000A
#define CDC_TX_POLL_INTERVAL K_MSEC(1)
#define DTR_POLL_INTERVAL K_MSEC(10)
#define OUTPUT_DRAIN_BATCH_BUDGET 32U

BUILD_ASSERT(sizeof(CONFIG_DUTCHMATE_FIRMWARE_VERSION) > 1U);
BUILD_ASSERT(sizeof(CONFIG_DUTCHMATE_FIRMWARE_VERSION) <= 65U);
BUILD_ASSERT(
	!IS_ENABLED(CONFIG_DUTCHMATE_PRODUCTION_BUILD) ||
	CONFIG_CDC_ACM_SERIAL_VID != DUTCHMATE_DEVELOPMENT_VID ||
	CONFIG_CDC_ACM_SERIAL_PID != DUTCHMATE_DEVELOPMENT_PID,
	"Production builds must override development USB VID/PID"
);
BUILD_ASSERT(DMH_HELLO_FRAME_CAPACITY <= DMH_CDC_TX_MAX_FRAME_BYTES);
BUILD_ASSERT(DMH_COMMAND_RESPONSE_FRAME_CAPACITY <= DMH_CDC_TX_MAX_FRAME_BYTES);
BUILD_ASSERT(DMH_TELEMETRY_FRAME_CAPACITY <= DMH_CDC_TX_MAX_FRAME_BYTES);
BUILD_ASSERT(DMH_UART_EVENT_FRAME_CAPACITY <= DMH_CDC_TX_MAX_FRAME_BYTES);

static const struct device *const cdc = DEVICE_DT_GET(DUTCHMATE_CDC_NODE);
static uint8_t uart_staging[DMH_UART_EVENT_MAX_DATA_BYTES];
static char evidence_frame[DMH_UART_EVENT_FRAME_CAPACITY];

static int publish_host_ready(void)
{
	int dcd_result = uart_line_ctrl_set(
		cdc,
		UART_LINE_CTRL_DCD,
		1U
	);
	int dsr_result = uart_line_ctrl_set(
		cdc,
		UART_LINE_CTRL_DSR,
		1U
	);

	return dcd_result != 0 ? dcd_result : dsr_result;
}

static int write_complete_frame(const char *frame, size_t frame_length)
{
	enum dmh_cdc_tx_result tx_result;

	tx_result = dutchmate_cdc_tx_start(
		(const uint8_t *)frame,
		frame_length
	);
	if (tx_result != DMH_CDC_TX_PENDING) {
		return tx_result == DMH_CDC_TX_INVALID_ARGUMENT ? -EINVAL : -EIO;
	}
	for (;;) {
		uint32_t dtr = 0U;
		int result = uart_line_ctrl_get(cdc, UART_LINE_CTRL_DTR, &dtr);

		if (result != 0) {
			dutchmate_cdc_tx_cancel();
			return result;
		}
		if (dtr == 0U) {
			dutchmate_cdc_tx_cancel();
			return -ENOTCONN;
		}
		tx_result = dutchmate_cdc_tx_poll();
		if (tx_result == DMH_CDC_TX_COMPLETED) {
			return 0;
		}
		if (tx_result != DMH_CDC_TX_PENDING) {
			return -EIO;
		}
		k_sleep(CDC_TX_POLL_INTERVAL);
	}
}

static void stage_status_if_due(struct dmh_telemetry_schedule *schedule)
{
	struct dmh_buffer_status_observation observation;
	uint64_t now_us = time_us_64();

	if (!dmh_telemetry_status_due(schedule, now_us)) {
		return;
	}
	observation.timestamp_us = now_us;
	dutchmate_uart_rx_snapshot_observation(
		&observation.snapshot,
		&observation.observation_sequence
	);
	dmh_telemetry_schedule_stage_status(schedule, &observation);
}

static int drain_one_evidence(struct dmh_telemetry_schedule *schedule)
{
	const struct dmh_buffer_status_observation *status =
		dmh_telemetry_pending_status(schedule);
	struct dmh_uart_rx_chunk chunk;
	struct dmh_uart_rx_overflow overflow;
	enum dmh_uart_rx_observation_kind kind;
	size_t frame_length;
	int result;

	result = dutchmate_uart_rx_take_before(
		status != NULL,
		status != NULL ? status->observation_sequence : 0U,
		uart_staging,
		sizeof(uart_staging),
		&kind,
		&chunk,
		&overflow
	);
	if (result != 0) {
		return result;
	}
	if (kind == DMH_UART_RX_OBSERVATION_CHUNK) {
		result = dmh_uart_event_encode(
			chunk.channel,
			chunk.timestamp_us,
			uart_staging,
			chunk.length,
			evidence_frame,
			sizeof(evidence_frame),
			&frame_length
		);
	} else if (kind == DMH_UART_RX_OBSERVATION_OVERFLOW) {
		result = dmh_buffer_overflow_encode(
			0U,
			overflow.first_drop_timestamp_us,
			overflow.dropped_bytes,
			evidence_frame,
			sizeof(evidence_frame),
			&frame_length
		);
	} else if (status != NULL) {
		result = dmh_buffer_status_encode(
			status->timestamp_us,
			&status->snapshot,
			evidence_frame,
			sizeof(evidence_frame),
			&frame_length
		);
	} else {
		return 0;
	}
	if (result != 0) {
		return result;
	}
	result = write_complete_frame(evidence_frame, frame_length);
	if (result != 0) {
		return result;
	}
	if (kind == DMH_UART_RX_OBSERVATION_NONE) {
		dmh_telemetry_schedule_status_sent(schedule);
	}
	return 1;
}

static int drain_one_output(struct dmh_telemetry_schedule *schedule)
{
	const char *response;
	size_t response_length;

	if (dutchmate_command_runtime_take_response(
		&response, &response_length
	)) {
		int result = write_complete_frame(response, response_length);

		if (result != 0) {
			return result;
		}
		dutchmate_command_runtime_response_sent();
		return 1;
	}
	return drain_one_evidence(schedule);
}

static int drain_one_output_adapter(void *context)
{
	return drain_one_output(context);
}

static int end_active_epoch(struct dmh_telemetry_schedule *schedule)
{
	int result;

	dmh_telemetry_schedule_stop(schedule);
	dutchmate_cdc_tx_cancel();
	result = dutchmate_command_runtime_end_epoch();
	dutchmate_uart_rx_stop();
	if (dutchmate_platform_io_force_safe() != 0 && result == 0) {
		result = -EIO;
	}
#ifdef CONFIG_DUTCHMATE_STACK_PROBE
	dutchmate_stack_probe_epoch_ended();
#endif
	return result;
}

int dutchmate_usb_connection_run(void)
{
	struct dmh_connection_epoch epoch;
	struct dmh_telemetry_schedule telemetry_schedule;
	struct dmh_output_drain_result drain_result;
	char hello_frame[DMH_HELLO_FRAME_CAPACITY];
	size_t hello_length;
	int result;

	if (!device_is_ready(cdc)) {
		return -ENODEV;
	}
	result = dutchmate_cdc_tx_initialize(cdc);
	if (result != 0) {
		return result;
	}
	result = dutchmate_command_runtime_initialize(cdc);
	if (result != 0) {
		return result;
	}
	result = dmh_hello_encode(
		CONFIG_DUTCHMATE_FIRMWARE_VERSION,
		hello_frame,
		sizeof(hello_frame),
		&hello_length
	);
	if (result != 0) {
		return result;
	}

	dmh_connection_epoch_init(&epoch);
	dmh_telemetry_schedule_init(&telemetry_schedule);
	for (;;) {
		enum dmh_epoch_transition transition;
		uint32_t dtr = 0U;

		result = uart_line_ctrl_get(cdc, UART_LINE_CTRL_DTR, &dtr);
		transition = dmh_connection_epoch_update(
			&epoch,
			result == 0 && dtr != 0U,
			time_us_64()
		);
		if (transition == DMH_EPOCH_STARTED) {
#ifdef CONFIG_DUTCHMATE_STACK_PROBE
			char firmware[65];

			if (dutchmate_stack_probe_firmware(
				    firmware, sizeof(firmware)) != 0) {
				return -EINVAL;
			}
			result = dmh_hello_encode(
				firmware,
				hello_frame,
				sizeof(hello_frame),
				&hello_length
			);
			if (result != 0) {
				return result;
			}
#endif
			dutchmate_command_runtime_discard_input();
			result = publish_host_ready();
			if (result != 0) {
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
			result = write_complete_frame(hello_frame, hello_length);
			if (result == -ENOTCONN) {
				(void)dmh_connection_epoch_update(
					&epoch,
					false,
					time_us_64()
				);
				if (dutchmate_platform_io_force_safe() != 0) {
					return -EIO;
				}
				continue;
			}
			if (result != 0) {
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
#ifdef CONFIG_DUTCHMATE_STACK_PROBE
			dutchmate_stack_probe_hello_sent();
#endif
			result = dutchmate_uart_rx_start();
			if (result != 0) {
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
			result = dutchmate_command_runtime_start_epoch();
			if (result != 0) {
				dutchmate_uart_rx_stop();
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
			dmh_telemetry_schedule_start(
				&telemetry_schedule,
				time_us_64()
			);
		} else if (transition == DMH_EPOCH_ENDED) {
			result = end_active_epoch(&telemetry_schedule);
			if (result != 0) {
				return result;
			}
		}
		if (epoch.active && (dutchmate_uart_rx_faulted() ||
				     dutchmate_command_runtime_faulted())) {
			(void)end_active_epoch(&telemetry_schedule);
			return -EIO;
		}
		if (epoch.active) {
			stage_status_if_due(&telemetry_schedule);
			result = dmh_output_drain_batch(
				drain_one_output_adapter,
				&telemetry_schedule,
				OUTPUT_DRAIN_BATCH_BUDGET,
				&drain_result
			);
			if (result == -ENOTCONN) {
				(void)dmh_connection_epoch_update(
					&epoch,
					false,
					time_us_64()
				);
				result = end_active_epoch(&telemetry_schedule);
				if (result != 0) {
					return result;
				}
				continue;
			}
			if (result != 0) {
				(void)end_active_epoch(&telemetry_schedule);
				return result;
			}
			if (!drain_result.idle) {
				continue;
			}
		}
		k_sleep(DTR_POLL_INTERVAL);
	}

	return 0;
}
