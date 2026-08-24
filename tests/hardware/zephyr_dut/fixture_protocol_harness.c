#include "fixture_protocol.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

struct harness_context {
    int trace_io;
};

static void write_bytes(void *context, const unsigned char *data, size_t length)
{
    const struct harness_context *harness = context;

    (void)fwrite(data, 1U, length, stdout);
    if (harness->trace_io != 0) {
        (void)fprintf(stderr, "W:%zu\n", length);
    }
}

static void sleep_ms(void *context, unsigned int duration_ms)
{
    const struct harness_context *harness = context;

    if (harness->trace_io != 0) {
        (void)fprintf(stderr, "S:%u\n", duration_ms);
    }
}

int main(int argc, char **argv)
{
    struct harness_context context = {0};
    struct dmf_fixture fixture;

    if (argc < 3) {
        return EXIT_FAILURE;
    }

    dmf_fixture_init(&fixture, write_bytes, sleep_ms, &context, "test-build");
    if (argc == 3 && strcmp(argv[1], "boot") == 0) {
        dmf_fixture_emit_boot(&fixture, (enum dmf_boot_mode)atoi(argv[2]));
    } else if (argc == 3 && strcmp(argv[1], "command") == 0) {
        dmf_fixture_handle_command(&fixture, (const unsigned char *)argv[2], strlen(argv[2]));
    } else if (argc == 3 && strcmp(argv[1], "trace-command") == 0) {
        context.trace_io = 1;
        dmf_fixture_handle_command(&fixture, (const unsigned char *)argv[2], strlen(argv[2]));
    } else if (argc == 4 && strcmp(argv[1], "sequence") == 0) {
        dmf_fixture_handle_command(&fixture, (const unsigned char *)argv[2], strlen(argv[2]));
        dmf_fixture_handle_command(&fixture, (const unsigned char *)argv[3], strlen(argv[3]));
    } else {
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
