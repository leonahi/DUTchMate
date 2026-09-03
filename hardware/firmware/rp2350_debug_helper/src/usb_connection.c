#include "usb_connection.h"

#include "connection_epoch.h"
#include "hello.h"
#include "platform_io.h"
#include "uart_event.h"
#include "uart_rx.h"

#include <errno.h>
#include <stddef.h>
#include <stdint.h>

#include <zephyr/device.h>
#include <zephyr/devicetree.h>
#include <zephyr/drivers/uart.h>
#include <zephyr/kernel.h>
#include <zephyr/sys/util.h>

#define DUTCHMATE_CDC_NODE DT_NODELABEL(cdc_acm_uart0)
#define DUTCHMATE_DEVELOPMENT_VID 0x2E8A
#define DUTCHMATE_DEVELOPMENT_PID 0x000A
#define DTR_POLL_INTERVAL K_MSEC(10)

BUILD_ASSERT(sizeof(CONFIG_DUTCHMATE_FIRMWARE_VERSION) > 1U);
BUILD_ASSERT(sizeof(CONFIG_DUTCHMATE_FIRMWARE_VERSION) <= 65U);
BUILD_ASSERT(
	!IS_ENABLED(CONFIG_DUTCHMATE_PRODUCTION_BUILD) ||
	CONFIG_CDC_ACM_SERIAL_VID != DUTCHMATE_DEVELOPMENT_VID ||
	CONFIG_CDC_ACM_SERIAL_PID != DUTCHMATE_DEVELOPMENT_PID,
	"Production builds must override development USB VID/PID"
);

static const struct device *const cdc = DEVICE_DT_GET(DUTCHMATE_CDC_NODE);
static uint8_t uart_staging[DMH_UART_EVENT_MAX_DATA_BYTES];
static char uart_event_frame[DMH_UART_EVENT_FRAME_CAPACITY];

static void write_complete_frame(const char *frame, size_t frame_length)
{
	size_t index;

	for (index = 0U; index < frame_length; index++) {
		uart_poll_out(cdc, frame[index]);
	}
}

static int drain_one_uart_event(void)
{
	struct dmh_uart_rx_chunk chunk;
	size_t frame_length;
	int result;

	result = dutchmate_uart_rx_take(
		uart_staging,
		sizeof(uart_staging),
		&chunk
	);
	if (result == -EAGAIN) {
		return 0;
	}
	if (result != 0 || chunk.length == 0U) {
		return result;
	}
	result = dmh_uart_event_encode(
		chunk.channel,
		chunk.timestamp_us,
		uart_staging,
		chunk.length,
		uart_event_frame,
		sizeof(uart_event_frame),
		&frame_length
	);
	if (result != 0) {
		return result;
	}
	write_complete_frame(uart_event_frame, frame_length);
	return 0;
}

int dutchmate_usb_connection_run(void)
{
	struct dmh_connection_epoch epoch;
	char hello_frame[DMH_HELLO_FRAME_CAPACITY];
	size_t hello_length;
	int result;

	if (!device_is_ready(cdc)) {
		return -ENODEV;
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
	for (;;) {
		enum dmh_epoch_transition transition;
		uint32_t dtr = 0U;

		result = uart_line_ctrl_get(cdc, UART_LINE_CTRL_DTR, &dtr);
		transition = dmh_connection_epoch_update(
			&epoch,
			result == 0 && dtr != 0U
		);
		if (transition == DMH_EPOCH_STARTED) {
			write_complete_frame(hello_frame, hello_length);
			result = dutchmate_uart_rx_start();
			if (result != 0) {
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
		} else if (transition == DMH_EPOCH_ENDED) {
			dutchmate_uart_rx_stop();
			(void)dutchmate_platform_io_force_safe();
		}
		if (epoch.active && dutchmate_uart_rx_faulted()) {
			dutchmate_uart_rx_stop();
			(void)dutchmate_platform_io_force_safe();
			return -EIO;
		}
		if (epoch.active) {
			result = drain_one_uart_event();
			if (result != 0) {
				dutchmate_uart_rx_stop();
				(void)dutchmate_platform_io_force_safe();
				return result;
			}
		}
		k_sleep(DTR_POLL_INTERVAL);
	}

	return 0;
}
