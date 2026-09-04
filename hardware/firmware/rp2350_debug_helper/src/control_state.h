#ifndef DUTCHMATE_CONTROL_STATE_H
#define DUTCHMATE_CONTROL_STATE_H

#include "control_types.h"

#include <stdbool.h>
#include <stdint.h>

#define DMH_CONTROL_CHANNEL_COUNT 4U
#define DMH_CONTROL_PULSE_MIN_MS 1U
#define DMH_CONTROL_PULSE_MAX_MS 10000U

enum dmh_control_result {
	DMH_CONTROL_OK = 0,
	DMH_CONTROL_PENDING,
	DMH_CONTROL_INVALID_ARGUMENT,
	DMH_CONTROL_NOT_CONFIGURED,
	DMH_CONTROL_HARDWARE_FAULT,
};

enum dmh_control_poll_result {
	DMH_CONTROL_POLL_NONE = 0,
	DMH_CONTROL_POLL_COMPLETED,
	DMH_CONTROL_POLL_HARDWARE_FAULT,
};

enum dmh_control_drive {
	DMH_CONTROL_DRIVE_HIGH_Z = 0,
	DMH_CONTROL_DRIVE_LOW,
	DMH_CONTROL_DRIVE_HIGH,
};

struct dmh_control_port {
	void *context;
	int (*set_enable)(void *context, uint8_t channel, bool enabled);
	int (*set_data)(void *context, uint8_t channel, enum dmh_control_level level);
};

struct dmh_control_channel {
	bool configured;
	enum dmh_control_mode mode;
	enum dmh_control_level active_level;
	enum dmh_control_level idle_level;
	bool has_idle_level;
	enum dmh_control_drive drive;
};

struct dmh_control_pulse {
	bool active;
	uint8_t channel;
	uint64_t started_us;
	uint64_t duration_us;
};

struct dmh_control {
	struct dmh_control_port port;
	struct dmh_control_channel channels[DMH_CONTROL_CHANNEL_COUNT];
	struct dmh_control_pulse pulse;
};

void dmh_control_init(
	struct dmh_control *controller,
	const struct dmh_control_port *port
);
bool dmh_control_is_configured(const struct dmh_control *controller, uint8_t channel);
enum dmh_control_result dmh_control_configure(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_mode mode,
	enum dmh_control_level active_level,
	bool has_idle_level,
	enum dmh_control_level idle_level
);
enum dmh_control_result dmh_control_set_state(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_state state
);
enum dmh_control_result dmh_control_pulse_start(
	struct dmh_control *controller,
	uint8_t channel,
	uint32_t pulse_ms,
	uint64_t now_us
);
enum dmh_control_poll_result dmh_control_poll(
	struct dmh_control *controller,
	uint64_t now_us
);
enum dmh_control_result dmh_control_force_channel_safe(
	struct dmh_control *controller,
	uint8_t channel
);
enum dmh_control_result dmh_control_end_epoch(struct dmh_control *controller);

#endif
