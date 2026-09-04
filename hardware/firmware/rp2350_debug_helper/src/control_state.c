#include "control_state.h"

#include <stddef.h>

static bool channel_valid(uint8_t channel)
{
	return channel < DMH_CONTROL_CHANNEL_COUNT;
}

static bool level_valid(enum dmh_control_level level)
{
	return level == DMH_CONTROL_LEVEL_LOW || level == DMH_CONTROL_LEVEL_HIGH;
}

static bool configuration_valid(
	enum dmh_control_mode mode,
	enum dmh_control_level active_level,
	bool has_idle_level,
	enum dmh_control_level idle_level
)
{
	if (!level_valid(active_level)) {
		return false;
	}
	if (mode == DMH_CONTROL_MODE_OPEN_DRAIN) {
		return active_level == DMH_CONTROL_LEVEL_LOW && !has_idle_level;
	}
	if (mode != DMH_CONTROL_MODE_PUSH_PULL || !has_idle_level ||
	    !level_valid(idle_level)) {
		return false;
	}
	return active_level != idle_level;
}

static int drive_apply(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_drive drive
)
{
	enum dmh_control_level level = drive == DMH_CONTROL_DRIVE_HIGH ?
		DMH_CONTROL_LEVEL_HIGH : DMH_CONTROL_LEVEL_LOW;
	int result;

	result = controller->port.set_enable(controller->port.context, channel, false);
	if (result != 0) {
		(void)controller->port.set_enable(controller->port.context, channel, false);
		return result;
	}
	result = controller->port.set_data(controller->port.context, channel, level);
	if (result != 0 || drive == DMH_CONTROL_DRIVE_HIGH_Z) {
		return result;
	}
	result = controller->port.set_enable(controller->port.context, channel, true);
	if (result != 0) {
		(void)controller->port.set_enable(controller->port.context, channel, false);
	}
	return result;
}

static enum dmh_control_drive configured_drive(
	const struct dmh_control_channel *channel,
	enum dmh_control_state state
)
{
	enum dmh_control_level level;

	if (channel->mode == DMH_CONTROL_MODE_OPEN_DRAIN &&
	    state == DMH_CONTROL_STATE_IDLE) {
		return DMH_CONTROL_DRIVE_HIGH_Z;
	}
	level = state == DMH_CONTROL_STATE_ACTIVE ?
		channel->active_level : channel->idle_level;
	return level == DMH_CONTROL_LEVEL_HIGH ?
		DMH_CONTROL_DRIVE_HIGH : DMH_CONTROL_DRIVE_LOW;
}

static enum dmh_control_result apply_configured_state(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_state state
)
{
	struct dmh_control_channel *configured = &controller->channels[channel];
	enum dmh_control_drive drive = configured_drive(configured, state);

	if (drive_apply(controller, channel, drive) != 0) {
		configured->drive = DMH_CONTROL_DRIVE_HIGH_Z;
		return DMH_CONTROL_HARDWARE_FAULT;
	}
	configured->drive = drive;
	return DMH_CONTROL_OK;
}

void dmh_control_init(
	struct dmh_control *controller,
	const struct dmh_control_port *port
)
{
	uint8_t channel;

	controller->port = *port;
	controller->pulse.active = false;
	controller->pulse.channel = 0U;
	controller->pulse.started_us = 0U;
	controller->pulse.duration_us = 0U;
	for (channel = 0U; channel < DMH_CONTROL_CHANNEL_COUNT; channel++) {
		controller->channels[channel] = (struct dmh_control_channel) {
			.configured = false,
			.mode = DMH_CONTROL_MODE_OPEN_DRAIN,
			.active_level = DMH_CONTROL_LEVEL_LOW,
			.idle_level = DMH_CONTROL_LEVEL_LOW,
			.has_idle_level = false,
			.drive = DMH_CONTROL_DRIVE_HIGH_Z,
		};
	}
}

bool dmh_control_is_configured(const struct dmh_control *controller, uint8_t channel)
{
	return channel_valid(channel) && controller->channels[channel].configured;
}

enum dmh_control_result dmh_control_configure(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_mode mode,
	enum dmh_control_level active_level,
	bool has_idle_level,
	enum dmh_control_level idle_level
)
{
	struct dmh_control_channel requested;
	enum dmh_control_drive idle_drive;

	if (!channel_valid(channel) ||
	    !configuration_valid(mode, active_level, has_idle_level, idle_level)) {
		return DMH_CONTROL_INVALID_ARGUMENT;
	}
	requested = (struct dmh_control_channel) {
		.configured = true,
		.mode = mode,
		.active_level = active_level,
		.idle_level = idle_level,
		.has_idle_level = has_idle_level,
		.drive = DMH_CONTROL_DRIVE_HIGH_Z,
	};
	idle_drive = configured_drive(&requested, DMH_CONTROL_STATE_IDLE);
	if (drive_apply(controller, channel, idle_drive) != 0) {
		controller->channels[channel].drive = DMH_CONTROL_DRIVE_HIGH_Z;
		return DMH_CONTROL_HARDWARE_FAULT;
	}
	requested.drive = idle_drive;
	controller->channels[channel] = requested;
	return DMH_CONTROL_OK;
}

enum dmh_control_result dmh_control_set_state(
	struct dmh_control *controller,
	uint8_t channel,
	enum dmh_control_state state
)
{
	if (!channel_valid(channel) ||
	    (state != DMH_CONTROL_STATE_ACTIVE && state != DMH_CONTROL_STATE_IDLE)) {
		return DMH_CONTROL_INVALID_ARGUMENT;
	}
	if (!controller->channels[channel].configured) {
		return DMH_CONTROL_NOT_CONFIGURED;
	}
	return apply_configured_state(controller, channel, state);
}

enum dmh_control_result dmh_control_pulse_start(
	struct dmh_control *controller,
	uint8_t channel,
	uint32_t pulse_ms,
	uint64_t now_us
)
{
	enum dmh_control_result result;

	if (!channel_valid(channel) || pulse_ms < DMH_CONTROL_PULSE_MIN_MS ||
	    pulse_ms > DMH_CONTROL_PULSE_MAX_MS) {
		return DMH_CONTROL_INVALID_ARGUMENT;
	}
	if (!controller->channels[channel].configured) {
		return DMH_CONTROL_NOT_CONFIGURED;
	}
	result = apply_configured_state(controller, channel, DMH_CONTROL_STATE_ACTIVE);
	if (result != DMH_CONTROL_OK) {
		return result;
	}
	controller->pulse = (struct dmh_control_pulse) {
		.active = true,
		.channel = channel,
		.started_us = now_us,
		.duration_us = (uint64_t)pulse_ms * 1000U,
	};
	return DMH_CONTROL_PENDING;
}

enum dmh_control_poll_result dmh_control_poll(
	struct dmh_control *controller,
	uint64_t now_us
)
{
	uint8_t channel;

	if (!controller->pulse.active ||
	    now_us - controller->pulse.started_us < controller->pulse.duration_us) {
		return DMH_CONTROL_POLL_NONE;
	}
	channel = controller->pulse.channel;
	controller->pulse.active = false;
	if (apply_configured_state(controller, channel, DMH_CONTROL_STATE_IDLE) !=
	    DMH_CONTROL_OK) {
		return DMH_CONTROL_POLL_HARDWARE_FAULT;
	}
	return DMH_CONTROL_POLL_COMPLETED;
}

enum dmh_control_result dmh_control_force_channel_safe(
	struct dmh_control *controller,
	uint8_t channel
)
{
	if (!channel_valid(channel)) {
		return DMH_CONTROL_INVALID_ARGUMENT;
	}
	if (controller->pulse.active && controller->pulse.channel == channel) {
		controller->pulse.active = false;
	}
	controller->channels[channel].drive = DMH_CONTROL_DRIVE_HIGH_Z;
	return drive_apply(controller, channel, DMH_CONTROL_DRIVE_HIGH_Z) == 0 ?
		DMH_CONTROL_OK : DMH_CONTROL_HARDWARE_FAULT;
}

enum dmh_control_result dmh_control_end_epoch(struct dmh_control *controller)
{
	enum dmh_control_result result = DMH_CONTROL_OK;
	uint8_t channel;

	controller->pulse.active = false;
	for (channel = 0U; channel < DMH_CONTROL_CHANNEL_COUNT; channel++) {
		if (drive_apply(controller, channel, DMH_CONTROL_DRIVE_HIGH_Z) != 0) {
			result = DMH_CONTROL_HARDWARE_FAULT;
		}
		controller->channels[channel].configured = false;
		controller->channels[channel].drive = DMH_CONTROL_DRIVE_HIGH_Z;
	}
	return result;
}
