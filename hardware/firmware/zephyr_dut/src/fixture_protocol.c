#include "fixture_protocol.h"

#include <stdio.h>
#include <string.h>

#define DMF_BURST_COUNT 2048U
#define DMF_SUSTAIN_COUNT 4096U
#define DMF_SUSTAIN_INTERVAL_MS 2U
#define DMF_FAULT_DELAY_MS 10000U

static void write_data(
    struct dmf_fixture *fixture,
    const unsigned char *data,
    size_t length
)
{
    fixture->write(fixture->context, data, length);
}

static void write_text(struct dmf_fixture *fixture, const char *text)
{
    write_data(fixture, (const unsigned char *)text, strlen(text));
}

static void write_hex(struct dmf_fixture *fixture, const unsigned char *data, size_t length)
{
    static const unsigned char hex[] = "0123456789abcdef";
    size_t index;

    for (index = 0U; index < length; index++) {
        const unsigned char encoded[] = {
            hex[data[index] >> 4U],
            hex[data[index] & 0x0fU],
        };

        write_data(fixture, encoded, sizeof(encoded));
    }
}

static int command_equals(
    const unsigned char *command,
    size_t length,
    const char *expected
)
{
    const size_t expected_length = strlen(expected);

    return length == expected_length && memcmp(command, expected, length) == 0;
}

static void emit_sequence(
    struct dmf_fixture *fixture,
    const char *name,
    unsigned int count,
    unsigned int interval_ms
)
{
    unsigned char line[96];
    unsigned int checksum = 0U;
    unsigned int sequence;
    int length;

    if (interval_ms == 0U) {
        length = snprintf(
            (char *)line,
            sizeof(line),
            "DMF/1 %s BEGIN count=%u\n",
            name,
            count
        );
    } else {
        length = snprintf(
            (char *)line,
            sizeof(line),
            "DMF/1 %s BEGIN count=%u interval_ms=%u\n",
            name,
            count,
            interval_ms
        );
    }
    if (length > 0 && (size_t)length < sizeof(line)) {
        write_data(fixture, line, (size_t)length);
    }

    for (sequence = 0U; sequence < count; sequence++) {
        length = snprintf(
            (char *)line,
            sizeof(line),
            "DMF/1 %s seq=%04u\n",
            name,
            sequence
        );
        if (length > 0 && (size_t)length < sizeof(line)) {
            write_data(fixture, line, (size_t)length);
        }
        checksum += sequence;
        if (interval_ms != 0U) {
            fixture->sleep_ms(fixture->context, interval_ms);
        }
    }

    length = snprintf(
        (char *)line,
        sizeof(line),
        "DMF/1 %s END count=%u checksum=%u\n",
        name,
        count,
        checksum
    );
    if (length > 0 && (size_t)length < sizeof(line)) {
        write_data(fixture, line, (size_t)length);
    }
}

void dmf_fixture_init(
    struct dmf_fixture *fixture,
    dmf_write_fn write,
    dmf_sleep_fn sleep_ms,
    void *context,
    const char *build_id
)
{
    fixture->write = write;
    fixture->sleep_ms = sleep_ms;
    fixture->context = context;
    fixture->build_id = build_id;
    fixture->silent = 0;
    fixture->fault_pending = 0;
    fixture->fault_due_ms = 0U;
}

void dmf_fixture_emit_boot(struct dmf_fixture *fixture, enum dmf_boot_mode mode)
{
    unsigned char message[128];
    const char *format;
    int length;

    fixture->fault_pending = 0;
    switch (mode) {
    case DMF_BOOT_SUCCESS:
        fixture->silent = 0;
        format = "DMF/1 BOOT OK board=rpi_pico build=%s\n";
        break;
    case DMF_BOOT_INIT_FAILURE:
        fixture->silent = 0;
        format = "DMF/1 ERROR INIT code=E_INIT_001 board=rpi_pico build=%s\n";
        break;
    case DMF_BOOT_SILENT:
        fixture->silent = 1;
        return;
    case DMF_BOOT_INVALID:
    default:
        fixture->silent = 0;
        format = "DMF/1 ERROR MODE code=E_MODE_001 board=rpi_pico build=%s\n";
        break;
    }

    length = snprintf((char *)message, sizeof(message), format, fixture->build_id);
    if (length > 0 && (size_t)length < sizeof(message)) {
        fixture->write(fixture->context, message, (size_t)length);
    }
}

void dmf_fixture_poll(struct dmf_fixture *fixture, uint64_t now_ms)
{
    if (fixture->fault_pending == 0) {
        return;
    }
    if (fixture->fault_due_ms == 0U) {
        /* Start the delay after the command handler and its ACK have returned. */
        fixture->fault_due_ms = now_ms + DMF_FAULT_DELAY_MS;
    }
    if (now_ms >= fixture->fault_due_ms) {
        fixture->fault_pending = 0;
        write_text(fixture, "DMF/1 ERROR ASYNC code=E_ASYNC_001\n");
    }
}

void dmf_fixture_handle_command(
    struct dmf_fixture *fixture,
    const unsigned char *command,
    size_t length,
    int discarding,
    const struct dmf_line_diagnostics *line
)
{
    static const unsigned char binary_payload[] = {
        'D', 'M', 'F', '/', '1', ' ', 'B', 'I', 'N', 'A', 'R', 'Y', ' ',
        0xf0U, 0x28U, 0x8cU, 0x28U, 0xffU, 0xfeU, '\n',
    };
    unsigned char message[128];
    int message_length;

    if (fixture->silent != 0) {
        return;
    }

    if (command_equals(command, length, "PING")) {
        write_text(fixture, "DMF/1 PONG\n");
    } else if (command_equals(command, length, "INFO")) {
        message_length = snprintf(
            (char *)message,
            sizeof(message),
            "DMF/1 INFO board=rpi_pico build=%s protocol=1\n",
            fixture->build_id
        );
        if (message_length > 0 && (size_t)message_length < sizeof(message)) {
            write_data(fixture, message, (size_t)message_length);
        }
    } else if (command_equals(command, length, "PARTIAL")) {
        write_text(fixture, "DMF/1 PART");
        fixture->sleep_ms(fixture->context, 50U);
        write_text(fixture, "IAL complete\n");
    } else if (command_equals(command, length, "BINARY")) {
        write_data(fixture, binary_payload, sizeof(binary_payload));
    } else if (command_equals(command, length, "BURST")) {
        emit_sequence(fixture, "BURST", DMF_BURST_COUNT, 0U);
    } else if (command_equals(command, length, "SUSTAIN")) {
        emit_sequence(
            fixture,
            "SUSTAIN",
            DMF_SUSTAIN_COUNT,
            DMF_SUSTAIN_INTERVAL_MS
        );
    } else if (command_equals(command, length, "DELAYFAULT")) {
        write_text(fixture, "DMF/1 DELAYFAULT armed delay_ms=10000\n");
        fixture->fault_pending = 1;
        fixture->fault_due_ms = 0U;
    } else if (command_equals(command, length, "SILENT")) {
        write_text(fixture, "DMF/1 SILENT armed-until-reset\n");
        fixture->silent = 1;
        fixture->fault_pending = 0;
    } else {
        message_length = snprintf(
            (char *)message,
            sizeof(message),
            "DMF/1 ERROR COMMAND code=E_COMMAND_001 command_len=%zu command_hex=",
            length
        );
        if (message_length > 0 && (size_t)message_length < sizeof(message)) {
            write_data(fixture, message, (size_t)message_length);
        }
        /* Encode the explicit length, including NULs; never use a string view. */
        write_hex(fixture, command, length);
        write_text(fixture, discarding != 0 ? " discard=1" : " discard=0");
        if (discarding != 0 && line != NULL) {
            if (line->counts_overflow != 0U) {
                write_text(fixture, " counts_overflow=1 prefix_hex=");
            } else {
                message_length = snprintf(
                    (char *)message, sizeof(message), " line_len=%lu prefix_hex=",
                    (unsigned long)line->line_len
                );
                if (message_length > 0 && (size_t)message_length < sizeof(message)) {
                    write_data(fixture, message, (size_t)message_length);
                }
            }
            write_hex(fixture, command, DMF_COMMAND_CAPACITY);
            write_text(fixture, " overflow_byte=");
            write_hex(fixture, &line->overflow_byte, 1U);
            if (line->counts_overflow == 0U) {
                message_length = snprintf(
                    (char *)message, sizeof(message), " discarded_count=%lu",
                    (unsigned long)(line->line_len - DMF_COMMAND_CAPACITY)
                );
                if (message_length > 0 && (size_t)message_length < sizeof(message)) {
                    write_data(fixture, message, (size_t)message_length);
                }
            }
            write_text(fixture, " suffix_hex=");
            write_hex(fixture, line->suffix, line->suffix_len);
        }
        write_text(fixture, "\n");
    }
}
