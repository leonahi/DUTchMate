#include "fixture_protocol.h"

#include <stdio.h>
#include <string.h>

#define DMF_BURST_COUNT 2048U
#define DMF_SUSTAIN_COUNT 4096U
#define DMF_SUSTAIN_INTERVAL_MS 2U

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
}

void dmf_fixture_emit_boot(struct dmf_fixture *fixture, enum dmf_boot_mode mode)
{
    unsigned char message[128];
    const char *format;
    int length;

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

void dmf_fixture_handle_command(
    struct dmf_fixture *fixture,
    const unsigned char *command,
    size_t length
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
    } else if (command_equals(command, length, "SILENT")) {
        write_text(fixture, "DMF/1 SILENT armed-until-reset\n");
        fixture->silent = 1;
    } else {
        write_text(fixture, "DMF/1 ERROR COMMAND code=E_COMMAND_001\n");
    }
}
