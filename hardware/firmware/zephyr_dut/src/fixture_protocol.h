#ifndef DUTCHMATE_FIXTURE_PROTOCOL_H_
#define DUTCHMATE_FIXTURE_PROTOCOL_H_

#include <stddef.h>
#include <stdint.h>

#define DMF_COMMAND_CAPACITY 32U
#define DMF_DISCARD_SUFFIX_CAPACITY 8U

#ifdef __cplusplus
extern "C" {
#endif

enum dmf_boot_mode {
    DMF_BOOT_SUCCESS = 0,
    DMF_BOOT_INIT_FAILURE = 1,
    DMF_BOOT_SILENT = 2,
    DMF_BOOT_INVALID = 3,
};

typedef void (*dmf_write_fn)(void *context, const unsigned char *data, size_t length);
typedef void (*dmf_sleep_fn)(void *context, unsigned int duration_ms);

struct dmf_fixture {
    dmf_write_fn write;
    dmf_sleep_fn sleep_ms;
    void *context;
    const char *build_id;
    int silent;
    int fault_pending;
    uint64_t fault_due_ms;
};

/* Fixed-size observation state; the prefix remains in the command buffer. */
struct dmf_line_diagnostics {
    uint32_t line_len;
    unsigned char overflow_byte;
    unsigned char suffix[DMF_DISCARD_SUFFIX_CAPACITY];
    unsigned char suffix_len;
    unsigned char counts_overflow;
};

void dmf_fixture_init(
    struct dmf_fixture *fixture,
    dmf_write_fn write,
    dmf_sleep_fn sleep_ms,
    void *context,
    const char *build_id
);

void dmf_fixture_emit_boot(struct dmf_fixture *fixture, enum dmf_boot_mode mode);

/* Poll from the UART owner loop with monotonic uptime in milliseconds. */
void dmf_fixture_poll(struct dmf_fixture *fixture, uint64_t now_ms);

/*
 * Discard state and line snapshot affect only unknown-command diagnostics.
 * For a discarded line with a snapshot, command still holds the first
 * DMF_COMMAND_CAPACITY bytes, even though the interpreted length is zero.
 */
void dmf_fixture_handle_command(
    struct dmf_fixture *fixture,
    const unsigned char *command,
    size_t length,
    int discarding,
    const struct dmf_line_diagnostics *line
);

#ifdef __cplusplus
}
#endif

#endif
