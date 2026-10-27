/* Exercise the actual firmware line assembler with stdin/stdout as UART I/O. */
#define main fixture_main
#include "main.c"
#undef main

int main(int argc, char **argv)
{
    if (argc == 2 && strcmp(argv[1], "count-limit") == 0) {
        struct zephyr_fixture_context context = {.uart = &test_device};
        struct dmf_fixture fixture;
        unsigned char prefix[DMF_COMMAND_CAPACITY];
        struct dmf_line_diagnostics line = {.line_len = UINT32_MAX - 1U};

        memset(prefix, 'X', sizeof(prefix));
        dmf_fixture_init(&fixture, write_uart, sleep_ms, &context, "test-build");
        dmf_fixture_emit_boot(&fixture, DMF_BOOT_SUCCESS);
        count_line_byte(&line);
        dmf_fixture_handle_command(&fixture, prefix, 0U, 1, &line);
        count_line_byte(&line);
        dmf_fixture_handle_command(&fixture, prefix, 0U, 1, &line);
        return 0;
    }
    return fixture_main();
}
