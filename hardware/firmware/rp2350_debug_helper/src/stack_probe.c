#include "stack_probe.h"

#include <ctype.h>
#include <stdbool.h>
#include <stdio.h>
#include <string.h>

#include <zephyr/debug/thread_analyzer.h>
#include <zephyr/kernel.h>

#define STACK_PROBE_MAX_ENTRIES 16U
#define STACK_PROBE_NAME_BYTES 25U

struct stack_probe_entry {
	char name[STACK_PROBE_NAME_BYTES];
	size_t used;
	size_t size;
};

static struct stack_probe_entry entries[STACK_PROBE_MAX_ENTRIES];
static size_t entry_count;
static size_t next_entry;
static bool ready;
static bool truncated;

static void record_entry(struct thread_analyzer_info *info)
{
	struct stack_probe_entry *entry;
	size_t index;

	if (entry_count == STACK_PROBE_MAX_ENTRIES) {
		truncated = true;
		return;
	}
	entry = &entries[entry_count++];
	for (index = 0U; index < STACK_PROBE_NAME_BYTES - 1U &&
	     info->name[index] != '\0'; index++) {
		unsigned char byte = (unsigned char)info->name[index];

		entry->name[index] = isalnum(byte) || byte == '_' || byte == '.' ?
			(char)byte : '_';
	}
	entry->name[index] = '\0';
	entry->used = info->stack_used;
	entry->size = info->stack_size;
}

void dutchmate_stack_probe_epoch_ended(void)
{
	if (ready) {
		if (next_entry == entry_count) {
			ready = false;
		}
		return;
	}
	entry_count = 0U;
	next_entry = 0U;
	truncated = false;
	thread_analyzer_run(record_entry, 0U);
	ready = true;
}

int dutchmate_stack_probe_firmware(char *output, size_t capacity)
{
	int length;

	if (output == NULL || capacity == 0U) {
		return -1;
	}
	if (!ready) {
		length = snprintf(output, capacity, "%s",
				  CONFIG_DUTCHMATE_FIRMWARE_VERSION);
	} else if (truncated || entry_count == 0U) {
		length = snprintf(output, capacity, "stack-error");
	} else {
		const struct stack_probe_entry *entry = &entries[next_entry];

		length = snprintf(output, capacity, "stack-%zuof%zu-%s-%zu-%zu",
				  next_entry + 1U, entry_count, entry->name,
				  entry->used, entry->size);
	}
	return length < 0 || (size_t)length >= capacity ? -1 : 0;
}

void dutchmate_stack_probe_hello_sent(void)
{
	if (ready) {
		if (truncated || entry_count == 0U) {
			next_entry = entry_count;
		} else if (next_entry < entry_count) {
			next_entry++;
		}
	}
}
