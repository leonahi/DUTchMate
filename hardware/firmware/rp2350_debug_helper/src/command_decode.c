#include "command_decode.h"

#include <errno.h>
#include <limits.h>
#include <string.h>

#define DMH_COMMAND_FRAME_MAX_BODY_BYTES 2047U
#define DMH_COMMAND_NAME_MAX_BYTES 23U
#define DMH_BASE64_MAX_BYTES 1368U

enum field_id {
	FIELD_CMD = 0,
	FIELD_CHANNEL,
	FIELD_MODE,
	FIELD_ACTIVE_LEVEL,
	FIELD_IDLE_LEVEL,
	FIELD_PULSE_MS,
	FIELD_STATE,
	FIELD_DATA_B64,
	FIELD_COUNT,
};

enum string_parse_result {
	STRING_PARSE_OK = 0,
	STRING_PARSE_SYNTAX,
	STRING_PARSE_LIMIT,
};

struct parser {
	const uint8_t *data;
	size_t length;
	size_t index;
};

struct raw_fields {
	uint32_t present;
	char cmd[DMH_COMMAND_NAME_MAX_BYTES + 1U];
	char channel[6];
	char mode[11];
	char active_level[5];
	char idle_level[5];
	char state[7];
	char data_b64[DMH_BASE64_MAX_BYTES + 1U];
	uint32_t pulse_ms;
};

static void skip_whitespace(struct parser *parser)
{
	while (parser->index < parser->length &&
	       (parser->data[parser->index] == ' ' ||
		parser->data[parser->index] == '\t')) {
		parser->index++;
	}
}

static int hex_value(uint8_t byte)
{
	if (byte >= '0' && byte <= '9') {
		return byte - '0';
	}
	if (byte >= 'a' && byte <= 'f') {
		return byte - 'a' + 10;
	}
	if (byte >= 'A' && byte <= 'F') {
		return byte - 'A' + 10;
	}
	return -1;
}

static enum string_parse_result append_string_byte(
	char *output,
	size_t output_capacity,
	size_t *output_length,
	uint8_t byte
)
{
	if (byte == 0U || *output_length + 1U >= output_capacity) {
		return STRING_PARSE_LIMIT;
	}
	output[*output_length] = (char)byte;
	(*output_length)++;
	return STRING_PARSE_OK;
}

static enum string_parse_result parse_unicode_escape(
	struct parser *parser,
	char *output,
	size_t output_capacity,
	size_t *output_length
)
{
	unsigned int codepoint = 0U;
	size_t count;

	if (parser->length - parser->index < 4U) {
		return STRING_PARSE_SYNTAX;
	}
	for (count = 0U; count < 4U; count++) {
		int digit = hex_value(parser->data[parser->index++]);

		if (digit < 0) {
			return STRING_PARSE_SYNTAX;
		}
		codepoint = (codepoint << 4U) | (unsigned int)digit;
	}
	if (codepoint > 0x7FU) {
		return STRING_PARSE_LIMIT;
	}
	return append_string_byte(
		output,
		output_capacity,
		output_length,
		(uint8_t)codepoint
	);
}

static enum string_parse_result parse_json_string(
	struct parser *parser,
	char *output,
	size_t output_capacity
)
{
	size_t output_length = 0U;

	if (parser->index >= parser->length || parser->data[parser->index] != '"') {
		return STRING_PARSE_SYNTAX;
	}
	parser->index++;
	while (parser->index < parser->length) {
		uint8_t byte = parser->data[parser->index++];
		enum string_parse_result result;

		if (byte == '"') {
			output[output_length] = '\0';
			return STRING_PARSE_OK;
		}
		if (byte < 0x20U || byte >= 0x80U) {
			return STRING_PARSE_SYNTAX;
		}
		if (byte != '\\') {
			result = append_string_byte(
				output, output_capacity, &output_length, byte
			);
		} else {
			if (parser->index >= parser->length) {
				return STRING_PARSE_SYNTAX;
			}
			byte = parser->data[parser->index++];
			if (byte == 'u') {
				result = parse_unicode_escape(
					parser,
					output,
					output_capacity,
					&output_length
				);
			} else {
				switch (byte) {
				case '"':
				case '\\':
				case '/':
					break;
				case 'b':
					byte = '\b';
					break;
				case 'f':
					byte = '\f';
					break;
				case 'n':
					byte = '\n';
					break;
				case 'r':
					byte = '\r';
					break;
				case 't':
					byte = '\t';
					break;
				default:
					return STRING_PARSE_SYNTAX;
				}
				result = append_string_byte(
					output, output_capacity, &output_length, byte
				);
			}
		}
		if (result != STRING_PARSE_OK) {
			return result;
		}
	}
	return STRING_PARSE_SYNTAX;
}

static int field_id_from_name(const char *name)
{
	static const char *const names[] = {
		[FIELD_CMD] = "cmd",
		[FIELD_CHANNEL] = "channel",
		[FIELD_MODE] = "mode",
		[FIELD_ACTIVE_LEVEL] = "active_level",
		[FIELD_IDLE_LEVEL] = "idle_level",
		[FIELD_PULSE_MS] = "pulse_ms",
		[FIELD_STATE] = "state",
		[FIELD_DATA_B64] = "data_b64",
	};
	size_t index;

	for (index = 0U; index < FIELD_COUNT; index++) {
		if (strcmp(name, names[index]) == 0) {
			return (int)index;
		}
	}
	return -1;
}

static enum string_parse_result parse_field_string(
	struct parser *parser,
	struct raw_fields *fields,
	enum field_id field
)
{
	switch (field) {
	case FIELD_CMD:
		return parse_json_string(parser, fields->cmd, sizeof(fields->cmd));
	case FIELD_CHANNEL:
		return parse_json_string(
			parser, fields->channel, sizeof(fields->channel)
		);
	case FIELD_MODE:
		return parse_json_string(parser, fields->mode, sizeof(fields->mode));
	case FIELD_ACTIVE_LEVEL:
		return parse_json_string(
			parser, fields->active_level, sizeof(fields->active_level)
		);
	case FIELD_IDLE_LEVEL:
		return parse_json_string(
			parser, fields->idle_level, sizeof(fields->idle_level)
		);
	case FIELD_STATE:
		return parse_json_string(parser, fields->state, sizeof(fields->state));
	case FIELD_DATA_B64:
		return parse_json_string(
			parser, fields->data_b64, sizeof(fields->data_b64)
		);
	case FIELD_PULSE_MS:
	case FIELD_COUNT:
		return STRING_PARSE_SYNTAX;
	}
	return STRING_PARSE_SYNTAX;
}

static bool parse_pulse_ms(struct parser *parser, uint32_t *value)
{
	uint32_t parsed = 0U;
	size_t start = parser->index;

	if (start >= parser->length || parser->data[start] < '0' ||
	    parser->data[start] > '9') {
		return false;
	}
	if (parser->data[start] == '0' && start + 1U < parser->length &&
	    parser->data[start + 1U] >= '0' && parser->data[start + 1U] <= '9') {
		return false;
	}
	while (parser->index < parser->length &&
	       parser->data[parser->index] >= '0' &&
	       parser->data[parser->index] <= '9') {
		uint32_t digit = parser->data[parser->index] - '0';

		if (parsed > (UINT32_MAX - digit) / 10U) {
			return false;
		}
		parsed = parsed * 10U + digit;
		parser->index++;
	}
	*value = parsed;
	return true;
}

static int parse_object(
	const uint8_t *frame,
	size_t frame_length,
	struct raw_fields *fields,
	enum dmh_command_decode_failure *failure
)
{
	struct parser parser = {
		.data = frame,
		.length = frame_length,
		.index = 1U,
	};

	if (frame_length < 2U || frame[0] != '{' || frame[frame_length - 1U] != '}') {
		*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
		return -EINVAL;
	}
	for (;;) {
		char key[17];
		enum string_parse_result string_result;
		int field_number;
		enum field_id field;

		skip_whitespace(&parser);
		if (parser.index >= parser.length) {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
		if (parser.data[parser.index] == '}') {
			parser.index++;
			break;
		}
		string_result = parse_json_string(&parser, key, sizeof(key));
		if (string_result != STRING_PARSE_OK) {
			*failure = string_result == STRING_PARSE_LIMIT ?
				DMH_COMMAND_DECODE_INVALID_ARGUMENT :
				DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
		field_number = field_id_from_name(key);
		if (field_number < 0) {
			*failure = DMH_COMMAND_DECODE_INVALID_ARGUMENT;
			return -EINVAL;
		}
		field = (enum field_id)field_number;
		if ((fields->present & (1U << field)) != 0U) {
			*failure = DMH_COMMAND_DECODE_INVALID_ARGUMENT;
			return -EINVAL;
		}
		skip_whitespace(&parser);
		if (parser.index >= parser.length || parser.data[parser.index] != ':') {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
		parser.index++;
		skip_whitespace(&parser);
		if (field == FIELD_PULSE_MS) {
			if (!parse_pulse_ms(&parser, &fields->pulse_ms)) {
				*failure = DMH_COMMAND_DECODE_INVALID_ARGUMENT;
				return -EINVAL;
			}
		} else {
			if (parser.index >= parser.length ||
			    parser.data[parser.index] != '"') {
				*failure = field == FIELD_CMD ?
					DMH_COMMAND_DECODE_INVALID_COMMAND :
					DMH_COMMAND_DECODE_INVALID_ARGUMENT;
				return -EINVAL;
			}
			string_result = parse_field_string(&parser, fields, field);
			if (string_result != STRING_PARSE_OK) {
				*failure = string_result == STRING_PARSE_SYNTAX ?
					DMH_COMMAND_DECODE_INVALID_COMMAND :
					DMH_COMMAND_DECODE_INVALID_ARGUMENT;
				return -EINVAL;
			}
		}
		fields->present |= 1U << field;
		skip_whitespace(&parser);
		if (parser.index >= parser.length) {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
		if (parser.data[parser.index] == '}') {
			parser.index++;
			break;
		}
		if (parser.data[parser.index] != ',') {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
		parser.index++;
		skip_whitespace(&parser);
		if (parser.index >= parser.length || parser.data[parser.index] == '}') {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
			return -EINVAL;
		}
	}
	if (parser.index != parser.length) {
		*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
		return -EINVAL;
	}
	return 0;
}

static bool decode_channel(const char *value, uint8_t *channel)
{
	if (strlen(value) != 5U || memcmp(value, "CTRL", 4U) != 0 ||
	    value[4] < '0' || value[4] > '3') {
		return false;
	}
	*channel = (uint8_t)(value[4] - '0');
	return true;
}

static bool decode_level(const char *value, enum dmh_control_level *level)
{
	if (strcmp(value, "low") == 0) {
		*level = DMH_CONTROL_LEVEL_LOW;
		return true;
	}
	if (strcmp(value, "high") == 0) {
		*level = DMH_CONTROL_LEVEL_HIGH;
		return true;
	}
	return false;
}

static int base64_value(char byte)
{
	if (byte >= 'A' && byte <= 'Z') {
		return byte - 'A';
	}
	if (byte >= 'a' && byte <= 'z') {
		return byte - 'a' + 26;
	}
	if (byte >= '0' && byte <= '9') {
		return byte - '0' + 52;
	}
	if (byte == '+') {
		return 62;
	}
	if (byte == '/') {
		return 63;
	}
	return -1;
}

static bool decode_base64(const char *encoded, struct dmh_uart_send_command *uart)
{
	size_t encoded_length = strlen(encoded);
	size_t input_index;
	size_t output_index = 0U;

	if (encoded_length < 4U || encoded_length > DMH_BASE64_MAX_BYTES ||
	    encoded_length % 4U != 0U) {
		return false;
	}
	for (input_index = 0U; input_index < encoded_length; input_index += 4U) {
		int first = base64_value(encoded[input_index]);
		int second = base64_value(encoded[input_index + 1U]);
		int third;
		int fourth;
		bool last = input_index + 4U == encoded_length;

		if (first < 0 || second < 0 || output_index >= sizeof(uart->data)) {
			return false;
		}
		uart->data[output_index++] =
			(uint8_t)(((unsigned int)first << 2U) |
				 ((unsigned int)second >> 4U));
		if (encoded[input_index + 2U] == '=') {
			if (!last || encoded[input_index + 3U] != '=') {
				return false;
			}
			continue;
		}
		third = base64_value(encoded[input_index + 2U]);
		if (third < 0 || output_index >= sizeof(uart->data)) {
			return false;
		}
		uart->data[output_index++] =
			(uint8_t)(((unsigned int)second << 4U) |
				 ((unsigned int)third >> 2U));
		if (encoded[input_index + 3U] == '=') {
			if (!last) {
				return false;
			}
			continue;
		}
		fourth = base64_value(encoded[input_index + 3U]);
		if (fourth < 0 || output_index >= sizeof(uart->data)) {
			return false;
		}
		uart->data[output_index++] =
			(uint8_t)(((unsigned int)third << 6U) | (unsigned int)fourth);
	}
	uart->length = output_index;
	return output_index > 0U;
}

static bool exact_fields(uint32_t actual, uint32_t required)
{
	return actual == required;
}

static bool decode_configure(
	const struct raw_fields *fields,
	struct dmh_command *command
)
{
	uint32_t required = (1U << FIELD_CMD) | (1U << FIELD_CHANNEL) |
			    (1U << FIELD_MODE) | (1U << FIELD_ACTIVE_LEVEL);
	struct dmh_configure_command *configure = &command->value.configure;

	if (!decode_channel(fields->channel, &command->channel) ||
	    !decode_level(fields->active_level, &configure->active_level)) {
		return false;
	}
	if (strcmp(fields->mode, "open_drain") == 0) {
		if (!exact_fields(fields->present, required) ||
		    configure->active_level != DMH_CONTROL_LEVEL_LOW) {
			return false;
		}
		configure->mode = DMH_CONTROL_MODE_OPEN_DRAIN;
		configure->has_idle_level = false;
	} else if (strcmp(fields->mode, "push_pull") == 0) {
		required |= 1U << FIELD_IDLE_LEVEL;
		if (!exact_fields(fields->present, required) ||
		    !decode_level(fields->idle_level, &configure->idle_level) ||
		    configure->active_level == configure->idle_level) {
			return false;
		}
		configure->mode = DMH_CONTROL_MODE_PUSH_PULL;
		configure->has_idle_level = true;
	} else {
		return false;
	}
	command->kind = DMH_COMMAND_CONFIGURE_GPIO_MODE;
	return true;
}

static bool decode_pulse(
	const struct raw_fields *fields,
	struct dmh_command *command
)
{
	uint32_t required = (1U << FIELD_CMD) | (1U << FIELD_CHANNEL) |
			    (1U << FIELD_PULSE_MS);

	if (!exact_fields(fields->present, required) || fields->pulse_ms < 1U ||
	    fields->pulse_ms > 10000U ||
	    !decode_channel(fields->channel, &command->channel)) {
		return false;
	}
	command->kind = DMH_COMMAND_PULSE_CONTROL;
	command->value.pulse_ms = fields->pulse_ms;
	return true;
}

static bool decode_state(
	const struct raw_fields *fields,
	struct dmh_command *command
)
{
	uint32_t required = (1U << FIELD_CMD) | (1U << FIELD_CHANNEL) |
			    (1U << FIELD_STATE);

	if (!exact_fields(fields->present, required) ||
	    !decode_channel(fields->channel, &command->channel)) {
		return false;
	}
	if (strcmp(fields->state, "active") == 0) {
		command->value.control_state = DMH_CONTROL_STATE_ACTIVE;
	} else if (strcmp(fields->state, "idle") == 0) {
		command->value.control_state = DMH_CONTROL_STATE_IDLE;
	} else {
		return false;
	}
	command->kind = DMH_COMMAND_SET_CONTROL_STATE;
	return true;
}

static bool decode_uart_send(
	const struct raw_fields *fields,
	struct dmh_command *command
)
{
	uint32_t required = (1U << FIELD_CMD) | (1U << FIELD_DATA_B64);

	if (!exact_fields(fields->present, required) ||
	    !decode_base64(fields->data_b64, &command->value.uart_send)) {
		return false;
	}
	command->kind = DMH_COMMAND_UART_SEND;
	return true;
}

int dmh_command_decode(
	const uint8_t *frame,
	size_t frame_length,
	struct dmh_command *command,
	enum dmh_command_decode_failure *failure
)
{
	struct raw_fields fields = {0};
	bool valid;

	if ((frame == NULL && frame_length > 0U) || command == NULL ||
	    failure == NULL) {
		return -EINVAL;
	}
	memset(command, 0, sizeof(*command));
	if (frame_length == 0U || frame_length > DMH_COMMAND_FRAME_MAX_BODY_BYTES ||
	    parse_object(frame, frame_length, &fields, failure) != 0) {
		if (frame_length == 0U || frame_length > DMH_COMMAND_FRAME_MAX_BODY_BYTES) {
			*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
		}
		return -EINVAL;
	}
	if ((fields.present & (1U << FIELD_CMD)) == 0U || fields.cmd[0] == '\0') {
		*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
		return -EINVAL;
	}
	if (strcmp(fields.cmd, "configure_gpio_mode") == 0) {
		valid = decode_configure(&fields, command);
	} else if (strcmp(fields.cmd, "pulse_control") == 0) {
		valid = decode_pulse(&fields, command);
	} else if (strcmp(fields.cmd, "set_control_state") == 0) {
		valid = decode_state(&fields, command);
	} else if (strcmp(fields.cmd, "uart_send") == 0) {
		valid = decode_uart_send(&fields, command);
	} else {
		*failure = DMH_COMMAND_DECODE_INVALID_COMMAND;
		return -EINVAL;
	}
	if (!valid) {
		memset(command, 0, sizeof(*command));
		*failure = DMH_COMMAND_DECODE_INVALID_ARGUMENT;
		return -EINVAL;
	}
	return 0;
}
