#ifndef DUTCHMATE_FIXTURE_PROTOCOL_H_
#define DUTCHMATE_FIXTURE_PROTOCOL_H_

#include <stddef.h>

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
};

void dmf_fixture_init(
    struct dmf_fixture *fixture,
    dmf_write_fn write,
    dmf_sleep_fn sleep_ms,
    void *context,
    const char *build_id
);

void dmf_fixture_emit_boot(struct dmf_fixture *fixture, enum dmf_boot_mode mode);

void dmf_fixture_handle_command(
    struct dmf_fixture *fixture,
    const unsigned char *command,
    size_t length
);

#ifdef __cplusplus
}
#endif

#endif
